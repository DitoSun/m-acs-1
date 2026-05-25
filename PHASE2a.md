# Phase 2a — Professional Document Intelligence Pipeline

## 一句话目标

> **上传专业 PDF（合同/财报/审计报告）→ 基于文档问答 → 显示引用来源。** 不引入任何框架依赖。

---

## 1. 技术栈

```
当前已有:                    Phase 2a 新增:
─────────────────────        ─────────────────────────
Python 3.12                 PyMuPDF (fitz)         — PDF 解析
FastAPI / Uvicorn           自定义 chunker          — 无框架
Ollama / Qwen 2.5          Ollama /api/embed       — bge-m3
SQLite                      sqlite-vec             — 向量存储
无                         无 LangChain / Chroma / OCR / Paddle
```

**Python 依赖净新增：3 个包（fitz, sqlite-vec, numpy）。**

---

## 2. Document Pipeline

```
用户拖入 PDF
    │
    ▼
PyMuPDF 提取文本
    │
    ├─ 文本过少? → 提示 "扫描件暂不支持"
    │
    ▼
正则清洗
    │
    ├─ 移除页眉/页脚/页码
    ├─ 合并断行
    │
    ▼
段落级 Chunking
    │
    ├─ 按 "第X条" / "第X章" / 段落 切割
    ├─ chunk_size = 400 tokens
    ├─ overlap = 50 tokens
    │
    ▼
Ollama /api/embed (bge-m3)
    │
    ▼
sqlite-vec 写入
    │
    ▼
用户可提问
```

---

## 3. Chunking（无 LangChain）

### 实现方案

```python
# 一个函数，无框架，~40 行
def chunk_legal_text(text: str, max_tokens=400, overlap_tokens=50):
    """Chunk Chinese legal text by article/section boundaries."""

    # 1. 中文法律分割模式（按优先级）
    separators = [
        r'\n第[一二三四五六七八九十百千]+[章节条]',   # "第一章" / "第二条"
        r'\n第\d+[章节条]',                          # "第1章" / "第2节"
        r'\n[一二三四五六七八九十]+[、．\.]',          # "一、" / "二、"
        r'\n（[一二三四五六七八九十]+）',              # "（一）" / "（二）"
        r'\n\n',                                      # 段落
        r'\n',                                        # 行
        r'。',                                        # 句
    ]

    # 2. 递归分割（同 LangChain RecursiveCharacterTextSplitter 思路，
    #    但 40 行内实现，无外部依赖）
    chunks = []
    # ...

    # 3. overlap: 每个 chunk 保留前一个 chunk 的最后 50 tokens
    # ...

    # 4. 附加 source info
    return [{
        "content": text,
        "page": page_num,
        "chunk_index": i,
        "tokens": token_count(text),
    }]
```

**没有 LangChain。没有 semantic chunker。没有 LLM-based splitting。只有正则 + 段落切割。**

---

## 4. OCR 策略

### Phase 2a 不做 OCR

```python
if len(extracted_text) < page_count * 30:
    raise ValueError(
        "该 PDF 可能是扫描件，暂不支持。"
        "请使用可复制文本的 PDF 文件。"
    )
```

### 为什么

| 问题 | 影响 |
|---|---|
| PaddleOCR 包大小 ~200MB | 拉取时间长，首次体验差 |
| OCR 结果错误 → retrieval 错误 | 用户无法区分是 OCR 错还是检索错 |
| 中文 OCR 质量波动大 | 法律文档一个字错可能改变条款含义 |

**只有 PDF 内嵌文本的文档才进入 pipeline。扫描件明确提示不支持。比给出错误结果更诚实。**

---

## 5. Embedding

### 方案

```python
POST /api/embed
{
    "model": "bge-m3",
    "input": [chunk1, chunk2, ...]   # 批量 embed
}
```

### 批量策略

- 每次 batch 16 chunks
- bge-m3 context window = 8192 tokens
- 单条 chunk < 512 tokens，不会截断
- 向量维度 = 1024

### bge-m3 第一次运行时拉取

```bash
ollama pull bge-m3    # ~1.3GB, 仅拉取一次
```

---

## 6. Retrieval（无固定 top-k）

### Token Budget 策略

```python
MAX_CONTEXT_TOKENS = 2048   # 保留给检索上下文的 token 预算
QUERY_EMBED_DIM = 1024

def retrieve(query, k_max=10):
    # 1. Embed query → 1024 维向量
    q_vec = embed(query)

    # 2. Vector search: 取余弦相似度 top-k_max
    candidates = vec_search(q_vec, k=k_max)

    # 3. Token budget: 从最相关开始累加，直到 token 预算用尽
    context = []
    total_tokens = 0
    for c in sorted(candidates, key=lambda x: -x.score):
        needed = c.tokens + 50  # 50 tokens overhead
        if total_tokens + needed > MAX_CONTEXT_TOKENS:
            break
        context.append(c)
        total_tokens += needed

    return context  # 可能是 3-8 个 chunks，取决于长度
```

### 为什么

| 固定 top-k | Token Budget |
|---|---|
| 短 chunk 浪费 budget | 充分利用 2048 tokens |
| 长 chunk 撑爆 context | 自动控制 |
| 结果数量不可预测 | 总是刚好填满 budget |

---

## 7. Source Attribution

### 优先级：source trust > generation quality

法律场景中，用户宁可看到：

```
我无法确定这个问题的答案。
以下是相关条款，请您自行判断:

📎 销售合同.pdf → 第7页
   "7.2 任何一方违约，应向对方支付合同总金额
    20%的违约金。"
```

也不要看到：

```
根据合同约定，违约金为20%。✅ （编的）
```

### 引用格式

```
📎 {文件名}.pdf → 第{page}页 → 第{chunk_index}块
   "{原文片段前 200 字}"
```

### Prompt 强制引用

```python
RAG_PROMPT = """你是一个法律文档分析助手。
基于以下文档内容回答问题。如果文档内容不足以回答，
请明确说"文档中未提及"，不要编造。

回答时，对于每条信息，必须说明来自哪个文件的哪一页。

文档内容：
{context_with_sources}

问题：{question}
---"""
```

---

## 8. SQLite Schema（最终版）

```sql
CREATE TABLE files (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    pages       INTEGER,
    size_bytes  INTEGER,
    sha256      TEXT UNIQUE,
    status      TEXT DEFAULT 'processing',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE chunks (
    id          INTEGER PRIMARY KEY,
    file_id     INTEGER REFERENCES files(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    page_num    INTEGER,
    chunk_index INTEGER,
    tokens      INTEGER
);

-- sqlite-vec 虚拟表
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[1024]
);
```

删除文件 = `DELETE FROM files WHERE id = ?`（cascade 删除 chunks + 向量）。

---

## 9. API Design

```
POST /api/documents/upload
  → 上传 PDF → 解析 → chunk → embed → store
  → { file_id, status: "processing" }

GET /api/documents
  → { files: [{ id, name, status, pages, created_at }] }

DELETE /api/documents/{id}
  → 删除文件及所有 chunks

POST /api/documents/ask
  { question: "...", file_ids: [1,2] }    # 可选限定文件
  → { answer, sources: [{ file, page, snippet }] }

GET /api/documents/{id}/chunks
  → 查看已提取的 chunks（调试用）
```

### 无 WebSocket

- 文件上传用 `POST` + 同步处理（法律文档通常 < 50 页，处理 < 30 秒）
- 如果需要异步，前端轮询 `GET /api/documents`

---

## 10. Phase 2a 边界

### 做

```
□  PDF 解析（PyMuPDF）
□  中文法律文本切割（自定义 chunker）
□  bge-m3 embedding（Ollama）
□  sqlite-vec 存储
□  Token-budget retrieval
□  Source attribution（文件/页码/原文）
□  文件管理（上传/列表/删除）
□  文档问答 API
```

### 不做

```
□  OCR / 扫描件                     → 明确提示不支持
□  LangChain / LlamaIndex            → 零框架
□  复杂 UI                           → 先用 curl 验证 pipeline
□  WebSocket 进度                    → 同步处理
□  Hybrid search / Reranking         → 不需要
□  多文件联合检索                      → Phase 2b
□  文件预览                           → Phase 2b
□  PDF 页眉页脚完美处理                 → 正则过滤即可
□  表格提取                           → 法律 PDF 表格少
```

---

## 11. 成功标准

### 技术验证

```
□  上传 3 份不同法律 PDF（合同/判决书/法规）→ 解析成功
□  每个文档正确切割为 5-50 个 chunks
□  每份文档的 chunks 写入 sqlite-vec
□  对每份文档提问 5 个问题 → 返回相关结果
□  每个回答附带正确的引用来源（文件名+页码）
□  同一问题在不同 chunk 配置下结果一致
□  200 页长文档处理时间 < 60 秒
```

### 方向验证（更重要）

```
以下场景通过，说明 Legal Appliance 方向成立:

□  场景 A: "这份合同第7条约定的违约金是多少？"
    → 找到第7条，提取违约金数额，显示原文

□  场景 B: "2024年新公司法对认缴期限有什么变化？"
    → 从法规 PDF 中找到相关条款

□  场景 C: "这两份合同中的保密条款有什么差异？"
    → 分别检索两份文档，比对条款（Phase 2b）
```

### 失败标准（说明方向有问题）

```
□  常用法律文档检索不到正确条款
□  引用来源不准确（指了错误的页码）
□  bge-m3 对中文法律术语的语义理解不够
□  用户倾向于用全文搜索而不是 RAG
```

### Phase 2a 终止条件

```
上述 3 个场景全部跑通，且用户确认检索结果可用。
然后进入 Phase 2b（Document Workspace UI）。
```

---

## 12. 依赖清单

### 新增 Python 包

```
PyMuPDF         PDF 解析
sqlite-vec      向量扩展（SQLite）
numpy           向量计算
```

### 新增 Ollama 模型

```
bge-m3          Embedding（~1.3GB, 首次拉取）
```

### 零新增服务

```
□  不装新 Docker 容器
□  不装新数据库
□  不装新运行时
```

---

## 13. 产品定位

### M-ACS-1 Phase 2 是什么

> **一台本地运行的专业文档智能 Appliance。**
>
> 律师审合同、会计看财报、审计查报告、金融做尽调——
> 上传 PDF，直接提问，AI 基于原文回答，附带来源引用。
> **所有文件不出本机，不依赖任何云服务。**

### 与竞品的核心区别

```
通用 AI 聊天（ChatGPT）     M-ACS-1 Professional Doc
──────────────────────      ────────────────────────
上传文件到云端              本地处理，文件不出门
无法追溯信息来源             每条回答带原文+页码
通用知识回答                基于用户自己的文档
不支持长文档结构            结构化章节分割+检索
```

### 目标场景

| 行业 | 文档类型 | 典型问题 |
|---|---|---|
| 法律 | 合同/判决书/法规 | "违约金比例是多少？" |
| 会计 | 审计报告/财报 | "今年的净利润是多少？" |
| 金融 | 招股书/尽调报告 | "主要风险因素有哪些？" |
| 企业 | 政策文件/SOP | "审批流程是什么？" |

---

## 14. Chunking Strategy Revision

当前 chunking 支持两种模式：

### 模式 1: 章节标题分割（通用）

检测以下章节边界：

```
英文: Article / Section / Chapter / Part / Clause
中文: 第X条 / 第X章 / 第X节 / 一、/ （一）
通用: 1.  / 1.1  / 1.1.1
```

适用：合同、政策文件、审计报告（带结构化编号）

### 模式 2: 段落分割（无编号文档）

当文档没有明确的章节编号时，回退到：

```
空行分割 → 段落级 chunk → 每个 chunk ≤ 400 tokens
```

适用：财报附注、叙述性报告、信函

### 当前不做

- 表格提取（PyMuPDF 表格识别不准确，Phase 2b）
- 页眉页脚完美去除（正则过滤即可，不追求 100%）
- OCR（扫描件明确提示不支持）

---

## 15. Retrieval Strategy Re-evaluation

### 当前策略（已验证）

```
查询 → bge-m3 1024维 embedding → sqlite-vec 余弦相似度
→ top-k 候选 (k=15) → 2048 token budget 择优 → 回答
```

### 各场景表现

| 场景 | 预期表现 | 风险 |
|---|---|---|
| 法律合同（条款化） | 高 — 每条款 = 独立 chunk | 条款编号不一致 |
| 财报（数字密集） | 中高 — 数字直接匹配 | 上下文需要表格 |
| 审计报告（叙述性） | 中 — 依赖段落分割质量 | 多段连续叙述 |
| 尽调报告（混合） | 中 — 标题+段落混合 | 格式多样性 |

### 调整方向（Phase 2a 不做）

```
□  针对数字/金额的精确匹配检索（Phase 2b）
□  表格结构的行/列感知检索（Phase 2b）
□  Hybrid search（语义+关键词，Phase 2b+）
□  Naive chunking of long narratives（Phase 2a 即可）
```

---

## 16. Product Language Audit

### UI / API 术语调整

| 当前用语 | 调整方向 | 原因 |
|---|---|---|
| "法律 PDF" | "专业文档" | 不限于法律场景 |
| "条款" | "章节" | 覆盖财报/报告 |
| "违约金" | Prompt 示例改为通用问题 | 避免法律偏见 |
| "Legal RAG" | "Document Intelligence" | 产品定位 |
| "legal_text" | "professional_doc" | 代码通用化 |

### 保留的术语

```
"source attribution"    — 跨行业通用
"reference"             — 跨行业通用
"document analysis"     — 跨行业通用
"retrieval"             — 跨行业通用
```

### 不做

```
- 不做术语本地化（当前中文+英文已足够）
- 不做行业定制 UI（太早）
- 不做场景切换器（太早）
```

---

## 17. Embedding Strategy Re-evaluation

### bge-m3 继续保留为默认选择

| 场景 | bge-m3 表现 | 说明 |
|---|---|---|
| 中文法律合同 | ✅ 最佳 | 法律术语理解准确 |
| 中文财报 | ✅ 优秀 | 数字+中文混合场景可靠 |
| 英文合同 | ✅ 良好 | BAAI 在英文上也有训练 |
| 中英混合 | ✅ 最佳 | 原生支持多语言混合 |
| 长文本（>512 tokens） | ✅ 8192 context | 远超其他本地模型 |

### 备选模型

| 模型 | 何时替代 bge-m3 |
|---|---|
| jina-embeddings-v2 | 如果 bge-m3 在法律术语上不够好（未发现） |
| nomic-embed-text | 如果 GPU 显存不足（~0.5GB），但中文弱一倍 |

**结论：bge-m3 保留，不引入多 embedding 模型。单一模型更简单。**

---

## 18. 文件结构

```
ai-os/
├── control-plane/
│   ├── main.py                     # + document routes
│   ├── rag/                        # 新增
│   │   ├── __init__.py
│   │   ├── parser.py               # PyMuPDF 提取
│   │   ├── chunker.py              # 自定义中文 chunker
│   │   ├── embedder.py             # Ollama /api/embed 调用
│   │   ├── store.py                # sqlite-vec 读写
│   │   ├── retriever.py            # token-budget retrieval
│   │   └── db.py                   # SQLite schema + 连接
│   ├── config.py                   # + RAG 配置
│   ├── static/
│   │   └── index.html              # Phase 2b 再改
│   └── services/                   # 不变
```

Phase 2a 所有后端逻辑在 `control-plane/rag/` 目录下，6 个文件，~300 行。
不修改现有代码，不引入前端变更。

---

## 19. Parser Robustness Analysis

### 已知失败模式

| # | 模式 | 触发条件 | 影响 | 缓解 |
|---|---|---|---|---|
| P1 | **Malformed PDF** | 损坏/不完整 PDF 文件 | PyMuPDF 抛出异常 | `try/except` 捕获 → 返回 "文件无法解析" |
| P2 | **PDF 加密/密码保护** | 只读锁定的文档 | PyMuPDF 需要密码参数 | 检测 `needs_pass` → 提示用户 |
| P3 | **字体编码异常** | 非标准编码的 PDF | 提取文本包含乱码字符 | `_normalize_text()` 已覆盖多数情况 |
| P4 | **页眉页脚残留** | 专业文档的复杂页眉 | 页码/章节名混入正文 | `clean_page_text()` 基本过滤 |
| P5 | **中英混排** | 财报/合同 | 格式正常，提取无问题 | 已验证通过 |
| P6 | **表格** | 财报数字表格 | 提取为无结构文本 | 行编号丢失。见 Table Handling 章节 |
| P7 | **扫描页（混合 PDF）** | 部分页为扫描件 | avg < 30 阈值 → 拒稿 | 整篇拒绝。优化：按页检测 |
| P8 | **巨型 PDF（>200 页）** | 招股书/年报 | 处理时间 > 60s | 同步处理尚可接受 |
| P9 | **空白页/分隔页** | 审计报告 | 页提取为空字符串 | `clean_page_text` 已清理 |
| P10 | **多栏布局** | 政策文件/法规汇编 | 文本跨栏混乱 | Phase 2b 使用 `get_text("blocks")` 重排序 |

### 当前已覆盖

```
□  空字节/不可打印字符 → _normalize_text() 清洗
□  Unicode 全角/半角    → translate() 转换
□  页码移除             → clean_page_text() 正则
□  页眉/页脚检测         → 顶部/底部 15% 过滤
□  扫描件检测           → avg < 30 字符/页 阈值
□  文件哈希去重         → SHA256 防止重复导入
```

### 当前不覆盖（可接受）

```
□  多栏布局完美还原      → 需要 PDF 布局分析
□  表格结构化提取        → 见下一节
□  跨页表格合并          → 复杂度过高
□  扫描件 OCR            → 明确不支持
□  图片内文字            → 同 OCR 限制
```

---

## 20. Table Handling Strategy

### 现状

PyMuPDF 的 `get_text("text")` 提取表格时：
- 保留单元格文本，但**丢失行列结构**
- 数字列如 `[1,000, 2,000, 3,000]` → 提取为空格分隔的文本 `1,000 2,000 3,000`
- 表头与表体难以关联

### Phase 2a 策略：接受现状

**不做表格结构化提取。** 接受表格文本作为一个连续的文本片段。

理由：

| 反对复杂的理由 | 说明 |
|---|---|
| 表格 AI 提取需要额外模型 | 增加依赖，与极简原则违背 |
| 表格提取错误 → 误导用户 | 比没有表格更危险 |
| 多数检索场景不依赖表格结构 | "净利润是多少？" → 在表格文本附近也能找到 |

### 实际效果

```
原始表格:
┌─────────┬──────────┐
│ 项目     │ 金额      │
├─────────┼──────────┤
│ 收入     │ 1,000,000 │
│ 成本     │ 600,000   │
│ 净利润   │ 400,000   │
└─────────┴──────────┘

提取为:
项目 金额  收入 1,000,000  成本 600,000  净利润 400,000

检索效果: "净利润是多少？" → 匹配到 "净利润 400,000" ✅
```

### 不做

```
□  表格行列重建           → Phase 2b
□  Table Transformer 模型  → 复杂度爆炸
□  OCR 表格识别            → 不支持 OCR
□  HTML/JSON 表格结构      → 需要额外解析
```

---

## 21. Retrieval Reproducibility

### 测试方法

```python
# 同一 query 查询 10 次，检查 Top-3 结果是否一致
query = "What is the purchase price?"
first_run = retrieve(query)
for i in range(9):
    results = retrieve(query)
    assert results[0]['content'] == first_run[0]['content']
    assert len(results) == len(first_run)
```

### 当前可重复性

| 组件 | 是否确定性 | 说明 |
|---|---|---|
| bge-m3 embedding | ✅ 确定性 | 相同输入 → 相同向量 |
| sqlite-vec cosine search | ✅ 确定性 | 相同向量 → 相同排序 |
| Token budget selection | ⚠️ 确定性 | 相同向量 → 相同 budget 分配 |
| LLM answer generation | ⚠️ 非确定性 | 受温度参数影响（当前使用默认值） |

**结论：检索结果（chunks + sources）是确定性的。** LLM 生成的回答文字可能有差异，但引用来源是一致的。

### 复现保证

```
同一 query + 同一文档集
  → 相同的 chunks（确定性）
  → 相同的 sources（确定性）
  → 相似的回答（非确定性，但基于相同上下文）
```

---

## 22. Benchmark Corpus Design

### 长期基准测试集

| 文档类型 | 数量 | 来源 | 覆盖场景 |
|---|---|---|---|
| 合同（中英文） | 3 份 | 合成 | 条款分割、金额提取、法律引用 |
| 财报/年报 | 3 份 | 公开财报 | 数字提取、表格文本、章节分割 |
| 审计报告 | 2 份 | 合成 | 叙述性段落、结论提取 |
| 政策法规 | 2 份 | 公开法规 | 中文法律条款、多级章节 |
| 银行文件 | 2 份 | 合成 | 数字密集、格式多样化 |

### 每个文档的标准测试

```
□  文档解析是否抛异常？
□  平均每页提取字符数 > 30？（扫描检测）
□  产生 N 个 chunks（N ≥ 页数 / 2）
□  每个 chunk 有非空 content
□  每个 chunk 有 page_num > 0
□  chunk 最大 token 数 < MAX_TOKENS
```

### 检索质量测试

```
□  预定义 20 个 query，覆盖所有文档
□  每个 query 有 "黄金答案"（人工标注）
□  记录: top-1 hit rate, top-3 hit rate
□  记录: source correctness（页码是否准确）
```

### 当前可立即使用的测试

```
test_pipeline.py         — chunker 单元测试
eval_retrieval.py        — 检索评估（5 queries）
debug_chunker.py         — chunker 可视化调试
```

### 基准维护

> 这些基准文档**不存入仓库**（版权问题）。只存储测试脚本 + 预期结果。

---

## 23. Source Trust Evaluation

### 验证层次

| 层次 | 验证内容 | 方法 |
|---|---|---|
| L1 | **文件名正确** | chunk 的 `file_name` 字段来自 `files` 表 |
| L2 | **页码正确** | chunk 的 `page_num` 来自 PyMuPDF 的页编号 |
| L3 | **原文可追溯** | 每个 chunk 的 `content` 直接来自 PDF 提取 |
| L4 | **引用可复现** | 同一 query → 同一 chunks（确定性） |

### 测试方法

```python
def test_source_trust():
    """Verify every source element against its origin."""
    query = "What is the purchase price?"
    chunks = retrieve(query)

    for c in chunks:
        # L1: file exists
        assert exists_in_db(c['file_name'])

        # L2: page number is valid
        assert 1 <= c['page_num'] <= max_pages

        # L3: content is from the actual chunk
        assert content_matches_db(c['content'])

        # L4: reproducibility
        assert c['score'] == previous_score(query, c)
```

### 已知的信任缺口

| 缺口 | 影响 | 当前状态 |
|---|---|---|
| PyMuPDF 提取错误 → chunk 内容有噪音 | 引用内容包含乱码 | `_normalize_text()` 缓解 |
| LLM 可能在回答中添加上下文外的内容 | 用户以为是文档内容 | Prompt 明确要求不编造 |
| 页码可能偏移（PDF 封面页 vs 内容页） | 页码偏差 1-2 页 | 当前从第 1 页开始编页码 |

---

## 24. Complexity Guardrails

### Phase 2a 明确不做

```
□  Semantic chunking        → 自定义正则足够，不引入 AI chunking
□  Reranking                → bge-m3 直接相似度排序已够用
□  Graph retrieval          → 不需要知识图谱
□  Hybrid search            → 关键词 + 向量 = 更复杂，收益未知
□  Query expansion          → 不需要用户问题改写
□  Multi-vector retrieval   → 不需要每个 chunk 多个向量
□  Distributed vector DB    → sqlite-vec 单机足够（< 10万 chunks）
□  Agent / Workflow         → 不需要
□  Multi-user / Auth        → 不需要
□  OCR pipeline             → 不需要
□  Table extraction AI      → 不需要
□  PDF layout reconstruction → 不需要
```

### 当前复杂度上限

```
Parser:     ~60 行  正则清洗 + 扫描检测
Chunker:    ~90 行  正则切割 + 章节保留
Embedder:   ~30 行  Ollama API 调用
Retriever:  ~70 行  Token-budget 检索
Store:      ~70 行  sqlite-vec 读写
DB:         ~40 行  Schema + 连接
Total:      ~360 行
```

**不需要引入任何新框架来保持这个行数。** 每增加一个新功能，必须对应删除同等复杂度的代码。

---

## 25. Retrieval Quality Roadmap

### 已知质量风险

| # | 风险 | 场景 | 影响 | 当前缓解 |
|---|---|---|---|---|
| R1 | **Wrong chunk retrieved** | 相似条款在不同位置 | 回答引用错误条款 | Token-budget 排序 + 多 chunk 召回 |
| R2 | **Partial context** | 条款跨 chunk（overlap=0） | 检索到的 context 不完整 | chunk 自包含设计 |
| R3 | **表格数字歧义** | 财报多行数字 | 检索到"净利润"但无金额 | 表格文本保留在 chunk 中 |
| R4 | **长文档衰减** | 100+ 页文档 | 中间页相关性下降 | bge-m3 8192 context 窗口 |
| R5 | **重复章节** | 多份相似合同 | 检索到错误版本的条款 | SHA256 去重 |
| R6 | **交叉引用丢失** | "如第7.2条所述" | 引用的条款不在同一 chunk | 当前不支持跨 chunk 追踪 |

### 优先级

```
P0（当前已覆盖）:  条款级分割、source引用、文件名+页码
P1（需要加固）:    长文档稳定性、数字检索精度
P2（Phase 2b+）:   表格行列重建、交叉引用追踪、混合检索
```

---

## 26. Long Document Stress Testing

### 测试方法

```python
# 生成 100 页测试文档 → 上传 → 验证 chunking + retrieval
from rag.create_complex_test import create_long_doc
create_long_doc("/tmp/100page-report.pdf", pages=100)

# 上传
result = ingest_file("/tmp/100page-report.pdf", ...)

# 验证
assert result["status"] == "ready"
assert result["chunks"] >= 50     # 100 页至少 50 个 chunks
```

### 验证标准

| 指标 | 目标 | 说明 |
|---|---|---|
| 解析时间 | < 60s | 100 页 PDF |
| Chunk 数量 | ≥ 页数 × 0.5 | 每 2 页至少 1 个 chunk |
| 最大 chunk tokens | ≤ 400 | 不超过上限 |
| Retrieval 响应 | < 5s | 100 页文档的检索时间 |
| Top-3 相关性 | ≥ 80% | 人工标注的黄金 query |

### 模拟文档结构

```
┌─ Cover Page
├─ Table of Contents
├─ Executive Summary
├─ Section 1: Financial Results (20 页)
│   ├─ 1.1 Revenue
│   ├─ 1.2 Cost
│   └─ 1.3 Profit
├─ Section 2: Risk Factors (30 页)
├─ Section 3: Legal Proceedings (15 页)
└─ Appendix (10 页)
```

每个 section 有不同长度和格式，模拟真实年报。

---

## 27. Financial Document Handling

### 当前表现

| 内容类型 | 当前处理 | 预期表现 |
|---|---|---|
| 文本段落 | 自然分割 | ✅ 正确 |
| 结构化编号 (1.1, 1.2) | chunk 内部保留 | ✅ 保留 |
| 数字 (500,000) | 提取为文本 | ✅ 保留 |
| 表格 | 无结构文本 | ⚠️ 行列丢失，但数字保留 |
| 百分比 (30%) | 纯文本 | ✅ 保留 |
| 货币符号 ($, ¥) | 可能被编码污染 | ✅ _normalize_text 修复 |

### 最容易失败的场景

| 场景 | 失败模式 | 影响 | 缓解 |
|---|---|---|---|
| 多列表格 | 列 A 和列 B 的文本混合 | "收入100成本200" → 无法区分 | 当前不做结构化 |
| 跨页表格 | 表格在页尾截断 | 只有部分表格内容被检索 | 无缓解 |
| 财务附注 (注1-50) | 密集编号段落 | chunk 边界可能切断编号 | 当前 chunking 按段落分割 |
| 金额单位 (万/亿) | 文本保留但上下文丢失 | "净利润 5.2亿" → 缺少"单位:人民币" | 需要更大 chunk |

### 不做

```
□  表格 AI 识别
□  数字类型标注（金额 vs 日期 vs 百分比）
□  汇率换算 / 单位转换
□  财务指标计算
```

---

## 28. Citation Precision

### 验证层次

| 层 | 测试 | 方法 |
|---|---|---|
| C1 | 文件名匹配 | `chunk.file_name == uploaded_file.name` |
| C2 | 页码有效 | `1 ≤ chunk.page_num ≤ doc.pages` |
| C3 | 原文可复现 | `retrieve(query)[0].content == retrieve(query)[0].content` |
| C4 | Source snippet 来自 chunk | `snippet in chunk.content` |
| C5 | LLM 未编造 | 在 prompt 中强制要求引用（无法绝对保证，但可检测） |

### 当前覆盖

```
□  C1 文件名:  ✅ 从数据库读取，确定性
□  C2 页码:   ✅ 从 PyMuPDF 页号映射
□  C3 复现性:  ✅ 确定性检索（embedding + cosine = 同结果）
□  C4 snippet: ✅ API 直接返回 chunk.content 的子串
□  C5 LLM 编造: ⚠️ 通过 prompt 约束，但无法硬保障
```

### 测试脚本

```bash
python3 -m rag.benchmark --quick  # 快速验证 C1-C4
```

---

## 29. Benchmark Automation

### 框架设计

```python
# benchmark.py — 单文件，无依赖

def test_parser_robustness():   ...
def test_chunker_english():     ...
def test_chunker_chinese():     ...
def test_chunker_max_tokens():  ...
def test_retrieval_source():    ...
def test_retrieval_repro():     ...
def test_known_queries():       ...

# 每次修改 chunker / parser / retriever 后:
python3 benchmark.py
# → 输出: 7/7 passed
# → 如果 regression: 显示具体失败项
```

### 测试覆盖

| 测试 | 覆盖 | 自动运行 |
|---|---|---|
| `test_parser_robustness` | 空字节、Unicode、空白 | ✅ 每次修改 parser |
| `test_chunker_english` | English Article 分割 | ✅ 每次修改 chunker |
| `test_chunker_chinese` | 中文 第X条 分割 | ✅ 每次修改 chunker |
| `test_chunker_max_tokens` | 无 chunk 超限 | ✅ 每次修改 chunker |
| `test_retrieval_source` | 文件名+页码+内容 | ✅ 每次检索修改 |
| `test_retrieval_repro` | 确定性验证 | ✅ 每次检索修改 |
| `test_known_queries` | 黄金 query 命中率 | ✅ 手动运行 |
| `test_doc_upload` | 上传管道完整性 | 🔄 需要测试 PDF |

### 集成方式

```bash
# 在 Dockerfile 或 CI 中
python3 /app/rag/benchmark.py && echo "All quality checks passed"
```

---

## 30. Complexity Guardrails Recheck

### 当前阶段明确不做

```
□  Reranking               → bge-m3 相似度排序已足够
□  Semantic orchestration   → 不需要 AI 编排
□  Graph retrieval         → 不需要知识图谱
□  Workflow AI             → 不需要
□  Autonomous agents       → 不需要
□  Query expansion         → 不需要改写用户问题
□  Multi-model routing     → 不需要选择 embedding 模型
□  Hybrid search           → 关键词 + 向量 = 更复杂，收益未知
□  Distributed vector DB   → sqlite-vec 单机足够
□  Real-time indexing      → 同步处理已够快
□  Incremental embedding   → 全量重新 embed 文档
□  Table extraction AI     → 接受非结构化表格文本
```

### 当前复杂度（最终版）

```
Parser:     ~60 行   正则清洗 + 扫描检测
Chunker:    ~90 行   正则切割 + 中英章节
Embedder:   ~30 行   Ollama API 套接
Retriever:  ~70 行   token-budget 检索
Store:      ~70 行   sqlite-vec 读写
DB:         ~40 行   schema + 连接
Benchmark:  ~160 行  回归测试（新增）
Total:      ~520 行
```

**每次新增功能，必须删除同等复杂度的代码。**

---

## 31. Real Document Corpus Strategy

### 原则

```
□  不存储受版权保护的原始文档
□  只存储：合成文档生成器 + 标准公开文档的元数据引用
□  每个文档类型附带：测试 queries + 预期黄金答案
□  合成文档应模拟真实文档的结构复杂度
```

### Corpus 结构

```
corpus/
├── registry.json              # 所有测试文档的元数据
├── generators/                # 合成文档生成器
│   ├── contract.py            # 合同（中英文条款）
│   ├── financial_report.py    # 财报（收入表/利润表文本）
│   ├── audit_report.py        # 审计报告（叙述性段落）
│   ├── regulatory.py          # 法规/政策文件
│   └── mixed_lang.py          # 中英混合文档
└── public_refs/               # 公开文档引用（URL + 章节 mapping）
    └── README.md
```

### 每类文档的测试内容

| 文档类型 | 合成尺寸 | 测试重点 | query 数量 |
|---|---|---|---|
| 合同（中英文） | 5-20 页 | 条款分割、金额提取、法律引用 | 10 |
| 财报/年报 | 20-100 页 | 数字提取、章节分割、长文档稳定性 | 10 |
| 审计报告 | 10-30 页 | 叙述性段落、结论提取 | 5 |
| 法规/政策 | 5-50 页 | 多级章节、交叉引用 | 5 |
| 中英混合 | 10-30 页 | 双语混合检索 | 5 |

### 不包含

```
□  真实的内部商业文件
□  受版权保护的法律文库
□  客户数据
□  未公开的财务报告
```

---

## 32. Corpus Diversity Matrix

### 文档维度 vs Pipeline 压力

| 维度 | 压力级别 | 最可能失败点 | 当前抗压能力 |
|---|---|---|---|
| **超长 PDF（>200 页）** | 🔴 高 | 处理时间、embedding 内存 | PyMuPDF 流式读取，无明显瓶颈 |
| **重复页眉（每页不同章节名）** | 🟡 中 | 页眉污染 chunk 内容 | `clean_page_text` 顶部/底部 15% 过滤 |
| **多级编号（1.1.1 / (a)(i)）** | 🟡 中 | chunk 边界切断编号链 | 当前 chunk 自包含，连续编号丢失 |
| **大量表格（财报 50%+ 表格）** | 🔴 高 | 表格文本混乱、行列无法关联 | 接受非结构化文本，数字可检索 |
| **混合中英文** | 🟢 低 | bge-m3 双语支持极好 | 已验证通过 |
| **扫描污染（混合扫描页）** | 🔴 高 | avg < 30 阈值 → 整篇拒绝 | 按页检测扫描件（Phase 2b+） |
| **损坏编码（非标准字体）** | 🟡 中 | 提取文本含乱码 | `_normalize_text()` 覆盖常见情况 |
| **无结构 PDF（纯图片）** | 🔴 高 | avg < 30 → 拒绝 | 明确提示不支持扫描件 |

### 压力测试优先级

```
P0（当前可测）:   超长 PDF、混合中英文、多级编号
P1（需建设）:     大量表格、重复页眉
P2（Phase 3）:    扫描污染、损坏编码、无结构 PDF
```

---

## 33. Retrieval Failure Capture

### Benchmark 之外的失败捕获

| 失败模式 | 触发条件 | 捕获方法 | 严重程度 |
|---|---|---|---|
| **Wrong citation** | LLM 引用了正确的文件名但错误的页码 | 人工 review API response | 🔴 |
| **Partial context** | chunk 边界在段落中间切断 | `benchmark.py test_chunker_max_tokens` | 🟡 |
| **Wrong section** | 语义相似的条款在不同位置被误匹配 | 人工标注的黄金 query + 人工审核 | 🔴 |
| **Retrieval drift** | 同一 query 在不同文档版本下返回不同结果 | `benchmark.py test_retrieval_repro` | 🟡 |
| **Hallucinated source** | LLM 回答中出现了文档中没有的信息 | Prompt 约束（无法硬防止） | 🔴 |

### 生产监控（当前不做）

```
□  User feedback button: "这个回答正确吗？" → Phase 3
□  Retrieval confidence score → Phase 3
□  Automatic A/B testing → 不需要
□  Answer variance tracking → 不需要
```

### 当前方案

```python
# 每次 ingestion 后自动验证
def validate_ingestion(file_id):
    chunks = db.query("SELECT * FROM chunks WHERE file_id = ?", file_id)
    assert len(chunks) > 0, "No chunks produced"
    for c in chunks:
        assert len(c.content) > 10, f"Chunk {c.id} too short"
        assert 1 <= c.page_num <= max_pages, f"Invalid page: {c.page_num}"
```

---

## 34. Benchmark Evolution Strategy

### 扩展路径

```
Phase 2a (当前):   ~50 个测试，覆盖 parser / chunker / retrieval 基础
Phase 2b:           ~100 个测试，增加多文档检索、跨文档查询
Phase 3:            ~200 个测试，增加生产场景、边缘案例、性能基准
```

### 每次代码修改的验证流程

```bash
# 1. 运行快速回归
python3 benchmark.py --quick    # ~10s, 核心测试

# 2. 运行完整套件
python3 benchmark.py            # ~60s, 全部测试

# 3. 运行 corpus 测试（如果有标准文档）
python3 -m corpus.run_all       # ~5min, 黄金文档集
```

### Regression Prevention 原则

```
1. 每次修改 chunker → 必须运行 benchmark.py
2. benchmark.py 不可通过 → 代码不可合并
3. 新增功能 → 必须同时新增 benchmark 测试
4. benchmark 失败数不允许超过当前基线 (0)
```

---

## 35. Source Trust Reinforcement

### 专业用户需要的 traceability

| 信任层 | 当前能力 | 专业用户需求 | 差距 |
|---|---|---|---|
| L1: 来源可见 | ✅ API 返回文件名+页码 | 能看到 chunk 原文 | ✅ 已满足 |
| L2: 原文可查 | ✅ Source snippet 展开 | 能一键定位原文段落 | ⚠️ 需要页码跳转 |
| L3: 检索透明 | ✅ API 返回相关 chunks | 能看到 AI 看到了哪些内容 | ✅ 已满足 |
| L4: 可验证 | ✅ 确定性检索 | 同一问题能得到相同引用 | ✅ 已满足 |
| L5: 可反驳 | ❌ 无此功能 | 用户能说"这个回答不对" | Phase 3 |
| L6: 版本追踪 | ❌ 无此功能 | 文档更新后旧引用仍可追踪 | Phase 3 |

### 当前已满足

```
□  用户可以看到每个引用的 chunk 原文
□  用户可以看到检索到了哪些 chunks
□  同一 query 返回稳定结果
□  文件名 + 页码 + snippet 三位一体
```

### 当前未满足（Phase 3）

```
□  PDF 内搜索定位到具体页码
□  用户反馈标注
□  文档版本对比
□  检索置信度展示
```

---

## 36. Phase 3 Readiness

### 当前系统给专业用户使用还缺什么

| 能力 | 必要性 | 当前状态 | 预计 Phase |
|---|---|---|---|
| 多文档联合检索 | 高 | ✅ 已支持（`file_ids` 参数） | ✅ 当前 |
| 文档删除 | 高 | ✅ 已支持 | ✅ 当前 |
| PDF 原文预览 | 高 | ❌ Dashboard 无 PDF 预览 | Phase 2b |
| 页码跳转 | 中 | ❌ 无法在 PDF 中定位到引用页 | Phase 2b |
| 文档版本对比 | 低 | ❌ 无对比功能 | Phase 3+ |
| 用户反馈标注 | 中 | ❌ 无法标记"回答正确/错误" | Phase 3 |
| 批量上传 | 低 | ❌ 一次只传一个文件 | Phase 3+ |
| 检索置信度 | 中 | ❌ 无分数展示 | Phase 3 |
| API 鉴权 | 低 | ❌ 无认证 | Phase 3+ |
| 审计日志 | 低 | ❌ 无操作记录 | Phase 3+ |

### Phase 3 不做（明确边界）

```
□  Enterprise SSO / LDAP
□  高可用 / 负载均衡
□  分布式部署
□  多租户 / 工作空间
□  Workflow / 审批流程
□  Agent / 自动执行
□  云端同步
□  移动端 APP
```

### 一句话结论

> **当前系统在技术能力上已可交付专业用户使用。**
> 缺失的主要是 **UI 层面的精细度**（PDF 预览、页码跳转、反馈标注），
> 而不是 **核心检索能力**。

### 建议的下一个用户测试关注点

```
□  专业用户能否理解 "source citation" 的使用方式？
□  用户是否会点击展开 source snippet 验证答案？
□  PDF 预览是否是必需品，还是 source snippet 就足够？
□  用户最常问的 10 个问题是什么类型？
□  用户是否会因为 LLM 编造内容而失去信任？
```
