"""
Projects Router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    workspace: str = "./workspace"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Project(BaseModel):
    id: str
    name: str
    description: str
    workspace: str
    created_at: str
    updated_at: str
    task_count: int = 0
    completed_count: int = 0


# In-memory storage (replace with database)
_projects: Dict[str, Project] = {}


@router.post("/", response_model=Project)
async def create_project(project: ProjectCreate):
    """Create a new project"""
    import uuid
    project_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()

    new_project = Project(
        id=project_id,
        name=project.name,
        description=project.description,
        workspace=project.workspace,
        created_at=now,
        updated_at=now,
    )
    _projects[project_id] = new_project
    return new_project


@router.get("/", response_model=List[Project])
async def list_projects():
    """List all projects"""
    return list(_projects.values())


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """Get project by ID"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return _projects[project_id]


@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: str, update: ProjectUpdate):
    """Update project"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    project = _projects[project_id]
    if update.name is not None:
        project.name = update.name
    if update.description is not None:
        project.description = update.description
    project.updated_at = datetime.now().isoformat()

    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete project"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    del _projects[project_id]
    return {"message": "Project deleted"}
