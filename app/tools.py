"""The agent's two tools (Step 6).

    query_documents(...)  -> structured questions about the document CATALOGUE (SQLite):
                             which documents exist, their dates, topics, language, and
                             how they relate (one amends / adopts another)
    search_documents(...) -> questions about the CONTENT of the documents (FAISS):
                             finds the most relevant chunks, optionally only within given
                             documents (chaining) or one language

Both return plain dicts/lists (JSON-serialisable), because their output is passed back
to the LLM in Step 7. Invalid arguments return an {"error": ...} dict that lists the
allowed values, so the LLM can correct itself instead of the app crashing.

Try them by hand:   python -m app.tools
"""
import json
import sqlite3
from functools import cache, lru_cache
from pathlib import Path

import faiss
import numpy as np

from app.embeddings import EMBED_MODEL, VoyageEmbeddings, normalise

ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = ROOT / "data" / "index"
DB_PATH = ROOT / "data" / "documents.db"


# ============================================================ loading (once per process)
@cache
def load_store() -> tuple[faiss.Index, list[dict]]:
    """Load the FAISS index and the chunks once; later calls reuse them (functools.cache)."""
    info = json.loads((INDEX_DIR / "index_info.json").read_text(encoding="utf-8"))
    if info["embedding_model"] != EMBED_MODEL:
        raise RuntimeError(f"Index was built with {info['embedding_model']}, but the app uses "
                           f"{EMBED_MODEL}. Rebuild the index with scripts/ingest.py.")
    index = faiss.read_index(str(INDEX_DIR / "index.faiss"))
    records = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
    if index.ntotal != len(records):
        raise RuntimeError("index.faiss and chunks.json are out of sync - rebuild with scripts/ingest.py.")
    return index, records


@cache
def load_embedder() -> VoyageEmbeddings:
    return VoyageEmbeddings()


@lru_cache(maxsize=512)
def embed_query_cached(query: str) -> tuple[float, ...]:
    """Embed a question once and remember it. When the agent searches the SAME query in
    several documents (e.g. comparing EBA and BaFin), Voyage is called only once -
    important with the free tier's 3 requests per minute."""
    return tuple(load_embedder().embed_query(query))


def _db() -> sqlite3.Connection:
    # read-only connection: the tools can never change the database
    db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


@cache
def allowed_values() -> dict[str, list[str]]:
    """The values that actually exist in the catalogue (used to validate tool arguments
    and to tell the LLM what it may ask for)."""
    with _db() as db:
        return {
            "topic": [r[0] for r in db.execute("SELECT DISTINCT topic FROM document_topics ORDER BY 1")],
            "issuer": [r[0] for r in db.execute("SELECT DISTINCT issuer FROM documents ORDER BY 1")],
            "language": [r[0] for r in db.execute("SELECT DISTINCT language FROM documents ORDER BY 1")],
            "doc_type": [r[0] for r in db.execute("SELECT DISTINCT doc_type FROM documents ORDER BY 1")],
            "doc_id": [r[0] for r in db.execute("SELECT doc_id FROM documents ORDER BY 1")],
        }


def _invalid(name: str, value) -> dict:
    return {"error": f"Unknown {name} {value!r}.", f"allowed_{name}_values": allowed_values()[name]}


# ============================================================ tool 1: the catalogue (SQL)
def query_documents(topic: str | None = None, issuer: str | None = None, language: str | None = None,
                    doc_type: str | None = None, date_from: str | None = None, date_to: str | None = None,
                    reference: str | None = None) -> dict:
    """List documents in the catalogue matching ALL given filters (none = all documents).

    topic      e.g. 'aml', 'outsourcing', 'credit_risk'
    issuer     'EBA' or 'BaFin'
    language   'en' or 'de'
    doc_type   'guideline', 'circular', 'interpretation_guidance'
    date_from  'YYYY-MM-DD' (inclusive)     date_to  'YYYY-MM-DD' (inclusive)
    reference  part of a reference, e.g. '2021/02' or '14/2026'

    The SQL is fixed; arguments are only inserted as '?' parameters, never as SQL text.
    """
    for name, value in (("topic", topic), ("issuer", issuer), ("language", language), ("doc_type", doc_type)):
        if value is not None and value not in allowed_values()[name]:
            return _invalid(name, value)
    for name, value in (("date_from", date_from), ("date_to", date_to)):
        if value is not None and not (len(value) == 10 and value[4] == "-" and value[7] == "-"):
            return {"error": f"{name} must look like 'YYYY-MM-DD', got {value!r}."}

    conditions, params = [], []
    if topic:
        conditions.append("d.doc_id IN (SELECT doc_id FROM document_topics WHERE topic = ?)")
        params.append(topic)
    for column, value in (("issuer", issuer), ("language", language), ("doc_type", doc_type)):
        if value:
            conditions.append(f"d.{column} = ?")     # column names are fixed above, never from input
            params.append(value)
    if date_from:
        conditions.append("d.date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("d.date <= ?")
        params.append(date_to)
    if reference:
        conditions.append("d.reference LIKE ?")
        params.append(f"%{reference}%")

    sql = """
        SELECT d.doc_id, d.reference, d.title, d.issuer, d.doc_type, d.language, d.date,
               d.status, d.amends, d.adopts, d.url, d.chunks,
               (SELECT group_concat(topic, ', ') FROM document_topics t WHERE t.doc_id = d.doc_id) AS topics,
               (SELECT group_concat(a.reference, ', ') FROM documents a WHERE a.amends = d.reference) AS amended_by
        FROM documents d
    """ + (" WHERE " + " AND ".join(conditions) if conditions else "") + " ORDER BY d.date"

    with _db() as db:
        rows = [dict(r) for r in db.execute(sql, params)]
    return {"count": len(rows), "documents": rows}


# ============================================================ tool 2: the content (FAISS)
LANGUAGE_MARGIN = 0.15   # balanced search: other-language results must score within this of the best


def search_documents(query: str, doc_ids: list[str] | None = None, language: str | None = None,
                     k: int = 5) -> dict:
    """Find the k chunks whose meaning is closest to `query` (works across languages).

    doc_ids   only search inside these documents (e.g. the result of query_documents)
    language  only return chunks in this language ('en' or 'de')

    Language-balanced: without a language filter, results come from BOTH languages when
    both have relevant passages. Multilingual embeddings score same-language text slightly
    higher, so a German question would otherwise mostly find German passages and miss an
    equally relevant English guideline (and vice versa). Each language gets up to half of
    the k slots, if its passages score within LANGUAGE_MARGIN of the best passage.
    """
    if not query or not query.strip():
        return {"error": "query must not be empty."}
    if doc_ids:
        unknown = [d for d in doc_ids if d not in allowed_values()["doc_id"]]
        if unknown:
            return _invalid("doc_id", unknown)
    if language is not None and language not in allowed_values()["language"]:
        return _invalid("language", language)
    k = max(1, min(int(k), 10))

    index, records = load_store()
    q = normalise(np.array([embed_query_cached(query.strip())], dtype="float32"))
    # Score ALL chunks (exact and only milliseconds for ~1,500 vectors), then filter.
    # With millions of vectors you'd use a vector DB with built-in metadata filters.
    scores, positions = index.search(q, index.ntotal)

    candidates = [(float(s), int(p)) for s, p in zip(scores[0], positions[0], strict=True)
                  if (not doc_ids or records[p]["metadata"]["doc_id"] in doc_ids)
                  and (not language or records[p]["metadata"]["language"] == language)]
    if not candidates:
        return {"count": 0, "results": []}

    languages = {records[p]["metadata"]["language"] for _, p in candidates}
    if language or len(languages) == 1:
        chosen = candidates[:k]
    else:
        best = candidates[0][0]
        quota = (k + 1) // 2
        chosen = []
        for lang in sorted(languages):
            same = [c for c in candidates if records[c[1]]["metadata"]["language"] == lang]
            chosen += [c for c in same[:quota] if c[0] >= best - LANGUAGE_MARGIN]
        chosen += [c for c in candidates if c not in chosen][:max(0, k - len(chosen))]
        chosen = sorted(chosen, reverse=True)[:k]

    return {"count": len(chosen), "results": [_result(records[p], score) for score, p in chosen]}


def _result(record: dict, score: float) -> dict:
    m = record["metadata"]
    section = m["section"] + (f" (part {m['part']})" if m.get("part") else "")
    label = f"para {section}" if m["issuer"] == "EBA" else section     # EBA numbers paragraphs
    return {
        "chunk_id": m["chunk_id"],
        "score": round(score, 3),
        "citation": f"{m['reference']}, {label}, p.{m['page']}",
        "doc_id": m["doc_id"],
        "reference": m["reference"],
        "title": m["title"],
        "language": m["language"],
        "date": m["date"],
        "section": section,
        "page": m["page"],
        "text": record["text"],
    }


# ============================================================ manual test
if __name__ == "__main__":
    def show_docs(title, result):
        print(f"\n=== {title}")
        if "error" in result:
            print("   ERROR:", result)
            return
        for d in result["documents"]:
            extra = "".join(f" | {key}: {d[key]}" for key in ("amends", "adopts", "amended_by") if d[key])
            print(f"   {d['date']}  {d['language']}  {d['reference']:<28} topics: {d['topics']}{extra}")

    def show_hits(title, result):
        print(f"\n=== {title}")
        if "error" in result:
            print("   ERROR:", result)
            return
        for r in result["results"]:
            print(f"   {r['score']:.2f}  {r['citation']:<45} {' '.join(r['text'].split())[:70]}")

    print("Allowed values:", allowed_values())

    show_docs("1. All documents", query_documents())
    show_docs("2. AML documents from 2023 onwards", query_documents(topic="aml", date_from="2023-01-01"))
    show_docs("3. What does Rundschreiben 14/2026 adopt?", query_documents(reference="14/2026"))
    show_docs("4. Invalid topic (the LLM would get this error back)", query_documents(topic="money laundering"))

    # chained: catalogue first, then search only inside those documents
    aml_recent = [d["doc_id"] for d in query_documents(topic="aml", date_from="2023-01-01")["documents"]]
    show_hits(f"5. CHAINED - search only in {aml_recent}",
              search_documents("enhanced due diligence for high-risk customers", doc_ids=aml_recent, k=4))
    show_hits("6. English question, German results only",
              search_documents("outsourcing of critical functions", language="de", k=3))