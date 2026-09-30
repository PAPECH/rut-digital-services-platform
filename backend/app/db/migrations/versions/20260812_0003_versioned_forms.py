"""Versioned tenant-aware forms and immutable submission snapshots.

Revision ID: f7d9b3a64c12
Revises: c2f4a8d19b73
Create Date: 2026-08-12 00:03:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7d9b3a64c12"
down_revision: str | None = "c2f4a8d19b73"
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


def _add_form_identity_columns() -> None:
    op.add_column("form_templates", sa.Column("slug", sa.String(80)))
    op.add_column(
        "form_templates",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "form_templates",
        sa.Column("last_published_revision", sa.Integer(), nullable=False, server_default="-1"),
    )
    op.execute(
        """
        UPDATE form_templates
        SET slug = 'form-' || id::text
        WHERE slug IS NULL
        """
    )
    op.alter_column("form_templates", "slug", nullable=False)
    op.create_unique_constraint(
        "uq_form_template_bot_slug",
        "form_templates",
        ["bot_instance_id", "slug"],
    )


def _create_version_tables() -> None:
    op.create_table(
        "form_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "form_definition_id",
            sa.Integer(),
            sa.ForeignKey("form_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("reply_on_accept", sa.Text()),
        sa.Column(
            "fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        *_timestamps(),
        sa.UniqueConstraint("form_definition_id", name="uq_form_draft_definition_id"),
    )
    op.create_index("ix_form_drafts_form_definition_id", "form_drafts", ["form_definition_id"])

    op.create_table(
        "form_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "form_definition_id",
            sa.Integer(),
            sa.ForeignKey("form_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("reply_on_accept", sa.Text()),
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "form_definition_id",
            "version",
            name="uq_form_version_definition_number",
        ),
    )
    op.create_index(
        "ix_form_versions_form_definition_id",
        "form_versions",
        ["form_definition_id"],
    )

    op.add_column("form_templates", sa.Column("published_version_id", sa.Integer()))
    op.create_foreign_key(
        "fk_form_template_published_version",
        "form_templates",
        "form_versions",
        ["published_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def _backfill_legacy_forms() -> None:
    op.execute(
        """
        INSERT INTO form_drafts (
            form_definition_id, name, description, reply_on_accept,
            fields, revision, updated_by, created_at, updated_at
        )
        SELECT
            template.id,
            template.name,
            template.description,
            template.reply_on_accept,
            COALESCE(
                jsonb_agg(
                    jsonb_strip_nulls(
                        CASE field.type::text
                            WHEN 'string' THEN jsonb_build_object(
                                'key', field.id::text,
                                'type', 'short_text',
                                'label', field.label,
                                'help_text', NULL,
                                'required', field.is_required,
                                'active', field.is_active,
                                'profile_key', field.profile_key,
                                'placeholder', NULL,
                                'default', field.default_value,
                                'min_length', 0,
                                'max_length', 20000,
                                'pattern', field.regexp
                            )
                            WHEN 'number' THEN jsonb_build_object(
                                'key', field.id::text,
                                'type', 'number',
                                'label', field.label,
                                'help_text', NULL,
                                'required', field.is_required,
                                'active', field.is_active,
                                'profile_key', field.profile_key,
                                'placeholder', NULL,
                                'default', CASE
                                    WHEN field.default_value ~ '^-?[0-9]+([.][0-9]+)?$'
                                    THEN to_jsonb(field.default_value::numeric)
                                    ELSE NULL
                                END,
                                'min', CASE
                                    WHEN field.min_value ~ '^-?[0-9]+([.][0-9]+)?$'
                                    THEN to_jsonb(field.min_value::numeric)
                                    ELSE NULL
                                END,
                                'max', CASE
                                    WHEN field.max_value ~ '^-?[0-9]+([.][0-9]+)?$'
                                    THEN to_jsonb(field.max_value::numeric)
                                    ELSE NULL
                                END,
                                'step', 1
                            )
                            WHEN 'date' THEN jsonb_build_object(
                                'key', field.id::text,
                                'type', 'date',
                                'label', field.label,
                                'help_text', NULL,
                                'required', field.is_required,
                                'active', field.is_active,
                                'profile_key', field.profile_key,
                                'default', CASE
                                    WHEN field.default_value ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                                    THEN field.default_value
                                    ELSE NULL
                                END,
                                'min', CASE
                                    WHEN field.min_value ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                                    THEN field.min_value
                                    ELSE NULL
                                END,
                                'max', CASE
                                    WHEN field.max_value ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                                    THEN field.max_value
                                    ELSE NULL
                                END
                            )
                            WHEN 'checkbox' THEN jsonb_build_object(
                                'key', field.id::text,
                                'type', 'checkbox',
                                'label', field.label,
                                'help_text', NULL,
                                'required', field.is_required,
                                'active', field.is_active,
                                'profile_key', field.profile_key,
                                'default', lower(COALESCE(field.default_value, 'false'))
                                    IN ('true', '1', 'yes', 'on', 'да')
                            )
                        END
                    ) ORDER BY field."order", field.id
                ) FILTER (WHERE field.id IS NOT NULL),
                '[]'::jsonb
            ),
            0,
            template.created_by,
            template.created_at,
            template.updated_at
        FROM form_templates AS template
        LEFT JOIN form_fields AS field ON field.form_template_id = template.id
        GROUP BY template.id
        ON CONFLICT (form_definition_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO form_versions (
            form_definition_id, version, source_revision, name, description,
            reply_on_accept, fields, published_by, published_at
        )
        SELECT
            draft.form_definition_id,
            1,
            draft.revision,
            draft.name,
            draft.description,
            draft.reply_on_accept,
            draft.fields,
            draft.updated_by,
            COALESCE(template.updated_at, now())
        FROM form_drafts AS draft
        JOIN form_templates AS template ON template.id = draft.form_definition_id
        ON CONFLICT (form_definition_id, version) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE form_templates AS template
        SET
            published_version_id = version.id,
            last_published_revision = version.source_revision,
            updated_at = template.updated_at
        FROM form_versions AS version
        WHERE
            version.form_definition_id = template.id
            AND version.version = 1
        """
    )


def _version_submissions() -> None:
    op.add_column("form_submissions", sa.Column("form_version_id", sa.Integer()))
    op.add_column(
        "form_submissions",
        sa.Column(
            "form_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "form_submissions",
        sa.Column(
            "profile_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.execute(
        """
        UPDATE form_submissions AS submission
        SET
            form_version_id = version.id,
            form_snapshot = jsonb_strip_nulls(jsonb_build_object(
                'form_id', template.id,
                'form_version_id', version.id,
                'version', version.version,
                'name', version.name,
                'description', version.description,
                'reply_on_accept', version.reply_on_accept,
                'fields', version.fields
            )),
            profile_snapshot = jsonb_strip_nulls(jsonb_build_object(
                'first_name', users.first_name,
                'last_name', users.last_name,
                'patronymic', users.patronymic,
                'phone', users.phone,
                'phone_verified', users.phone_verified,
                'email', users.email,
                'birth_date', users.birth_date,
                'job_title', users.job_title,
                'structural_unit', users.structural_unit,
                'shared_data', COALESCE(users.shared_data, '{}'::jsonb)
                    - 'external_user_id' - 'max_user_id' - 'max_id' - 'provider' - 'user_id'
            ))
        FROM form_templates AS template
        JOIN form_versions AS version
            ON version.id = template.published_version_id
        CROSS JOIN users
        WHERE template.id = submission.form_template_id
          AND users.id = submission.user_id
        """
    )
    op.alter_column("form_submissions", "form_version_id", nullable=False)
    op.create_foreign_key(
        "fk_form_submissions_form_version_id",
        "form_submissions",
        "form_versions",
        ["form_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_form_submissions_form_version_id",
        "form_submissions",
        ["form_version_id"],
    )


def upgrade() -> None:
    _add_form_identity_columns()
    _create_version_tables()
    _backfill_legacy_forms()
    _version_submissions()


def downgrade() -> None:
    # Legacy form tables and fields are retained. Forms created after this migration may
    # require export before downgrade because their typed JSON fields have no legacy rows.
    op.drop_index("ix_form_submissions_form_version_id", table_name="form_submissions")
    op.drop_constraint(
        "fk_form_submissions_form_version_id",
        "form_submissions",
        type_="foreignkey",
    )
    op.drop_column("form_submissions", "profile_snapshot")
    op.drop_column("form_submissions", "form_snapshot")
    op.drop_column("form_submissions", "form_version_id")

    op.drop_constraint(
        "fk_form_template_published_version",
        "form_templates",
        type_="foreignkey",
    )
    op.drop_column("form_templates", "published_version_id")
    op.drop_table("form_versions")
    op.drop_table("form_drafts")

    op.drop_constraint("uq_form_template_bot_slug", "form_templates", type_="unique")
    op.drop_column("form_templates", "last_published_revision")
    op.drop_column("form_templates", "is_archived")
    op.drop_column("form_templates", "slug")
