"""
Ingestion pipeline — built one step at a time.

Step 1: Load each PDF listed in data/documents.csv, page by page, as LangChain
        Documents, with the document's metadata + page number attached.
Step 2: Clean the pages:
        2a. keep only the pages that contain the actual rules (drop EBA background
            and consultation-feedback sections)
        2b. remove noise inside pages: repeated headers/footers, page numbers,
            table-of-contents lines, words split by hyphens, extra whitespace
Step 3: Chunk each document at its own section numbers (EBA "9.19.", MaRisk
        "BTO 1.1 Tz. 3", AuA "5.2.2.2"), then fix chunk sizes.
Step 4: Embed every chunk with Voyage AI's multilingual model voyage-4 (one vector of
        1024 numbers per chunk), cache the vectors.
Step 5: Store what the live app needs: a FAISS index of the vectors, the chunks
        (text + metadata, same order), and the document catalogue as a SQLite database.
        Then load everything back from disk and run a test search + a test SQL query.

Run from the project folder:   python scripts/ingest.py
"""
import bisect
import csv
import hashlib
import json
import re
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

import faiss
import numpy as np
import pymupdf
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# the embedding client lives in app/embeddings.py, shared with the live app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.embeddings import (
    EMBED_MODEL,
    MAX_TOKENS_PER_REQUEST,
    VoyageEmbeddings,
    estimate_tokens,
    normalise,
)

DATA_DIR = Path("data")
PDF_DIR = DATA_DIR / "raw_pdf"
CATALOGUE = DATA_DIR / "documents.csv"
CLEANED_DIR = DATA_DIR / "cleaned"      # cleaned text saved here so you can inspect it
CHUNKS_PREVIEW = DATA_DIR / "chunks_preview.txt"
INDEX_DIR = DATA_DIR / "index"          # vectors, FAISS index and chunks are saved here
DB_PATH = DATA_DIR / "documents.db"     # the document catalogue as a SQLite database

# Document-level fields copied from the CSV onto every page (and later every chunk).
# 'amends', 'adopts' and 'url' stay only in the database: they describe the whole
# document, not a piece of text.
DOC_FIELDS = ["doc_id", "language", "issuer", "doc_type", "reference", "title", "date", "topic"]

# Step 2a: page ranges (inclusive) that contain the actual guidelines.
# Found by inspecting each PDF's bookmarks / section headings.
# Documents not listed here are kept in full.
PAGE_RANGES = {
    "eba_gl_2019_02": (17, 55),
    "eba_gl_2020_06": (12, 76),
    "eba_gl_2021_02": (16, 137),
    "eba_gl_2022_15": (7, 23),
    "eba_gl_2024_01": (11, 32),
}


# ============================================================ Step 1: load
def load_catalogue() -> list[dict]:
    """Read documents.csv into a list of dicts (one per document), trimming stray spaces."""
    with open(CATALOGUE, encoding="utf-8") as f:
        return [
            {key.strip(): (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(f)
        ]


def load_pdf_pages(doc: dict) -> list[Document]:
    """Open one PDF and return one LangChain Document per page."""
    pdf = pymupdf.open(PDF_DIR / doc["filename"])
    pages = []
    for page_number, page in enumerate(pdf, start=1):
        pages.append(Document(
            page_content=page.get_text(),
            metadata={
                **{field: doc[field] for field in DOC_FIELDS},
                "source": doc["filename"],
                "page": page_number,
            },
        ))
    return pages


# ============================================================ Step 2: clean
def select_pages(pages: list[Document], doc_id: str) -> list[Document]:
    """2a. Keep only the page range that contains the actual rules."""
    if doc_id not in PAGE_RANGES:
        return pages
    first, last = PAGE_RANGES[doc_id]
    return [p for p in pages if first <= p.metadata["page"] <= last]


def _normalise(line: str) -> str:
    """Make header/footer lines comparable across pages: '152' and '153' both become '#'."""
    return re.sub(r"\d+", "#", line.strip().lower())


def find_repeated_lines(pages: list[Document], edge: int = 4, share: float = 0.5) -> set[str]:
    """Lines that appear at the top or bottom of at least half the pages = headers/footers.
    Only the first/last few lines of each page are considered, so real body text that
    happens to repeat (e.g. a heading used twice) is never removed."""
    if len(pages) < 3:
        return set()
    counts = Counter()
    for p in pages:
        lines = [ln for ln in p.page_content.splitlines() if ln.strip()]
        counts.update({_normalise(ln) for ln in lines[:edge] + lines[-edge:]})
    return {line for line, n in counts.items() if n >= share * len(pages) and line not in ("", "#")}


TOC_LINE = re.compile(r"\.{4,}\s*\d+\s*$")   # "3. Guidelines ........ 12"
GERMAN_CONJUNCTIONS = ("und", "oder", "bzw", "sowie", "als", "noch")  # "Auslegungs- und ..."


def fix_hyphenation(text: str, language: str) -> str:
    r"""Re-join words split across lines.
    English: keep the hyphen ('risk-\nbased' -> 'risk-based'), since English line-end
             hyphens in these PDFs are mostly real compound words.
    German:  'Geldwäsche-\ngesetz' -> 'Geldwäschegesetz', but keep
             'Auslegungs-\nund' -> 'Auslegungs- und' (hyphen means 'shared word ending')."""
    if language == "de":
        def join(m):
            nxt = m.group(2)
            if nxt.lower().startswith(GERMAN_CONJUNCTIONS) or nxt[:1].isupper():
                return f"{m.group(1)}- {nxt}"
            return m.group(1) + nxt
        return re.sub(r"(\w)-\n(\w+)", join, text)
    return re.sub(r"(\w)-\n(\w)", r"\1-\2", text)


def detect_page_number_offset(pages: list[Document], edge: int = 2) -> int | None:
    """Printed page numbers often differ from the PDF page index by a fixed amount
    (e.g. the cover isn't numbered). Find that offset from lone numbers at the
    top/bottom of pages. Only numbers matching it are treated as page numbers later,
    so a MaRisk 'Tz.' number that happens to start a page is NOT deleted."""
    offsets = Counter()
    for p in pages:
        lines = [ln.strip() for ln in p.page_content.splitlines() if ln.strip()]
        for ln in lines[:edge] + lines[-edge:]:
            if re.fullmatch(r"\d{1,3}", ln):
                offsets[int(ln) - p.metadata["page"]] += 1
    if not offsets:
        return None
    offset, n = offsets.most_common(1)[0]
    return offset if n >= 0.3 * len(pages) else None


def clean_page(text: str, repeated: set[str], language: str,
               page: int, page_offset: int | None, edge: int = 2) -> str:
    """2b. Remove noise inside one page. Line breaks are KEPT on purpose:
    the chunking step needs them to see where numbered paragraphs start."""
    # first drop running headers/footers, so the page's real first/last lines become visible
    lines = [ln for ln in text.splitlines() if _normalise(ln) not in repeated]
    content_idx = [i for i, ln in enumerate(lines) if ln.strip()]
    edge_idx = set(content_idx[:edge] + content_idx[-edge:])

    kept = []
    for i, line in enumerate(lines):
        s = line.strip()
        is_page_number = (
            i in edge_idx and (
                (page_offset is not None and s.isdigit() and int(s) - page == page_offset)
                or re.fullmatch(r"(page|seite)\s*\d+(\s*(of|von|/)\s*\d+)?", s, re.IGNORECASE)
            )
        )
        if is_page_number or TOC_LINE.search(line):
            continue
        kept.append(re.sub(r"[ \t\xa0]+", " ", line).strip())
    text = "\n".join(kept)
    text = fix_hyphenation(text, language)
    text = re.sub(r"\n{3,}", "\n\n", text)   # at most one blank line in a row
    return text.strip()


def clean_document(pages: list[Document], doc_id: str) -> tuple[list[Document], set[str]]:
    """Run Step 2 on one document. Returns cleaned pages + the header/footer lines removed."""
    pages = select_pages(pages, doc_id)
    repeated = find_repeated_lines(pages)
    page_offset = detect_page_number_offset(pages)
    cleaned = []
    for p in pages:
        text = clean_page(p.page_content, repeated, p.metadata["language"],
                          p.metadata["page"], page_offset)
        if text:   # drop pages that are empty after cleaning
            cleaned.append(Document(page_content=text, metadata=p.metadata))
    return cleaned, repeated


# ============================================================ Step 3: chunk
# Which numbering style each document uses (found by inspecting the cleaned text).
CHUNK_STYLE = {
    "eba_gl_2019_02": "eba", "eba_gl_2020_06": "eba", "eba_gl_2021_02": "eba",
    "eba_gl_2022_15": "eba", "eba_gl_2024_01": "eba",
    "bafin_rs_06_2026": "marisk",
    "bafin_aua_gwg": "aua",
    "bafin_rs_14_2026": "plain",     # 2-page notice: no numbering, size-split only
}

# EBA paragraph number, in either layout found in the PDFs:
#   "9.19. Where the conditions ..."   (number + text on one line)
#   "100."  then the text on the next line  (number alone on its line)
EBA_PARA = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){0,2})\.(?:\s+\S|$)")
# AuA heading:    "5.2.2.2 Fiktive wirtschaftlich Berechtigte, ..."
AUA_HEADING = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,4})\.?\s+[A-ZÄÖÜ§]")
# MaRisk module:  "BTO 1 Kreditgeschäft", "AT 4.3.2 Risikosteuerungs- und -controllingprozesse",
#                 and modules without a number: "BTO Anforderungen an die Aufbau- und Ablauforganisation"
#   (must not be a wrapped cross-reference like "BTO 1.2 Tz. 1 und ...")
MARISK_MODULE = re.compile(r"^((?:AT|BT|BTO|BTR)(?:\s?\d+(?:\.\d+)*)?)\s+(?!Tz)[A-ZÄÖÜ][^()]{2,100}$")
# MaRisk point:   a line that is only a number = the 'Tz.' (Textziffer) in the margin
MARISK_TZ = re.compile(r"^(\d{1,2})$")
SIMPLE_PATTERNS = {"aua": AUA_HEADING}   # one pattern = one section start


def continues_sequence(prev: tuple | None, cur: tuple) -> bool:
    """True if paragraph number `cur` plausibly comes right after `prev`.
    Real EBA paragraph numbers run in order through the document (99 -> 100 -> 101,
    9.19 -> 9.20 -> 10.1), while numbered LISTS inside a paragraph restart at 1.
    Small gaps (up to 3) are tolerated in case a number was not extracted."""
    if prev is None:
        return False                                   # the start is found by re-syncing
    if len(cur) == len(prev) and cur[:-1] == prev[:-1]:
        return 1 <= cur[-1] - prev[-1] <= 3            # next sibling: 9.19 -> 9.20
    if len(cur) == len(prev) + 1 and cur[:-1] == prev:
        return cur[-1] <= 2                            # first child: 9 -> 9.1
    if 2 <= len(cur) < len(prev) and cur[:-1] == prev[:len(cur) - 1]:
        return 1 <= cur[-1] - prev[len(cur) - 1] <= 3  # back up a level: 9.19.2 -> 9.20
    if len(cur) == len(prev) >= 2:
        return 1 <= cur[0] - prev[0] <= 2 and all(x <= 2 for x in cur[1:])  # next major: 9.25 -> 10.1
    return False   # e.g. 1.2 -> 2. : a dotted paragraph is never followed by a single-level one


def eba_sections(text: str) -> list[tuple[int, str]]:
    """EBA: keep only the numbered lines that belong to the paragraph sequence.

    A number is accepted if
      (a) it continues the sequence from the last accepted paragraph, or
      (b) it jumps FORWARD and the next number confirms it (re-sync), e.g. after a
          paragraph number was missed, or at the first page we kept (which may start at 9.18).
      (c) it starts a DEEPER numbering scheme that the next number confirms, e.g. the
          intro chapters run 1. .. 12. and the guidelines then restart at 1.1., 1.2.
    A numbered list inside a paragraph (1., 2., 3.) jumps BACKWARDS to the same or a
    shallower depth, so it never qualifies."""
    candidates, pos = [], 0
    for line in text.splitlines(keepends=True):
        if m := EBA_PARA.match(line.strip()):
            candidates.append((pos, m.group(1), tuple(int(x) for x in m.group(1).split("."))))
        pos += len(line)

    sections, last = [], None
    for i, (position, label, number) in enumerate(candidates):
        following = [n for _, _, n in candidates[i + 1:i + 3]]
        confirmed = any(continues_sequence(number, n) for n in following)
        forward = last is None or (number > last and len(number) >= len(last))
        deeper_restart = last is not None and len(number) > len(last) and number[-1] <= 2
        resync = confirmed and (forward or deeper_restart)
        if continues_sequence(last, number) or resync:
            sections.append((position, label))
            last = number
    return sections


MAX_CHARS = 1500    # longer sections are split further
MIN_CHARS = 200     # a heading shorter than this is merged into the next piece
TINY_CHARS = 60     # fragments shorter than this are attached to the previous piece
splitter = RecursiveCharacterTextSplitter(
    chunk_size=MAX_CHARS, chunk_overlap=150, separators=["\n\n", "\n", ". ", " ", ""]
)


def join_pages(pages: list[Document]) -> tuple[str, list[int], list[int]]:
    """Join a document's pages into one text, remembering where each page starts,
    so a rule that continues onto the next page is not cut at the page border."""
    text, starts, numbers = "", [], []
    for p in pages:
        starts.append(len(text))
        numbers.append(p.metadata["page"])
        text += p.page_content + "\n"
    return text, starts, numbers


def find_sections(text: str, style: str) -> list[tuple[int, str]]:
    """Return (character position, section label) for every section start."""
    if style == "eba":
        return eba_sections(text)
    sections, module, pos = [], None, 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        label = None
        if style in SIMPLE_PATTERNS and (m := SIMPLE_PATTERNS[style].match(stripped)):
            label = m.group(1)
        elif style == "marisk":
            if m := MARISK_MODULE.match(stripped):
                module = " ".join(m.group(1).split())          # 'BTO1.1' -> 'BTO 1.1'
                module = re.sub(r"^([A-Z]+)(\d)", r"\1 \2", module)
                label = module
            elif module and (m := MARISK_TZ.match(stripped)):
                label = f"{module} Tz. {m.group(1)}"
        if label:
            sections.append((pos, label))
        pos += len(line)
    return sections


def merged_label(first: str, second: str) -> str:
    """Label for a heading-like piece merged into the next piece.
    'intro' + '9.20'                 -> '9.20'
    'BTO 1.1' + 'BTO 1.1 Tz. 1'      -> 'BTO 1.1 Tz. 1'   (heading of its own first point)
    '1.1' + '1.2'                    -> '1.1–1.2'          (two real paragraphs: cite both)"""
    if first == "intro" or second.startswith(first + " ") or first == second:
        return second
    return f"{first}–{second}"


def chunk_document(pages: list[Document]) -> list[Document]:
    """Step 3 for one document: cut at section numbers, then fix sizes."""
    if not pages:
        return []
    meta = {k: v for k, v in pages[0].metadata.items() if k != "page"}
    style = CHUNK_STYLE.get(meta["doc_id"], "plain")
    text, page_starts, page_numbers = join_pages(pages)

    def page_at(position: int) -> int:
        return page_numbers[bisect.bisect_right(page_starts, position) - 1]

    # 1. cut at section starts (text before the first section = 'intro')
    cuts = find_sections(text, style)
    if not cuts or cuts[0][0] > 0:
        cuts.insert(0, (0, "intro"))
    pieces = []
    for (start, label), (end, _) in zip(cuts, cuts[1:] + [(len(text), None)]):
        body = text[start:end].strip()
        if body:
            pieces.append({"text": body, "section": label, "page": page_at(start)})

    # 2. a short piece that looks like a HEADING (no sentence ending, e.g. "Customers that
    #    offer services related to virtual currencies") is merged into the next piece, so
    #    the heading stays with its content. Short REAL rules (ending in . ; : etc.) keep
    #    their own chunk and label; only tiny fragments are attached to the previous piece.
    def is_heading(p):
        return len(p["text"]) < MIN_CHARS and not re.search(r"[.;:!?)]$", p["text"])

    merged, carry = [], None
    for piece in pieces:
        if carry:
            piece = {**piece, "text": carry["text"] + "\n" + piece["text"], "page": carry["page"],
                     "section": merged_label(carry["section"], piece["section"])}
            carry = None
        if is_heading(piece):
            carry = piece
        elif len(piece["text"]) < TINY_CHARS and merged:
            merged[-1]["text"] += "\n" + piece["text"]
        else:
            merged.append(piece)
    if carry:   # a heading left over at the very end
        if merged:
            merged[-1]["text"] += "\n" + carry["text"]
        else:
            merged.append(carry)

    # 3. split too-long pieces; every part keeps the same section label
    chunks = []
    for piece in merged:
        parts = splitter.split_text(piece["text"]) if len(piece["text"]) > MAX_CHARS else [piece["text"]]
        for i, part in enumerate(parts, start=1):
            chunks.append(Document(
                page_content=part,
                metadata={
                    **meta,
                    "section": piece["section"],
                    "part": i if len(parts) > 1 else None,
                    "page": piece["page"],
                },
            ))
    # give every chunk a unique id, e.g. 'eba_gl_2021_02::0042'
    for n, c in enumerate(chunks):
        c.metadata["chunk_id"] = f"{meta['doc_id']}::{n:04d}"
    return chunks


# ============================================================ Step 4: embed
# (VoyageEmbeddings, estimate_tokens and normalise come from app/embeddings.py)


def text_for_embedding(chunk: Document) -> str:
    """The text that is turned into a vector: a short context header + the chunk.
    The header lets a question that names a document ('loan origination guidelines')
    match that document's chunks. The stored chunk text itself stays unchanged."""
    m = chunk.metadata
    return f"{m['reference']} – {m['title']} – {m['section']}\n{chunk.page_content}"


def make_batches(texts: list[str], max_tokens: int = MAX_TOKENS_PER_REQUEST) -> list[list[int]]:
    """Group text positions into batches of at most `max_tokens` (estimated) each."""
    batches, current, size = [], [], 0
    for i, t in enumerate(texts):
        n = estimate_tokens(t)
        if current and size + n > max_tokens:
            batches.append(current)
            current, size = [], 0
        current.append(i)
        size += n
    if current:
        batches.append(current)
    return batches


def embed_chunks(chunks: list[Document], embedder: Embeddings) -> np.ndarray:
    """Return one normalised vector per chunk (rows in the same order as `chunks`).

    Every vector is cached on disk by a fingerprint of (model + text) right after its
    batch is embedded. So an interrupted run continues where it stopped, and after a
    change to cleaning/chunking only new or changed chunks are sent to the API."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = INDEX_DIR / "embedding_cache.json"
    cache: dict[str, list[float]] = json.loads(cache_file.read_text()) if cache_file.exists() else {}

    texts = [text_for_embedding(c) for c in chunks]
    keys = [hashlib.sha256(f"{EMBED_MODEL}\n{t}".encode()).hexdigest() for t in texts]
    missing = [i for i, k in enumerate(keys) if k not in cache]
    print(f"{len(chunks) - len(missing)} chunks already embedded (cache), {len(missing)} to embed with {EMBED_MODEL}")

    batches = make_batches([texts[i] for i in missing])
    for b, batch in enumerate(batches, start=1):
        positions = [missing[j] for j in batch]
        vectors = embedder.embed_documents([texts[i] for i in positions])
        for i, v in zip(positions, vectors, strict=True):
            cache[keys[i]] = v
        cache_file.write_text(json.dumps(cache))   # save after every batch
        print(f"   batch {b}/{len(batches)} done ({len(positions)} chunks)")

    return normalise(np.array([cache[k] for k in keys], dtype="float32"))


# ============================================================ Step 5: store
def build_faiss_index(vectors: np.ndarray) -> faiss.Index:
    """Exact search index. Vectors are normalised, so inner product = cosine similarity.
    'Flat' compares the question with every vector: exact, and instant for ~1,500 vectors
    (approximate index types only pay off with millions of vectors)."""
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index


def save_store(chunks: list[Document], vectors: np.ndarray) -> None:
    """Write the three files the live app loads: index.faiss, chunks.json, index_info.json.
    Row i of the FAISS index belongs to chunks.json entry i."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(build_faiss_index(vectors), str(INDEX_DIR / "index.faiss"))
    records = [{"text": c.page_content, "metadata": c.metadata} for c in chunks]
    (INDEX_DIR / "chunks.json").write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    info = {"embedding_model": EMBED_MODEL, "dimensions": int(vectors.shape[1]),
            "chunks": len(chunks), "built": time.strftime("%Y-%m-%d %H:%M")}
    (INDEX_DIR / "index_info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")


def build_database(catalogue: list[dict], chunks: list[Document]) -> None:
    """Create data/documents.db from documents.csv (rebuilt from scratch every run).
      documents        one row per document (metadata from the CSV + number of chunks)
      document_topics  one row per (document, topic): MaRisk has three topics, so
                       'all outsourcing documents' is an exact query, not a text search"""
    chunk_counts = {}
    for c in chunks:
        chunk_counts[c.metadata["doc_id"]] = chunk_counts.get(c.metadata["doc_id"], 0) + 1

    DB_PATH.unlink(missing_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.executescript("""
            CREATE TABLE documents (
                doc_id     TEXT PRIMARY KEY,
                reference  TEXT NOT NULL,      -- e.g. 'EBA/GL/2021/02', 'Rundschreiben 06/2026 (BA)'
                title      TEXT NOT NULL,
                issuer     TEXT NOT NULL,      -- 'EBA' or 'BaFin'
                doc_type   TEXT NOT NULL,      -- guideline / circular / interpretation_guidance
                language   TEXT NOT NULL,      -- 'en' or 'de'
                date       TEXT NOT NULL,      -- ISO 'YYYY-MM-DD', so text comparison = date comparison
                status     TEXT NOT NULL,      -- e.g. 'active'
                amends     TEXT,               -- reference of the document this one amends
                adopts     TEXT,               -- reference of the EBA guideline this one adopts
                url        TEXT,
                filename   TEXT NOT NULL,
                chunks     INTEGER NOT NULL
            );
            CREATE TABLE document_topics (
                doc_id TEXT NOT NULL REFERENCES documents(doc_id),
                topic  TEXT NOT NULL,
                PRIMARY KEY (doc_id, topic)
            );
        """)
        for d in catalogue:
            db.execute(
                "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (d["doc_id"], d["reference"], d["title"], d["issuer"], d["doc_type"], d["language"],
                 d["date"], d["status"], d["amends"] or None, d["adopts"] or None, d["url"] or None,
                 d["filename"], chunk_counts.get(d["doc_id"], 0)),
            )
            for topic in filter(None, (t.strip() for t in d["topic"].split(";"))):
                db.execute("INSERT INTO document_topics VALUES (?, ?)", (d["doc_id"], topic))


def verify_store(embedder: Embeddings) -> None:
    """Load everything back FROM DISK (exactly as the app will) and test it."""
    index = faiss.read_index(str(INDEX_DIR / "index.faiss"))
    records = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
    info = json.loads((INDEX_DIR / "index_info.json").read_text(encoding="utf-8"))
    assert index.ntotal == len(records) == info["chunks"], "index and chunks.json are out of sync!"
    print(f"Loaded from disk: {index.ntotal} vectors, {len(records)} chunks, model {info['embedding_model']}")

    question = "Separation of front office and back office functions in lending"
    q = normalise(np.array([embedder.embed_query(question)], dtype="float32"))
    scores, positions = index.search(q, 3)
    print(f"\nFAISS test search: {question}")
    for score, pos in zip(scores[0], positions[0], strict=True):
        m = records[pos]["metadata"]
        snippet = " ".join(records[pos]["text"].split())[:80]
        print(f"   {score:.2f}  {m['reference']:<28} {m['section']:<16} p.{m['page']:<4} {snippet}")

    print("\nSQL test query: AML documents issued after 2022 (both languages)")
    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute("""
            SELECT d.reference, d.language, d.date, d.chunks
            FROM documents d JOIN document_topics t ON t.doc_id = d.doc_id
            WHERE t.topic = 'aml' AND d.date > '2022-12-31'
            ORDER BY d.date
        """).fetchall()
    for reference, language, date, n in rows:
        print(f"   {date}  {language}  {reference:<28} ({n} chunks)")


# ============================================================ run
if __name__ == "__main__":
    catalogue = load_catalogue()
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    all_chunks: list[Document] = []
    preview = []

    print(f"{'doc_id':<18} {'pages':>6} {'chunks':>7} {'avg len':>8} {'min':>5} {'max':>6}  sections found")
    for doc in catalogue:
        raw = load_pdf_pages(doc)
        cleaned, repeated = clean_document(raw, doc["doc_id"])

        # Save the cleaned text so you can open it in VS Code and check it by eye
        with open(CLEANED_DIR / f"{doc['doc_id']}.txt", "w", encoding="utf-8") as f:
            f.writelines(f"\n\n===== page {p.metadata['page']} =====\n{p.page_content}" for p in cleaned)

        chunks = chunk_document(cleaned)
        all_chunks.extend(chunks)

        lengths = [len(c.page_content) for c in chunks] or [0]
        n_sections = len({c.metadata["section"] for c in chunks})
        print(f"{doc['doc_id']:<18} {len(cleaned):>6} {len(chunks):>7} {sum(lengths)//len(lengths):>8} "
              f"{min(lengths):>5} {max(lengths):>6}  {n_sections}")

        # first 6 chunks of each document go into the preview file
        for c in chunks[:6]:
            m = c.metadata
            preview.append(f"----- {m['chunk_id']} | {m['reference']} | section {m['section']}"
                           f"{' part ' + str(m['part']) if m['part'] else ''} | page {m['page']}\n"
                           f"{c.page_content[:500]}\n")

    PREVIEW_HEADER = "Preview: first chunks of each document\n\n"
    CHUNKS_PREVIEW.write_text(PREVIEW_HEADER + "\n".join(preview), encoding="utf-8")
    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Preview of the first chunks per document: {CHUNKS_PREVIEW}")

    # ---- Step 4: embed
    print()
    embedder = VoyageEmbeddings()
    vectors = embed_chunks(all_chunks, embedder)
    print(f"Vectors: {vectors.shape[0]} chunks x {vectors.shape[1]} numbers each")

    # ---- Step 5: store + verify
    print()
    save_store(all_chunks, vectors)
    build_database(catalogue, all_chunks)
    print(f"Saved: {INDEX_DIR / 'index.faiss'}, {INDEX_DIR / 'chunks.json'}, {DB_PATH}")
    verify_store(embedder)