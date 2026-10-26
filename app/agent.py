"""The agent loop (Step 7): an LLM decides which tools to call, in which order,
and writes an answer that cites numbered sources.

    question -> LLM -> tool call(s) -> results (numbered sources) -> LLM -> ... -> answer [1][3]

Try it:   python -m app.agent "Which AML documents were issued after 2022?"
"""
import json
import re
import sys
import time

from app.llm import GroqClient
from app.tools import allowed_values, query_documents, search_documents

MAX_TOOL_ROUNDS = 4          # after this, the LLM must answer with what it has
TEXT_FOR_LLM = 900           # characters of each chunk sent to the LLM (saves tokens)
SEARCH_K = 4                 # chunks per search sent to the LLM

SYSTEM_PROMPT = """You are a research assistant for banking regulation. The corpus contains
EBA guidelines (English) and BaFin documents (German). Today is {today}.

Tools:
- query_documents: the document CATALOGUE (which documents exist, dates, topics, issuer,
  language, and relations: amends / amended_by / adopts). Use it for questions about documents.
- search_documents: the CONTENT of the documents. Searches across languages.

Rules:
1. Never answer from memory. Every fact must come from a tool result.
2. Use as few tool calls as possible, and only set filters the question actually asks for.
   For a pure content question, call search_documents directly (no catalogue lookup needed).
3. If a content question is limited by metadata (e.g. "AML documents after 2022"), first call
   query_documents, then search_documents with those doc_ids.
4. Only restrict doc_ids when the question or a catalogue lookup tells you which documents;
   otherwise search all documents (leave doc_ids out). When comparing documents or regulators,
   search each document separately (one doc_id per call).
5. LANGUAGE: write the whole answer in the language of the QUESTION (English question -> English
   answer), even when the sources are German. You may add the original term in brackets,
   e.g. "back office (Marktfolge)".
6. Cite every factual sentence with the source numbers from the tool results. Write citations
   exactly as [2] or [1][4] - plain square brackets, number only. Never invent numbers like [2a].
7. Keep the source's normative strength: "should" stays "should" (EBA guidelines say "should"),
   "muss" = "must", "kann/darf" = "may". Do not turn a recommendation into an obligation.
   Report the wording; do not add your own commentary on whether rules are binding.
8. Do not add examples, numbers or details that are not in the sources.
9. If the tool results do not contain the answer, say so plainly. If a document is only
   referenced (e.g. an EBA guideline adopted by a BaFin circular) but its text is not in the
   corpus, say that its content is not available - do not describe it using other documents.
10. Be concise and well-structured."""



def document_guide() -> str:
    """One line per document: 'doc_id = title (issuer, language)', read from the database,
    so the LLM knows what each doc_id is about instead of guessing from the id."""
    docs = query_documents()["documents"]
    return "; ".join(f"{d['doc_id']} = {d['title']} ({d['issuer']}, {d['language']})" for d in docs)


def tool_schemas() -> list[dict]:
    """Describe both tools to the LLM. Allowed values come from the database itself."""
    v = allowed_values()
    return [
        {"type": "function", "function": {
            "name": "query_documents",
            "description": "List documents in the catalogue by metadata (not content). All filters optional.",
            "parameters": {"type": "object", "properties": {
                "topic": {"type": "string", "enum": v["topic"]},
                "issuer": {"type": "string", "enum": v["issuer"]},
                "language": {"type": "string", "enum": v["language"]},
                "doc_type": {"type": "string", "enum": v["doc_type"]},
                "date_from": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
                "reference": {"type": "string", "description": "part of a reference, e.g. '2021/02' or '14/2026'"},
            }},
        }},
        {"type": "function", "function": {
            "name": "search_documents",
            "description": "Find the passages most relevant to a query in the documents' content.",
            "parameters": {"type": "object", "required": ["query"], "properties": {
                "query": {"type": "string", "description": "what to look for, in English or German"},
                "doc_ids": {"type": "array", "items": {"type": "string", "enum": v["doc_id"]},
                            "description": "optional: only search inside these documents. "
                                           "Documents: " + document_guide()},
                "language": {"type": "string", "enum": v["language"]},
            }},
        }},
    ]


class SourceRegistry:
    """Gives every chunk / catalogue row a stable number the LLM can cite, e.g. [3]."""

    def __init__(self):
        self.sources: list[dict] = []
        self._by_key: dict[str, int] = {}

    def add(self, key: str, source: dict) -> int:
        if key not in self._by_key:
            self.sources.append({"n": len(self.sources) + 1, **source})
            self._by_key[key] = len(self.sources)
        return self._by_key[key]


def run_tool(name: str, args: dict, registry: SourceRegistry) -> tuple[dict, str, list[int]]:
    """Run one tool. Returns (compact result for the LLM, summary for the trace, source numbers)."""
    if name == "query_documents":
        result = query_documents(**args)
        if "error" in result:
            return result, f"error: {result['error']}", []
        rows, numbers = [], []
        query = ", ".join(f"{k}={v}" for k, v in args.items()) or "no filters"
        for d in result["documents"]:
            relations = "".join(f" {label}: {d[key]}." for key, label in (
                ("amends", "Amends"), ("amended_by", "Amended by"), ("adopts", "Adopts")) if d[key])
            # The full catalogue row + the query that produced it, so the reflection step can
            # verify claims like "these are the only AML documents after 2022" or "amends X".
            n = registry.add(f"doc:{d['doc_id']}", {
                "type": "catalogue", "citation": f"Catalogue entry: {d['reference']}",
                "doc_id": d["doc_id"], "reference": d["reference"], "url": d["url"], "language": d["language"],
                "text": (f"{d['reference']}: {d['title']} (issuer {d['issuer']}, language {d['language']}, "
                         f"date {d['date']}, topics: {d['topics']}).{relations} "
                         f"[Catalogue query ({query}) returned {result['count']} document(s) in total.]"),
            })
            numbers.append(n)
            rows.append({"source": n} | {k: d[k] for k in (
                "doc_id", "reference", "title", "issuer", "language", "date", "topics",
                "amends", "amended_by", "adopts") if d[k]})
        return {"count": len(rows), "documents": rows}, f"{len(rows)} documents", numbers

    if name == "search_documents":
        result = search_documents(k=SEARCH_K, **{k: v for k, v in args.items() if k != "k"})
        if "error" in result:
            return result, f"error: {result['error']}", []
        hits, numbers = [], []
        for r in result["results"]:
            n = registry.add(f"chunk:{r['chunk_id']}", {
                "type": "passage", "citation": r["citation"], "doc_id": r["doc_id"],
                "reference": r["reference"], "language": r["language"], "score": r["score"],
                "text": r["text"],
            })
            numbers.append(n)
            hits.append({"source": n, "citation": r["citation"], "language": r["language"],
                         "text": r["text"][:TEXT_FOR_LLM]})
        return {"count": len(hits), "passages": hits}, f"{len(hits)} passages", numbers

    return {"error": f"Unknown tool {name!r}."}, "error: unknown tool", []


def _assistant_turn(message: dict) -> dict:
    """Keep only what the next call needs (drops the model's hidden reasoning to save tokens)."""
    turn = {"role": "assistant", "content": message.get("content") or ""}
    if message.get("tool_calls"):
        turn["tool_calls"] = message["tool_calls"]
    return turn


def normalise_citations(text: str) -> str:
    """Bring citations into one format, [n], whatever style the model used:
    '【3†L1-L7】' / '【3】' (a style gpt-oss learned in training) -> '[3]'
    '[1, 4]' or '[1,4]'                                         -> '[1][4]'"""
        # the model sometimes writes narrow/no-break spaces and non-breaking hyphens,
    # which render badly in browsers: replace them with normal characters
    text = text.replace("\u202f", " ").replace("\u00a0", " ").replace("\u2011", "-")
    text = re.sub(r"【\s*(\d+)[^】]*】", r"[\1]", text)
    text = re.sub(r"\[(\d+)†[^\]]*\]", r"[\1]", text)
    return re.sub(r"\[(\d+(?:\s*,\s*\d+)+)\]",
                  lambda m: "".join(f"[{n.strip()}]" for n in m.group(1).split(",")), text)


GERMAN_WORDS = {"der", "die", "das", "und", "ist", "sind", "nicht", "ein", "eine", "welche", "welcher",
                "wann", "wie", "was", "gilt", "gelten", "für", "bei", "mit", "zu", "den", "dem", "des",
                "im", "auf", "nach", "oder", "muss", "müssen", "kann", "wird", "werden"}


def question_language(question: str) -> str:
    """'German' or 'English'. Two or more German function words -> German.
    German terms inside an English question (e.g. 'MaRisk', 'Marktfolge') don't count."""
    words = set(re.findall(r"[a-zäöüß]+", question.lower()))
    return "German" if len(words & GERMAN_WORDS) >= 2 else "English"

def answer_question(question: str, llm: GroqClient | None = None) -> dict:
    """Run the agent loop. Returns the answer, the numbered sources, and the trace."""
    llm = llm or GroqClient()
    registry = SourceRegistry()
    trace: list[dict] = []
    reminder = f"(Write the whole answer in {question_language(question)}.)"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(today=time.strftime("%Y-%m-%d"))},
        {"role": "user", "content": f"{question}\n\n{reminder}"},
    ]
    tools = tool_schemas()

    for _ in range(MAX_TOOL_ROUNDS):
        message = llm.chat(messages, tools=tools)
        messages.append(_assistant_turn(message))
        if not message.get("tool_calls"):
            break
        for call in message["tool_calls"]:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            result, summary, numbers = run_tool(name, args, registry)
            trace.append({"step": len(trace) + 1, "tool": name, "args": args,
                          "result": summary, "sources": numbers})
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(result, ensure_ascii=False) + "\n\n" + reminder})
    else:
        # step limit reached: ask for a final answer without allowing more tool calls
        messages.append({"role": "user", "content": "Tool limit reached. Answer now using only the sources above."})
        message = llm.chat(messages, tools=tools, tool_choice="none")
        messages.append(_assistant_turn(message))

    return {
        "question": question,
        "answer": normalise_citations(message.get("content") or ""),
        "sources": registry.sources,
        "trace": trace,
        "tokens_used": llm.tokens_used,
        "model": llm.model,
    }


def print_result(result: dict) -> None:
    print("\n=== TRACE")
    for t in result["trace"]:
        print(f"   {t['step']}. {t['tool']}({t['args']}) -> {t['result']}  sources {t['sources']}")
    print("\n=== ANSWER\n" + result["answer"])
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", result["answer"])}
    print("\n=== SOURCES CITED")
    for s in result["sources"]:
        if s["n"] in cited:
            print(f"   [{s['n']}] {s['citation']}")
    print(f"\n(tokens used: {result['tokens_used']}, model: {result['model']})")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Which AML documents were issued after 2022?"
    print_result(answer_question(q))