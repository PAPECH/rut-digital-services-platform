"""Consent gate + cascading erasure (Task 064, supersedes Task 031)

Revision ID: 07b00e429bd2
Revises: a092acf6995a
Create Date: 2026-09-11 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "07b00e429bd2"
down_revision: str | None = "a092acf6995a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUM_NAME = "consent_event_type_enum"
_ENUM_VALUES = ("given", "revoked", "deletion_executed")

# Existing type, must not be recreated -- create_type=False, same convention as every other
# table that references it (see 20260101_0000_init.py).
system_enum = postgresql.ENUM("max", "beavers", name="system_enum", create_type=False)
consent_event_type_enum = postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME, create_type=False)


def upgrade() -> None:
    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {_ENUM_NAME} AS ENUM ({", ".join(f"'{v}'" for v in _ENUM_VALUES)});
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    op.create_table(
        "user_consents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_user_id", sa.String(64), nullable=False),
        sa.Column("system", system_enum, nullable=False),
        sa.Column("given_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletion_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_version", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("external_user_id", "system", name="uq_user_consents_external_system"),
    )
    op.create_index("ix_user_consents_user_id", "user_consents", ["user_id"])
    op.create_index("ix_user_consents_deletion_due_at", "user_consents", ["deletion_due_at"])

    op.create_table(
        "consent_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_consent_id",
            sa.Integer(),
            sa.ForeignKey("user_consents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", consent_event_type_enum, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=True),
    )
    op.create_index("ix_consent_events_user_consent_id", "consent_events", ["user_consent_id"])

    op.create_table(
        "consent_funnel_counters",
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("event_type", sa.String(32), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Grandfathering (Task 064): every pre-existing account is backfilled as already
    # consented, dated to its own `users.created_at` -- not a single shared migration
    # timestamp, which would read as fabricated consent rather than a grandfathering marker.
    # This is bookkeeping under a continued-service legal basis, not a claim that ст. 9
    # consent was obtained on that date (see docs/tasks/064, "Legal basis and nuances").
    # COALESCE is defensive, not decorative: this exact backfill produced one NULL
    # given_at against a real dev database despite users.created_at being NOT NULL at the
    # schema level -- root cause not conclusively pinned (the leading theory is a legacy
    # import path setting created_at through something other than the ORM's Python-side
    # default), but a grandfathering backfill must never silently leave `given_at` unset,
    # since that reads as "never consented" and defeats the entire point of grandfathering.
    op.execute(
        """
        WITH inserted AS (
            INSERT INTO user_consents (user_id, external_user_id, system, given_at, created_at, updated_at)
            SELECT id, user_id, system, COALESCE(created_at, now()), now(), now() FROM users
            RETURNING id, given_at
        )
        INSERT INTO consent_events (user_consent_id, event_type, occurred_at)
        SELECT id, 'given', given_at FROM inserted
        """
    )

    # Reverses a previous protective RESTRICT: this task is what authorizes deleting a
    # person's own submission row on erasure. Does not touch form_templates/form_versions
    # (guardrails.md's "preserve published form/content versions" protects those, not an
    # individual submission) -- see docs/tasks/064, Data and migration impact.
    op.drop_constraint("form_submissions_user_id_fkey", "form_submissions", type_="foreignkey")
    op.create_foreign_key(
        "fk_form_submissions_user_id",
        "form_submissions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_form_submissions_user_id", "form_submissions", type_="foreignkey")
    op.create_foreign_key(
        "form_submissions_user_id_fkey",
        "form_submissions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_table("consent_funnel_counters")
    op.drop_index("ix_consent_events_user_consent_id", table_name="consent_events")
    op.drop_table("consent_events")
    op.drop_index("ix_user_consents_deletion_due_at", table_name="user_consents")
    op.drop_index("ix_user_consents_user_id", table_name="user_consents")
    op.drop_table("user_consents")
    op.execute(f"DROP TYPE IF EXISTS {_ENUM_NAME}")
