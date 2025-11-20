"""Helpers to parse OSCAL catalog JSON."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from ..utils import json


@dataclass(slots=True)
class CatalogMetadata:
    title: str | None
    version: str | None
    oscal_version: str | None


@dataclass(slots=True)
class CatalogControl:
    control_id: str
    family: str | None
    title: str | None
    parameters: list[dict[str, Any]]
    assessment_objectives: list[dict[str, Any]]


@dataclass(slots=True)
class CatalogDocument:
    metadata: CatalogMetadata
    controls: list[CatalogControl]


def load_catalog(path: Path) -> CatalogDocument:
    """Load and normalize an OSCAL catalog JSON file."""
    data = json.loads(path.read_bytes())
    if "catalog" not in data:
        raise ValueError("Expected OSCAL catalog JSON with top-level 'catalog'.")
    catalog = data["catalog"]
    metadata = catalog.get("metadata", {})
    meta = CatalogMetadata(
        title=metadata.get("title"),
        version=_extract_version(metadata),
        oscal_version=metadata.get("oscal-version"),
    )
    controls = list(_iter_controls(catalog))
    return CatalogDocument(metadata=meta, controls=controls)


def _extract_version(metadata: dict[str, Any]) -> str | None:
    if "version" in metadata:
        value = metadata["version"]
        if isinstance(value, dict):
            return value.get("text") or value.get("value")
        if isinstance(value, str):
            return value
    for prop in metadata.get("props", []):
        if prop.get("name") == "version":
            return prop.get("value")
    return None


def _iter_controls(catalog: dict[str, Any]) -> Iterator[CatalogControl]:
    for control in catalog.get("controls", []):
        yield from _iter_control_tree(control, None)
    for group in catalog.get("groups", []):
        family = group.get("title") or group.get("id")
        yield from _iter_group(group, family)


def _iter_group(group: dict[str, Any], family: str | None) -> Iterator[CatalogControl]:
    for control in group.get("controls", []):
        yield from _iter_control_tree(control, family)
    for subgroup in group.get("groups", []):
        sub_family = subgroup.get("title") or subgroup.get("id") or family
        yield from _iter_group(subgroup, sub_family)


def _iter_control_tree(control: dict[str, Any], family: str | None) -> Iterator[CatalogControl]:
    yield _control_from_node(control, family)
    for child in control.get("controls", []):
        yield from _iter_control_tree(child, family)


def _control_from_node(control: dict[str, Any], family: str | None) -> CatalogControl:
    control_id = control.get("id")
    if not control_id:
        raise ValueError("Encountered control without 'id'.")
    title = control.get("title")
    parameters = list(control.get("params", []))
    objectives = _extract_assessment_objectives(control)
    return CatalogControl(
        control_id=control_id,
        family=family,
        title=title,
        parameters=parameters,
        assessment_objectives=objectives,
    )


def _extract_assessment_objectives(control: dict[str, Any]) -> list[dict[str, Any]]:
    """Capture parts that look like assessment objectives."""
    parts = control.get("parts", [])
    if not isinstance(parts, list):
        return []
    objectives: list[dict[str, Any]] = []
    for part in parts:
        name = part.get("name", "")
        if name in {"assessment-objectives", "assessment-objective", "objective"}:
            objectives.append(part)
            continue
        if part.get("class") == "assessment":
            objectives.append(part)
            continue
        if any(prop.get("name") == "assessment-objective" for prop in part.get("props", [])):
            objectives.append(part)
    return objectives
