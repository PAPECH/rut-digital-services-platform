from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.main import app
from app.modules.analytics.application.dashboard_use_cases import resolve_period
from app.modules.analytics.application.use_cases import RecordAnalyticsEvent
from app.modules.analytics.domain.events import (
    AnalyticsEvent,
    AnalyticsEventName,
    ContentInteractionKind,
    InvalidAnalyticsEvent,
    SourceSurface,
)
from app.modules.analytics.infrastructure.dashboard_repository import SqlAlchemyDashboardRepository
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.content.infrastructure.models import ContentVersionRecord
from app.modules.tenancy.presentation.dependencies import resolve_tenant


def _event(**overrides) -> AnalyticsEvent:
    values = {
        "event_id": "a01f9091-a293-4f26-86a5-cc7feca04c7b",
        "session_id": "7cc9f565-22c3-4a8b-a227-e0725292f843",
        "bot_instance_id": 1,
        "user_id": 7,
        "action_type": AnalyticsEventName.CONTENT_BLOCK_INTERACTION,
        "source_surface": SourceSurface.CATEGORY,
        "interaction_kind": ContentInteractionKind.FORM_CARD_OPEN,
        "category_id": 11,
        "content_version_id": 12,
        "block_id": "form-card-1",
        "form_template_id": 15,
    }
    values.update(overrides)
    return AnalyticsEvent(**values)


def test_content_event_requires_concrete_stable_block() -> None:
    event = _event()
    assert event.block_id == "form-card-1"
    assert event.form_template_id == 15

    with pytest.raises(InvalidAnalyticsEvent, match="block_id"):
        _event(block_id=None)


def test_capability_card_open_from_a_shortcut_tile_does_not_require_a_content_version() -> None:
    """A Task 044 capability shortcut tile fires this event from the category grid, not from
    inside a rendered content page/version -- unlike every other content_block_interaction kind,
    it has no content_version_id to report."""
    event = _event(
        interaction_kind=ContentInteractionKind.CAPABILITY_CARD_OPEN,
        content_version_id=None,
        form_template_id=None,
        capability_installation_id=3,
        capability_key="rut_schedule",
        capability_view_key="browse",
    )
    assert event.content_version_id is None
    assert event.category_id == 11

    with pytest.raises(InvalidAnalyticsEvent, match="block_id"):
        _event(
            interaction_kind=ContentInteractionKind.CAPABILITY_CARD_OPEN,
            content_version_id=None,
            block_id=None,
        )


def test_other_content_block_interactions_still_require_a_content_version() -> None:
    with pytest.raises(InvalidAnalyticsEvent, match="content_version_id"):
        _event(content_version_id=None)


def test_record_event_validates_context_before_idempotent_write() -> None:
    calls: list[str] = []

    class Repository:
        def validate_context(self, event: AnalyticsEvent) -> None:
            calls.append(f"validate:{event.bot_instance_id}")

        def add(self, event: AnalyticsEvent) -> bool:
            calls.append(f"add:{event.event_id}")
            return False

    created = RecordAnalyticsEvent(Repository()).execute(_event())
    assert created is False
    assert calls == [
        "validate:1",
        "add:a01f9091-a293-4f26-86a5-cc7feca04c7b",
    ]


def test_dashboard_calendar_period_is_moscow_and_previous_is_equal_length() -> None:
    period, previous = resolve_period(
        days=30,
        date_from=date(2026, 8, 14),
        date_to=date(2026, 8, 14),
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )
    assert period.start == datetime(2026, 8, 13, 21, tzinfo=UTC)
    assert period.end == datetime(2026, 8, 14, 21, tzinfo=UTC)
    assert previous.end == period.start
    assert previous.end - previous.start == period.end - period.start


def test_legacy_tab_event_resolves_readable_title_without_tabs_block_id() -> None:
    version = ContentVersionRecord(
        id=4,
        category_id=1,
        version=1,
        source_revision=1,
        title="Добро пожаловать",
        blocks=[
            {
                "id": "tabs_welcome",
                "type": "tabs",
                "tabs": [
                    {
                        "key": "tab_89c436843c49",
                        "title": "Информация",
                        "blocks": [],
                    }
                ],
            }
        ],
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )

    label, target = SqlAlchemyDashboardRepository._content_label(
        version,
        action_type=AnalyticsEventName.CONTENT_TAB_OPEN.value,
        interaction_kind=None,
        block_id=None,
        item_id=None,
        tabs_block_id=None,
        tab_key="tab_89c436843c49",
        attachment_id=None,
    )

    assert label == "Информация"
    assert target is None


def test_platform_dashboard_denies_non_platform_admin() -> None:
    principal = CurrentPrincipal(
        sub="admin:9",
        role="admin",
        system="max",
        user_id=None,
        admin_id=9,
    )
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_db] = lambda: None
    try:
        response = TestClient(app).get("/api/analytics/dashboard/platform")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403


def test_analytics_event_denies_token_from_another_bot() -> None:
    principal = CurrentPrincipal(
        sub="student:7",
        role="student",
        system="max",
        user_id=7,
        admin_id=None,
        bot_instance_id=1,
        bot_slug="one",
    )
    other_bot = BotInstance(id=2, slug="two", name="Bot two")
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[resolve_tenant] = lambda: other_bot
    app.dependency_overrides[get_db] = lambda: None
    try:
        response = TestClient(app).post(
            "/api/analytics/events",
            json={
                "event_id": "a01f9091-a293-4f26-86a5-cc7feca04c7b",
                "session_id": "7cc9f565-22c3-4a8b-a227-e0725292f843",
                "action_type": "app_open",
                "source_surface": "direct",
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
