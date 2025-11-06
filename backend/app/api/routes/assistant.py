from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ...assistant import AssistantService, AssistantConfig, ChatRequest, ChatResponse

router = APIRouter(prefix="/assistant", tags=["assistant"])
service = AssistantService()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Entry point for the SWFT assistant."""
    try:
        return service.generate(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get("/config", response_model=AssistantConfig)
async def config() -> AssistantConfig:
    """Expose assistant runtime configuration to the frontend."""
    return service.configuration()


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream assistant responses as newline-delimited JSON events."""
    try:
        generator = service.stream(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return StreamingResponse(generator, media_type="application/x-ndjson")
