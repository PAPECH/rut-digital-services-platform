from __future__ import annotations

import time

import pytest

from app.services.content_preview_tokens import (
    InvalidPreviewToken,
    make_preview_token,
    verify_preview_token,
)


def test_preview_token_round_trips() -> None:
    token, expires_at = make_preview_token(bot_instance_id=7, category_id=42)
    assert expires_at > int(time.time())

    payload = verify_preview_token(token)
    assert payload.bot_instance_id == 7
    assert payload.category_id == 42
    assert payload.expires_at == expires_at


def test_preview_token_rejects_expired() -> None:
    token, _ = make_preview_token(bot_instance_id=1, category_id=1, ttl_seconds=-10)
    with pytest.raises(InvalidPreviewToken):
        verify_preview_token(token)


def test_preview_token_rejects_tampered_ids() -> None:
    token, _ = make_preview_token(bot_instance_id=1, category_id=1)
    bot_id, category_id, exp, nonce, sig = token.split(".")
    tampered = ".".join([bot_id, "999", exp, nonce, sig])
    with pytest.raises(InvalidPreviewToken):
        verify_preview_token(tampered)


def test_preview_token_rejects_malformed_input() -> None:
    with pytest.raises(InvalidPreviewToken):
        verify_preview_token("not-a-real-token")
    with pytest.raises(InvalidPreviewToken):
        verify_preview_token("1.2.notanumber.nonce.sig")


def test_two_tokens_for_same_target_do_not_collide() -> None:
    token_a, _ = make_preview_token(bot_instance_id=1, category_id=1)
    token_b, _ = make_preview_token(bot_instance_id=1, category_id=1)
    assert token_a != token_b, "nonce must make repeated tokens unguessable/unique"
