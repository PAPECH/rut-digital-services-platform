"""Per-test participation consent checkbox and admin-managed consent documents (Task 073)

Revision ID: 4f6b1c8e2a91
Revises: 8721935f5fb2
Create Date: 2026-09-21 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f6b1c8e2a91"
down_revision: str | None = "8721935f5fb2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "form_test_consent_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_form_test_consent_documents_bot_instance_id",
        "form_test_consent_documents",
        ["bot_instance_id"],
    )

    op.add_column(
        "form_test_drafts",
        sa.Column("consent_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "form_test_drafts",
        sa.Column(
            "consent_document_id",
            sa.Integer(),
            sa.ForeignKey("form_test_consent_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("form_test_drafts", sa.Column("consent_checkbox_text", sa.Text(), nullable=True))
    op.alter_column("form_test_drafts", "consent_enabled", server_default=None)

    op.add_column(
        "form_test_versions",
        sa.Column("consent_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("form_test_versions", sa.Column("consent_document_title", sa.String(300), nullable=True))
    op.add_column("form_test_versions", sa.Column("consent_document_body_html", sa.Text(), nullable=True))
    op.add_column("form_test_versions", sa.Column("consent_checkbox_text", sa.Text(), nullable=True))
    op.alter_column("form_test_versions", "consent_enabled", server_default=None)

    op.add_column(
        "form_test_attempts",
        sa.Column("consent_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "form_test_attempts", sa.Column("consent_accepted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.alter_column("form_test_attempts", "consent_accepted", server_default=None)


def downgrade() -> None:
    op.drop_column("form_test_attempts", "consent_accepted_at")
    op.drop_column("form_test_attempts", "consent_accepted")

    op.drop_column("form_test_versions", "consent_checkbox_text")
    op.drop_column("form_test_versions", "consent_document_body_html")
    op.drop_column("form_test_versions", "consent_document_title")
    op.drop_column("form_test_versions", "consent_enabled")

    op.drop_column("form_test_drafts", "consent_checkbox_text")
    op.drop_column("form_test_drafts", "consent_document_id")
    op.drop_column("form_test_drafts", "consent_enabled")

    op.drop_index("ix_form_test_consent_documents_bot_instance_id", table_name="form_test_consent_documents")
    op.drop_table("form_test_consent_documents")
