"""Evaluation (Step 9).

    python eval/run_eval.py run                 ask all questions (resumes; saves after each one)
    python eval/run_eval.py run --rerun H2      ask one question again
    python eval/run_eval.py grade               write eval/grading.md + eval/grades.json to fill in
    python eval/run_eval.py reflection-test     plant false claims, check that reflection flags them
    python eval/run_eval.py report              metrics table -> eval/results.md
    python eval/run_eval.py report --version v1 tables for a saved run: reads eval/results_v1.json +
                                                eval/grades_v1.json, writes eval/results_v1.md

Metrics
    routing      the agent used the expected tools (chained: query_documents BEFORE search_documents;
                 catalogue: no content search needed)                           -> automatic
    doc recall   share of the expected documents the answer actually cites       -> automatic
    faithful     share of checked claims the reflection step marked 'supported'  -> automatic
    correct      does the answer contain the key points? 0 / 0.5 / 1             -> graded by you
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.llm import DailyLimitReached, GroqClient
from app.pipeline import ask
from app.reflect import reflect

EVAL_DIR = ROOT / "eval"
QUESTIONS = EVAL_DIR / "questions.json"
RESULTS = EVAL_DIR / "results.json"          # raw results, one entry per question id
GRADES = EVAL_DIR / "grades.json"            # your 0 / 0.5 / 1 scores
REFLECTION_TEST = EVAL_DIR / "reflection_test.json"


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ============================================================ run
def cited_doc_ids(result: dict) -> list[str]:
    numbers = {int(n) for n in re.findall(r"\[(\d+)\]", result["answer"])}
    return sorted({s["doc_id"] for s in result["sources"] if s["n"] in numbers})


def routing_ok(q: dict, tools_used: list[str]) -> bool:
    if q["category"] == "chained":
        return ("query_documents" in tools_used and "search_documents" in tools_used
                and tools_used.index("query_documents") < tools_used.index("search_documents"))
    if q["category"] == "catalogue":
        return "query_documents" in tools_used and "search_documents" not in tools_used
    return all(t in tools_used for t in q["expected_tools"])


def run(rerun: str | None) -> None:
    questions = load(QUESTIONS, [])
    results = load(RESULTS, {})
    rerun_ids = {x.strip() for x in rerun.split(",")} if rerun else set()
    todo = [q for q in questions if q["id"] in rerun_ids] if rerun else [q for q in questions if q["id"] not in results]
    print(f"{len(results)} done, {len(todo)} to run")

    for i, q in enumerate(todo, start=1):
        print(f"\n[{i}/{len(todo)}] {q['id']} ({q['category']}): {q['question']}")
        res = ask(q["question"])
        if res.get("error") == "daily_limit":
            print("Groq's daily budget is used up - stopping. Run the same command tomorrow to continue.")
            break
        tools_used = [t["tool"] for t in res["trace"]]
        reflection = res["reflection"] or {}
        results[q["id"]] = {
            "question": q["question"], "category": q["category"],
            "answer": res["answer"], "trace": res["trace"],
            "tools_used": tools_used, "tool_calls": len(tools_used),
            "routing_ok": routing_ok(q, tools_used),
            "cited_docs": cited_doc_ids(res), "expected_docs": q["expected_docs"],
            "faithfulness": reflection.get("faithfulness"), "flags": reflection.get("flags", []),
            "sources": res["sources"], "tokens": res["tokens_used"], "seconds": res["seconds"],
            "run_at": time.strftime("%Y-%m-%d %H:%M"),
        }
        save(RESULTS, results)        # save after EVERY question, so nothing is lost
        r = results[q["id"]]
        print(f"   tools: {tools_used}  routing ok: {r['routing_ok']}  cited: {r['cited_docs']}  "
              f"faithfulness: {r['faithfulness']}  tokens: {r['tokens']}  {r['seconds']}s")


# ============================================================ grade
def grade() -> None:
    questions, results = load(QUESTIONS, []), load(RESULTS, {})
    grades = load(GRADES, {})
    instructions = (
        "For each question, compare the answer with the key points and enter a score in "
        "`eval/grades.json`: **1** = all key points correct, **0.5** = partly correct or incomplete, "
        "**0** = wrong or invented. For `not_in_corpus` questions: 1 = clearly says the information "
        "is not available (and does not invent it)."
    )
    lines = ["# Grading sheet", "", instructions, ""]
    for q in questions:
        if q["id"] not in results:
            continue
        r = results[q["id"]]
        grades.setdefault(q["id"], None)
        lines += [f"## {q['id']} ({q['category']}): {q['question']}", "", "**Key points:**"]
        lines += [f"- {k}" for k in q["key_points"]]
        meta = (f"**Tools:** {r['tools_used']} | **cited docs:** {r['cited_docs']} | "
                f"**expected docs:** {r['expected_docs']}")
        lines += ["", meta, "", "**Answer:**", "", r["answer"], ""]
        if r["flags"]:
            lines += ["**Reflection flags:**"] + [f"- {f['verdict']}: {f['claim']} ({f['reason']})" for f in r["flags"]] + [""]
        lines += ["---", ""]
    (EVAL_DIR / "grading.md").write_text("\n".join(lines), encoding="utf-8")
    save(GRADES, grades)
    print("Wrote eval/grading.md (read it) and eval/grades.json (enter your scores there: 1, 0.5 or 0).")


# ============================================================ reflection test
FALSE_CLAIMS = [
    "Institutions must keep all onboarding video recordings for at least 25 years [{n}].",
    "This requirement does not apply to banks with fewer than 500 employees [{n}].",
    "Breaches are punished with a fine of exactly EUR 10,000 per customer [{n}].",
]


def reflection_test() -> None:
    """Plant one invented claim into each of three real answers, citing a real source.
    A good checker must flag every planted claim."""
    results = load(RESULTS, {})
    candidates = [r for r in results.values() if r["category"] in ("content", "cross_lingual") and r["sources"]][:3]
    if len(candidates) < 3:
        raise SystemExit("Run the evaluation first (need 3 answered content questions).")
    llm, report = GroqClient(), []
    for r, template in zip(candidates, FALSE_CLAIMS, strict=True):
        n = min(int(x) for x in re.findall(r"\[(\d+)\]", r["answer"]) or ["1"])
        planted = template.format(n=n)
        tampered = {"answer": r["answer"] + "\n\n" + planted, "sources": r["sources"]}
        try:
            reflection = reflect(tampered, llm=llm)
        except DailyLimitReached:
            raise SystemExit("Groq's daily budget is used up - try again tomorrow.") from None
        caught = any(f["verdict"] != "supported" and _overlap(f["claim"], planted) for f in reflection["flags"])
        report.append({"question": r["question"], "planted": planted, "caught": caught})
        print(f"{'CAUGHT ' if caught else 'MISSED '} {planted}")
    save(REFLECTION_TEST, report)
    print(f"\nReflection caught {sum(x['caught'] for x in report)}/{len(report)} planted false claims.")


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3}


def _overlap(claim: str, planted: str) -> bool:
    """Did the checker flag the planted sentence? (shared distinctive words)"""
    return len(_words(claim) & _words(planted)) >= 2


# ============================================================ report
def report(version: str | None = None) -> None:
    suffix = f"_{version}" if version else ""
    results = load(EVAL_DIR / f"results{suffix}.json", {})
    grades = load(EVAL_DIR / f"grades{suffix}.json", {})
    questions = load(QUESTIONS, [])
    if not results:
        raise SystemExit(f"No eval/results{suffix}.json found.")
    rows = []
    for q in questions:
        if q["id"] not in results:
            continue
        r = results[q["id"]]
        expected = set(r["expected_docs"])
        recall = len(expected & set(r["cited_docs"])) / len(expected) if expected else None
        rows.append({"id": q["id"], "category": q["category"], "routing": r["routing_ok"],
                     "recall": recall, "faithful": r["faithfulness"], "correct": grades.get(q["id"]),
                     "calls": r["tool_calls"], "tokens": r["tokens"], "seconds": r["seconds"]})

    def avg(values):
        values = [float(v) for v in values if v is not None]
        return sum(values) / len(values) if values else None

    def pct(v):
        return "–" if v is None else f"{v:.0%}"

    categories = ["catalogue", "content", "cross_lingual", "chained", "not_in_corpus"]
    table = ["| Category | Questions | Routing | Doc recall | Faithfulness | Correctness | Avg tool calls | Avg tokens | Avg seconds |",
             "|---|---|---|---|---|---|---|---|---|"]
    for cat in [*categories, "all"]:
        group = [r for r in rows if cat == "all" or r["category"] == cat]
        if not group:
            continue
        name = "**All**" if cat == "all" else cat
        table.append(f"| {name} | {len(group)} | {pct(avg(r['routing'] for r in group))} | "
                     f"{pct(avg(r['recall'] for r in group))} | {pct(avg(r['faithful'] for r in group))} | "
                     f"{pct(avg(r['correct'] for r in group))} | {avg(r['calls'] for r in group):.1f} | "
                     f"{avg(r['tokens'] for r in group):,.0f} | {avg(r['seconds'] for r in group):.0f} |")

    per_question = ["| ID | Routing | Doc recall | Faithfulness | Correct | Tool calls | Tokens |", "|---|---|---|---|---|---|---|"]
    per_question += [f"| {r['id']} | {'✅' if r['routing'] else '❌'} | {pct(r['recall'])} | {pct(r['faithful'])} | "
                     f"{'–' if r['correct'] is None else r['correct']} | {r['calls']} | {r['tokens']:,} |" for r in rows]

    test = load(EVAL_DIR / f"reflection_test{suffix}.json", [])
    title = f"# Evaluation results{' (' + version + ')' if version else ''}"
    out = [title, "", f"{len(rows)} questions, model: openai/gpt-oss-120b (Groq), embeddings: voyage-4", "",
           *table, ""]
    if test:
        out += [f"**Reflection test:** {sum(t['caught'] for t in test)}/{len(test)} planted false claims flagged.", ""]
    out += ["## Per question", "", *per_question, ""]
    (EVAL_DIR / f"results{suffix}.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    missing = [r["id"] for r in rows if r["correct"] is None]
    if missing:
        print(f"\nNot graded yet: {missing} - fill in eval/grades{suffix}.json, then run 'report' again.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["run", "grade", "reflection-test", "report"])
    parser.add_argument("--rerun", help="question id(s) to ask again, e.g. H2 or X1,X2,X3")
    parser.add_argument("--version", help="report on a saved run, e.g. v1 (eval/results_v1.json)")
    args = parser.parse_args()
    {"run": lambda: run(args.rerun), "grade": grade, "reflection-test": reflection_test,
     "report": lambda: report(args.version)}[args.mode]()