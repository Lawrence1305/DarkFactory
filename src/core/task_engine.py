"""
Task Engine - manages task lifecycle
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from .task import Task, TaskStatus, TaskResult, DependencyEdge


class TaskEngine:
    """
    Core task engine - manages the complete task lifecycle

    Responsibilities:
    1. Load and validate task.json
    2. Select tasks based on dependencies and priority
    3. Execute tasks and capture results
    4. Update task status
    5. Trigger self-improvement (skill creation)
    """

    def __init__(
        self,
        task_store_path: Optional[Path] = None,
        workspace_path: Optional[Path] = None,
    ):
        self.task_store_path = task_store_path or Path("task.json")
        self.workspace_path = workspace_path or Path(".")
        self._tasks: Dict[str, Task] = {}
        self._current_task: Optional[Task] = None
        self._task_history: List[TaskResult] = []

    def load_tasks(self) -> List[Task]:
        """
        Load tasks from task.json

        Returns:
            List of Task objects
        """
        if not self.task_store_path.exists():
            return []

        with open(self.task_store_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tasks_data = data.get("tasks", [])
        self._tasks = {}

        for task_data in tasks_data:
            task = Task.from_dict(task_data)
            self._tasks[task.id] = task

        return list(self._tasks.values())

    def save_tasks(self) -> None:
        """Save tasks to task.json"""
        tasks_data = [task.to_dict() for task in self._tasks.values()]

        data = {
            "tasks": tasks_data,
            "updated_at": datetime.now().isoformat(),
        }

        with open(self.task_store_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_task(self, task: Task) -> None:
        """Add a task"""
        self._tasks[task.id] = task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self._tasks.get(task_id)

    def select_next_task(self) -> Optional[Task]:
        """
        Select the next task to execute

        Selection criteria (in order of priority):
        1. status == PENDING
        2. All dependencies are COMPLETED
        3. Highest priority (lowest number)

        Returns:
            Next Task to execute, or None if no task is ready
        """
        pending_tasks = [
            task for task in self._tasks.values()
            if task.status == TaskStatus.PENDING
        ]

        # Filter by completed dependencies
        ready_tasks = []
        for task in pending_tasks:
            deps_completed = all(
                self._tasks.get(dep_id, Task(status=TaskStatus.PENDING)).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if deps_completed:
                ready_tasks.append(task)

        if not ready_tasks:
            return None

        # Sort by priority (lower = higher priority)
        ready_tasks.sort(key=lambda t: t.priority)

        return ready_tasks[0]

    def select_ready_tasks(self) -> List[Task]:
        """
        Select all tasks that are ready to execute (dependencies met)

        Returns:
            List of ready tasks
        """
        pending_tasks = [
            task for task in self._tasks.values()
            if task.status == TaskStatus.PENDING
        ]

        ready_tasks = []
        for task in pending_tasks:
            deps_completed = all(
                self._tasks.get(dep_id, Task(status=TaskStatus.PENDING)).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if deps_completed:
                ready_tasks.append(task)

        # Sort by priority
        ready_tasks.sort(key=lambda t: t.priority)
        return ready_tasks

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        blocked_reason: Optional[str] = None,
    ) -> None:
        """Update task status"""
        task = self._tasks.get(task_id)
        if task:
            task.update_status(status, blocked_reason)
            self.save_tasks()

    def get_blocked_tasks(self) -> List[Task]:
        """Get all blocked tasks"""
        return [
            task for task in self._tasks.values()
            if task.status == TaskStatus.BLOCKED
        ]

    def get_completed_tasks(self) -> List[Task]:
        """Get all completed tasks"""
        return [
            task for task in self._tasks.values()
            if task.status == TaskStatus.COMPLETED
        ]

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks"""
        return [
            task for task in self._tasks.values()
            if task.status == TaskStatus.PENDING
        ]

    def get_in_progress_tasks(self) -> List[Task]:
        """Get all in-progress tasks"""
        return [
            task for task in self._tasks.values()
            if task.status == TaskStatus.IN_PROGRESS
        ]

    def get_statistics(self) -> Dict[str, int]:
        """Get task statistics"""
        return {
            "total": len(self._tasks),
            "pending": len(self.get_pending_tasks()),
            "in_progress": len(self.get_in_progress_tasks()),
            "completed": len(self.get_completed_tasks()),
            "blocked": len(self.get_blocked_tasks()),
        }

    def record_result(self, result: TaskResult) -> None:
        """Record task execution result"""
        self._task_history.append(result)

    def get_task_history(self) -> List[TaskResult]:
        """Get task execution history"""
        return self._task_history.copy()

    def clear_finished_tasks(self) -> None:
        """Clear completed tasks from memory (keep for history)"""
        # Tasks are kept in task.json for history
        pass

    def merge_tasks(self, tasks: List[Task]) -> None:
        """Merge tasks into the current task store"""
        for task in tasks:
            self._tasks[task.id] = task

    def remove_task(self, task_id: str) -> bool:
        """Remove a task"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False
