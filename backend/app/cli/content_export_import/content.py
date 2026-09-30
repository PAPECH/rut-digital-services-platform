from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...modules.capabilities.infrastructure.models import CapabilityInstallationRecord
from ...modules.content.domain.blocks import (
    extract_capability_references,
    extract_card_image_attachment_id,
    remap_attachment_and_category_references,
    remap_form_references,
    remap_test_references,
)
from ...modules.content.infrastructure.models import (
    ContentCategoryRecord,
    ContentDraftRecord,
    ContentVersionRecord,
)
from ...modules.content.infrastructure.repositories import _sync_attachment_references
from ...services.files import make_signed_url
from .archive import ContentExportImportError

HOME_CATEGORY_SLUG = "system-home-screen"


def export_categories(session: Session, bot_id: int) -> list[dict[str, Any]]:
    categories = session.execute(
        select(ContentCategoryRecord).where(ContentCategoryRecord.bot_instance_id == bot_id)
    ).scalars().all()
    data: list[dict[str, Any]] = []
    for category in categories:
        is_shortcut = category.capability_key is not None
        draft_data = None
        if not is_shortcut:
            draft = session.execute(
                select(ContentDraftRecord).where(ContentDraftRecord.category_id == category.id)
            ).scalar_one()
            draft_data = {
                "title": draft.title,
                "subtitle": draft.subtitle,
                "language": draft.language,
                "blocks": draft.blocks,
                "is_filled": draft.is_filled,
                "image_url": draft.image_url,
                "header_visible": draft.header_visible,
            }
        published = None
        if category.published_version_id is not None:
            version = session.get(ContentVersionRecord, category.published_version_id)
            assert version is not None
            published = {
                "title": version.title,
                "subtitle": version.subtitle,
                "language": version.language,
                "blocks": version.blocks,
                "is_filled": version.is_filled,
                "image_url": version.image_url,
                "header_visible": version.header_visible,
            }
        data.append(
            {
                "id": category.id,
                "slug": category.slug,
                "parent_id": category.parent_id,
                "icon": category.icon,
                "order": category.order,
                "is_active": category.is_active,
                "is_home": category.is_home,
                "capability_key": category.capability_key,
                "capability_view_key": category.capability_view_key,
                "shortcut_title": category.title,
                "shortcut_subtitle": category.subtitle,
                "shortcut_image_url": category.image_url,
                "draft": draft_data,
                "published": published,
            }
        )
    return data


def guard_target_empty(session: Session, bot_id: int) -> None:
    unexpected_category = session.execute(
        select(ContentCategoryRecord.id)
        .where(
            ContentCategoryRecord.bot_instance_id == bot_id,
            ContentCategoryRecord.slug != HOME_CATEGORY_SLUG,
        )
        .limit(1)
    ).scalar_one_or_none()
    if unexpected_category is not None:
        raise ContentExportImportError(
            "target bot already has content categories -- refusing to import content "
            "(this tool only performs a one-time initial import for that part)"
        )


def validate_capabilities(session: Session, bot_id: int, manifest: dict[str, Any]) -> None:
    all_blocks: list[dict[str, Any]] = []
    referenced_keys: set[str] = set()
    for category in manifest["categories"]:
        if category["capability_key"] is not None:
            referenced_keys.add(category["capability_key"])
            continue
        if category["draft"] is not None:
            all_blocks.extend(category["draft"]["blocks"])
        if category["published"]:
            all_blocks.extend(category["published"]["blocks"])
    referenced_keys |= {key for key, _view_key in extract_capability_references(all_blocks)}
    if not referenced_keys:
        return
    installed = set(
        session.execute(
            select(CapabilityInstallationRecord.capability_key).where(
                CapabilityInstallationRecord.bot_instance_id == bot_id,
                CapabilityInstallationRecord.capability_key.in_(referenced_keys),
                CapabilityInstallationRecord.is_enabled.is_(True),
            )
        ).scalars()
    )
    missing = referenced_keys - installed
    if missing:
        raise ContentExportImportError(
            "target bot is missing required, enabled capabilities: " + ", ".join(sorted(missing))
        )


def _existing_home_category(session: Session, bot_id: int) -> ContentCategoryRecord | None:
    return session.execute(
        select(ContentCategoryRecord).where(
            ContentCategoryRecord.bot_instance_id == bot_id,
            ContentCategoryRecord.slug == HOME_CATEGORY_SLUG,
        )
    ).scalar_one_or_none()


def remap_image_url(
    image_url: str | None,
    attachment_id_map: dict[int, int],
) -> str | None:
    if image_url is None:
        return None
    source_attachment_id = extract_card_image_attachment_id(image_url)
    if source_attachment_id is None:
        return image_url
    target_attachment_id = attachment_id_map.get(source_attachment_id)
    if target_attachment_id is None:
        raise ContentExportImportError(
            f"content references attachment {source_attachment_id}, which is not in the archive"
        )
    return make_signed_url(target_attachment_id, ttl_seconds=-1)


def import_categories(
    session: Session,
    manifest: dict[str, Any],
    bot_id: int,
    attachment_id_map: dict[int, int],
) -> dict[int, int]:
    existing_home = _existing_home_category(session, bot_id)
    remaining = {int(category["id"]): category for category in manifest["categories"]}
    category_id_map: dict[int, int] = {}
    while remaining:
        progressed = False
        for source_id, category in list(remaining.items()):
            parent_source = category["parent_id"]
            if parent_source is not None and int(parent_source) not in category_id_map:
                continue
            target_parent_id = (
                category_id_map[int(parent_source)] if parent_source is not None else None
            )
            if existing_home is not None and category["slug"] == HOME_CATEGORY_SLUG:
                record = existing_home
                record.parent_id = target_parent_id
                record.icon = category["icon"]
                record.order = category["order"]
                record.is_active = category["is_active"]
            else:
                record = ContentCategoryRecord(
                    bot_instance_id=bot_id,
                    slug=category["slug"],
                    parent_id=target_parent_id,
                    icon=category["icon"],
                    order=category["order"],
                    is_active=category["is_active"],
                    is_home=False,
                    capability_key=category["capability_key"],
                    capability_view_key=category["capability_view_key"],
                    title=category["shortcut_title"],
                    subtitle=category["shortcut_subtitle"],
                    image_url=remap_image_url(category["shortcut_image_url"], attachment_id_map),
                )
                session.add(record)
            session.flush()
            category_id_map[source_id] = record.id
            del remaining[source_id]
            progressed = True
        if not progressed:
            raise ContentExportImportError(
                "archive category tree has a cycle or a dangling parent reference"
            )
    return category_id_map


def _remap_blocks(
    blocks: list[dict[str, Any]],
    form_id_map: dict[int, int],
    test_id_map: dict[int, int],
    attachment_id_map: dict[int, int],
    category_id_map: dict[int, int],
) -> list[dict[str, Any]]:
    remapped = remap_form_references(blocks, form_id_map)
    remapped = remap_test_references(remapped, test_id_map)
    return remap_attachment_and_category_references(
        remapped,
        attachment_id_map,
        category_id_map,
    )


def import_content(
    session: Session,
    manifest: dict[str, Any],
    bot_id: int,
    category_id_map: dict[int, int],
    form_id_map: dict[int, int],
    test_id_map: dict[int, int],
    attachment_id_map: dict[int, int],
) -> None:
    for category in manifest["categories"]:
        if category["draft"] is None:
            continue
        target_category_id = category_id_map[int(category["id"])]
        draft = category["draft"]
        has_published = category["published"] is not None

        draft_blocks = _remap_blocks(
            draft["blocks"],
            form_id_map,
            test_id_map,
            attachment_id_map,
            category_id_map,
        )
        draft_image_url = remap_image_url(draft["image_url"], attachment_id_map)

        existing_draft = session.execute(
            select(ContentDraftRecord).where(
                ContentDraftRecord.category_id == target_category_id
            )
        ).scalar_one_or_none()
        if existing_draft is not None:
            existing_draft.title = draft["title"]
            existing_draft.subtitle = draft["subtitle"]
            existing_draft.language = draft["language"]
            existing_draft.blocks = draft_blocks
            existing_draft.revision += 1
            existing_draft.is_shared = False
            existing_draft.is_filled = draft["is_filled"]
            existing_draft.image_url = draft_image_url
            existing_draft.header_visible = draft["header_visible"]
            draft_record = existing_draft
        else:
            draft_record = ContentDraftRecord(
                category_id=target_category_id,
                title=draft["title"],
                subtitle=draft["subtitle"],
                language=draft["language"],
                blocks=draft_blocks,
                revision=1 if has_published else 0,
                is_shared=False,
                is_filled=draft["is_filled"],
                image_url=draft_image_url,
                header_visible=draft["header_visible"],
            )
            session.add(draft_record)
        session.flush()

        version_record: ContentVersionRecord | None = None
        if has_published:
            published = category["published"]
            published_blocks = _remap_blocks(
                published["blocks"],
                form_id_map,
                test_id_map,
                attachment_id_map,
                category_id_map,
            )
            next_version = (
                session.execute(
                    select(func.max(ContentVersionRecord.version)).where(
                        ContentVersionRecord.category_id == target_category_id
                    )
                ).scalar_one()
                or 0
            ) + 1
            version_record = ContentVersionRecord(
                category_id=target_category_id,
                version=next_version,
                source_revision=draft_record.revision,
                title=published["title"],
                subtitle=published["subtitle"],
                language=published["language"],
                blocks=published_blocks,
                published_at=datetime.now(tz=UTC),
                is_filled=published["is_filled"],
                image_url=remap_image_url(published["image_url"], attachment_id_map),
                header_visible=published["header_visible"],
            )
            session.add(version_record)
            session.flush()
            category_record = session.get(ContentCategoryRecord, target_category_id)
            assert category_record is not None
            category_record.published_version_id = version_record.id
            category_record.last_published_revision = draft_record.revision
            session.flush()

        _sync_attachment_references(
            session,
            bot_instance_id=bot_id,
            category_id=target_category_id,
            scope="draft",
            blocks=draft_record.blocks or [],
            image_url=draft_record.image_url,
        )
        if version_record is not None:
            _sync_attachment_references(
                session,
                bot_instance_id=bot_id,
                category_id=target_category_id,
                scope="published",
                blocks=version_record.blocks or [],
                image_url=version_record.image_url,
            )


def set_home_category(
    session: Session,
    manifest: dict[str, Any],
    category_id_map: dict[int, int],
) -> None:
    home_source_id = next(
        (int(category["id"]) for category in manifest["categories"] if category["is_home"]),
        None,
    )
    if home_source_id is None:
        return
    record = session.get(ContentCategoryRecord, category_id_map[home_source_id])
    assert record is not None
    record.is_home = True
    session.flush()
