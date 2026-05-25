"""Create a test PDF for pipeline verification."""
from fpdf import FPDF
import sys, os

pdf = FPDF()
pdf.add_page()
pdf.set_font('Helvetica', size=12)

content = """Test Contract

Article 1: Products
Seller agrees to sell 100 units of Product X-2000.
Unit price: $5,000. Total: $500,000.

Article 2: Payment
Buyer shall pay 30% deposit within 15 days of signing.
Balance due 5 business days before delivery.

Article 3: Delivery
Seller shall deliver within 30 days of receiving deposit.
Delivery location: Buyer's designated warehouse.

Article 4: Penalty
Either party breaching this contract shall pay 20% of total contract value.
Delays caused by force majeure shall not be deemed breach.

Article 5: Confidentiality
Both parties shall keep this contract confidential.
Confidentiality obligation continues for 3 years after termination.

Article 6: Governing Law
This contract is governed by PRC law.
Disputes shall be submitted to BIAC arbitration."""

for line in content.split('\n'):
    pdf.cell(0, 8, line, new_x='LMARGIN', new_y='NEXT')

out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/test-contract.pdf'
pdf.output(out)
print(f'PDF created: {out} ({os.path.getsize(out)} bytes)')
