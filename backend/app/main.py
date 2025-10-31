from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import projects as projects_router
from .api.routes import runs as runs_router
from .api.routes import artifacts as artifacts_router
from .core.logging import configure_logging


def create_app() -> FastAPI:
    """Assemble the FastAPI application with middleware, routes, and logging."""
    configure_logging()
    app = FastAPI(title="SWFT Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(projects_router.router)
    app.include_router(runs_router.router)
    app.include_router(artifacts_router.router)
    return app


app = create_app()
