from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ToolResult:
    public_text: str
    ctx_patch: Dict[str, Any] | None = None
    private_data: Any = None

    def __str__(self) -> str:  # pragma: no cover - simple
        return self.public_text
