"""Pydantic schemas for the HTTP API. Kept separate from models.py: these
describe the wire format, not the domain."""

from pydantic import BaseModel, Field


class SingleJudgeRequest(BaseModel):
    url: str


class BatchJudgeRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)


class CriteriaUpdateRequest(BaseModel):
    content: str
