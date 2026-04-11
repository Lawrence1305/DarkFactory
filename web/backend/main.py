"""
DarkFactory Web Backend - FastAPI
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from .routers import projects, tasks, execution, websocket
from .services.scheduler import SchedulerService
from .services.agent_manager import AgentManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting DarkFactory Web Backend")

    # Initialize services
    app.state.scheduler = SchedulerService()
    app.state.agent_manager = AgentManager()

    yield

    # Shutdown
    logger.info("Shutting down DarkFactory Web Backend")


app = FastAPI(
    title="DarkFactory",
    description="AI-Native Agent Framework Web Interface",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(execution.router, prefix="/api/execution", tags=["execution"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@app.get("/")
async def root():
    return {"message": "DarkFactory Web Backend", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}
