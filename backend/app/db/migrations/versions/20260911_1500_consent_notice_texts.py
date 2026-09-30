"""Platform-wide, admin-editable consent notice text (Task 064 follow-up)

Revision ID: de77815643d0
Revises: 07b00e429bd2
Create Date: 2026-09-11 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "de77815643d0"
down_revision: str | None = "07b00e429bd2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_POLICY_URL = (
    "https://rut-miit.ru/content/"
    "Положение%20о%20раб"
    "оте%20с%20персональ"
    "ными%20данными.pdf?id_wm=986949"
)

_DEFAULT_RU = (
    "Чтобы пользоваться ботом, подтвердите согласие на обработку персональных данных "
    f'в соответствии с <a href="{_POLICY_URL}">Положением о работе с персональными '
    "данными</a>."
)
_DEFAULT_EN = (
    "To use this bot, please confirm your consent to personal data processing under the "
    f'<a href="{_POLICY_URL}">Personal Data Processing Regulation</a>.'
)


def upgrade() -> None:
    op.create_table(
        "consent_notice_texts",
        sa.Column("key", sa.String(8), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # Seeded to match the bot's previous hardcoded text exactly, so behavior is unchanged
    # until a platform admin actually edits it via PUT /consent/admin/notice/{lang}.
    op.execute(
        sa.text("INSERT INTO consent_notice_texts (key, value) VALUES ('ru', :v)").bindparams(v=_DEFAULT_RU)
    )
    op.execute(
        sa.text("INSERT INTO consent_notice_texts (key, value) VALUES ('en', :v)").bindparams(v=_DEFAULT_EN)
    )


def downgrade() -> None:
    op.drop_table("consent_notice_texts")
