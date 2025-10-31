from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Any

from ...services.catalog import ArtifactCatalogService
from ...services.exceptions import NotFoundError, RepositoryError
from ..deps import get_catalog, get_user
from ...core.security import UserContext
import logging

logger = logging.getLogger("swft.backend.artifacts")

router = APIRouter(prefix="/projects/{project_id}/runs/{run_id}/artifacts", tags=["artifacts"])


@router.get("/{artifact_type}", response_model=dict[str, Any])
def fetch_artifact(project_id: str = Path(..., description="Project identifier"), run_id: str = Path(..., description="Run identifier"), artifact_type: str = Path(..., description="Artifact type (sbom|trivy|run)"), catalog: ArtifactCatalogService = Depends(get_catalog), user: UserContext = Depends(get_user)) -> dict[str, Any]:
    """Return the raw JSON payload for a specific artifact if the user has access."""
    if user.allowed_projects and project_id not in user.allowed_projects:
        raise HTTPException(status_code=403, detail="Access to project denied.")
    try:
        detail = catalog.run_detail(project_id, run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RepositoryError as exc:
        logger.exception("Failed to load run '%s' for project '%s' while fetching artifact '%s'", run_id, project_id, artifact_type)
        raise HTTPException(status_code=500, detail="Failed to load artifact metadata.") from exc
    matches = [artifact for artifact in detail.artifacts if artifact.artifact_type == artifact_type]
    if not matches:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_type}' not available for run '{run_id}'.")
    try:
        return catalog.fetch_artifact(matches[0])
    except RepositoryError as exc:
        logger.exception("Failed to fetch artifact '%s' for project '%s' run '%s'", artifact_type, project_id, run_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
