"""
Scheduler Optimizer - optimize agent scheduling
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
import heapq

from ..core.task import Task
from .critical_path import ActivityNetwork, ScheduledTask, CriticalPathAnalyzer


@dataclass
class ScheduledTask:
    """Task with scheduled time and agent assignment"""
    task_id: str
    title: str = ""
    start_time: int = 0  # minutes
    end_time: int = 0
    assigned_agent_id: Optional[str] = None
    parallel_tasks: List[str] = field(default_factory=list)
    is_critical: bool = False
    priority: int = 3


@dataclass
class AgentAssignment:
    """Assignment of tasks to an agent"""
    agent_id: str
    task_ids: List[str] = field(default_factory=list)
    schedule: List[Tuple[int, str]] = field(default_factory=list)  # (time, event) events


@dataclass
class ScheduleResult:
    """Result of schedule optimization"""
    agent_count_needed: int
    estimated_total_duration: int
    agent_assignments: List[AgentAssignment]
    schedule: List[ScheduledTask]
    critical_path: List[str]
    idle_times: Dict[str, List[Tuple[int, int]]]  # agent_id -> [(start, end), ...]
    utilization: float  # 0.0 to 1.0


class SchedulerOptimizer:
    """
    Scheduler Optimizer

    Optimizes task scheduling for multi-agent execution.
    Uses critical path analysis and greedy scheduling.

    Algorithm:
    1. Analyze critical path
    2. Schedule critical tasks first
    3. Greedily fill non-critical tasks in idle time
    4. Calculate optimal agent count
    """

    def __init__(self):
        self._critical_path_analyzer = CriticalPathAnalyzer()
        self._network: Optional[ActivityNetwork] = None
        self._tasks: Dict[str, Task] = {}

    def optimize(
        self,
        tasks: List[Task],
        max_agents: int = 4,
        prioritize_critical: bool = True,
    ) -> ScheduleResult:
        """
        Optimize schedule for given tasks

        Args:
            tasks: List of tasks to schedule
            max_agents: Maximum number of agents to use
            prioritize_critical: Whether to prioritize critical path tasks

        Returns:
            ScheduleResult with optimized schedule
        """
        # Build task map
        self._tasks = {t.id: t for t in tasks}

        # Analyze critical path
        self._network = self._critical_path_analyzer.analyze(tasks)

        # Get critical path
        critical_path = self._critical_path_analyzer.get_critical_path()

        # Calculate minimum agents needed
        min_agents = self._critical_path_analyzer.calculate_agent_requirements()

        # Use at most max_agents, at least min_agents
        agent_count = min(max_agents, max(min_agents, 1))

        # Create agent pools
        agent_pools: Dict[int, List[int]] = {i: [] for i in range(agent_count)}  # agent_id -> available_time
        task_schedules: Dict[str, ScheduledTask] = {}

        # Get all task nodes sorted by priority and dependency
        sorted_nodes = self._sort_by_priority_and_deps(
            self._network.nodes,
            critical_path,
            prioritize_critical,
        )

        # Schedule tasks
        for node in sorted_nodes:
            task = self._tasks.get(node.task_id)
            if not task:
                continue

            # Find best available agent
            best_agent = self._find_best_agent(
                agent_pools,
                node,
                self._network,
            )

            if best_agent is None:
                # No agent available - shouldn't happen with proper agent count
                continue

            # Calculate task times
            start_time = agent_pools[best_agent]
            end_time = start_time + node.duration

            # Update agent pool
            agent_pools[best_agent] = end_time

            # Create scheduled task
            scheduled = ScheduledTask(
                task_id=node.task_id,
                title=task.title,
                start_time=start_time,
                end_time=end_time,
                assigned_agent_id=f"agent-{best_agent}",
                is_critical=node.is_critical,
                priority=task.priority,
            )

            task_schedules[node.task_id] = scheduled

        # Calculate parallel tasks for each scheduled task
        self._calculate_parallel_tasks(task_schedules)

        # Create agent assignments
        agent_assignments = self._create_agent_assignments(agent_pools, task_schedules)

        # Calculate idle times
        idle_times = self._calculate_idle_times(
            agent_pools,
            task_schedules,
            self._critical_path_analyzer.get_total_duration(),
        )

        # Calculate utilization
        total_task_time = sum(s.end_time - s.start_time for s in task_schedules.values())
        total_available_time = agent_count * self._critical_path_analyzer.get_total_duration()
        utilization = total_task_time / total_available_time if total_available_time > 0 else 0

        return ScheduleResult(
            agent_count_needed=agent_count,
            estimated_total_duration=self._critical_path_analyzer.get_total_duration(),
            agent_assignments=agent_assignments,
            schedule=list(task_schedules.values()),
            critical_path=critical_path,
            idle_times=idle_times,
            utilization=utilization,
        )

    def _sort_by_priority_and_deps(
        self,
        nodes: List[Any],
        critical_path: List[str],
        prioritize_critical: bool,
    ) -> List[Any]:
        """
        Sort nodes by priority and dependency order
        """
        # Create dependency count map
        dep_counts: Dict[str, int] = {}
        for node in nodes:
            dep_counts[node.task_id] = len(
                self._network.reverse_adjacency.get(node.task_id, [])
            ) if self._network else 0

        # Sort by: dependencies first, then priority
        return sorted(
            nodes,
            key=lambda n: (
                dep_counts.get(n.task_id, 0),  # Tasks with fewer deps first
                -n.duration if prioritize_critical and n.is_critical else 0,
                self._tasks.get(n.task_id, Task(id="")).priority,
            ),
        )

    def _find_best_agent(
        self,
        agent_pools: Dict[int, int],  # agent_id -> available_time
        node: Any,  # TaskNode
        network: ActivityNetwork,
    ) -> Optional[int]:
        """
        Find the best available agent for a task

        Best = earliest available, considering dependencies
        """
        best_agent = None
        earliest_time = float('inf')

        for agent_id, available_time in agent_pools.items():
            # Check if all dependencies are satisfied by this time
            deps = network.reverse_adjacency.get(node.task_id, [])
            dep_ready_time = 0

            for dep_id in deps:
                # Find the scheduled end time of dependency
                # This is simplified - real implementation would check actual schedules
                for other_node in network.nodes:
                    if other_node.task_id == dep_id:
                        dep_ready_time = max(dep_ready_time, other_node.earliest_finish)
                        break

            # This agent can start when both they're available AND deps are ready
            start_time = max(available_time, dep_ready_time)

            if start_time < earliest_time:
                earliest_time = start_time
                best_agent = agent_id

        if best_agent is not None:
            # Update to return the actual start time
            agent_pools[best_agent] = earliest_time

        return best_agent

    def _calculate_parallel_tasks(
        self,
        task_schedules: Dict[str, ScheduledTask],
    ) -> None:
        """Calculate which tasks run in parallel"""
        for task_id, scheduled in task_schedules.items():
            parallel = []
            for other_id, other_scheduled in task_schedules.items():
                if other_id == task_id:
                    continue
                # Check time overlap
                if (scheduled.start_time < other_scheduled.end_time and
                    scheduled.end_time > other_scheduled.start_time):
                    parallel.append(other_id)
            scheduled.parallel_tasks = parallel

    def _create_agent_assignments(
        self,
        agent_pools: Dict[int, int],
        task_schedules: Dict[str, ScheduledTask],
    ) -> List[AgentAssignment]:
        """Create agent assignment records"""
        assignments: Dict[int, AgentAssignment] = {}

        for agent_id in agent_pools.keys():
            assignments[agent_id] = AgentAssignment(agent_id=f"agent-{agent_id}")

        for scheduled in task_schedules.values():
            if scheduled.assigned_agent_id:
                agent_num = int(scheduled.assigned_agent_id.split("-")[1])
                if agent_num in assignments:
                    assignments[agent_num].task_ids.append(scheduled.task_id)
                    assignments[agent_num].schedule.append(
                        (scheduled.start_time, f"start:{scheduled.task_id}")
                    )
                    assignments[agent_num].schedule.append(
                        (scheduled.end_time, f"end:{scheduled.task_id}")
                    )

        # Sort schedules by time
        for assignment in assignments.values():
            assignment.schedule.sort(key=lambda x: x[0])

        return list(assignments.values())

    def _calculate_idle_times(
        self,
        agent_pools: Dict[int, int],
        task_schedules: Dict[str, ScheduledTask],
        total_duration: int,
    ) -> Dict[str, List[Tuple[int, int]]]:
        """Calculate idle times for each agent"""
        idle_times: Dict[str, List[Tuple[int, int]]] = {}

        for agent_id, end_time in agent_pools.items():
            agent_id_str = f"agent-{agent_id}"
            idle_times[agent_id_str] = []

            # Find gaps in agent's schedule
            events: List[Tuple[int, str]] = []
            for scheduled in task_schedules.values():
                if scheduled.assigned_agent_id == agent_id_str:
                    events.append((scheduled.start_time, "start"))
                    events.append((scheduled.end_time, "end"))

            events.sort(key=lambda x: x[0])

            # Calculate gaps
            last_end = 0
            for time, event_type in events:
                if event_type == "start" and time > last_end:
                    idle_times[agent_id_str].append((last_end, time))
                if event_type == "end":
                    last_end = time

            # Gap at end
            if last_end < total_duration:
                idle_times[agent_id_str].append((last_end, total_duration))

        return idle_times

    def get_schedule_statistics(self, result: ScheduleResult) -> Dict[str, Any]:
        """Get statistics about the schedule"""
        return {
            "agent_count": result.agent_count_needed,
            "total_duration": result.estimated_total_duration,
            "utilization": f"{result.utilization * 100:.1f}%",
            "critical_path_length": len(result.critical_path),
            "critical_path_tasks": result.critical_path,
            "parallel_execution_gain": self._calculate_parallel_gain(result),
        }

    def _calculate_parallel_gain(self, result: ScheduleResult) -> float:
        """Calculate time saved due to parallelization"""
        # Compare sequential time vs parallel time
        sequential_time = sum(
            s.end_time - s.start_time for s in result.schedule
        )
        parallel_time = result.estimated_total_duration

        if parallel_time == 0:
            return 0.0

        return (sequential_time / parallel_time) - 1.0  # e.g., 2.5 = 250% faster
