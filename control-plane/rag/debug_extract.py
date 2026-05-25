"""Debug: show raw extracted text from PDF."""
import sys, os
sys.path.insert(0, "/app")
from rag.parser import extract

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/test-real.pdf"
doc = extract(path)
print(f"Pages: {doc['pages']}")
for i, text in enumerate(doc["text_by_page"]):
    lines = text.split('\n')
    print(f"\n--- Page {i+1} ({len(lines)} lines) ---")
    for j, line in enumerate(lines):
        print(f"  [{j}] {repr(line[:100])}")
