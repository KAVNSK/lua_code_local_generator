from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """OpenAPI requires `prompt`; optional fields extend PDF-style tasks and agent loop."""

    prompt: str = Field(..., min_length=1)
    context: dict[str, Any] | None = None
    previous_code: str | None = None
    feedback: str | None = None


class GenerateResponse(BaseModel):
    code: str
    confidence_gate_triggered: bool = False
    repair_report: dict[str, Any] | None = None


class RefineRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    context: dict[str, Any] | None = None
    previous_code: str = Field(..., min_length=1)
    feedback: str = Field(..., min_length=1)


class ClarifyAnswer(BaseModel):
    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class ClarifyQuestion(BaseModel):
    id: str
    text: str
    why: str
    blocking: bool = True
    options: list[str] = Field(default_factory=list)


class ClarifyRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    context: dict[str, Any] | None = None
    answers: list[ClarifyAnswer] = Field(default_factory=list)


class ClarifyResponse(BaseModel):
    status: str
    questions: list[ClarifyQuestion] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    merged_context: dict[str, Any] | None = None


class GenerateFromClarifyRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    context: dict[str, Any] | None = None
    answers: list[ClarifyAnswer] = Field(default_factory=list)
    previous_code: str | None = None
    feedback: str | None = None


class GenerateFromClarifyResponse(BaseModel):
    status: str
    code: str | None = None
    questions: list[ClarifyQuestion] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    merged_context: dict[str, Any] | None = None
    confidence_gate_triggered: bool = False
    repair_report: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    model_ready: bool = False
    model: str
    num_ctx: int
    num_predict: int
    batch: int
    parallel: int
    gpu_only: bool
