"""
Agent Manager Service
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class AgentStatus:
    id: str
    status: str  # idle, running, blocked, stopped
    current_task: Optional[str] = None
    started_at: Optional[str] = None
    completed_steps: List[str] = None


class AgentManager:
    """
    Agent Manager Service

    Manages agent pool and execution coordination.
    """

    def __init__(self, max_agents: int = 4):
        self.max_agents = max_agents
        self._agents: Dict[str, AgentStatus] = {}

    def create_agent(self, agent_id: str) -> AgentStatus:
        """Create a new agent"""
        agent = AgentStatus(
            id=agent_id,
            status="idle",
            completed_steps=[],
        )
        self._agents[agent_id] = agent
        return agent

    def get_agent(self, agent_id: str) -> Optional[AgentStatus]:
        """Get agent status"""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentStatus]:
        """List all agents"""
        return list(self._agents.values())

    def assign_task(self, agent_id: str, task_id: str) -> bool:
        """Assign a task to an agent"""
        if agent_id not in self._agents:
            return False

        agent = self._agents[agent_id]
        agent.status = "running"
        agent.current_task = task_id
        agent.started_at = datetime.now().isoformat()
        return True

    def complete_task(self, agent_id: str) -> bool:
        """Mark agent task as complete"""
        if agent_id not in self._agents:
            return False

        agent = self._agents[agent_id]
        agent.status = "idle"
        agent.current_task = None
        agent.started_at = None
        return True

    def block_agent(self, agent_id: str, reason: str) -> bool:
        """Block an agent"""
        if agent_id not in self._agents:
            return False

        agent = self._agents[agent_id]
        agent.status = "blocked"
        return True

    def get_available_agent(self) -> Optional[str]:
        """Get an available agent"""
        for agent_id, agent in self._agents.items():
            if agent.status == "idle":
                return agent_id
        return None
