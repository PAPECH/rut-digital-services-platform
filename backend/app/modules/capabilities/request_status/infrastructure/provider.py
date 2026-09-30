from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from .....core.config import settings
from ..domain.config import RequestStatusConfig
from ..domain.identity import normalize_request_number

_SHEETS_API_ROOT = "https://sheets.googleapis.com/v4"
_GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
_CONNECT_TIMEOUT_SECONDS = 3.05
_READ_TIMEOUT_SECONDS = 10
_MAX_RESPONSE_BYTES = 5_000_000
_MAX_ROWS = 100_000
_MAX_CELL_CHARACTERS = 2_000
_CIRCUIT_FAILURE_THRESHOLD = 3
_CIRCUIT_OPEN_SECONDS = 30
_circuit_lock = threading.Lock()
_circuit_state: dict[str, tuple[int, float]] = {}


def provider_error_code(error: BaseException) -> str:
    """Return an operator-safe diagnostic code without leaking provider details."""

    if isinstance(error, FileNotFoundError):
        return "credentials_file_missing"
    if isinstance(error, PermissionError):
        return "credentials_file_unreadable"
    if isinstance(error, OSError):
        return "provider_network_unavailable"
    detail = str(error)
    known = {
        "credential_ref_not_available": "credentials_not_configured",
        "provider_sdk_unavailable": "provider_sdk_unavailable",
        "provider_circuit_open": "provider_circuit_open",
        "provider_http_error": "provider_http_error",
    }
    if detail in known:
        return known[detail]
    if isinstance(error, ValueError):
        return "provider_response_invalid"
    return "provider_unavailable"


class _StreamingHttpResponse(Protocol):
    status_code: int

    def iter_content(self, *, chunk_size: int) -> Iterator[bytes]: ...

    def close(self) -> None: ...


class GoogleSheetsStatusProvider:
    def __init__(self, *, circuit_key: str | None = None) -> None:
        self._circuit_key = circuit_key

    def read_statuses(self, config: RequestStatusConfig) -> dict[str, str]:
        if config.credential_ref == "mock" or (
            config.credential_ref == "legacy_google_sheets" and settings.GOOGLE_SHEETS_MODE == "mock"
        ):
            source = json.loads(_read_bounded_file(Path(settings.GOOGLE_SHEETS_MOCK_FILE)))
            if isinstance(source, dict):
                if len(source) > _MAX_ROWS:
                    raise ValueError("Provider returned too many rows")
                if any(
                    len(str(key)) > _MAX_CELL_CHARACTERS or len(str(value)) > _MAX_CELL_CHARACTERS
                    for key, value in source.items()
                ):
                    raise ValueError("Provider returned an oversized cell")
                return {
                    normalize_request_number(str(key), config.normalization): str(value).strip()
                    for key, value in source.items()
                    if str(key).strip()
                }
            return parse_status_rows(
                source,
                number_column=config.request_number_column,
                status_column=config.status_column,
                normalization=config.normalization,
            )
        if config.credential_ref != "legacy_google_sheets":
            raise RuntimeError("credential_ref_not_available")
        if not settings.GOOGLE_SHEETS_CREDENTIALS_FILE:
            raise RuntimeError("credential_ref_not_available")
        self._ensure_circuit_closed()
        try:
            from google.auth.transport.requests import AuthorizedSession  # type: ignore
            from google.oauth2 import service_account  # type: ignore
            from requests.adapters import HTTPAdapter  # type: ignore
            from urllib3.util.retry import Retry  # type: ignore
        except ImportError as exc:
            raise RuntimeError("provider_sdk_unavailable") from exc
        try:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_SHEETS_CREDENTIALS_FILE,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            ).with_token_uri(_GOOGLE_TOKEN_URI)
            retry = Retry(
                total=2,
                connect=2,
                read=2,
                status=2,
                backoff_factor=0.25,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset({"GET"}),
                respect_retry_after_header=True,
                raise_on_status=False,
            )
            with AuthorizedSession(credentials) as session:
                session.mount(_SHEETS_API_ROOT, HTTPAdapter(max_retries=retry))
                encoded_range = quote(config.sheet_range, safe="")
                response = session.get(
                    f"{_SHEETS_API_ROOT}/spreadsheets/{config.spreadsheet_id}/values/{encoded_range}",
                    params={
                        "fields": "values",
                        "majorDimension": "ROWS",
                        "valueRenderOption": "FORMATTED_VALUE",
                    },
                    timeout=(_CONNECT_TIMEOUT_SECONDS, _READ_TIMEOUT_SECONDS),
                    allow_redirects=False,
                    stream=True,
                )
                values = _read_values_response(response)
            result = parse_status_rows(
                values,
                number_column=config.request_number_column,
                status_column=config.status_column,
                normalization=config.normalization,
            )
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result

    def _ensure_circuit_closed(self) -> None:
        if self._circuit_key is None:
            return
        with _circuit_lock:
            failures, opened_until = _circuit_state.get(self._circuit_key, (0, 0.0))
            if opened_until > time.monotonic():
                raise RuntimeError("provider_circuit_open")
            if opened_until:
                _circuit_state[self._circuit_key] = (failures, 0.0)

    def _record_failure(self) -> None:
        if self._circuit_key is None:
            return
        with _circuit_lock:
            failures, _ = _circuit_state.get(self._circuit_key, (0, 0.0))
            failures += 1
            opened_until = (
                time.monotonic() + _CIRCUIT_OPEN_SECONDS if failures >= _CIRCUIT_FAILURE_THRESHOLD else 0.0
            )
            _circuit_state[self._circuit_key] = (failures, opened_until)

    def _record_success(self) -> None:
        if self._circuit_key is None:
            return
        with _circuit_lock:
            _circuit_state.pop(self._circuit_key, None)


def _read_values_response(response: _StreamingHttpResponse) -> object:
    try:
        status_code = int(response.status_code)
        if not 200 <= status_code < 300:
            raise RuntimeError("provider_http_error")
        content = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            content.extend(chunk)
            if len(content) > _MAX_RESPONSE_BYTES:
                raise ValueError("Provider response exceeds the size limit")
        payload = json.loads(content.decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) - {"values"}:
            raise ValueError("Provider returned an invalid payload")
        return payload.get("values", [])
    finally:
        response.close()


def _read_bounded_file(path: Path) -> bytes:
    with path.open("rb") as source:
        content = source.read(_MAX_RESPONSE_BYTES + 1)
    if len(content) > _MAX_RESPONSE_BYTES:
        raise ValueError("Provider response exceeds the size limit")
    return content


def parse_status_rows(
    rows: object,
    *,
    number_column: int,
    status_column: int,
    normalization: str,
) -> dict[str, str]:
    if not isinstance(rows, list):
        raise ValueError("Provider returned invalid rows")
    if len(rows) > _MAX_ROWS:
        raise ValueError("Provider returned too many rows")
    result: dict[str, str] = {}
    required_index = max(number_column, status_column)
    for row in rows:
        if not isinstance(row, list) or len(row) <= required_index:
            continue
        raw_number = str(row[number_column]).strip()
        if not raw_number:
            continue
        if len(raw_number) > _MAX_CELL_CHARACTERS or len(str(row[status_column])) > _MAX_CELL_CHARACTERS:
            raise ValueError("Provider returned an oversized cell")
        normalized = normalize_request_number(raw_number, normalization)
        result[normalized] = str(row[status_column]).strip()
    return result
