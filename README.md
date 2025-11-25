
# 🔬 SciAgent

**智能实验运行守护与分析工具｜AI-Powered Experiment Guardian**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org)

**零代码侵入 · 自动追踪 · AI 智能分析 · 本地运行**

---

# 📌 目录

- [为什么选择 SciAgent](#为什么选择-sciagent)
- [安装](#安装)
- [快速开始](#快速开始)
- [核心功能](#核心功能)
- [AI 智能分析](#ai-智能分析)
- [应用场景](#应用场景)
- [常见问题](#常见问题)
- [贡献](#贡献)

---

# 🎯 为什么选择 SciAgent

### 常见痛点

| 问题 | SciAgent 解决方案 |
|------|------------------|
| 实验跑崩、日志丢失 | 自动捕获错误与环境快照 |
| 参数忘记、配置混乱 | 自动记录命令行、代码参数与配置 |
| 调参靠感觉 | AI 自动分析指标与趋势 |
| 写周报麻烦 | 一键生成日报 / 周报 / 月报 |

### 核心优势

- 🚀 **零代码侵入**：无需修改训练脚本  
- 🤖 **AI 驱动**：支持 GPT-5 / DeepSeek / Claude / Gemini / Qwen / GLM  
- 📦 **本地存储**：不用联网即可使用  
- 🎨 **现代 CLI**：结构清晰、交互友好  
- 🔧 **灵活扩展**：兼容任意 OpenAI 格式 API

---

# 📦 安装

```bash
cd /path/to/sciagent
pip install -e .
````

依赖包含：`pyyaml`, `rich`, `questionary`, `psutil`, `openai`, `python-dotenv`

---

# 🚀 快速开始

### 1️⃣ 初始化

```bash
sciagent init
```

### 2️⃣ 运行实验（零侵入）

```bash
sciagent run python train.py --lr 1e-3 --epochs 100
```

### 3️⃣ 查看历史

```bash
sciagent history
```

### 4️⃣ AI 分析

```bash
sciagent analyze --last
```

---

# 🎨 核心功能

### ✔ 实验运行守护

自动记录参数、指标、环境、输出日志与错误信息。

### ✔ 历史管理

按时间查看所有运行记录，可过滤、搜索。

### ✔ AI 分析

自动生成：

* 指标变化解读
* 参数影响分析
* 调优建议

### ✔ 自动生成工作报告

```bash
sciagent daily
sciagent weekly
sciagent monthly
```

### ✔ 消融实验对比表

```bash
sciagent table --name lr
```

---

# 🤖 AI 智能分析

支持的文字 LLM：

| 提供商      | 模型示例                             |
| -------- | -------------------------------- |
| OpenAI   | gpt-5.1, gpt-5-mini              |
| DeepSeek | deepseek-chat, deepseek-reasoner |
| Qwen     | qwen-plus, qwen-max              |
| GLM      | glm-4.6, glm-4.5                 |
| Kimi     | moonshot-v1-8k/32k/128k          |
| Gemini   | gemini-2.5-flash/pro             |
| Claude   | claude-sonnet-4-5                |
| 自定义      | 任意 OpenAI 格式 API                 |

配置示例：

```json
{
  "llm_provider": "deepseek",
  "llm_model": "deepseek-chat",
  "llm_api_key": "sk-xxxxx"
}
```

---

# 📚 应用场景

### 🧪 学术研究

* 快速生成消融对比表
* 复现实验环境
* 自动整理实验记录

### 🏆 算法竞赛

* 保存所有提交记录
* AI 给出调参方向

### 🛠 工程项目

* A/B 测试
* 多版本性能对比
* 团队共享实验记录

---

# ❓ 常见问题

**Q: 必须使用 metrics.json 吗？**
A: 是，SciAgent 会在多个路径自动检测。

**Q: Windows 可用吗？**
A: 完全支持。

**Q: 如何删除历史？**

```bash
rm -rf .sciagent/
```

---

# 🤝 贡献

欢迎提交 PR、Issue 和功能建议！

---

# 📄 许可证

MIT License

---

# 🙏 致谢

感谢所有贡献者和早期用户！

---

