from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Sequence
import logging

from ...models.api import RunSummaryModel, RunDetailModel, ArtifactModel
from ...services.catalog import ArtifactCatalogService
from ...services.exceptions import NotFoundError, RepositoryError
from ..deps import get_catalog, get_user
from ...core.security import UserContext

router = APIRouter(prefix="/projects/{project_id}/runs", tags=["runs"])

logger = logging.getLogger("swft.backend.runs")


def _summary_model(summary) -> RunSummaryModel: return RunSummaryModel(project_id=summary.project_id, run_id=summary.run_id, created_at=summary.created_at, artifact_counts=summary.artifact_counts, cosign_status=summary.cosign_status, trivy_findings_total=summary.trivy_findings_total, trivy_findings_failset=summary.trivy_findings_failset, deployment_url=summary.deployment_url)


def _artifact_model(artifact) -> ArtifactModel: return ArtifactModel(project_id=artifact.project_id, run_id=artifact.run_id, artifact_type=artifact.artifact_type, blob_name=artifact.blob_name, container=artifact.container, last_modified=artifact.last_modified, size_bytes=artifact.size_bytes)


@router.get("", response_model=Sequence[RunSummaryModel])
def list_runs(project_id: str = Path(..., description="Project identifier"), catalog: ArtifactCatalogService = Depends(get_catalog), user: UserContext = Depends(get_user)) -> Sequence[RunSummaryModel]:
    """Return run summaries for the chosen project, enforcing access restrictions."""
    if user.allowed_projects and project_id not in user.allowed_projects:
        raise HTTPException(status_code=403, detail="Access to project denied.")
    try:
        summaries = catalog.list_runs(project_id)
    except RepositoryError as exc:
        logger.exception("Failed to list runs for project '%s'", project_id)
        raise HTTPException(status_code=500, detail="Failed to enumerate runs.") from exc
    return [_summary_model(item) for item in summaries]


@router.get("/{run_id}", response_model=RunDetailModel)
def get_run(project_id: str = Path(..., description="Project identifier"), run_id: str = Path(..., description="Run identifier"), catalog: ArtifactCatalogService = Depends(get_catalog), user: UserContext = Depends(get_user)) -> RunDetailModel:
    """Return detailed metadata and artifacts for an individual run."""
    if user.allowed_projects and project_id not in user.allowed_projects:
        raise HTTPException(status_code=403, detail="Access to project denied.")
    try:
        detail = catalog.run_detail(project_id, run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RepositoryError as exc:
        logger.exception("Failed to load run '%s' for project '%s'", run_id, project_id)
        raise HTTPException(status_code=500, detail="Failed to load run detail.") from exc
    artifacts = [_artifact_model(item) for item in detail.artifacts]
    summary = _summary_model(detail.summary)
    return RunDetailModel(summary=summary, artifacts=artifacts, metadata=detail.metadata)
