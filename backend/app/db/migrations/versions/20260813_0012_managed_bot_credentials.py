"""Track whether bot credentials come from deployment env or managed storage.

Revision ID: f24b8d0ac731
Revises: e13a7c94b621
Create Date: 2026-08-13 03:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f24b8d0ac731"
down_revision: str | None = "e13a7c94b621"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bot_runtimes", sa.Column("credential_source", sa.String(length=20)))
    op.execute(
        "UPDATE bot_runtimes SET credential_source = 'environment' "
        "WHERE credential_env_key IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("bot_runtimes", "credential_source")
