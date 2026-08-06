"""Ingestion and provenance.

Turns raw text into chunks that each know their character offset within the
original document. Small documents (a single draft, the #7 case) stay as one
chunk with offset 0, so span offsets map exactly. Large corpora (the #4 case)
get packed into offset-tagged chunks.
"""
from __future__ import annotations

from .models import Chunk


def chunk_text(doc_id: str, text: str, max_chars: int = 6000) -> list[Chunk]:
    if len(text) <= max_chars:
        return [Chunk(doc_id=doc_id, index=0, text=text, offset=0)]

    chunks: list[Chunk] = []
    idx = 0
    cursor = 0
    n = len(text)
    while cursor < n:
        end = min(cursor + max_chars, n)
        # try to break on a paragraph or sentence boundary near the end
        window = text[cursor:end]
        brk = window.rfind("\n\n")
        if brk == -1 or end == n:
            brk = window.rfind(". ")
        if brk == -1 or end == n:
            brk = len(window)
        else:
            brk += 2
        piece = text[cursor:cursor + brk]
        chunks.append(Chunk(doc_id=doc_id, index=idx, text=piece, offset=cursor))
        idx += 1
        cursor += brk
    return chunks


def locate(needle: str, haystack: str, start: int = 0) -> tuple[int, int] | None:
    """Find a returned quote inside the source text to recover its offsets."""
    if not needle:
        return None
    i = haystack.find(needle, start)
    if i != -1:
        return i, i + len(needle)
    trimmed = needle.strip()
    if trimmed and trimmed != needle:
        i = haystack.find(trimmed, start)
        if i != -1:
            return i, i + len(trimmed)
    return None
