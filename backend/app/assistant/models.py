from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class Persona(str, Enum):
    security_assessor = "security_assessor"
    compliance_officer = "compliance_officer"
    devops_engineer = "devops_engineer"
    software_developer = "software_developer"


class Facet(str, Enum):
    run_manifest = "run_manifest"
    sbom = "sbom"
    trivy = "trivy"
    general = "general"
    architecture = "architecture"


HistoryDepth = Literal[0, 2, 5, 7, 10, 15, "all"]


class ChatMessage(BaseModel):
    """Represents a single turn of conversation history provided by the client."""

    role: Literal["system", "user", "assistant"]
    content: Annotated[str, Field(min_length=1)]


class ChatRequest(BaseModel):
    """Payload accepted by the assistant endpoint."""

    question: Annotated[str, Field(min_length=1)]
    persona: Persona
    facet: Facet
    selected_model: str | None = Field(default=None, description="Key of the desired model defined in model_config.json.")
    history: list[ChatMessage] = Field(default_factory=list)
    history_depth: HistoryDepth = Field(default=5)
    conversation_id: str | None = Field(default=None, description="Client-provided conversation identifier.")
    context: dict[str, str] = Field(default_factory=dict, description="Optional map of context label to raw content.")
    project_id: str | None = Field(default=None, description="Project identifier whose artifacts should be referenced.")
    run_id: str | None = Field(default=None, description="Run identifier tied to the provided evidence.")

    @model_validator(mode="after")
    def validate_history_depth(self) -> "ChatRequest":
        """Ensure the conversation history does not contain system messages."""
        for entry in self.history:
            if entry.role == "system":
                raise ValueError("Conversation history may not contain system messages.")
        if (self.project_id and not self.run_id) or (self.run_id and not self.project_id):
            raise ValueError("project_id and run_id must be provided together.")
        return self


class AssistantMetadata(BaseModel):
    provider: str
    model_key: str
    model_identifier: str
    persona: Persona
    facet: Facet
    history_included: int
    max_output_tokens: int | None = None
    max_input_tokens: int | None = None
    total_context_window: int | None = None


class ChatResponse(BaseModel):
    """Structured response returned by the assistant endpoint."""

    answer: str
    conversation_id: str
    metadata: AssistantMetadata


class ModelOption(BaseModel):
    key: str
    label: str
    response_format: str | None = None
    total_context_window: int | None = Field(default=None, ge=1)
    max_input_tokens: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)


class AssistantConfig(BaseModel):
    provider: str
    models: list[ModelOption]
    personas: list[Persona]
    facets: list[Facet]
    history_depths: list[HistoryDepth]
    streaming_enabled: bool = True
