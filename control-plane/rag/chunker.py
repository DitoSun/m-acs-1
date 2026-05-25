"""Professional document chunking — regex + paragraph based.

Supports: contracts, financial reports, audit reports, policies.
Preserves section boundaries, numbering, and cross-page context.
No LangChain. No semantic chunking. No LLM.
"""

import re
import logging

logger = logging.getLogger("m-acs.rag.chunker")

# Legal chunking separators (priority order)
SEPARATORS = [
    r'\n第[一二三四五六七八九十百千零]+[章节条]',    # "第一条" / "第二章"
    r'\n第\d+[章节条]',                              # "第1条" / "第2章"
    r'\n[一二三四五六七八九十]+[、．\.\s]',            # "一、" / "二、"
    r'\n（[一二三四五六七八九十]+）',                  # "（一）"
    r'\n•',                                           # bullet
    r'\n\n',                                          # paragraph
    r'。',                                            # sentence (last resort)
]

MAX_TOKENS = 400
OVERLAP_TOKENS = 50


def count_tokens(text: str) -> int:
    """Approximate token count for Chinese + English mix."""
    chinese = len(re.findall(r'[一-鿿　-〿＀-￯]', text))
    other = len(re.sub(r'[一-鿿　-〿＀-￯\s]', '', text))
    return chinese + max(1, other // 4)


def chunk_text(text_by_page: list, max_tokens=MAX_TOKENS, overlap_tokens=OVERLAP_TOKENS) -> list:
    """Chunk legal text preserving clause and section boundaries.

    Returns:
        [{"content": str, "page_num": int, "chunk_index": int, "tokens": int}, ...]
    """
    # Build line-indexed text with page tracking
    full_lines = []
    for page_idx, page_text in enumerate(text_by_page):
        for line in page_text.split('\n'):
            line = line.strip()
            if line:
                full_lines.append((page_idx, line))

    if not full_lines:
        return []

    # Group lines into clause-based raw chunks
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

    # Sub-split oversized chunks
    final_chunks = []
    for page_num, text in raw_chunks:
        if count_tokens(text) <= max_tokens:
            final_chunks.append((page_num, text))
        else:
            parts = _split_by_separators(text, SEPARATORS)
            for p in parts:
                p = p.strip()
                if p:
                    final_chunks.append((page_num, p))

    # Build output (no overlap - legal articles are self-contained)
    # Merge title/header into the first article
    if len(final_chunks) > 1 and count_tokens(final_chunks[0][1]) < 20:
        first_page = final_chunks[0][0]
        second_page = final_chunks[1][0]
        merged_text = final_chunks[0][1] + '\n' + final_chunks[1][1]
        final_chunks = [(first_page, merged_text)] + final_chunks[2:]

    result = []
    for idx, (page_num, text) in enumerate(final_chunks):
        t_count = count_tokens(text)
        if t_count > max_tokens:
            chars = max_tokens * 2
            text = text[:chars]
            t_count = count_tokens(text)

        result.append({
            "content": text,
            "page_num": page_num + 1,
            "chunk_index": idx,
            "tokens": t_count,
        })

    return result


def format_clause_ref(chunk: dict) -> str:
    """Extract the clause/section reference from a chunk."""
    lines = chunk["content"].strip().split('\n')
    for line in lines:
        line = line.strip()
        if re.match(r'^第[一二三四五六七八九十百千零\d]+[章节条]', line):
            return line[:30]
    return f"第{chunk['chunk_index']+1}段"


def _is_clause_start(line: str) -> bool:
    """Detect legal clause/section headings (NOT sub-clauses like 1.1)."""
    patterns = [
        r'^第[一二三四五六七八九十百千零]+[章节条]',     # Chinese: 第一条
        r'^第\d+[章节条]',                               # Chinese: 第1条
        r'^[一二三四五六七八九十]+[、．\.]',                # Chinese: 一、
        r'^（[一二三四五六七八九十]+）',                   # Chinese: （一）
        r'^(Article|Section|Clause|Part|Chapter)\s+\d+',  # English articles
    ]
    return any(re.match(p, line.strip()) for p in patterns)


def _split_by_separators(text: str, separators: list) -> list:
    """Recursive text splitting — smallest first."""
    if not separators:
        return [text]
    sep = separators[0]
    parts = re.split(sep, text)
    if len(parts) <= 1:
        return _split_by_separators(text, separators[1:])
    result = []
    for p in parts:
        result.extend(_split_by_separators(p, separators[1:]))
    return result
