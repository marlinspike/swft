"""Parsers for Azure Policy initiative definitions and state snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...utils import json


@dataclass(slots=True)
class InitiativePolicy:
    policy_definition_id: str
    reference_id: str | None
    display_name: str | None
    category: str | None
    control_ids: list[str]


@dataclass(slots=True)
class InitiativeDocument:
    name: str | None
    version: str | None
    policies: list[InitiativePolicy]


@dataclass(slots=True)
class PolicyStateEntry:
    policy_definition_id: str
    policy_assignment_id: str
    resource_id: str
    compliance_state: str
    last_evaluated: str


def load_initiative(path: Path) -> InitiativeDocument:
    data = json.loads(path.read_bytes())
    properties = data.get("properties", {})
    metadata = properties.get("metadata", {})
    version = metadata.get("version") or properties.get("version")
    policies: list[InitiativePolicy] = []
    for entry in properties.get("policyDefinitions", []):
        definition_id = entry.get("policyDefinitionId")
        if not definition_id:
            continue
        reference_id = entry.get("policyDefinitionReferenceId")
        display_name = entry.get("displayName") or reference_id
        category = (
            entry.get("metadata", {}).get("category")
            or metadata.get("category")
            or properties.get("category")
        )
        control_ids = _extract_control_ids(entry)
        policies.append(
            InitiativePolicy(
                policy_definition_id=definition_id,
                reference_id=reference_id,
                display_name=display_name,
                category=category,
                control_ids=control_ids,
            )
        )
    return InitiativeDocument(
        name=data.get("name") or properties.get("displayName"),
        version=version,
        policies=policies,
    )


def load_policy_states(path: Path) -> list[PolicyStateEntry]:
    raw = json.loads(path.read_bytes())
    if isinstance(raw, dict):
        entries = raw.get("value") or raw.get("states") or []
    elif isinstance(raw, list):
        entries = raw
    else:
        raise ValueError("Unsupported policy state payload format.")
    states: list[PolicyStateEntry] = []
    for entry in entries:
        definition_id = entry.get("policyDefinitionId") or entry.get("policyDefinition")
        assignment_id = entry.get("policyAssignmentId")
        resource_id = entry.get("resourceId") or entry.get("resourceUri")
        compliance_state = entry.get("complianceState") or entry.get("state")
        timestamp = (
            entry.get("timestamp")
            or entry.get("lastEvaluatedOn")
            or entry.get("evaluatedTime")
        )
        if not (definition_id and assignment_id and resource_id and compliance_state and timestamp):
            continue
        states.append(
            PolicyStateEntry(
                policy_definition_id=definition_id,
                policy_assignment_id=assignment_id,
                resource_id=resource_id,
                compliance_state=compliance_state,
                last_evaluated=timestamp,
            )
        )
    return states


def _extract_control_ids(entry: dict[str, Any]) -> list[str]:
    metadata = entry.get("metadata", {})
    compliance = metadata.get("compliance", {})
    control_ids = compliance.get("complianceControlIds") or metadata.get("nistControlIds") or []
    normalized = []
    for cid in control_ids:
        if isinstance(cid, str):
            normalized.append(cid.strip().upper())
    return normalized

