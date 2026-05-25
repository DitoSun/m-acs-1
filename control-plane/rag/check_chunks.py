"""Check chunks in the database. Run inside container."""
import sys
sys.path.insert(0, "/app")
from rag.db import get_db

db = get_db("/rag/rag.db")
cur = db.execute("SELECT COUNT(*) as c FROM files")
print(f"Files: {cur.fetchone()['c']}")

cur = db.execute("SELECT id, name, pages, status FROM files")
for r in cur.fetchall():
    print(f"  File {r['id']}: {r['name']} ({r['pages']}p, {r['status']})")

cur = db.execute("SELECT COUNT(*) as c FROM chunks")
print(f"Total chunks: {cur.fetchone()['c']}")

cur = db.execute("""
    SELECT c.id, c.file_id, c.chunk_index, c.tokens, c.page_num, substr(c.content,1,100) as txt
    FROM chunks c ORDER BY c.file_id, c.chunk_index
""")
for r in cur.fetchall():
    txt = r['txt'].replace('\n', ' | ')
    print(f"  Chunk {r['id']}: file={r['file_id']} idx={r['chunk_index']} "
          f"tokens={r['tokens']} page={r['page_num']}")
    print(f"    {txt}")

db.close()
