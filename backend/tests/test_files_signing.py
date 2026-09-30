"""Тесты подписанных URL для вложений."""

import time

import pytest

from app.core.config import settings
from app.core.errors import ApiError
from app.services import files as files_svc


def test_verify_ok_for_valid_signature():
    url = files_svc.make_signed_url(42, ttl_seconds=60)
    # Извлекаем exp и sig
    qs = url.split("?", 1)[1]
    params = dict(p.split("=", 1) for p in qs.split("&"))
    files_svc.verify_signed(42, int(params["exp"]), params["sig"])  # не должно бросать


def test_verify_rejects_expired():
    sig = files_svc._sign(42, int(time.time()) - 10)  # уже истёк
    with pytest.raises(ApiError) as ei:
        files_svc.verify_signed(42, int(time.time()) - 10, sig)
    assert ei.value.detail["code"] == "link_expired"


def test_verify_rejects_wrong_signature():
    with pytest.raises(ApiError) as ei:
        files_svc.verify_signed(42, int(time.time()) + 60, "deadbeef")
    assert ei.value.detail["code"] == "bad_signature"


def test_verify_rejects_wrong_id():
    """Подпись от id=42 не должна валидироваться для id=43."""
    url = files_svc.make_signed_url(42, ttl_seconds=60)
    qs = url.split("?", 1)[1]
    params = dict(p.split("=", 1) for p in qs.split("&"))
    with pytest.raises(ApiError) as ei:
        files_svc.verify_signed(43, int(params["exp"]), params["sig"])
    assert ei.value.detail["code"] == "bad_signature"


def test_ttl_minus_one_never_expires():
    """Task 025: content-module attachment URLs are minted with ttl_seconds=-1 so public bot
    assets (card images, file_list files) never go stale. `exp=-1` must stay valid no matter how
    much time has passed -- unlike a real expiry, there is no future point at which this should
    start rejecting."""
    url = files_svc.make_signed_url(42, ttl_seconds=-1)
    qs = url.split("?", 1)[1]
    params = dict(p.split("=", 1) for p in qs.split("&"))
    assert params["exp"] == "-1"

    files_svc.verify_signed(42, -1, params["sig"])  # valid right away

    future = time.time() + 60 * 60 * 24 * 365 * 10  # +10 years
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(time, "time", lambda: future)
        files_svc.verify_signed(42, -1, params["sig"])  # still valid


def test_delete_file_removes_bytes_and_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOADS_DIR", str(tmp_path))
    relative_path, _ = files_svc.store_file(b"hello", original_name="note.txt")
    assert (tmp_path / relative_path).exists()

    files_svc.delete_file(relative_path)
    assert not (tmp_path / relative_path).exists()

    files_svc.delete_file(relative_path)  # already gone -- must not raise


def test_delete_file_ignores_paths_outside_uploads_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOADS_DIR", str(tmp_path))
    outside = tmp_path.parent / "escaped.txt"
    outside.write_bytes(b"secret")

    files_svc.delete_file("../escaped.txt")

    assert outside.exists()
