"""RUT schedule capability (demo slice of Task 043): institute/course/group hierarchy cache,
per-group lesson cache, and the seeded `default` bot installation.

Revision ID: 40ed7f5258ee
Revises: da7f87e5405a
Create Date: 2026-09-01 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "40ed7f5258ee"
down_revision: str | None = "da7f87e5405a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.create_table(
        "rut_schedule_institutes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id", sa.Integer(), sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "installation_id", sa.Integer(),
            sa.ForeignKey("capability_installations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("external_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("bot_instance_id", "external_id", name="uq_rut_schedule_institute"),
    )
    op.create_index(
        "ix_rut_schedule_institutes_bot_instance_id", "rut_schedule_institutes", ["bot_instance_id"]
    )
    op.create_index(
        "ix_rut_schedule_institutes_installation_id", "rut_schedule_institutes", ["installation_id"]
    )

    op.create_table(
        "rut_schedule_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id", sa.Integer(), sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "installation_id", sa.Integer(),
            sa.ForeignKey("capability_installations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("external_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("institute_external_id", sa.String(32), nullable=False),
        sa.Column("course_number", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("bot_instance_id", "external_id", name="uq_rut_schedule_group"),
    )
    op.create_index("ix_rut_schedule_groups_bot_instance_id", "rut_schedule_groups", ["bot_instance_id"])
    op.create_index("ix_rut_schedule_groups_installation_id", "rut_schedule_groups", ["installation_id"])
    op.create_index("ix_rut_schedule_groups_external_id", "rut_schedule_groups", ["external_id"])
    op.create_index(
        "ix_rut_schedule_groups_institute_external_id", "rut_schedule_groups", ["institute_external_id"]
    )

    op.create_table(
        "rut_schedule_lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id", sa.Integer(), sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "installation_id", sa.Integer(),
            sa.ForeignKey("capability_installations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("group_external_id", sa.String(32), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("week_parity", sa.Integer(), nullable=False),
        sa.Column("period_label", sa.String(32), nullable=False),
        sa.Column("start_time", sa.String(8), nullable=False),
        sa.Column("end_time", sa.String(8), nullable=False),
        sa.Column("lesson_kind", sa.String(120), nullable=False),
        sa.Column("discipline", sa.String(255), nullable=False),
        sa.Column("room", sa.String(500), nullable=True),
        sa.Column("teachers", sa.String(1000), nullable=True),
        sa.Column("combined_groups", sa.String(1000), nullable=True),
        sa.Column("periodicity_code", sa.Integer(), nullable=True),
        sa.UniqueConstraint(
            "bot_instance_id", "group_external_id", "weekday", "week_parity", "start_time", "discipline",
            name="uq_rut_schedule_lesson",
        ),
    )
    op.create_index("ix_rut_schedule_lessons_bot_instance_id", "rut_schedule_lessons", ["bot_instance_id"])
    op.create_index(
        "ix_rut_schedule_lessons_installation_id", "rut_schedule_lessons", ["installation_id"]
    )
    op.create_index(
        "ix_rut_schedule_lessons_group_external_id", "rut_schedule_lessons", ["group_external_id"]
    )

    op.create_table(
        "rut_schedule_group_sync",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id", sa.Integer(), sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "installation_id", sa.Integer(),
            sa.ForeignKey("capability_installations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("group_external_id", sa.String(32), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bot_instance_id", "group_external_id", name="uq_rut_schedule_group_sync"),
    )
    op.create_index(
        "ix_rut_schedule_group_sync_bot_instance_id", "rut_schedule_group_sync", ["bot_instance_id"]
    )
    op.create_index(
        "ix_rut_schedule_group_sync_installation_id", "rut_schedule_group_sync", ["installation_id"]
    )
    op.create_index(
        "ix_rut_schedule_group_sync_group_external_id", "rut_schedule_group_sync", ["group_external_id"]
    )

    op.execute(
        """
        INSERT INTO capability_installations (
            bot_instance_id, capability_key, is_enabled, "order", config, config_revision,
            last_health_status, created_at, updated_at
        )
        SELECT bot.id, 'rut_schedule', true, 1,
            jsonb_build_object(
                'provider', 'miit_timetable',
                'title', 'Расписание',
                'subtitle', 'Институт → курс → группа.',
                'group_cache_ttl_seconds', 900,
                'hierarchy_sync_interval_seconds', 21600
            ), 1, 'unknown', now(), now()
        FROM bot_instances AS bot WHERE bot.slug = 'default'
        ON CONFLICT (bot_instance_id, capability_key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM capability_installations WHERE capability_key = 'rut_schedule'")
    op.drop_table("rut_schedule_group_sync")
    op.drop_table("rut_schedule_lessons")
    op.drop_table("rut_schedule_groups")
    op.drop_table("rut_schedule_institutes")
