"""Token-budget retrieval with source attribution."""

import json
import logging
from typing import Optional

logger = logging.getLogger("m-acs.rag.retriever")

MAX_CONTEXT_TOKENS = 2048
TOP_K = 15  # initial candidate pool


def retrieve(
    db_path: str,
    ollama_url: str,
    query: str,
    file_ids: Optional[list[int]] = None,
    max_tokens: int = 2048,
) -> list[dict]:
    """Search relevant chunks. Returns list sorted by relevance.

    Each item: {"file_name": str, "page_num": int, "content": str, "tokens": int, "score": float}
    """
    from rag.db import get_db
    from rag.embedder import embed_texts
    import sqlite_vec

    # 1. Embed query
    vecs = embed_texts([query], ollama_url)
    q_vec = vecs[0]

    # 2. Vector search
    db = get_db(db_path)

    if file_ids:
        # Get chunk IDs belonging to these files
        placeholders = ",".join("?" for _ in file_ids)
        rows = db.execute(
            f"SELECT id FROM chunks WHERE file_id IN ({placeholders})",
            file_ids,
        ).fetchall()
        chunk_ids = [r["id"] for r in rows]
    else:
        chunk_ids = None

    # Build vec0 query
    vec_json = json.dumps(q_vec)
    if chunk_ids:
        # Filter by chunk_id
        cid_placeholders = ",".join("?" for _ in chunk_ids)
        results = db.execute(
            f"""
            SELECT chunk_id, distance FROM vec_chunks
            WHERE chunk_id IN ({cid_placeholders})
            AND embedding MATCH ?
            ORDER BY distance
            LIMIT ?
            """,
            chunk_ids + [vec_json, TOP_K],
        ).fetchall()
    else:
        results = db.execute(
            """
            SELECT chunk_id, distance FROM vec_chunks
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
            """,
            (vec_json, TOP_K),
        ).fetchall()

    # 3. Fetch chunk content + file info
    candidates = []
    for r in results:
        chunk = db.execute("""
            SELECT c.id, c.content, c.page_num, c.tokens, c.file_id, f.name as file_name
            FROM chunks c
            JOIN files f ON f.id = c.file_id
            WHERE c.id = ?
        """, (r["chunk_id"],)).fetchone()
        if chunk:
            candidates.append({
                "file_name": chunk["file_name"],
                "page_num": chunk["page_num"],
                "content": chunk["content"],
                "tokens": chunk["tokens"],
                "score": r["distance"],
            })

    # 4. Apply token budget
    candidates.sort(key=lambda x: x["score"])
    selected = []
    total = 0
    for c in candidates:
        needed = c["tokens"] + 30  # overhead
        if total + needed > max_tokens:
            continue
        selected.append(c)
        total += needed

    db.close()
    return selected


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a prompt context block."""
    parts = []
    for i, c in enumerate(chunks):
        parts.append(
            f"[来源 {i + 1}] {c['file_name']} → 第{c['page_num']}页\n"
            f"{c['content']}\n"
        )
    return "\n---\n".join(parts)


def format_sources(chunks: list[dict]) -> list[dict]:
    """Format chunks as clean source citations for API response."""
    seen = set()
    sources = []
    for c in chunks:
        key = (c["file_name"], c["page_num"])
        if key not in seen:
            seen.add(key)
            snippet = c["content"][:300]
            sources.append({
                "file": c["file_name"],
                "page": c["page_num"],
                "snippet": snippet,
            })
    return sources
