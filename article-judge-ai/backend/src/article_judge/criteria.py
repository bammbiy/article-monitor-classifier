"""Load and save the user-editable collection criteria (criteria.md).

This is the only place that knows criteria.md lives on disk — the CLI and
the API both go through here, and the web UI's "edit criteria" panel writes
back through this module too.
"""

from .config import CRITERIA_PATH


def load_criteria() -> str:
    if not CRITERIA_PATH.exists():
        raise FileNotFoundError(f"{CRITERIA_PATH} not found.")
    return CRITERIA_PATH.read_text(encoding="utf-8")


def save_criteria(content: str) -> None:
    CRITERIA_PATH.write_text(content, encoding="utf-8")
