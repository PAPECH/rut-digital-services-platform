"""Seed RUT's socio-psychological testing (SPT) questionnaire into a bot as a published
`form_tests` test (Task 068's `build_rut_spt_schema`/`SqlAlchemyTestRepository.
seed_published_test` -- built then, never actually run against a real database until now; see
that repository method's own docstring: "not exposed over HTTP; called only from a CLI seed
script").

Usage:
    python -m app.cli.seed_rut_spt --bot-instance <slug-or-id>
    python -m app.cli.seed_rut_spt --bot-instance <slug-or-id> --slug my-slug --name "Custom name"
"""

from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import main as _app_main  # noqa: F401 -- registers the full SQLAlchemy mapper graph;
# `form_tests` models cross-reference `admins`/`users`/etc., and those in turn have their own
# cross-module `relationship()`s (e.g. `Admin.favorites -> StaffFavorite`), so importing just the
# directly-referenced model modules chases an open-ended chain -- importing the app once up front
# is the documented, known-good fix for a standalone script (see docs/development.md's admin
# session-minting recipe).
from ..db.session import SessionLocal
from ..modules.bot_instances.infrastructure.models import BotInstanceRecord
from ..modules.form_tests.infrastructure.repositories import SqlAlchemyTestRepository
from ..modules.form_tests.infrastructure.rut_spt_seed import build_rut_spt_schema

DEFAULT_SLUG = "rut-spt"
DEFAULT_NAME = "Социально-психологическое тестирование"


def _resolve_bot(session: Session, value: str) -> BotInstanceRecord | None:
    if value.isdigit():
        record = session.get(BotInstanceRecord, int(value))
    else:
        record = session.execute(
            select(BotInstanceRecord).where(BotInstanceRecord.slug == value.strip().lower())
        ).scalar_one_or_none()
    if record is None or record.deleted_at is not None:
        return None
    return record


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed RUT's SPT questionnaire as a published form_tests test",
    )
    parser.add_argument("--bot-instance", required=True, help="Target bot slug or numeric id")
    parser.add_argument("--slug", default=DEFAULT_SLUG, help=f"Test slug (default: {DEFAULT_SLUG!r})")
    parser.add_argument("--name", default=DEFAULT_NAME, help="Test display name")
    parser.add_argument(
        "--inactive", action="store_true", help="Publish but leave is_active=false (hidden from students)"
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        bot = _resolve_bot(db, args.bot_instance)
        if bot is None:
            raise SystemExit(f"Bot instance not found: {args.bot_instance!r}")
        bot_id, bot_slug = bot.id, bot.slug
        try:
            schema = build_rut_spt_schema()
            published = SqlAlchemyTestRepository(db).seed_published_test(
                bot_instance_id=bot_id,
                slug=args.slug,
                name=args.name,
                intro_text=None,
                schema=schema,
                is_active=not args.inactive,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        definition_id = published.definition.id
        version = published.version.version

    print(
        f"Seeded test #{definition_id} ({args.slug!r}) version {version} into "
        f"bot #{bot_id} ({bot_slug!r}) -- {len(schema['elements'])} elements, "
        f"{len(schema['result_scales'])} result scales, {len(schema['filters'])} filters"
    )


if __name__ == "__main__":
    main()
