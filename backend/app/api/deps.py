from __future__ import annotations

from fastapi import Depends

from ..core.config import get_settings, AppSettings
from ..core.security import resolve_user, UserContext
from ..services.catalog import ArtifactCatalogService, create_catalog


def get_settings_dep() -> AppSettings: return get_settings()


def get_catalog(settings: AppSettings = Depends(get_settings_dep)) -> ArtifactCatalogService: return create_catalog(settings)


async def get_user(context: UserContext = Depends(resolve_user)) -> UserContext: return context
