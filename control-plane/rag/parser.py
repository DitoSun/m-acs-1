"""PDF text extraction with robust normalization for legal documents.

Handles: null bytes, corrupted encodings, whitespace normalization.
"""

import logging
import os
import re

logger = logging.getLogger("m-acs.rag.parser")

SCAN_THRESHOLD = 30


def extract(path: str) -> dict:
    """Extract text from PDF. Returns {pages: int, text_by_page: [str]}."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")

    import fitz

    doc = fitz.open(path)
    pages = []
    for page in doc:
        raw = page.get_text("text")
        pages.append(_normalize_text(raw))

    total_chars = sum(len(p) for p in pages)
    avg = total_chars / max(len(pages), 1)

    if avg < SCAN_THRESHOLD:
        raise ValueError(
            f"该 PDF 可能是扫描件（平均每页仅 {avg:.0f} 个字符），"
            f"暂不支持。请使用可复制文本的 PDF 文件。"
        )

    result = {"pages": len(pages), "text_by_page": pages}
    doc.close()
    return result


def _normalize_text(text: str) -> str:
    """Full text normalization pipeline for legal PDFs."""
    # 1. Remove null bytes and other non-printable chars (except newlines/tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # 2. Normalize Unicode: fullwidth ASCII (U+FF01-FF5E → U+0021-007E)
    #    Fullwidth A (U+FF21) → A, fullwidth a (U+FF41) → a, etc.
    text = text.translate(str.maketrans(
        ''.join(chr(0xFF01 + i) for i in range(94)),
        ''.join(chr(0x21 + i) for i in range(94)),
    ))

    # 3. Fix common PDF encoding glitches
    replacements = {
        '�': '',           # replacement character
        '​': '',           # zero-width space
        '': '•',          # bullet
        '': ' ',          # some PDFs use these for spaces
        ' ': ' ',          # non-breaking space -> regular space
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # 4. Currency symbols: PyMuPDF sometimes encodes $ as \x00
    text = text.replace('\x00', '$')

    # 5. Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)         # multiple spaces -> one
    text = re.sub(r'\n\s*\n', '\n\n', text)     # blank lines -> single

    return text.strip()


def clean_page_text(text: str) -> str:
    """Page-level cleaning: headers, footers, page numbers."""
    # Remove standalone page numbers
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*第\s*\d+\s*页\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*-\s*\d+\s*-\s*$', '', text, flags=re.MULTILINE)

    # Remove common header/footer patterns (lines at top/bottom 15%)
    lines = text.split('\n')
    n = len(lines)
    body = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            body.append('')
            continue
        # Skip short lines at top or bottom that look like headers/footers
        if (i < n * 0.15 or i > n * 0.85) and len(stripped) < 40:
            continue
        body.append(line)

    text = '\n'.join(body)

    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
