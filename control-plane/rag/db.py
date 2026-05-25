"""SQLite + sqlite-vec database setup."""

import sqlite3
import os
import logging

logger = logging.getLogger("m-acs.rag.db")

VECTOR_DIM = 1024  # bge-m3


def get_db(db_path: str) -> sqlite3.Connection:
    """Open DB, load sqlite-vec extension, create tables if needed."""
    import sqlite_vec

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")

    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    _create_tables(db)
    return db


def _create_tables(db: sqlite3.Connection):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            pages       INTEGER DEFAULT 0,
            size_bytes  INTEGER DEFAULT 0,
            sha256      TEXT UNIQUE,
            status      TEXT DEFAULT 'processing',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id          INTEGER PRIMARY KEY,
            file_id     INTEGER REFERENCES files(id) ON DELETE CASCADE,
            content     TEXT NOT NULL,
            page_num    INTEGER DEFAULT 0,
            chunk_index INTEGER DEFAULT 0,
            tokens      INTEGER DEFAULT 0
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
            chunk_id INTEGER PRIMARY KEY,
            embedding FLOAT[1024]
        );
    """)
    db.commit()


def drop_tables(db: sqlite3.Connection):
    """Drop all RAG tables (for testing/reset)."""
    db.executescript("""
        DROP TABLE IF EXISTS vec_chunks;
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS files;
    """)
    db.commit()
