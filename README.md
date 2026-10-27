# AI Checker — EU AI Act Risk Triage

Paste the URL of an AI product and get a best-effort read on where it falls under the
**EU AI Act's four risk tiers** — *Prohibited*, *High Risk*, *Limited Risk*, or *Minimal Risk* —
with a plain-English explanation, the specific articles behind it, and honest caveats.

Built for founders and small teams who need a quick first read before they can afford a lawyer.

> ⚠️ **Not legal advice.** AI Checker is an educational, best-effort triage tool based only on a
> site's public-facing text. Always confirm with qualified counsel before relying on the result.

---

## Features

- **URL in, classification out** — the backend crawls the site (sitemap → `robots.txt` sitemap →
  homepage links → homepage only) and reads up to 5 pages.
- **Three analysis modes**
  | Mode | Cost | How it works |
  |------|------|--------------|
  | **Local Rule Engine** | Free, no key | Curated domain lookup (`database.json`), then a keyword heuristic per risk tier |
  | **Advanced AI Scan — Anthropic** | Your API key | Claude reads the scraped text and returns a structured classification |
  | **Advanced AI Scan — OpenAI** | Your API key | GPT reads the scraped text and returns a structured classification |
- **Grounded citations** — the model may only cite provisions from a verified reference table
  (`eu_ai_act_reference.py`); any citation that doesn't match is stripped and flagged.
- **Bring your own key** — keys are sent for a single request and never stored or logged
  server-side. Optionally, the server owner can set keys via environment variables.
- **Safe scraping** — request timeouts, response size caps, redirect limits and private-IP blocking.
- **Rate limited** — 10 requests/minute per IP on the analyze endpoint.
- **Single process** — FastAPI serves both the API and the static frontend.

## Tech stack

- **Backend:** Python, FastAPI, Uvicorn, Pydantic, Requests, BeautifulSoup, SlowAPI
- **LLM providers:** Anthropic SDK, OpenAI SDK (both optional)
- **Frontend:** Plain HTML, CSS and JavaScript — no build step

## Project structure

```
AI Checker/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, /api/analyze + /api/health, serves frontend
│   │   ├── scraper.py              # Site discovery + text extraction
│   │   ├── classifier.py           # LLM-backed classification (Anthropic / OpenAI)
│   │   ├── local_classifier.py     # Free Local Rule Engine
│   │   ├── eu_ai_act_reference.py  # Risk tiers, provisions and keywords used for grounding
│   │   ├── database.json           # Curated known-domain classifications
│   │   └── models.py               # Request / response schemas
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── index.html
    ├── script.js
    └── style.css
```

## Getting started

### Prerequisites

- Python 3.10+
- (Optional) an [Anthropic](https://console.anthropic.com/settings/keys) or
  [OpenAI](https://platform.openai.com/api-keys) API key for the Advanced AI Scan

### Install

```bash
git clone https://github.com/<your-username>/ai-checker.git
cd ai-checker/backend

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Configure (optional)

```bash
cp .env.example .env
```

Both keys are optional. If set, visitors don't need to paste their own key for that provider.
Leave them empty to require every visitor to bring their own key. Neither is needed for the
free Local Rule Engine.

```env
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

### Run

From the `backend/` folder:

```bash
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** in your browser. Interactive API docs are at
**http://127.0.0.1:8000/docs**.

## API

### `POST /api/analyze`

```json
{
  "url": "https://example.com",
  "mode": "free",
  "api_key": null
}
```

- `mode`: `"free"` (default), `"anthropic"`, or `"openai"`
- `api_key`: optional, used for this request only; ignored in `free` mode

**Response**

```json
{
  "url": "https://example.com",
  "source": "sitemap",
  "pages_analyzed": 5,
  "classification": {
    "category": "limited_risk",
    "confidence": "medium",
    "explanation": "…",
    "cited_articles": ["Art. 50(1)"],
    "caveats": ["…"]
  },
  "disclaimer": "This is an automated, best-effort triage …"
}
```

| Status | Meaning |
|--------|---------|
| `400` | AI mode selected but no API key available |
| `422` | Invalid request body |
| `424` | No page content could be extracted from the URL |
| `429` | Rate limit exceeded |
| `502` | The LLM provider returned an error |

### `GET /api/health`

Returns `{"status": "ok"}`.

## How classification works

1. **Scrape** — discover up to 5 pages and extract their visible text (capped at 12,000 characters).
2. **Classify**
   - *Local Rule Engine:* exact root-domain match in `database.json`; otherwise scan the text
     for tier keywords, checking the strictest tier first. Falls back to Minimal Risk (low confidence).
   - *Advanced AI Scan:* the model receives the scraped text plus the verified reference table
     and returns structured output. It is instructed to prefer the stricter tier when in doubt.
3. **Validate** — citations not in the reference table are removed and a caveat is added.

## Limitations

- Only reads public marketing text — it can't see how a product actually behaves.
- The Local Rule Engine is keyword-based and can miss context.
- Some sites block bots or render content with JavaScript only, which the scraper can't read.
- The EU AI Act and its guidance keep evolving; the reference table may lag behind.

## Contributing

Issues and pull requests are welcome. To add a known domain, add an entry to
`backend/app/database.json` using only citation IDs that exist in `eu_ai_act_reference.py`.

## Disclaimer

AI Checker is an educational tool, not a law firm. Its output is not legal advice. For an actual
compliance determination, consult qualified counsel.
