"""Control data models and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ControlParameter:
    control_id: str
    param_id: str
    label: str | None
    description: str | None
    values: list[str]
    current_value: str | None = None


def normalize_parameter(control_id: str, data: dict[str, Any]) -> ControlParameter:
    param_id = data.get("id") or data.get("param-id")
    if not param_id:
        raise ValueError(f"Control '{control_id}' has a parameter without an id.")
    return ControlParameter(
        control_id=control_id,
        param_id=param_id,
        label=data.get("label"),
        description=data.get("description") or data.get("guidance"),
        values=data.get("values") or [],
    )

