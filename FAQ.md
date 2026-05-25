# 常见问题

## 安装相关

### 安装花了多久？

正常情况 5-15 分钟。中国大陆用户可能需要 10-30 分钟（取决于镜像速度）。绝大部分时间花在下载 Docker 镜像上。

### 提示 "REBOOT REQUIRED" 怎么办？

NVIDIA 驱动安装后需要重启。运行 `sudo reboot` 重启电脑，重启后再次运行 `sudo ./install.sh`，脚本会从上次中断的地方继续。

### 安装到一半断了怎么办？

直接重新运行 `sudo ./install.sh`。脚本是幂等的——已完成的步骤会自动跳过，不会重复执行。

### 提示 "No NVIDIA GPU detected" 但我明明有显卡

可能原因：
1. 显卡驱动未安装 —— 运行 `lspci | grep -i nvidia` 确认是否能检测到
2. WSL2 环境下 —— 确认 Windows 上已安装最新的 NVIDIA 驱动，且 WSL2 已启用 GPU 加速
3. 显卡直通给虚拟机 —— 需要物理机安装

### 支持 AMD 显卡吗？

不支持。仅支持 NVIDIA CUDA 显卡。

### 可以在 Windows 上直接运行吗？

推荐使用 WSL2（Windows Subsystem for Linux）：
1. 安装 WSL2：`wsl --install -d Ubuntu`
2. 安装 Windows NVIDIA 驱动（最新版）
3. 在 WSL2 中运行 `sudo ./install.sh`

---

## Dashboard

### 为什么 GPU 面板显示 "Offline"？

可能原因：
1. GPU 监控服务未运行 —— 检查 `systemctl status m-acs-host-agent`
2. 显卡驱动问题 —— 运行 `nvidia-smi` 确认
3. WSL2/WM 环境下可能无法读取所有 GPU 指标

### 为什么 AI Engine 显示 "offline"？

Ollama 服务未运行。系统会自动尝试恢复。如果持续 offline，运行：
```bash
cd /opt/m-acs-1 && docker compose restart ollama
```

### 显存使用率一直很高？

Ollama 默认会保持模型在显存中 24 小时（`OLLAMA_KEEP_ALIVE=24h`），避免重复加载。这是正常行为。如果不需要，可以修改 `docker-compose.yml` 中的 `OLLAMA_KEEP_ALIVE` 值。

### 模型名后面的 Q4_K_M 是什么意思？

这是模型的量化方式。Q4_K_M 表示 4-bit 量化，是质量和体积的平衡选择。量化后的模型占用空间更小、运行更快，但质量略有损失。

---

## 模型

### 怎么知道该装哪个模型？

| 模型 | 大小 | 用途 |
|---|---|---|
| qwen2.5:0.5b | 397 MB | 快速测试，性能有限 |
| llama3.2:3b | ~2 GB | 通用对话 |
| deepseek-coder:6.7b | ~4 GB | 代码生成 |
| qwen2.5:7b | ~4 GB | 中文对话 |
| llama3.1:8b | ~4.7 GB | 英文通用，质量高 |

建议首次安装从 **Quick Start（qwen2.5:0.5b）** 开始，验证系统正常工作后再安装更大的模型。

### 模型下载到一半能中断吗？

可以。但下次需要重新安装。

### 模型文件存在哪里？

Docker 卷中：`ollama_data`。运行 `docker volume inspect m-acs-1_ollama_data` 查看实际路径。

### 模型会不会泄漏到互联网？

不会。所有模型在本地运行，数据不会离开你的电脑。Dashboard 绑定在 `127.0.0.1`（仅本机可访问）。

---

## 网络

### 为什么安装脚本提示 "Docker Hub unreachable"？

中国大陆网络环境下，Docker Hub 经常被阻断。安装脚本会自动使用国内镜像（DaoCloud / 阿里云），正常情况下可以正常下载。

### 模型下载速度很慢

Ollama 模型托管在 `registry.ollama.ai`，在中国大陆可能限速。建议：
1. 先安装小模型（qwen2.5:0.5b，397MB）验证系统
2. 大模型（7B/8B）下载需要较长时间（10-30 分钟）
3. 考虑使用代理

### 支持代理吗？

当前安装脚本会自动检测网络并切换镜像。如果需要通过 HTTP 代理安装：
```bash
sudo http_proxy=http://your-proxy:port https_proxy=http://your-proxy:port ./install.sh
```
