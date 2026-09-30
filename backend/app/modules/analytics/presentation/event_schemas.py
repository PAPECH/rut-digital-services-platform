from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

ClientAnalyticsAction = Literal[
    "app_open",
    "navigator_open",
    "content_category_open",
    "content_tab_open",
    "content_block_interaction",
    "form_open",
    "form_start",
    "faq_open",
]
SourceSurfaceValue = Literal[
    "home",
    "category",
    "bottom_nav",
    "form_catalog",
    "submission_history",
    "direct",
]
InteractionKindValue = Literal[
    "link_open",
    "accordion_item_open",
    "contact_open",
    "file_download",
    "form_card_open",
    "capability_card_open",
    "form_catalog_open",
    "submission_history_open",
    "faq_list_open",
    "test_card_open",
    "test_catalog_open",
    "test_attempt_history_open",
]


class AnalyticsEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    session_id: UUID
    action_type: ClientAnalyticsAction
    source_surface: SourceSurfaceValue | None = None
    interaction_kind: InteractionKindValue | None = None
    category_id: PositiveInt | None = None
    source_category_id: PositiveInt | None = None
    content_version_id: PositiveInt | None = None
    block_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    item_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    tabs_block_id: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"
    )
    tab_key: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    form_template_id: PositiveInt | None = None
    form_version_id: PositiveInt | None = None
    faq_id: PositiveInt | None = None
    attachment_id: PositiveInt | None = None
    capability_installation_id: PositiveInt | None = None
    capability_key: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{1,63}$")
    capability_view_key: str | None = Field(
        default=None, pattern=r"^[a-z][a-z0-9_-]{1,63}$"
    )
