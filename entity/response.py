from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Response:
    """A handler response with explicit Taomee response-header fields."""

    payload: bytes = b""
    command_id: Optional[int] = None
    user_id: Optional[int] = None
    status: int = 0
    error: int = 0
