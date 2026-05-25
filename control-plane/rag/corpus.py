"""Professional document corpus registry and test harness.

This file defines the test corpus for retrieval validation.
It does NOT store copyrighted documents — only metadata + generators.

Usage:
    python3 corpus.py --list         # List registered documents
    python3 corpus.py --generate     # Generate synthetic documents
    python3 corpus.py --validate     # Run all corpus validation tests
"""

import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

DB_PATH = os.getenv("RAG_DB_PATH", "/rag/rag.db")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

CORPUS = {
    "contract_english": {
        "type": "contract",
        "lang": "en",
        "pages": 5,
        "description": "English sales agreement with Articles 1-12",
        "generator": "generate_contract_en",
        "queries": [
            ("What is the purchase price?", ["500,000", "purchase price"]),
            ("What is the deposit percentage?", ["30%", "30 percent"]),
            ("What law governs?", ["PRC", "China"]),
        ],
    },
    "contract_chinese": {
        "type": "contract",
        "lang": "zh",
        "pages": 5,
        "description": "Chinese sales contract with 第X条 clauses",
        "generator": "generate_contract_zh",
        "queries": [
            ("违约金是多少？", ["20%"]),
            ("合同金额是多少？", ["500万"]),
            ("争议解决方式是什么？", ["仲裁"]),
        ],
    },
    "financial_report": {
        "type": "financial",
        "lang": "en",
        "pages": 30,
        "description": "Annual report with revenue, costs, and profit tables",
        "generator": "generate_financial_report",
        "queries": [
            ("What is the total revenue?", ["1,000,000", "revenue"]),
            ("What is the net profit?", ["400,000", "net profit"]),
            ("What are the risk factors?", ["risk", "market"]),
        ],
    },
    "regulation": {
        "type": "regulatory",
        "lang": "zh",
        "pages": 20,
        "description": "Chinese regulatory document with multi-level sections",
        "generator": "generate_regulation",
        "queries": [
            ("适用范围是什么？", ["适用"]),
            ("处罚措施有哪些？", ["罚款", "处罚"]),
        ],
    },
}


def list_corpus():
    """Print all registered documents."""
    print(f"Corpus: {len(CORPUS)} documents\n")
    for name, meta in CORPUS.items():
        print(f"  {name}")
        print(f"    Type: {meta['type']}  Lang: {meta['lang']}  Pages: {meta['pages']}")
        print(f"    {meta['description']}")
        print(f"    Queries: {len(meta['queries'])}")
        print()


def validate_all():
    """Run validation for all generated corpus documents."""
    from rag.store import ingest_file, get_db
    from rag.retriever import retrieve
    import tempfile

    passed = 0
    failed = 0

    for name, meta in CORPUS.items():
        print(f"\n=== {name} ===")

        # Generate the document
        gen_func = globals().get(meta["generator"])
        if not gen_func:
            print(f"  ⚠ No generator: {meta['generator']}")
            continue

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        gen_func(path)

        # Ingest
        result = ingest_file(path, DB_PATH, OLLAMA_URL, filename=f"{name}.pdf")
        os.unlink(path)

        if result.get("status") not in ("ready", "duplicate"):
            print(f"  ✗ Ingest failed: {result}")
            continue

        file_id = result.get("file_id")
        print(f"  Ingest: file_id={file_id} chunks={result.get('chunks', '?')}")

        # Run queries
        for query, expected in meta["queries"]:
            chunks = retrieve(DB_PATH, OLLAMA_URL, query)
            if not chunks:
                print(f"  ✗ No results: '{query}'")
                failed += 1
                continue
            all_text = " ".join(c["content"] for c in chunks).lower()
            found = any(e.lower() in all_text for e in expected)
            if found:
                print(f"  ✓ '{query[:40]}'")
                passed += 1
            else:
                print(f"  ✗ '{query}' (expected: {expected[0]})")
                failed += 1

    print(f"\n{'='*40}")
    print(f"Corpus validation: {passed}/{passed+failed} passed")
    print(f"{'='*40}")
    return failed == 0


# ── Document Generators ──


def generate_contract_en(path: str):
    """Generate a realistic English contract PDF."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    sections = [
        ("", "SALES AGREEMENT", "B"),
        ("", "", ""),
        ("B", "Article 1 - Definitions", ""),
        ("", "1.1 Goods means the products described in Schedule A.", ""),
        ("", "1.2 Purchase Price means the total amount payable by the Buyer.", ""),
        ("", "", ""),
        ("B", "Article 2 - Sale and Purchase", ""),
        ("", "2.1 The total Purchase Price is 500,000 USD.", ""),
        ("", "2.2 The Buyer shall pay a deposit of 30% within 15 days.", ""),
        ("", "2.3 The balance shall be paid 5 business days before delivery.", ""),
        ("", "", ""),
        ("B", "Article 11 - Governing Law", ""),
        ("", "11.1 This Agreement is governed by PRC law.", ""),
        ("", "11.2 Disputes shall be submitted to SHIAC arbitration.", ""),
    ]
    for style, text, _ in sections:
        pdf.set_font("Helvetica", "B" if style == "B" else "", 11)
        pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")

    pdf.output(path)
    print(f"  Generated: {path}")


def generate_contract_zh(path: str):
    """Generate a Chinese contract PDF."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    lines = [
        ("B", "销售合同"),
        ("", ""),
        ("B", "第一条 合同标的"),
        ("", "甲方同意出售、乙方同意购买以下产品。"),
        ("", "产品名称：工业设备X-2000。数量：100台。"),
        ("", ""),
        ("B", "第二条 价格与支付"),
        ("", "合同总金额为人民币500万元整。"),
        ("", "乙方应于合同签订后15日内支付30%定金。"),
        ("", ""),
        ("B", "第七条 争议解决"),
        ("", "本合同适用中华人民共和国法律。"),
        ("", "如发生争议，应提交北京仲裁委员会仲裁。"),
    ]
    for style, text in lines:
        pdf.set_font("Helvetica", "B" if style == "B" else "", 11)
        pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")

    pdf.output(path)


def generate_financial_report(path: str):
    """Generate a financial report with tables (text-based)."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    sections = [
        ("B", "ANNUAL REPORT 2024"),
        ("", ""),
        ("B", "Financial Highlights"),
        ("", "Total Revenue: $1,000,000"),
        ("", "Cost of Goods Sold: $600,000"),
        ("", "Gross Profit: $400,000"),
        ("", "Operating Expenses: $200,000"),
        ("", "Net Profit: $200,000"),
        ("", ""),
        ("B", "Revenue Breakdown"),
        ("", "Product A: $500,000"),
        ("", "Product B: $300,000"),
        ("", "Service: $200,000"),
        ("", ""),
        ("B", "Risk Factors"),
        ("", "1. Market risk: The industry faces increased competition."),
        ("", "2. Operational risk: Supply chain disruptions may occur."),
        ("", "3. Regulatory risk: Changes in tax policy could impact margins."),
    ]
    for style, text in sections:
        pdf.set_font("Helvetica", "B" if style == "B" else "", 11)
        pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
    pdf.output(path)


def generate_regulation(path: str):
    """Generate a Chinese regulatory document."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    lines = [
        ("B", "数据安全管理办法"),
        ("", ""),
        ("B", "第一条 制定目的"),
        ("", "为保障数据安全，制定本办法。"),
        ("", ""),
        ("B", "第二条 适用范围"),
        ("", "本办法适用于所有数据处理活动。"),
        ("", ""),
        ("B", "第五章 法律责任"),
        ("", "第三十条 违反本办法的，可处以10万元以上罚款。"),
    ]
    for style, text in lines:
        pdf.set_font("Helvetica", "B" if style == "B" else "", 11)
        pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
    pdf.output(path)


if __name__ == "__main__":
    if "--list" in sys.argv:
        list_corpus()
    elif "--generate" in sys.argv:
        import tempfile
        for name, meta in CORPUS.items():
            gen_func = globals().get(meta["generator"])
            if gen_func:
                path = f"/tmp/{name}.pdf"
                gen_func(path)
                print(f"  Generated: {path}")
    elif "--validate" in sys.argv:
        ok = validate_all()
        sys.exit(0 if ok else 1)
    else:
        list_corpus()
        print("Usage: corpus.py --list | --generate | --validate")
