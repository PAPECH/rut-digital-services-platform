from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ....models.attachment import Attachment
from ....models.logger import UserAction
from ...capabilities.infrastructure.models import CapabilityInstallationRecord
from ...content.infrastructure.models import ContentCategoryRecord, ContentVersionRecord
from ...forms.infrastructure.models import FormDefinitionRecord, FormVersionRecord
from ...knowledge_base.infrastructure.models import KbFaqRecord
from ..domain.events import (
    AnalyticsEvent,
    AnalyticsEventName,
    ContentInteractionKind,
    InvalidAnalyticsEvent,
)


def _iter_blocks(blocks: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for block in blocks:
        yield block
        if block.get("type") == "tabs":
            for tab in block.get("tabs", []):
                yield from _iter_blocks(tab.get("blocks", []))


class SqlAlchemyAnalyticsEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def validate_context(self, event: AnalyticsEvent) -> None:
        version: ContentVersionRecord | None = None
        if event.category_id is not None or event.content_version_id is not None:
            if event.category_id is None or event.content_version_id is None:
                raise InvalidAnalyticsEvent("Category and content version must be supplied together")
            version = self._session.execute(
                select(ContentVersionRecord)
                .join(
                    ContentCategoryRecord,
                    ContentCategoryRecord.id == ContentVersionRecord.category_id,
                )
                .where(
                    ContentCategoryRecord.bot_instance_id == event.bot_instance_id,
                    ContentCategoryRecord.id == event.category_id,
                    ContentVersionRecord.id == event.content_version_id,
                )
            ).scalar_one_or_none()
            if version is None:
                raise InvalidAnalyticsEvent("Content context belongs to another bot or version")

        if event.source_category_id is not None:
            source_exists = self._session.execute(
                select(ContentCategoryRecord.id).where(
                    ContentCategoryRecord.bot_instance_id == event.bot_instance_id,
                    ContentCategoryRecord.id == event.source_category_id,
                )
            ).scalar_one_or_none()
            if source_exists is None:
                raise InvalidAnalyticsEvent("Source category belongs to another bot")

        block: dict[str, Any] | None = None
        if event.block_id is not None or event.tabs_block_id is not None:
            if version is None:
                raise InvalidAnalyticsEvent("Block context requires a content version")
            requested_id = event.tabs_block_id or event.block_id
            block = next(
                (item for item in _iter_blocks(version.blocks) if item.get("id") == requested_id),
                None,
            )
            if block is None:
                raise InvalidAnalyticsEvent("Content block does not belong to the published version")

        if event.action_type == AnalyticsEventName.CONTENT_TAB_OPEN:
            if block is None or block.get("type") != "tabs":
                raise InvalidAnalyticsEvent("Tab does not belong to a tabs block")
            if event.tab_key not in {tab.get("key") for tab in block.get("tabs", [])}:
                raise InvalidAnalyticsEvent("Tab does not belong to the published version")

        if event.action_type == AnalyticsEventName.CONTENT_BLOCK_INTERACTION:
            self._validate_block_interaction(event, block)

        if event.form_template_id is not None or event.form_version_id is not None:
            if event.form_template_id is None:
                raise InvalidAnalyticsEvent("Form version requires a form")
            form_query = select(FormDefinitionRecord.id).where(
                FormDefinitionRecord.bot_instance_id == event.bot_instance_id,
                FormDefinitionRecord.id == event.form_template_id,
            )
            if event.form_version_id is not None:
                form_query = form_query.join(
                    FormVersionRecord,
                    FormVersionRecord.form_definition_id == FormDefinitionRecord.id,
                ).where(FormVersionRecord.id == event.form_version_id)
            form_exists = self._session.execute(form_query).scalar_one_or_none()
            if form_exists is None:
                raise InvalidAnalyticsEvent("Form context belongs to another bot or version")

        if event.faq_id is not None:
            faq_exists = self._session.execute(
                select(KbFaqRecord.id).where(
                    KbFaqRecord.bot_instance_id == event.bot_instance_id,
                    KbFaqRecord.id == event.faq_id,
                )
            ).scalar_one_or_none()
            if faq_exists is None:
                raise InvalidAnalyticsEvent("FAQ belongs to another bot")

        if event.attachment_id is not None:
            attachment_exists = self._session.execute(
                select(Attachment.id).where(
                    Attachment.bot_instance_id == event.bot_instance_id,
                    Attachment.id == event.attachment_id,
                )
            ).scalar_one_or_none()
            if attachment_exists is None:
                raise InvalidAnalyticsEvent("Attachment belongs to another bot")

        if event.capability_installation_id is not None:
            capability_exists = self._session.execute(
                select(CapabilityInstallationRecord.id).where(
                    CapabilityInstallationRecord.bot_instance_id == event.bot_instance_id,
                    CapabilityInstallationRecord.id == event.capability_installation_id,
                    CapabilityInstallationRecord.capability_key == event.capability_key,
                )
            ).scalar_one_or_none()
            if capability_exists is None:
                raise InvalidAnalyticsEvent("Capability belongs to another bot")

    @staticmethod
    def _validate_block_interaction(
        event: AnalyticsEvent,
        block: dict[str, Any] | None,
    ) -> None:
        if block is None or event.interaction_kind is None:
            raise InvalidAnalyticsEvent("Content interaction requires a concrete block")
        expected_types = {
            ContentInteractionKind.LINK_OPEN: "link",
            ContentInteractionKind.ACCORDION_ITEM_OPEN: "accordion",
            ContentInteractionKind.CONTACT_OPEN: "contact_list",
            ContentInteractionKind.FILE_DOWNLOAD: "file_list",
            ContentInteractionKind.FORM_CARD_OPEN: "form_action",
            ContentInteractionKind.CAPABILITY_CARD_OPEN: "capability_action",
            ContentInteractionKind.FORM_CATALOG_OPEN: "form_catalog",
            ContentInteractionKind.SUBMISSION_HISTORY_OPEN: "submission_history",
            ContentInteractionKind.FAQ_LIST_OPEN: "faq_list",
            ContentInteractionKind.TEST_CARD_OPEN: "test_action",
            ContentInteractionKind.TEST_CATALOG_OPEN: "test_catalog",
            ContentInteractionKind.TEST_ATTEMPT_HISTORY_OPEN: "test_attempt_history",
        }
        if block.get("type") != expected_types[event.interaction_kind]:
            raise InvalidAnalyticsEvent("Interaction kind does not match the content block")
        if event.interaction_kind == ContentInteractionKind.ACCORDION_ITEM_OPEN:
            if event.item_id not in {item.get("id") for item in block.get("items", [])}:
                raise InvalidAnalyticsEvent("Accordion item does not belong to the block")
        elif event.interaction_kind == ContentInteractionKind.FILE_DOWNLOAD:
            if event.attachment_id not in {
                item.get("attachment_id") for item in block.get("items", [])
            }:
                raise InvalidAnalyticsEvent("File does not belong to the block")
        elif event.interaction_kind == ContentInteractionKind.FORM_CARD_OPEN:
            if event.form_template_id != block.get("form_id"):
                raise InvalidAnalyticsEvent("Form target does not match the block")
        elif event.interaction_kind == ContentInteractionKind.CAPABILITY_CARD_OPEN:
            if (
                event.capability_key != block.get("capability_key")
                or event.capability_view_key != block.get("view_key")
            ):
                raise InvalidAnalyticsEvent("Capability target does not match the block")

    def add(self, event: AnalyticsEvent) -> bool:
        values = {
            "event_id": event.event_id,
            "session_id": event.session_id,
            "bot_instance_id": event.bot_instance_id,
            "user_id": event.user_id,
            "action_type": event.action_type.value,
            "source_surface": event.source_surface.value if event.source_surface else None,
            "interaction_kind": (
                event.interaction_kind.value if event.interaction_kind else None
            ),
            "category_id": event.category_id,
            "source_category_id": event.source_category_id,
            "content_version_id": event.content_version_id,
            "block_id": event.block_id,
            "item_id": event.item_id,
            "tabs_block_id": event.tabs_block_id,
            "tab_key": event.tab_key,
            "form_template_id": event.form_template_id,
            "form_version_id": event.form_version_id,
            "faq_id": event.faq_id,
            "attachment_id": event.attachment_id,
            "capability_installation_id": event.capability_installation_id,
            "capability_key": event.capability_key,
            "capability_view_key": event.capability_view_key,
            "outcome_code": event.outcome_code,
            "description": None,
            "payload": None,
        }
        result = self._session.execute(
            insert(UserAction)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[UserAction.event_id])
        )
        return bool(result.rowcount)
