# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## DarkFactory Agent Framework

DarkFactory is an AI-native agent framework where all code, testing, and reviews are handled by AI - no human in the loop.

### Core Architecture

The framework combines capabilities from 4 source projects:
- **mempalace**: Palace memory system (wings/rooms/closets/drawers), 4-layer memory stack
- **hermes-agent**: Self-improvement through skills creation, cron scheduling
- **openclaw**: Plugin system architecture, multi-channel operations
- **auto-coding-agent-demo**: Task-driven workflow with CLAUDE.md enforced processes

### Key Components

```
darkfactory/src/
├── core/           # Task engine, workflow, validator, context manager
├── scheduler/      # Critical path analysis, Gantt charts, optimization
├── memory/        # Palace, knowledge graph, memory layers
├── skills/        # Skill generation and storage
├── plugins/       # Plugin system (linter, test-runner, browser)
├── compression/   # Context compression
├── tools/         # Tool registry and executor
└── cron/          # Job scheduling
```

### Workflow (6-Step Mandatory Process)

1. **Initialize** - `darkfactory init` or `./init.sh`
2. **Select Task** - Read task.json, select `passes: false` + highest priority
3. **Analyze** - Call `memory_stack.wake_up()` + skills + knowledge graph
4. **Implement** - Execute task steps
5. **Validate** - Layered testing (lint → build → browser/单元)
6. **Record** - Update task.json passes + progress.txt + git commit

### Validation Requirements

| Change Type | Required Validation |
|------------|---------------------|
| UI major | lint + build + browser_test |
| API | lint + build + unit_test |
| Bug fix | lint + build |

### Critical Commands

```bash
darkfactory plan "自然语言目标"    # 自然语言拆分 + 用户确认
darkfactory init                  # 初始化项目
darkfactory run                   # 执行下一个任务
darkfactory run --all             # 并行执行所有任务
darkfactory status               # 显示项目状态
darkfactory critical-path        # 显示关键路径
darkfactory web                  # 启动可视化界面
```

### Memory System

- **L0** (Identity ~50 tokens): Agent identity, always loaded
- **L1** (Essential Facts ~120 tokens): Essential context, always loaded
- **L2** (On-Demand ~200-500 tokens): Retrieved when needed
- **L3** (Deep Search unlimited): Explicit queries

### Self-Improvement Triggers

Skills are auto-generated when:
- Complex task (tool calls >= 5)
- Error recovery (克服棘手错误)
- User correction
- Repeated pattern (3+ times)

### Plugin System

Built-in plugins:
- `ruff-linter`: Fast Python linting
- `pytest-runner`: Test execution with coverage
- `playwright-browser`: End-to-end browser testing
