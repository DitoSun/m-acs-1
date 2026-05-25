# M-ACS-1 v0.1 MVP — Release Checklist

## Install Validation

```
□  全新 Ubuntu 24.04 裸机，sudo ./install.sh → exit 0
□  NVIDIA 驱动未装 → 脚本自动安装后提示重启 → 重启后重跑 → 继续完成
□  第二次重跑 → 幂等，不重装任何已存在组件
□  第三次重跑 → 幂等，不报错
□  Docker 未装 → 从官方 apt repo 安装
□  nvidia-container-toolkit 未装 → 自动安装配置
□  最终 docker compose ps → 3 容器 running
□  systemctl status m-acs-host-agent → active
□  http://localhost:8080 → Dashboard 正常加载
```

## Dashboard Validation

```
□  页面加载无白屏
□  浏览器控制台零错误
□  GPU 面板显示显卡型号、温度、显存
□  所有指标 5 秒自动刷新
□  System Health 显示 AI Engine / Dashboard / GPU Monitor 状态
```

## Model Lifecycle Validation

```
□  无模型时欢迎页显示推荐选项卡
□  点 Quick Start 选项卡 → 开始下载，状态显示 "qwen2.5:0.5b: connecting..."
□  下载完成后显示 "✓ qwen2.5:0.5b installed!"
□  模型名完整显示：qwen2.5:0.5b
□  点 ✕ 删除 → confirm 对话框 → 删除后列表更新
□  选项卡在模型安装后仍然可见
□  自定义输入框可安装非推荐模型
```

## Chat Validation

```
□  点 "Try it" 展开聊天
□  发送消息 → AI 流式回复
□  回复不重复（无 buf 截断问题）
□  无网络错误
```

## API Validation

```
□  curl http://localhost:8080/api/health → 200
□  curl http://localhost:8080/api/gpu → 200 + GPU 数据
□  curl http://localhost:8080/api/models → 200 + 模型列表
□  curl http://localhost:8080/v1/chat/completions → 200 (OpenAI 兼容)
□  curl http://localhost:8080/health → 200
```

## Reboot Recovery

```
□  sudo reboot → 所有容器自动启动
□  systemctl status m-acs-host-agent → active
□  浏览器打开 Dashboard → 数据正常
□  之前的模型还在
```

## Failure Recovery

```
□  docker compose stop ollama → /api/health 显示 ollama offline
□  docker compose start ollama → 30 秒内恢复
□  systemctl stop m-acs-host-agent → /api/gpu 显示 unavailable
□  systemctl start m-acs-host-agent → 10 秒内恢复 GPU 数据
□  删除 /opt/m-acs-1/data/gpu.json → host-agent 自动重新生成
```

## Documentation

```
□  README.md 更新完成
□  FAQ.md 覆盖常见问题
□  KNOWN_ISSUES.md 列出已知限制
□  FEEDBACK.md 提供反馈模板
□  .env.example 存在
□  RELEASE_CHECKLIST.md 存在（本文档）
```

## Screenshots

```
□  Dashboard 欢迎页截图
□  GPU 面板截图
□  模型列表截图
□  Chat 对话截图
□  移动端/宽屏响应式截图（可选）
```

## Release Artifacts

```
□  GitHub 仓库创建
□  release v0.1.0 标记
□  所有敏感信息已排除（.env 不存在，只有 .env.example）
□  无 dev 工具文件（validate.py 等已删除）
□  install.sh 可执行权限已设置
```
