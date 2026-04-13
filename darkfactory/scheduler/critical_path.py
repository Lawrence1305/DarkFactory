"""
Critical Path Analyzer - CPM (Critical Path Method) implementation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum

from ..core.task import Task, TaskNode, DependencyEdge


class TaskNodeState(Enum):
    """Task node state for visualization"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class ScheduledTask:
    """Task with scheduled time and agent assignment"""
    task_id: str
    title: str
    start_time: int  # minutes from project start
    end_time: int
    assigned_agent_id: Optional[str] = None
    parallel_tasks: List[str] = field(default_factory=list)
    is_critical: bool = False
    state: TaskNodeState = TaskNodeState.PENDING


@dataclass
class ScheduleResult:
    """Result of scheduling optimization"""
    agent_count_needed: int  # Theoretical minimum agents
    estimated_total_duration: int  # minutes
    schedule: List[ScheduledTask]
    critical_path: List[str]  # task IDs on critical path
    parallel_opportunities: List[Tuple[str, str]]  # tasks that can run in parallel


class CriticalPathAnalyzer:
    """
    Critical Path Analyzer using CPM (Critical Path Method)

    Features:
    1. Forward pass: Calculate EET (Earliest Event Time)
    2. Backward pass: Calculate LET (Latest Event Time)
    3. Calculate slack (LF - EF)
    4. Identify critical path (slack = 0)
    5. Find parallelization opportunities
    6. Calculate minimum agent requirements
    """

    def __init__(self):
        self._network: Optional["ActivityNetwork"] = None
        self._nodes_map: Dict[str, TaskNode] = {}

    def analyze(
        self,
        tasks: List[Task],
        dependencies: Optional[List[DependencyEdge]] = None,
    ) -> "ActivityNetwork":
        """
        Perform critical path analysis

        Args:
            tasks: List of tasks
            dependencies: Optional explicit dependencies

        Returns:
            ActivityNetwork with calculated ES, EF, LS, LF, slack
        """
        # Build dependency edges from tasks
        if dependencies is None:
            dependencies = []
            for task in tasks:
                for dep_id in task.dependencies:
                    dependencies.append(DependencyEdge(
                        from_task=dep_id,
                        to_task=task.id,
                    ))

        # Build adjacency lists
        adjacency = {t.id: [] for t in tasks}
        reverse_adj = {t.id: [] for t in tasks}

        for dep in dependencies:
            if dep.from_task in adjacency and dep.to_task in reverse_adj:
                adjacency[dep.from_task].append(dep.to_task)
                reverse_adj[dep.to_task].append(dep.from_task)

        # Create task nodes
        nodes = []
        for task in tasks:
            node = TaskNode(
                task_id=task.id,
                duration=task.estimated_duration,
            )
            nodes.append(node)

        self._nodes_map = {n.task_id: n for n in nodes}
        self._network = ActivityNetwork(
            nodes=nodes,
            edges=dependencies,
            adjacency=adjacency,
            reverse_adjacency=reverse_adj,
        )

        # Topological sort
        sorted_ids = self._topological_sort()

        # Forward pass
        self._forward_pass(sorted_ids)

        # Backward pass
        self._backward_pass(sorted_ids)

        # Calculate slack and critical path
        self._calculate_slack()

        return self._network

    def _topological_sort(self) -> List[str]:
        """Topological sort of tasks"""
        visited: Set[str] = set()
        result: List[str] = []

        def visit(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)

            # Visit all dependencies first
            for dep in self._network.reverse_adjacency.get(task_id, []):
                visit(dep)

            result.append(task_id)

        for node in self._network.nodes:
            visit(node.task_id)

        return result

    def _forward_pass(self, sorted_ids: List[str]) -> None:
        """
        Forward pass: Calculate Earliest Event Times

        EET[j] = max(EET[i] + duration[i]) for all i -> j
        """
        for task_id in sorted_ids:
            node = self._nodes_map[task_id]
            deps = self._network.reverse_adjacency.get(task_id, [])

            if not deps:
                node.earliest_start = 0
            else:
                node.earliest_start = max(
                    self._nodes_map[dep_id].earliest_finish
                    for dep_id in deps
                )

            node.earliest_finish = node.earliest_start + node.duration

    def _backward_pass(self, sorted_ids: List[str]) -> None:
        """
        Backward pass: Calculate Latest Event Times

        LET[i] = min(LET[j] - duration[i]) for all i -> j
        """
        # Find project end time
        project_end = max(n.earliest_finish for n in self._network.nodes)

        # Process in reverse topological order
        for task_id in reversed(sorted_ids):
            node = self._nodes_map[task_id]
            dependents = self._network.adjacency.get(task_id, [])

            if not dependents:
                node.latest_finish = project_end
            else:
                node.latest_finish = min(
                    self._nodes_map[dep_id].latest_start
                    for dep_id in dependents
                )

            node.latest_start = node.latest_finish - node.duration

    def _calculate_slack(self) -> None:
        """
        Calculate slack and identify critical path

        Slack = LET - EET
        Critical path: tasks with slack = 0
        """
        for node in self._network.nodes:
            node.slack = node.latest_start - node.earliest_start
            node.is_critical = node.slack == 0

    def get_critical_path(self) -> List[str]:
        """Get list of task IDs on the critical path"""
        if not self._network:
            return []

        return [
            node.task_id for node in self._network.nodes
            if node.is_critical
        ]

    def get_total_duration(self) -> int:
        """Get total project duration"""
        if not self._network:
            return 0

        return max(node.earliest_finish for node in self._network.nodes)

    def calculate_agent_requirements(self) -> int:
        """
        Calculate minimum number of agents needed

        Find maximum parallelism at any time point.
        """
        if not self._network:
            return 1

        # Create timeline of all start/end events
        events: List[Tuple[int, str, str]] = []  # (time, event_type, task_id)

        for node in self._network.nodes:
            events.append((node.earliest_start, "start", node.task_id))
            events.append((node.earliest_finish, "end", node.task_id))

        # Sort: by time, ends before starts at same time
        events.sort(key=lambda e: (e[0], e[1] == "start"))

        max_parallel = 0
        current_parallel = 0
        active_tasks: Set[str] = set()

        for time, event_type, task_id in events:
            if event_type == "start":
                active_tasks.add(task_id)
                current_parallel = len(active_tasks)
            else:
                active_tasks.discard(task_id)

            max_parallel = max(max_parallel, current_parallel)

        return max(1, max_parallel)

    def find_parallel_opportunities(self) -> List[Tuple[str, str]]:
        """
        Find pairs of tasks that can run in parallel

        Two tasks can run in parallel if:
        1. Neither depends on the other
        2. They don't overlap in time (given agent constraints)
        """
        if not self._network:
            return []

        opportunities = []

        # Find tasks that start at the same time or overlap
        for i, node_a in enumerate(self._network.nodes):
            for node_b in self._network.nodes[i + 1:]:
                # Check if they can run in parallel (non-blocking overlap)
                if self._can_run_parallel(node_a, node_b):
                    opportunities.append((node_a.task_id, node_b.task_id))

        return opportunities

    def _can_run_parallel(self, node_a: TaskNode, node_b: TaskNode) -> bool:
        """Check if two tasks can theoretically run in parallel"""
        # Check dependency relationship
        # A depends on B means B must finish before A starts
        # So they can't be parallel if there's a dependency

        # Check if A depends on B
        if self._depends_on(node_a.task_id, node_b.task_id):
            return False

        # Check if B depends on A
        if self._depends_on(node_b.task_id, node_a.task_id):
            return False

        return True

    def _depends_on(self, task_id: str, potential_dep: str) -> bool:
        """Check if task_id depends on potential_dep (directly or transitively)"""
        visited: Set[str] = set()
        queue = [task_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            node = self._nodes_map.get(current)
            if not node:
                continue

            for dep_id in self._network.reverse_adjacency.get(current, []):
                if dep_id == potential_dep:
                    return True
                queue.append(dep_id)

        return False

    def generate_schedule(
        self,
        max_agents: int = 1,
        agent_assignments: Optional[Dict[str, str]] = None,
    ) -> List[ScheduledTask]:
        """
        Generate a scheduled task list

        Args:
            max_agents: Maximum number of agents to use
            agent_assignments: Optional dict mapping task_id to agent_id

        Returns:
            List of ScheduledTasks
        """
        if not self._network:
            return []

        scheduled = []
        agent_assignments = agent_assignments or {}

        # Sort nodes by earliest start time
        sorted_nodes = sorted(
            self._network.nodes,
            key=lambda n: (n.earliest_start, -n.duration if n.is_critical else n.duration)
        )

        for node in sorted_nodes:
            scheduled_task = ScheduledTask(
                task_id=node.task_id,
                title=node.task_id,  # Would look up actual title
                start_time=node.earliest_start,
                end_time=node.earliest_finish,
                assigned_agent_id=agent_assignments.get(node.task_id),
                is_critical=node.is_critical,
            )

            # Find parallel tasks
            for other_node in sorted_nodes:
                if other_node.task_id == node.task_id:
                    continue
                # Tasks overlap in time
                if (other_node.earliest_start < node.earliest_finish and
                    other_node.earliest_finish > node.earliest_start):
                    scheduled_task.parallel_tasks.append(other_node.task_id)

            scheduled.append(scheduled_task)

        return scheduled

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        if not self._network:
            return {}

        return {
            "nodes": [
                {
                    "task_id": n.task_id,
                    "duration": n.duration,
                    "earliest_start": n.earliest_start,
                    "earliest_finish": n.earliest_finish,
                    "latest_start": n.latest_start,
                    "latest_finish": n.latest_finish,
                    "slack": n.slack,
                    "is_critical": n.is_critical,
                }
                for n in self._network.nodes
            ],
            "edges": [
                {"from": e.from_task, "to": e.to_task}
                for e in self._network.edges
            ],
            "critical_path": self.get_critical_path(),
            "total_duration": self.get_total_duration(),
            "agent_requirements": self.calculate_agent_requirements(),
            "parallel_opportunities": self.find_parallel_opportunities(),
        }


@dataclass
class ActivityNetwork:
    """
    Activity Network graph
    """
    nodes: List[TaskNode] = field(default_factory=list)
    edges: List[DependencyEdge] = field(default_factory=list)
    adjacency: Dict[str, List[str]] = field(default_factory=dict)
    reverse_adjacency: Dict[str, List[str]] = field(default_factory=dict)
