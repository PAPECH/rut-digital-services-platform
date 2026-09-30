from __future__ import annotations

from app.modules.form_tests.domain.message_split import split_message


def test_short_text_is_a_single_chunk() -> None:
    assert split_message("hello", 100) == ["hello"]


def test_splits_at_paragraph_boundaries_without_exceeding_the_limit() -> None:
    paragraphs = [
        "Первый абзац текста результата. " * 2,
        "Второй абзац. " * 2,
        "Третий.",
    ]
    text = "\n\n".join(paragraphs)
    chunks = split_message(text, 60)
    assert len(chunks) > 1
    assert all(len(chunk) <= 60 for chunk in chunks)
    # Word-wrapping a paragraph that overflows the limit necessarily drops the exact
    # whitespace at chunk boundaries (it's split precisely where a space was); every word
    # survives in order, which is what actually matters for a chat message.
    assert " ".join(chunks).split() == text.split()


def test_a_single_paragraph_longer_than_the_limit_wraps_at_word_boundaries() -> None:
    text = "слово " * 40
    chunks = split_message(text, 25)
    assert all(len(chunk) <= 25 for chunk in chunks)
    assert " ".join(chunks).split() == text.split()


def test_a_single_word_longer_than_the_limit_is_hard_cut_as_a_last_resort() -> None:
    text = "а" * 100
    chunks = split_message(text, 30)
    assert all(len(chunk) <= 30 for chunk in chunks)
    assert "".join(chunks) == text


def test_reconstructs_exactly_when_no_splitting_is_needed() -> None:
    text = "Одна строка без переносов."
    assert split_message(text, 4000) == [text]
