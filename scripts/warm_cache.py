"""Fill data/answer_cache.json with answers to the example questions, so the demo's
example buttons answer instantly and for free.

    python scripts/warm_cache.py            reuse answers from eval/results.json (0 tokens)
    python scripts/warm_cache.py --live     ask the pipeline again (uses Groq tokens)

Commit data/answer_cache.json to the repo afterwards.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.main import CACHE_FILE, EXAMPLES, cache_key, to_response
from app.pipeline import ask

EVAL_RESULTS = ROOT / "eval" / "results.json"


def from_eval(question: str) -> dict | None:
    """Rebuild a pipeline result from a saved evaluation run (same question text)."""
    results = json.loads(EVAL_RESULTS.read_text(encoding="utf-8")) if EVAL_RESULTS.exists() else {}
    for r in results.values():
        if r["question"] == question:
            return {"question": question, "answer": r["answer"], "sources": r["sources"], "trace": r["trace"],
                    "reflection": {"checked": r["faithfulness"] is not None, "faithfulness": r["faithfulness"],
                                   "claims": [], "flags": r["flags"]},
                    "tokens_used": r["tokens"], "seconds": r["seconds"], "model": "openai/gpt-oss-120b"}
    return None


if __name__ == "__main__":
    live = "--live" in sys.argv
    cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}
    for example in EXAMPLES:
        q = example["question"]
        result = ask(q) if live else from_eval(q)
        if result is None:
            print(f"NOT FOUND in eval/results.json (run with --live): {q}")
            continue
        if result.get("error"):
            print(f"FAILED ({result['error']}): {q}")
            continue
        cache[cache_key(q)] = to_response(result)
        print(f"cached: {q}")
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(cache)} answers in {CACHE_FILE}")