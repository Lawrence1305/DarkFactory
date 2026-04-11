"""
Execution Router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

router = APIRouter()


class ExecutionStart(BaseModel):
    project_id: str
    agent_count: int = 1
    task_ids: Optional[List[str]] = None


class ExecutionStatus(BaseModel):
    running: bool
    project_id: str
    active_tasks: List[str]
    completed_tasks: List[str]
    blocked_tasks: List[str]
    agent_status: Dict[str, str]
    current_step: Optional[str] = None
    progress_percent: float = 0.0


class ExecutionResponse(BaseModel):
    success: bool
    message: str
    execution_id: Optional[str] = None


# In-memory execution state
_execution_state: Dict[str, ExecutionStatus] = {}


@router.post("/start", response_model=ExecutionResponse)
async def start_execution(execution: ExecutionStart):
    """Start project execution"""
    execution_id = f"exec_{execution.project_id}_{int(datetime.now().timestamp())}"

    state = ExecutionStatus(
        running=True,
        project_id=execution.project_id,
        active_tasks=[],
        completed_tasks=[],
        blocked_tasks=[],
        agent_status={f"agent_{i}": "idle" for i in range(execution.agent_count)},
    )
    _execution_state[execution_id] = state

    return ExecutionResponse(
        success=True,
        message="Execution started",
        execution_id=execution_id,
    )


@router.get("/status/{execution_id}", response_model=ExecutionStatus)
async def get_execution_status(execution_id: str):
    """Get execution status"""
    if execution_id not in _execution_state:
        raise HTTPException(status_code=404, detail="Execution not found")
    return _execution_state[execution_id]


@router.post("/stop/{execution_id}", response_model=ExecutionResponse)
async def stop_execution(execution_id: str):
    """Stop execution"""
    if execution_id not in _execution_state:
        raise HTTPException(status_code=404, detail="Execution not found")

    state = _execution_state[execution_id]
    state.running = False
    for agent_id in state.agent_status:
        state.agent_status[agent_id] = "stopped"

    return ExecutionResponse(
        success=True,
        message="Execution stopped",
    )


@router.get("/{execution_id}/logs")
async def get_execution_logs(execution_id: str, limit: int = 100):
    """Get execution logs"""
    # Return mock logs
    return {
        "execution_id": execution_id,
        "logs": [
            {"timestamp": datetime.now().isoformat(), "level": "info", "message": "Execution running..."}
        ],
        "total": 1,
    }
