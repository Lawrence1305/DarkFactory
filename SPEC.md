# SPEC.md

## DarkFactory Agent Framework Specification

### Project Overview

- **Name**: DarkFactory
- **Type**: AI-Native Agent Framework
- **Core Principle**: No human writes code, reviews code, or tests code - AI handles everything
- **Target Users**: AI agents working on software development tasks

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Pure Python | Simplified implementation |
| Task Input | Natural language | AI auto-decomposes to task.json |
| Execution | Multi-agent parallel | Max throughput |
| Memory | 4-layer palace | Token-efficient context |

### Core Features

#### 1. Natural Language Task Decomposition
- Input: Natural language goal
- Process: LLM analyzes and splits into verifiable tasks
- Output: task.json with activity network
- **Human-in-loop**: User confirms before execution

#### 2. Critical Path Analysis (CPM)
- Forward pass: Calculate EET (Earliest Event Time)
- Backward pass: Calculate LET (Latest Event Time)
- Slack = LET - EET
- Critical path: Tasks with slack = 0

#### 3. Activity Network
- Node: Task (id, duration, status)
- Edge: Dependency (finish-to-start)
- Visualization: React Flow
- Critical path highlighted in yellow

#### 4. Gantt Chart
- D3.js generated SVG
- Time scale: Minutes/Hours/Days
- Task bars colored by status
- Critical path highlighted

#### 5. Multi-Agent Execution
- Agent pool: Max 4 concurrent
- Message bus: Agent communication
- Task isolation: Each agent has own context
- Shared memory: Via MemoryManager

#### 6. Four-Layer Memory Stack

| Layer | Content | Token Budget | Loading |
|-------|---------|--------------|---------|
| L0 | Identity | ~50 | Always |
| L1 | Essential Facts | ~120 | Always |
| L2 | Room Recall | ~200-500 | On-demand |
| L3 | Deep Search | Unlimited | Explicit query |

#### 7. Palace Memory Structure

```
Wing (project/person)
  └─ Room (topic)
       └─ Hall (type: facts/events/discoveries/preferences/advice)
            └─ Closet (summary)
                 └─ Drawer (raw vector)
```

#### 8. Temporal Knowledge Graph

- SQLite-based
- Triples: (subject, predicate, object)
- Temporal validity: valid_from, valid_to
- Operations: add, query, invalidate

#### 9. Self-Improvement System

Skills auto-generated from:
- Complex tasks (>=5 tool calls)
- Error recovery
- User corrections
- Repeated patterns (3+ times)

Skill structure:
- name: kebab-case
- trigger: when to use
- steps: execution steps
- pitfalls: known traps
- verification: how to verify success

#### 10. Plugin System

OpenClaw-style architecture:
- Plugin base class with lifecycle hooks
- PluginRegistry for management
- Hook system for events
- Built-in: linter, test-runner, browser

### task.json Format

```json
{
  "project": {
    "id": "string",
    "name": "string",
    "workspace": "path"
  },
  "tasks": [{
    "id": "string",
    "title": "string",
    "description": "string",
    "steps": ["string"],
    "priority": 1-5,
    "dependencies": ["task_id"],
    "skills_required": ["skill_name"],
    "test_strategy": "auto|browser|lint|unit",
    "passes": boolean,
    "estimated_duration": minutes,
    "estimated_tokens": number
  }]
}
```

### CLI Commands

```bash
darkfactory plan "goal"     # Natural language planning
darkfactory plan confirm    # Confirm plan
darkfactory plan modify     # Modify plan
darkfactory init            # Initialize project
darkfactory run              # Execute next task
darkfactory run --all       # Parallel execution
darkfactory run --agents N  # Specify agents
darkfactory status           # Show status
darkfactory progress        # Show progress
darkfactory critical-path   # Show critical path
darkfactory memory search   # Search memories
darkfactory skills list    # List skills
darkfactory kg query        # Query knowledge graph
darkfactory cron list       # List scheduled jobs
darkfactory web             # Start web UI
```

### Web API

```bash
POST /api/projects           # Create project
GET  /api/projects/{id}      # Get project
POST /api/tasks              # Create task
PUT  /api/tasks/{id}         # Update task
POST /api/execution/start    # Start execution
WS   /ws/{project_id}       # WebSocket updates
```

### Technology Stack

- **Backend**: Python 3.11+, FastAPI, ChromaDB, SQLite
- **Frontend**: React 18, React Flow, D3.js, Vite
- **Testing**: pytest, Playwright
- **CLI**: Click, Rich

### Directory Structure

```
darkfactory/
├── CLAUDE.md               # This file - framework guide
├── AGENTS.md               # Agent coordination rules
├── SPEC.md                 # This specification
├── pyproject.toml
├── src/
│   ├── main.py
│   ├── main_cli.py
│   ├── core/               # Task, workflow, validator
│   ├── scheduler/           # CPM, Gantt, optimizer
│   ├── memory/              # Palace, layers, KG
│   ├── skills/             # Skill system
│   ├── plugins/            # Plugin system
│   ├── compression/         # Context compression
│   ├── tools/              # Tool registry
│   └── cron/               # Job scheduling
├── web/
│   ├── backend/            # FastAPI
│   └── frontend/          # React + Vite
├── skills/                 # AI-generated skills
├── memory/                 # Memory storage
└── tests/                  # Unit + integration
```

### Success Criteria

1. AI can decompose natural language goal into executable tasks
2. AI can execute tasks in parallel with multiple agents
3. AI can learn from errors and generate skills
4. AI can maintain context across sessions via memory
5. Human can visualize progress via web UI
6. Human can intervene/adjust plan before execution
