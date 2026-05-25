"""Store and search document chunks + vectors in sqlite-vec."""

import hashlib
import json
import logging
import os
from typing import Optional

from rag.db import get_db
from rag.parser import extract, clean_page_text
from rag.chunker import chunk_text
from rag.embedder import embed_texts

logger = logging.getLogger("m-acs.rag.store")


def ingest_file(path: str, db_path: str, ollama_url: str, filename: str = "") -> dict:
    """Full ingestion pipeline: parse → chunk → embed → store.

    Returns dict with file_id and status.
    """
    db = get_db(db_path)
    if not filename:
        filename = os.path.basename(path)

    # 1. Parse PDF
    doc = extract(path)
    cleaned_pages = [clean_page_text(p) for p in doc["text_by_page"]]

    # 2. Chunk
    chunks = chunk_text(cleaned_pages)

    if not chunks:
        return {"file_id": None, "status": "failed", "error": "no text extracted"}

    # 3. Compute hash for dedup
    with open(path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    # 4. Check duplicate
    existing = db.execute("SELECT id FROM files WHERE sha256 = ?", (sha256,)).fetchone()
    if existing:
        db.close()
        return {"file_id": existing["id"], "status": "duplicate"}

    # 5. Insert file record
    cursor = db.execute(
        "INSERT INTO files (name, pages, size_bytes, sha256, status) VALUES (?, ?, ?, ?, 'processing')",
        (filename, doc["pages"], os.path.getsize(path), sha256),
    )
    file_id = cursor.lastrowid
    db.commit()

    # 6. Insert chunks
    chunk_texts = []
    for c in chunks:
        db.execute(
            "INSERT INTO chunks (file_id, content, page_num, chunk_index, tokens) VALUES (?, ?, ?, ?, ?)",
            (file_id, c["content"], c["page_num"], c["chunk_index"], c["tokens"]),
        )
        chunk_texts.append(c["content"])
    db.commit()

    # 7. Get chunk IDs
    chunk_rows = db.execute(
        "SELECT id FROM chunks WHERE file_id = ? ORDER BY chunk_index",
        (file_id,),
    ).fetchall()
    chunk_ids = [r["id"] for r in chunk_rows]

    # 8. Embed
    try:
        vectors = embed_texts(chunk_texts, ollama_url)
    except Exception as e:
        logger.warning("embedding failed, marking file as failed: %s", e)
        db.execute("UPDATE files SET status = ? WHERE id = ?", ("failed", file_id))
        db.commit()
        db.close()
        return {"file_id": file_id, "status": "failed", "error": str(e)}

    # 9. Insert vectors
    for cid, vec in zip(chunk_ids, vectors):
        vec_sql = f"INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)"
        db.execute(vec_sql, (cid, json.dumps(vec)))
    db.commit()

    # 10. Mark ready
    db.execute("UPDATE files SET status = ? WHERE id = ?", ("ready", file_id))
    db.commit()
    db.close()

    return {"file_id": file_id, "status": "ready", "chunks": len(chunks)}


def delete_file(db_path: str, file_id: int):
    """Delete a file and all its chunks + vectors."""
    db = get_db(db_path)
    # sqlite-vec virtual table doesn't support CASCADE, delete manually
    chunk_ids = [r["id"] for r in db.execute(
        "SELECT id FROM chunks WHERE file_id = ?", (file_id,)
    ).fetchall()]
    for cid in chunk_ids:
        db.execute("DELETE FROM vec_chunks WHERE chunk_id = ?", (cid,))
    db.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
    db.execute("DELETE FROM files WHERE id = ?", (file_id,))
    db.commit()
    db.close()


def list_files(db_path: str) -> list[dict]:
    """List all ingested files."""
    db = get_db(db_path)
    rows = db.execute(
        "SELECT id, name, pages, status, created_at FROM files ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]
