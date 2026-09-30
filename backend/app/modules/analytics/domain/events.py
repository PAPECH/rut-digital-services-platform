from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

STABLE_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class AnalyticsEventName(StrEnum):
    APP_OPEN = "app_open"
    FAQ_OPEN = "faq_open"
    ABITURE_SEARCH = "abiture_search"
    NAVIGATOR_OPEN = "navigator_open"
    SUBMIT_PHONE = "submit_phone"
    PROFILE_UPDATED = "profile_updated"
    SUBMIT_FORM = "submit_form"
    FORM_OPEN = "form_open"
    FORM_START = "form_start"
    CONTENT_CATEGORY_OPEN = "content_category_open"
    CONTENT_TAB_OPEN = "content_tab_open"
    CONTENT_BLOCK_INTERACTION = "content_block_interaction"
    CAPABILITY_VIEW_OPEN = "capability_view_open"
    CAPABILITY_LOOKUP_COMPLETE = "capability_lookup_complete"
    CAPABILITY_SUBSCRIPTION_CHANGED = "capability_subscription_changed"
    NEWS_OPEN = "news_open"
    NEWS_ITEM_OPEN = "news_item_open"


class SourceSurface(StrEnum):
    HOME = "home"
    CATEGORY = "category"
    BOTTOM_NAV = "bottom_nav"
    FORM_CATALOG = "form_catalog"
    SUBMISSION_HISTORY = "submission_history"
    DIRECT = "direct"
    LEGACY = "legacy"


class ContentInteractionKind(StrEnum):
    LINK_OPEN = "link_open"
    ACCORDION_ITEM_OPEN = "accordion_item_open"
    CONTACT_OPEN = "contact_open"
    FILE_DOWNLOAD = "file_download"
    FORM_CARD_OPEN = "form_card_open"
    CAPABILITY_CARD_OPEN = "capability_card_open"
    FORM_CATALOG_OPEN = "form_catalog_open"
    SUBMISSION_HISTORY_OPEN = "submission_history_open"
    FAQ_LIST_OPEN = "faq_list_open"
    TEST_CARD_OPEN = "test_card_open"
    TEST_CATALOG_OPEN = "test_catalog_open"
    TEST_ATTEMPT_HISTORY_OPEN = "test_attempt_history_open"


class InvalidAnalyticsEvent(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AnalyticsEvent:
    event_id: str
    session_id: str | None
    bot_instance_id: int
    user_id: int
    action_type: AnalyticsEventName
    source_surface: SourceSurface | None = None
    interaction_kind: ContentInteractionKind | None = None
    category_id: int | None = None
    source_category_id: int | None = None
    content_version_id: int | None = None
    block_id: str | None = None
    item_id: str | None = None
    tabs_block_id: str | None = None
    tab_key: str | None = None
    form_template_id: int | None = None
    form_version_id: int | None = None
    faq_id: int | None = None
    attachment_id: int | None = None
    capability_installation_id: int | None = None
    capability_key: str | None = None
    capability_view_key: str | None = None
    outcome_code: str | None = None

    def __post_init__(self) -> None:
        self._validate_uuid(self.event_id, "event_id")
        if self.session_id is not None:
            self._validate_uuid(self.session_id, "session_id")
        if self.bot_instance_id <= 0 or self.user_id <= 0:
            raise InvalidAnalyticsEvent("Invalid analytics actor context")
        for field_name in (
            "category_id",
            "source_category_id",
            "content_version_id",
            "form_template_id",
            "form_version_id",
            "faq_id",
            "attachment_id",
            "capability_installation_id",
        ):
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                raise InvalidAnalyticsEvent(f"{field_name} must be positive")
        for field_name in ("block_id", "item_id", "tabs_block_id", "tab_key"):
            value = getattr(self, field_name)
            if value is not None and not STABLE_KEY_RE.fullmatch(value):
                raise InvalidAnalyticsEvent(f"Invalid {field_name}")
        self._validate_required_dimensions()

    @staticmethod
    def _validate_uuid(value: str, field_name: str) -> None:
        try:
            UUID(value)
        except (TypeError, ValueError) as exc:
            raise InvalidAnalyticsEvent(f"Invalid {field_name}") from exc

    def _require(self, *field_names: str) -> None:
        missing = [name for name in field_names if getattr(self, name) is None]
        if missing:
            raise InvalidAnalyticsEvent(
                f"Missing analytics dimensions: {', '.join(missing)}"
            )

    def _validate_required_dimensions(self) -> None:
        if self.action_type == AnalyticsEventName.CONTENT_CATEGORY_OPEN:
            self._require("category_id", "content_version_id")
        elif self.action_type == AnalyticsEventName.CONTENT_TAB_OPEN:
            self._require(
                "category_id",
                "content_version_id",
                "tabs_block_id",
                "tab_key",
            )
        elif self.action_type == AnalyticsEventName.CONTENT_BLOCK_INTERACTION:
            self._require("category_id", "block_id", "interaction_kind")
            # A capability shortcut tile (Task 044) taps this same event from the category grid,
            # not from within a rendered content page -- it has no content_version_id to report
            # (a shortcut category has no version at all). Every other interaction kind still
            # fires from inside an actual published content version, so keep requiring it there.
            if self.interaction_kind != ContentInteractionKind.CAPABILITY_CARD_OPEN:
                self._require("content_version_id")
        elif self.action_type in {
            AnalyticsEventName.FORM_OPEN,
            AnalyticsEventName.FORM_START,
        }:
            self._require("form_template_id", "form_version_id")
        elif self.action_type == AnalyticsEventName.FAQ_OPEN:
            self._require("faq_id")

