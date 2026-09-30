from __future__ import annotations

import tarfile
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.attachment import Attachment
from ...modules.content.domain.blocks import (
    extract_card_image_attachment_id,
    extract_references,
)
from ...services.files import open_file, store_file
from .archive import ContentExportImportError


def collect_referenced_attachment_ids(categories_data: list[dict[str, Any]]) -> set[int]:
    ids: set[int] = set()
    for category in categories_data:
        for section in (category["draft"], category["published"]):
            if section is None:
                continue
            _, attachment_ids = extract_references(section["blocks"])
            ids.update(attachment_ids)
            card_image_id = extract_card_image_attachment_id(section["image_url"])
            if card_image_id is not None:
                ids.add(card_image_id)
    return ids


def export_attachments(
    session: Session,
    bot_id: int,
    categories_data: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[int, Path]]]:
    attachment_ids = collect_referenced_attachment_ids(categories_data)
    records = (
        session.execute(
            select(Attachment).where(
                Attachment.bot_instance_id == bot_id,
                Attachment.id.in_(attachment_ids),
            )
        )
        .scalars()
        .all()
        if attachment_ids
        else []
    )
    metadata = [
        {
            "id": record.id,
            "original_name": record.original_name,
            "mime": record.mime,
            "size_bytes": record.size_bytes,
        }
        for record in records
    ]
    files = [(record.id, Path(open_file(record.storage_path))) for record in records]
    return metadata, files


def import_attachments(
    session: Session,
    tar: tarfile.TarFile,
    manifest: dict[str, Any],
    bot_id: int,
    *,
    commit: bool,
    copied_paths: list[str],
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for meta in manifest["attachments"]:
        member_name = f"attachments/{meta['id']}.bin"
        try:
            tar.getmember(member_name)
        except KeyError as exc:
            raise ContentExportImportError(
                f"archive is missing attachment file: {member_name}"
            ) from exc

        if commit:
            extracted = tar.extractfile(member_name)
            assert extracted is not None
            storage_path, size_bytes = store_file(
                extracted.read(),
                original_name=meta["original_name"],
            )
            copied_paths.append(storage_path)
        else:
            storage_path, size_bytes = f"dry-run/{meta['id']}", meta["size_bytes"]

        record = Attachment(
            bot_instance_id=bot_id,
            storage_path=storage_path,
            original_name=meta["original_name"],
            mime=meta["mime"],
            size_bytes=size_bytes,
        )
        session.add(record)
        session.flush()
        mapping[int(meta["id"])] = record.id
    return mapping
