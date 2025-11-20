"""Helpers to parse OSCAL profile JSON."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..utils import json


@dataclass(slots=True)
class ProfileMetadata:
    title: str | None
    version: str | None
    oscal_version: str | None


@dataclass(slots=True)
class ProfileDocument:
    metadata: ProfileMetadata
    control_ids: list[str]


def load_profile(path: Path) -> ProfileDocument:
    data = json.loads(path.read_bytes())
    if "profile" not in data:
        raise ValueError("Expected OSCAL profile JSON with top-level 'profile'.")
    profile = data["profile"]
    metadata = profile.get("metadata", {})
    meta = ProfileMetadata(
        title=metadata.get("title"),
        version=_extract_version(metadata),
        oscal_version=metadata.get("oscal-version"),
    )
    control_ids = sorted(_collect_control_ids(profile))
    if not control_ids:
        raise ValueError("Profile did not yield any control identifiers.")
    return ProfileDocument(metadata=meta, control_ids=control_ids)


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


def _collect_control_ids(profile: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for imp in profile.get("imports", []):
        for include in imp.get("include-controls", []):
            if "with-ids" in include:
                ids.update(include["with-ids"])
            if "matching" in include:
                # Not supported yet: provide guidance for future extension.
                raise NotImplementedError("Profile include-controls with 'matching' not supported yet.")
    if ids:
        return ids
    # Some profiles may include explicit controls array
    for control in profile.get("controls", []):
        cid = control.get("id")
        if cid:
            ids.add(cid)
    return ids
