# M-ACS-1 — Your Private AI Server

**把一台 Ubuntu 电脑变成你私有的 AI 服务器。**

插电，运行一条命令，打开浏览器，开始聊天。不需要配置云服务，不需要注册账号，不需要折腾 GPU 驱动。

```
裸 Ubuntu 机器
    ↓ git clone && sudo ./install.sh
    ↓ ~15 分钟
浏览器打开 http://localhost:8080
    ↓ 点一下装模型
开始对话
```

---

## 为什么做这个

本地 AI 已经足够好了，但部署体验还很糟糕。

如果你想在本地跑 Llama 或 Qwen，你需要：
1. 搞懂 NVIDIA 驱动和 CUDA 版本
2. 安装 Docker 并配置 GPU 加速
3. 手动拉 Ollama、配 systemd、写 docker-compose
4. 装个 Open WebUI 或者自己写前端
5. 每次想换个模型都要敲命令

**这个过程对绝大多数人来说不可接受。** M-ACS-1 把这 5 步变成了一条命令。

---

## Quick Start

### 你需要

- 一台装了 **Ubuntu 24.04** 的电脑
- 一块 **NVIDIA 显卡**
- 能联网

### 安装

```bash
git clone https://github.com/DitoSun/m-acs-1.git
cd m-acs-1
sudo ./install.sh
```

安装过程是自动的：
1. 检测你的显卡型号
2. 安装 NVIDIA 驱动（如果需要重启会提示你）
3. 安装 Docker
4. 配置 GPU 容器加速
5. 启动 AI 引擎 + 控制面板
6. 设置开机自启

### 开始使用

打开浏览器访问 **http://localhost:8080**

你会看到：

```
┌─ M-ACS-1 Dashboard ─────────────────────┐
│  GPU Monitor          System Health     │
│  ─────────────        ─────────────     │
│  温度 50°C            AI Engine ● run   │
│  显存 3.2/8 GB        Dashboard ● run   │
│                                         │
│  Models                                 │
│  ─────────────                          │
│  [Quick Start] [Balanced] [Coding]      │
│  [Chinese]     [High Quality]           │
│                                         │
│  点一下 → 自动安装 → 开始聊天            │
└─────────────────────────────────────────┘
```

点 **Quick Start**，等一两分钟，模型就装好了。然后展开 **Chat** 开始对话。

---

## 支持硬件

| 项目 | 要求 |
|---|---|
| 操作系统 | Ubuntu 22.04 或 24.04 LTS |
| 显卡 | NVIDIA GeForce RTX 20/30/40 系列 |
| 内存 | 建议 16 GB 以上 |
| 硬盘 | 建议 50 GB 以上可用空间 |
| 网络 | 首次安装需联网 |

暂不支持：AMD 显卡、Intel 显卡、Mac、Windows 原生。
Windows 用户可使用 WSL2（见 FAQ）。

---

## 日常使用

```bash
# 启动
cd /opt/m-acs-1 && docker compose up -d

# 停止
cd /opt/m-acs-1 && docker compose down

# 看状态
cd /opt/m-acs-1 && make status
```

---

## 中国网络用户

中国大陆访问 Docker Hub 不稳定，install.sh 会自动检测网络并切换到国内镜像（阿里云 / DaoCloud），无需手动配置。

模型下载速度取决于 `registry.ollama.ai` 的连通性。建议首次安装选择 **Quick Start**（397 MB），快速验证系统正常工作。

如果你有 HTTP 代理：

```bash
sudo http_proxy=http://your-proxy:port ./install.sh
```

---

## 常见问题

> **需要多大的显存？**
> 8 GB 显存可运行 7B 参数模型（如 Qwen 2.5 7B），24 GB 可运行 70B 模型。

> **支持 AMD 显卡吗？**
> 暂不支持。M-ACS-1 依赖 NVIDIA CUDA。

> **训练模型吗？**
> 不。M-ACS-1 只做推理（运行模型），不训练。

> **模型文件存在哪？**
> Docker 卷中，`docker compose down` 不会删除模型。删除卷才会。

> **数据会传到外网吗？**
> 不会。所有模型在本地运行，数据不离开你的电脑。

> **能用 OpenAI API 吗？**
> M-ACS-1 提供兼容 OpenAI 格式的 API，地址是 `http://localhost:8080/v1`。任何支持 OpenAI 的工具（如 Cursor、Continue.dev）都可以连接使用。

更多问题见 [FAQ.md](./FAQ.md)。

---

## 已知限制

详见 [KNOWN_ISSUES.md](./KNOWN_ISSUES.md)。

- 仅支持 Ubuntu + NVIDIA
- Open WebUI（全功能聊天界面）默认不安装，需手动启用
- 无多用户支持
- 无知识库 / RAG 功能

---

## 给测试用户的反馈

如果你在使用中遇到问题，请填写 [FEEDBACK.md](./FEEDBACK.md) 并发给我们。你的反馈直接决定下一个版本做什么。

---

## License

MIT
