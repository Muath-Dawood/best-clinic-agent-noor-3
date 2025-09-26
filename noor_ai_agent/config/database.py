"""
Database configuration and connection management.
"""

from typing import Optional
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration settings."""

    state_db_path: str = "state.db"
    sessions_db_path: str = "noor_sessions.db"
    connection_timeout: float = 30.0
    max_connections: int = 10

    def get_state_db_url(self) -> str:
        """Get SQLite URL for state database."""
        return f"sqlite:///{self.state_db_path}"

    def get_sessions_db_url(self) -> str:
        """Get SQLite URL for sessions database."""
        return f"sqlite:///{self.sessions_db_path}"
