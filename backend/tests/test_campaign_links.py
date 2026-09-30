from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.modules.campaign_links.application.use_cases import (
    CampaignLinkCodeTaken,
    CreateCampaignLink,
    DeleteCampaignLink,
    ListCampaignLinks,
    ListUnmatchedCampaignLinks,
    RecordAnonymousCampaignLinkOpen,
    RecordIdentifiedCampaignLinkOpen,
)
from app.modules.campaign_links.domain.entities import (
    CampaignLink,
    CampaignLinkCodeTooLongForBotTarget,
    CampaignLinkTarget,
    CampaignLinkTouch,
    InvalidCampaignLink,
    UnmatchedCodeSummary,
    UnmatchedOpenSource,
    build_deep_link,
    validate_code,
)
from app.modules.profiles.domain.entities import BotMembership


class InMemoryCampaignLinkRepository:
    def __init__(self) -> None:
        self._links: dict[int, CampaignLink] = {}
        self._next_id = 1
        self.opens: list[tuple[int, int, int]] = []  # (bot_instance_id, campaign_link_id, bot_membership_id)
        self.unmatched: list[tuple[int, str, UnmatchedOpenSource, datetime]] = []

    def add(self, link: CampaignLink) -> CampaignLink:
        link = CampaignLink(
            id=self._next_id,
            bot_instance_id=link.bot_instance_id,
            code=link.code,
            campaign=link.campaign,
            source=link.source,
            placement=link.placement,
            target=link.target,
            created_by_admin_id=link.created_by_admin_id,
            created_at=datetime.now(UTC),
        )
        self._links[link.id] = link
        self._next_id += 1
        return link

    def get(self, bot_instance_id: int, link_id: int) -> CampaignLink | None:
        link = self._links.get(link_id)
        if link is None or link.bot_instance_id != bot_instance_id:
            return None
        return link

    def get_by_code(self, bot_instance_id: int, code: str) -> CampaignLink | None:
        for link in self._links.values():
            if link.bot_instance_id == bot_instance_id and link.code == code and not link.is_deleted:
                return link
        return None

    def code_exists(self, bot_instance_id: int, code: str) -> bool:
        return self.get_by_code(bot_instance_id, code) is not None

    def list_for_bot(self, bot_instance_id: int) -> list[CampaignLink]:
        return [
            link
            for link in self._links.values()
            if link.bot_instance_id == bot_instance_id and not link.is_deleted
        ]

    def soft_delete(self, bot_instance_id: int, link_id: int) -> CampaignLink | None:
        link = self.get(bot_instance_id, link_id)
        if link is None or link.is_deleted:
            return None
        deleted = replace(link, deleted_at=datetime.now(UTC))
        self._links[link_id] = deleted
        return deleted

    def unique_open_counts(self, bot_instance_id: int, link_ids: list[int]) -> dict[int, int]:
        counts: dict[int, set[int]] = {}
        for bid, link_id, membership_id in self.opens:
            if bid == bot_instance_id and link_id in link_ids:
                counts.setdefault(link_id, set()).add(membership_id)
        return {link_id: len(members) for link_id, members in counts.items()}

    def record_open(
        self, bot_instance_id: int, code: str, *, touch: CampaignLinkTouch
    ) -> CampaignLink | None:
        link = self.get_by_code(bot_instance_id, code.strip())
        if link is None:
            return None
        now = datetime.now(UTC)
        if touch == CampaignLinkTouch.REPEAT:
            updated = replace(link, repeat_open_count=link.repeat_open_count + 1, last_opened_at=now)
        else:
            updated = replace(link, open_count=link.open_count + 1, last_opened_at=now)
        self._links[link.id] = updated
        return updated

    def record_identified_open(
        self, bot_instance_id: int, code: str, bot_membership_id: int
    ) -> CampaignLink | None:
        updated = self.record_open(bot_instance_id, code, touch=CampaignLinkTouch.FIRST)
        if updated is None:
            return None
        self.opens.append((bot_instance_id, updated.id, bot_membership_id))
        return updated

    def record_unmatched(
        self, bot_instance_id: int, code: str, *, event_source: UnmatchedOpenSource
    ) -> None:
        self.unmatched.append((bot_instance_id, code, event_source, datetime.now(UTC)))

    def list_unmatched(self, bot_instance_id: int) -> list[UnmatchedCodeSummary]:
        groups: dict[tuple[str, UnmatchedOpenSource], list[datetime]] = {}
        for bid, code, source, occurred_at in self.unmatched:
            if bid != bot_instance_id:
                continue
            groups.setdefault((code, source), []).append(occurred_at)
        return [
            UnmatchedCodeSummary(
                code=code, event_source=source, hit_count=len(times), last_seen_at=max(times)
            )
            for (code, source), times in groups.items()
        ]


class FakeProfileGateway:
    def __init__(self) -> None:
        self.memberships: dict[tuple[int, int], BotMembership] = {}
        self.source_calls: list[tuple[int, int, int]] = []

    def get_shared_profile(self, user_id: int):
        raise NotImplementedError

    def update_shared_profile(self, user_id: int, values: dict):
        raise NotImplementedError

    def get_membership(self, bot_instance_id: int, user_id: int) -> BotMembership | None:
        return self.memberships.get((bot_instance_id, user_id))

    def create_membership(self, membership: BotMembership) -> BotMembership:
        self.memberships[(membership.bot_instance_id, membership.user_id)] = membership
        return membership

    def update_membership_data(self, bot_instance_id: int, user_id: int, values: dict):
        raise NotImplementedError

    def set_membership_campaign_source(
        self, bot_instance_id: int, user_id: int, campaign_link_id: int
    ) -> None:
        self.source_calls.append((bot_instance_id, user_id, campaign_link_id))
        key = (bot_instance_id, user_id)
        membership = self.memberships[key]
        if membership.source_campaign_link_id is None:
            self.memberships[key] = replace(
                membership, source_campaign_link_id=campaign_link_id
            )


# --- domain: code validation ---


def test_code_rejects_invalid_charset() -> None:
    with pytest.raises(InvalidCampaignLink):
        validate_code("has spaces", CampaignLinkTarget.WEBAPP)
    with pytest.raises(InvalidCampaignLink):
        validate_code("has/slash", CampaignLinkTarget.WEBAPP)


def test_code_between_129_and_512_accepted_for_webapp_rejected_for_bot() -> None:
    code = "a" * 200
    assert validate_code(code, CampaignLinkTarget.WEBAPP) == code
    with pytest.raises(CampaignLinkCodeTooLongForBotTarget):
        validate_code(code, CampaignLinkTarget.BOT)


def test_code_over_512_rejected_for_both_targets() -> None:
    code = "a" * 513
    with pytest.raises(InvalidCampaignLink):
        validate_code(code, CampaignLinkTarget.WEBAPP)
    with pytest.raises(InvalidCampaignLink):
        validate_code(code, CampaignLinkTarget.BOT)


def test_deep_link_shape_per_target() -> None:
    assert build_deep_link("mybot", "abc", CampaignLinkTarget.WEBAPP) == (
        "https://max.ru/mybot?startapp=abc"
    )
    assert build_deep_link("mybot", "abc", CampaignLinkTarget.BOT) == (
        "https://max.ru/mybot?start=abc"
    )


# --- application: create / list / delete ---


def test_create_campaign_link_rejects_duplicate_code_for_same_bot() -> None:
    repository = InMemoryCampaignLinkRepository()
    use_case = CreateCampaignLink(repository)
    use_case.execute(
        bot_instance_id=1,
        code="promo1",
        campaign="fall",
        source="vk",
        placement="post",
        target=CampaignLinkTarget.WEBAPP,
        created_by_admin_id=None,
    )
    with pytest.raises(CampaignLinkCodeTaken):
        use_case.execute(
            bot_instance_id=1,
            code="promo1",
            campaign="fall",
            source="vk",
            placement="story",
            target=CampaignLinkTarget.WEBAPP,
            created_by_admin_id=None,
        )


def test_create_campaign_link_allows_same_code_on_different_bots() -> None:
    repository = InMemoryCampaignLinkRepository()
    use_case = CreateCampaignLink(repository)
    link_a = use_case.execute(
        bot_instance_id=1,
        code="promo1",
        campaign="fall",
        source="vk",
        placement="post",
        target=CampaignLinkTarget.WEBAPP,
        created_by_admin_id=None,
    )
    link_b = use_case.execute(
        bot_instance_id=2,
        code="promo1",
        campaign="fall",
        source="vk",
        placement="post",
        target=CampaignLinkTarget.WEBAPP,
        created_by_admin_id=None,
    )
    assert link_a.bot_instance_id != link_b.bot_instance_id
    assert link_a.code == link_b.code


def test_soft_deleted_link_code_is_reusable() -> None:
    repository = InMemoryCampaignLinkRepository()
    create = CreateCampaignLink(repository)
    link = create.execute(
        bot_instance_id=1,
        code="promo1",
        campaign="fall",
        source="vk",
        placement="post",
        target=CampaignLinkTarget.WEBAPP,
        created_by_admin_id=None,
    )
    DeleteCampaignLink(repository).execute(1, link.id)
    assert repository.list_for_bot(1) == []
    # code is free again for a new link
    new_link = create.execute(
        bot_instance_id=1,
        code="promo1",
        campaign="winter",
        source="vk",
        placement="post",
        target=CampaignLinkTarget.WEBAPP,
        created_by_admin_id=None,
    )
    assert new_link.id != link.id


def test_list_campaign_links_reports_unique_open_counts() -> None:
    repository = InMemoryCampaignLinkRepository()
    CreateCampaignLink(repository).execute(
        bot_instance_id=1,
        code="promo1",
        campaign="fall",
        source="vk",
        placement="post",
        target=CampaignLinkTarget.WEBAPP,
        created_by_admin_id=None,
    )
    gateway = FakeProfileGateway()
    gateway.create_membership(BotMembership(id=10, bot_instance_id=1, user_id=100))
    identified = RecordIdentifiedCampaignLinkOpen(repository, gateway)
    identified.execute(1, "promo1", user_id=100)
    identified.execute(1, "promo1", user_id=100)  # same member, opens twice

    pairs = ListCampaignLinks(repository).execute(1)
    assert len(pairs) == 1
    result_link, unique_count = pairs[0]
    assert result_link.open_count == 2
    assert unique_count == 1


# --- application: recording opens ---


def test_anonymous_open_increments_counter_without_identity() -> None:
    repository = InMemoryCampaignLinkRepository()
    CreateCampaignLink(repository).execute(
        bot_instance_id=1,
        code="qrcode1",
        campaign="fall",
        source="poster",
        placement="lobby",
        target=CampaignLinkTarget.BOT,
        created_by_admin_id=None,
    )
    RecordAnonymousCampaignLinkOpen(repository).execute(1, "qrcode1", CampaignLinkTouch.FIRST)
    link = repository.get_by_code(1, "qrcode1")
    assert link.open_count == 1
    assert link.repeat_open_count == 0
    assert repository.opens == []  # no identity ever recorded
    assert repository.unmatched == []


def test_anonymous_open_with_unknown_code_does_not_error() -> None:
    repository = InMemoryCampaignLinkRepository()
    RecordAnonymousCampaignLinkOpen(repository).execute(1, "does-not-exist", CampaignLinkTouch.FIRST)
    assert repository.list_for_bot(1) == []


# --- application: repeat opens and unmatched-code capture (Task 074) -----------------------


def test_repeat_touch_increments_repeat_counter_not_open_counter() -> None:
    repository = InMemoryCampaignLinkRepository()
    CreateCampaignLink(repository).execute(
        bot_instance_id=1,
        code="qrcode1",
        campaign="fall",
        source="poster",
        placement="lobby",
        target=CampaignLinkTarget.BOT,
        created_by_admin_id=None,
    )
    RecordAnonymousCampaignLinkOpen(repository).execute(1, "qrcode1", CampaignLinkTouch.FIRST)
    RecordAnonymousCampaignLinkOpen(repository).execute(1, "qrcode1", CampaignLinkTouch.REPEAT)
    RecordAnonymousCampaignLinkOpen(repository).execute(1, "qrcode1", CampaignLinkTouch.REPEAT)
    link = repository.get_by_code(1, "qrcode1")
    assert link.open_count == 1
    assert link.repeat_open_count == 2


def test_anonymous_open_with_well_formed_unknown_code_is_captured_as_unmatched() -> None:
    repository = InMemoryCampaignLinkRepository()
    RecordAnonymousCampaignLinkOpen(repository).execute(1, "unknown123", CampaignLinkTouch.FIRST)
    RecordAnonymousCampaignLinkOpen(repository).execute(1, "unknown123", CampaignLinkTouch.REPEAT)
    summaries = {(s.code, s.event_source): s.hit_count for s in ListUnmatchedCampaignLinks(repository).execute(1)}
    assert summaries[("unknown123", UnmatchedOpenSource.BOT_STARTED)] == 1
    assert summaries[("unknown123", UnmatchedOpenSource.BOT_REPEAT)] == 1


def test_anonymous_open_with_malformed_code_writes_nothing() -> None:
    repository = InMemoryCampaignLinkRepository()
    RecordAnonymousCampaignLinkOpen(repository).execute(1, "has spaces", CampaignLinkTouch.FIRST)
    assert repository.unmatched == []
    assert repository.list_for_bot(1) == []


def test_anonymous_open_with_oversized_bot_code_writes_nothing() -> None:
    repository = InMemoryCampaignLinkRepository()
    oversized = "a" * 129  # exceeds BOT_CODE_MAX_LENGTH (128); well-formed charset otherwise
    RecordAnonymousCampaignLinkOpen(repository).execute(1, oversized, CampaignLinkTouch.FIRST)
    assert repository.unmatched == []


def test_identified_open_with_well_formed_unknown_code_is_captured_as_unmatched() -> None:
    repository = InMemoryCampaignLinkRepository()
    gateway = FakeProfileGateway()
    gateway.create_membership(BotMembership(id=10, bot_instance_id=1, user_id=100))
    RecordIdentifiedCampaignLinkOpen(repository, gateway).execute(1, "unknown-code", user_id=100)
    summaries = ListUnmatchedCampaignLinks(repository).execute(1)
    assert len(summaries) == 1
    assert summaries[0].code == "unknown-code"
    assert summaries[0].event_source == UnmatchedOpenSource.WEBAPP
    assert gateway.source_calls == []  # no identity attached to the unmatched row


def test_unmatched_codes_are_cross_tenant_scoped() -> None:
    repository = InMemoryCampaignLinkRepository()
    RecordAnonymousCampaignLinkOpen(repository).execute(1, "shared-unknown", CampaignLinkTouch.FIRST)
    RecordAnonymousCampaignLinkOpen(repository).execute(2, "shared-unknown", CampaignLinkTouch.FIRST)
    bot_1_codes = ListUnmatchedCampaignLinks(repository).execute(1)
    bot_2_codes = ListUnmatchedCampaignLinks(repository).execute(2)
    assert len(bot_1_codes) == 1
    assert len(bot_2_codes) == 1


def test_identified_open_sets_first_touch_source_once() -> None:
    repository = InMemoryCampaignLinkRepository()
    link = CreateCampaignLink(repository).execute(
        bot_instance_id=1,
        code="promo1",
        campaign="fall",
        source="vk",
        placement="post",
        target=CampaignLinkTarget.WEBAPP,
        created_by_admin_id=None,
    )
    CreateCampaignLink(repository).execute(
        bot_instance_id=1,
        code="promo2",
        campaign="fall",
        source="vk",
        placement="story",
        target=CampaignLinkTarget.WEBAPP,
        created_by_admin_id=None,
    )
    gateway = FakeProfileGateway()
    gateway.create_membership(BotMembership(id=10, bot_instance_id=1, user_id=100))
    use_case = RecordIdentifiedCampaignLinkOpen(repository, gateway)

    use_case.execute(1, "promo1", user_id=100)
    membership = gateway.get_membership(1, 100)
    assert membership.source_campaign_link_id == link.id

    # opening a different link afterward must not overwrite first-touch source
    use_case.execute(1, "promo2", user_id=100)
    membership = gateway.get_membership(1, 100)
    assert membership.source_campaign_link_id == link.id
    assert repository.get_by_code(1, "promo2").open_count == 1  # still recorded as an open


def test_identified_open_with_unknown_code_is_ignored() -> None:
    repository = InMemoryCampaignLinkRepository()
    gateway = FakeProfileGateway()
    gateway.create_membership(BotMembership(id=10, bot_instance_id=1, user_id=100))
    RecordIdentifiedCampaignLinkOpen(repository, gateway).execute(1, "unknown", user_id=100)
    assert gateway.source_calls == []


def test_identified_open_without_membership_is_ignored() -> None:
    repository = InMemoryCampaignLinkRepository()
    CreateCampaignLink(repository).execute(
        bot_instance_id=1,
        code="promo1",
        campaign="fall",
        source="vk",
        placement="post",
        target=CampaignLinkTarget.WEBAPP,
        created_by_admin_id=None,
    )
    gateway = FakeProfileGateway()  # no membership registered
    RecordIdentifiedCampaignLinkOpen(repository, gateway).execute(1, "promo1", user_id=100)
    link = repository.get_by_code(1, "promo1")
    assert link.open_count == 0  # nothing recorded without a resolvable membership


def test_cross_tenant_open_does_not_resolve_other_bots_code() -> None:
    repository = InMemoryCampaignLinkRepository()
    CreateCampaignLink(repository).execute(
        bot_instance_id=1,
        code="shared-code",
        campaign="fall",
        source="vk",
        placement="post",
        target=CampaignLinkTarget.WEBAPP,
        created_by_admin_id=None,
    )
    gateway = FakeProfileGateway()
    gateway.create_membership(BotMembership(id=20, bot_instance_id=2, user_id=100))
    # Bot 2 has no campaign link with this code, even though bot 1 does.
    RecordIdentifiedCampaignLinkOpen(repository, gateway).execute(2, "shared-code", user_id=100)
    assert repository.get_by_code(1, "shared-code").open_count == 0
    assert repository.list_for_bot(2) == []
