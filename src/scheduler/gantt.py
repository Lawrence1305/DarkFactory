"""
Gantt Chart Generator
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..core.task import Task
from .critical_path import ActivityNetwork, ScheduledTask, CriticalPathAnalyzer


@dataclass
class GanttTask:
    """Single task in Gantt chart"""
    task_id: str
    title: str
    start: int  # minutes from project start
    duration: int  # minutes
    end: int  # start + duration
    is_critical: bool = False
    status: str = "pending"  # pending / in_progress / completed / blocked
    progress: float = 0.0  # 0.0 to 1.0
    assigned_agents: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class GanttMilestone:
    """Milestone marker"""
    id: str
    name: str
    time: int  # minutes from project start
    depends_on: List[str] = field(default_factory=list)


@dataclass
class GanttChart:
    """
    Gantt chart data structure
    """
    tasks: List[GanttTask] = field(default_factory=list)
    milestones: List[GanttMilestone] = field(default_factory=list)
    start_time: int = 0  # minutes from project start
    end_time: int = 0  # minutes from project start
    project_start_date: Optional[datetime] = None
    project_end_date: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "tasks": [
                {
                    "id": t.task_id,
                    "title": t.title,
                    "start": t.start,
                    "duration": t.duration,
                    "end": t.end,
                    "is_critical": t.is_critical,
                    "status": t.status,
                    "progress": t.progress,
                    "assigned_agents": t.assigned_agents,
                    "dependencies": t.dependencies,
                }
                for t in self.tasks
            ],
            "milestones": [
                {
                    "id": m.id,
                    "name": m.name,
                    "time": m.time,
                    "depends_on": m.depends_on,
                }
                for m in self.milestones
            ],
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class GanttTimeline:
    """Timeline configuration for Gantt chart"""
    start: int = 0  # minutes
    end: int = 0  # minutes
    tick_interval: int = 60  # minutes per tick
    unit: str = "hours"  # hours, days, weeks

    def time_to_offset(self, time: int) -> float:
        """Convert time to pixel offset"""
        return (time - self.start) / self.tick_interval

    def offset_to_time(self, offset: float) -> int:
        """Convert pixel offset to time"""
        return int(self.start + offset * self.tick_interval)

    def format_tick(self, time: int) -> str:
        """Format tick label"""
        if self.unit == "hours":
            hours = time // 60
            return f"{hours:02d}:00"
        elif self.unit == "days":
            days = time // (60 * 24)
            hours = (time % (60 * 24)) // 60
            return f"D{days+1} {hours:02d}:00"
        return f"{time}m"


class GanttChartGenerator:
    """
    Gantt Chart Generator

    Generates Gantt chart data from tasks and activity network.
    Supports multiple timeline scales (hours, days, weeks).
    """

    def __init__(self):
        self._critical_path_analyzer = CriticalPathAnalyzer()

    def generate(
        self,
        tasks: List[Task],
        network: Optional[ActivityNetwork] = None,
        project_start: Optional[datetime] = None,
        timeline_unit: str = "hours",
    ) -> GanttChart:
        """
        Generate Gantt chart from tasks

        Args:
            tasks: List of tasks
            network: Optional pre-computed activity network
            project_start: Optional project start date
            timeline_unit: Timeline unit ("hours", "days")

        Returns:
            GanttChart
        """
        # Analyze critical path if network not provided
        if network is None:
            network = self._critical_path_analyzer.analyze(tasks)

        # Calculate project timeline
        start_time = 0
        end_time = max(n.earliest_finish for n in network.nodes) if network.nodes else 0

        # Create node map for quick lookup
        node_map = {n.task_id: n for n in network.nodes}
        task_map = {t.id: t for t in tasks}

        # Generate Gantt tasks
        gantt_tasks = []
        for node in network.nodes:
            task = task_map.get(node.task_id)
            task_title = task.title if task else node.task_id
            task_status = task.status.value if task else "pending"
            task_steps = task.steps if task else []
            task_progress = len([s for s in task_steps if s]) / max(len(task_steps), 1) if task_steps else 0

            # Get dependencies
            deps = network.reverse_adjacency.get(node.task_id, [])

            gantt_task = GanttTask(
                task_id=node.task_id,
                title=task_title,
                start=node.earliest_start,
                duration=node.duration,
                end=node.earliest_finish,
                is_critical=node.is_critical,
                status=task_status,
                progress=task_progress,
                dependencies=deps,
            )
            gantt_tasks.append(gantt_task)

        # Calculate tick interval based on total duration
        tick_interval = self._calculate_tick_interval(start_time, end_time, timeline_unit)

        # Generate milestones
        milestones = self._generate_milestones(network, tasks)

        return GanttChart(
            tasks=gantt_tasks,
            milestones=milestones,
            start_time=start_time,
            end_time=end_time,
            project_start_date=project_start,
            project_end_date=project_start + timedelta(minutes=end_time) if project_start else None,
        )

    def _calculate_tick_interval(self, start: int, end: int, unit: str) -> int:
        """Calculate appropriate tick interval"""
        duration = end - start

        if unit == "hours":
            # Aim for ~20-40 ticks
            if duration < 60:  # < 1 hour
                return 10  # 10 minutes
            elif duration < 240:  # < 4 hours
                return 30  # 30 minutes
            elif duration < 1440:  # < 24 hours
                return 60  # 1 hour
            else:
                return 240  # 4 hours
        elif unit == "days":
            return 60 * 24  # 1 day
        elif unit == "weeks":
            return 60 * 24 * 7  # 1 week

        return 60  # Default 1 hour

    def _generate_milestones(
        self,
        network: ActivityNetwork,
        tasks: List[Task],
    ) -> List[GanttMilestone]:
        """
        Generate milestones from task completion points

        Milestones are placed at:
        1. End of critical path tasks
        2. Tasks with no dependents (end points)
        """
        milestones = []
        task_ids = {t.id for t in tasks}

        # Find end points (tasks with no dependents)
        for node in network.nodes:
            dependents = network.adjacency.get(node.task_id, [])
            if not dependents and dependents is not None:
                # This is an end point
                milestones.append(GanttMilestone(
                    id=f"milestone-{node.task_id}",
                    name=f"Complete: {node.task_id}",
                    time=node.earliest_finish,
                    depends_on=[node.task_id],
                ))

        # Sort milestones by time
        milestones.sort(key=lambda m: m.time)

        return milestones

    def generate_timeline(self, gantt: GanttChart, unit: str = "hours") -> GanttTimeline:
        """Generate timeline configuration"""
        tick_interval = self._calculate_tick_interval(
            gantt.start_time,
            gantt.end_time,
            unit,
        )

        return GanttTimeline(
            start=gantt.start_time,
            end=gantt.end_time,
            tick_interval=tick_interval,
            unit=unit,
        )

    def export_for_d3(
        self,
        gantt: GanttChart,
    ) -> Dict[str, Any]:
        """
        Export Gantt chart data in D3.js compatible format

        Returns:
            Dictionary with nodes and links for D3.js
        """
        nodes = []
        for task in gantt.tasks:
            nodes.append({
                "id": task.task_id,
                "name": task.title,
                "start": task.start,
                "duration": task.duration,
                "end": task.end,
                "critical": task.is_critical,
                "status": task.status,
                "progress": task.progress,
                "level": 0,  # Would calculate actual level for hierarchical layout
            })

        links = []
        for task in gantt.tasks:
            for dep in task.dependencies:
                links.append({
                    "source": dep,
                    "target": task.task_id,
                })

        return {
            "nodes": nodes,
            "links": links,
            "timeline": {
                "start": gantt.start_time,
                "end": gantt.end_time,
            },
        }

    def export_for_react_flow(
        self,
        gantt: GanttChart,
    ) -> Dict[str, Any]:
        """
        Export Gantt chart data in React Flow compatible format

        Returns:
            Dictionary with nodes and edges for React Flow
        """
        # Calculate node positions
        # Group tasks by their start time for vertical alignment
        start_groups: Dict[int, List[GanttTask]] = {}
        for task in gantt.tasks:
            if task.start not in start_groups:
                start_groups[task.start] = []
            start_groups[task.start].append(task)

        # Assign vertical positions
        node_positions: Dict[str, int] = {}
        y_offset = 0
        for start_time in sorted(start_groups.keys()):
            for i, task in enumerate(start_groups[start_time]):
                node_positions[task.task_id] = y_offset + i * 80
            y_offset += len(start_groups[start_time]) * 80 + 40

        nodes = []
        for task in gantt.tasks:
            x = task.start * 2  # Scale factor
            y = node_positions.get(task.task_id, 0)

            nodes.append({
                "id": task.task_id,
                "type": "taskNode",
                "position": {"x": x, "y": y},
                "data": {
                    "title": task.title,
                    "duration": task.duration,
                    "is_critical": task.is_critical,
                    "status": task.status,
                    "progress": task.progress,
                },
            })

        edges = []
        for task in gantt.tasks:
            for dep in task.dependencies:
                source_x = task.start * 2
                target_x = node_positions.get(task.task_id, 0)
                edges.append({
                    "id": f"{dep}->{task.task_id}",
                    "source": dep,
                    "target": task.task_id,
                    "type": "smoothstep",
                    "animated": task.is_critical,
                })

        return {
            "nodes": nodes,
            "edges": edges,
        }
