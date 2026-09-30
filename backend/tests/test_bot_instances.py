from dataclasses import replace
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.modules.bot_instances.application.commands import (
    CreateBotInstanceCommand,
    UpdateBotInstanceCommand,
)
from app.modules.bot_instances.application.use_cases import (
    BotInstanceNotFound,
    BotSlugAlreadyExists,
    CreateBotInstance,
    DeleteBotInstance,
    ListBotInstances,
    ProfileDisabledWithGatedCapability,
    ProfileDisabledWithRequiredFields,
    RestoreBotInstance,
    UpdateBotInstance,
)
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.bot_instances.domain.profile_consistency import profile_disabled_with_required_fields
from app.modules.bot_instances.presentation.schemas import (
    BotInstancePatchRequest,
    BotSettings,
    ProfileFieldDefinition,
)


class InMemoryBotRepository:
    def __init__(self) -> None:
        self.items: dict[int, BotInstance] = {}

    def add(self, bot: BotInstance) -> BotInstance:
        stored = BotInstance(
            id=len(self.items) + 1,
            slug=bot.slug,
            name=bot.name,
            description=bot.description,
            is_active=bot.is_active,
            order=bot.order,
            branding=bot.branding,
            settings=bot.settings,
            profile_schema=bot.profile_schema,
        )
        assert stored.id is not None
        self.items[stored.id] = stored
        return stored

    def get(self, bot_id: int) -> BotInstance | None:
        return self.items.get(bot_id)

    def get_by_slug(self, slug: str) -> BotInstance | None:
        return next(
            (bot for bot in self.items.values() if bot.slug == slug and not bot.is_deleted),
            None,
        )

    def list_all(self, *, include_deleted: bool = False) -> list[BotInstance]:
        return [
            bot
            for bot in self.items.values()
            if include_deleted or not bot.is_deleted
        ]

    def update(self, bot: BotInstance) -> BotInstance:
        assert bot.id is not None
        self.items[bot.id] = bot
        return bot

    def soft_delete(self, bot_id: int) -> BotInstance:
        current = self.items[bot_id]
        updated = replace(current, deleted_at=datetime.now(tz=timezone.utc), is_active=False)
        self.items[bot_id] = updated
        return updated

    def restore(self, bot_id: int) -> BotInstance:
        current = self.items[bot_id]
        updated = replace(current, deleted_at=None)
        self.items[bot_id] = updated
        return updated


def test_create_bot_normalizes_slug_and_rejects_duplicate() -> None:
    repository = InMemoryBotRepository()
    use_case = CreateBotInstance(repository)

    created = use_case.execute(CreateBotInstanceCommand(slug="hr-bot", name="  Кадры  "))

    assert created.id == 1
    assert created.name == "Кадры"
    with pytest.raises(BotSlugAlreadyExists):
        use_case.execute(CreateBotInstanceCommand(slug="hr-bot", name="Дубликат"))


def test_bottom_navigation_has_typed_bounded_contract() -> None:
    valid = BotInstancePatchRequest(
        settings={
            "bottom_navigation": {
                "custom_items": [
                    {"category_slug": "contacts", "label": "Контакты", "icon": "contact"},
                ],
            },
        },
    )
    assert valid.settings is not None
    assert valid.settings.bottom_navigation.custom_items[0].category_slug == "contacts"
    assert valid.settings.bottom_navigation.custom_items[0].target == "category"
    assert valid.settings.submission_table.profile_fields == [
        "full_name",
        "phone",
        "email",
        "birth_date",
    ]

    with pytest.raises(ValidationError):
        BotInstancePatchRequest(
            settings={
                "bottom_navigation": {
                    "custom_items": [
                        {"category_slug": f"page-{index}", "label": "Раздел", "icon": "folder"}
                        for index in range(3)
                    ],
                },
            },
        )

    system = BotInstancePatchRequest(
        settings={
            "bottom_navigation": {
                "custom_items": [
                    {
                        "target": "submission_history",
                        "label": "Мои заявки",
                        "icon": "document",
                    },
                    {
                        "target": "form_catalog",
                        "label": "Формы",
                        "icon": "folder",
                    },
                ],
            },
        },
    )
    assert system.settings is not None
    assert system.settings.bottom_navigation.custom_items[0].category_slug is None

    with pytest.raises(ValidationError):
        BotInstancePatchRequest(
            settings={
                "bottom_navigation": {
                    "custom_items": [
                        {
                            "target": "submission_history",
                            "category_slug": "contacts",
                            "label": "Мои заявки",
                            "icon": "document",
                        },
                    ],
                },
            },
        )

    with pytest.raises(ValidationError):
        BotInstancePatchRequest(
            settings={
                "bottom_navigation": {
                    "custom_items": [
                        {"category_slug": "contacts", "label": "Контакты", "icon": "script"},
                    ],
                },
            },
        )


def test_submission_table_profile_fields_have_typed_unique_contract() -> None:
    valid = BotInstancePatchRequest(
        settings={
            "submission_table": {
                "profile_fields": ["full_name", "phone", "structural_unit"],
            },
        },
    )

    assert valid.settings is not None
    assert valid.settings.submission_table.profile_fields[-1] == "structural_unit"

    with pytest.raises(ValidationError):
        BotInstancePatchRequest(
            settings={
                "submission_table": {
                    "profile_fields": ["phone", "phone"],
                },
            },
        )

    with pytest.raises(ValidationError):
        BotInstancePatchRequest(
            settings={
                "submission_table": {
                    "profile_fields": ["invalid field"],
                },
            },
        )


def test_chat_and_knowledge_base_settings_default_to_todays_behavior() -> None:
    # No "chat"/"knowledge_base" section at all -- every existing bot's stored
    # settings JSON predates Task 049, so this must not change their behavior.
    defaults = BotInstancePatchRequest(settings={})
    assert defaults.settings is not None
    assert defaults.settings.chat.student_text_enabled is True
    assert defaults.settings.knowledge_base.auto_answer_threshold is None
    assert defaults.settings.knowledge_base.candidate_min_threshold is None
    assert defaults.settings.knowledge_base.max_candidates is None


def test_chat_settings_toggle_and_kb_threshold_overrides_have_typed_bounded_contract() -> None:
    valid = BotInstancePatchRequest(
        settings={
            "chat": {"student_text_enabled": False},
            "knowledge_base": {
                "auto_answer_threshold": 0.75,
                "candidate_min_threshold": 0.6,
                "max_candidates": 5,
            },
        },
    )
    assert valid.settings is not None
    assert valid.settings.chat.student_text_enabled is False
    assert valid.settings.knowledge_base.auto_answer_threshold == 0.75
    assert valid.settings.knowledge_base.candidate_min_threshold == 0.6
    assert valid.settings.knowledge_base.max_candidates == 5

    # candidate_min_threshold above auto_answer_threshold is a nonsensical config.
    with pytest.raises(ValidationError):
        BotInstancePatchRequest(
            settings={
                "knowledge_base": {
                    "auto_answer_threshold": 0.5,
                    "candidate_min_threshold": 0.9,
                },
            },
        )

    # Cosine-similarity thresholds are bounded to [0, 1].
    with pytest.raises(ValidationError):
        BotInstancePatchRequest(
            settings={"knowledge_base": {"auto_answer_threshold": 1.5}},
        )

    # Typed contract, not a JSON escape hatch: unknown keys are rejected.
    with pytest.raises(ValidationError):
        BotInstancePatchRequest(
            settings={"chat": {"student_text_enabled": True, "unexpected_field": 1}},
        )


def test_delete_hides_bot_and_stops_it_but_keeps_it_restorable() -> None:
    repository = InMemoryBotRepository()
    bot = CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(slug="hr-bot", name="Кадры")
    )
    assert bot.id is not None

    deleted = DeleteBotInstance(repository).execute(bot.id)
    assert deleted.is_deleted
    assert deleted.is_active is False

    assert ListBotInstances(repository).execute() == []
    assert [item.id for item in ListBotInstances(repository).execute(include_deleted=True)] == [bot.id]

    restored = RestoreBotInstance(repository).execute(bot.id)
    assert restored.is_deleted is False
    assert restored.is_active is False, "restore must not silently turn the bot back on"
    assert [item.id for item in ListBotInstances(repository).execute()] == [bot.id]


def test_deleted_bot_slug_can_be_reused_by_a_new_bot() -> None:
    repository = InMemoryBotRepository()
    original = CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(slug="hr-bot", name="Кадры")
    )
    assert original.id is not None
    DeleteBotInstance(repository).execute(original.id)

    recreated = CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(slug="hr-bot", name="Кадры (новый)")
    )
    assert recreated.id != original.id
    assert recreated.slug == "hr-bot"


def test_restore_rejects_when_a_new_bot_already_claimed_the_slug() -> None:
    repository = InMemoryBotRepository()
    original = CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(slug="hr-bot", name="Кадры")
    )
    assert original.id is not None
    DeleteBotInstance(repository).execute(original.id)
    CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(slug="hr-bot", name="Кадры (новый)")
    )

    with pytest.raises(BotSlugAlreadyExists):
        RestoreBotInstance(repository).execute(original.id)


def test_delete_and_restore_reject_unknown_bot() -> None:
    repository = InMemoryBotRepository()
    with pytest.raises(BotInstanceNotFound):
        DeleteBotInstance(repository).execute(999)
    with pytest.raises(BotInstanceNotFound):
        RestoreBotInstance(repository).execute(999)


def test_update_rejects_a_deleted_bot_until_restored() -> None:
    repository = InMemoryBotRepository()
    bot = CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(slug="hr-bot", name="Кадры")
    )
    assert bot.id is not None
    DeleteBotInstance(repository).execute(bot.id)

    with pytest.raises(BotInstanceNotFound):
        UpdateBotInstance(repository).execute(
            UpdateBotInstanceCommand(bot_id=bot.id, name="Новое имя")
        )

    RestoreBotInstance(repository).execute(bot.id)
    updated = UpdateBotInstance(repository).execute(
        UpdateBotInstanceCommand(bot_id=bot.id, name="Новое имя")
    )
    assert updated.name == "Новое имя"


def test_profile_field_rejects_core_key() -> None:
    with pytest.raises(ValidationError):
        ProfileFieldDefinition(key="phone", label="Телефон")


@pytest.mark.parametrize("key", ["study_group", "job_title", "structural_unit"])
def test_profile_field_rejects_direct_optional_key_without_shared_flag(key: str) -> None:
    # These keys always route to the shared User column regardless of `shared`
    # (see DIRECT_OPTIONAL_PROFILE_KEYS) — declaring shared: false would be a lie
    # about actual routing behavior, so it must be rejected up front.
    with pytest.raises(ValidationError):
        ProfileFieldDefinition(key=key, label="Тест", shared=False)


@pytest.mark.parametrize("key", ["study_group", "job_title", "structural_unit"])
def test_profile_field_accepts_direct_optional_key_with_shared_flag(key: str) -> None:
    field = ProfileFieldDefinition(key=key, label="Тест", shared=True)
    assert field.key == key


# --- Task 054: configurable profile tab -------------------------------------------------


def test_profile_settings_default_to_todays_behavior() -> None:
    # No "profile" section at all -- every existing bot's stored settings JSON predates
    # Task 054, so the tab must stay shown, matching today's hardcoded-on behavior.
    defaults = BotInstancePatchRequest(settings={})
    assert defaults.settings is not None
    assert defaults.settings.profile.enabled is True


def test_profile_settings_have_typed_bounded_contract() -> None:
    valid = BotSettings(profile={"enabled": False})
    assert valid.profile.enabled is False

    with pytest.raises(ValidationError):
        BotSettings(profile={"enabled": False, "unexpected_field": 1})


def test_profile_disabled_with_required_fields_is_pure_and_bidirectional() -> None:
    enabled_settings = {"profile": {"enabled": True}}
    disabled_settings = {"profile": {"enabled": False}}
    no_required = [{"key": "bio", "required": False}]
    has_required = [{"key": "bio", "required": True}]

    assert profile_disabled_with_required_fields(enabled_settings, has_required) is False
    assert profile_disabled_with_required_fields(disabled_settings, no_required) is False
    assert profile_disabled_with_required_fields(disabled_settings, has_required) is True
    # Missing "profile" key entirely (pre-Task-054 stored settings) defaults to enabled.
    assert profile_disabled_with_required_fields({}, has_required) is False


def test_update_bot_instance_rejects_disabling_profile_with_a_required_field() -> None:
    repository = InMemoryBotRepository()
    bot = CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(
            slug="school-bot",
            name="Школьный бот",
            profile_schema=[{"key": "bio", "label": "О себе", "required": True}],
        )
    )
    assert bot.id is not None

    with pytest.raises(ProfileDisabledWithRequiredFields):
        UpdateBotInstance(repository).execute(
            UpdateBotInstanceCommand(bot_id=bot.id, settings={"profile": {"enabled": False}})
        )


def test_update_bot_instance_rejects_adding_a_required_field_while_profile_disabled() -> None:
    repository = InMemoryBotRepository()
    bot = CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(
            slug="school-bot-2",
            name="Школьный бот 2",
            settings={"profile": {"enabled": False}},
        )
    )
    assert bot.id is not None

    with pytest.raises(ProfileDisabledWithRequiredFields):
        UpdateBotInstance(repository).execute(
            UpdateBotInstanceCommand(
                bot_id=bot.id,
                profile_schema=[{"key": "bio", "label": "О себе", "required": True}],
            )
        )


def test_create_bot_instance_rejects_profile_disabled_with_required_field_up_front() -> None:
    repository = InMemoryBotRepository()
    with pytest.raises(ProfileDisabledWithRequiredFields):
        CreateBotInstance(repository).execute(
            CreateBotInstanceCommand(
                slug="bad-bot",
                name="Плохой бот",
                settings={"profile": {"enabled": False}},
                profile_schema=[{"key": "bio", "label": "О себе", "required": True}],
            )
        )


def test_update_bot_instance_allows_disabling_profile_when_nothing_requires_it() -> None:
    repository = InMemoryBotRepository()
    bot = CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(slug="simple-bot", name="Простой бот")
    )
    assert bot.id is not None

    updated = UpdateBotInstance(repository).execute(
        UpdateBotInstanceCommand(bot_id=bot.id, settings={"profile": {"enabled": False}})
    )
    assert updated.settings["profile"]["enabled"] is False


def test_update_bot_instance_rejects_disabling_profile_with_a_gated_capability() -> None:
    repository = InMemoryBotRepository()
    bot = CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(slug="gated-bot", name="Бот с capability")
    )
    assert bot.id is not None

    use_case = UpdateBotInstance(repository, has_profile_gated_capability=lambda _bot_id: True)
    with pytest.raises(ProfileDisabledWithGatedCapability):
        use_case.execute(
            UpdateBotInstanceCommand(bot_id=bot.id, settings={"profile": {"enabled": False}})
        )


def test_update_bot_instance_without_injected_checker_never_blocks_on_capabilities() -> None:
    # The callable defaults to "never gated" -- callers that don't care about capabilities
    # (or don't pass one) must not be blocked by this half of the validation.
    repository = InMemoryBotRepository()
    bot = CreateBotInstance(repository).execute(
        CreateBotInstanceCommand(slug="uninjected-bot", name="Бот без проверки")
    )
    assert bot.id is not None

    updated = UpdateBotInstance(repository).execute(
        UpdateBotInstanceCommand(bot_id=bot.id, settings={"profile": {"enabled": False}})
    )
    assert updated.settings["profile"]["enabled"] is False
