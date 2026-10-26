"""Embedding client shared by the ingestion script and the live app.

Both MUST use the same model: questions are only comparable with chunks that were
embedded by the same model (the app checks data/index/index_info.json at startup).
"""
import operator
import os
import time

import numpy as np
import requests
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings

EMBED_MODEL = "voyage-4"                 # Voyage AI, multilingual, 1024 numbers per vector
VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"
# Free account without a payment method: 3 requests and 10,000 tokens per minute.
# If you ever add a payment method, raise these to speed up indexing.
VOYAGE_RPM = 3
VOYAGE_TPM = 10_000
MAX_TOKENS_PER_REQUEST = 6_000           # stay well under the per-minute token budget


class TooManyRequests(Exception):
    """Voyage kept answering 429 'too many requests' for one batch."""


def estimate_tokens(text: str) -> int:
    """Rough token count, on the safe side: about 1 token per 2.5 characters.
    (German text produces more tokens per character than English.)"""
    return int(len(text) / 2.5) + 1


class VoyageEmbeddings(Embeddings):
    """LangChain-compatible embeddings via the Voyage AI API, paced to the account's
    rate limits. Documents (chunks) and queries (questions) are embedded with different
    `input_type`s, which Voyage uses to optimise retrieval."""

    def __init__(self, model: str = EMBED_MODEL, rpm: int = VOYAGE_RPM, tpm: int = VOYAGE_TPM):
        load_dotenv()   # reads VOYAGE_API_KEY from the .env file
        self.api_key = os.getenv("VOYAGE_API_KEY")
        if not self.api_key:
            raise SystemExit("VOYAGE_API_KEY is missing - add it to your .env file")
        self.model, self.rpm, self.tpm = model, rpm, tpm
        self.history: list[tuple[float, int]] = []   # (time, tokens) of recent requests

    def _wait_for_budget(self, tokens: int) -> None:
        """Sleep until one more request of `tokens` fits into the last-60-seconds budget."""
        while True:
            now = time.time()
            self.history = [(t, n) for t, n in self.history if now - t < 60]
            used = sum(n for _, n in self.history)
            if len(self.history) < self.rpm and used + tokens <= self.tpm:
                return
            wait = 60 - (now - self.history[0][0]) + 0.5
            print(f"   (rate limit: waiting {wait:.0f}s)")
            time.sleep(max(wait, 1))

    def _embed(self, texts: list[str], input_type: str, retries: int = 2) -> list[list[float]]:
        estimate = sum(estimate_tokens(t) for t in texts)
        for attempt in range(retries + 1):
            self._wait_for_budget(min(estimate, self.tpm))
            response = requests.post(
                VOYAGE_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts, "input_type": input_type},
                timeout=120,
            )
            if response.status_code == 429:          # too many requests: wait and retry
                print(f"   (Voyage says: too many requests - attempt {attempt + 1} of {retries + 1})")
                self.history.append((time.time(), self.tpm))   # block the budget for a minute
                continue
            if response.status_code != 200:
                raise SystemExit(f"Voyage API error {response.status_code}: {response.text}")
            body = response.json()
            self.history.append((time.time(), body.get("usage", {}).get("total_tokens", estimate)))
            return [d["embedding"] for d in sorted(body["data"], key=operator.itemgetter("index"))]
        raise TooManyRequests

    def _embed_adaptive(self, texts: list[str], input_type: str) -> list[list[float]]:
        """Embed a batch; if Voyage keeps refusing it (probably too many tokens for one
        minute), split it in half and embed both halves separately."""
        try:
            return self._embed(texts, input_type)
        except TooManyRequests:
            if len(texts) == 1:
                raise SystemExit("Voyage refuses even a single chunk - try again later.") from None
            half = len(texts) // 2
            print(f"   (splitting this batch of {len(texts)} chunks into {half} + {len(texts) - half})")
            return self._embed_adaptive(texts[:half], input_type) + self._embed_adaptive(texts[half:], input_type)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_adaptive(texts, "document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed_adaptive([text], "query")[0]


def normalise(vectors: np.ndarray) -> np.ndarray:
    """Scale every vector to length 1, so similarity = a simple dot product."""
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)