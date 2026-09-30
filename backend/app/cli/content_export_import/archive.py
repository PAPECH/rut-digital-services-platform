from __future__ import annotations

import io
import json
import tarfile
from collections.abc import Iterable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FORMAT_VERSION = 3
LEGACY_FORMAT_VERSION = 2
MANIFEST_NAME = "manifest.json"
PART_ORDER = ("content", "tests", "kb")
KNOWN_PARTS = frozenset(PART_ORDER)


class ContentExportImportError(RuntimeError):
    """A validation or guard failure that must stop the run before any row is written."""


class ImportAborted(RuntimeError):
    """The operator declined the confirmation prompt."""


def normalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Normalize a supported archive into the v3 in-memory contract.

    Version 2 archives contained only content. Unknown versions fail before any DB access.
    """

    version = manifest.get("format_version")
    if version not in {LEGACY_FORMAT_VERSION, FORMAT_VERSION}:
        raise ContentExportImportError(f"unsupported archive format_version: {version!r}")

    normalized = deepcopy(manifest)
    if version == LEGACY_FORMAT_VERSION:
        normalized["format_version"] = FORMAT_VERSION
        normalized["parts"] = ["content"]
        normalized.setdefault("tests", [])
        normalized.setdefault("consent_documents", [])
        normalized.setdefault("kb_faq", [])
        normalized.setdefault("kb_documents", [])
        counts = normalized.setdefault("counts", {})
        for key in ("tests", "consent_documents", "kb_faq", "kb_documents"):
            counts.setdefault(key, 0)

    parts = normalized.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ContentExportImportError("archive has no parts")
    unknown = set(parts) - KNOWN_PARTS
    if unknown:
        raise ContentExportImportError(
            "archive contains unknown part(s): " + ", ".join(sorted(unknown))
        )
    return normalized


def parse_only_parts(value: str | None, available_parts: Iterable[str]) -> tuple[str, ...]:
    available = set(available_parts)
    if value is None:
        return tuple(part for part in PART_ORDER if part in available)

    requested = {part.strip() for part in value.split(",") if part.strip()}
    if not requested:
        raise ContentExportImportError("--only must name at least one part")
    unknown = requested - KNOWN_PARTS
    if unknown:
        raise ContentExportImportError("unknown --only part(s): " + ", ".join(sorted(unknown)))
    missing = requested - available
    if missing:
        raise ContentExportImportError(
            "archive does not contain part(s): " + ", ".join(sorted(missing))
        )
    return tuple(part for part in PART_ORDER if part in requested)


def read_manifest(tar: tarfile.TarFile) -> dict[str, Any]:
    try:
        manifest_member = tar.extractfile(MANIFEST_NAME)
    except KeyError as exc:
        raise ContentExportImportError("archive is missing manifest.json") from exc
    if manifest_member is None:
        raise ContentExportImportError("archive is missing manifest.json")
    try:
        raw = json.loads(manifest_member.read())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ContentExportImportError("archive manifest.json is invalid") from exc
    if not isinstance(raw, dict):
        raise ContentExportImportError("archive manifest.json must be an object")
    return normalize_manifest(raw)


def write_archive(
    out_path: Path,
    manifest: dict[str, Any],
    attachment_files: Iterable[tuple[int, Path]],
) -> None:
    with tarfile.open(out_path, "w:gz") as tar:
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        info = tarfile.TarInfo(name=MANIFEST_NAME)
        info.size = len(manifest_bytes)
        info.mtime = int(datetime.now(tz=UTC).timestamp())
        tar.addfile(info, io.BytesIO(manifest_bytes))
        for attachment_id, file_path in attachment_files:
            tar.add(str(file_path), arcname=f"attachments/{attachment_id}.bin")
