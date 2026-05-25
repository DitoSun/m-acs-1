# M-ACS-1 Stable Observation Manifesto

8048 行代码。60 个文件。12 份哲学文档。0 个待开发功能。

---

## 1. 当前最重要的能力已经不是软件开发，而是系统观察

```
0 -> v0.1.0 的开发阶段需要: coding ability
v0.1.0 -> v0.2.0 的观察阶段需要: observation discipline

coding 回答 "what"（系统能做什么）
observation 回答 "why"（用户为什么用/不用）

v0.1.0 的功能集已经足够回答一个问题:
  「专业用户是否愿意使用本地部署的文档分析工具？」

这个问题不能通过加功能来回答。
只能通过观察真实用户行为来回答。
```

相关文档：[DOCTRINE.md §1](./DOCTRINE.md)

---

## 2. Identity Drift 的早期信号

```
最能掩盖 identity drift 的 feature request:

"只是加个小功能" → 累积成 bloated platform
"用户要求了" → 1 个用户 ≠ 真实需求
"竞品有这个" → 我们不是竞品
"先加上以后优化" → 代码从不被删除
"这不需要多少代码" → 每个功能都这么说

M-ACS-1 的四根支柱:
  本地 · 可信 · 低复杂度 · 文档优先

任何新功能必须通过 5 问检查 (DOCTRINE.md §4):
  1. 用户还会说这是本机工具吗？
  2. 需要新基础设施吗？
  3. 代码增长 > 20% 吗？
  4. 10 个独立用户要求了吗？
  5. 不做的真实风险是什么？
```

相关文档：[DOCTRINE.md §4](./DOCTRINE.md)，[SIGNAL_TAXONOMY.md §3](./SIGNAL_TAXONOMY.md)

---

## 3. 复杂度预算

```
预算        当前     上限    突破后果
────────────────────────────────────────
LOC         8048    9000    代码失控
Docker 服务  3       3       运维复杂度倍增
Python 依赖  8       12      依赖冲突
运行时进程   3       4       资源竞争
API 端点     16      25      API 混乱
数据库表     3       6       迁移困难

预算就是预算。没有例外。
超过 = 冻结新功能 = 直到回到预算内。
```

相关文档：[DISCIPLINE.md §4](./DISCIPLINE.md)

---

## 4. Workflow Emergence 的观察

```
最值得观察的不是用户说了什么，而是用户反复做了什么。

Workflow 类型            含义                      优先级
──────────────────────────────────────────────────────────
上传 → 提问 → 离开       搜索引擎替代                核心场景
上传 → 深度分析          专业知识工作                定位验证
上传多份 → 跨文档提问    需求超出单文档              方向信号
检索 → 展开 source       用户验证                信任验证
截图发给同事             用户传播                社会信任
每天使用                 习惯形成                产品粘性

一个 workflow 固化的判定:
  7 天内回访 ≥ 3 次 + 持续 2 周 + 每次时长不减
```

相关文档：[DOCTRINE.md §5](./DOCTRINE.md)，[SIGNAL_TAXONOMY.md §1](./SIGNAL_TAXONOMY.md)

---

## 5. Retrieval Trust 的核心地位

```
M-ACS-1 与通用 AI 产品的根本区别:

  ChatGPT:   黑盒生成 → 用户无法验证
  M-ACS-1:  检索 → 引用 → 用户可验证

这就是为什么 source traceability 和 deterministic retrieval
不是功能特性，而是产品 identity 的核心组成部分。

宁可 "文档中未提及"，不可编造。
宁可空，不可错。

一次错误的 citation，可能永远失去一个专业用户。
```

相关文档：[PHASE2a.md §23](./PHASE2a.md)，[FRAMEWORK.md §4](./FRAMEWORK.md)

---

## 6. 打破 Guardrails 的唯一条件

```
1 次信号 → 记录，不行动
3 次信号 → 确认模式，不行动
10 次信号 → 进入决策流程

同一方向累计权重 ≥ 500 + identity 检查通过 + 预算有余量
→ 才考虑打破当前 guardrails

以下情况永远不能打破:
  □  功能很酷
  □  竞品有
  □  一个人强烈要求
  □  技术很新
  □  投资人说应该做

产品演化由信号驱动，不是由冲动驱动。
```

相关文档：[DISCIPLINE.md §2](./DISCIPLINE.md)，[SIGNAL_TAXONOMY.md §5](./SIGNAL_TAXONOMY.md)

---

## 当前状态

```
M-ACS-1 v0.1.0
60 个文件，8048 行代码
3 个服务，8 个依赖
0 个待开发功能

阶段: Stable Observation State
等待: 第一批真实专业用户的自然 workflow

项目最成熟的不是代码，是 philosophy:
  └─ 本地优先 · 可信优先 · 低复杂度 · 文档优先
```
