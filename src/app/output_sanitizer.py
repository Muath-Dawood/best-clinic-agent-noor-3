import re
from typing import Pattern, List

TOKEN_PATTERNS: List[Pattern[str]] = [
    re.compile(r"\bsvc\w+\b"),
    re.compile(r"\bemp\w+\b"),
    re.compile(r"\b[a-zA-Z0-9+/=_-]{20,}\b"),
]


def redact_tokens(text: str) -> str:
    """Redact service/employee tokens from a string.

    Any substrings that look like service or employee tokens are replaced
    with ``[REDACTED]`` before the text is sent to users.
    """
    if not isinstance(text, str):
        return text
    redacted = text
    for pattern in TOKEN_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted
