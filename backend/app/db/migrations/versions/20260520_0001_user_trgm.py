"""pg_trgm extension + GIN-indices on User text fields for ILIKE search

Revision ID: 0005_user_trgm
Revises: 0004_user_extra
Create Date: 2026-05-20 01:00:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0005_user_trgm"
down_revision: Union[str, None] = "0004_user_extra"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Поля User, по которым админка ищет пользователей через ILIKE '%q%'.
# Без GIN+gin_trgm_ops каждый ILIKE — seq scan по всей таблице.
_TRGM_INDEXES: list[tuple[str, str]] = [
    ("ix_users_first_name_trgm", "first_name"),
    ("ix_users_last_name_trgm", "last_name"),
    ("ix_users_patronymic_trgm", "patronymic"),
    ("ix_users_username_trgm", "username"),
    ("ix_users_phone_trgm", "phone"),
    ("ix_users_email_trgm", "email"),
    ("ix_users_study_group_trgm", "study_group"),
    ("ix_users_user_id_trgm", "user_id"),
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for index_name, column in _TRGM_INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {index_name} " f"ON users USING gin ({column} gin_trgm_ops)")


def downgrade() -> None:
    for index_name, _ in _TRGM_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
    # pg_trgm не сносим — может использоваться другими таблицами.
