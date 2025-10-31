from __future__ import annotations

from dataclasses import dataclass
from fastapi import Header
from typing import Sequence


@dataclass(frozen=True, slots=True)
class UserContext:
    subject: str
    allowed_projects: Sequence[str] | None = None


async def resolve_user(x_user_id: str | None = Header(default=None)) -> UserContext:
    """Create a lightweight user context from headers (placeholder for full auth)."""
    subject = x_user_id or "anonymous"
    return UserContext(subject=subject, allowed_projects=None)
