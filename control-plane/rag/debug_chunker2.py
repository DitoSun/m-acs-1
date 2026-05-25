"""Deep debug: show raw_chunks before and after processing."""
import sys
sys.path.insert(0, "/app")
from rag.parser import extract, clean_page_text
from rag.chunker import chunk_text, _is_clause_start, count_tokens

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/test-real.pdf"
doc = extract(path)
text = doc["text_by_page"][0]
lines = text.split("\n")

# Simulate chunker's raw_chunk construction
full_lines = []
for line in text.split('\n'):
    line = line.strip()
    if line:
        full_lines.append((0, line))

raw_chunks = []
current = [full_lines[0]]
current_page = full_lines[0][0]

for page_idx, line in full_lines[1:]:
    if _is_clause_start(line):
        raw_chunks.append((current_page, '\n'.join(l for _, l in current)))
        current = [(page_idx, line)]
        current_page = page_idx
    else:
        current.append((page_idx, line))
if current:
    raw_chunks.append((current_page, '\n'.join(l for _, l in current)))

print("Raw chunks after clause detection:")
for i, (p, t) in enumerate(raw_chunks):
    print(f"  [{i}] tokens={count_tokens(t)} text={t[:80]}")
