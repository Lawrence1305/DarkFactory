"""
Tasks Router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

router = APIRouter()


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TestStrategy(str, Enum):
    AUTO = "auto"
    BROWSER = "browser"
    LINT = "lint"
    UNIT = "unit"


class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: str = ""
    steps: List[str] = []
    priority: int = 3
    dependencies: List[str] = []
    skills_required: List[str] = []
    test_strategy: TestStrategy = TestStrategy.AUTO
    estimated_duration: int = 30


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[str]] = None
    priority: Optional[int] = None
    dependencies: Optional[List[str]] = None
    status: Optional[TaskStatus] = None
    passes: Optional[bool] = None


class Task(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    steps: List[str]
    status: TaskStatus
    priority: int
    dependencies: List[str]
    skills_required: List[str]
    test_strategy: TestStrategy
    passes: bool
    estimated_duration: int
    estimated_tokens: int = 5000
    created_at: str
    updated_at: str


# In-memory storage
_tasks: Dict[str, Task] = {}


@router.post("/", response_model=Task)
async def create_task(task: TaskCreate):
    """Create a new task"""
    import uuid
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()

    new_task = Task(
        id=task_id,
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        steps=task.steps,
        status=TaskStatus.PENDING,
        priority=task.priority,
        dependencies=task.dependencies,
        skills_required=task.skills_required,
        test_strategy=task.test_strategy,
        passes=False,
        estimated_duration=task.estimated_duration,
        created_at=now,
        updated_at=now,
    )
    _tasks[task_id] = new_task
    return new_task


@router.get("/project/{project_id}", response_model=List[Task])
async def list_project_tasks(project_id: str):
    """List all tasks for a project"""
    return [t for t in _tasks.values() if t.project_id == project_id]


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """Get task by ID"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return _tasks[task_id]


@router.put("/{task_id}", response_model=Task)
async def update_task(task_id: str, update: TaskUpdate):
    """Update task"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = _tasks[task_id]
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(task, field, value)
    task.updated_at = datetime.now().isoformat()

    return task


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete task"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    del _tasks[task_id]
    return {"message": "Task deleted"}
