# Post-Release Observation — v0.1.0

发布后的观察策略：看用户怎么用，不主动加功能。

---

## 1. Post-Release Observation Plan

### 观察维度

```
Install      → 用户能否走完安装流程？
Dashboard    → 用户理解系统状态吗？
Document     → 用户上传了什么类型的文件？
Retrieval    → 用户问的问题检索到了吗？
Trust        → 用户信任 AI 的回答吗？
Stability    → 系统在真实环境下稳定吗？
```

### 具体观察项

| 观察点 | 信号 | 收集方式 |
|---|---|---|
| **安装成功率** | install.sh exit 0 或报错 | collect-debug.sh 输出 |
| **安装耗时** | clone → Dashboard 可访问的时间 | 用户自报 |
| **首次模型安装** | 用户选择了哪个推荐模型 | 用户反馈 |
| **上传文档类型** | PDF 是合同/财报/法规/其他 | GitHub Issues + 文件名推断 |
| **常见 query** | 用户问了什么问题 | GitHub Issues / FEEDBACK |
| **检索失败** | 用户说"没找到" 或 "不准确" | GitHub Issues |
| **引用信任** | 用户是否展开 source snippet 验证 | 当前无法追踪（Phase 3 加） |
| **Benchmark 退化** | 新发现的分词/检索问题 | `benchmark.py` 定期运行 |
| **系统稳定性** | Docker 容器重启、磁盘使用 | 用户报告 |

### 不主动收集（隐私）

```
□  不上传用户的文档
□  不记录用户 IP
□  不记录用户 query
□  不使用任何 analytics SDK
□  所有数据保留在用户机器上
```

---

## 2. Real-World Failure Intake

### 反馈处理流程

```
用户提交 Issue
    │
    ├─ 模板引导: 运行 collect-debug.sh
    │   └─ 自动包含: 硬件/网络/容器/日志信息
    │
    ▼
开发者分类
    │
    ├─ Install Failure (T1-T8)
    │   └─ 修复 install.sh / 更新文档
    │
    ├─ Retrieval Failure
    │   ├─ Source mismatch     → 检查 chunker 边界
    │   ├─ Wrong citation      → 检查 page_num 映射
    │   ├─ Malformed PDF       → 检查 parser 错误处理
    │   └─ Retrieval drift     → 运行 benchmark 验证
    │
    ├─ Deployment Issue
    │   ├─ Ubuntu version mismatch  → 更新兼容性矩阵
    │   ├─ GPU driver problem      → 更新 NVIDIA 检测
    │   └─ Docker change           → 更新 docker-compose
    │
    └─ UX Confusion
        └─ 更新 FAQ / README / Dashboard 文案
```

### Retrieval Failure 优先级

```
严重度                     处理响应时间
─────────────────────────────────────────
回答明显错误 + 引用不存在  → 24h 内确认
检索不到正确条款            → 48h 内确认
引用页码不对                → 72h 内确认
LLM 编造内容                → 立即确认 prompt 约束
```

### 失败复现标准

```
要处理一个 retrieval failure，必须满足:
□  提供 PDF 文件（或等价的合成文件）
□  提供 query
□  提供预期正确回答
□  提供实际检索结果（API 原始输出）
```

---

## 3. Deployment Stability Tracking

### v0.1.0 已知风险（按概率排序）

| # | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| D1 | **Ubuntu 24.04 内核更新后 NVIDIA 驱动不兼容** | 中 | nvidia-smi 不可用 | install.sh 检测驱动版本 |
| D2 | **用户手动升级 Docker 后 compose v2 不可用** | 中 | docker compose 命令失败 | Makefile 中封装检测 |
| D3 | **中国大陆 ghcr.io 访问超时** | 中 | Open WebUI 无法拉取 | 默认注释掉，可选 |
| D4 | **Ollama 镜像更新导致 API 变化** | 低 | `/api/embed` 格式变化 | 版本固定 `ollama:0.3.12` |
| D5 | **用户误删 Docker 卷** | 中 | 模型+数据库丢失 | FAQ 中说明备份方式 |
| D6 | **系统磁盘写满（模型太大）** | 中 | Docker 无法写入 | FAQ 中说明空间要求 |
| D7 | **用户在内网环境无网络安装** | 低 | 镜像拉取失败 | 文档说明需要首次联网 |
| D8 | **WSL2 文件权限问题** | 低 | install.sh 执行权限 | Ubuntu 24.04 WSL 已验证 |

### 每个 Issue 需要确认

```
对于每个部署问题，需要确认:
□  OS: Ubuntu 版本 + 内核版本
□  GPU: 型号 + 驱动版本
□  Docker: 版本 + compose 版本
□  网络: 中国大陆/海外/内网
□  容器: docker compose ps 输出
```

---

## 4. Benchmark Evolution Strategy

### v0.1.x 阶段的 benchmark 策略

```
频率: 每周运行一次完整 benchmark
目标: 始终保持 47/47 passed

如果 benchmark 退化:
1. 确认是否是因为代码修改
2. 如果是因为真实文档暴露了新的边界情况: 新增测试用例
3. 修复退化
4. benchmark 回到基线
```

### 测试用例增长计划

```
v0.1.0:  47 个测试（当前）
v0.1.x:  50-60 个测试（根据真实用户反馈新增）
v0.2.0:  80-100 个测试（覆盖新能力）
```

### 新增测试用例的来源

```
真实用户反馈 → 解析失败 → 新增 parser 测试
真实用户反馈 → chunk 错误 → 新增 chunker 测试
真实用户反馈 → 检索不对 → 新增 query 测试
真实用户反馈 → source 错误 → 新增引用测试
```

### Regression Prevention 流程

```bash
# 开发者修改代码后的标准流程
python3 benchmark.py           # 全部通过？
python3 corpus.py --validate   # 全部通过？
git add ...

# CI gate（当前无 CI，手动执行）
# 每次 release 前必须运行
```

---

## 5. Product Identity Protection

### 即使用户提出，当前也应该拒绝的功能

| 功能 | 用户可能的理由 | 拒绝原因 | 替代方案 |
|---|---|---|---|
| **云端同步** | "我想在公司电脑和家里都能用" | 需要云服务后端，偏离本地 Appliance 定位 | 用户自行用网盘同步 `/rag` 目录 |
| **多用户** | "我们团队 3 个人要用" | 需要用户系统、权限、session 管理 | 每人一台机器，或写在共享机器上用同一个账号 |
| **PDF 标注** | "我想在 PDF 上画线标记" | 需要 PDF 渲染引擎+标注系统 | 导出原文到本地 PDF 阅读器操作 |
| **移动端** | "我想在手机上查文档" | 需要移动端适配 | 通过 SSH 隧道在手机浏览器访问 |
| **Agent/自动执行** | "AI 帮我自动审合同" | 法律场景不可自动决策 | 当前只做辅助分析，不做自动执行 |
| **工作流/审批** | "合同审核需要流程" | 需要 workflow 引擎，10x 复杂度 | 使用专业的合同管理系统 |
| **大模型训练** | "我想用自己的数据微调" | 需要训练 infra，不是这个产品的方向 | 使用 Colab / RunPod 等训练平台 |
| **企业 SSO** | "我们公司用 Okta 登录" | 企业级功能，当前不适用 | 单机场景不需要 |

### 核心 Identity 原则

```
M-ACS-1 不是一个平台。
它是一台「专业文档智能 Appliance」。

它的核心 identity 是:
  「本地、可信、低复杂度」
  
不是:
  「云端、协作、全功能」
```

### 决策检查清单

```
当考虑是否添加一个功能时，问这三个问题:

1. 这个功能需要额外的基础设施吗？
   (数据库/云服务/新运行时) → 拒绝

2. 这个功能需要用户注册/登录吗？
   → 拒绝

3. 这个功能会让代码行数翻倍吗？
   → 拒绝

如果三个问题都是「不」——才考虑。
```

---

## 6. v0.2.0 Decision Signals

### 什么时候考虑 v0.2.0

**只有以下信号出现 3 个以上，才启动 v0.2.0：**

```
信号 1: 超过 10 个活跃用户重复使用（不只是装完试试）
信号 2: GitHub Issues 中出现同一功能请求超过 3 次
信号 3: 发现 benchmark 无法覆盖的系统性检索失败
信号 4: 用户明确表示 "我愿意付费买更多功能"
信号 5: 同一个文档类型（如财报）出现超过 5 个用户
```

### v0.2.0 候选方向（当前仅研究，不承诺）

```
方向 A: PDF 分析增强
  触发条件: OCR / 表格 / 图片提取频繁出现
  复杂度: 中（引入 PaddleOCR 或开源表格模型）

方向 B: Advaned Retrieval
  触发条件: benchmark 显示检索精度不足
  复杂度: 低-中（引入 hybrid search / reranking）

方向 C: 专业工作空间
  触发条件: 用户需要多文档联合分析
  复杂度: 中（改进 UI）

方向 D: 跨文档推理
  触发条件: 用户需要比较多个文档
  复杂度: 中（多文档 query）

方向 E: 团队协作
  触发条件: 超过 3 个团队要求
  复杂度: 高（引入多用户）
```

### 不应该驱动 v0.2.0 的信号

```
□  你觉得 "这个功能很酷"
□  投资人要求 "加 AI 功能"
□  竞品做了某个功能
□  某个 KOL 在社交媒体上提了建议
□  一个人重复提了同一个需求（除非是付费客户）
```

### 决策原则

```
v0.1.x 阶段只做:
  □  Bug 修复
  □  文档改进
  □  Benchmark 扩展
  □  安装兼容性

v0.2.0 只做:
  □  基于真实用户使用数据
  □  至少 3 个独立用户/团队验证过的方向
  □  不超过 20% 的代码增长
```

---

## 总结

```
Phase               Status
──────────────────────────────────────────
v0.1.0 发布         ✅  2026-05-25 已发布
Post-Release        ✅  当前阶段
  └─ 观察 + 修复     →  持续
  └─ 不新增功能       →  原则
  └─ 收集信号         →  决定 v0.2.0

下一步: 看用户反馈，等信号，不冲动。
```
