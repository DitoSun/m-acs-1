"""Debug chunker behavior. Run inside container."""
import sys
sys.path.insert(0, "/app")
from rag.parser import extract, clean_page_text
from rag.chunker import chunk_text, _is_clause_start

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/test-real.pdf"
doc = extract(path)
text = doc["text_by_page"][0]
lines = text.split("\n")

print(f"Lines: {len(lines)}")
for i, l in enumerate(lines[:30]):
    stripped = l.strip()
    if stripped:
        match = "ARTICLE" if _is_clause_start(stripped) else ""
        print(f"  {i:2d} [{match:8s}] {stripped[:80]}")

cleaned = [clean_page_text(p) for p in doc["text_by_page"]]
chunks = chunk_text(cleaned)
print(f"\nChunks: {len(chunks)}")
for c in chunks:
    print(f"  [{c['chunk_index']}] tokens={c['tokens']} page={c['page_num']}")

print("\nFull pipeline result:")
for c in chunks:
    print(f"--- Chunk {c['chunk_index']} (page {c['page_num']}) ---")
    print(c['content'][:200])
    print()
