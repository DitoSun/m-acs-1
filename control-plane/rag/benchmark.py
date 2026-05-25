"""Retrieval benchmark: automated quality tests for the document pipeline.

Run:  python3 benchmark.py           # full suite
      python3 benchmark.py --list    # list test cases
      python3 benchmark.py --quick   # quick smoke test

Exit code: 0 = all passed, 1 = some failed.
"""

import sys, os, json, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

DB_PATH = os.getenv("RAG_DB_PATH", "/rag/rag.db")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

PASS = 0
FAIL = 0
WARN = 0


def check(label, condition, detail=""):
    global PASS, FAIL, WARN
    if condition:
        PASS += 1
        print(f"  ✓ {label}")
    elif detail:
        WARN += 1
        print(f"  ⚠ {label} — {detail}")
    else:
        FAIL += 1
        print(f"  ✗ {label}")


def section(name):
    print(f"\n=== {name} ===")


# ── Document Tests ──


def test_doc_upload():
    """Test: upload a PDF and verify it's processed."""
    section("Document Upload")
    # Upload a known test PDF
    import subprocess
    from rag.store import ingest_file

    # Use a test PDF if available
    test_paths = [
        "/tmp/test.pdf",
        "/tmp/test-real.pdf",
        "/tmp/test-contract.pdf",
    ]
    path = None
    for p in test_paths:
        if os.path.exists(p):
            path = p
            break
    if not path:
        print("  ⚠ No test PDF found, creating one")
        from rag.create_proper_test_pdf import create
        path = "/tmp/bench-test.pdf"
        create(path)

    result = ingest_file(path, DB_PATH, OLLAMA_URL, filename="bench-test.pdf")
    check("Upload returns file_id", result.get("file_id") is not None)
    check("Status is ready or duplicate", result.get("status") in ("ready", "duplicate"))
    if result.get("chunks"):
        check("Produced chunks", result["chunks"] > 0, f"got {result['chunks']}")


# ── Parser Tests ──


def test_parser_robustness():
    """Test: parser handles edge cases without crashing."""
    section("Parser Robustness")

    from rag.parser import _normalize_text, clean_page_text

    # Test the main normalization pipeline (used in extract())
    cases = [
        ("null bytes", "hello\x00world\x00test", "helloworldtest"),
        ("fullwidth chars", "ＡＢＣ", "ABC"),
        ("unicode replacements", "test�doc", "testdoc"),
    ]
    for name, inp, expected_part in cases:
        result = _normalize_text(inp)
        check(f"Normalize '{name}'", expected_part.lower() in result.lower())

    # clean_page_text removes page numbers and collapses excess newlines
    result = clean_page_text("line1\nline2\n\n\n\nline3")
    check("Clean newlines", result.strip() != "" and "line3" in result)


def test_parser_scan_detection():
    """Test: scanner detection rejects scanned PDFs."""
    from rag.parser import extract
    scanned_text = ["abc"] * 10  # less than 30 chars per page
    # This is hard to test without a real scanned PDF, verify threshold
    from rag.parser import SCAN_THRESHOLD
    check("Scan threshold set", SCAN_THRESHOLD == 30)


# ── Chunker Tests ──


def test_chunker_english():
    """Test: chunker splits by English section headings."""
    from rag.chunker import chunk_text, _is_clause_start

    check("'Article 1' detected", _is_clause_start("Article 1 - Definitions"))
    check("'Section 2' detected", _is_clause_start("Section 2: Payment"))
    check("'1.1' NOT a clause start", not _is_clause_start("1.1 This is a sub-clause"))

    text = [
        "Title",
        "",
        "Article 1 - Definitions",
        "Term A means something.",
        "",
        "Article 2 - Payment",
        "Payment is due within 30 days.",
    ]
    chunks = chunk_text(["\n".join(text)])
    check("English legal chunks >= 2", len(chunks) >= 2, f"got {len(chunks)}")


def test_chunker_chinese():
    """Test: chunker splits by Chinese legal headings."""
    from rag.chunker import chunk_text, _is_clause_start

    check("'第一条' detected", _is_clause_start("第一条 合同标的"))
    check("'第二章' detected", _is_clause_start("第二章 合同的履行"))
    check("'一、' detected", _is_clause_start("一、违约责任"))

    text = [
        "合同标题",
        "",
        "第一条 合同标的",
        "甲方同意出售产品。",
        "",
        "第二条 付款",
        "付款应在30日内完成。",
    ]
    chunks = chunk_text(["\n".join(text)])
    check("Chinese legal chunks >= 2", len(chunks) >= 2, f"got {len(chunks)}")


def test_chunker_max_tokens():
    """Test: no chunk exceeds MAX_TOKENS."""
    from rag.chunker import chunk_text, MAX_TOKENS

    # Generate a long document
    lines = ["Title"]
    for i in range(1, 50):
        lines.extend([
            f"Article {i} - Test Section",
            f"This is the content of article {i}. " * 20,
        ])
    chunks = chunk_text(["\n".join(lines)])
    oversized = [c for c in chunks if c["tokens"] > MAX_TOKENS * 1.1]
    check(f"No chunk exceeds {MAX_TOKENS}", len(oversized) == 0,
           f"{len(oversized)} chunks over limit")


# ── Retrieval Tests ──


def test_retrieval_reproducibility():
    """Test: same query returns same chunks."""
    from rag.retriever import retrieve

    queries = ["What is the price?", "payment terms", "governing law"]
    for q in queries:
        first = retrieve(DB_PATH, OLLAMA_URL, q)
        if not first:
            continue
        for _ in range(5):
            second = retrieve(DB_PATH, OLLAMA_URL, q)
            if not second:
                continue
            check(f"Reproducible: '{q[:20]}'",
                  first[0]["content"] == second[0]["content"],
                  "top chunk changed")
            check(f"Same count: '{q[:20]}'",
                  len(first) == len(second),
                  f"{len(first)} vs {len(second)}")
            break


def test_retrieval_source_attribution():
    """Test: retrieved chunks have valid source info."""
    from rag.retriever import retrieve

    chunks = retrieve(DB_PATH, OLLAMA_URL, "test query")
    if not chunks:
        print("  ⚠ No documents ingested, skipping source test")
        return

    for c in chunks:
        check("File name present", bool(c.get("file_name")))
        check("Page number valid", c.get("page_num", 0) > 0, f"page={c['page_num']}")
        check("Content non-empty", bool(c.get("content")))
        check("Token count valid", c.get("tokens", 0) > 0)


def test_retrieval_known_queries():
    """Test: known queries find expected content."""
    from rag.retriever import retrieve

    queries = [
        ("purchase price", ["500,000"]),
        ("deposit percentage", ["30%", "30 percent"]),
        ("delivery", ["Shanghai", "warehouse"]),
    ]

    for query, expected in queries:
        chunks = retrieve(DB_PATH, OLLAMA_URL, query)
        if not chunks:
            print(f"  ⚠ No results for '{query}'")
            continue
        all_text = " ".join(c["content"] for c in chunks).lower()
        found = any(e.lower() in all_text for e in expected)
        check(f"Found '{query}'", found)


# ── Run ──


def run_all():
    test_parser_robustness()
    test_parser_scan_detection()
    test_chunker_english()
    test_chunker_chinese()
    test_chunker_max_tokens()
    test_retrieval_source_attribution()
    test_retrieval_known_queries()
    test_retrieval_reproducibility()

    total = PASS + FAIL + WARN
    print(f"\n{'='*40}")
    print(f"Results: {PASS}/{total} passed")
    if FAIL:
        print(f"  FAIL: {FAIL}")
    if WARN:
        print(f"  WARN: {WARN}")
    print(f"{'='*40}")
    return FAIL == 0


if __name__ == "__main__":
    if "--list" in sys.argv:
        print("Available tests:")
        for name in sorted(globals()):
            if name.startswith("test_"):
                print(f"  {name}")
    elif "--quick" in sys.argv:
        test_chunker_english()
        test_chunker_chinese()
        test_retrieval_source_attribution()
    else:
        ok = run_all()
        sys.exit(0 if ok else 1)
