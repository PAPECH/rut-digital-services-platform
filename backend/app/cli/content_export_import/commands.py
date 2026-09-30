from __future__ import annotations

import argparse
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ...db.session import SessionLocal
from ...services.files import delete_file
from . import attachments, content, form_tests, forms, knowledge_base
from .archive import (
    FORMAT_VERSION,
    PART_ORDER,
    ContentExportImportError,
    parse_only_parts,
    read_manifest,
    write_archive,
)
from .bots import confirm, resolve_bot
from .form_test_references import (
    TestReferencePlan,
    collect_referenced_test_ids,
    existing_target_test_ids_by_slug,
    finalize_test_id_mapping,
    resolve_test_reference_plan,
)


def cmd_export(args: argparse.Namespace) -> None:
    with SessionLocal() as session:
        bot = resolve_bot(session, args.bot_instance)
        if bot is None:
            raise ContentExportImportError(f"source bot not found: {args.bot_instance}")

        categories_data = content.export_categories(session, bot.id)
        forms_data = forms.export_forms(session, bot.id)
        attachments_data, attachment_files = attachments.export_attachments(
            session,
            bot.id,
            categories_data,
        )
        tests_data = form_tests.export_tests(session, bot.id)
        consent_documents = form_tests.export_consent_documents(session, bot.id)
        faq_data = knowledge_base.export_faq(session, bot.id)
        kb_documents = knowledge_base.export_standalone_documents(session, bot.id)

        manifest = {
            "format_version": FORMAT_VERSION,
            "exported_at": datetime.now(tz=UTC).isoformat(),
            "source_bot": {"id": bot.id, "slug": bot.slug, "name": bot.name},
            "parts": list(PART_ORDER),
            "counts": {
                "categories": len(categories_data),
                "forms": len(forms_data),
                "attachments": len(attachments_data),
                "tests": len(tests_data),
                "consent_documents": len(consent_documents),
                "kb_faq": len(faq_data),
                "kb_documents": len(kb_documents),
            },
            "categories": categories_data,
            "forms": forms_data,
            "attachments": attachments_data,
            "tests": tests_data,
            "consent_documents": consent_documents,
            "kb_faq": faq_data,
            "kb_documents": kb_documents,
        }
        out_path = Path(args.out)
        write_archive(out_path, manifest, attachment_files)
        bot_slug = bot.slug

    print(f"Exported bot {bot_slug!r} to {out_path}")
    for key, value in manifest["counts"].items():
        print(f"{key}: {value}")


def _preflight_test_references(
    session: Session,
    manifest: dict[str, Any],
    bot_id: int,
    selected_parts: tuple[str, ...],
) -> TestReferencePlan:
    referenced_ids = collect_referenced_test_ids(manifest["categories"])
    archive_slug_by_id = {int(test["id"]): str(test["slug"]) for test in manifest["tests"]}
    referenced_slugs = {
        archive_slug_by_id[source_id]
        for source_id in referenced_ids
        if source_id in archive_slug_by_id
    }
    existing = (
        {}
        if "tests" in selected_parts
        else existing_target_test_ids_by_slug(session, bot_id, referenced_slugs)
    )
    return resolve_test_reference_plan(
        referenced_ids,
        manifest["tests"],
        tests_selected="tests" in selected_parts,
        existing_target_ids_by_slug=existing,
    )


def _preflight(
    session: Session,
    manifest: dict[str, Any],
    bot_id: int,
    selected_parts: tuple[str, ...],
) -> TestReferencePlan | None:
    if "content" in selected_parts:
        content.guard_target_empty(session, bot_id)
        forms.require_no_forms(session, bot_id)
    if "tests" in selected_parts:
        form_tests.guard_target_empty(session, bot_id)
        form_tests.validate_consent_references(manifest)
    if "kb" in selected_parts:
        knowledge_base.guard_target_empty(session, bot_id)
    if "content" in selected_parts:
        content.validate_capabilities(session, bot_id, manifest)
        return _preflight_test_references(
            session,
            manifest,
            bot_id,
            selected_parts,
        )
    return None


def import_manifest(
    session: Session,
    tar: tarfile.TarFile,
    manifest: dict[str, Any],
    bot_id: int,
    selected_parts: tuple[str, ...],
    *,
    commit: bool,
    copied_paths: list[str],
) -> dict[str, int]:
    test_plan = _preflight(session, manifest, bot_id, selected_parts)
    counts: dict[str, int] = {}
    imported_test_ids: dict[int, int] = {}

    if "tests" in selected_parts:
        consent_id_map = form_tests.import_consent_documents(session, manifest, bot_id)
        imported_test_ids = form_tests.import_tests(
            session,
            manifest,
            bot_id,
            consent_id_map,
        )
        counts["tests"] = len(imported_test_ids)
        counts["consent_documents"] = len(consent_id_map)

    if "content" in selected_parts:
        assert test_plan is not None
        test_id_map = finalize_test_id_mapping(test_plan, imported_test_ids)
        attachment_id_map = attachments.import_attachments(
            session,
            tar,
            manifest,
            bot_id,
            commit=commit,
            copied_paths=copied_paths,
        )
        form_id_map = forms.import_forms(session, manifest, bot_id)
        category_id_map = content.import_categories(
            session,
            manifest,
            bot_id,
            attachment_id_map,
        )
        content.import_content(
            session,
            manifest,
            bot_id,
            category_id_map,
            form_id_map,
            test_id_map,
            attachment_id_map,
        )
        content.set_home_category(session, manifest, category_id_map)
        counts["categories"] = len(category_id_map)
        counts["forms"] = len(form_id_map)
        counts["attachments"] = len(attachment_id_map)

    if "kb" in selected_parts:
        counts.update(knowledge_base.import_knowledge_base(session, manifest, bot_id))

    session.flush()
    return counts


def cmd_import(args: argparse.Namespace) -> None:
    archive_path = Path(args.archive)
    with tarfile.open(archive_path, "r:gz") as tar:
        manifest = read_manifest(tar)
        selected_parts = parse_only_parts(args.only, manifest["parts"])

        with SessionLocal() as session:
            target_bot = resolve_bot(session, args.bot_instance)
            if target_bot is None:
                raise ContentExportImportError(f"target bot not found: {args.bot_instance}")

            confirm(
                manifest,
                target_bot,
                selected_parts,
                assume_yes=args.yes,
            )

            copied_paths: list[str] = []
            try:
                counts = import_manifest(
                    session,
                    tar,
                    manifest,
                    target_bot.id,
                    selected_parts,
                    commit=args.commit,
                    copied_paths=copied_paths,
                )
                if args.commit:
                    session.commit()
                    mode = "COMMITTED"
                else:
                    session.rollback()
                    mode = "DRY RUN (rolled back)"
            except Exception:
                session.rollback()
                for path in copied_paths:
                    delete_file(path)
                raise

    print(mode)
    for key, value in counts.items():
        if key != "missing_embeddings":
            print(f"{key}: {value}")
    missing_embeddings = counts.get("missing_embeddings", 0)
    if missing_embeddings:
        print(
            "WARNING: "
            f"{missing_embeddings} knowledge-base document(s) were stored without an embedding"
        )
