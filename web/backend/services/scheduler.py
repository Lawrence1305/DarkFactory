"""
Scheduler Service
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class SchedulerService:
    """
    Scheduler Service

    Manages task scheduling and execution coordination.
    """

    def __init__(self):
        self._scheduled_tasks: Dict[str, Dict] = {}

    def schedule_task(
        self,
        task_id: str,
        project_id: str,
        start_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Schedule a task for execution"""
        schedule_id = f"{project_id}_{task_id}"

        self._scheduled_tasks[schedule_id] = {
            "task_id": task_id,
            "project_id": project_id,
            "scheduled_time": start_time or datetime.now(),
            "agent_id": agent_id,
            "status": "scheduled",
        }

        return self._scheduled_tasks[schedule_id]

    def get_schedule(self, project_id: str) -> List[Dict]:
        """Get all scheduled tasks for a project"""
        return [
            s for s in self._scheduled_tasks.values()
            if s["project_id"] == project_id
        ]

    def cancel_schedule(self, task_id: str, project_id: str) -> bool:
        """Cancel a scheduled task"""
        schedule_id = f"{project_id}_{task_id}"
        if schedule_id in self._scheduled_tasks:
            del self._scheduled_tasks[schedule_id]
            return True
        return False
