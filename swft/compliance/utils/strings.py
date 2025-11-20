"""String helpers."""

from __future__ import annotations

import re

SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def slugify(value: str | None, default: str) -> str:
    if not value:
        return default
    slug = SLUG_PATTERN.sub("-", value.lower()).strip("-")
    return slug or default

