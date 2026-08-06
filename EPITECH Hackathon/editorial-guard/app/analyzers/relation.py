"""Relation extractor (topic #4).

The "add later" plugin. Included in a lighter form to prove the seam is real: it
implements the same Analyzer interface, so the runner drives it with no changes.
Its mock extracts naive person/organization relationships from role phrases like
"X, chairman of Y". Swap in a real LLM key and the prompt takes over.
"""
from __future__ import annotations

import re
from typing import Any

from ..core.ingest import locate
from ..core.models import Chunk, Finding, SourceRef
from .base import Analyzer


class RelationAnalyzer(Analyzer):
    name = "relation"
    kind = "relation"

    ROLE = re.compile(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}),?\s+"
        r"(?:the\s+)?(chief executive|ceo|chairman|chairwoman|director|founder|"
        r"president|owner|head|treasurer)\s+of\s+"
        r"([A-Z][A-Za-z0-9&.\-]+(?:\s+[A-Z][A-Za-z0-9&.\-]+){0,3})", re.I)

    def system_prompt(self, context: str = "") -> str:
        return (
            "You extract factual relationships between named entities from text. "
            "Only extract relationships the text actually supports. Return JSON only."
        )

    def user_prompt(self, chunk: Chunk, context: str = "") -> str:
        return (
            "Return a JSON array. Each item is an object with fields: "
            '"subject", "predicate", "object", and "quote" (the exact supporting '
            "substring copied verbatim). If none, return [].\n\n"
            f"Text:\n{chunk.text}"
        )

    def parse(self, raw: Any, chunk: Chunk, full_text: str) -> list[Finding]:
        if not isinstance(raw, list):
            return []
        out: list[Finding] = []
        for item in raw:
            quote = (item.get("quote") or "").strip()
            subj, pred, obj = item.get("subject"), item.get("predicate"), item.get("object")
            if not (quote and subj and pred and obj):
                continue
            span = locate(quote, full_text)
            if span is None:
                continue
            s, e = span
            out.append(self._relation(chunk.doc_id, s, e, full_text[s:e], subj, pred, obj))
        return out

    def mock(self, chunk: Chunk, full_text: str, context: str = "") -> list[Finding]:
        out: list[Finding] = []
        for m in self.ROLE.finditer(chunk.text):
            s = chunk.offset + m.start()
            e = chunk.offset + m.end()
            span = chunk.text[m.start():m.end()]
            out.append(self._relation(
                chunk.doc_id, s, e, span,
                m.group(1).strip(), m.group(2).lower().strip(), m.group(3).strip()))
        return out

    def _relation(self, doc_id: str, s: int, e: int, span: str,
                  subj: str, pred: str, obj: str) -> Finding:
        return Finding(
            kind=self.kind,
            doc_id=doc_id,
            char_start=s,
            char_end=e,
            text=span,
            payload={"subject": subj, "predicate": pred, "object": obj},
            evidence=[SourceRef(label=doc_id, quote=span, doc_id=doc_id,
                                char_start=s, char_end=e)],
        )
