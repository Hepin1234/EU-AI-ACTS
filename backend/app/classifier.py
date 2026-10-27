from __future__ import annotations

from typing import Literal

import anthropic
import openai
from pydantic import BaseModel, Field

from . import eu_ai_act_reference as ref
from .scraper import ScrapeResult

Provider = Literal["anthropic", "openai"]

ANTHROPIC_MODEL = "claude-sonnet-5"
OPENAI_MODEL = "gpt-5"
MAX_TOKENS = 4096

MISSING_API_KEY_MESSAGES: dict[Provider, str] = {
    "anthropic": (
        "No Anthropic API key available. Pass one explicitly (e.g. a key the user typed into "
        "the form) or set the ANTHROPIC_API_KEY environment variable."
    ),
    "openai": (
        "No OpenAI API key available. Pass one explicitly (e.g. a key the user typed into "
        "the form) or set the OPENAI_API_KEY environment variable."
    ),
}

DISCLAIMER = (
    "This is an automated, best-effort triage based on public-facing text — "
    "not legal advice, and not a substitute for a qualified lawyer."
)

RiskCategory = Literal["prohibited", "high_risk", "limited_risk", "minimal_risk"]

SYSTEM_PROMPT_TEMPLATE = """You are a triage assistant that classifies AI products under \
the EU AI Act's four risk tiers, for founders who cannot afford a lawyer.

Ground every citation in the reference table below — never cite an article, annex, or \
provision that is not listed there. Do not use articles you recall from general knowledge; \
only the ones given here are valid.

This is best-effort triage from public-facing marketing text, not a legal audit. Be \
conservative: if the described use case plausibly falls under a stricter tier, prefer the \
stricter tier and explain the ambiguity in `caveats` rather than picking the lenient reading. \
If the scraped text doesn't give you enough to classify with confidence, say so in `caveats` \
and set `confidence` to "low" rather than guessing at specifics.

{reference_table}
"""


class ClassificationResult(BaseModel):
    category: RiskCategory = Field(description="One of the four EU AI Act risk tiers")
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence in this classification, given it is based only on public marketing text"
    )
    explanation: str = Field(
        description="Plain-English explanation of why this classification applies, written for a non-lawyer founder"
    )
    cited_articles: list[str] = Field(
        default_factory=list,
        description="Citation IDs copied verbatim from the provided reference table, e.g. 'Art. 5(1)(c)'",
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Limitations of this analysis: missing information, ambiguous use case, edge cases not covered",
    )


class ClassifierError(Exception):
    pass


def _build_user_content(scrape: ScrapeResult) -> str:
    return (
        f"Root URL: {scrape.root_url}\n"
        f"Pages analyzed: {len(scrape.pages)} (discovery source: {scrape.source})\n\n"
        f"{scrape.combined_text}"
    )


def _classify_anthropic(scrape: ScrapeResult, *, model: str, api_key: str) -> ClassificationResult:
    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(reference_table=ref.format_reference_for_prompt())

    try:
        response = client.messages.parse(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": _build_user_content(scrape)}],
            output_format=ClassificationResult,
        )
    except anthropic.AuthenticationError as exc:
        raise ClassifierError("The Anthropic API key was rejected — check that it's correct and active.") from exc
    except anthropic.RateLimitError as exc:
        raise ClassifierError("This Anthropic API key is being rate-limited right now — wait a moment and try again.") from exc
    except anthropic.APIConnectionError as exc:
        raise ClassifierError("Couldn't reach the Anthropic API — check your network connection and try again.") from exc
    except anthropic.APIStatusError as exc:
        raise ClassifierError(f"The Anthropic API returned an error: {exc.message}") from exc

    if response.stop_reason == "refusal":
        raise ClassifierError("Classification request was declined by safety filters")

    result = response.parsed_output
    if result is None:
        raise ClassifierError("Model did not return a parseable classification")
    return result


def _classify_openai(scrape: ScrapeResult, *, model: str, api_key: str) -> ClassificationResult:
    client = openai.OpenAI(api_key=api_key)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(reference_table=ref.format_reference_for_prompt())

    try:
        response = client.chat.completions.parse(
            model=model,
            max_completion_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _build_user_content(scrape)},
            ],
            response_format=ClassificationResult,
        )
    except openai.AuthenticationError as exc:
        raise ClassifierError("The OpenAI API key was rejected — check that it's correct and active.") from exc
    except openai.RateLimitError as exc:
        raise ClassifierError("This OpenAI API key is being rate-limited right now — wait a moment and try again.") from exc
    except openai.APIConnectionError as exc:
        raise ClassifierError("Couldn't reach the OpenAI API — check your network connection and try again.") from exc
    except openai.APIStatusError as exc:
        raise ClassifierError(f"The OpenAI API returned an error: {exc.message}") from exc

    message = response.choices[0].message
    if message.refusal:
        raise ClassifierError("Classification request was declined by safety filters")

    result = message.parsed
    if result is None:
        raise ClassifierError("Model did not return a parseable classification")
    return result


def classify(
    scrape: ScrapeResult,
    *,
    provider: Provider = "anthropic",
    model: str | None = None,
    api_key: str | None = None,
) -> ClassificationResult:
    """Classify a scraped site via a live LLM call. `api_key` lets a caller (e.g. a
    user-supplied key from the request) override the server's own credentials — this app
    never bundles or bills against a shared key; every call runs against whichever key was
    actually provided."""
    if not scrape.pages:
        raise ClassifierError(
            "No page content available to classify: " + "; ".join(scrape.errors or ["unknown scrape failure"])
        )

    if not api_key:
        raise ClassifierError(MISSING_API_KEY_MESSAGES[provider])

    if provider == "anthropic":
        result = _classify_anthropic(scrape, model=model or ANTHROPIC_MODEL, api_key=api_key)
    else:
        result = _classify_openai(scrape, model=model or OPENAI_MODEL, api_key=api_key)

    # Defense in depth: the prompt instructs the model to cite only from the reference
    # table, but LLMs still occasionally hallucinate a citation — strip anything that
    # doesn't match our verified table rather than trust the prompt alone.
    valid_citations = [a for a in result.cited_articles if ref.is_valid_citation(a)]
    if len(valid_citations) != len(result.cited_articles):
        result.caveats.append(
            "Some citations returned by the model did not match our verified reference "
            "table and were removed."
        )
    result.cited_articles = valid_citations

    return result
