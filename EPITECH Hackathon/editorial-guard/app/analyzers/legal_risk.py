"""Legal risk analyzer (topic #7).

A linter for pre-publication legal risk. It never gives legal advice or a verdict.
It flags spans that match known risk patterns, explains why in plain language,
cites the editorial standard behind each flag, and suggests a rewrite. The human
editor accepts, rewrites, or ignores. Nothing is ever changed automatically.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..core.ingest import locate
from ..core.models import Chunk, Finding, SourceRef
from .base import Analyzer

RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "rules.json"


def _load_rules() -> dict[str, dict[str, Any]]:
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return {r["id"]: r for r in data}


class LegalRiskAnalyzer(Analyzer):
    name = "legal"
    kind = "risk_flag"

    def __init__(self) -> None:
        self.rules = _load_rules()

    # ---- shared helpers -------------------------------------------------

    def _finding(self, rule_id: str, doc_id: str, start: int, end: int,
                 span: str, explanation: str, rewrite: str | None) -> Finding:
        rule = self.rules[rule_id]
        evidence = [SourceRef(label=rule["standard_label"], quote=rule["standard_text"])]
        return Finding(
            kind=self.kind,
            doc_id=doc_id,
            char_start=start,
            char_end=end,
            text=span,
            payload={
                "rule_id": rule_id,
                "category": rule["category"],
                "name": rule["name"],
                "severity": rule["severity"],
                "explanation": explanation or rule["why"],
                "suggested_rewrite": rewrite,
            },
            evidence=evidence,
        )

    # ---- LLM mode -------------------------------------------------------

    def system_prompt(self, context: str = "") -> str:
        base = (
            "You are a careful pre-publication editorial reviewer, like a newspaper's "
            "night lawyer. You do not give legal advice and you do not deliver verdicts. "
            "You flag possible risks so a human editor can judge them. Only flag text that "
            "is actually present in the draft. For each risky span, explain the risk in one "
            "or two sentences and suggest a rewrite that lowers the risk while preserving "
            "the reporting. Return JSON only, no prose."
        )
        if context:
            base += (
                " You have been given the newsroom's own standards or the applicable law. "
                "Prefer these uploaded standards over the built-in rules where they apply, "
                "and when a flag relies on an uploaded standard, quote the specific passage "
                "you relied on."
            )
        return base

    def user_prompt(self, chunk: Chunk, context: str = "") -> str:
        rule_lines = "\n".join(
            f'- {rid}: {r["name"]} (severity: {r["severity"]}). {r["why"]}'
            for rid, r in self.rules.items()
        )
        context_block = ""
        if context:
            context_block = (
                "Uploaded standards or applicable law (prefer these where relevant):\n"
                f"{context}\n\n"
            )
        return (
            f"{context_block}"
            "Built-in rules to check against:\n"
            f"{rule_lines}\n\n"
            "Return a JSON array. Each item must be an object with fields: "
            '"rule_id" (one of the built-in ids above, or "CUSTOM" if the flag comes from '
            'an uploaded standard), "quote" (the exact substring from the draft that '
            'triggers the flag, copied verbatim), "explanation" (one or two sentences), '
            '"standard" (the passage from the uploaded standards you relied on, or null), '
            '"suggested_rewrite" (a safer version of the quote, or null). '
            "If nothing is risky, return [].\n\n"
            "Draft:\n"
            f"{chunk.text}"
        )

    def parse(self, raw: Any, chunk: Chunk, full_text: str) -> list[Finding]:
        if not isinstance(raw, list):
            return []
        findings: list[Finding] = []
        for item in raw:
            rule_id = item.get("rule_id")
            quote = (item.get("quote") or "").strip()
            if not quote:
                continue
            span = locate(quote, full_text)
            if span is None:
                continue
            start, end = span
            if rule_id in self.rules:
                findings.append(self._finding(
                    rule_id, chunk.doc_id, start, end, full_text[start:end],
                    item.get("explanation", ""), item.get("suggested_rewrite")))
            elif rule_id == "CUSTOM":
                findings.append(self._custom_finding(
                    chunk.doc_id, start, end, full_text[start:end],
                    item.get("explanation", "Flagged by an uploaded standard."),
                    item.get("standard") or "Uploaded newsroom standard",
                    item.get("suggested_rewrite")))
        return findings

    def _custom_finding(self, doc_id: str, start: int, end: int, span: str,
                        explanation: str, standard: str, rewrite: str | None) -> Finding:
        return Finding(
            kind=self.kind,
            doc_id=doc_id,
            char_start=start,
            char_end=end,
            text=span,
            payload={
                "rule_id": "CUSTOM",
                "category": "custom_standard",
                "name": "Matches an uploaded standard",
                "severity": "medium",
                "explanation": explanation,
                "suggested_rewrite": rewrite,
            },
            evidence=[SourceRef(label="Uploaded standard", quote=standard)],
        )

    # ---- offline mock mode ---------------------------------------------

    ACCUSATION = re.compile(
        r"\b(stole|embezzled|defrauded|laundered|bribed|took\s+bribes|murdered|"
        r"assaulted|forged|smuggled|trafficked|swindled)\b", re.I)
    ATTRIBUTION = re.compile(
        r"(alleged|allegedly|accus|charg|prosecutor|police|according to|reportedly|"
        r"suspect|indict|convicted|court heard|claim)", re.I)
    LABELS = re.compile(
        r"\b(the\s+(fraudster|thief|criminal|crook|liar|killer|swindler))\b", re.I)
    LOADED = re.compile(
        r"\b(certainly|obviously|clearly|undoubtedly|of course|furious|outrageous|"
        r"disgraceful|shocking|scandalous|shameful)\b", re.I)
    ABSOLUTE = re.compile(
        r"\b(always|never|the only|everyone|nobody|no one|the worst|the best)\b", re.I)
    PRIVACY = re.compile(
        r"(lives\s+at\s+[^.,\n]+|\b\d{1,4}\s+[A-Z][a-z]+\s+"
        r"(street|st|avenue|ave|road|rd|lane|drive|dr)\b)")
    LONG_QUOTE = re.compile(r"[\"\u201c]([^\"\u201d]{140,})[\"\u201d]")

    # directive lines in an uploaded standard, e.g. 'Avoid "collateral damage".'
    DIRECTIVE = re.compile(r"(avoid|do not use|don't use|never use|ban|banned|prohibit|"
                           r"discourage|refrain from)", re.I)
    QUOTED = re.compile(r"[\"\u201c\u2018']([^\"\u201d\u2019']{2,60})[\"\u201d\u2019']")

    def mock(self, chunk: Chunk, full_text: str, context: str = "") -> list[Finding]:
        text = chunk.text
        base = chunk.offset
        out: list[Finding] = []

        out.extend(self._mock_context(chunk, context))

        for m in self.ACCUSATION.finditer(text):
            window = text[max(0, m.start() - 70):m.start()]
            if self.ATTRIBUTION.search(window):
                continue
            # flag the sentence around the accusation
            s, e = self._sentence_bounds(text, m.start(), m.end())
            span = text[s:e].strip()
            abs_s = base + text.find(span, s)
            rewrite = self._attribute(span)
            out.append(self._finding(
                "R1", chunk.doc_id, abs_s, abs_s + len(span), span,
                "This states wrongdoing as fact without attributing it to a source or a charge.",
                rewrite))

        for m in self.LABELS.finditer(text):
            s, e = base + m.start(), base + m.end()
            span = text[m.start():m.end()]
            noun = m.group(2).lower()
            out.append(self._finding(
                "R2", chunk.doc_id, s, e, span,
                f"Labelling someone '{span}' asserts guilt before conviction.",
                f"the accused" if noun != "killer" else "the accused"))

        for m in self.LOADED.finditer(text):
            s, e = base + m.start(), base + m.end()
            span = text[m.start():m.end()]
            out.append(self._finding(
                "R3", chunk.doc_id, s, e, span,
                f"The word '{span}' inserts a judgement into neutral reporting.",
                ""))

        for m in self.ABSOLUTE.finditer(text):
            s, e = base + m.start(), base + m.end()
            span = text[m.start():m.end()]
            out.append(self._finding(
                "R4", chunk.doc_id, s, e, span,
                f"'{span}' is an absolute that is hard to defend as literally true.",
                ""))

        for m in self.PRIVACY.finditer(text):
            s, e = base + m.start(), base + m.end()
            span = text[m.start():m.end()]
            out.append(self._finding(
                "R5", chunk.doc_id, s, e, span,
                "This looks like a private identifying detail such as a home address.",
                "[private detail removed unless there is a clear public interest]"))

        for m in self.LONG_QUOTE.finditer(text):
            s, e = base + m.start(), base + m.end()
            span = text[m.start():m.end()]
            out.append(self._finding(
                "R6", chunk.doc_id, s, e, span,
                "This is a long verbatim quotation that may exceed fair use.",
                "[paraphrase and keep any direct quote short and attributed]"))

        return out

    def _mock_context(self, chunk: Chunk, context: str) -> list[Finding]:
        """Offline effect for uploaded standards: flag quoted banned terms.

        Scans the uploaded standards for directive lines (avoid / do not use / ban)
        that quote a specific term, then flags occurrences of that term in the draft
        and cites the standard's line as the proof.
        """
        if not context:
            return []
        terms: list[tuple[str, str]] = []
        for line in context.splitlines():
            if self.DIRECTIVE.search(line):
                for q in self.QUOTED.finditer(line):
                    terms.append((q.group(1).strip(), line.strip()))
        if not terms:
            return []
        out: list[Finding] = []
        text = chunk.text
        for term, rule_line in terms:
            for m in re.finditer(re.escape(term), text, re.I):
                s = chunk.offset + m.start()
                e = chunk.offset + m.end()
                out.append(self._custom_finding(
                    chunk.doc_id, s, e, text[m.start():m.end()],
                    f"'{term}' is flagged by an uploaded standard.",
                    rule_line, None))
        return out

    @staticmethod
    def _sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
        left = max(text.rfind(". ", 0, start), text.rfind("\n", 0, start))
        s = 0 if left == -1 else left + 1
        right_candidates = [i for i in (text.find(". ", end), text.find("\n", end)) if i != -1]
        e = min(right_candidates) + 1 if right_candidates else len(text)
        return s, e

    @staticmethod
    def _attribute(sentence: str) -> str:
        s = sentence.strip()
        # keep the leading word as-is if it looks like a proper noun or title,
        # otherwise lowercase it so the sentence reads naturally
        titles = ("Mayor", "President", "Mr", "Mrs", "Ms", "Dr", "Sir", "Lord", "Chief")
        first = s.split(" ", 1)[0] if s else ""
        if s and not (first in titles or (first[:1].isupper() and first[1:2].islower())):
            s = s[0].lower() + s[1:]
        return f"Prosecutors allege that {s}"
