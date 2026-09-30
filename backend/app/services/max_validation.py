from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from urllib.parse import unquote_plus

from ..core.config import settings

log = logging.getLogger(__name__)

AUTH_TTL_SECONDS = 3600


@dataclass
class InitData:
    raw: str
    user_id: str
    username: str | None
    first_name: str | None
    last_name: str | None
    photo_url: str | None
    language_code: str
    auth_date: int
    start_param: str | None
    user: dict
    chat: dict | None


def _parse_pairs(web_app_data: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for token in web_app_data.split("&"):
        if not token:
            continue
        if "=" not in token:
            pairs.append((token, ""))
            continue
        k, v = token.split("=", 1)
        pairs.append((k, v))
    return pairs


def _decode(value: str) -> str:
    return unquote_plus(value)


def _calc_signature(system_token: str, launch_params: str) -> str:
    secret_key = hmac.new(b"WebAppData", system_token.encode("utf-8"), hashlib.sha256).digest()
    sig = hmac.new(secret_key, launch_params.encode("utf-8"), hashlib.sha256).hexdigest()
    return sig


class InitDataValidationError(Exception):
    pass


def validate_init_data(web_app_data: str, *, token: str | None) -> InitData:
    pairs = _parse_pairs(web_app_data)
    if not pairs:
        raise InitDataValidationError("Пустой WebAppData")

    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise InitDataValidationError("Дублирующиеся ключи в WebAppData")

    pairs_dict: dict[str, str] = {k: v for k, v in pairs}
    if "hash" not in pairs_dict:
        raise InitDataValidationError("Отсутствует hash")

    received_hash = pairs_dict.pop("hash")

    decoded: dict[str, str] = {k: _decode(v) for k, v in pairs_dict.items()}

    sorted_pairs = sorted(decoded.items(), key=lambda kv: kv[0])
    launch_params = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

    if not settings.DEV_BYPASS_INITDATA:
        if not token:
            raise InitDataValidationError("Токен бота не настроен")
        expected = _calc_signature(token, launch_params)
        if not hmac.compare_digest(expected, received_hash):
            raise InitDataValidationError("Подпись initData не совпадает")

    try:
        auth_date = int(decoded.get("auth_date", "0"))
    except ValueError as e:
        raise InitDataValidationError("Некорректный auth_date") from e
    if auth_date and time.time() - auth_date > AUTH_TTL_SECONDS:
        raise InitDataValidationError("Устаревший initData (auth_date)")

    user: dict = {}
    if "user" in decoded:
        try:
            user = json.loads(decoded["user"])
        except json.JSONDecodeError:
            user = {}

    if not user.get("id") and decoded.get("user_id"):
        user["id"] = decoded.get("user_id")
    for k in ("first_name", "last_name", "username", "photo_url", "language_code"):
        if not user.get(k) and decoded.get(k):
            user[k] = decoded.get(k)

    user_id = str(user.get("id") or decoded.get("user_id") or "")
    if not user_id:
        raise InitDataValidationError("Отсутствует user_id")

    chat: dict | None = None
    if "chat" in decoded:
        try:
            chat = json.loads(decoded["chat"])
        except json.JSONDecodeError:
            chat = None

    return InitData(
        raw=web_app_data,
        user_id=user_id,
        username=user.get("username"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        photo_url=user.get("photo_url"),
        language_code=str(user.get("language_code") or "ru"),
        auth_date=auth_date,
        start_param=decoded.get("start_param"),
        user=user,
        chat=chat,
    )


def validate_contact(
    phone: str, auth_date: int, user_id: str, received_hash: str, *, token: str | None
) -> bool:
    if not token:
        return bool(settings.DEV_BYPASS_INITDATA)

    phone_clean = phone[1:] if phone.startswith("+") else phone
    pairs = {
        "authDate": str(auth_date),
        "phone": phone_clean,
        "userId": str(user_id),
    }
    msg = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    sig = hmac.new(token.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, received_hash)
