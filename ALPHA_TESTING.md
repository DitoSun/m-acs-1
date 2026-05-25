# M-ACS-1 Alpha Testing Guide

感谢你参与 M-ACS-1 的 Alpha 测试。你的反馈直接决定产品方向。

---

## 测试流程

```
1. 准备环境    →  一台 Ubuntu 24.04 + NVIDIA 显卡的电脑
2. 安装        →  sudo ./install.sh
3. 打开        →  浏览器访问 http://localhost:8080
4. 装模型      →  点 "Quick Start" 选项卡
5. 聊天        →  模型装好后点 Chat → Try it
6. 反馈        →  遇到问题运行 bash collect-debug.sh 并提交 Issue
```

---

## Alpha Test Checklist

### 安装

```
□  git clone 成功
□  sudo ./install.sh 开始运行
□  网络检测正常（中国大陆用户应看到 mirror 切换提示）
□  NVIDIA 驱动安装提示（如需重启）
□  Docker 安装成功
□  GPU 容器加速配置成功
□  所有容器启动成功
□  浏览器能打开 http://localhost:8080
```

### Dashboard

```
□  看到 GPU 面板，显示显卡型号和温度
□  看到 System Health，三个服务都显示 running
□  温度 / 显存数据自动刷新
□  页面没有空白或样式错乱
```

### 模型安装

```
□  欢迎页显示 5 个推荐选项卡
□  点 "Quick Start" → 显示 "qwen2.5:0.5b: connecting..."
□  等待 1-2 分钟 → 显示 "✓ qwen2.5:0.5b installed!"
□  模型出现在列表中
□  点其他选项卡也能安装
□  自定义输入框可以安装非推荐模型
```

### 聊天

```
□  展开 Chat
□  输入消息 → AI 回复
□  回复完整不重复
```

### 稳定性

```
□  机器重启 → 所有服务自动恢复
□  Dashboard 数据不丢失
□  已安装模型不丢失
```

---

## 遇到问题？

1. 运行 `bash collect-debug.sh`
2. 复制全部输出
3. 在 GitHub 提交 Issue：https://github.com/DitoSun/m-acs-1/issues

提交 Issue 时请选择对应模板，你会被引导填写必要信息。

---

## 提供反馈

试用后请填写 [FEEDBACK.md](./FEEDBACK.md) 中的问题，这对我们非常有价值。

感谢你的时间！
