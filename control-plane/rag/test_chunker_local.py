"""Test chunker directly with legal text. Run inside container."""
import sys
sys.path.insert(0, "/app")
from rag.chunker import chunk_text

text = [
    "SALES AGREEMENT",
    "",
    "Article 1 - Definitions",
    "1.1 Goods means the products in Schedule A.",
    "1.2 Purchase Price means total amount payable.",
    "",
    "Article 2 - Sale and Purchase",
    "2.1 Total Purchase Price is 500,000 USD.",
    "2.2 Deposit of 30% within 15 days of signing.",
    "2.3 Balance due 5 business days before delivery.",
    "",
    "Article 3 - Delivery",
    "3.1 Seller delivers within 30 days of deposit.",
    "3.2 Delivery to Buyer warehouse in Shanghai.",
    "",
    "Article 4 - Inspection",
    "4.1 Buyer inspects within 7 days of delivery.",
    "4.2 Defects notified in writing within 7 days.",
    "",
    "Article 5 - Payment Terms",
    "5.1 All payments by wire transfer.",
    "5.2 Late payment interest: 1.5 percent per month.",
    "",
    "Article 6 - Warranties",
    "6.1 Seller warrants goods free from defects.",
    "6.2 Warranty period: 12 months from delivery.",
    "",
    "Article 11 - Governing Law",
    "11.1 Governed by PRC law.",
    "11.2 Disputes to SHIAC arbitration.",
    "11.3 Award is final and binding.",
]

chunks = chunk_text(["\n".join(text)])
print(f"Chunks: {len(chunks)}")
for c in chunks:
    s = c["content"][:80].replace('\n', ' ')
    print(f"  [{c['chunk_index']}] page={c['page_num']} tokens={c['tokens']} text={s}...")
