"""Free, local, non-LLM triage path: 'Local Rule Engine' mode.

Two-stage lookup, no network calls beyond the scrape already performed:
1. Exact root-domain match against database.json (curated, high-confidence).
2. Fallback keyword heuristic against eu_ai_act_reference's per-tier
   signal_keywords, scanning the scraped page text.

This is deliberately coarser than the LLM-backed classify() in classifier.py —
it exists so a visitor with no API key still gets an instant, best-effort read.
"""

from __future__ import annotations

import json
import os
from urllib.parse import urlparse

from . import eu_ai_act_reference as ref
from .classifier import ClassificationResult
from .scraper import ScrapeResult

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(APP_DIR, "database.json")

LOCAL_ENGINE_CAVEAT = (
    "This result came from the free Local Rule Engine (domain lookup + keyword matching), "
    "not a live AI reading of the site's content — it is coarser than the Advanced AI Scan "
    "and can miss nuance or context. Consider the Advanced AI Scan for a closer read."
)


def _load_database() -> dict:
    try:
        with open(DATABASE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _root_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _domain_lookup(root_url: str) -> ClassificationResult | None:
    entry = _load_database().get(_root_domain(root_url))
    if not entry:
        return None
    return ClassificationResult(
        category=entry["category"],
        confidence=entry.get("confidence", "medium"),
        explanation=entry["explanation"],
        cited_articles=[a for a in entry.get("cited_articles", []) if ref.is_valid_citation(a)],
        caveats=[*entry.get("caveats", []), LOCAL_ENGINE_CAVEAT],
    )


def _keyword_heuristic(scrape: ScrapeResult) -> ClassificationResult:
    text = scrape.combined_text.lower()

    # RISK_TIERS is ordered prohibited -> high_risk -> limited_risk -> minimal_risk,
    # so the first tier with any keyword hit is the most severe applicable match.
    for tier in ref.RISK_TIERS:
        hits = [kw for kw in tier.signal_keywords if kw in text]
        if not hits:
            continue
        return ClassificationResult(
            category=tier.id,
            confidence="low",
            explanation=(
                f"The Local Rule Engine matched term(s) associated with {tier.label} use cases "
                f"in the site's text: {', '.join(hits)}. {tier.consequence}"
            ),
            cited_articles=[p.id for p in tier.provisions[:2]],
            caveats=[
                "Matched via keyword heuristic, not a contextual reading of the site's actual "
                "product behaviour — verify manually or run the Advanced AI Scan.",
                LOCAL_ENGINE_CAVEAT,
            ],
        )

    return ClassificationResult(
        category="minimal_risk",
        confidence="low",
        explanation=(
            "No known domain match and no EU AI Act risk-tier keywords were found in the site's "
            "text, so this defaults to Minimal Risk. That means the free engine found no signal "
            "either way, not that the product is confirmed risk-free."
        ),
        cited_articles=["Art. 95"],
        caveats=[
            "No strong signal was found in the scraped text — this is a low-confidence default.",
            LOCAL_ENGINE_CAVEAT,
        ],
    )


def classify_local(scrape: ScrapeResult) -> ClassificationResult:
    return _domain_lookup(scrape.root_url) or _keyword_heuristic(scrape)
