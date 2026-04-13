<<<<<<< HEAD
# DarkFactory
=======
# DarkFactory

**AI-Native Agent Framework** - 一个完全由 AI 驱动、无需人工编写/审核/测试代码的智能代理框架。

融合了 mempalace、hermes-agent、openclaw 和 auto-coding-agent-demo 四大项目的核心能力。

[English](./README_EN.md) | 中文

---

## 核心特性

### 1. 自然语言任务规划
```
darkfactory plan "我想做一个博客系统，有用户认证、文章发布、评论功能"
```
AI 自动分析需求，拆分成可独立验证的任务列表，生成活动网络图和关键路径。

### 2. 多 Agent 并行执行
```bash
darkfactory run --all --agents 4
```
支持最多 4 个 Agent 并行工作，通过 MessageBus 进行通信协调。

### 3. 四层记忆系统
| Layer | Content | Token | 用途 |
|-------|---------|-------|------|
| L0 | Identity | ~50 | 始终加载 |
| L1 | Essential Facts | ~120 | 始终加载 |
| L2 | Room Recall | ~200-500 | 按需加载 |
| L3 | Deep Search | 无限 | 显式查询 |

### 4. 自改进技能系统
从经验中自动生成可复用技能：
- 复杂任务（工具调用 >= 5）
- 错误恢复
- 用户纠正
- 重复模式（3+ 次）

### 5. 关键路径分析 (CPM)
自动计算 EET/LET、Slack 值，识别关键路径，优化调度。

### 6. Web 可视化
Blueprint 风格 UI，实时监控执行状态、活动网络图、甘特图。

---

## 支持的 LLM 提供商

框架支持任意兼容 Anthropic 或 OpenAI API 的大模型：

| 类型 | 提供商 | 配置示例 |
|------|--------|---------|
| Anthropic | Claude, MiniMax | `provider: anthropic` |
| OpenAI | GPT-4, Qwen, DeepSeek | `provider: openai` |

### 快速配置

```bash
# 交互式配置
darkfactory config setup

# 指定 provider
darkfactory config setup --provider qwen
darkfactory config setup --provider minimax
darkfactory config setup --provider deepseek

# 命令行配置
darkfactory config set --api-key "your-key" --base-url "https://your-api.com/v1" --model "model-name"
```

---

## 安装

### 环境要求
- Python 3.11+
- pip

### 安装方式一：直接使用脚本（推荐）

克隆后添加 `scripts`（Windows）或 `bin`（Linux/Mac）目录到 PATH 即可：

```bash
# Windows (PowerShell)
git clone https://github.com/Lawrence1305/DarkFactory.git
$env:PATH = "E:\Documents\Coding\AIFrameStudy\DarkFactory\scripts;$env:PATH"
darkfactory config setup   # 首次配置 AI API

# Linux/Mac
git clone https://github.com/Lawrence1305/DarkFactory.git
export PATH="/path/to/DarkFactory/bin:$PATH"
darkfactory config setup   # 首次配置 AI API
```

### 安装方式二：pip 安装

```bash
# 克隆项目
git clone https://github.com/Lawrence1305/DarkFactory.git
cd DarkFactory

# 安装依赖
pip install -e ".[dev]"

# 配置 AI API
darkfactory config setup
```

---

## 使用方法

### CLI 命令

```bash
# 1. 任务规划（自然语言）
darkfactory plan "我想做一个博客系统，有用户认证、文章发布、评论功能"
darkfactory plan confirm     # 确认计划

# 2. 初始化
darkfactory init

# 3. 执行任务
darkfactory run              # 执行下一个任务
darkfactory run --all       # 并行执行所有任务
darkfactory run --agents 4   # 指定并发数

# 4. 查看状态
darkfactory status           # 项目状态
darkfactory progress         # 进度
darkfactory critical-path    # 关键路径

# 5. 配置
darkfactory config show      # 查看配置
darkfactory config set --api-key "xxx"  # 设置 API Key

# 6. 启动 Web UI
darkfactory web
```

### Python 模块使用

```python
from src.core.task_engine import TaskEngine
from src.core.agent_pool import AgentPool
from src.memory.memory_manager import MemoryManager
from src.scheduler.critical_path import CriticalPathAnalyzer

# 初始化
engine = TaskEngine()
pool = AgentPool(max_agents=4)
memory = MemoryManager()

# 添加任务
from src.core.task import Task
task = Task(
    id="task-001",
    title="实现用户认证",
    steps=["创建用户模型", "实现注册API", "实现登录API"],
    priority=1,
)
engine.add_task(task)

# 关键路径分析
analyzer = CriticalPathAnalyzer()
network = analyzer.analyze(list(engine._tasks.values()))
print(f"关键路径: {analyzer.get_critical_path()}")
```

---

## 项目结构

```
darkfactory/
├── CLAUDE.md              # 框架执行指南
├── AGENTS.md              # Agent 协调规则
├── SPEC.md                # 项目规格说明
├── pyproject.toml         # Python 项目配置
├── src/
│   ├── config.py          # 配置模块
│   ├── main_cli.py        # CLI 入口
│   ├── core/              # 核心引擎
│   │   ├── task.py        # 任务模型
│   │   ├── task_engine.py # 任务引擎
│   │   ├── task_planner.py # 任务规划器
│   │   ├── workflow.py    # 工作流
│   │   ├── validator.py   # 验证器
│   │   ├── agent_pool.py  # Agent 池
│   │   └── context_manager.py # 上下文管理
│   ├── scheduler/         # 调度模块
│   │   ├── critical_path.py # 关键路径分析
│   │   ├── gantt.py       # 甘特图
│   │   └── optimizer.py   # 调度优化
│   ├── memory/            # 记忆系统
│   │   ├── palace.py       # Palace 结构
│   │   ├── layers.py       # 四层记忆栈
│   │   ├── knowledge_graph.py # 知识图谱
│   │   └── memory_manager.py # 记忆管理器
│   ├── skills/            # 技能系统
│   ├── plugins/           # 插件系统
│   ├── compression/        # 上下文压缩
│   ├── tools/             # 工具注册
│   ├── cron/               # 任务调度
│   └── llm/                # LLM 客户端
│       ├── client.py       # 客户端基类
│       ├── anthropic_client.py
│       └── openai_client.py
└── web/
    ├── backend/           # FastAPI 后端
    └── frontend/          # React 前端
```

---

## 工作流程

```
┌─────────────────────────────────────────────────────────┐
│                     DarkFactory 工作流                   │
└─────────────────────────────────────────────────────────┘

  自然语言目标
       │
       ▼
  ┌─────────┐    ┌──────────┐    ┌────────────┐
  │   Plan   │───▶│  Confirm │───▶│ task.json  │
  └─────────┘    └──────────┘    └────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────┐
  │                     执行循环                          │
  │  ┌──────┐  ┌────────┐  ┌──────────┐  ┌──────────┐  │
  │  │Select│─▶│Analyze │─▶│Implement │─▶│ Validate │  │
  │  └──────┘  └────────┘  └──────────┘  └──────────┘  │
  │                                          │          │
  │              ◀───── 失败重试 ◀───────────┘          │
  └─────────────────────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────┐
  │                  记录 & 自改进                       │
  │  ┌─────────┐  ┌───────────┐  ┌─────────────────┐   │
  │  │progress │  │  Skill    │  │   Memory        │   │
  │  │.txt    │  │ Generator │──│   Palace        │   │
  │  └─────────┘  └───────────┘  └─────────────────┘   │
  └─────────────────────────────────────────────────────┘
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 核心 | Python 3.11+ |
| Web 框架 | FastAPI + React 18 |
| 向量存储 | ChromaDB |
| 知识图谱 | SQLite |
| 浏览器测试 | Playwright |
| CLI | Click + Rich |

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request！
>>>>>>> bc6bebd (Initial commit: DarkFactory AI-Native Agent Framework)
