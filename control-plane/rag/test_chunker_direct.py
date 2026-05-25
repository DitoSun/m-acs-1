"""Minimal test of chunk_text function."""
import sys
sys.path.insert(0, "/app")
from rag.chunker import chunk_text, count_tokens

text = """SALES AGREEMENT

Article 1 - Definitions
1.1 Goods means the products in Schedule A.
1.2 Purchase Price means total amount payable.

Article 2 - Sale and Purchase
2.1 Total Purchase Price is 500,000 USD.
2.2 Deposit of 30% within 15 days of signing.
2.3 Balance due 5 business days before delivery.

Article 3 - Delivery
3.1 Seller delivers within 30 days of deposit.
3.2 Delivery to Buyer warehouse in Shanghai.

Article 11 - Governing Law
11.1 Governed by PRC law.
11.2 Disputes to SHIAC arbitration."""

chunks = chunk_text([text])
print(f"Chunks: {len(chunks)}")
for c in chunks:
    content = c["content"][:100].replace('\n', ' | ')
    print(f"  [{c['chunk_index']}] tokens={c['tokens']} page={c['page_num']}")
    print(f"    {content}")
