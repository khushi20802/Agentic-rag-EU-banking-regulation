"""One call for the whole question-answering pipeline: agent (Step 7) + reflection (Step 8).
This is what the web API will call.

Try it:   python -m app.pipeline "What should firms check when onboarding customers remotely by video?"
"""
import sys
import time

from app.agent import answer_question, print_result
from app.llm import DailyLimitReached, GroqClient
from app.reflect import reflect

DAILY_LIMIT_MESSAGE = ("The free demo has used up today's AI budget. Please try again tomorrow, "
                       "or use one of the example questions.")


def ask(question: str) -> dict:
    """Answer a question and check the answer. Always returns a dict (never crashes on limits)."""
    started = time.time()
    llm = GroqClient()            # one client, so tokens_used covers the agent AND the check
    try:
        result = answer_question(question, llm=llm)
        result["reflection"] = reflect(result, llm=llm)
    except DailyLimitReached:
        return {"question": question, "answer": DAILY_LIMIT_MESSAGE, "sources": [], "trace": [],
                "reflection": None, "error": "daily_limit"}
    result["tokens_used"] = llm.tokens_used
    result["seconds"] = round(time.time() - started, 1)
    return result


def print_reflection(reflection: dict | None) -> None:
    if not reflection:
        return
    print("\n=== REFLECTION")
    if reflection.get("note"):
        print("   " + reflection["note"])
    for c in reflection["claims"]:
        mark = {"supported": "OK  ", "partially_supported": "PART", "unsupported": "FLAG"}[c["verdict"]]
        print(f"   {mark} {c['claim']}  {c['cited']}  - {c['reason']}")
    if reflection["faithfulness"] is not None:
        print(f"   faithfulness: {reflection['faithfulness']:.0%} of checked claims fully supported")
    for f in reflection["flags"]:
        if f["verdict"] == "no_sources":
            print(f"   NOTE {f['reason']}")
    real_flags = [f for f in reflection["flags"] if f["verdict"] != "no_sources"]
    if real_flags:
        print(f"   {len(real_flags)} claim(s) flagged for the user")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What should firms check when onboarding customers remotely by video?"
    res = ask(q)
    if res.get("error"):
        print(res["answer"])
    else:
        print_result(res)
        print_reflection(res["reflection"])
        print(f"\n(total: {res['tokens_used']} tokens, {res['seconds']}s)")