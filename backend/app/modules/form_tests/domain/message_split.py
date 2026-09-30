from __future__ import annotations


def split_message(text: str, limit: int) -> list[str]:
    """Split `text` into a sequence of chunks each at most `limit` characters, breaking at
    paragraph boundaries (blank lines) first, then line boundaries, and only as a last resort
    at a word boundary mid-line -- so a multi-scale result that exceeds a channel's per-message
    length limit (MAX's is 4000 characters, see Task 068's Security section) arrives as several
    coherent messages instead of being cut mid-sentence."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(paragraph) <= limit:
            current = paragraph
            continue
        chunks.extend(_split_long_paragraph(paragraph, limit))
    if current:
        chunks.append(current)
    return chunks


def _split_long_paragraph(paragraph: str, limit: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in paragraph.split("\n"):
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(line) <= limit:
            current = line
            continue
        pieces, current = _wrap_long_line(line, limit)
        chunks.extend(pieces)
    if current:
        chunks.append(current)
    return chunks


def _wrap_long_line(line: str, limit: int) -> tuple[list[str], str]:
    chunks: list[str] = []
    piece = ""
    for word in line.split(" "):
        candidate = f"{piece} {word}" if piece else word
        if len(candidate) <= limit:
            piece = candidate
            continue
        if piece:
            chunks.append(piece)
        piece = ""
        remainder = word
        while len(remainder) > limit:
            chunks.append(remainder[:limit])
            remainder = remainder[limit:]
        piece = remainder
    return chunks, piece
