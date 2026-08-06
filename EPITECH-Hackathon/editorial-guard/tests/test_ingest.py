from app.core.ingest import chunk_text, locate


def test_single_chunk_offset_zero():
    text = "A short draft."
    chunks = chunk_text("d", text)
    assert len(chunks) == 1
    assert chunks[0].offset == 0
    assert chunks[0].text == text


def test_chunks_preserve_offsets():
    text = ("Para one. " * 400) + "\n\n" + ("Para two. " * 400)
    chunks = chunk_text("d", text, max_chars=1000)
    assert len(chunks) > 1
    for ch in chunks:
        assert text[ch.offset:ch.offset + len(ch.text)] == ch.text


def test_locate_finds_span():
    text = "The mayor stole funds."
    span = locate("stole funds", text)
    assert span is not None
    s, e = span
    assert text[s:e] == "stole funds"
