# Article Judge AI

A tool that reads a link — a news article, a YouTube video, or a social
post — and decides whether it should be **collected** or **skipped**,
based on rules you write in plain English. No manual reading required.

It started as a single script for one repetitive judgment call. It's now
a small full-stack app: a Python backend that knows how to read different
kinds of links and ask Claude to judge them, plus a browser UI for
pasting in a batch of links and watching the verdicts land in real time.

```
 links.txt / pasted URLs
          │
          ▼
 ┌────────────────────┐        picks the right extractor per URL
 │   pipeline.py       │──────────────────────────────┐
 └────────────────────┘                               ▼
          │                                  ┌───────────────────┐
          │  extracted title + body          │  extractors/       │
          ▼                                  │  article / youtube │
 ┌────────────────────┐                      │  / social          │
 │   judge.py          │◀────────────────────└───────────────────┘
 │  (asks Claude,       │
 │   applies criteria.md)│
 └────────────────────┘
          │
          ▼
   COLLECT / SKIP + reason
          │
   ┌──────┴──────┐
   ▼             ▼
 CLI output   Web UI (FastAPI + SSE stream)
```

## Project structure

```
article-judge-ai/
├── backend/
│   ├── src/article_judge/
│   │   ├── extractors/       # one file per link type + a registry that routes by URL
│   │   │   ├── base.py       #   interface every extractor implements
│   │   │   ├── article.py    #   news/blogs (also the generic fallback)
│   │   │   ├── youtube.py    #   title + channel (oEmbed) + transcript
│   │   │   ├── social.py     #   Open Graph tags (X, Instagram, etc.)
│   │   │   └── registry.py   #   get_extractor(url) -> the right one
│   │   ├── judge.py          # sends content + criteria.md to Claude, parses the verdict
│   │   ├── pipeline.py       # extract -> judge, shared by the CLI and the API
│   │   ├── api.py            # FastAPI app the web UI talks to
│   │   ├── cli.py            # `article-judge single|batch`
│   │   ├── criteria.py       # load/save criteria.md
│   │   ├── config.py         # env-based settings (model, concurrency, ...)
│   │   ├── models.py         # domain dataclasses
│   │   └── schemas.py        # pydantic request/response shapes for the API
│   ├── tests/                 # pytest — extractor routing, error handling, API contract
│   ├── criteria.md            # your collection rules — edit this, not the code
│   ├── links.txt              # paste links here for CLI batch mode
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js                 # vanilla JS — no build step, no framework
└── .gitignore
```

**Why it's split up this way:** every link type has to be fetched
differently (a news page's HTML isn't a YouTube transcript isn't a
tweet's Open Graph tags), but everything downstream — judging, CLI output,
the API, the CSV export — only ever deals with the same shape of data.
`extractors/base.py` is that shape's contract. Adding a new link type later
(say, a podcast RSS entry) means adding one new file that implements
`matches()` / `extract()` and one line in `registry.py` — nothing else in
the app has to change.

## Setup

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env
# then edit .env and paste in your key
```

Get an API key at [console.anthropic.com](https://console.anthropic.com)
(billed separately from a claude.ai subscription).

## Running it

**CLI**

```bash
article-judge single "https://example.com/news/123"

article-judge batch links.txt
# or paste links directly:
article-judge batch
```

**Web UI**

Terminal 1 — start the backend:

```bash
cd backend
uvicorn article_judge.api:app --reload --port 8000
```

Terminal 2 — serve the frontend (opening `index.html` directly also
works in most browsers, but a static server avoids edge cases):

```bash
cd frontend
python -m http.server 5500
```

Open `http://localhost:5500`. Paste links, hit **Run judgment**, and
results stamp in live as each one finishes — no need to wait for the
whole batch. If your backend runs somewhere other than
`localhost:8000`, update the **Connection** field in the sidebar.

## Customizing the criteria

Edit `backend/criteria.md` directly, or use the **Collection criteria**
panel in the web UI (it reads and writes the same file). Every run reads
it fresh — no restart needed. Rules are written in terms of topic and
content, not link type, so the same criteria file judges articles,
videos, and social posts consistently.

## Testing

```bash
cd backend
pytest
```

Tests cover URL-routing logic, pipeline error handling, and the API
contract. They don't call Claude or hit real news/YouTube/social sites,
so they run offline and don't need an API key.

## Notes / limitations

- **Paywalled or JS-rendered pages** may fail to extract. You'll get a
  clear error in the result, not a silently wrong verdict.
- **Social platforms** (X, Instagram, etc.) often require login or an
  official API for full access; this tool reads whatever Open Graph
  preview data the page serves publicly, which can be thin or blocked
  entirely on some platforms.
- **YouTube captions** aren't available for every video (auto-captions
  disabled, age-restricted, etc.) — when that happens the judge falls
  back to the title and channel name only.
- Default model is `claude-sonnet-5` (`backend/src/article_judge/config.py`,
  or set `ARTICLE_JUDGE_MODEL` in `.env`). Swap to
  `claude-haiku-4-5-20251001` for large batches where cost/latency
  matters more than squeezing out the last bit of accuracy.
- `ARTICLE_JUDGE_MAX_WORKERS` (default 5) controls how many links are
  processed concurrently — lower it if you hit API rate limits.
