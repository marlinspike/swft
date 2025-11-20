"""orjson wrapper with stdlib fallback."""

from __future__ import annotations

import json as std_json
from typing import Any

try:
    import orjson  # type: ignore
except ImportError:  # pragma: no cover
    orjson = None


def loads(data: bytes | str) -> Any:
    if orjson:
        return orjson.loads(data)
    if isinstance(data, bytes):
        return std_json.loads(data.decode("utf-8"))
    return std_json.loads(data)


def dumps(obj: Any) -> bytes:
    if orjson:
        return orjson.dumps(obj)
    return std_json.dumps(obj).encode("utf-8")

