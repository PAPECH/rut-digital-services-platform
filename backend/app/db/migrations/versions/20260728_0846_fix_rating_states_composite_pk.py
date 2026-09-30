"""fix rating_states composite pk

Revision ID: 323686b772f8
Revises: 565303c8a1ee
Create Date: 2026-07-28 08:46:06.732466

"""

from typing import Sequence, Union

from alembic import op


revision: str = "323686b772f8"
down_revision: Union[str, None] = "565303c8a1ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("rating_states_pkey", "rating_states", type_="primary")
    op.create_primary_key(
        "rating_states_pkey",
        "rating_states",
        ["plan_id", "display_name", "competition_name"],
    )


def downgrade() -> None:
    op.drop_constraint("rating_states_pkey", "rating_states", type_="primary")
    op.create_primary_key(
        "rating_states_pkey",
        "rating_states",
        ["plan_id", "display_name"],
    )
