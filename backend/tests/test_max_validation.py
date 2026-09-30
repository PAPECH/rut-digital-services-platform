"""Тесты алгоритма валидации initData MAX (§4.6 ТЗ)."""

import hashlib
import hmac
import json
import time
from urllib.parse import quote

import pytest

from app.core.config import settings
from app.services import max_validation


BOT_TOKEN = "test-bot-token-1234567890"


def _build_init_data(
    *,
    bot_token: str = BOT_TOKEN,
    user: dict | None = None,
    chat: dict | None = None,
    auth_date: int | None = None,
    start_param: str | None = None,
    extra: dict | None = None,
    corrupt_hash: bool = False,
) -> str:
    """Собрать валидный initData с правильной подписью.

    Шаги соответствуют §4.6 ТЗ:
      1. Собрать пары (URL-кодированные значения)
      2. Декодировать, отсортировать по ключу
      3. HMAC_SHA256 в два шага
    """
    if user is None:
        user = {"id": 12345, "first_name": "Тест", "last_name": "Пользователь", "language_code": "ru"}
    if auth_date is None:
        auth_date = int(time.time())

    raw_params: dict[str, str] = {
        "auth_date": str(auth_date),
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
    }
    if chat is not None:
        raw_params["chat"] = json.dumps(chat, ensure_ascii=False, separators=(",", ":"))
    if start_param is not None:
        raw_params["start_param"] = start_param
    if extra:
        raw_params.update(extra)

    # 4–6: сортировка, склейка декодированными значениями (мы и кодируем, и декодируем потом)
    sorted_items = sorted(raw_params.items(), key=lambda kv: kv[0])
    launch_params = "\n".join(f"{k}={v}" for k, v in sorted_items)

    # 7–9: подпись
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    sig = hmac.new(secret_key, launch_params.encode("utf-8"), hashlib.sha256).hexdigest()
    if corrupt_hash:
        sig = sig[::-1]  # портим подпись

    # query-строка: значения URL-кодированы, hash добавлен последним
    qs_parts: list[str] = [f"{k}={quote(v, safe='')}" for k, v in sorted_items]
    qs_parts.append(f"hash={sig}")
    return "&".join(qs_parts)


@pytest.fixture(autouse=True)
def _dev_bypass_off(monkeypatch):
    """Выключаем dev-bypass, чтобы тесты проверяли реальную HMAC-проверку.

    Task 036: `validate_init_data` больше не читает `settings.MAX_BOT_TOKEN` сама -- вызывающий
    код передаёт токен явно (для каждого бота свой), так что тесты ниже делают то же самое."""
    monkeypatch.setattr(settings, "DEV_BYPASS_INITDATA", False)


def test_validates_correct_signature():
    init = _build_init_data()
    result = max_validation.validate_init_data(init, token=BOT_TOKEN)
    assert result.user_id == "12345"
    assert result.first_name == "Тест"
    assert result.language_code == "ru"


def test_rejects_corrupted_signature():
    init = _build_init_data(corrupt_hash=True)
    with pytest.raises(max_validation.InitDataValidationError):
        max_validation.validate_init_data(init, token=BOT_TOKEN)


def test_rejects_signature_signed_with_a_different_bots_token():
    """Regression for Task 036: MAX signs `initData` per-bot -- verifying it against ANY other
    bot's token (not just a corrupted hash) must fail, exactly the bug that made every bot but one
    unable to log in when verification was pinned to a single global token."""
    init = _build_init_data(bot_token=BOT_TOKEN)
    with pytest.raises(max_validation.InitDataValidationError, match="Подпись"):
        max_validation.validate_init_data(init, token="a-different-bots-token")


def test_rejects_stale_auth_date():
    init = _build_init_data(auth_date=int(time.time()) - max_validation.AUTH_TTL_SECONDS - 60)
    with pytest.raises(max_validation.InitDataValidationError):
        max_validation.validate_init_data(init, token=BOT_TOKEN)


def test_rejects_missing_user_id():
    init = _build_init_data(user={"first_name": "X"})  # без id
    with pytest.raises(max_validation.InitDataValidationError):
        max_validation.validate_init_data(init, token=BOT_TOKEN)


def test_extracts_start_param():
    init = _build_init_data(start_param="admin_login")
    result = max_validation.validate_init_data(init, token=BOT_TOKEN)
    assert result.start_param == "admin_login"


def test_rejects_when_no_token_configured():
    init = _build_init_data()
    with pytest.raises(max_validation.InitDataValidationError, match="не настроен"):
        max_validation.validate_init_data(init, token=None)


def test_dev_bypass_without_token(monkeypatch):
    """DEV_BYPASS_INITDATA=true и пустой токен — подпись не проверяется."""
    monkeypatch.setattr(settings, "DEV_BYPASS_INITDATA", True)
    init = _build_init_data(corrupt_hash=True)
    result = max_validation.validate_init_data(init, token=None)
    assert result.user_id == "12345"


def test_dev_bypass_with_token(monkeypatch):
    """DEV_BYPASS_INITDATA=true работает даже если токен заполнен (для локального теста админки)."""
    monkeypatch.setattr(settings, "DEV_BYPASS_INITDATA", True)
    init = _build_init_data(corrupt_hash=True)
    result = max_validation.validate_init_data(init, token=BOT_TOKEN)
    assert result.user_id == "12345"
