"""One-off content fix: apply the RUT SPT source file's updated question/option numbering
("N." -> "N)", and the Beck Depression Inventory's answer options renumbered from a 0-based to a
1-based scale) to every already-seeded copy of the `rut-spt` test -- draft and every published
version, across every bot instance that has one.

Only rewrites `elements[].label` and `elements[].options[].label`, matching options by their
stable `value` (e.g. "opt1", "opt2" -- unaffected by the relabeling) rather than position or old
text. `options[].score`/`value` and every other field are left untouched, so this cannot affect
scoring or already-recorded `form_test_attempts.answers`. New labels are read straight off
`build_rut_spt_schema()`, i.e. the already-updated `backend/seed/form_tests/rut_spt_source.md`, so
this script can't drift from that source of truth.

`schema` is a plain `Mapped[dict]` JSONB column (not `MutableDict`-wrapped), so this reassigns the
whole `schema` dict on each row rather than mutating it in place.

Usage:
    python -m app.cli.renumber_rut_spt_labels              # dry-run, prints the diff
    python -m app.cli.renumber_rut_spt_labels --commit      # persists it
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


def _relabeled_elements(
    elements: list[dict], new_by_key: dict[str, dict]
) -> tuple[list[dict], list[tuple[str, str, str]]]:
    changes: list[tuple[str, str, str]] = []
    updated = []
    for element in elements:
        new_element = new_by_key.get(element.get("key", ""))
        if new_element is None:
            updated.append(element)
            continue

        out = dict(element)
        if element.get("label") != new_element["label"]:
            changes.append((f"{element['key']} label", element["label"], new_element["label"]))
            out["label"] = new_element["label"]

        if "options" in element:
            new_options_by_value = {opt["value"]: opt for opt in new_element.get("options", [])}
            new_options = []
            for option in element["options"]:
                new_option = new_options_by_value.get(option.get("value"))
                if new_option is not None and option.get("label") != new_option["label"]:
                    changes.append(
                        (f"{element['key']}.{option['value']}", option["label"], new_option["label"])
                    )
                    new_options.append({**option, "label": new_option["label"]})
                else:
                    new_options.append(option)
            out["options"] = new_options

        updated.append(out)
    return updated, changes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply rut-spt's updated question/option numbering to every already-seeded draft/version",
    )
    parser.add_argument("--commit", action="store_true", help="Persist changes; default is dry-run")
    args = parser.parse_args()

    new_by_key = {element["key"]: element for element in build_rut_spt_schema()["elements"]}

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
                new_elements, changes = _relabeled_elements(record.schema["elements"], new_by_key)
                if not changes:
                    continue
                total_rows_changed += 1
                version_suffix = f" v{record.version}" if isinstance(record, TestVersionRecord) else ""
                print(f"bot #{definition.bot_instance_id} test #{definition.id} {label}{version_suffix}: {len(changes)} label(s) changed")
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
