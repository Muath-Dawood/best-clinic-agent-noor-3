"""
Health check handler.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

from ...config import get_settings


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    uptime: float


class HealthHandler:
    """Handler for health check endpoints."""

    def __init__(self):
        self.settings = get_settings()
        self.start_time = datetime.now()
        self.router = APIRouter()
        self._setup_routes()

    def _setup_routes(self):
        """Setup health check routes."""

        @self.router.get("/", response_model=HealthResponse)
        async def health_check():
            """Basic health check endpoint."""
            uptime = (datetime.now() - self.start_time).total_seconds()
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now().isoformat(),
                version=self.settings.app_version,
                uptime=uptime
            )

        @self.router.get("/ready")
        async def readiness_check():
            """Readiness check for container orchestration."""
            return {"status": "ready"}

        @self.router.get("/live")
        async def liveness_check():
            """Liveness check for container orchestration."""
            return {"status": "alive"}
