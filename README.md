# Article Judge AI

A small CLI tool that reads a news article from a URL and decides whether
it should be **collected** or **skipped**, based on rules you define in a
plain-text file — no manual reading required.

Originally built to automate a repetitive "should I collect this article
or not?" judgment call that used to require reading each link by hand.
Point it at a link (or a list of links), and it fetches the page,
extracts the article text, and asks Claude to judge it against your
criteria.

## How it works

```
URL → fetch + extract article text → Claude judges against criteria.md → COLLECT / SKIP + reason
```

The judging logic isn't hardcoded — it lives entirely in [`criteria.md`](./criteria.md).
Change that file and the tool's behavior changes immediately, no code edits needed.

## Setup

```bash
pip install -r requirements.txt
```

Get an API key at [console.anthropic.com](https://console.anthropic.com)
(API keys are billed separately from a claude.ai subscription), then
create a `.env` file in this folder:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## Usage

**Single link:**

```bash
python judge.py "https://example.com/news/123"
```

```
==================================================
Source   : TechCrunch
Title    : Startup X raises $50M to build AI coding agents
--------------------------------------------------
Decision : ✅ Collect
Topic    : Funding round for an AI coding tool startup
Reason   : Matches the "funding rounds involving AI companies" criterion.
==================================================
```

**Many links at once:**

Paste your links into [`links.txt`](./links.txt) (one per line), then:

```bash
python judge_batch.py links.txt
```

Or pipe links straight into the terminal without a file:

```bash
python judge_batch.py
# paste URLs, one per line, then Ctrl+D (Mac/Linux) or Ctrl+Z + Enter (Windows)
```

Batch mode processes links concurrently, prints a live summary, and
writes a `results_<timestamp>.csv` file you can open directly in Excel.

## Customizing the criteria

Edit [`criteria.md`](./criteria.md). It ships with an example for
monitoring AI/tech product news — replace it with rules for whatever
you're actually tracking (a competitor, an industry, a person, a
keyword, etc.). Be as specific as you like; the more concrete the
examples in your criteria, the more consistent the judgments.

## Notes / limitations

- Pages that require a login, sit behind a paywall, or render content
  via JavaScript may fail to extract — you'll get a clear error instead
  of a silent wrong answer.
- Default model is `claude-sonnet-5` (set in `common.py`). Swap to
  `claude-haiku-4-5-20251001` for lower cost/latency on large batches,
  at a small accuracy tradeoff.
- `MAX_WORKERS` in `judge_batch.py` controls concurrency (default 5).
  Lower it if you hit API rate limits.

## Project structure

```
article-judge-ai/
├── judge.py         # single-URL CLI
├── judge_batch.py   # multi-URL / batch CLI
├── common.py         # shared fetch + judge logic
├── criteria.md        # your collection rules (edit this, not the code)
├── links.txt          # paste links here for batch mode
└── requirements.txt
```
