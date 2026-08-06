"""The extraction runner.

This is the task-agnostic spine. It ingests, chunks, drives whatever analyzer it
is handed, collects findings, and post-processes. It does not know or care which
task it is running. That is the whole point of the seam.
"""
from __future__ import annotations

from ..analyzers.base import Analyzer
from .ingest import chunk_text
from .llm import LLMClient
from .models import AnalyzeResult, Finding


class Runner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(self, doc_id: str, text: str, analyzer: Analyzer,
            context: str = "") -> AnalyzeResult:
        chunks = chunk_text(doc_id, text)
        findings: list[Finding] = []
        mode = "mock"
        note: str | None = None

        if self.llm.live:
            try:
                for chunk in chunks:
                    raw = self.llm.complete_json(
                        analyzer.system_prompt(context),
                        analyzer.user_prompt(chunk, context))
                    findings.extend(analyzer.parse(raw, chunk, text))
                mode = "live"
            except Exception as exc:
                # surface why we fell back instead of hiding it
                findings = []
                for chunk in chunks:
                    findings.extend(analyzer.mock(chunk, text, context))
                mode = "mock"
                note = "live call failed, showing offline results: " + self.llm.explain(exc)
                self.llm.last_error = note
        else:
            for chunk in chunks:
                findings.extend(analyzer.mock(chunk, text, context))

        findings = analyzer.postprocess(findings)
        return AnalyzeResult(
            doc_id=doc_id,
            mode=mode,
            analyzer=analyzer.name,
            findings=findings,
            counts=self._counts(findings),
            note=note,
        )

    @staticmethod
    def _counts(findings: list[Finding]) -> dict[str, int]:
        counts = {"high": 0, "medium": 0, "low": 0, "total": len(findings)}
        for f in findings:
            sev = f.payload.get("severity")
            if sev in counts:
                counts[sev] += 1
        return counts
