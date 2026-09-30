"""One-off content fix: strip psychometric instrument names out of the RUT SPT test's block
titles (`questionnaire_title`/`section_title` elements) in every already-seeded copy of the
`rut-spt` test -- draft and every published version, across every bot instance that has one.

Only touches `elements[].label` for the 10 known title-element keys (BDI_TITLE, STAI_TITLE,
STAI_STATE_TITLE, STAI_TRAIT_TITLE, AMS_TITLE, SCU_TITLE, BAT_TITLE, BPNS_TITLE, SURPS_TITLE,
BPAQ_TITLE). Those elements are structural (`domain/elements.py`'s STRUCTURAL_TYPES) -- never
answerable, never referenced by a `scoring_key` or `result_scales` -- so this cannot touch any
already-recorded `form_test_attempts.answers`/`computed_results`. New labels are read straight off
`build_rut_spt_schema()`, i.e. the already-updated `backend/seed/form_tests/rut_spt_source.md`, so
this script can't drift from that source of truth.

`schema` is a plain `Mapped[dict]` JSONB column (not `MutableDict`-wrapped), so nested in-place
mutation wouldn't be picked up by the ORM's change tracking -- this reassigns the whole `schema`
dict on each row instead.

Usage:
    python -m app.cli.relabel_rut_spt_titles              # dry-run, prints the diff
    python -m app.cli.relabel_rut_spt_titles --commit      # persists it
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from .. import main as _app_main  # noqa: F401 -- registers the full SQLAlchemy mapper graph, see
# seed_rut_spt.py's identical import for why a standalone script needs this.
from ..db.session import SessionLocal
from ..modules.form_tests.infrastructure.models import TestDefinitionRecord, TestDraftRecord, TestVersionRecord
from ..modules.form_tests.infrastructure.rut_spt_seed import build_rut_spt_schema

SLUG = "rut-spt"


def _relabeled_elements(elements: list[dict], new_labels: dict[str, str]) -> tuple[list[dict], list[tuple[str, str, str]]]:
    changes: list[tuple[str, str, str]] = []
    updated = []
    for element in elements:
        new_label = new_labels.get(element.get("key", ""))
        if new_label is not None and element.get("label") != new_label:
            changes.append((element["key"], element["label"], new_label))
            updated.append({**element, "label": new_label})
        else:
            updated.append(element)
    return updated, changes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Relabel rut-spt's block titles in every already-seeded draft/version",
    )
    parser.add_argument("--commit", action="store_true", help="Persist changes; default is dry-run")
    args = parser.parse_args()

    new_labels = {
        element["key"]: element["label"]
        for element in build_rut_spt_schema()["elements"]
        if element["type"] in ("questionnaire_title", "section_title")
    }

    with SessionLocal() as db:
        definitions = db.execute(
            select(TestDefinitionRecord).where(TestDefinitionRecord.slug == SLUG)
        ).scalars().all()
        if not definitions:
            print(f"No form_tests rows with slug={SLUG!r} found.")
            return

        total_rows_changed = 0
        for definition in definitions:
            draft = db.execute(
                select(TestDraftRecord).where(TestDraftRecord.test_definition_id == definition.id)
            ).scalar_one_or_none()
            versions = db.execute(
                select(TestVersionRecord).where(TestVersionRecord.test_definition_id == definition.id)
            ).scalars().all()

            for label, record in [("draft", draft), *[("version", v) for v in versions]]:
                if record is None:
                    continue
                new_elements, changes = _relabeled_elements(record.schema["elements"], new_labels)
                if not changes:
                    continue
                total_rows_changed += 1
                version_suffix = f" v{record.version}" if isinstance(record, TestVersionRecord) else ""
                print(f"bot #{definition.bot_instance_id} test #{definition.id} {label}{version_suffix}:")
                for key, old, new in changes:
                    print(f"  {key}: {old!r} -> {new!r}")
                if args.commit:
                    record.schema = {**record.schema, "elements": new_elements}

        if not total_rows_changed:
            print("Nothing to change -- all rows already match the new labels.")
        elif args.commit:
            db.commit()
            print(f"Committed changes to {total_rows_changed} row(s).")
        else:
            print(f"Dry-run: {total_rows_changed} row(s) would change. Re-run with --commit to persist.")


if __name__ == "__main__":
    main()
