from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core.config import settings

log = logging.getLogger(__name__)


class GoogleSheetsError(Exception):
    pass


def read_status_map() -> dict[str, str]:
    if settings.GOOGLE_SHEETS_MODE == "mock":
        return _read_mock()
    return _read_live()


def _read_mock() -> dict[str, str]:
    path = Path(settings.GOOGLE_SHEETS_MOCK_FILE)
    if not path.exists():
        log.warning("google_sheets mock file not found: %s", path)
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise GoogleSheetsError(f"Невалидный JSON в моке: {e}") from e

    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items() if k}

    if isinstance(data, list):
        out: dict[str, str] = {}
        for row in data:
            if not row:
                continue
            num = str(row[0]) if len(row) >= 1 else ""
            stat = str(row[1]) if len(row) >= 2 else ""
            if num:
                out[num] = stat
        return out

    raise GoogleSheetsError("Неожиданный формат мок-файла")


def _read_live() -> dict[str, str]:
    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except ImportError as e:
        raise GoogleSheetsError("Не установлены google API библиотеки") from e

    if not settings.GOOGLE_SHEETS_ID:
        raise GoogleSheetsError("GOOGLE_SHEETS_ID не задан")
    if not settings.GOOGLE_SHEETS_CREDENTIALS_FILE:
        raise GoogleSheetsError("GOOGLE_SHEETS_CREDENTIALS_FILE не задан")

    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SHEETS_CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    resp = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=settings.GOOGLE_SHEETS_ID, range=settings.GOOGLE_SHEETS_RANGE)
        .execute()
    )
    values = resp.get("values", [])
    out: dict[str, str] = {}
    for row in values:
        if not row:
            continue
        num = str(row[0]).strip() if len(row) >= 1 else ""
        stat = str(row[1]).strip() if len(row) >= 2 else ""
        if num:
            out[num] = stat
    return out
