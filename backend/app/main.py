from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .classifier import ClassifierError, classify
from .local_classifier import classify_local
from .models import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from .scraper import scrape_url

load_dotenv()  # no-op if there's no .env file — lets a local run read ANTHROPIC_API_KEY / OPENAI_API_KEY from one

ENV_KEY_BY_PROVIDER = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
PROVIDER_LABELS = {"anthropic": "Anthropic", "openai": "OpenAI"}

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(APP_DIR))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AI Checker",
    description="EU AI Act risk triage for an AI product, from its URL. Educational use only — not legal advice.",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    responses={400: {"model": ErrorResponse}, 424: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
def analyze(request: Request, payload: AnalyzeRequest) -> AnalyzeResponse:
    api_key: str | None = None
    if payload.mode != "free":
        env_var = ENV_KEY_BY_PROVIDER[payload.mode]
        api_key = payload.api_key or os.environ.get(env_var)
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No {PROVIDER_LABELS[payload.mode]} API key available. Paste your own key in the "
                    f"form above, or set {env_var} before starting the server. Or switch Analysis "
                    "Mode to the free Local Rule Engine, which needs no key."
                ),
            )

    # scrape_url() never raises — malformed/blocked/unreachable URLs come back as a
    # ScrapeResult with .errors populated, surfaced below as a 424.
    scrape = scrape_url(payload.url)

    if not scrape.pages:
        # 424, not 422 — FastAPI's own request-body validation errors already use 422
        # with a list-shaped `detail`; reusing it here would make the two indistinguishable
        # to the frontend even though their `detail` shapes and meanings differ.
        raise HTTPException(
            status_code=424,
            detail="Could not extract any page content from that URL: " + "; ".join(scrape.errors),
        )

    if payload.mode == "free":
        result = classify_local(scrape)
    else:
        try:
            result = classify(scrape, provider=payload.mode, api_key=api_key)
        except ClassifierError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AnalyzeResponse(
        url=scrape.root_url,
        source=scrape.source,
        pages_analyzed=len(scrape.pages),
        classification=result,
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# Serve the static frontend (if it exists yet) at the root — one process, no separate host.
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
