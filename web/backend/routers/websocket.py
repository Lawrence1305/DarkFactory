"""
WebSocket Router
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json
from datetime import datetime

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()
        self.active_connections[project_id].add(websocket)

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            self.active_connections[project_id].discard(websocket)

    async def broadcast(self, project_id: str, message: dict):
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


@router.websocket("/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """WebSocket endpoint for project updates"""
    await manager.connect(websocket, project_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)

                # Handle ping
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                # Handle subscribe to execution updates
                elif message.get("type") == "subscribe_execution":
                    execution_id = message.get("execution_id")
                    # Start broadcasting execution updates
                    asyncio.create_task(_broadcast_execution_updates(project_id, execution_id))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)


async def _broadcast_execution_updates(project_id: str, execution_id: str):
    """Simulate execution updates"""
    from .execution import _execution_state

    while True:
        if execution_id in _execution_state:
            state = _execution_state[execution_id]
            await manager.broadcast(project_id, {
                "type": "execution_update",
                "execution_id": execution_id,
                "state": {
                    "running": state.running,
                    "active_tasks": state.active_tasks,
                    "completed_tasks": state.completed_tasks,
                    "progress_percent": state.progress_percent,
                },
                "timestamp": datetime.now().isoformat(),
            })

            if not state.running:
                break

        await asyncio.sleep(1)


async def send_task_update(project_id: str, task_id: str, update: dict):
    """Send task update to all connected clients"""
    await manager.broadcast(project_id, {
        "type": "task_update",
        "task_id": task_id,
        "update": update,
        "timestamp": datetime.now().isoformat(),
    })


async def send_log(project_id: str, log: dict):
    """Send log entry to all connected clients"""
    await manager.broadcast(project_id, {
        "type": "log",
        "log": log,
        "timestamp": datetime.now().isoformat(),
    })
