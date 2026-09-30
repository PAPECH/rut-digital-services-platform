from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from aiohttp import web

from .config import settings

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessConfig:
    bot_instance_id: int
    slug: str
    credential_env_key: str
    mode: str
    runtime_token_configured: bool


@dataclass
class ManagedProcess:
    config: ProcessConfig
    process: asyncio.subprocess.Process
    webhook_port: int | None = None
    credential_fingerprint: str = ""


def runtime_token_env_key(slug: str) -> str:
    suffix = re.sub(r"[^A-Z0-9]+", "_", slug.upper()).strip("_")
    return f"BOT_RUNTIME_TOKEN_{suffix}"


def webhook_secret_env_key(slug: str) -> str:
    suffix = re.sub(r"[^A-Z0-9]+", "_", slug.upper()).strip("_")
    return f"BOT_WEBHOOK_SECRET_{suffix}"


def _managed_credentials() -> dict[str, str]:
    path = Path(settings.BOT_MANAGED_ENV_FILE)
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        log.error("cannot read managed bot credentials: %s", exc)
        return result
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        if key and isinstance(value, str):
            result[key] = value
    return result


def _credential_value(key: str, managed: dict[str, str]) -> str:
    return os.getenv(key, "") or managed.get(key, "")


def _credential_fingerprint(config: ProcessConfig) -> str:
    managed = _managed_credentials()
    values = [
        _credential_value(config.credential_env_key, managed),
        _credential_value(runtime_token_env_key(config.slug), managed),
        _credential_value(webhook_secret_env_key(config.slug), managed)
        if config.mode == "webhook"
        else "",
    ]
    return hashlib.sha256("\0".join(values).encode()).hexdigest()


def _parse_manifest(payload: Any) -> dict[str, ProcessConfig]:
    result: dict[str, ProcessConfig] = {}
    if not isinstance(payload, list):
        return result
    for item in payload:
        if not isinstance(item, dict):
            continue
        slug = item.get("slug")
        env_key = item.get("credential_env_key")
        if not isinstance(slug, str):
            continue
        if not isinstance(env_key, str) or not env_key:
            log.error("bot %s skipped: credential environment key is not configured", slug)
            continue
        result[slug] = ProcessConfig(
            bot_instance_id=int(item["bot_instance_id"]),
            slug=slug,
            credential_env_key=env_key,
            mode=str(item.get("mode") or "polling"),
            runtime_token_configured=bool(item.get("runtime_token_configured")),
        )
    return result


async def _fetch_manifest(client: httpx.AsyncClient) -> dict[str, ProcessConfig]:
    response = await client.get("/api/instances/runtime/processes")
    response.raise_for_status()
    return _parse_manifest(response.json())


async def _stop(managed: ManagedProcess) -> None:
    if managed.process.returncode is not None:
        return
    managed.process.terminate()
    try:
        await asyncio.wait_for(managed.process.wait(), timeout=15)
    except TimeoutError:
        managed.process.kill()
        await managed.process.wait()


def _allocate_webhook_port(children: dict[str, ManagedProcess]) -> int:
    used = {item.webhook_port for item in children.values() if item.webhook_port is not None}
    start = settings.BOT_WEBHOOK_CHILD_PORT_BASE
    for port in range(start, start + settings.BOT_WEBHOOK_CHILD_PORT_LIMIT):
        if port not in used:
            return port
    raise RuntimeError("webhook child port pool is exhausted")


async def _start(
    config: ProcessConfig,
    children: dict[str, ManagedProcess],
) -> ManagedProcess | None:
    managed_credentials = _managed_credentials()
    bot_token = _credential_value(config.credential_env_key, managed_credentials)
    if not bot_token:
        log.error("bot %s skipped: environment variable %s is empty", config.slug, config.credential_env_key)
        return None

    token_key = runtime_token_env_key(config.slug)
    runtime_token = _credential_value(token_key, managed_credentials)
    if not runtime_token and config.slug == settings.BOT_SLUG:
        runtime_token = settings.BOT_RUNTIME_TOKEN
    if config.runtime_token_configured and not runtime_token:
        log.error("bot %s skipped: issued runtime token must be set in %s", config.slug, token_key)
        return None

    webhook_port: int | None = None
    webhook_secret = ""
    webhook_url = ""
    if config.mode == "webhook":
        secret_key = webhook_secret_env_key(config.slug)
        webhook_secret = _credential_value(secret_key, managed_credentials)
        if not webhook_secret and config.slug == settings.BOT_SLUG:
            webhook_secret = settings.BOT_WEBHOOK_SECRET
        if not webhook_secret:
            log.error("bot %s skipped: webhook secret must be set in %s", config.slug, secret_key)
            return None
        webhook_port = _allocate_webhook_port(children)
        webhook_url = (
            f"{settings.PUBLIC_WEBHOOK_BASE_URL.rstrip('/')}/webhook/{config.slug}"
        )
    force_polling = (
        os.getenv("BOT_FORCE_POLLING", "false").strip().lower() == "true"
    )
    child_env = os.environ.copy()
    child_env[config.credential_env_key] = bot_token
    child_env.update(
        {
            "BOT_SLUG": config.slug,
            "BOT_TOKEN_ENV_KEY": config.credential_env_key,
            "BOT_RUNTIME_TOKEN": runtime_token,
            "USE_WEBHOOK": "false" if force_polling else "true" if config.mode == "webhook" else "false",
            "BOT_WEBHOOK_SECRET": webhook_secret,
            "BOT_WEBHOOK_URL": webhook_url,
            "BOT_WEBHOOK_HOST": "127.0.0.1",
            "BOT_WEBHOOK_PORT": str(webhook_port or settings.BOT_WEBHOOK_PORT)
        }
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "app.main",
        env=child_env,
    )
    log.info("bot %s started (pid=%s)", config.slug, process.pid)
    return ManagedProcess(
        config=config,
        process=process,
        webhook_port=webhook_port,
        credential_fingerprint=_credential_fingerprint(config),
    )


def _gateway_app(
    children: dict[str, ManagedProcess],
    proxy_client: httpx.AsyncClient,
) -> web.Application:
    async def proxy(request: web.Request) -> web.Response:
        slug = request.match_info["slug"]
        managed = children.get(slug)
        if (
            managed is None
            or managed.config.mode != "webhook"
            or managed.webhook_port is None
            or managed.process.returncode is not None
        ):
            return web.json_response({"error": "webhook bot unavailable"}, status=503)
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in {"host", "content-length", "connection", "transfer-encoding"}
        }
        target = f"http://127.0.0.1:{managed.webhook_port}/"
        if request.query_string:
            target = f"{target}?{request.query_string}"
        try:
            response = await proxy_client.request(
                request.method,
                target,
                content=await request.read(),
                headers=headers,
            )
        except httpx.HTTPError as exc:
            log.warning("webhook proxy failed for %s: %s", slug, exc)
            return web.json_response({"error": "webhook child unavailable"}, status=503)
        response_headers: dict[str, str] = {}
        content_type = response.headers.get("content-type")
        if content_type:
            response_headers["Content-Type"] = content_type
        return web.Response(
            status=response.status_code,
            body=response.content,
            headers=response_headers,
        )

    app = web.Application(client_max_size=20 * 1024 * 1024)
    app.router.add_route("*", "/webhook/{slug}", proxy)
    return app


async def run() -> None:
    children: dict[str, ManagedProcess] = {}
    headers = {"X-Bot-Token": settings.BOT_INTERNAL_API_TOKEN}
    async with httpx.AsyncClient(
        base_url=settings.BOT_INTERNAL_API_URL,
        headers=headers,
        timeout=20,
    ) as client, httpx.AsyncClient(timeout=30) as proxy_client:
        runner = web.AppRunner(_gateway_app(children, proxy_client))
        await runner.setup()
        site = web.TCPSite(
            runner,
            host=settings.BOT_WEBHOOK_GATEWAY_HOST,
            port=settings.BOT_WEBHOOK_GATEWAY_PORT,
        )
        await site.start()
        log.info(
            "webhook gateway listening on %s:%s",
            settings.BOT_WEBHOOK_GATEWAY_HOST,
            settings.BOT_WEBHOOK_GATEWAY_PORT,
        )
        try:
            while True:
                try:
                    desired = await _fetch_manifest(client)
                except httpx.HTTPError as exc:
                    log.error("cannot load bot process manifest: %s", exc)
                    await asyncio.sleep(settings.BOT_SUPERVISOR_INTERVAL_SECONDS)
                    continue

                for slug, managed in list(children.items()):
                    replacement = desired.get(slug)
                    credentials_unchanged = bool(
                        replacement
                        and managed.credential_fingerprint
                        == _credential_fingerprint(replacement)
                    )
                    if (
                        managed.process.returncode is None
                        and replacement == managed.config
                        and credentials_unchanged
                    ):
                        continue
                    if managed.process.returncode is None:
                        log.info("bot %s configuration removed or changed; stopping", slug)
                        await _stop(managed)
                    else:
                        log.warning("bot %s exited with code %s; restarting", slug, managed.process.returncode)
                    children.pop(slug, None)

                for slug, config in desired.items():
                    if slug in children:
                        continue
                    managed = await _start(config, children)
                    if managed is not None:
                        children[slug] = managed

                await asyncio.sleep(settings.BOT_SUPERVISOR_INTERVAL_SECONDS)
        finally:
            await asyncio.gather(*(_stop(item) for item in children.values()), return_exceptions=True)
            await runner.cleanup()


def main() -> None:
    logging.basicConfig(
        level=os.getenv("APP_LOG_LEVEL", settings.APP_LOG_LEVEL),
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
    )
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
