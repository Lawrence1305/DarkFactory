"""
Task data models
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class TestStrategy(Enum):
    """Validation test strategy"""
    AUTO = "auto"
    BROWSER = "browser"
    LINT = "lint"
    UNIT = "unit"


@dataclass
class Task:
    """
    Task definition

    A task is the unit of work in DarkFactory. Each task should be
    small enough to be completed independently and verifiable.
    """
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    steps: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 3  # 1 = highest
    dependencies: List[str] = field(default_factory=list)  # task IDs
    skills_required: List[str] = field(default_factory=list)
    test_strategy: TestStrategy = TestStrategy.AUTO
    passes: bool = False
    blocked_reason: Optional[str] = None
    estimated_duration: int = 30  # minutes
    estimated_tokens: int = 5000
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        d = asdict(self)
        d["status"] = self.status.value
        d["test_strategy"] = self.test_strategy.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create from dictionary"""
        if isinstance(data.get("status"), str):
            data["status"] = TaskStatus(data["status"])
        if isinstance(data.get("test_strategy"), str):
            data["test_strategy"] = TestStrategy(data["test_strategy"])
        return cls(**data)

    def update_status(self, status: TaskStatus, blocked_reason: Optional[str] = None):
        """Update task status"""
        self.status = status
        self.updated_at = datetime.now().isoformat()
        if blocked_reason:
            self.blocked_reason = blocked_reason
        if status == TaskStatus.COMPLETED:
            self.completed_at = datetime.now().isoformat()
            self.passes = True


@dataclass
class TaskResult:
    """
    Task execution result
    """
    task_id: str
    success: bool
    output: str = ""
    errors: List[str] = field(default_factory=list)
    tool_call_count: int = 0
    attempts: int = 1
    tokens_used: int = 0
    duration_seconds: float = 0.0
    skills_created: List[str] = field(default_factory=list)
    validation_results: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class DependencyEdge:
    """Represents a dependency between tasks"""
    from_task: str
    to_task: str
    dependency_type: str = "finish_to_start"  # finish_to_start, start_to_start, etc.


@dataclass
class TaskNode:
    """
    Task node for critical path analysis
    """
    task_id: str
    duration: int  # minutes
    earliest_start: int = 0  # ES
    earliest_finish: int = 0  # EF
    latest_start: int = 0  # LS
    latest_finish: int = 0  # LF
    slack: int = 0  # LF - EF
    is_critical: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
