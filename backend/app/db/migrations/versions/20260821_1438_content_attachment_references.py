"""Track current draft/published usage of admin-uploaded content attachments, so file deletion
can be gated against "is this still in the live published version" without scanning JSON at
delete time (Task 025).

Revision ID: 7a1c13d55e47
Revises: 8c25e0f4b913
Create Date: 2026-08-21 14:38:00
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a1c13d55e47"
down_revision: str | None = "8c25e0f4b913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_IMAGE_URL_ATTACHMENT_ID_RE = re.compile(r"/api/files/(\d+)(?:[/?]|$)")


def _file_list_attachment_ids(blocks: list | None) -> set[int]:
    """Mirrors `extract_references`'s file_list handling in
    `app.modules.content.domain.blocks` -- duplicated rather than imported so this migration
    keeps working unchanged if that module's shape ever moves."""
    ids: set[int] = set()
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "file_list":
            for item in block.get("items") or []:
                attachment_id = item.get("attachment_id") if isinstance(item, dict) else None
                if isinstance(attachment_id, int):
                    ids.add(attachment_id)
        elif block.get("type") == "tabs":
            for tab in block.get("tabs") or []:
                if isinstance(tab, dict):
                    ids |= _file_list_attachment_ids(tab.get("blocks"))
    return ids


def _card_image_attachment_id(image_url: str | None) -> int | None:
    if not image_url:
        return None
    match = _IMAGE_URL_ATTACHMENT_ID_RE.search(image_url)
    return int(match.group(1)) if match else None


def _reference_rows(
    *,
    bot_instance_id: int,
    category_id: int,
    scope: str,
    blocks: list | None,
    image_url: str | None,
    valid_attachment_ids: set[int],
) -> list[dict]:
    usages: set[tuple[int, str]] = {
        (attachment_id, "file_list_item")
        for attachment_id in _file_list_attachment_ids(blocks)
        if attachment_id in valid_attachment_ids
    }
    card_image_id = _card_image_attachment_id(image_url)
    if card_image_id is not None and card_image_id in valid_attachment_ids:
        usages.add((card_image_id, "card_image"))
    return [
        {
            "bot_instance_id": bot_instance_id,
            "attachment_id": attachment_id,
            "category_id": category_id,
            "scope": scope,
            "usage": usage,
        }
        for attachment_id, usage in usages
    ]


def upgrade() -> None:
    op.create_table(
        "content_attachment_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "attachment_id",
            sa.Integer(),
            sa.ForeignKey("attachments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("content_categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("usage", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("scope IN ('draft', 'published')", name="ck_content_attachment_reference_scope"),
        sa.CheckConstraint(
            "usage IN ('card_image', 'file_list_item')", name="ck_content_attachment_reference_usage"
        ),
        sa.UniqueConstraint(
            "category_id", "scope", "attachment_id", "usage", name="uq_content_attachment_reference"
        ),
    )
    op.create_index(
        "ix_content_attachment_references_bot_instance_id",
        "content_attachment_references",
        ["bot_instance_id"],
    )
    op.create_index(
        "ix_content_attachment_references_attachment_id",
        "content_attachment_references",
        ["attachment_id"],
    )
    op.create_index(
        "ix_content_attachment_references_category_id",
        "content_attachment_references",
        ["category_id"],
    )

    bind = op.get_bind()
    valid_attachment_ids = set(bind.execute(sa.text("SELECT id FROM attachments")).scalars().all())
    categories = bind.execute(
        sa.text("SELECT id, bot_instance_id, published_version_id FROM content_categories")
    ).mappings().all()
    drafts_by_category = {
        row["category_id"]: row
        for row in bind.execute(
            sa.text("SELECT category_id, blocks, image_url FROM content_drafts")
        ).mappings().all()
    }
    versions_by_id = {
        row["id"]: row
        for row in bind.execute(
            sa.text("SELECT id, blocks, image_url FROM content_versions")
        ).mappings().all()
    }

    rows: list[dict] = []
    for category in categories:
        draft = drafts_by_category.get(category["id"])
        if draft is not None:
            rows += _reference_rows(
                bot_instance_id=category["bot_instance_id"],
                category_id=category["id"],
                scope="draft",
                blocks=draft["blocks"],
                image_url=draft["image_url"],
                valid_attachment_ids=valid_attachment_ids,
            )
        if category["published_version_id"] is not None:
            version = versions_by_id.get(category["published_version_id"])
            if version is not None:
                rows += _reference_rows(
                    bot_instance_id=category["bot_instance_id"],
                    category_id=category["id"],
                    scope="published",
                    blocks=version["blocks"],
                    image_url=version["image_url"],
                    valid_attachment_ids=valid_attachment_ids,
                )

    if rows:
        table = sa.table(
            "content_attachment_references",
            sa.column("bot_instance_id", sa.Integer()),
            sa.column("attachment_id", sa.Integer()),
            sa.column("category_id", sa.Integer()),
            sa.column("scope", sa.String()),
            sa.column("usage", sa.String()),
        )
        op.bulk_insert(table, rows)


def downgrade() -> None:
    op.drop_table("content_attachment_references")
