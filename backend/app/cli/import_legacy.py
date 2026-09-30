"""One-way, tenant-scoped import from the first single-bot platform version."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..db.session import SessionLocal, engine as target_engine
from ..modules.admins.infrastructure.models import Admin
from ..models.attachment import Attachment
from ..models.enums import MessageDirectionEnum, SubmissionStatusEnum, SystemEnum
from ..models.legacy_import import LegacyImportReference
from ..modules.support_chat.infrastructure.models import Message
from ..modules.bot_instances.infrastructure.models import BotInstanceRecord
from ..modules.forms.infrastructure.models import (
    FormDefinitionRecord,
    FormDraftRecord,
    FormSubmission,
    FormVersionRecord,
    SubmissionStatusHistory,
)
from ..modules.knowledge_base.domain.entities import MessageAiClassificationEnum
from ..modules.profiles.infrastructure.models import BotMembershipRecord, User
from ..services.files import MAX_UPLOAD_BYTES, make_signed_url, open_file, store_file


class LegacyImportSourceError(RuntimeError):
    """The source backup cannot be imported without losing referenced data."""


def _rows(source: Engine, table: str) -> list[dict[str, Any]]:
    if table not in inspect(source).get_table_names():
        return []
    with source.connect() as connection:
        return [dict(row) for row in connection.execute(text(f'SELECT * FROM "{table}"')).mappings()]


def _json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _source_key(value: str) -> str:
    clean = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    if not clean:
        raise ValueError("source-key must contain letters or digits")
    return clean[:24]


def _legacy_idempotency(source_key: str, entity: str, source_id: Any) -> str:
    digest = hashlib.sha256(f"{source_key}:{entity}:{source_id}".encode()).hexdigest()[:32]
    return f"legacy:{entity}:{digest}"


def _field(field: dict[str, Any]) -> dict[str, Any]:
    common = {
        "key": str(field["id"]),
        "label": field.get("label") or f"Поле {field['id']}",
        "help_text": None,
        "required": bool(field.get("is_required", False)),
        "active": bool(field.get("is_active", True)),
        "profile_key": field.get("profile_key"),
    }
    field_type = _enum_value(field.get("type") or "string")
    if field_type == "number":
        return {
            **common,
            "type": "number",
            "default": field.get("default_value"),
            "min": field.get("min_value"),
            "max": field.get("max_value"),
            "step": 1,
        }
    if field_type == "date":
        return {
            **common,
            "type": "date",
            "default": field.get("default_value"),
            "min": field.get("min_value"),
            "max": field.get("max_value"),
        }
    if field_type == "checkbox":
        checked = str(field.get("default_value") or "false").lower() in {
            "true",
            "1",
            "yes",
            "on",
            "да",
        }
        return {**common, "type": "checkbox", "default": checked}
    return {
        **common,
        "type": "short_text",
        "placeholder": None,
        "default": field.get("default_value"),
        "min_length": 0,
        "max_length": 20_000,
        "pattern": field.get("regexp"),
    }


def _status(value: Any, *, allow_none: bool = False) -> SubmissionStatusEnum | None:
    if value is None and allow_none:
        return None
    try:
        return SubmissionStatusEnum(_enum_value(value or "new"))
    except ValueError:
        return None


def _ai_classification(value: Any) -> MessageAiClassificationEnum | None:
    """Map a legacy Message.ai_classification string onto the current enum. An
    exact match to a live member is kept; anything else — including the old
    kb:{id}/kb_selected:{id} shape (this importer never imports kb_documents, so
    that id has no meaning in the target schema) — becomes legacy_unknown so the
    column stays exhaustive. None stays None."""
    if value is None:
        return None
    try:
        return MessageAiClassificationEnum(_enum_value(value))
    except ValueError:
        return MessageAiClassificationEnum.legacy_unknown


class LegacyUploads:
    """Read legacy files beneath one trusted, read-only source directory."""

    def __init__(self, source_root: str | None) -> None:
        self._root = Path(source_root).resolve() if source_root else None

    def require_root(self) -> None:
        if self._root is None:
            raise LegacyImportSourceError(
                "Legacy attachments exist. Set LEGACY_UPLOADS_DIR or pass --legacy-uploads-dir."
            )
        if not self._root.is_dir():
            raise LegacyImportSourceError("Legacy uploads directory does not exist or is not a directory.")

    def read(self, storage_path: Any) -> bytes:
        self.require_root()
        raw_path = str(storage_path or "").strip()
        if not raw_path:
            raise LegacyImportSourceError("A legacy attachment has no storage path.")
        relative = Path(raw_path)
        if relative.is_absolute():
            raise LegacyImportSourceError("Legacy attachment storage path must be relative.")
        assert self._root is not None
        candidate = (self._root / relative).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise LegacyImportSourceError("Legacy attachment storage path escapes uploads directory.") from exc
        if not candidate.is_file():
            raise LegacyImportSourceError(f"Legacy attachment file is missing: {raw_path}")
        with candidate.open("rb") as source:
            content = source.read(MAX_UPLOAD_BYTES + 1)
        if not content:
            raise LegacyImportSourceError(f"Legacy attachment file is empty: {raw_path}")
        if len(content) > MAX_UPLOAD_BYTES:
            raise LegacyImportSourceError(f"Legacy attachment exceeds the 20 MB platform limit: {raw_path}")
        return content


class LegacyImporter:
    def __init__(
        self,
        source: Engine,
        target: Session,
        bot: BotInstanceRecord,
        source_key: str,
        *,
        legacy_uploads_dir: str | None,
        persist_files: bool,
    ) -> None:
        self.source = source
        self.target = target
        self.bot = bot
        self.source_key = source_key
        self.uploads = LegacyUploads(legacy_uploads_dir)
        self.persist_files = persist_files
        self.counts: Counter[str] = Counter()
        self.user_ids: dict[int, int] = {}
        self.form_ids: dict[int, tuple[int, int]] = {}
        self.form_snapshots: dict[int, dict[str, Any]] = {}
        self.submission_ids: dict[int, int] = {}
        self.attachment_ids: dict[int, int] = {}
        self.target_admin_ids: dict[int, int] = {}
        self._source_attachments: list[dict[str, Any]] = []
        self._created_file_paths: list[str] = []

    def run(self) -> Counter[str]:
        self._preflight_attachments()
        self.import_users()
        self.import_attachments()
        self.import_forms()
        self.import_submissions()
        self.import_submission_history()
        self.import_messages()
        return self.counts

    def cleanup_copied_files(self) -> None:
        for storage_path in reversed(self._created_file_paths):
            try:
                open_file(storage_path).unlink()
            except OSError:
                continue

    def _preflight_attachments(self) -> None:
        self._source_attachments = _rows(self.source, "attachments")
        if not self._source_attachments:
            return
        self.uploads.require_root()
        for row in self._source_attachments:
            self.uploads.read(row.get("storage_path"))
        self.counts["attachments_validated"] = len(self._source_attachments)

    def _reference(self, entity_type: str, source_id: Any) -> LegacyImportReference | None:
        return self.target.execute(
            select(LegacyImportReference).where(
                LegacyImportReference.bot_instance_id == self.bot.id,
                LegacyImportReference.source_key == self.source_key,
                LegacyImportReference.entity_type == entity_type,
                LegacyImportReference.source_record_id == str(source_id),
            )
        ).scalar_one_or_none()

    def _remember_reference(self, entity_type: str, source_id: Any, target_id: int) -> None:
        reference = self._reference(entity_type, source_id)
        if reference is None:
            reference = LegacyImportReference(
                bot_instance_id=self.bot.id,
                source_key=self.source_key,
                entity_type=entity_type,
                source_record_id=str(source_id),
                target_id=target_id,
            )
            self.target.add(reference)
        else:
            reference.target_id = target_id

    def _load_admin_mapping(self) -> None:
        if self.target_admin_ids:
            return
        source_admins = _rows(self.source, "admins")
        source_max_ids = {
            int(row["id"]): str(row.get("max_user_id") or "").strip()
            for row in source_admins
            if row.get("id") is not None and str(row.get("max_user_id") or "").strip()
        }
        if not source_max_ids:
            return
        existing_admins = {
            admin.max_user_id: admin.id
            for admin in self.target.execute(
                select(Admin).where(Admin.max_user_id.in_(set(source_max_ids.values())))
            ).scalars()
        }
        self.target_admin_ids = {
            source_id: existing_admins[max_user_id]
            for source_id, max_user_id in source_max_ids.items()
            if max_user_id in existing_admins
        }

    def _target_admin_id(self, source_admin_id: Any) -> int | None:
        if source_admin_id is None:
            return None
        self._load_admin_mapping()
        try:
            return self.target_admin_ids.get(int(source_admin_id))
        except (TypeError, ValueError):
            return None

    def import_users(self) -> None:
        for row in _rows(self.source, "users"):
            system_value = _enum_value(row.get("system") or "max")
            try:
                system = SystemEnum(system_value)
            except ValueError:
                self.counts["users_skipped"] += 1
                continue
            external_user_id = str(row.get("user_id") or "")
            if not external_user_id:
                self.counts["users_skipped"] += 1
                continue
            user = self.target.execute(
                select(User).where(User.user_id == external_user_id, User.system == system)
            ).scalar_one_or_none()
            if user is None:
                user = User(user_id=external_user_id, system=system)
                self.target.add(user)
                self.counts["users_created"] += 1
            else:
                self.counts["users_existing"] += 1
            for name in (
                "last_name",
                "first_name",
                "patronymic",
                "username",
                "phone",
                "email",
                "photo_url",
                "language_code",
                "birth_date",
                "study_group",
                "rut_personnel_number",
                "job_title",
                "structural_unit",
            ):
                if row.get(name) is not None and getattr(user, name, None) is None:
                    setattr(user, name, row[name])
            user.phone_verified = bool(row.get("phone_verified", user.phone_verified or False))
            if row.get("shared_data"):
                user.shared_data = _json(row["shared_data"], {})
            self.target.flush()
            self.user_ids[int(row["id"])] = user.id

            membership = self.target.execute(
                select(BotMembershipRecord).where(
                    BotMembershipRecord.bot_instance_id == self.bot.id,
                    BotMembershipRecord.user_id == user.id,
                )
            ).scalar_one_or_none()
            if membership is None:
                membership = BotMembershipRecord(bot_instance_id=self.bot.id, user_id=user.id)
                self.target.add(membership)
                self.counts["memberships_created"] += 1
            for flag in ("ban_chat", "ban_forms", "ban_app"):
                setattr(membership, flag, bool(row.get(flag, False)))
                setattr(membership, f"{flag}_reason", row.get(f"{flag}_reason"))

    def import_attachments(self) -> None:
        for row in self._source_attachments:
            source_id = int(row["id"])
            reference = self._reference("attachment", source_id)
            existing = self.target.get(Attachment, reference.target_id) if reference else None
            if existing is not None:
                self.attachment_ids[source_id] = existing.id
                self.counts["attachments_existing"] += 1
                continue

            content = self.uploads.read(row.get("storage_path"))
            if self.persist_files:
                storage_path, size_bytes = store_file(
                    content,
                    original_name=str(row.get("original_name") or "legacy-file"),
                )
                self._created_file_paths.append(storage_path)
            else:
                storage_path = f"dry-run/{self.source_key}/attachment-{source_id}"
                size_bytes = len(content)
            attachment = Attachment(
                bot_instance_id=self.bot.id,
                storage_path=storage_path,
                original_name=str(row.get("original_name") or "legacy-file")[:255],
                mime=str(row.get("mime") or "application/octet-stream")[:120],
                size_bytes=size_bytes,
                uploaded_by_user_id=self.user_ids.get(int(row["uploaded_by_user_id"]))
                if row.get("uploaded_by_user_id") is not None
                else None,
            )
            self.target.add(attachment)
            self.target.flush()
            self._remember_reference("attachment", source_id, attachment.id)
            self.attachment_ids[source_id] = attachment.id
            self.counts["attachments_created"] += 1

    def import_forms(self) -> None:
        fields_by_form: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for field in _rows(self.source, "form_fields"):
            fields_by_form[int(field["form_template_id"])].append(field)
        for source_id, fields in fields_by_form.items():
            fields.sort(key=lambda item: (item.get("order") or 0, item["id"]))

        for row in _rows(self.source, "form_templates"):
            source_id = int(row["id"])
            converted = [_field(field) for field in fields_by_form[source_id]]
            slug = f"legacy-{self.source_key}-{source_id}"[:80]
            definition = self.target.execute(
                select(FormDefinitionRecord).where(
                    FormDefinitionRecord.bot_instance_id == self.bot.id,
                    FormDefinitionRecord.slug == slug,
                )
            ).scalar_one_or_none()
            if definition is not None:
                version_id = definition.published_version_id
                if version_id is None:
                    version_id = self.target.execute(
                        select(FormVersionRecord.id)
                        .where(FormVersionRecord.form_definition_id == definition.id)
                        .order_by(FormVersionRecord.version.desc())
                    ).scalar_one_or_none()
                if version_id is not None:
                    self.form_ids[source_id] = (definition.id, version_id)
                    version = self.target.get(FormVersionRecord, version_id)
                    self.form_snapshots[source_id] = {
                        "legacy_source_id": source_id,
                        "name": definition.name,
                        "fields": version.fields if version is not None else converted,
                    }
                self.counts["forms_existing"] += 1
                continue

            now = row.get("created_at") or datetime.now(tz=timezone.utc)
            definition = FormDefinitionRecord(
                bot_instance_id=self.bot.id,
                slug=slug,
                name=row.get("name") or f"Форма {source_id}",
                description=row.get("description"),
                reply_on_accept=row.get("reply_on_accept"),
                is_active=bool(row.get("is_active", True)),
                order=int(row.get("order") or 0),
                is_archived=False,
                last_published_revision=0,
                created_at=now,
                updated_at=row.get("updated_at") or now,
            )
            self.target.add(definition)
            self.target.flush()
            draft = FormDraftRecord(
                form_definition_id=definition.id,
                name=definition.name,
                description=definition.description,
                reply_on_accept=definition.reply_on_accept,
                fields=converted,
                revision=0,
                created_at=now,
                updated_at=row.get("updated_at") or now,
            )
            version = FormVersionRecord(
                form_definition_id=definition.id,
                version=1,
                source_revision=0,
                name=definition.name,
                description=definition.description,
                reply_on_accept=definition.reply_on_accept,
                fields=converted,
                published_at=now,
            )
            self.target.add_all([draft, version])
            self.target.flush()
            definition.published_version_id = version.id
            self.form_ids[source_id] = (definition.id, version.id)
            self.form_snapshots[source_id] = {
                "legacy_source_id": source_id,
                "name": definition.name,
                "fields": converted,
            }
            self.counts["forms_created"] += 1

    def import_submissions(self) -> None:
        for row in _rows(self.source, "form_submissions"):
            source_id = int(row["id"])
            user_id = self.user_ids.get(int(row["user_id"]))
            form = self.form_ids.get(int(row["form_template_id"]))
            if user_id is None or form is None:
                self.counts["submissions_skipped"] += 1
                continue
            key = _legacy_idempotency(self.source_key, "submission", source_id)
            existing = self.target.execute(
                select(FormSubmission).where(
                    FormSubmission.bot_instance_id == self.bot.id,
                    FormSubmission.idempotency_key == key,
                )
            ).scalar_one_or_none()
            if existing is not None:
                self.submission_ids[source_id] = existing.id
                self.counts["submissions_existing"] += 1
                continue

            status = _status(row.get("status")) or SubmissionStatusEnum.new
            values = _json(row.get("values"), {})
            source_form_id = int(row["form_template_id"])
            form_snapshot = self.form_snapshots.get(
                source_form_id,
                {"legacy_source_id": source_form_id, "name": None, "fields": []},
            )
            field_labels = _json(row.get("field_labels"), None) or {
                field["key"]: field["label"] for field in form_snapshot["fields"]
            }
            submission = FormSubmission(
                bot_instance_id=self.bot.id,
                form_template_id=form[0],
                form_version_id=form[1],
                user_id=user_id,
                values=values,
                values_en=_json(row.get("values_en"), None),
                field_labels=field_labels,
                form_snapshot=_json(row.get("form_snapshot"), form_snapshot),
                profile_snapshot=_json(row.get("profile_snapshot"), {}),
                status=status,
                taken_at=row.get("taken_at"),
                closed_at=row.get("closed_at"),
                assignee_admin_id=self._target_admin_id(row.get("assignee_admin_id")),
                idempotency_key=key,
                created_at=row.get("created_at") or datetime.now(tz=timezone.utc),
                updated_at=row.get("updated_at")
                or row.get("created_at")
                or datetime.now(tz=timezone.utc),
            )
            self.target.add(submission)
            self.target.flush()
            self.submission_ids[source_id] = submission.id
            self.counts["submissions_created"] += 1

    def import_submission_history(self) -> None:
        for row in _rows(self.source, "submission_status_history"):
            source_id = int(row["id"])
            submission_id = self.submission_ids.get(int(row["submission_id"]))
            to_status = _status(row.get("to_status"))
            if submission_id is None or to_status is None:
                self.counts["submission_history_skipped"] += 1
                continue
            reference = self._reference("submission_status_history", source_id)
            if reference is not None and reference.target_id is not None:
                self.counts["submission_history_existing"] += 1
                continue
            history = SubmissionStatusHistory(
                submission_id=submission_id,
                from_status=_status(row.get("from_status"), allow_none=True),
                to_status=to_status,
                changed_by=self._target_admin_id(row.get("changed_by")),
                changed_at=row.get("changed_at") or datetime.now(tz=timezone.utc),
                comment=row.get("comment"),
            )
            self.target.add(history)
            self.target.flush()
            self._remember_reference("submission_status_history", source_id, history.id)
            self.counts["submission_history_created"] += 1

    def _message_attachments(self, value: Any) -> list[dict[str, Any]] | None:
        raw_attachments = _json(value, [])
        if not isinstance(raw_attachments, list):
            return None
        result: list[dict[str, Any]] = []
        for item in raw_attachments:
            if not isinstance(item, dict):
                self.counts["message_attachments_skipped"] += 1
                continue
            source_id = item.get("id")
            try:
                target_id = self.attachment_ids.get(int(source_id))
            except (TypeError, ValueError):
                target_id = None
            attachment = self.target.get(Attachment, target_id) if target_id else None
            if attachment is not None:
                result.append(
                    {
                        "id": attachment.id,
                        "url": make_signed_url(attachment.id),
                        "name": attachment.original_name,
                        "mime": attachment.mime,
                        "size": attachment.size_bytes,
                    }
                )
                continue
            url = item.get("url")
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                result.append(
                    {
                        "url": url,
                        "name": item.get("name"),
                        "mime": item.get("mime"),
                        "size": item.get("size"),
                    }
                )
                self.counts["message_external_attachments_preserved"] += 1
            else:
                self.counts["message_attachments_skipped"] += 1
        return result or None

    def import_messages(self) -> None:
        for row in _rows(self.source, "messages"):
            source_id = int(row["id"])
            user_id = self.user_ids.get(int(row["user_id"]))
            if user_id is None:
                self.counts["messages_skipped"] += 1
                continue
            external_id = _legacy_idempotency(self.source_key, "message", source_id)
            exists = self.target.execute(
                select(Message.id).where(
                    Message.bot_instance_id == self.bot.id,
                    Message.external_id == external_id,
                )
            ).scalar_one_or_none()
            if exists is not None:
                self.counts["messages_existing"] += 1
                continue
            try:
                direction = MessageDirectionEnum(_enum_value(row.get("direction") or "in"))
                system = SystemEnum(_enum_value(row.get("system") or "max"))
            except ValueError:
                self.counts["messages_skipped"] += 1
                continue
            self.target.add(
                Message(
                    bot_instance_id=self.bot.id,
                    user_id=user_id,
                    system=system,
                    direction=direction,
                    text=row.get("text"),
                    attachments=self._message_attachments(row.get("attachments")),
                    is_ai_answered=bool(row.get("is_ai_answered", False)),
                    ai_classification=_ai_classification(row.get("ai_classification")),
                    external_id=external_id,
                    created_at=row.get("created_at") or datetime.now(tz=timezone.utc),
                    updated_at=row.get("updated_at")
                    or row.get("created_at")
                    or datetime.now(tz=timezone.utc),
                )
            )
            self.counts["messages_created"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a legacy bot database into one bot tenant")
    parser.add_argument("--bot-slug", required=True, help="Target bot slug in the new platform")
    parser.add_argument("--source-key", default="legacy", help="Stable source key, e.g. personnel-v1")
    parser.add_argument(
        "--legacy-uploads-dir",
        default=os.getenv("LEGACY_UPLOADS_DIR", "").strip() or None,
        help="Read-only path to the legacy uploads directory; required when it contains attachments",
    )
    parser.add_argument("--commit", action="store_true", help="Commit changes; default is dry-run rollback")
    args = parser.parse_args()
    source_url = os.getenv("LEGACY_DATABASE_URL", "").strip()
    if not source_url:
        parser.error("LEGACY_DATABASE_URL is required")
    target_url = target_engine.url.render_as_string(hide_password=False)
    if source_url == target_url:
        parser.error("legacy source and target database URLs must differ")

    source = create_engine(source_url, pool_pre_ping=True, future=True)
    importer: LegacyImporter | None = None
    try:
        if "users" not in inspect(source).get_table_names():
            parser.error("legacy source does not contain the required users table")
        with SessionLocal() as target:
            bot = target.execute(
                select(BotInstanceRecord).where(BotInstanceRecord.slug == args.bot_slug)
            ).scalar_one_or_none()
            if bot is None:
                parser.error(f"target bot slug not found: {args.bot_slug}")
            importer = LegacyImporter(
                source,
                target,
                bot,
                _source_key(args.source_key),
                legacy_uploads_dir=args.legacy_uploads_dir,
                persist_files=args.commit,
            )
            try:
                counts = importer.run()
                target.flush()
                if args.commit:
                    target.commit()
                    mode = "COMMITTED"
                else:
                    target.rollback()
                    mode = "DRY RUN (rolled back)"
            except Exception:
                target.rollback()
                importer.cleanup_copied_files()
                raise
    finally:
        source.dispose()

    print(mode)
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")


if __name__ == "__main__":
    main()
