"""Load the demo bots, their content, FAQ, a published test and synthetic activity.

Usage:
    python -m app.cli.demo_seed

Idempotent: a bot that already exists is left untouched.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import tarfile
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .. import models as _models  # noqa: F401  (must load before module models)
from ..db.model_registry import load_all_models
from ..db.session import SessionLocal
from ..modules.bot_instances.infrastructure.models import AppSetting, BotInstanceRecord
from ..modules.form_tests.domain.schema import validate_test_schema
from ..modules.form_tests.infrastructure.repositories import SqlAlchemyTestRepository
from ..modules.forms.infrastructure.models import (
    FormDefinitionRecord,
    FormDraftRecord,
    FormVersionRecord,
)
from ..modules.knowledge_base.application.use_cases import create_faq_mirror
from ..modules.knowledge_base.domain.entities import KbFaq
from ..modules.knowledge_base.infrastructure.embedding import FastEmbedEmbeddingPort
from ..modules.knowledge_base.infrastructure.repositories import (
    SqlAlchemyKbDocumentRepository,
    SqlAlchemyKbFaqRepository,
)
from .content_export_import import HOME_CATEGORY_SLUG, MANIFEST_NAME, import_manifest
from .demo_activity import seed_activity

log = logging.getLogger(__name__)

DEMO_DIR = Path(os.getenv("DEMO_SEED_DIR", Path(__file__).resolve().parents[2] / "seed" / "demo"))
MAIN_BOT_SLUG = "helper_rut_bot"
REQUEST_FORM_SLUG = "certificates-request"
REPLY_ON_ACCEPT = (
    "Статус: «Принята». Мы сообщим в этом чате, когда документы будут готовы. "
    "Следить за заявкой можно в разделе «Мои обращения»."
)


def _find_bot(db: Session, slug: str) -> BotInstanceRecord | None:
    return db.execute(
        select(BotInstanceRecord).where(
            BotInstanceRecord.slug == slug, BotInstanceRecord.deleted_at.is_(None)
        )
    ).scalar_one_or_none()


def _create_bot(db: Session, spec: dict[str, Any]) -> BotInstanceRecord:
    bot = BotInstanceRecord(
        slug=spec["slug"],
        name=spec["name"],
        description=spec.get("description"),
        order=spec.get("order", 0),
        branding=spec.get("branding") or {},
        settings=spec.get("settings") or {},
        profile_schema=spec.get("profile_schema") or [],
    )
    db.add(bot)
    db.flush()
    for key, value in (spec.get("app_settings") or {}).items():
        db.add(AppSetting(bot_instance_id=bot.id, key=key, value=value))
    db.flush()
    return bot


def _publish_test(db: Session, bot_id: int, path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    published = SqlAlchemyTestRepository(db).seed_published_test(
        bot_instance_id=bot_id,
        slug=data["slug"],
        name=data["name"],
        intro_text=data.get("intro_text"),
        schema=validate_test_schema(data["schema"]),
        is_active=True,
    )
    return published.definition.id


def _add_test_tile(manifest: dict[str, Any], test_id: int, title: str) -> None:
    tile = {"id": "demo_test", "type": "test_action", "test_id": test_id, "title": title}
    for category in manifest["categories"]:
        if category["slug"] != HOME_CATEGORY_SLUG:
            continue
        for part in ("draft", "published"):
            if category[part] is not None:
                category[part]["blocks"].append(copy.deepcopy(tile))


def _import_content(db: Session, bot_id: int, archive: Path, test: tuple[int, str] | None) -> None:
    copied: list[str] = []
    with tarfile.open(archive, "r:gz") as tar:
        member = tar.extractfile(MANIFEST_NAME)
        if member is None:
            raise RuntimeError(f"{archive.name} has no {MANIFEST_NAME}")
        manifest = json.loads(member.read())
        if test is not None:
            _add_test_tile(manifest, *test)
        counts = import_manifest(db, tar, manifest, bot_id, commit=True, copied_paths=copied)
    log.info("imported %s: %s", archive.name, counts)


def _activate_forms(db: Session, bot_id: int) -> None:
    db.execute(
        update(FormDefinitionRecord)
        .where(
            FormDefinitionRecord.bot_instance_id == bot_id,
            FormDefinitionRecord.published_version_id.isnot(None),
            FormDefinitionRecord.is_archived.is_(False),
        )
        .values(is_active=True)
    )


def _set_reply_on_accept(db: Session, bot_id: int) -> None:
    form = db.execute(
        select(FormDefinitionRecord).where(
            FormDefinitionRecord.bot_instance_id == bot_id,
            FormDefinitionRecord.slug == REQUEST_FORM_SLUG,
        )
    ).scalar_one_or_none()
    if form is None:
        return
    draft = db.execute(
        select(FormDraftRecord).where(FormDraftRecord.form_definition_id == form.id)
    ).scalar_one_or_none()
    if draft is not None:
        draft.reply_on_accept = REPLY_ON_ACCEPT
    if form.published_version_id is not None:
        version = db.get(FormVersionRecord, form.published_version_id)
        if version is not None:
            version.reply_on_accept = REPLY_ON_ACCEPT
    db.flush()


def _add_faq(db: Session, bot_id: int, items: list[dict[str, Any]]) -> None:
    faq_repository = SqlAlchemyKbFaqRepository(db)
    document_repository = SqlAlchemyKbDocumentRepository(db)
    embedder = FastEmbedEmbeddingPort()
    for item in items:
        faq = faq_repository.add(
            KbFaq(
                id=None,
                bot_instance_id=bot_id,
                question=item["question"],
                answer=item["answer"],
                is_active=item.get("is_active", True),
                order=item.get("order", 0),
            )
        )
        create_faq_mirror(faq, document_repository, embedder)
    db.flush()


def run() -> None:
    load_all_models()
    specs = json.loads((DEMO_DIR / "bots.json").read_text(encoding="utf-8"))
    test_path = DEMO_DIR / "tests" / "railway_safety.json"
    with SessionLocal() as db:
        created: dict[str, BotInstanceRecord] = {}
        for spec in specs:
            if _find_bot(db, spec["slug"]) is not None:
                log.info("bot %s already exists, skipping", spec["slug"])
                continue
            bot = _create_bot(db, spec)
            test = None
            if spec["slug"] == MAIN_BOT_SLUG and test_path.exists():
                test = (_publish_test(db, bot.id, test_path), "Тест: безопасность на железной дороге")
            _import_content(db, bot.id, DEMO_DIR / spec["archive"], test)
            _activate_forms(db, bot.id)
            if spec["slug"] == MAIN_BOT_SLUG:
                _set_reply_on_accept(db, bot.id)
            _add_faq(db, bot.id, spec.get("faq") or [])
            created[spec["slug"]] = bot
        if created:
            seed_activity(db, created, main_slug=MAIN_BOT_SLUG, request_form_slug=REQUEST_FORM_SLUG)
        db.commit()
    log.info("demo seed done: %s", ", ".join(created) or "nothing to do")


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")
    run()
