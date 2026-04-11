# AGENTS.md

Architecture boundaries and coordination rules for DarkFactory agents.

## Multi-Agent Architecture

### Agent Types

1. **Master Agent** - Coordinates overall execution, manages task selection
2. **Sub Agents** - Execute individual tasks in parallel
3. **Specialized Agents** - Task-specific (linter, tester, browser)

### Communication Protocol

All agent communication goes through the MessageBus:

```python
class AgentMessage:
    type: str      # "result", "blocking", "skill_created", "memory_updated"
    from_agent: str
    to_agent: Optional[str]  # None = broadcast
    payload: dict
```

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `task_assigned` | Master → Sub | New task assignment |
| `task_result` | Sub → Master | Task completion |
| `blocking` | Sub → Master | Task blocked |
| `skill_created` | Sub → Master | New skill generated |
| `memory_updated` | Any → All | Memory state change |

## Agent Pool

```python
class AgentPool:
    max_agents: int = 4
    spawn(task) → SubAgent
    run_parallel(tasks) → list[TaskResult]
```

## Task Execution

1. Master selects next task from queue
2. Assigns to available SubAgent
3. SubAgent executes with own context
4. Results returned via MessageBus
5. Master updates task status

## Resource Constraints

- Max concurrent agents: 4 (configurable)
- Agent memory: Isolated per agent
- Shared state: Only through MemoryManager
- No direct agent-to-agent communication

## Blocking Issues

When blocked:
1. SubAgent sends `blocking` message
2. Master records to progress.txt
3. Task marked as BLOCKED
4. Execution continues with other tasks
