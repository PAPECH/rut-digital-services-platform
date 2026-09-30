from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...modules.forms.domain.fields import clone_fields
from ...modules.forms.infrastructure.models import (
    FormDefinitionRecord,
    FormDraftRecord,
    FormVersionRecord,
)
from .archive import ContentExportImportError


def export_forms(session: Session, bot_id: int) -> list[dict[str, Any]]:
    forms = session.execute(
        select(FormDefinitionRecord).where(FormDefinitionRecord.bot_instance_id == bot_id)
    ).scalars().all()
    data: list[dict[str, Any]] = []
    for form in forms:
        draft = session.execute(
            select(FormDraftRecord).where(FormDraftRecord.form_definition_id == form.id)
        ).scalar_one()
        published = None
        if form.published_version_id is not None:
            version = session.get(FormVersionRecord, form.published_version_id)
            assert version is not None
            published = {
                "name": version.name,
                "description": version.description,
                "reply_on_accept": version.reply_on_accept,
                "fields": deepcopy(version.fields),
            }
        data.append(
            {
                "id": form.id,
                "slug": form.slug,
                "is_archived": form.is_archived,
                "show_in_catalog": form.show_in_catalog,
                "order": form.order,
                "draft": {
                    "name": draft.name,
                    "description": draft.description,
                    "reply_on_accept": draft.reply_on_accept,
                    "fields": deepcopy(draft.fields),
                },
                "published": published,
            }
        )
    return data


def target_has_forms(session: Session, bot_id: int) -> bool:
    return (
        session.execute(
            select(FormDefinitionRecord.id)
            .where(FormDefinitionRecord.bot_instance_id == bot_id)
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def import_forms(
    session: Session,
    manifest: dict[str, Any],
    bot_id: int,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for form in manifest["forms"]:
        draft = form["draft"]
        has_published = form["published"] is not None
        definition = FormDefinitionRecord(
            bot_instance_id=bot_id,
            slug=form["slug"],
            is_archived=form["is_archived"],
            show_in_catalog=form["show_in_catalog"],
            order=form["order"],
            last_published_revision=0 if has_published else -1,
            name=draft["name"],
            description=draft["description"],
            is_active=False,
            reply_on_accept=draft["reply_on_accept"],
        )
        session.add(definition)
        session.flush()

        draft_record = FormDraftRecord(
            form_definition_id=definition.id,
            name=draft["name"],
            description=draft["description"],
            reply_on_accept=draft["reply_on_accept"],
            fields=clone_fields(draft["fields"]),
            revision=1 if has_published else 0,
            is_shared=False,
        )
        session.add(draft_record)
        session.flush()

        if has_published:
            published = form["published"]
            version = FormVersionRecord(
                form_definition_id=definition.id,
                version=1,
                source_revision=0,
                name=published["name"],
                description=published["description"],
                reply_on_accept=published["reply_on_accept"],
                fields=clone_fields(published["fields"]),
                published_at=datetime.now(tz=UTC),
            )
            session.add(version)
            session.flush()
            definition.published_version_id = version.id
            session.flush()

        mapping[int(form["id"])] = definition.id
    return mapping


def require_no_forms(session: Session, bot_id: int) -> None:
    if target_has_forms(session, bot_id):
        raise ContentExportImportError(
            "target bot already has forms -- refusing to import content "
            "(this tool only performs a one-time initial import for that part)"
        )
