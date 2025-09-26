"""
Tool result model for agent tools.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Result from agent tool execution."""

    public_text: str = Field(description="Text to show to the user")
    ctx_patch: Dict[str, Any] = Field(default_factory=dict, description="Context updates to apply")
    private_data: Optional[Dict[str, Any]] = Field(default=None, description="Private data for internal use")
    version: int = Field(description="Context version for consistency")

    class Config:
        extra = "forbid"
