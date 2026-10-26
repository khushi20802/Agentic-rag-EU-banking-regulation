"""Reflection (Step 8): an independent check of the answer against its cited sources.

The checker LLM does not answer the question. It only judges, claim by claim, whether the
cited passages support what the answer says. Unsupported claims are FLAGGED (not removed),
so the user sees the answer plus a warning, and we can measure faithfulness.
"""
import json
import re

from app.llm import GroqClient

MAX_CLAIMS = 10
SOURCE_CHARS = 1500          # the checker sees the full chunk (chunks are <= 1,500 characters)

CHECK_PROMPT = """You are a strict fact-checker for answers about banking regulation.
You get an ANSWER and the SOURCES it cites (numbered). Sources may be German while the answer
is English (or the other way round): judge the MEANING, not the wording.

Pick the {max_claims} most important factual claims in the answer (fewer if the answer is short).
For each claim decide:
- "supported": the cited source(s) clearly say this
- "partially_supported": the gist is there, but the answer adds details or is stronger/broader
  than the source (e.g. "must" where the source says "may")
- "unsupported": the cited source(s) do not say this, or the claim has no citation

Reply with JSON only, in exactly this shape:
{{"claims": [{{"claim": "<short paraphrase>", "cited": [<numbers>], "verdict": "supported|partially_supported|unsupported", "reason": "<one short sentence>"}}]}}"""


def cited_numbers(answer: str) -> list[int]:
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})


def _parse_json(text: str) -> dict | None:
    """Read the checker's JSON, even if it wrapped it in ```json fences or extra words."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data.get("claims"), list) else None


def reflect(result: dict, llm: GroqClient | None = None) -> dict:
    """Check result['answer'] against the sources it cites. Returns verdicts + flags + score."""
    answer, sources = result["answer"], {s["n"]: s for s in result["sources"]}
    numbers = cited_numbers(answer)

    # 1. cheap check in code: citations of sources that don't exist
    flags = [{"claim": f"Citation [{n}]", "cited": [n], "verdict": "unsupported",
              "reason": "This source number does not exist."} for n in numbers if n not in sources]
    valid = [n for n in numbers if n in sources]

    if not answer.strip() or not valid:
        # e.g. "the documents do not cover the EU AI Act": nothing to verify. This is shown as
        # a note, not as a false claim (an honest refusal is the CORRECT behaviour).
        flags.append({"claim": "Whole answer", "cited": [], "verdict": "no_sources",
                      "reason": "The answer cites no sources (for example because it says the "
                                "information is not available), so there is nothing to verify."})
        return {"checked": False, "claims": [], "flags": flags, "faithfulness": None}

    # 2. the checker LLM: answer + full text of the cited sources only
    evidence = "\n\n".join(f"[{n}] {sources[n]['citation']}\n{sources[n]['text'][:SOURCE_CHARS]}" for n in valid)
    messages = [
        {"role": "system", "content": CHECK_PROMPT.format(max_claims=MAX_CLAIMS)},
        {"role": "user", "content": f"ANSWER:\n{answer}\n\nSOURCES:\n{evidence}"},
    ]
    llm = llm or GroqClient()
    data = _parse_json(llm.chat(messages, temperature=0.0).get("content") or "")
    if data is None:
        return {"checked": False, "claims": [], "flags": flags, "faithfulness": None,
                "note": "Reflection unavailable: the checker's reply could not be read."}

    claims = []
    for c in data["claims"][:MAX_CLAIMS]:
        verdict = str(c.get("verdict", "")).strip().lower()
        if verdict not in ("supported", "partially_supported", "unsupported"):
            verdict = "unsupported"
        claims.append({"claim": str(c.get("claim", "")), "cited": c.get("cited") or [],
                       "verdict": verdict, "reason": str(c.get("reason", ""))})

    flags += [c for c in claims if c["verdict"] != "supported"]
    supported = sum(c["verdict"] == "supported" for c in claims)
    return {"checked": True, "claims": claims, "flags": flags,
            "faithfulness": round(supported / len(claims), 2) if claims else None}