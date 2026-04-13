"""
Agent Pool - Multi-agent parallel execution
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import uuid

from .task import Task, TaskResult


class AgentStatus(Enum):
    """Agent status"""
    IDLE = "idle"
    BUSY = "busy"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Agent:
    """
    Sub-agent for parallel task execution

    Each sub-agent has:
    - Independent context
    - Shared memory and skills (via RPC)
    - Task assignment
    """
    id: str = field(default_factory=lambda: f"agent-{uuid.uuid4().hex[:8]}")
    name: str = ""
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[Task] = None
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[TaskResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "current_task": self.current_task.id if self.current_task else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class AgentMessage:
    """
    Message between agents
    """
    type: str  # "result", "blocking", "skill_created", "memory_updated", "heartbeat"
    from_agent: str
    to_agent: Optional[str] = None  # None = broadcast
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "from": self.from_agent,
            "to": self.to_agent,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


class MessageBus:
    """
    Agent message bus for inter-agent communication

    Supports:
    - Publish/subscribe
    - Direct messages
    - Broadcast
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._broadcast_subscribers: List[Callable] = []
        self._message_history: List[AgentMessage] = []

    async def publish(self, message: AgentMessage) -> None:
        """
        Publish a message

        Args:
            message: AgentMessage to publish
        """
        self._message_history.append(message)

        if message.to_agent:
            # Direct message
            subscribers = self._subscribers.get(message.to_agent, [])
        else:
            # Broadcast
            subscribers = self._broadcast_subscribers.copy()

        for callback in subscribers:
            try:
                await callback(message)
            except Exception:
                pass  # Don't let callback errors break message bus

    def subscribe(
        self,
        agent_id: str,
        callback: Callable,
    ) -> None:
        """Subscribe to messages for a specific agent"""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(callback)

    def subscribe_broadcast(self, callback: Callable) -> None:
        """Subscribe to all broadcast messages"""
        self._broadcast_subscribers.append(callback)

    def unsubscribe(self, agent_id: str, callback: Callable) -> None:
        """Unsubscribe from messages"""
        if agent_id in self._subscribers:
            self._subscribers[agent_id] = [
                cb for cb in self._subscribers[agent_id]
                if cb != callback
            ]

    def get_history(
        self,
        agent_id: Optional[str] = None,
        message_type: Optional[str] = None,
    ) -> List[AgentMessage]:
        """Get message history"""
        messages = self._message_history

        if agent_id:
            messages = [
                m for m in messages
                if m.from_agent == agent_id or m.to_agent == agent_id
            ]

        if message_type:
            messages = [m for m in messages if m.type == message_type]

        return messages


class AgentPool:
    """
    Agent Pool Manager

    Manages a pool of sub-agents for parallel task execution.

    Features:
    - Spawn agents up to max_agents limit
    - Assign tasks based on dependencies
    - Track agent status
    - Handle inter-agent communication
    - Support task result aggregation
    """

    def __init__(
        self,
        max_agents: int = 4,
        message_bus: Optional[MessageBus] = None,
        workflow_executor: Optional[Any] = None,
    ):
        self.max_agents = max_agents
        self.message_bus = message_bus or MessageBus()
        self.workflow_executor = workflow_executor

        self._agents: Dict[str, Agent] = {}
        self._idle_agents: List[str] = []  # Queue of idle agent IDs
        self._busy_agents: Dict[str, Agent] = {}

        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def spawn(self, task: Task) -> Agent:
        """
        Spawn an agent for a task

        Args:
            task: Task to assign

        Returns:
            Spawned Agent
        """
        # Check if we can spawn a new agent
        if len(self._agents) >= self.max_agents:
            # Wait for an agent to become idle
            await self._wait_for_idle_agent()

        # Create new agent
        agent = Agent(
            name=f"Agent-{len(self._agents) + 1}",
            current_task=task,
            status=AgentStatus.BUSY,
            assigned_at=datetime.now(),
        )

        self._agents[agent.id] = agent
        self._busy_agents[agent.id] = agent

        if agent.id in self._idle_agents:
            self._idle_agents.remove(agent.id)

        return agent

    async def run_parallel(
        self,
        tasks: List[Task],
        max_agents: Optional[int] = None,
    ) -> List[TaskResult]:
        """
        Run tasks in parallel

        Args:
            tasks: List of tasks to run
            max_agents: Override max agents for this run

        Returns:
            List of TaskResults
        """
        if max_agents:
            original_max = self.max_agents
            self.max_agents = max_agents

        # Spawn agents for tasks
        agents = []
        for task in tasks:
            agent = await self.spawn(task)
            agents.append(agent)

        # Run all tasks concurrently
        run_tasks = []
        for agent in agents:
            task = asyncio.create_task(self._run_agent(agent))
            self._running_tasks[agent.id] = task
            run_tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*run_tasks, return_exceptions=True)

        # Restore max_agents
        if max_agents:
            self.max_agents = original_max

        # Process results
        task_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Task failed
                task_results.append(TaskResult(
                    task_id=tasks[i].id,
                    success=False,
                    errors=[str(result)],
                ))
            else:
                task_results.append(result)

        return task_results

    async def _run_agent(self, agent: Agent) -> TaskResult:
        """
        Run a single agent

        Args:
            agent: Agent to run

        Returns:
            TaskResult
        """
        if not agent.current_task:
            return TaskResult(
                task_id="",
                success=False,
                errors=["No task assigned to agent"],
            )

        task = agent.current_task
        start_time = datetime.now()

        try:
            # Execute workflow
            if self.workflow_executor:
                result = await self.workflow_executor.run(task)

                if result.blocked:
                    # Handle blocking
                    agent.status = AgentStatus.FAILED
                    return TaskResult(
                        task_id=task.id,
                        success=False,
                        errors=[result.blocked_reason or "Task blocked"],
                    )

                agent.result = result.task_result
                agent.status = AgentStatus.COMPLETED

                # Notify completion
                await self.message_bus.publish(AgentMessage(
                    type="result",
                    from_agent=agent.id,
                    payload={
                        "task_id": task.id,
                        "success": result.success,
                    },
                ))

                return result.task_result
            else:
                # No workflow executor - simulate execution
                await asyncio.sleep(0.1)  # Simulate work
                agent.status = AgentStatus.COMPLETED
                return TaskResult(
                    task_id=task.id,
                    success=True,
                    output="Simulated execution",
                )

        except Exception as e:
            agent.status = AgentStatus.FAILED
            return TaskResult(
                task_id=task.id,
                success=False,
                errors=[str(e)],
            )

        finally:
            agent.completed_at = datetime.now()
            self._release_agent(agent)

    async def _wait_for_idle_agent(self) -> None:
        """Wait for an agent to become idle"""
        while not self._idle_agents:
            await asyncio.sleep(0.1)

    def _release_agent(self, agent: Agent) -> None:
        """Release agent back to idle pool"""
        if agent.id in self._busy_agents:
            del self._busy_agents[agent.id]

        agent.status = AgentStatus.IDLE
        agent.current_task = None
        self._idle_agents.append(agent.id)

    def get_idle_agents(self) -> List[Agent]:
        """Get list of idle agents"""
        return [self._agents[a_id] for a_id in self._idle_agents]

    def get_busy_agents(self) -> List[Agent]:
        """Get list of busy agents"""
        return list(self._busy_agents.values())

    def get_all_agents(self) -> List[Agent]:
        """Get all agents"""
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self._agents.get(agent_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        for agent_id, running_task in self._running_tasks.items():
            agent = self._agents.get(agent_id)
            if agent and agent.current_task and agent.current_task.id == task_id:
                running_task.cancel()
                self._release_agent(agent)
                return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            "total_agents": len(self._agents),
            "idle_agents": len(self._idle_agents),
            "busy_agents": len(self._busy_agents),
            "max_agents": self.max_agents,
            "running_tasks": len(self._running_tasks),
        }

    async def shutdown(self) -> None:
        """Shutdown all agents"""
        for task in self._running_tasks.values():
            task.cancel()

        self._agents.clear()
        self._idle_agents.clear()
        self._busy_agents.clear()
        self._running_tasks.clear()
