from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Sequence


class SwftProjectModel(BaseModel):
    project_id: str = Field(..., description="GitHub repository identifier used across SCAI.")
    services: list[str]
    regions: list[str]
    boundary_description: str | None = None


class SwftProjectUpdate(BaseModel):
    services: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    boundary_description: str | None = None


class SwftParameterModel(BaseModel):
    control_id: str
    param_id: str
    label: str | None = None
    description: str | None = None
    allowed_values: list[str] = Field(default_factory=list)
    current_value: str | None = None


class CatalogSyncResponse(BaseModel):
    catalog: dict
    baseline: dict


class PolicyImportResponse(BaseModel):
    initiative: str
    scope: str
    policies: int
    mappings: int
    version: str


class PolicyStateResponse(BaseModel):
    processed: int
    inserted: int


class EvidenceIngestResponse(BaseModel):
    evidence_id: int
    run_id: str
    kind: str
    metadata: dict | None = None


class StorageEvidenceItem(BaseModel):
    kind: str
    status: str
    message: str | None = None
    evidence_id: int | None = None
    metadata: dict | None = None


class StorageEvidenceResponse(BaseModel):
    project_id: str
    run_id: str
    results: Sequence[StorageEvidenceItem]


class AzurePolicySetModel(BaseModel):
    id: str
    label: str
    default_scope: str
    description: str


class AzurePolicyImportRequest(BaseModel):
    policy_id: str
    scope: str | None = None
