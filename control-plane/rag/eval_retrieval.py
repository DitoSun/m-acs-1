"""Retrieval correctness evaluation for legal document RAG.

Run inside WSL after uploading test documents.
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.db import get_db
from rag.retriever import retrieve, format_sources

DB_PATH = "/rag/rag.db"
OLLAMA_URL = "http://ollama:11434"

# Test queries with expected answers (generic professional docs)
TEST_CASES = [
    {
        "query": "What is the total purchase price?",
        "expect": ["500,000", "500000"],
        "clause": "2",
    },
    {
        "query": "What is the penalty rate for late payment?",
        "expect": ["1.5%", "1.5"],
        "clause": "5",
    },
    {
        "query": "How long is the warranty period?",
        "expect": ["12 months", "12"],
        "clause": "6",
    },
    {
        "query": "What law governs this agreement?",
        "expect": ["PRC", "China"],
        "clause": "11",
    },
    {
        "query": "How much is the required deposit?",
        "expect": ["30%", "30 percent", "150,000"],
        "clause": "2",
    },
]


def evaluate():
    db = get_db(DB_PATH)
    file_count = db.execute("SELECT COUNT(*) as c FROM files WHERE status='ready'").fetchone()["c"]
    db.close()

    print(f"Documents in DB: {file_count}\n")

    if file_count == 0:
        print("No documents found. Upload a PDF first.")
        return

    passed = 0
    failed = 0

    for tc in TEST_CASES:
        chunks = retrieve(DB_PATH, OLLAMA_URL, tc["query"])
        sources = format_sources(chunks)

        print(f"Q: {tc['query']}")
        print(f"  Expected: {tc['expect'][0]} (from {tc['clause']})")

        if not chunks:
            print(f"  ✗ FAIL: No chunks retrieved\n")
            failed += 1
            continue

        # Check if any chunk content matches expected answer
        all_text = " ".join(c["content"] for c in chunks).lower()
        found = any(exp.lower() in all_text for exp in tc["expect"])
        clause_found = tc["clause"].lower() in all_text

        print(f"  Chunks: {len(chunks)}")
        print(f"  Sources: {len(sources)} files")
        for s in sources[:2]:
            print(f"    - {s['file']} page {s['page']}")

        if found and clause_found:
            print(f"  ✓ PASS\n")
            passed += 1
        elif found:
            print(f"  ⚠ Partial: content found but clause reference weak\n")
            passed += 0.5
            failed += 0.5
        else:
            print(f"  ✗ FAIL: No expected content found\n")
            failed += 1

        # Show top chunk preview
        if chunks:
            preview = chunks[0]["content"][:150]
            print(f"  Top chunk: {preview}...\n")

    print(f"=== Results: {passed}/{passed+failed} passed ({passed/(passed+failed)*100:.0f}%) ===")


def show_chunk_detail(chunk_id: int = None):
    """Debug: show a specific chunk's content and source."""
    db = get_db(DB_PATH)
    if chunk_id:
        rows = db.execute("""
            SELECT c.*, f.name as file_name
            FROM chunks c JOIN files f ON f.id = c.file_id
            WHERE c.id = ?
        """, (chunk_id,)).fetchall()
    else:
        rows = db.execute("""
            SELECT c.*, f.name as file_name
            FROM chunks c JOIN files f ON f.id = c.file_id
            LIMIT 5
        """).fetchall()
    db.close()
    for r in rows:
        print(f"\nChunk {r['id']}: {r['file_name']} page {r['page_num']}")
        print(f"Tokens: {r['tokens']}")
        print(f"Content: {r['content'][:300]}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "chunks":
        show_chunk_detail(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        evaluate()
