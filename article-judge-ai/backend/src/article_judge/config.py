"""Central configuration. Reads from environment variables so behavior can be
tuned per-deployment without touching code (12-factor style)."""

import os
from pathlib import Path

# backend/src/article_judge/config.py -> parents[2] == backend/
BASE_DIR = Path(__file__).resolve().parents[2]

CRITERIA_PATH = BASE_DIR / "criteria.md"

MODEL = os.environ.get("ARTICLE_JUDGE_MODEL", "claude-sonnet-5")
MAX_WORKERS = int(os.environ.get("ARTICLE_JUDGE_MAX_WORKERS", "5"))
MAX_BODY_CHARS = int(os.environ.get("ARTICLE_JUDGE_MAX_BODY_CHARS", "6000"))
REQUEST_TIMEOUT_SECONDS = 15

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
