"""Create a properly structured PDF for testing chunking."""
from fpdf import FPDF
import sys, os

pdf = FPDF()
pdf.add_page()
pdf.set_font('Helvetica', size=11)

content = [
    ("", "SALES AGREEMENT"),
    ("", ""),
    ("B", "Article 1 - Definitions"),
    ("", "1.1 Goods means the products in Schedule A."),
    ("", "1.2 Purchase Price means total amount payable."),
    ("", ""),
    ("B", "Article 2 - Sale and Purchase"),
    ("", "2.1 Total Purchase Price is 500,000 USD."),
    ("", "2.2 Deposit of 30% within 15 days of signing."),
    ("", "2.3 Balance due 5 business days before delivery."),
    ("", ""),
    ("B", "Article 3 - Delivery"),
    ("", "3.1 Seller delivers within 30 days of deposit."),
    ("", "3.2 Delivery to Buyer warehouse in Shanghai."),
    ("", ""),
    ("B", "Article 11 - Governing Law"),
    ("", "11.1 Governed by PRC law."),
    ("", "11.2 Disputes to SHIAC arbitration."),
]

for style, text in content:
    if style == "B":
        pdf.set_font("Helvetica", "B", 11)
    else:
        pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")

out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/test-real.pdf"
pdf.output(out)
print(f"PDF created: {out} ({os.path.getsize(out)} bytes)")
