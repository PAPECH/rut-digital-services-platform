"""RUT schedule: make the crawled catalog/lessons/manual-sync-log platform-wide instead of scoped
per (bot_instance_id, installation_id) -- follow-up to Task 045. miit.ru's public schedule is the
same regardless of which bot asks; a second bot enabling `rut_schedule` was independently crawling
and caching the exact same site, wastefully and impolitely. Per-bot config (title/subtitle/
intervals/night_auto_sync_enabled) stays on `capability_installations`, untouched -- only the
crawled data (`rut_schedule_institutes`/`rut_schedule_groups`/`rut_schedule_lessons`/
`rut_schedule_group_sync`) drops its tenant scoping. `rut_schedule_manual_sync_requests` keeps
`bot_instance_id`/`installation_id` as informational context (which bot's panel triggered a run)
but they stop being a read filter -- no schema change needed there.

One-time consolidation before dropping the scoping columns: if more than one bot had already
independently crawled the same external_id (this platform's own dev DB briefly had exactly that --
a second bot enabled the capability before this migration shipped), keep only one row per natural
key so the new global unique constraints don't fail on a real duplicate.

Revision ID: 01d4fc1875d1
Revises: be95e962aecd
Create Date: 2026-09-02 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "01d4fc1875d1"
down_revision: str | None = "be95e962aecd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Consolidate any pre-existing per-scope duplicates (see module docstring) ---
    op.execute(
        """
        DELETE FROM rut_schedule_institutes a
        USING rut_schedule_institutes b
        WHERE a.external_id = b.external_id AND a.id < b.id
        """
    )
    op.execute(
        """
        DELETE FROM rut_schedule_groups a
        USING rut_schedule_groups b
        WHERE a.external_id = b.external_id AND a.id < b.id
        """
    )
    # Lessons have no unique constraint (by design -- a single time slot can legitimately hold two
    # subgroup lessons), so nothing here would fail without this step -- but leaving lesson rows
    # from more than one old scope for the same group would silently double up (or mix stale/fresh)
    # displayed lessons until that group happens to be re-synced. Keep only the lessons belonging
    # to whichever scope's group_sync row survives the dedup below (highest id = most recent).
    op.execute(
        """
        DELETE FROM rut_schedule_lessons l
        WHERE EXISTS (
            SELECT 1 FROM rut_schedule_group_sync gs WHERE gs.group_external_id = l.group_external_id
        )
        AND (l.bot_instance_id, l.installation_id) NOT IN (
            SELECT DISTINCT ON (gs.group_external_id) gs.bot_instance_id, gs.installation_id
            FROM rut_schedule_group_sync gs
            WHERE gs.group_external_id = l.group_external_id
            ORDER BY gs.group_external_id, gs.id DESC
        )
        """
    )
    op.execute(
        """
        DELETE FROM rut_schedule_group_sync a
        USING rut_schedule_group_sync b
        WHERE a.group_external_id = b.group_external_id AND a.id < b.id
        """
    )

    # --- Institutes ---
    op.drop_constraint("uq_rut_schedule_institute", "rut_schedule_institutes", type_="unique")
    op.drop_constraint(
        "rut_schedule_institutes_bot_instance_id_fkey", "rut_schedule_institutes", type_="foreignkey"
    )
    op.drop_constraint(
        "rut_schedule_institutes_installation_id_fkey", "rut_schedule_institutes", type_="foreignkey"
    )
    op.drop_column("rut_schedule_institutes", "bot_instance_id")
    op.drop_column("rut_schedule_institutes", "installation_id")
    op.create_unique_constraint(
        "uq_rut_schedule_institute_external_id", "rut_schedule_institutes", ["external_id"]
    )

    # --- Groups ---
    op.drop_constraint("uq_rut_schedule_group", "rut_schedule_groups", type_="unique")
    op.drop_constraint(
        "rut_schedule_groups_bot_instance_id_fkey", "rut_schedule_groups", type_="foreignkey"
    )
    op.drop_constraint(
        "rut_schedule_groups_installation_id_fkey", "rut_schedule_groups", type_="foreignkey"
    )
    op.drop_column("rut_schedule_groups", "bot_instance_id")
    op.drop_column("rut_schedule_groups", "installation_id")
    op.create_unique_constraint("uq_rut_schedule_group_external_id", "rut_schedule_groups", ["external_id"])

    # --- Lessons (no unique constraint before or after) ---
    op.drop_constraint(
        "rut_schedule_lessons_bot_instance_id_fkey", "rut_schedule_lessons", type_="foreignkey"
    )
    op.drop_constraint(
        "rut_schedule_lessons_installation_id_fkey", "rut_schedule_lessons", type_="foreignkey"
    )
    op.drop_column("rut_schedule_lessons", "bot_instance_id")
    op.drop_column("rut_schedule_lessons", "installation_id")

    # --- Group sync status ---
    op.drop_constraint("uq_rut_schedule_group_sync", "rut_schedule_group_sync", type_="unique")
    op.drop_constraint(
        "rut_schedule_group_sync_bot_instance_id_fkey", "rut_schedule_group_sync", type_="foreignkey"
    )
    op.drop_constraint(
        "rut_schedule_group_sync_installation_id_fkey", "rut_schedule_group_sync", type_="foreignkey"
    )
    op.drop_column("rut_schedule_group_sync", "bot_instance_id")
    op.drop_column("rut_schedule_group_sync", "installation_id")
    op.create_unique_constraint(
        "uq_rut_schedule_group_sync_group_external_id", "rut_schedule_group_sync", ["group_external_id"]
    )


def downgrade() -> None:
    # Guarded downgrade: re-adds the scoping columns nullable (there is no way to recover which
    # bot each now-global row "belonged" to, since that information was deliberately consolidated
    # away above) and re-creates the old FKs/unique constraints. A backfill onto a real bot is a
    # manual follow-up if this is ever actually rolled back, not something this migration can infer.
    op.add_column(
        "rut_schedule_institutes", sa.Column("bot_instance_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "rut_schedule_institutes", sa.Column("installation_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "rut_schedule_institutes_bot_instance_id_fkey",
        "rut_schedule_institutes",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "rut_schedule_institutes_installation_id_fkey",
        "rut_schedule_institutes",
        "capability_installations",
        ["installation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "uq_rut_schedule_institute_external_id", "rut_schedule_institutes", type_="unique"
    )
    op.create_unique_constraint(
        "uq_rut_schedule_institute", "rut_schedule_institutes", ["bot_instance_id", "external_id"]
    )

    op.add_column("rut_schedule_groups", sa.Column("bot_instance_id", sa.Integer(), nullable=True))
    op.add_column("rut_schedule_groups", sa.Column("installation_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "rut_schedule_groups_bot_instance_id_fkey",
        "rut_schedule_groups",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "rut_schedule_groups_installation_id_fkey",
        "rut_schedule_groups",
        "capability_installations",
        ["installation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_rut_schedule_group_external_id", "rut_schedule_groups", type_="unique")
    op.create_unique_constraint(
        "uq_rut_schedule_group", "rut_schedule_groups", ["bot_instance_id", "external_id"]
    )

    op.add_column("rut_schedule_lessons", sa.Column("bot_instance_id", sa.Integer(), nullable=True))
    op.add_column("rut_schedule_lessons", sa.Column("installation_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "rut_schedule_lessons_bot_instance_id_fkey",
        "rut_schedule_lessons",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "rut_schedule_lessons_installation_id_fkey",
        "rut_schedule_lessons",
        "capability_installations",
        ["installation_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column(
        "rut_schedule_group_sync", sa.Column("bot_instance_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "rut_schedule_group_sync", sa.Column("installation_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "rut_schedule_group_sync_bot_instance_id_fkey",
        "rut_schedule_group_sync",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "rut_schedule_group_sync_installation_id_fkey",
        "rut_schedule_group_sync",
        "capability_installations",
        ["installation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "uq_rut_schedule_group_sync_group_external_id", "rut_schedule_group_sync", type_="unique"
    )
    op.create_unique_constraint(
        "uq_rut_schedule_group_sync",
        "rut_schedule_group_sync",
        ["bot_instance_id", "group_external_id"],
    )
