"""Файлы / вложения (§8.3, §16 ТЗ).

- POST /api/files — загрузка multipart (для админов и студентов).
- GET /api/files/{id} — отдача файла по подписанному URL (без авторизации, проверяется sig).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Literal

from ...core.errors import bad_request, not_found
from ...db.session import get_db
from ...models.attachment import Attachment
from ...modules.bot_instances.domain.entities import BotInstance
from ...modules.forms.domain.fields import MAX_FILE_SIZE_BYTES
from ...modules.maintenance.presentation.dependencies import enforce_user_write_available
from ...modules.tenancy.presentation.dependencies import require_tenant_access
from ...services.files import make_signed_url, open_file, store_file, verify_signed
from ...services.rate_limit import rate_limit
from ...shared.images import UPLOAD_IMAGE_PRESETS, UnsupportedImageError, optimize_image_bytes
from ..deps import CurrentPrincipal, get_current_principal

router = APIRouter()

# 30 загрузок / мин — для админа bulk-загрузка вложений, для студента — анти-флуд.
_upload_rl = rate_limit("file_upload", limit=30, window_seconds=60)


@router.post("", dependencies=[Depends(_upload_rl)])
async def upload(
    file: UploadFile = File(...),
    purpose: str | None = Form(default=None),
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(get_current_principal),
    bot: BotInstance = Depends(require_tenant_access),
    _: None = Depends(enforce_user_write_available),
) -> dict:
    """Загрузить файл. Доступно любой авторизованной роли (студент/сотрудник/админ).

    `purpose` — необязательный именованный пресет обработки (сейчас только `category_icon`:
    ресайз до 128x128 + конвертация в WEBP, Task 065). Без него файл сохраняется как есть.

    Возвращает: { id, url, name, mime, size_bytes }
    """
    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise bad_request("Файл превышает лимит 20 МБ", code="file_too_large")
    original_name = file.filename or "file"
    mime = file.content_type or "application/octet-stream"

    preset = None
    if purpose is not None:
        preset = UPLOAD_IMAGE_PRESETS.get(purpose)
        if preset is None:
            raise bad_request("Неизвестное назначение загрузки", code="unknown_upload_purpose")
        try:
            content = optimize_image_bytes(
                content,
                max_width=preset.max_width,
                max_height=preset.max_height,
                quality=preset.quality,
            )
        except UnsupportedImageError as exc:
            raise bad_request("Файл не является изображением", code="file_type") from exc
        original_name = f"{Path(original_name).stem}.webp"
        mime = "image/webp"

    storage_path, size_bytes = store_file(content, original_name=original_name)

    att = Attachment(
        bot_instance_id=bot.id,
        storage_path=storage_path,
        original_name=original_name,
        mime=mime,
        size_bytes=size_bytes,
        uploaded_by_admin_id=p.admin_id,
        uploaded_by_user_id=p.user_id,
    )
    db.add(att)
    db.commit()
    db.refresh(att)

    url = make_signed_url(att.id, ttl_seconds=-1) if preset and preset.permanent_url else make_signed_url(att.id)
    return {
        "id": att.id,
        "url": url,
        "name": att.original_name,
        "mime": att.mime,
        "size_bytes": att.size_bytes,
    }


@router.get("/{file_id}")
def download(
    file_id: int,
    exp: int = Query(...),
    sig: str = Query(...),
    action: Literal["view", "download"] = Query('download'),
    db: Session = Depends(get_db),
) -> Response:
    verify_signed(file_id, exp, sig)
    att = db.get(Attachment, file_id)
    if att is None:
        raise not_found("Файл не найден")
    abs_path = open_file(att.storage_path)
    return FileResponse(
        path=str(abs_path),
        media_type=att.mime,
        filename=att.original_name,
        # RFC 6266 only defines "inline" and "attachment" -- "download" is not a valid
        # Content-Disposition type. Every URL made by make_signed_url() defaults to action=download
        # and therefore used to send this invalid value on every response, category tile images
        # (<img src=...>) included even though they're never meant to trigger a download at all.
        content_disposition_type="inline" if action == 'view' else 'attachment',
        # Each upload gets its own random storage path (see store_file) and is never overwritten
        # in place, so the bytes at this exact signed URL never change -- safe to tell the
        # browser not to re-fetch or even revalidate it, which is what makes image preloading
        # (frontend-miniapp's preloadImages()) actually pay off on the next navigation instead of
        # downloading the same file again.
        headers={"Cache-Control": "public, max-age=2592000, immutable"},
    )
