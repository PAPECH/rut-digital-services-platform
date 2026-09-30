from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import settings

log = logging.getLogger(__name__)


class BackendClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.BOT_INTERNAL_API_URL,
            timeout=20.0,
            headers={
                "X-Bot-Token": settings.BOT_INTERNAL_API_TOKEN,
                "X-Bot-Runtime-Token": settings.BOT_RUNTIME_TOKEN,
                "X-Bot-Slug": settings.BOT_SLUG,
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def ingress_message(
        self,
        *,
        user_id: str,
        system: str,
        text: str | None,
        external_id: str | None = None,
        language_code: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "user_id": user_id,
            "system": system,
            "text": text,
            "external_id": external_id,
            "language_code": language_code,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "attachments": attachments,
        }
        try:
            r = await self._client.post("/api/messages/ingress", json=payload)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            log.warning("backend ingress failed: %s", e)
            return {}

    async def ai_callback(
        self,
        *,
        user_id: str,
        system: str,
        message_ref: str,
        action: str,
        document_ref: int | None = None,
    ) -> str | None:
        payload = {
            "user_id": user_id,
            "system": system,
            "message_ref": message_ref,
            "action": action,
            "document_ref": document_ref,
        }
        try:
            r = await self._client.post("/api/messages/ai/callback", json=payload)
            r.raise_for_status()
            data = r.json() or {}
            return data.get("text")
        except httpx.HTTPError as e:
            log.warning("ai_callback failed: %s", e)
            return None

    async def open_campaign_link(self, code: str, *, touch: str = "first") -> bool:
        try:
            r = await self._client.post(
                f"/api/campaign-links/{code}/open/bot", params={"touch": touch}
            )
            r.raise_for_status()
            return True
        except httpx.HTTPError as e:
            log.warning("open_campaign_link(%s, touch=%s) failed: %s", code, touch, e)
            return False

    async def consent_status(self, *, user_id: str, system: str) -> dict[str, Any]:
        return await self._consent_call("status", user_id=user_id, system=system)

    async def consent_accept(self, *, user_id: str, system: str) -> dict[str, Any]:
        return await self._consent_call("accept", user_id=user_id, system=system)

    async def consent_revoke(self, *, user_id: str, system: str) -> dict[str, Any]:
        return await self._consent_call("revoke", user_id=user_id, system=system)

    async def _consent_call(self, action: str, *, user_id: str, system: str) -> dict[str, Any]:
        try:
            r = await self._client.post(
                f"/api/consent/bot/{action}", json={"user_id": user_id, "system": system}
            )
            r.raise_for_status()
            return r.json() or {}
        except httpx.HTTPError as e:
            log.warning("consent %s failed: %s", action, e)
            return {}

    async def get_consent_notice(self, lang: str) -> str | None:
        try:
            r = await self._client.get(f"/api/consent/notice/{lang}")
            r.raise_for_status()
            data = r.json() or {}
            value = data.get("value")
            return value if isinstance(value, str) and value else None
        except httpx.HTTPError as e:
            log.warning("get_consent_notice(%s) failed: %s", lang, e)
            return None

    async def get_setting(self, key: str) -> str | None:
        try:
            r = await self._client.get(f"/api/settings/{key}")
            r.raise_for_status()
            data = r.json() or {}
            value = data.get("value")
            return value if isinstance(value, str) and value else None
        except httpx.HTTPError as e:
            log.warning("get_setting(%s) failed: %s", key, e)
            return None

    async def heartbeat(
        self,
        *,
        username: str | None,
        user_id: str | None,
        error_code: str | None = None,
    ) -> bool:
        try:
            response = await self._client.post(
                "/api/instances/runtime/heartbeat",
                json={
                    "username": username,
                    "user_id": user_id,
                    "version": settings.BOT_RUNTIME_VERSION,
                    "error_code": error_code,
                },
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            log.warning("runtime heartbeat failed: %s", exc)
            return False

    async def fetch_bytes(self, url: str) -> tuple[bytes, str] | None:
       
        try:
            
            r = await self._client.get(url)
            r.raise_for_status()
            return r.content, r.headers.get("content-type", "application/octet-stream")
        except httpx.HTTPError as e:
            log.warning("fetch_bytes(%s) failed: %s", url, e)
            return None
