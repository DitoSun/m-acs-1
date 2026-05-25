"""Generate a realistic multi-page legal contract PDF for testing."""
import sys, os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpdf import FPDF

def create():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', size=11)

    contract = """SALES AGREEMENT (the "Agreement")

dated as of January 15, 2024

BETWEEN: ABC Corporation (the "Seller")
AND: XYZ Ltd (the "Buyer")

Article 1: Definitions and Interpretation
1.1 In this Agreement, the following terms shall have the meanings set forth below:
(a) "Goods" means the products described in Schedule A.
(b) "Purchase Price" means the total amount payable by the Buyer.
(c) "Delivery Date" means the date specified in Article 3.

Article 2: Sale and Purchase
2.1 The Seller agrees to sell and the Buyer agrees to purchase the Goods.
2.2 The total Purchase Price is $500,000, exclusive of applicable taxes.
2.3 The Buyer shall pay a deposit of 30% ($150,000) within 15 days of signing.
2.4 The balance of $350,000 shall be paid 5 business days before the Delivery Date.

Article 3: Delivery
3.1 The Seller shall deliver the Goods within 30 days of receiving the deposit.
3.2 Delivery shall be made to the Buyer's designated warehouse in Shanghai.
3.3 Risk of loss passes to the Buyer upon delivery.

Article 4: Inspection and Acceptance
4.1 The Buyer shall inspect the Goods within 7 days of delivery.
4.2 If any defects are found, the Buyer must notify the Seller in writing.
4.3 The Buyer is deemed to have accepted the Goods after 7 days without notice.

Article 5: Price and Payment Terms
5.1 The Purchase Price is $500,000 as set forth in Article 2.
5.2 All payments shall be made by wire transfer to the Seller's designated account.
5.3 Late payments shall accrue interest at 1.5% per month.

Article 6: Representations and Warranties
6.1 The Seller warrants that the Goods are free from defects in materials.
6.2 The warranty period is 12 months from the Delivery Date.
6.3 This warranty does not cover damage caused by misuse or modification.

Article 7: Indemnification
7.1 Each party shall indemnify the other against third-party claims.
7.2 The indemnifying party shall have the right to control the defense.
7.3 The indemnified party shall provide reasonable cooperation.

Article 8: Limitation of Liability
8.1 Neither party shall be liable for indirect or consequential damages.
8.2 The total liability of either party shall not exceed the Purchase Price.
8.3 This limitation does not apply in cases of fraud or gross negligence.

Article 9: Termination
9.1 Either party may terminate this Agreement by 30 days written notice.
9.2 In case of material breach, the non-breaching party may terminate immediately.
9.3 Upon termination, the Buyer shall pay for all Goods delivered up to that date.

Article 10: Confidentiality
10.1 Both parties shall keep this Agreement confidential.
10.2 Confidentiality obligations survive termination for 3 years.
10.3 This Article does not apply to information already in the public domain.

Article 11: Governing Law and Dispute Resolution
11.1 This Agreement is governed by the laws of the People's Republic of China.
11.2 Any dispute shall be settled through friendly negotiation.
11.3 If negotiation fails, disputes shall be submitted to the Shanghai International Arbitration Center (SHIAC).
11.4 The arbitration shall be conducted in English.
11.5 The arbitration award shall be final and binding on both parties.

Article 12: Force Majeure
12.1 Neither party shall be liable for delays caused by force majeure.
12.2 Force majeure includes but is not limited to: natural disasters, war, government actions.
12.3 The affected party shall notify the other party within 7 days.
12.4 If force majeure lasts more than 60 days, either party may terminate."""

    for line in contract.split('\n'):
        pdf.cell(0, 6, line, new_x='LMARGIN', new_y='NEXT')

    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/test-contract-complex.pdf'
    pdf.output(out)
    print(f'Created: {out} ({os.path.getsize(out)} bytes)')
    print(f'Total lines: {len(contract.splitlines())}')

if __name__ == '__main__':
    create()
