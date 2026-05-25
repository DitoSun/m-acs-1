# 已知限制

当前版本：Phase 1.5（2026.05）

---

## 平台限制

| 限制 | 说明 | 计划 |
|---|---|---|
| **仅支持 Ubuntu 22.04 / 24.04** | install.sh 仅测试了这两个版本 | Phase 2+ |
| **仅支持 NVIDIA GPU** | 依赖 CUDA / nvidia-container-toolkit | 路线图中 |
| **不支持 ARM 架构** | 未测试树莓派 / Apple Silicon | 未计划 |
| **WSL2 兼容性** | 功能可用但功耗读数为 N/A | 已记录 |

## 网络限制

| 限制 | 说明 | 状态 |
|---|---|---|
| **Docker Hub 在中国受限** | 已添加 DaoCloud mirror 作为 fallback | ✅ 已解决 |
| **ghcr.io 访问性** | Open WebUI 从 ghcr.io 拉取，部分网络不可达 | Open WebUI 默认禁用 |
| **Ollama registry 可能限速** | 大模型下载可能较慢 | 已提示用户 |
| **不支持离线安装** | 需要首次联网下载 | Phase 4 计划 |

## 功能限制

| 限制 | 说明 |
|---|---|
| **Open WebUI 默认不安装** | 在 `docker-compose.yml` 中取消注释即可启用 |
| **Dashboard 仅限单用户** | 无登录 / 无多用户支持 |
| **Chat 为轻量测试功能** | 不支持多会话、Markdown 渲染、文件上传 |
| **无知识库 / RAG** | Phase 2 |
| **无模型进度 ETA** | 安装进度条显示百分比但无剩余时间估算 |
| **无系统资源面板** | 不显示 CPU / 内存 / 磁盘使用率 |
| **无卸载脚本** | 手动 `docker compose down` + 删除目录即可 |

## 硬件限制

| 限制 | 说明 |
|---|---|
| **VRAM 决定模型上限** | 8GB 显存 → 7B 模型；24GB → 70B 模型（取决于量化方式） |
| **WSL2 下功耗读数异常** | `power_limit_w` 字段始终为 0（GPU 虚拟化限制） |
| **多 GPU 未优化** | 默认使用第一块显卡，未做负载均衡 |

## 已知 Bug

| Bug | 状态 | 说明 |
|---|---|---|
| GPU JSON 文件写入时读取冲突 | 概率极低 | `os.replace` 原子写入基本避免 |
| `DELETE /api/delete` 返回 500 | 仅发生于模型不存在时 | 前端可正常处理 |
