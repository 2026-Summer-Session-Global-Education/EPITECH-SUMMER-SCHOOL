"""The Analyzer interface: the single seam between the shared core and a task.

The runner is task-blind. It calls these methods and never knows whether it is
flagging legal risk or extracting relationships. Adding a new capability means
writing one more Analyzer, not touching the core.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..core.models import Chunk, Finding


class Analyzer(ABC):
    name: str = "base"
    kind: str = "finding"

    @abstractmethod
    def system_prompt(self, context: str = "") -> str:
        """Task instructions for the LLM. `context` holds uploaded standards."""

    @abstractmethod
    def user_prompt(self, chunk: Chunk, context: str = "") -> str:
        """The per-chunk request sent to the LLM."""

    @abstractmethod
    def parse(self, raw: Any, chunk: Chunk, full_text: str) -> list[Finding]:
        """Turn the raw LLM JSON into Findings, attaching provenance."""

    @abstractmethod
    def mock(self, chunk: Chunk, full_text: str, context: str = "") -> list[Finding]:
        """Deterministic offline detection so the app runs with no API key."""

    def postprocess(self, findings: list[Finding]) -> list[Finding]:
        """Task-specific cleanup. Default: sort and drop overlaps."""
        findings = sorted(findings, key=lambda f: (f.char_start, -(f.char_end - f.char_start)))
        kept: list[Finding] = []
        last_end = -1
        for f in findings:
            if f.char_start >= last_end:
                kept.append(f)
                last_end = f.char_end
        return kept
