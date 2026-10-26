"""Web API (Step 10).

    GET  /               the web page (static/index.html, Step 11)
    GET  /api/health     is the app alive? (used by Render)
    GET  /api/examples   example questions for the buttons
    POST /api/ask        {"question": "..."} -> answer, citations, trace, reflection

Run locally:   uvicorn app.main:app --reload
Then open:     http://127.0.0.1:8000/docs   (FastAPI's automatic API docs)
"""
import contextlib
import hashlib
import json
import logging
import re
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.embeddings import EMBED_MODEL
from app.llm import LLM_MODEL
from app.pipeline import ask
from app.tools import load_store

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
CACHE_FILE = ROOT / "data" / "answer_cache.json"   # committed to the repo: examples stay instant

EXAMPLES = [
    {"label": "Content", "question": "What should firms check when onboarding customers remotely by video?"},
    {"label": "Catalogue → content (chained)",
     "question": "What do AML documents issued after 2022 say about enhanced due diligence for high-risk customers?"},
    {"label": "Cross-lingual (EN → DE sources)",
     "question": "How must the front office and back office be separated in lending under German rules?"},
]

MAX_QUESTION_CHARS = 500
LLM_WAIT_SECONDS = 150          # how long a visitor waits for the one-at-a-time lock
PER_MINUTE, PER_DAY = 3, 15     # new (uncached) questions per visitor; cached answers are free

log = logging.getLogger("regrag")


# ============================================================ rate limit (per visitor)
class RateLimiter:
    """Counts only questions that really use the LLM. Cached answers never count,
    so the example buttons keep working for everyone."""

    def __init__(self, per_minute: int, per_day: int):
        self.per_minute, self.per_day = per_minute, per_day
        self.history: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def check_and_count(self, visitor: str) -> str | None:
        """Return None if allowed (and count it), or a message explaining the limit."""
        now = time.time()
        with self.lock:
            times = self.history[visitor]
            while times and now - times[0] > 86_400:
                times.popleft()
            if len(times) >= self.per_day:
                return f"You have asked {self.per_day} new questions today - please come back tomorrow."
            if sum(now - t < 60 for t in times) >= self.per_minute:
                return f"Please wait a minute - at most {self.per_minute} new questions per minute."
            times.append(now)
            return None


def visitor_id(request: Request) -> str:
    """The visitor's IP. Behind Render's proxy the real IP is the first X-Forwarded-For entry."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


rate_limiter = RateLimiter(PER_MINUTE, PER_DAY)

# ============================================================ answer cache
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()


def cache_key(question: str) -> str:
    """Same question, different spacing/case/final '?' -> same key."""
    normalised = re.sub(r"\s+", " ", question.strip().lower()).rstrip(" ?!.")
    return hashlib.sha256(normalised.encode()).hexdigest()[:16]


def load_cache() -> None:
    if CACHE_FILE.exists():
        _cache.update(json.loads(CACHE_FILE.read_text(encoding="utf-8")))


def save_to_cache(question: str, response: dict) -> None:
    with _cache_lock:
        _cache[cache_key(question)] = response
        with contextlib.suppress(OSError):   # best effort: Render's free-tier disk is temporary anyway
            CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False, indent=1), encoding="utf-8")


# ============================================================ response shape
def to_response(result: dict) -> dict:
    """Turn the pipeline result into the JSON contract the web page uses."""
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", result["answer"])}
    citations = [{
        "n": s["n"], "citation": s["citation"], "type": s["type"], "doc_id": s["doc_id"],
        "reference": s["reference"], "language": s.get("language"), "url": s.get("url"),
        "snippet": " ".join(s["text"].split())[:600],
    } for s in result["sources"] if s["n"] in cited]
    reflection = result.get("reflection") or {}
    return {
        "question": result["question"],
        "answer": result["answer"],
        "citations": citations,
        "trace": result["trace"],
        "reflection": {
            "checked": reflection.get("checked", False),
            "faithfulness": reflection.get("faithfulness"),
            "claims": reflection.get("claims", []),
            "flags": reflection.get("flags", []),
            "note": reflection.get("note"),
        },
        "meta": {"cached": False, "tokens": result.get("tokens_used"), "seconds": result.get("seconds"),
                 "model": result.get("model", LLM_MODEL), "embedding_model": EMBED_MODEL},
    }


# ============================================================ app
@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_store()      # load FAISS index + chunks once at startup (fails fast if files are missing)
    load_cache()
    yield


app = FastAPI(title="RegRAG: agentic RAG over EBA & BaFin regulation", lifespan=lifespan)

_llm_lock = threading.Lock()     # Groq's per-minute budget is shared by ALL visitors: one at a time

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=MAX_QUESTION_CHARS)


@app.get("/")
def index():
    page = STATIC_DIR / "index.html"
    if page.exists():
        return FileResponse(page)
    return {"message": "API is running. The web page (static/index.html) is added in Step 11. See /docs."}


@app.get("/api/health")
def health():
    index, records = load_store()
    return {"status": "ok", "chunks": index.ntotal, "documents": len({r["metadata"]["doc_id"] for r in records}),
            "llm": LLM_MODEL, "embeddings": EMBED_MODEL, "cached_answers": len(_cache)}


@app.get("/api/examples")
def examples():
    return [{**e, "cached": cache_key(e["question"]) in _cache} for e in EXAMPLES]


@app.post("/api/ask")
def ask_endpoint(request: Request, body: AskRequest):
    question = body.question.strip()
    cached = _cache.get(cache_key(question))
    if cached:                                   # instant, free, never rate-limited
        return {**cached, "meta": {**cached["meta"], "cached": True}}

    limit_message = rate_limiter.check_and_count(visitor_id(request))
    if limit_message:
        return JSONResponse(status_code=429, content={
            "error": "rate_limit", "message": limit_message + " The example questions still work instantly."})

    if not _llm_lock.acquire(timeout=LLM_WAIT_SECONDS):
        return JSONResponse(status_code=503, content={
            "error": "busy", "message": "The demo is answering other questions right now. Please try again in a minute."})
    try:
        result = ask(question)
    except Exception as exc:
        # deliberately catch everything: log the details (visible in Render's logs),
        # but never show a stack trace to visitors
        log.exception("Error while answering %r", question)
        return JSONResponse(status_code=500, content={
            "error": "internal", "message": f"Something went wrong while answering: {type(exc).__name__}."})
    finally:
        _llm_lock.release()

    if result.get("error") == "daily_limit":
        return JSONResponse(status_code=429, content={"error": "daily_limit", "message": result["answer"]})

    response = to_response(result)
    save_to_cache(question, response)
    return response