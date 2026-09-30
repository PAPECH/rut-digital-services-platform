from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from maxapi.enums.format import Format
from redis.asyncio import Redis

from .config import settings

log = logging.getLogger(__name__)

PUSH_QUEUE_KEY = f"max:{settings.BOT_SLUG}:push:queue"
LEGACY_PUSH_QUEUE_KEY = "max:push:queue"


def _is_en(language_code: str | None) -> bool:
    lc = (language_code or "").lower()
    return bool(lc) and not lc.startswith("ru")


_STATUS_LABELS_RU = {
    "new": "Новая",
    "in_work": "В работе",
    "done": "Завершено",
    "rejected": "Отклонено",
}
_STATUS_LABELS_EN = {
    "new": "New",
    "in_work": "In progress",
    "done": "Done",
    "rejected": "Rejected",
}


def _format_given_at_msk(given_at_iso: str | None) -> str:
    """Mirrors `_format_given_at_msk` in `main.py` -- duplicated rather than imported since
    `main.py` already imports this module (`from .push import consume`), so the reverse
    import would be circular."""
    if not given_at_iso:
        return ""
    try:
        dt = datetime.fromisoformat(given_at_iso.replace("Z", "+00:00"))
        return dt.astimezone(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M МСК")
    except ValueError:
        return ""


def _format_message(
    kind: str, payload: dict[str, Any], language_code: str | None
) -> str:
    en = _is_en(language_code)
    labels = _STATUS_LABELS_EN if en else _STATUS_LABELS_RU

    if kind == "submission_created":
        return payload.get("reply_on_accept")

    if kind == "consent_accepted":
        # Sent only for a mini-app accept (first-time gate or re-accept during the revoke
        # grace window) -- a bot-chat accept already confirms in place by editing the
        # existing message (see `_consent_accepted_plate` in `main.py`), so this wording is
        # kept identical to that plate for a consistent read regardless of surface.
        when = _format_given_at_msk(payload.get("given_at"))
        if en:
            return f"✅ Personal data processing consent given{f': {when}' if when else ''}."
        return f"✅ Согласие на обработку персональных данных получено{f': {when}' if when else ''}."

    if kind == "submission_status":
        status = payload.get("status", "")
        label = labels.get(status, status)

        isComment = payload.get("comment")
        comment = ""
        if isComment:
            comment = (
                f"Комментарий: {payload.get('comment')}"
                if not en
                else f"Comment: {payload.get('comment')}"
            )

        head = (
            f"Application #{payload.get('submission_id')} status has changed: {label}. {comment}"
            if en
            else f"Статус заявки #{payload.get('submission_id')} изменён: {label}. {comment}"
        )
        return head

    if kind == "submission_appointment":
        if en:
            return (
                f"Your meeting has been scheduled for {payload.get('date')} at "
                f"{payload.get('time')}. Location: {payload.get('location')}. "
                "Please bring your student ID. If you have any questions, send them "
                "in this chat. A university employee will reply during business hours."
            )
        return (
            f"Встреча назначена на {payload.get('date')} с {payload.get('time')}.\n\n"
            f"Место проведения: {payload.get('location')}.\n"
            "При себе необходимо иметь студенческий билет.\n\n"
            "Если у вас остались вопросы по встрече, напишите их в этот чат. "
            "Сотрудник университета ответит в рабочее время."
        )

    if kind == "staff_message":
        text = (payload.get("text") or "").strip()
        admin_name = (payload.get("admin_name") or "").strip()
        if admin_name and text:
            return f"{admin_name}: {text}"
        if admin_name:
            return admin_name
        return text

    if kind == "monitoring_changed":
        number = payload.get("request_number", "")
        new_status = payload.get("new_status", "")
        new_label = labels.get(new_status, new_status)
        return (
            f"Status update for request #{number}. Current status: {new_label}"
            if en
            else f"Обновление статуса по заявлению #{number}. Текущий статус: {new_label}"
        )

    if kind == "request_status_changed":
        return (
            "The status of your request has changed. Open the mini-app for details."
            if en
            else "Статус вашего заявления изменился. Откройте мини-приложение, чтобы посмотреть подробности."
        )

    if kind in {"rating_changed", "admission_rating_changed"}:
        return (
            "Your admission ranking has changed. Open the mini-app for details."
            if en
            else "Позиция вашей заявки в рейтинге на поступление изменилась. "
            "Откройте мини-приложение, чтобы посмотреть подробности."
        )
    if kind == "test_result":
        # Already split to fit MAX's message-length limit and fully rendered server-side
        # (form_tests.infrastructure.push_delivery) -- sent verbatim, no further formatting.
        return payload.get("text") or ""
    return json.dumps(payload, ensure_ascii=False)


_MIME_TO_UPLOAD_TYPE: dict[str, str] = {
    "image/": "image",
    "video/": "video",
    "audio/": "audio",
}


def _upload_type_for_mime(mime: str | None) -> str:
    if not mime:
        return "file"
    for prefix, t in _MIME_TO_UPLOAD_TYPE.items():
        if mime.startswith(prefix):
            return t
    return "file"


async def _resolve_attachment_url(url: str, is_public: bool = True) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = (
        settings.PUBLIC_API_URL if is_public else settings.BOT_INTERNAL_API_URL
    ).rstrip("/")
    return f"{base}{url}"


async def _download_attachment(
    client: httpx.AsyncClient, att: dict[str, Any]
) -> tuple[bytes, str, str] | None:
    url = att.get("url")
    if not url:
        return None
    abs_url = await _resolve_attachment_url(url, is_public=False)
    try:
        r = await client.get(abs_url, timeout=20.0)
        r.raise_for_status()
        name = att.get("name") or os.path.basename(abs_url.split("?")[0]) or "file"
        mime = (
            att.get("mime")
            or r.headers.get("content-type")
            or "application/octet-stream"
        )
        return r.content, name, mime
    except httpx.HTTPError as e:
        log.warning("attachment download failed (%s): %s", abs_url, e)
        return None


async def _send_with_attachments(
    bot: Any,
    user_id: int,
    text: str,
    attachments: list[dict[str, Any]],
) -> None:
    try:
        from maxapi.enums import UploadType
        from maxapi.types import InputMediaBuffer
    except ImportError:
        log.warning("maxapi attachments import failed — falling back to URLs in text")
        await _send_with_urls_fallback(bot, user_id, text, attachments)
        return

    upload_type_map = {
        "image": UploadType.IMAGE,
        "video": UploadType.VIDEO,
        "audio": UploadType.AUDIO,
        "file": UploadType.FILE,
    }

    async with httpx.AsyncClient() as client:
        uploaded: list[Any] = []
        unsent: list[dict[str, Any]] = []
        for att in attachments:
            blob = await _download_attachment(client, att)
            if blob is None:
                unsent.append(att)
                continue
            content, name, mime = blob
            ut_str = _upload_type_for_mime(mime)
            ut = upload_type_map.get(ut_str, UploadType.FILE)
            try:
                media = await bot.upload_media(
                    InputMediaBuffer(buffer=content, filename=name, type=ut)
                )
                uploaded.append(media)
            except Exception as e:  # noqa: BLE001
                log.warning("max upload_media failed for %s: %s", name, e)
                unsent.append(att)

        try:
            await bot.send_message(
                user_id=user_id,
                text=text or None,
                attachments=uploaded or None,
                format=Format.HTML if text else None,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("send_message with attachments failed: %s", e)
            await _send_with_urls_fallback(bot, user_id, text, attachments)
            return

        if unsent:
            await _send_with_urls_fallback(bot, user_id, "", unsent)


async def _send_with_urls_fallback(
    bot: Any,
    user_id: int,
    text: str,
    attachments: list[dict[str, Any]],
) -> None:
    """Если файлы не получилось залить в MAX — отправляем ссылки текстом."""
    lines = [text] if text else []
    for att in attachments:
        url = att.get("url")
        if not url:
            continue
        abs_url = await _resolve_attachment_url(url)
        name = att.get("name") or "файл"
        lines.append(f"📎 {name}\n{abs_url}")
    final = "\n\n".join(filter(None, lines))
    if not final:
        return
    try:
        await bot.send_message(user_id=user_id, text=final, format=Format.HTML)
    except Exception as e:
        log.warning("urls fallback send failed: %s", e)


async def consume(bot: Any) -> None:
    redis: Redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    log.info("push consumer: started")
    try:
        queue_keys = [PUSH_QUEUE_KEY]
        if settings.BOT_SLUG == "default":
            queue_keys.append(LEGACY_PUSH_QUEUE_KEY)
        while True:
            try:
                res = await redis.blpop(queue_keys, timeout=5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("push redis blpop failed: %s", e)
                await asyncio.sleep(2)
                continue
            if not res:
                continue
            _, raw = res
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                log.warning("push: bad json in queue: %s", raw[:200])
                continue

            kind = item.get("kind", "")
            payload = item.get("payload", {}) or {}
            text = _format_message(kind, payload, item.get("language_code"))
            external_user_id = item.get("external_user_id")
            if not external_user_id:
                log.warning("push: empty external_user_id, skipping: %s", item)
                continue
            try:
                user_id_int = int(external_user_id)
            except (TypeError, ValueError):
                log.warning("push: bad external_user_id=%r, skipping", external_user_id)
                continue

            attachments = (
                payload.get("attachments") if kind == "staff_message" else None
            )
            if attachments:
                await _send_with_attachments(bot, user_id_int, text, attachments)
            else:
                await _send(bot, user_id_int, text)
    except asyncio.CancelledError:
        log.info("push consumer: cancelled")
        raise
    finally:
        try:
            await redis.aclose()
        except Exception:
            pass


async def _send(bot: Any, user_id: int, text: str) -> None:
    if not text:
        return
    try:
        await bot.send_message(user_id=user_id, text=text, format=Format.HTML)
        log.info("push delivered to user_id=%s", user_id)
    except Exception as e:
        log.warning("push send to user_id=%s failed: %s", user_id, e)
