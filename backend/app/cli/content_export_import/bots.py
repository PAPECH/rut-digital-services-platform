from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...modules.bot_instances.infrastructure.models import BotInstanceRecord
from .archive import ImportAborted


def resolve_bot(session: Session, value: str) -> BotInstanceRecord | None:
    if value.isdigit():
        record = session.get(BotInstanceRecord, int(value))
    else:
        record = session.execute(
            select(BotInstanceRecord).where(
                BotInstanceRecord.slug == value.strip().lower(),
                BotInstanceRecord.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
    if record is None or record.deleted_at is not None:
        return None
    return record


def print_confirmation_banner(
    manifest: dict[str, Any],
    target_bot: BotInstanceRecord,
    selected_parts: tuple[str, ...],
) -> None:
    source = manifest["source_bot"]
    counts = manifest["counts"]
    print("Source bot (from archive):")
    print(f"  slug={source['slug']!r} name={source['name']!r} id={source['id']}")
    print("Target bot (resolved on this server):")
    print(f"  slug={target_bot.slug!r} name={target_bot.name!r} id={target_bot.id}")
    print("Selected parts: " + ", ".join(selected_parts))
    if "content" in selected_parts:
        print(
            f"  content: {counts['categories']} categories, "
            f"{counts['forms']} forms, {counts['attachments']} attachments"
        )
    if "tests" in selected_parts:
        print(
            f"  tests: {counts['tests']} tests, "
            f"{counts['consent_documents']} consent documents"
        )
    if "kb" in selected_parts:
        print(
            f"  kb: {counts['kb_faq']} FAQ, "
            f"{counts['kb_documents']} standalone documents"
        )


def confirm(
    manifest: dict[str, Any],
    target_bot: BotInstanceRecord,
    selected_parts: tuple[str, ...],
    *,
    assume_yes: bool,
) -> None:
    print_confirmation_banner(manifest, target_bot, selected_parts)
    if assume_yes:
        return
    answer = input(f'Import into "{target_bot.slug}" on this server? [y/N] ').strip().lower()
    if answer != "y":
        raise ImportAborted
