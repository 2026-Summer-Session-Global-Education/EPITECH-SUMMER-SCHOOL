"""Shared engine types.

Every analyzer, whether it flags legal risk (#7) or extracts relationships (#4),
produces the same thing: a Finding. A Finding is a claim, anchored to a span of
source text, backed by evidence. That single abstraction is what lets the two
tasks share one core.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class SourceRef(BaseModel):
    """Where a finding's evidence lives.

    For the relation analyzer (#4) this points backward into the source corpus:
    the sentence that proves the relationship is real. For the legal analyzer (#7)
    it points sideways to the rule or standard that makes the flag legitimate.
    Same field, different target.
    """
    label: str
    quote: str
    doc_id: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None


class Finding(BaseModel):
    kind: str  # "risk_flag" | "relation"
    doc_id: str
    char_start: int
    char_end: int
    text: str  # the exact span in the analyzed document
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[SourceRef] = Field(default_factory=list)


class Chunk(BaseModel):
    doc_id: str
    index: int
    text: str
    offset: int  # char offset of this chunk within the whole document


class AnalyzeResult(BaseModel):
    doc_id: str
    mode: str  # "mock" | "live"
    analyzer: str
    findings: list[Finding]
    counts: dict[str, int] = Field(default_factory=dict)
    note: Optional[str] = None  # why we fell back to mock, if we did
