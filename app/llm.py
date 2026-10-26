"""Minimal Groq chat client (OpenAI-compatible API) with retry on rate limits.

Free tier for openai/gpt-oss-120b: 30 requests/min, 8,000 tokens/min, 200,000 tokens/day.
When Groq answers 429 'too many requests', it says how long to wait; we wait and retry.
If the DAILY budget is used up, waiting does not help, so we raise DailyLimitReached
and the app can show a friendly message instead.
"""
import os
import re
import time

import requests
from dotenv import load_dotenv

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
LLM_MODEL = "openai/gpt-oss-120b"


class DailyLimitReached(Exception):
    """The free tier's daily token or request budget is used up."""


class GroqClient:
    def __init__(self, model: str = LLM_MODEL, max_retries: int = 4):
        load_dotenv()   # reads GROQ_API_KEY from the .env file
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise SystemExit("GROQ_API_KEY is missing - add it to your .env file")
        self.model = model
        self.max_retries = max_retries
        self.tokens_used = 0          # running total, shown in the trace

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             tool_choice: str = "auto", temperature: float = 0.1) -> dict:
        """Send the conversation; return the assistant's message (text and/or tool calls)."""
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        if tools:
            payload |= {"tools": tools, "tool_choice": tool_choice}

        for attempt in range(self.max_retries + 1):
            r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {self.api_key}"},
                              json=payload, timeout=90)
            if r.status_code == 429:
                if "per day" in r.text.lower() or "(tpd)" in r.text.lower() or "(rpd)" in r.text.lower():
                    raise DailyLimitReached(r.text)
                wait = _retry_after(r)
                print(f"   (Groq rate limit: waiting {wait:.0f}s, attempt {attempt + 1}/{self.max_retries})")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                raise RuntimeError(f"Groq error {r.status_code}: {r.text}")
            body = r.json()
            self.tokens_used += body.get("usage", {}).get("total_tokens", 0)
            return body["choices"][0]["message"]
        raise RuntimeError("Groq kept refusing requests - try again in a minute.")


def _retry_after(response: requests.Response) -> float:
    """How long Groq asks us to wait: the Retry-After header, or 'try again in 7.5s' in the text."""
    header = response.headers.get("retry-after")
    if header:
        try:
            return float(header) + 1
        except ValueError:
            pass
    m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", response.text)
    if m:
        return int(m.group(1) or 0) * 60 + float(m.group(2)) + 1
    return 20.0