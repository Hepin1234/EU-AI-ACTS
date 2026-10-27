from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .classifier import DISCLAIMER, ClassificationResult

AnalysisMode = Literal["free", "anthropic", "openai"]


class AnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=3, max_length=2048, description="URL of the AI product's site to analyze")
    mode: AnalysisMode = Field(
        default="free",
        description=(
            "'free' runs the local rule engine (no key needed). 'anthropic' and 'openai' run "
            "a live LLM triage using the matching provider's API key."
        ),
    )
    api_key: str | None = Field(
        default=None,
        description=(
            "Optional provider API key for this request only — never stored. Required when "
            "mode is 'anthropic' or 'openai' unless the server has a matching key set as an "
            "environment variable (ANTHROPIC_API_KEY / OPENAI_API_KEY). Ignored when mode is 'free'."
        ),
    )


class AnalyzeResponse(BaseModel):
    url: str
    source: str
    pages_analyzed: int
    classification: ClassificationResult
    disclaimer: str = DISCLAIMER


class ErrorResponse(BaseModel):
    """Documents the shape of HTTPException responses (FastAPI's own `{"detail": ...}`
    envelope) for the OpenAPI schema. Automatic request-validation errors (422) use a
    different built-in shape where `detail` is a list, not a string — not represented here."""

    detail: str
