"""user extra fields: patronymic, phone_verified, ban_chat/forms/app + reasons; field_labels snapshot in submissions; admin name fields not needed (using join)

Revision ID: 0004_user_extra
Revises: 0003_audit
Create Date: 2026-05-20 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_user_extra"
down_revision: Union[str, None] = "0003_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # User: новые поля профиля и блокировок
    op.add_column("users", sa.Column("patronymic", sa.String(120), nullable=True))
    op.add_column(
        "users",
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column("ban_chat", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("ban_chat_reason", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("ban_forms", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("ban_forms_reason", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("ban_app", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("ban_app_reason", sa.Text(), nullable=True))

    # FormSubmission: snapshot названий полей на момент подачи (§ задача 5)
    op.add_column(
        "form_submissions",
        sa.Column(
            "field_labels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("form_submissions", "field_labels")
    op.drop_column("users", "ban_app_reason")
    op.drop_column("users", "ban_app")
    op.drop_column("users", "ban_forms_reason")
    op.drop_column("users", "ban_forms")
    op.drop_column("users", "ban_chat_reason")
    op.drop_column("users", "ban_chat")
    op.drop_column("users", "phone_verified")
    op.drop_column("users", "patronymic")
