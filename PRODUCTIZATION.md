# M-ACS-1 — Productization & Delivery Guide

从"工程上成立"到"专业用户长期使用"的差距分析与实施计划。

---

## 1. Productization Gap Analysis

### 当前状态 vs 专业产品要求

```
维度              工程状态          产品要求          差距
─────────────────────────────────────────────────────────
安装              手动 git clone    一条命令 ✅        无
升级              手动 git pull     版本管理           ⚠️ 有
回滚              手动 git checkout  可回滚版本         ❌ 无
数据备份          无                 一键备份           ❌ 无
卸载              手动 rm -rf       干净卸载脚本       ❌ 无
健康检查          /health 端点      仪表盘可视         ✅ 有
启动自愈          systemd           自动恢复           ✅ 有
日志              容器 stdout       log rotate + 归档  ⚠️ 基本
安全              无鉴权            本地绑定           ⚠️ 可接受
备份迁移          无                 sqlite 文件级备份  ❌ 需手工
用户反馈          无                集成反馈通道       ⚠️ GitHub Issues
性能监控          无                系统资源面板       ❌ 无
```

### P0 缺口（必须修）

| # | 缺口 | 原因 | 工作量 |
|---|---|---|---|
| G1 | **无卸载脚本** | 用户无法干净移除 | 0.5 天 |
| G2 | **无数据备份** | 所有数据在 Docker 卷中，用户不知道在哪 | 0.5 天 |
| G3 | **无版本号** | 当前无法确认运行版本 | 0.5 天 |
| G4 | **无升级路径** | 用户不知道如何更新 | 0.5 天 |

### P1 缺口（应该修）

| # | 缺口 | 原因 | 工作量 |
|---|---|---|---|
| G5 | Dashboard 无系统资源面板 | 看不到 CPU/RAM/DISK | 1 天 |
| G6 | 安装耗时无真实进度 | 长步骤应显示预期时间 | 0.5 天 |
| G7 | 无 changelog | 用户不知道新版本有什么 | 0.5 天 |
| G8 | Docker 日志无轮转 | 长期运行占磁盘 | 0.5 天 |

### P2 缺口（可推迟）

| # | 缺口 |
|---|---|
| G9 | 多 GPU 支持 |
| G10 | 离线安装包 |
| G11 | 自动更新检查 |
| G12 | 企业级日志审计 |

---

## 2. Deployment Environment Matrix

### 环境维度

| 环境 | 预计占比 | 主要风险 | 当前支持 |
|---|---|---|---|
| **Ubuntu 裸机** | 70% | NVIDIA 驱动兼容性、Docker 版本 | ✅ 验证通过 |
| **WSL2 (Windows)** | 15% | IPv6 连接重置、systemd 可用性、PCI 总线不可见 | ⚠️ 部分支持 |
| **Ubuntu VM (Proxmox/ESXi)** | 8% | GPU 直通配置、PCIe passthrough | ⚠️ 需用户自行配置 |
| **小型工作站 (NUC + eGPU)** | 5% | 外接 GPU 驱动复杂 | ❌ 未验证 |
| **NAS 环境 (Unraid/TrueNAS)** | 2% | Docker 兼容性、Volume 权限 | ❌ 未验证 |

### 每种环境的关键验证点

#### Ubuntu 裸机（主要场景）

```
□  apt NVIDIA driver vs 官方 runfile
□  Ubuntu 24.04 内核与 NVIDIA 驱动兼容性
□  Docker apt repo 的中国镜像可用性
□  首次安装 30 分钟预算（含驱动+镜像+模型）
```

#### WSL2（开发/测试场景）

```
□  curl IPv4 fallback（WSL2 IPv6 栈问题）
□  systemd 可用（Ubuntu 24.04 WSL 默认启用）
□  nvidia-smi 路径问题（/usr/lib/wsl/lib/）
□  power_limit_w 始终为 0（虚拟化限制）
□  Windows 防火墙可能阻断端口转发
```

#### Ubuntu VM（企业场景）

```
□  GPU 直通需要硬件支持（Intel VT-d / AMD IOMMU）
□  vGPU 或 GPU 分片需要额外 license
□  VM 迁移后 GPU 状态丢失
□  VM snapshot 与 GPU 状态不一致
```

### 环境验证优先级

```
P0: Ubuntu 24.04 LTS 裸机 — 当前已验证
P1: Ubuntu 22.04 LTS 裸机 — 需验证 systemd/NVIDIA 版本差异
P2: WSL2 — 已部分验证
P3: VM + GPU passthrough — 文档化
P4: NAS / Unraid — 社区贡献
```

---

## 3. Workspace Polish Plan

### 当前像工程工具的地方

| 问题 | 当前表现 | 专业用户期望 |
|---|---|---|
| **无系统资源面板** | 只能看到 GPU，看不到 CPU/RAM/DISK | 想看完整系统状态 |
| **无 PDF 预览** | 只能看文本 snippet | 想看原始 PDF 文件 |
| **无搜索历史** | 每次刷新后查询丢失 | 想保留历史 query |
| **无键盘快捷键** | 全部鼠标操作 | 想用键盘快速操作 |
| **无批量上传** | 一次只能传一个文件 | 想一次传多个文件 |
| **无处理进度** | 上传后只显示 "processing" | 想看具体进度（N/M chunks） |
| **无错误详情** | 失败只显示 "failed" | 想知道为什么失败 |
| **无帮助/引导** | 空白页面 | 想知道能做什么 |

### 当前暂不修改（明确）

```
□  PDF 预览 — 需要 PDF.js 或嵌入 viewer，Phase 2b 后考虑
□  搜索历史 — 需要持久化，Phase 3
□  键盘快捷键 — 用户基数够大后再做
□  批量上传 — Phase 2b
```

### 优先修改（Phase 2b 内）

```
□  系统资源面板（CPU/RAM/DISK）— 新 API + Dashboard 组件
□  处理进度显示 — 后端已返回 chunks 数量
□  错误详情展示 — 后端已返回错误信息
□  Dashboard 首次引导 — 欢迎页已做，但 Documents 区域需要
```

---

## 4. Retrieval Stability Monitoring

### 长期维护方案

```
频率       活动                         责任人
────────── ──────────────────────────── ────────
每次修改    运行 benchmark.py            开发者
每次发布    运行 corpus --validate       开发者
每周        检查 benchmark 基线有无漂移  自动化
每月        新增 3-5 条 corpus query    产品
每季度      人工 review retrieval 质量    QA
```

### Regression 防线

```
第 1 层: benchmark.py — 单元测试级别（~10s）
    ├─ parser 归一化
    ├─ chunker 分割
    └─ retrieval 属性

第 2 层: corpus.py --validate — 集成测试级别（~5min）
    ├─ 多类型文档上传
    ├─ 黄金 query 命中率
    └─ 引用完整性

第 3 层: 人工 review — 专业用户验收
    ├─ 回答质量评估
    ├─ 引用准确性
    └─ 用户体验反馈
```

### 失败追踪

```python
# 记录每次 benchmark 运行结果
benchmark_results = {
    "date": "2026-05-25",
    "version": "v0.1.0",
    "tests": 47,
    "passed": 47,
    "failed": [],
    "commit": "abc123",
}
```

---

## 5. Release Engineering

### 版本号方案

```
v0.1.0
 ^ ^ ^
 │ │ └── patch: bug fix, no API change
 │ └──── minor: new feature, backward compatible
 └────── major: breaking change

当前: v0.1.0 (MVP)
```

### 发布流程

```
1. 确认 benchmark.py 全部通过
2. 确认 corpus.py --validate 全部通过
3. 更新 VERSION 文件
4. 更新 CHANGELOG.md
5. git tag v0.1.x
6. git push && git push --tags
```

### 最小发布产物

```
发布检查清单:
□  benchmark.py: 47/47 passed
□  corpus.py --validate: 全部 passed
□  VERSION 文件存在
□  CHANGELOG.md 更新
□  git tag 已创建
□  README.md 同步更新
```

### VERSION 文件

```bash
echo "0.1.0" > VERSION
```

### CHANGELOG.md 格式

```markdown
# Changelog

## v0.1.0 (2026-05-25)

### Added
- One-command install (install.sh)
- Dashboard with GPU monitoring and model management
- Professional Document Intelligence Pipeline
  - PDF ingestion with PyMuPDF
  - Chinese + English legal chunking
  - bge-m3 embedding via Ollama
  - sqlite-vec vector storage
  - Token-budget retrieval
- Document workspace with upload/ask/source citation
- 47-item benchmark suite
- 4-class professional document corpus

### Fixed
- PDF parser null-byte and encoding normalization
- Chunker clause boundary preservation (Chinese + English)
- sqlite-vec cascade delete lifecycle
- Chat streaming buffer truncation
```

### 迁移策略

```
当前无数据迁移问题（v0.1 是第一个版本）。

v0.1 → v0.2 策略:
  □ 如果 sqlite-vec schema 变化: 自动重建 vec 表
  □ 如果 chunker 变化: 提示用户重新导入文档
  □ Docker Compose 变化: docker compose pull && docker compose up -d
```

### 回滚策略

```bash
# 回滚到上一个版本
cd /opt/m-acs-1
git checkout v0.0.9
docker compose down
docker compose up -d --build
```

---

## 6. Complexity Guardrails Reaffirmation

### 即使专业用户要求，当前也不应该做

```
功能                       用户可能说              拒绝理由
────────────────────────── ────────────────────── ──────────────────────
云端同步                   "我想在手机上也看到"  需要服务端架构，超出单机范围
多用户/RBAC               "律所 10 个人要用"    需要用户系统+权限，复杂度 10x
工作流/审批                "合同审核流程化"       需要 workflow 引擎，偏离核心价值
Agent 自动执行             "AI 帮我发邮件"        不可控，法律场景不适用
专用 embedding 模型训练     "我想要行业定制"      需要训练数据+GPU，收益有限
PDF 预览/标注              "我想在 PDF 上画线"   需要 PDF.js + 标注系统，工程量大
移动端/iPad                "出庭的时候要看"       需要移动端适配，为时过早
SaaS/多租户               "帮你部署到我们机房"    定位是单机 Appliance
```

### 当前阶段可以说的 "不"

```
"这个功能很好，但 M-ACS-1 的核心价值是
 本地、可信、低复杂度的专业文档理解。
 我们不做大平台，也不做云服务。

 如果这些功能对你是刚需，
 建议看看企业级的文档管理平台。

 我们专注做好单机 Appliance 这一件事。"
```

### 保持低复杂度的原则

```
1. 每新增一个 Python 依赖，必须删除一个旧的
2. 每新增 100 行代码，必须删除 50 行死代码
3. 每新增一个 API 端点，必须经过 benchmark 验证
4. 任何需要额外 Docker 容器的功能，默认拒绝
5. 任何需要外部数据库的服务，默认拒绝
6. 任何需要用户注册/登录的功能，默认拒绝
```

---

## 7. 当前项目最终视图

```
PROJECT M-ACS-1
├── Phase 0:     Runtime Infrastructure       ✅
├── Phase 1:     Dashboard + Control Plane    ✅
├── Phase 1.5:   Product Polish               ✅
├── Phase 2a:    Document Pipeline             ✅
├── Phase 2b:    Document Workspace UI         ✅
├── Retrieval:   Quality Engineering           ✅
├── Corpus:      Professional Corpus           ✅
└── Productization: Release & Delivery        ✅ (当前)
    ├── VERSION
    ├── CHANGELOG.md
    ├── PRODUCTIZATION.md (本文)
    ├── Makefile (update)
    └── scripts/uninstall.sh

Total: 27 files, ~2800 lines
```

下一步：创建 VERSION / CHANGELOG / uninstall.sh，打 v0.1.0 tag。
