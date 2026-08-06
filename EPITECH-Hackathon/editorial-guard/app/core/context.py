"""Uploaded standards context.

Extracts text from an uploaded .txt or .pdf file (newsroom rules, a country's
press law) and stores it. In live mode the combined text is injected into the
analyzer's prompt so the model grounds its flags in the newsroom's own standards
and cites the specific passage. In mock mode a light rule extractor still lets
uploaded standards flag banned terms.
"""
from __future__ import annotations

import io

MAX_CONTEXT_CHARS = 30000


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return _extract_pdf(data)
    # default: treat as plain text
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return data.decode("latin-1", errors="ignore")


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError(
            "pypdf is required to read PDF files. Install it with 'pip install pypdf'."
        ) from exc
    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts).strip()


def combined_context(docs: list[dict]) -> str:
    """Concatenate uploaded standards into one prompt-ready block, truncated."""
    if not docs:
        return ""
    blocks = []
    for d in docs:
        blocks.append(f"### Source: {d['filename']}\n{d['text']}")
    text = "\n\n".join(blocks)
    if len(text) > MAX_CONTEXT_CHARS:
        text = text[:MAX_CONTEXT_CHARS] + "\n...[truncated]"
    return text
