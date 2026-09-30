"""Tenant-aware content CMS and analytics ownership.

Revision ID: c2f4a8d19b73
Revises: 8f41d2c9a601
Create Date: 2026-08-12 00:02:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2f4a8d19b73"
down_revision: str | None = "8f41d2c9a601"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    ]


def _add_tenant_ownership() -> None:
    op.add_column("attachments", sa.Column("bot_instance_id", sa.Integer()))
    op.add_column("user_actions", sa.Column("bot_instance_id", sa.Integer()))
    op.execute(
        """
        UPDATE attachments
        SET bot_instance_id = (SELECT id FROM bot_instances WHERE slug = 'default')
        WHERE bot_instance_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE user_actions
        SET bot_instance_id = (SELECT id FROM bot_instances WHERE slug = 'default')
        WHERE bot_instance_id IS NULL
        """
    )
    op.alter_column("attachments", "bot_instance_id", nullable=False)
    op.alter_column("user_actions", "bot_instance_id", nullable=False)
    op.create_foreign_key(
        "fk_attachments_bot_instance_id",
        "attachments",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_user_actions_bot_instance_id",
        "user_actions",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_attachments_bot_instance_id", "attachments", ["bot_instance_id"])
    op.create_index("ix_user_actions_bot_instance_id", "user_actions", ["bot_instance_id"])


def _create_content_tables() -> None:
    op.create_table(
        "content_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("icon", sa.String(80), nullable=False, server_default="folder"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("published_version_id", sa.Integer()),
        sa.Column("last_published_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        *_timestamps(),
        sa.UniqueConstraint("bot_instance_id", "slug", name="uq_content_category_bot_slug"),
    )
    op.create_index(
        "ix_content_categories_bot_instance_id",
        "content_categories",
        ["bot_instance_id"],
    )

    op.create_table(
        "content_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("content_categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("subtitle", sa.Text()),
        sa.Column("language", sa.String(16), nullable=False, server_default="ru"),
        sa.Column(
            "blocks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        *_timestamps(),
        sa.UniqueConstraint("category_id", name="uq_content_drafts_category_id"),
    )
    op.create_index("ix_content_drafts_category_id", "content_drafts", ["category_id"])

    op.create_table(
        "content_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("content_categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("subtitle", sa.Text()),
        sa.Column("language", sa.String(16), nullable=False, server_default="ru"),
        sa.Column("blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "category_id",
            "version",
            name="uq_content_version_category_number",
        ),
    )
    op.create_index("ix_content_versions_category_id", "content_versions", ["category_id"])
    op.create_foreign_key(
        "fk_content_category_published_version",
        "content_categories",
        "content_versions",
        ["published_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def _seed_default_content() -> None:
    op.execute(
        """
        INSERT INTO content_categories (
            bot_instance_id, slug, icon, "order", is_active,
            last_published_revision, created_at, updated_at
        )
        SELECT id, 'welcome', 'sparkles', 0, true, 1, now(), now()
        FROM bot_instances
        WHERE slug = 'default'
        ON CONFLICT (bot_instance_id, slug) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO content_drafts (
            category_id, title, subtitle, language, blocks, revision,
            created_at, updated_at
        )
        SELECT
            category.id,
            'Добро пожаловать',
            'Эта карточка создана через универсальный конструктор',
            'ru',
            jsonb_build_array(
                jsonb_build_object(
                    'id', 'welcome_heading',
                    'type', 'heading',
                    'text', 'Универсальная платформа готова',
                    'level', 2
                ),
                jsonb_build_object(
                    'id', 'welcome_text',
                    'type', 'paragraph',
                    'text', 'Содержимое этой страницы можно изменить и опубликовать в админке.'
                )
            ),
            1,
            now(),
            now()
        FROM content_categories AS category
        JOIN bot_instances AS bot ON bot.id = category.bot_instance_id
        WHERE bot.slug = 'default' AND category.slug = 'welcome'
        ON CONFLICT (category_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO content_versions (
            category_id, version, source_revision, title, subtitle,
            language, blocks, published_at
        )
        SELECT
            draft.category_id,
            1,
            draft.revision,
            draft.title,
            draft.subtitle,
            draft.language,
            draft.blocks,
            now()
        FROM content_drafts AS draft
        JOIN content_categories AS category ON category.id = draft.category_id
        JOIN bot_instances AS bot ON bot.id = category.bot_instance_id
        WHERE bot.slug = 'default' AND category.slug = 'welcome'
        ON CONFLICT (category_id, version) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE content_categories AS category
        SET
            published_version_id = version.id,
            last_published_revision = version.source_revision,
            updated_at = now()
        FROM content_versions AS version, bot_instances AS bot
        WHERE
            version.category_id = category.id
            AND version.version = 1
            AND bot.id = category.bot_instance_id
            AND bot.slug = 'default'
            AND category.slug = 'welcome'
        """
    )


def upgrade() -> None:
    _add_tenant_ownership()
    _create_content_tables()
    _seed_default_content()


def downgrade() -> None:
    # Production rollback requires exporting published content first: dropping these
    # tables is intentionally data-destructive and cannot recreate cross-bot ownership.
    op.drop_constraint(
        "fk_content_category_published_version",
        "content_categories",
        type_="foreignkey",
    )
    op.drop_table("content_versions")
    op.drop_table("content_drafts")
    op.drop_table("content_categories")

    op.drop_index("ix_user_actions_bot_instance_id", table_name="user_actions")
    op.drop_index("ix_attachments_bot_instance_id", table_name="attachments")
    op.drop_constraint(
        "fk_user_actions_bot_instance_id",
        "user_actions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_attachments_bot_instance_id",
        "attachments",
        type_="foreignkey",
    )
    op.drop_column("user_actions", "bot_instance_id")
    op.drop_column("attachments", "bot_instance_id")
