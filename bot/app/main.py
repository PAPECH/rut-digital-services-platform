from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from .backend import BackendClient
from .config import settings
from .push import consume as push_consume
from maxapi.enums.update import UpdateType
from maxapi.enums.parse_mode import ParseMode

log = logging.getLogger(__name__)

# OpenAppButton.payload value that tells the mini-app to boot straight into its in-app policy
# screen (read via getStartParam() in frontend-miniapp/src/max/bridge.ts) -- must match
# POLICY_START_PARAM in frontend-miniapp/src/features/consent/model/policyStartParam.ts.
# Deliberately not a plausible real campaign-link id, since the mini-app's generic
# start_param handling would otherwise try to report it as one.
_POLICY_START_PARAM = "__policy__"


def _default_start_text(lang: str) -> str:
    if lang == "ru":
        return (
            "Здравствуйте! Это бот РУТ МИИТ.\n"
            "Откройте мини-приложение, чтобы заказать справку или посмотреть статус заявки."
        )
    return (
        "Hello! This is the RUT MIIT bot.\n"
        "Open the mini-app to request a certificate or track your application."
    )


async def _get_start_text(backend: BackendClient, lang: str) -> str:
    key = "bot_start_message_ru" if lang == "ru" else "bot_start_message_en"
    text = await backend.get_setting(key)
    return text or _default_start_text(lang)


async def _run_mock() -> None:
    log.warning("BOT_MODE=mock — only push consumer is running (no MAX polling)")

    class _NoopBot:
        async def send_message(self, **kwargs: Any) -> None:
            log.info("[push mock] %s", kwargs)

    await push_consume(_NoopBot())


def _extract_attachments(body: Any) -> list[dict[str, Any]] | None:

    if body is None:
        return None
    raw = getattr(body, "attachments", None) or []
    out: list[dict[str, Any]] = []
    for att in raw:
        t = getattr(att, "type", None)
        t = t.value if hasattr(t, "value") else t
        item: dict[str, Any] = {"type": t}
        payload = getattr(att, "payload", None)

        if t == "image" and payload is not None:
            item["url"] = getattr(payload, "url", None)
            item["mime"] = "image/jpeg"
        elif t == "video":
            urls = getattr(att, "urls", None)
            # Берём mp4_720 если есть, иначе любой доступный.
            if urls is not None:
                for k in ("mp4_720", "mp4_480", "mp4_1080", "mp4_360", "mp4_240", "mp4_144", "hls"):
                    v = getattr(urls, k, None)
                    if v:
                        item["url"] = v
                        break
            item["mime"] = "video/mp4"
        elif t == "audio" and payload is not None:
            item["url"] = getattr(payload, "url", None)
            item["mime"] = "audio/mpeg"
            transcription = getattr(att, "transcription", None)
            if transcription:
                item["transcription"] = transcription
        elif t == "file":
            if payload is not None:
                item["url"] = getattr(payload, "url", None)
            item["name"] = getattr(att, "filename", None)
            size = getattr(att, "size", None)
            if size:
                item["size"] = size
            item["mime"] = "application/octet-stream"
        elif t == "sticker" and payload is not None:
            item["url"] = getattr(payload, "url", None)
            item["mime"] = "image/webp"
        else:
            continue

        if item.get("url"):
            out.append(item)
    return out or None


def _external_message_id(event: Any) -> str | None:
    message = getattr(event, "message", None)
    body = getattr(message, "body", None)
    for owner, names in (
        (body, ("mid", "message_id", "id")),
        (message, ("message_id", "id")),
        (event, ("update_id", "id")),
    ):
        for name in names:
            value = getattr(owner, name, None)
            if value is not None:
                return str(value)[:120]
    return None


def _is_adapter_command(text: str | None) -> bool:
    if not text:
        return False
    command = text.strip().split(maxsplit=1)[0].lower().split("@", 1)[0]
    return command in {"/start", "/miniapp", "/id", "/privacy"}


async def run_polling(bot, dp):
    # await bot.unsubscribe_webhook(url="https://rut.bot.wish-edu.ru/")
    await dp.start_polling(bot)

async def run_webhook(bot, dp):
    if not settings.BOT_WEBHOOK_SECRET:
        raise RuntimeError("BOT_WEBHOOK_SECRET is required when USE_WEBHOOK=true")
    webhook_url = settings.BOT_WEBHOOK_URL or settings.PUBLIC_WEBHOOK_BASE_URL
    await bot.subscribe_webhook(
        url=webhook_url,
        update_types=[UpdateType.MESSAGE_CREATED, UpdateType.MESSAGE_CALLBACK, UpdateType.BOT_STARTED],
        secret=settings.BOT_WEBHOOK_SECRET,
    )
    await dp.handle_webhook(
        bot,
        host=settings.BOT_WEBHOOK_HOST,
        port=settings.BOT_WEBHOOK_PORT,
        secret=settings.BOT_WEBHOOK_SECRET,
    )
    await bot.unsubscribe_webhook(url=webhook_url)

async def _run_live() -> None:
    try:
        from maxapi import Bot, Dispatcher
        from maxapi.types import (
            BotStarted,
            CallbackButton,
            Command,
            CommandStart,
            MessageCallback,
            MessageCreated,
            OpenAppButton,
        )
        from maxapi.types.updates.message_callback import MessageForCallback
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
    except ImportError as e:
        log.error("maxapi not installed (%s) — falling back to mock", e)
        await _run_mock()
        return

    backend = BackendClient()
    bot = Bot(settings.max_bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    bot_username: str | None = None
    max_bot_id: str | None = None
    startup_error_code: str | None = None
    try:
        me = await bot.get_me()
        bot_username = getattr(me, "username", None)
        raw_user_id = getattr(me, "user_id", None)
        max_bot_id = str(raw_user_id) if raw_user_id is not None else None
        log.info("MAX bot connected: @%s (id=%s)", bot_username or "?", max_bot_id or "?")
    except Exception as e:  # noqa: BLE001
        log.warning("get_me failed: %s", e)
        startup_error_code = "max_get_me_failed"

    async def heartbeat_loop() -> None:
        while True:
            await backend.heartbeat(
                username=bot_username,
                user_id=max_bot_id,
                error_code=startup_error_code,
            )
            await asyncio.sleep(settings.BOT_HEARTBEAT_SECONDS)

    def _build_miniapp_keyboard(lang: str) -> list[Any]:
        builder = InlineKeyboardBuilder()
        text = "Открыть мини-приложение" if lang == "ru" else "Open the mini-app"
        builder.row(
            OpenAppButton(
                text=text,
                web_app=bot.me.username,
                contact_id=bot.me.user_id,
            ),
        )
        return [builder.as_markup()]

    def _call_staff_label(lang: str) -> str:
        return "Позвать сотрудника" if lang == "ru" else "Contact support"

    def _build_candidates_keyboard(lang: str, message_ref: str, candidates: list[dict]) -> list[Any]:
        builder = InlineKeyboardBuilder()
        for c in candidates:
            label = str(c.get("topic") or "")[:120]
            payload = f"kbs:{message_ref}:{c.get('document_ref')}"
            builder.row(CallbackButton(text=label, payload=payload))
        builder.row(CallbackButton(text=_call_staff_label(lang), payload=f"kbc:{message_ref}"))
        return [builder.as_markup()]

    def _build_call_staff_keyboard(lang: str, message_ref: str) -> list[Any]:
        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text=_call_staff_label(lang), payload=f"kbc:{message_ref}"))
        return [builder.as_markup()]

    # --- Consent gate (Task 064) --------------------------------------------------------
    #
    # Mirrors the mini-app's gate 1:1: a person without active consent gets this instead of
    # the normal welcome/miniapp flow or any message processing, everywhere identity is
    # first established (bot_started, /start, on_message) -- and /privacy offers the
    # opposite action depending on current state.

    def _default_consent_notice(lang: str) -> str:
        """Fallback only -- used when the platform-admin-editable notice
        (GET /consent/notice/{lang}) is unset or unreachable. Kept in sync in spirit with
        the seed row the migration inserts, not literally the same string on purpose: an
        admin editing the live text shouldn't need to also touch bot source to change the
        fallback that only ever fires on an actual outage. Plain text, no embedded link --
        the policy document is always opened through the dedicated OpenAppButton next to this
        text (see _build_policy_button), not by parsing one out of admin-authored prose that
        may or may not contain it (mirrors the mini-app's ConsentGateScreen fix -- same
        reasoning, same bug class)."""
        if lang == "ru":
            return "Чтобы пользоваться ботом, подтвердите согласие на обработку персональных данных."
        return "To use this bot, please confirm your consent to personal data processing."

    async def _get_consent_notice(lang: str) -> str:
        value = await backend.get_consent_notice(lang)
        return value or _default_consent_notice(lang)

    def _format_given_at_msk(given_at_iso: str | None) -> str:
        if not given_at_iso:
            return ""
        try:
            dt = datetime.fromisoformat(given_at_iso.replace("Z", "+00:00"))
            return dt.astimezone(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M МСК")
        except ValueError:
            return ""

    def _consent_accepted_plate(lang: str, given_at_iso: str | None) -> str:
        when = _format_given_at_msk(given_at_iso)
        if lang == "ru":
            return f"✅ Согласие на обработку персональных данных получено{f': {when}' if when else ''}."
        return f"✅ Personal data processing consent given{f': {when}' if when else ''}."

    def _with_plate(base_text: str, plate: str) -> str:
        return f"{base_text}\n\n{plate}"

    async def _ungated_start_response(lang: str) -> tuple[str, list[Any]]:
        start_text = await _get_start_text(backend, lang)
        notice = await _get_consent_notice(lang)
        return _with_plate(start_text, notice), _build_consent_accept_keyboard(lang)

    def _consent_active_text(lang: str) -> str:
        if lang == "ru":
            return (
                "Согласие на обработку персональных данных действует. Отозвать согласие "
                "можно ниже — все данные, включая сообщения и заявки, будут удалены через "
                "10 рабочих дней, если согласие не будет подтверждено повторно."
            )
        return (
            "Your personal data processing consent is currently active. You can revoke it "
            "below -- all data, including messages and submissions, will be deleted in 10 "
            "business days unless you re-confirm consent."
        )

    def _consent_revoked_text(lang: str) -> str:
        if lang == "ru":
            return (
                "Согласие отозвано, бот недоступен. Аккаунт и все данные будут удалены "
                "через 10 рабочих дней, если вы не подтвердите согласие повторно."
            )
        return (
            "Consent has been revoked and the bot is unavailable. The account and all data "
            "will be deleted in 10 business days unless you re-confirm consent."
        )

    def _consent_accept_label(lang: str) -> str:
        return "Принимаю" if lang == "ru" else "Accept"

    def _policy_link_label(lang: str) -> str:
        return (
            "Положение о работе с персональными данными"
            if lang == "ru"
            else "Personal Data Processing Regulation"
        )

    def _build_policy_button(lang: str) -> OpenAppButton:
        # Opens the mini-app directly on its in-app policy screen (payload lands in the
        # mini-app's initData as start_param, read by getStartParam() in max/bridge.ts) --
        # not a LinkButton/external URL: MAX's own in-app "_blank" target didn't reliably
        # render a plain document (blank screen -- see docs/tasks/066, "Superseded designs"),
        # and per explicit product direction the policy should be a mini-app screen anyway,
        # not a browser tab, in either surface (chat button or mini-app button).
        return OpenAppButton(
            text=_policy_link_label(lang),
            web_app=bot.me.username,
            contact_id=bot.me.user_id,
            payload=_POLICY_START_PARAM,
        )

    def _build_consent_accept_keyboard(lang: str) -> list[Any]:
        builder = InlineKeyboardBuilder()
        # Separate row/button, not a link embedded in the message text -- same reasoning as
        # the mini-app's ConsentGateScreen: a dedicated button is guaranteed present, unlike
        # a link parsed out of admin-authored notice prose.
        builder.row(_build_policy_button(lang))
        builder.row(CallbackButton(text=_consent_accept_label(lang), payload="cns:accept"))
        return [builder.as_markup()]

    def _build_consent_revoke_keyboard(lang: str) -> list[Any]:
        builder = InlineKeyboardBuilder()
        builder.row(_build_policy_button(lang))
        label = "Отозвать согласие" if lang == "ru" else "Revoke consent"
        builder.row(CallbackButton(text=label, payload="cns:revoke"))
        return [builder.as_markup()]

    @dp.bot_started()
    async def on_bot_started(event: BotStarted) -> None:
        payload = getattr(event, "payload", None)
        if payload:
            try:
                await backend.open_campaign_link(payload, touch="first")
            except Exception as e:
                log.warning("campaign-link open report failed: %s", e)

        lang = getattr(event, "user_locale", "ru")
        raw_user_id = getattr(event.user, "user_id", None)
        if raw_user_id is None:
            log.warning("bot_started ignored: sender user_id is missing")
            return

        status = await backend.consent_status(user_id=str(raw_user_id), system="max")
        if not status.get("is_active"):
            # Not a separate message: the consent plate rides along at the bottom of the
            # normal start message (whose own text is the same DB-configured
            # bot_start_message_* as always), with only the accept button under it --
            # tapping it edits *this* message in place (see cns:accept below), it doesn't
            # send a second one.
            text, keyboard = await _ungated_start_response(lang)
            try:
                await event.bot.send_message(chat_id=event.chat_id, text=text, attachments=keyboard)
            except Exception as e:
                log.warning("on_bot_started consent prompt failed: %s", e)
            return

        text = await _get_start_text(backend, lang)
        try:
            await event.bot.send_message(
                chat_id=event.chat_id,
                text=text,
                attachments=_build_miniapp_keyboard(lang)
            )
        except Exception as e:
            log.warning("on_bot_started send failed: %s", e)

    @dp.message_created(CommandStart())
    async def on_start(event: MessageCreated, args: list[str] | None = None) -> None:
        # `CommandStart()`'s own `__call__` returns {"args": args} on a match (see
        # maxapi/filters/command.py) -- the dispatcher merges that dict into this handler's
        # kwargs by parameter name (maxapi/dispatcher.py's `_resolve_...`/`process_base_filters`),
        # the same mechanism `on_bot_started` relies on for `event.payload`. `args` is whatever
        # followed "/start " split on whitespace, e.g. ["ABC123"] for "/start ABC123" -- this is
        # the deep-link code MAX delivers as a plain text message (not a `bot_started` update) to
        # anyone who has already contacted the bot before, which this handler previously never
        # read (docs/tasks/074's reported bug).
        if args:
            code = args[0]
            try:
                await backend.open_campaign_link(code, touch="repeat")
            except Exception as e:
                log.warning("campaign-link repeat-open report failed: %s", e)

        lang = getattr(event, "user_locale", "ru")
        raw_user_id = getattr(event.from_user, "user_id", None)
        if raw_user_id is None:
            log.warning("/start ignored: sender user_id is missing")
            return

        status = await backend.consent_status(user_id=str(raw_user_id), system="max")
        if not status.get("is_active"):
            text, keyboard = await _ungated_start_response(lang)
            try:
                await event.message.answer(text=text, attachments=keyboard)
            except Exception as e:
                log.warning("/start consent prompt failed: %s", e)
            return

        text = await _get_start_text(backend, lang)
        try:
            await event.message.answer(
                text=text,
                attachments=_build_miniapp_keyboard(lang)
            )
        except Exception as e:
            log.warning("/start answer failed: %s", e)

    @dp.message_created(Command("privacy"))
    async def on_privacy(event: MessageCreated) -> None:
        lang = getattr(event, "user_locale", "ru")
        raw_user_id = getattr(event.from_user, "user_id", None)
        if raw_user_id is None:
            log.warning("/privacy ignored: sender user_id is missing")
            return

        status = await backend.consent_status(user_id=str(raw_user_id), system="max")
        try:
            if status.get("is_active"):
                await event.message.answer(
                    text=_consent_active_text(lang),
                    attachments=_build_consent_revoke_keyboard(lang),
                )
            else:
                await event.message.answer(
                    text=await _get_consent_notice(lang),
                    attachments=_build_consent_accept_keyboard(lang),
                )
        except Exception as e:
            log.warning("/privacy answer failed: %s", e)

    @dp.message_created(Command("miniapp"))
    async def on_miniapp(event: MessageCreated) -> None:
        lang = getattr(event, "user_locale", "ru")
        try:
            await event.message.answer(
                text=("Откройте мини-приложение:" if lang == "ru" else "Open the mini-app:"),
                attachments=_build_miniapp_keyboard(lang),
            )
        except Exception as e:
            log.warning("/miniapp answer failed: %s", e)

    @dp.message_created(Command("id"))
    async def on_id(event: MessageCreated) -> None:
        user_id = getattr(event.from_user, "user_id", None) or "—"
        try:
            await event.message.answer(
                text=(
                    f"Ваш MAX user_id: `{user_id}`\n"
                ),
            )
        except Exception as e:
            log.warning("/id answer failed: %s", e)

    @dp.message_created()
    async def on_message(event: MessageCreated) -> None:
        user = event.from_user
        body = getattr(event.message, "body", None)
        text = getattr(body, "text", None)
        if _is_adapter_command(text):
            return
        attachments = _extract_attachments(body)
        if not text and not attachments:
            return
        raw_user_id = getattr(user, "user_id", None)
        if raw_user_id is None:
            log.warning("MAX message ignored: sender user_id is missing")
            return
        lang_code = (
            getattr(user, "locale", None)
            or getattr(user, "language_code", None)
            or getattr(event, "user_locale", None)
        )
        result = await backend.ingress_message(
            user_id=str(raw_user_id),
            system="max",
            text=text,
            external_id=_external_message_id(event),
            language_code=lang_code,
            first_name=getattr(user, "first_name", None),
            last_name=getattr(user, "last_name", None),
            username=getattr(user, "username", None),
            attachments=attachments,
        )

        log.info(f'{raw_user_id=} {result=}')
        if not result:
            try:
                await event.message.answer(
                    text="Не удалось доставить сообщение специалисту. Попробуйте ещё раз позже."
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("ingress failure notification failed: %s", exc)
            return

        lang = "ru" if not lang_code or str(lang_code).lower().startswith("ru") else "en"

        if result.get("consent_required"):
            try:
                await event.message.answer(
                    text=await _get_consent_notice(lang),
                    attachments=_build_consent_accept_keyboard(lang),
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("consent prompt delivery failed: %s", exc)
            return

        if result.get("chat_disabled"):
            # Бот настроен не принимать свободный текст (BotSettings.chat) — backend
            # ничего не сохранил, показываем тот же редирект, что и по /start.
            redirect_text = await _get_start_text(backend, lang)
            try:
                await event.message.answer(
                    text=redirect_text, attachments=_build_miniapp_keyboard(lang)
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("chat-disabled redirect failed: %s", exc)
            return

        answer = result.get("answer")
        candidates = result.get("candidates")
        message_ref = result.get("message_ref")
        try:
            if answer:
                await event.message.answer(text=answer)
            elif candidates and message_ref:
                await event.message.answer(
                    text=result.get("candidates_prompt") or "",
                    attachments=_build_candidates_keyboard(lang, message_ref, candidates),
                )
            elif result.get("no_match_prompt") and message_ref:
                await event.message.answer(
                    text=result["no_match_prompt"],
                    attachments=_build_call_staff_keyboard(lang, message_ref),
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("AI answer delivery failed: %s", exc)

    @dp.message_callback()
    async def on_ai_callback(event: MessageCallback) -> None:
        raw_payload = event.callback.payload or ""
        raw_user_id = getattr(event.callback.user, "user_id", None)
        if raw_user_id is None:
            return
        lang = getattr(event, "user_locale", None) or "ru"
        lang = "ru" if not lang or str(lang).lower().startswith("ru") else "en"
        current_text = getattr(getattr(event.message, "body", None), "text", None)

        async def _resolve_callback(new_text: str | None, attachments: list[Any] | None = None) -> None:
            """Отвечает на callback, редактируя исходное сообщение с кнопками: меняет
            текст (если задан) и клавиатуру (по умолчанию attachments=[] — снимает её,
            кнопку больше нельзя нажать повторно; consent-accept передаёт свою — кнопку
            открытия мини-приложения). Заменяет собой event.answer(), второй ответ на тот
            же callback_id недопустим."""
            await event.bot.send_callback(
                callback_id=event.callback.callback_id,
                # format=HTML explicitly: MessageForCallback.format defaults to None
                # (plain text) regardless of the Bot's own parse_mode=ParseMode.HTML --
                # without this, an edited message loses HTML rendering, which matters now
                # that cns:accept edits start_text back in (it may contain an admin-typed
                # link) rather than only ever substituting link-free confirmation text.
                message=MessageForCallback(
                    text=new_text, attachments=attachments or [], format=ParseMode.HTML
                ),
            )

        try:
            if raw_payload.startswith("kbs:"):
                # Выбор кандидата — реальный ответ из базы знаний уходит отдельным
                # новым сообщением (он же попадает в историю на бэкенде); кнопки под
                # исходным сообщением-подсказкой снимаем, текст подсказки не трогаем.
                _, message_ref, document_ref = raw_payload.split(":", 2)
                text = await backend.ai_callback(
                    user_id=str(raw_user_id),
                    system="max",
                    message_ref=message_ref,
                    action="select",
                    document_ref=int(document_ref),
                )
                if text:
                    await _resolve_callback(current_text)
                    await event.message.answer(text=text)
                else:
                    await event.answer(
                        notification="Не удалось получить ответ" if lang == "ru" else "Could not fetch the answer"
                    )
            elif raw_payload.startswith("kbc:"):
                # Эскалация к сотруднику — подменяем текст исходного сообщения
                # подтверждением и снимаем кнопку, чтобы её нельзя было нажать снова.
                _, message_ref = raw_payload.split(":", 1)
                text = await backend.ai_callback(
                    user_id=str(raw_user_id),
                    system="max",
                    message_ref=message_ref,
                    action="call_staff",
                )
                if text:
                    await _resolve_callback(text)
                else:
                    await event.answer(
                        notification="Не удалось отправить запрос" if lang == "ru" else "Could not send the request"
                    )
            elif raw_payload == "cns:accept":
                status = await backend.consent_accept(user_id=str(raw_user_id), system="max")
                if status.get("is_active"):
                    # Edits *this* message in place -- the one already showing the start
                    # text + consent plate -- into start text + acceptance timestamp, and
                    # swaps the keyboard from "accept" to "open mini-app". No second
                    # message is sent.
                    start_text = await _get_start_text(backend, lang)
                    plate = _consent_accepted_plate(lang, status.get("given_at"))
                    await _resolve_callback(
                        _with_plate(start_text, plate), attachments=_build_miniapp_keyboard(lang)
                    )
                else:
                    await event.answer(
                        notification="Не удалось подтвердить согласие" if lang == "ru" else "Could not confirm consent"
                    )
            elif raw_payload == "cns:revoke":
                status = await backend.consent_revoke(user_id=str(raw_user_id), system="max")
                if not status.get("is_active"):
                    await _resolve_callback(_consent_revoked_text(lang))
                else:
                    await event.answer(
                        notification="Не удалось отозвать согласие" if lang == "ru" else "Could not revoke consent"
                    )
        except Exception as exc:  # noqa: BLE001
            log.warning("ai callback handling failed: %s", exc)

    push_task = asyncio.create_task(push_consume(bot))
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    try:
        if settings.USE_WEBHOOK:
            await run_webhook(bot, dp)
        else:
            await run_polling(bot, dp)
    finally:
        push_task.cancel()
        heartbeat_task.cancel()
        try:
            await push_task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.debug("push task ended with: %s", e)
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        await backend.aclose()



def main() -> None:
    logging.basicConfig(
        level=os.getenv("APP_LOG_LEVEL", settings.APP_LOG_LEVEL),
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
        stream=sys.stdout,
    )

    if settings.BOT_MODE == "live" and settings.max_bot_token:
        asyncio.run(_run_live())
    else:
        if settings.BOT_MODE == "live":
            log.warning("BOT_MODE=live, но токен из BOT_TOKEN_ENV_KEY пуст — переключаюсь в mock")
        asyncio.run(_run_mock())


if __name__ == "__main__":
    main()
