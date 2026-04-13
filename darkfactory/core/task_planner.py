"""
Task Planner - Human-computer collaboration for task planning
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum

from .task import Task, DependencyEdge, TaskNode


class PlanStatus(Enum):
    """Plan status"""
    DRAFT = "draft"
    PRESENTED = "presented"
    CONFIRMED = "confirmed"
    MODIFIED = "modified"


@dataclass
class PlanResult:
    """
    Result of task planning

    Contains the decomposed tasks, activity network, Gantt data,
    critical path analysis, and resource estimates.
    """
    status: PlanStatus = PlanStatus.DRAFT
    tasks: List[Task] = field(default_factory=list)
    dependencies: List[DependencyEdge] = field(default_factory=list)
    activity_network: Optional["ActivityNetwork"] = None
    gantt_data: Optional["GanttData"] = None
    critical_path: List[str] = field(default_factory=list)  # task IDs
    total_duration: int = 0  # minutes
    agent_requirements: int = 1  # theoretical minimum agents
    user_modifications: List[str] = field(default_factory=list)


@dataclass
class ActivityNetwork:
    """
    Activity Network for critical path analysis

    A directed acyclic graph where nodes are tasks and edges are dependencies.
    """
    nodes: List[TaskNode] = field(default_factory=list)
    edges: List[DependencyEdge] = field(default_factory=list)
    adjacency: Dict[str, List[str]] = field(default_factory=dict)  # task_id -> [dependent_task_ids]
    reverse_adjacency: Dict[str, List[str]] = field(default_factory=dict)  # task_id -> [dependency_task_ids]


@dataclass
class GanttData:
    """
    Gantt chart data for visualization
    """
    tasks: List["GanttTask"] = field(default_factory=list)
    milestones: List["Milestone"] = field(default_factory=list)
    start_time: int = 0  # minutes from project start
    end_time: int = 0  # minutes from project start


@dataclass
class GanttTask:
    """Single task in Gantt chart"""
    task_id: str
    title: str
    start: int  # minutes from project start
    duration: int  # minutes
    assigned_agents: int = 1
    is_critical: bool = False
    status: str = "pending"  # pending / in_progress / completed / blocked
    progress: float = 0.0  # 0.0 to 1.0


@dataclass
class Milestone:
    """Milestone in Gantt chart"""
    id: str
    name: str
    time: int  # minutes from project start
    depends_on: List[str] = field(default_factory=list)


class TaskPlanner:
    """
    Task Planner - Human-computer collaboration for task planning

    Key features:
    1. Natural language decomposition
    2. Activity network generation
    3. Critical path analysis
    4. Gantt chart generation
    5. Resource estimation
    6. User confirmation loop
    """

    DECOMPOSITION_PROMPT = """
You are a task decomposition expert. Break down the user's natural language
goal into independent, verifiable tasks.

## Input
User Goal: {goal}
Context: {context}

## Decomposition Principles
1. Each task must be independently completable and verifiable
2. Follow dependency order: base tasks first
3. Each task should have 3-7 steps
4. Distinguish UI tasks from backend tasks
5. Identify tasks requiring browser testing

## Task Fields
- id: Unique identifier (task-001, task-002, ...)
- title: Short title (max 50 chars)
- description: Detailed description
- steps: List of concrete steps
- priority: 1-4 (1 = highest)
- dependencies: List of task IDs this depends on
- skills_required: List of required skills
- test_strategy: "browser" | "lint" | "unit" | "auto"
- estimated_duration: Minutes to complete
- estimated_tokens: Estimated LLM tokens needed

## Output Format
Return a JSON array of task objects.
"""

    def __init__(
        self,
        llm_client: Optional[Any] = None,  # LLM client for natural language processing
        workspace_path: Optional[str] = None,
    ):
        self.llm_client = llm_client
        self.workspace_path = workspace_path or "."
        self._current_plan: Optional[PlanResult] = None

    async def plan(self, goal: str, context: str = "") -> PlanResult:
        """
        Create a task plan from natural language

        Args:
            goal: User's natural language goal
            context: Additional context (e.g., existing project info)

        Returns:
            PlanResult containing tasks, activity network, Gantt data, etc.
        """
        # Step 1: Decompose natural language to tasks
        tasks = await self._decompose(goal, context)

        # Step 2: Build activity network
        dependencies = self._extract_dependencies(tasks)
        network = self._build_activity_network(tasks, dependencies)

        # Step 3: Analyze critical path
        self._analyze_critical_path(network)

        # Step 4: Generate Gantt data
        gantt_data = self._generate_gantt(network)

        # Step 5: Estimate resources
        agent_count = self._calculate_agent_requirements(network)

        # Step 6: Calculate total duration
        total_duration = max(
            (node.earliest_finish for node in network.nodes),
            default=0
        )

        # Create plan result
        self._current_plan = PlanResult(
            status=PlanStatus.PRESENTED,
            tasks=tasks,
            dependencies=dependencies,
            activity_network=network,
            gantt_data=gantt_data,
            critical_path=[n.task_id for n in network.nodes if n.is_critical],
            total_duration=total_duration,
            agent_requirements=agent_count,
        )

        return self._current_plan

    async def _decompose(self, goal: str, context: str) -> List[Task]:
        """
        Decompose natural language goal into tasks

        If LLM client is available, use it. Otherwise, use simple heuristics.
        """
        if self.llm_client:
            return await self._llm_decompose(goal, context)
        return self._heuristic_decompose(goal)

    async def _llm_decompose(self, goal: str, context: str) -> List[Task]:
        """Use LLM to decompose tasks"""
        prompt = self.DECOMPOSITION_PROMPT.format(goal=goal, context=context)

        # This would call the LLM client
        # For now, return empty list
        return []

    def _heuristic_decompose(self, goal: str) -> List[Task]:
        """
        Simple heuristic decomposition when no LLM is available

        This is a fallback that creates basic tasks based on keywords.
        """
        tasks = []
        goal_lower = goal.lower()

        # Basic task structure
        task_id = 1

        # Project initialization
        tasks.append(Task(
            id=f"task-{task_id:03d}",
            title="Project Initialization",
            description=f"Initialize project based on goal: {goal}",
            steps=[
                "Create project structure",
                "Install dependencies",
                "Set up configuration files",
                "Initialize git repository"
            ],
            priority=1,
            estimated_duration=30,
        ))
        task_id += 1

        # Core features
        if any(kw in goal_lower for kw in ["用户", "user", "认证", "auth", "登录", "login"]):
            tasks.append(Task(
                id=f"task-{task_id:03d}",
                title="User Authentication",
                description="Implement user registration and login",
                steps=[
                    "Design user data model",
                    "Implement registration API",
                    "Implement login API",
                    "Create auth frontend components",
                    "Add session management"
                ],
                priority=2,
                dependencies=[f"task-{task_id-1:03d}"],
                test_strategy=TestStrategy.BROWSER,
                estimated_duration=60,
            ))
            task_id += 1

        if any(kw in goal_lower for kw in ["博客", "blog", "文章", "post", "content"]):
            tasks.append(Task(
                id=f"task-{task_id:03d}",
                title="Content Management",
                description="Implement blog post functionality",
                steps=[
                    "Design post data model",
                    "Implement CRUD API",
                    "Create post list page",
                    "Create post detail page",
                    "Add rich text editor"
                ],
                priority=3,
                dependencies=[f"task-{task_id-1:03d}"],
                test_strategy=TestStrategy.BROWSER,
                estimated_duration=90,
            ))
            task_id += 1

        # Default feature task if nothing matched
        if len(tasks) == 1:
            tasks.append(Task(
                id=f"task-{task_id:03d}",
                title="Core Feature Implementation",
                description=f"Implement core features for: {goal}",
                steps=[
                    "Analyze requirements",
                    "Design data models",
                    "Implement backend",
                    "Implement frontend",
                    "Test integration"
                ],
                priority=2,
                dependencies=[f"task-{task_id-1:03d}"],
                test_strategy=TestStrategy.AUTO,
                estimated_duration=120,
            ))

        return tasks

    def _extract_dependencies(self, tasks: List[Task]) -> List[DependencyEdge]:
        """Extract dependencies from tasks"""
        dependencies = []
        for task in tasks:
            for dep_id in task.dependencies:
                dependencies.append(DependencyEdge(
                    from_task=dep_id,
                    to_task=task.id,
                    dependency_type="finish_to_start"
                ))
        return dependencies

    def _build_activity_network(
        self,
        tasks: List[Task],
        dependencies: List[DependencyEdge]
    ) -> ActivityNetwork:
        """Build activity network from tasks and dependencies"""
        # Create task ID to index mapping
        task_ids = [t.id for t in tasks]

        # Build adjacency lists
        adjacency: Dict[str, List[str]] = {t.id: [] for t in tasks}
        reverse_adjacency: Dict[str, List[str]] = {t.id: [] for t in tasks}

        for dep in dependencies:
            if dep.from_task in adjacency and dep.to_task in reverse_adjacency:
                adjacency[dep.from_task].append(dep.to_task)
                reverse_adjacency[dep.to_task].append(dep.from_task)

        # Create task nodes
        nodes = []
        for task in tasks:
            node = TaskNode(
                task_id=task.id,
                duration=task.estimated_duration,
            )
            nodes.append(node)

        return ActivityNetwork(
            nodes=nodes,
            edges=dependencies,
            adjacency=adjacency,
            reverse_adjacency=reverse_adjacency,
        )

    def _analyze_critical_path(self, network: ActivityNetwork) -> None:
        """
        Analyze critical path using CPM (Critical Path Method)

        Forward pass: Calculate EET (Earliest Event Time)
        Backward pass: Calculate LET (Latest Event Time)
        Slack = LET - EET
        Critical path: tasks with slack = 0
        """
        nodes_map = {n.task_id: n for n in network.nodes}

        # Topological sort
        sorted_ids = self._topological_sort(network)

        # Forward pass: Calculate EET
        for task_id in sorted_ids:
            node = nodes_map[task_id]
            deps = network.reverse_adjacency.get(task_id, [])

            if not deps:
                node.earliest_start = 0
            else:
                node.earliest_start = max(
                    nodes_map[dep_id].earliest_finish
                    for dep_id in deps
                )

            node.earliest_finish = node.earliest_start + node.duration

        # Find project end time
        project_end = max(n.earliest_finish for n in network.nodes)

        # Backward pass: Calculate LET
        for task_id in reversed(sorted_ids):
            node = nodes_map[task_id]
            dependents = network.adjacency.get(task_id, [])

            if not dependents:
                node.latest_finish = project_end
            else:
                node.latest_finish = min(
                    nodes_map[dep_id].latest_start
                    for dep_id in dependents
                )

            node.latest_start = node.latest_finish - node.duration
            node.slack = node.latest_start - node.earliest_start
            node.is_critical = node.slack == 0

    def _topological_sort(self, network: ActivityNetwork) -> List[str]:
        """Topological sort of tasks"""
        visited = set()
        result = []

        def visit(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)
            for dep in network.reverse_adjacency.get(task_id, []):
                visit(dep)
            result.append(task_id)

        for node in network.nodes:
            visit(node.task_id)

        return result

    def _generate_gantt(self, network: ActivityNetwork) -> GanttData:
        """Generate Gantt chart data"""
        gantt_tasks = []
        nodes_map = {n.task_id: n for n in network.nodes}

        for node in network.nodes:
            gantt_tasks.append(GanttTask(
                task_id=node.task_id,
                title=node.task_id,  # Would be replaced with actual title
                start=node.earliest_start,
                duration=node.duration,
                is_critical=node.is_critical,
                status="pending",
            ))

        project_start = 0
        project_end = max(n.earliest_finish for n in network.nodes)

        return GanttData(
            tasks=gantt_tasks,
            milestones=[],
            start_time=project_start,
            end_time=project_end,
        )

    def _calculate_agent_requirements(self, network: ActivityNetwork) -> int:
        """
        Calculate minimum number of agents needed

        Find the maximum parallelism at any time point.
        """
        if not network.nodes:
            return 1

        # Create timeline of task start/end
        events = []
        for node in network.nodes:
            events.append((node.earliest_start, "start", node.task_id))
            events.append((node.earliest_finish, "end", node.task_id))

        # Sort by time, ends before starts at same time
        events.sort(key=lambda e: (e[0], e[1] == "start"))

        max_parallel = 0
        current_parallel = 0
        active_tasks = set()

        for time, event_type, task_id in events:
            if event_type == "start":
                active_tasks.add(task_id)
                current_parallel = len(active_tasks)
            else:
                active_tasks.discard(task_id)

            max_parallel = max(max_parallel, current_parallel)

        return max(1, max_parallel)

    def get_current_plan(self) -> Optional[PlanResult]:
        """Get the current plan"""
        return self._current_plan

    def confirm_plan(self) -> bool:
        """Confirm the current plan"""
        if self._current_plan:
            self._current_plan.status = PlanStatus.CONFIRMED
            return True
        return False

    async def modify(self, feedback: str) -> PlanResult:
        """
        Modify the current plan based on user feedback

        Args:
            feedback: User's modification request

        Returns:
            Updated PlanResult
        """
        if not self._current_plan:
            raise ValueError("No current plan to modify")

        # Record modification
        self._current_plan.user_modifications.append(feedback)

        # Re-plan with modified constraints
        # For now, just mark as modified
        self._current_plan.status = PlanStatus.MODIFIED

        # In a full implementation, this would:
        # 1. Parse the feedback
        # 2. Identify what needs to change
        # 3. Re-run planning with new constraints

        return self._current_plan

    def to_dict(self, plan: PlanResult) -> dict:
        """Convert plan to dictionary"""
        return {
            "status": plan.status.value,
            "tasks": [t.to_dict() for t in plan.tasks],
            "dependencies": [
                {"from": d.from_task, "to": d.to_task, "type": d.dependency_type}
                for d in plan.dependencies
            ],
            "critical_path": plan.critical_path,
            "total_duration": plan.total_duration,
            "agent_requirements": plan.agent_requirements,
            "gantt": {
                "start": plan.gantt_data.start_time if plan.gantt_data else 0,
                "end": plan.gantt_data.end_time if plan.gantt_data else 0,
                "tasks": [
                    {
                        "id": g.task_id,
                        "start": g.start,
                        "duration": g.duration,
                        "is_critical": g.is_critical,
                        "status": g.status,
                    }
                    for g in plan.gantt_data.tasks if plan.gantt_data
                ],
            },
        }


# Import for type hints
from .task import TestStrategy
