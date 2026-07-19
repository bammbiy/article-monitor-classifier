"""Domain models. Plain dataclasses on purpose — these represent internal
concepts (an extracted piece of content, a judged result), separate from the
pydantic schemas in schemas.py that shape the HTTP API."""

from dataclasses import dataclass, field


@dataclass
class ExtractedContent:
    """What an Extractor produces after reading a URL."""

    url: str
    source_type: str  # "article" | "youtube" | "social"
    site: str
    title: str
    body: str


@dataclass
class JudgeResult:
    """Final verdict for one link, ready to display or export."""

    no: int
    url: str
    source_type: str
    source: str
    title: str
    decision: str  # "COLLECT" | "SKIP" | "?"
    topic: str = ""
    reason: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "no": self.no,
            "url": self.url,
            "source_type": self.source_type,
            "source": self.source,
            "title": self.title,
            "decision": self.decision,
            "topic": self.topic,
            "reason": self.reason,
            "error": self.error,
        }
