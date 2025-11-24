# 🔬 SciAgent

<div align="center">

**智能实验运行守护与分析工具 | AI-Powered Experiment Guardian & Analyzer**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

专为科研、竞赛、工程项目设计的实验管理工具  
零代码侵入 · AI 智能分析 · 本地运行

</div>

---

## 📖 目录

- [为什么选择 SciAgent](#-为什么选择-sciagent)
- [安装](#-安装)
- [快速开始](#-快速开始)
- [核心功能](#-核心功能)
- [AI 智能分析](#-ai-智能分析)
- [高级用法](#-高级用法)
- [应用场景](#-应用场景)
- [常见问题](#-常见问题)
- [贡献](#-贡献)

---

## 🎯 为什么选择 SciAgent？

### 你是否遇到过这些痛点？

| 问题 | SciAgent 解决方案 |
|------|------------------|
| 💥 **实验跑崩了**，找不到日志和崩溃原因 | ✅ 自动捕获错误、保存日志、记录环境快照 |
| 😖 **忘记参数了**，不知道哪组配置效果最好 | ✅ 自动追踪命令行参数、代码参数、配置文件 |
| 🤔 **盲目调参**，不知道下一步该调哪个参数 | ✅ AI 智能分析实验结果，给出调优建议 |
| 📊 **写周报/论文**，每次写周报太苦恼不知从何下手 | ✅ 一键生成日报/周报/月报，含代码变更和实验对比 |

### SciAgent 的独特优势

- **🚀 零代码侵入**：只需在命令前加 `sciagent run`，无需修改现有代码
- **🤖 AI 驱动**：支持 8+ 主流 LLM（GPT-5、DeepSeek、Claude、Gemini 等）
- **📦 轻量本地**：无需联网，数据完全本地存储，隐私安全
- **🎨 美观易用**：现代化 CLI 界面，交互友好
- **🔧 灵活扩展**：支持自定义 API、多种导出格式

---

## 📦 安装

### 系统要求

- **Python 3.9+**
- **Git**（可选，用于代码变更追踪）
- **操作系统**：macOS / Linux / Windows

### 快速安装

#### 方法 1：从源码安装（开发/内测）

```bash
# 1. 克隆或下载项目
cd /path/to/sciagent

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 3. 安装 SciAgent
pip install -e .

# 4. 验证安装
sciagent --version
```

#### 方法 2：直接安装（不使用虚拟环境）

```bash
cd /path/to/sciagent
pip install -e .
```

### 依赖说明

SciAgent 会自动安装以下依赖：

- `pyyaml>=6.0` - YAML 配置文件支持
- `rich>=13.0` - 美观的终端 UI
- `questionary>=2.0` - 交互式命令行
- `psutil>=5.9` - 系统信息获取
- `openai>=1.0` - LLM API 客户端（支持 OpenAI 兼容接口）
- `python-dotenv>=1.0` - 环境变量管理

### 验证安装

```bash
# 查看版本
sciagent --version

# 查看帮助
sciagent --help
```

---

## 🚀 快速开始

### 1️⃣ 初始化项目

```bash
cd your-project
sciagent init
```

交互式配置向导将引导你完成：
- ✅ 环境检测（Python、系统、依赖）
- ✅ 项目配置（名称、目录）
- ✅ AI 功能配置（LLM 提供商、API Key，可选）

### 2️⃣ 运行实验

**原来的命令**：
```bash
python train.py --lr 0.001 --epochs 100
```

**使用 SciAgent**：
```bash
sciagent run python train.py --lr 0.001 --epochs 100
```

> **注意**：直接在 `sciagent run` 后面写命令，不需要引号！

就这么简单！SciAgent 会：
- 🕒 自动记录开始/结束时间
- 📊 追踪所有命令行参数（`--lr`, `--epochs`）
- 🔍 捕获输出和错误信息
- 📸 保存环境快照（Python 版本、依赖、Git commit）
- 💾 自动检测 `metrics.json` 中的指标

### 3️⃣ 查看历史

```bash
sciagent history
```

输出示例：
```
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ 运行 ID              ┃ 状态     ┃ 开始时间             ┃ 耗时      ┃ 备注        ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━┩
│ abc123def456         │ ✓ 完成   │ 2025-01-15 10:23:45 │ 2h 15m   │ 尝试新优化器 │
│ 789ghi012jkl         │ ✗ 失败   │ 2025-01-15 08:10:12 │ 5m       │ OOM 错误    │
│ mno345pqr678         │ ✓ 完成   │ 2025-01-14 16:45:30 │ 1h 32m   │ baseline    │
└──────────────────────┴─────────┴─────────────────────┴──────────┴─────────────┘
```

### 4️⃣ AI 智能分析

```bash
# 分析最近一次实验
sciagent analyze --last

# 分析指定实验
sciagent analyze abc123def456
```

AI 会告诉你：
- 🎯 **问题诊断**：为什么指标不理想
- 💡 **调优建议**：下一步应该调哪些参数
- 📈 **趋势分析**：与历史最佳结果的对比

---

## 🎨 核心功能

### 1. 实验运行守护

```bash
sciagent run [命令]
```

**自动记录**：
- ✅ 命令行参数（`--lr 0.001`）
- ✅ 代码内参数（使用 `sciagent.track.log_params()`）
- ✅ 训练指标（自动检测 `metrics.json`）
- ✅ 环境信息（Python、系统、Git、依赖版本）
- ✅ 运行时长、退出码、错误日志

**实时监控**：
- 📺 实时显示输出
- ⚡ 崩溃自动保存现场
- 🔔 支持 Ctrl+C 优雅退出

**使用示例**：
```bash
# 基础用法
sciagent run python train.py

# 带参数
sciagent run python train.py --config config.yaml --gpu 0

# 添加备注
sciagent run --note "baseline model" python train.py

# 设置工作目录
sciagent run --workdir experiments/exp1 python train.py
```

### 2. 历史管理

```bash
# 查看所有实验
sciagent history

# 限制显示数量
sciagent history --limit 20
```

### 3. AI 分析

```bash
# 分析实验结果（包含参数对比和调优建议）
sciagent analyze --last
sciagent analyze abc123def456
```

分析报告包含：
- **配置对比**：当前参数 vs 历史最佳（或上一次）
- **指标对比**：accuracy, loss 等指标的变化
- **AI 调优建议**：下一步该调哪些参数

### 4. 工作报告

```bash
# 生成今日工作日志
sciagent daily

# 生成本周工作周报
sciagent weekly

# 生成本月工作月报
sciagent monthly
```

报告包含：
- 📊 实验统计（成功/失败数、运行时长）
- 🏆 最佳结果（最高 accuracy、最低 loss）
- 💻 代码变更（Git 提交历史 + AI 总结）
- 🤖 AI 工作概览（实验分析、参数影响、关键发现）
- 💡 AI 计划建议（下一步调优方向）

### 5. 消融实验表格

```bash
# 生成消融实验对比表
sciagent table --name "learning_rate"

# 导出为 LaTeX
sciagent table --format latex --output results.tex
```

---

## 🤖 AI 智能分析

### 支持的 LLM 提供商

| 提供商 | 模型示例 | 需要 VPN |
|--------|---------|---------|
| 🇨🇳 **DeepSeek** | deepseek-chat, deepseek-reasoner | ❌ |
| 🇨🇳 **通义千问** | qwen-plus, qwen-max | ❌ |
| 🇨🇳 **Kimi** | moonshot-v1-32k | ❌ |
| 🇨🇳 **智谱 GLM** | glm-4.6, glm-4.5 | ❌ |
| 🇺🇸 **OpenAI** | gpt-5.1, gpt-5-mini | ✅ |
| 🇺🇸 **Claude** | claude-sonnet-4-5 | ✅ |
| 🇺🇸 **Gemini** | gemini-2.5-flash | ✅ |
| 🔧 **自定义 API** | 任意 OpenAI 兼容 | - |

### 配置 AI

**方法 1：初始化时配置**

运行 `sciagent init` 时选择启用 AI 功能，按照提示选择 LLM 提供商和输入 API Key。

**方法 2：手动编辑配置**

编辑 `.sciagent.json`：

```json
{
  "project_name": "my-research",
  "workdir": "/path/to/project",
  "llm_provider": "deepseek",
  "llm_model": "deepseek-chat",
  "llm_api_key": "sk-xxxxxxxxxxxxx",
  "llm_base_url": "https://api.deepseek.com"
}
```

### AI 功能

1. **实验分析** (`sciagent analyze`)：
   - 诊断为什么指标不理想
   - 分析参数对结果的影响
   - 给出下一步调优建议

2. **工作报告** (`sciagent daily/weekly/monthly`)：
   - 总结实验趋势和关键发现
   - 分析代码变更的技术价值
   - 提供下一阶段计划建议

3. **消融分析** (`sciagent table`)：
   - 生成对比表格
   - AI 解读实验结果

---

## 🔧 高级用法

### 代码内参数追踪

如果参数定义在代码里（而非命令行），使用 `sciagent.track`：

```python
import sciagent.track as st

# 记录参数
st.log_params({
    "learning_rate": 0.001,
    "batch_size": 32,
    "optimizer": "adam"
})

# 训练过程...
for epoch in range(epochs):
    train_loss = train_one_epoch()
    val_acc = validate()
    
    # 记录指标
    st.log_metrics({
        "train_loss": train_loss,
        "val_accuracy": val_acc
    })

# 保存（会自动生成 metrics.json 和 params.json）
st.save()
```

### 自动指标检测

SciAgent 会自动在以下位置查找 `metrics.json`：
- `workdir/metrics.json`
- `workdir/outputs/metrics.json`
- `workdir/results/metrics.json`
- `workdir/logs/metrics.json`
- 脚本运行目录

**metrics.json 示例**：
```json
{
  "accuracy": 0.9523,
  "loss": 0.1234,
  "f1_score": 0.9401,
  "learning_rate": 0.001,
  "batch_size": 32
}
```

### 配置文件管理

编辑 `.sciagent.json` 自定义行为：

```json
{
  "project_name": "my-research",
  "workdir": "/path/to/project",
  "state_dir": ".sciagent",
  "primary_metric": "accuracy",
  "llm_provider": "deepseek",
  "llm_model": "deepseek-chat",
  "llm_api_key": "sk-xxxx"
}
```

---

## 📚 应用场景

### 1. 学术研究

- 📝 **写论文**：快速找到实验数据，生成消融表格
- 🔄 **复现实验**：记录完整环境，确保可复现性
- 📊 **对比分析**：多组实验结果自动对比

**示例**：
```bash
# 运行基线模型
sciagent run --note "baseline" python train.py --model resnet50

# 运行改进模型
sciagent run --note "with attention" python train.py --model resnet50_attn

# 生成对比表格
sciagent table --format latex
```

### 2. 算法竞赛

- 🏆 **快速迭代**：记录每次提交的参数和分数
- 📈 **追踪排名**：自动记录 leaderboard 分数
- 🤖 **AI 建议**：分析哪些特征工程有效

**示例**：
```bash
# 运行实验
sciagent run python train.py --features "v1,v2,v3"

# 查看最佳结果
sciagent history --limit 20

# AI 分析
sciagent analyze --last
```

### 3. 工程项目

- 🔧 **模型调优**：系统化地调整超参数
- 📊 **A/B 测试**：对比不同模型版本的效果
- 📝 **团队协作**：共享实验记录和配置

**示例**：
```bash
# 尝试不同优化器
sciagent run --note "adam" python train.py --optimizer adam
sciagent run --note "sgd" python train.py --optimizer sgd

# 生成周报
sciagent weekly
```

---

## ❓ 常见问题

### Q1: 提示 `command not found: sciagent`

**A**: 确保已激活虚拟环境，或重新安装：
```bash
# 如果使用虚拟环境
source venv/bin/activate

# 重新安装
pip uninstall sciagent
pip install -e .
```

### Q2: 安装时提示权限错误

**A**: 使用虚拟环境（推荐），或添加 `--user` 参数：
```bash
pip install --user -e .
```

### Q3: 如何更新 SciAgent？

**A**: 如果从源码安装，直接 pull 最新代码即可：
```bash
cd /path/to/sciagent
git pull  # 如果使用 Git
pip install -e . --force-reinstall
```

### Q4: metrics.json 放在哪里？

**A**: SciAgent 会自动检测以下位置的 `metrics.json`：
- 工作目录根目录
- `outputs/`, `results/`, `logs/`, `output/` 子目录
- 训练脚本所在目录

推荐：在训练脚本中使用 `sciagent.track.save()` 自动生成。

### Q5: 如何使用自定义 LLM API？

**A**: 在 `sciagent init` 时选择"自定义 API"，然后输入：
- API Base URL（如：`http://localhost:8000/v1`）
- API Key
- 模型名称

或直接编辑 `.sciagent.json`：
```json
{
  "llm_provider": "custom",
  "llm_model": "my-model",
  "llm_api_key": "your-key",
  "llm_base_url": "http://localhost:8000/v1"
}
```

### Q6: Windows 上如何使用？

**A**: Windows 完全支持！唯一区别是激活虚拟环境的命令：
```cmd
# Windows 命令提示符
venv\Scripts\activate.bat

# Windows PowerShell
venv\Scripts\Activate.ps1
```

### Q7: 如何删除实验历史？

**A**: 实验记录存储在 `.sciagent/` 目录中：
```bash
# 删除所有历史
rm -rf .sciagent/

# 或只删除特定记录
rm -rf .sciagent/history/abc123def456/
```

---

## 🤝 贡献

我们欢迎所有形式的贡献！

- 🐛 **报告 Bug**：[提交 Issue](https://github.com/yourusername/sciagent/issues)
- 💡 **功能建议**：[讨论区](https://github.com/yourusername/sciagent/discussions)
- 📖 **改进文档**：提交 PR
- ⭐ **如果觉得有用，请给个 Star！**

### 开发指南

```bash
# 1. Fork 项目并克隆
git clone https://github.com/yourusername/sciagent.git
cd sciagent

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装开发依赖
pip install -e .

# 4. 运行测试
cd examples
sciagent run python simple_train.py

# 5. 提交修改
git add .
git commit -m "你的修改说明"
git push
```

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

感谢所有贡献者和用户的支持！

如果 SciAgent 对你的研究有帮助，欢迎引用：

```bibtex
@software{sciagent2025,
  title = {SciAgent: AI-Powered Experiment Guardian \& Analyzer},
  author = {SciAgent Contributors},
  year = {2025},
  url = {https://github.com/yourusername/sciagent}
}
```

---

<div align="center">

**让科研实验更高效、更智能！**

Made with ❤️ by SciAgent Contributors

[⬆ 回到顶部](#-sciagent)

</div>
