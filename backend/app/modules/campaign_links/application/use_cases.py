from __future__ import annotations

from ...profiles.application.ports import ProfileGateway
from ..domain.entities import (
    CampaignLink,
    CampaignLinkTarget,
    CampaignLinkTouch,
    InvalidCampaignLink,
    UnmatchedCodeSummary,
    UnmatchedOpenSource,
    validate_code,
)
from ..domain.repositories import CampaignLinkRepository

_BOT_TOUCH_EVENT_SOURCE = {
    CampaignLinkTouch.FIRST: UnmatchedOpenSource.BOT_STARTED,
    CampaignLinkTouch.REPEAT: UnmatchedOpenSource.BOT_REPEAT,
}


class CampaignLinkCodeTaken(ValueError):
    pass


class CreateCampaignLink:
    def __init__(self, repository: CampaignLinkRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        bot_instance_id: int,
        code: str,
        campaign: str,
        source: str,
        placement: str,
        target: CampaignLinkTarget,
        created_by_admin_id: int | None,
    ) -> CampaignLink:
        link = CampaignLink(
            id=None,
            bot_instance_id=bot_instance_id,
            code=code,
            campaign=campaign,
            source=source,
            placement=placement,
            target=target,
            created_by_admin_id=created_by_admin_id,
        )
        if self._repository.code_exists(bot_instance_id, link.code):
            raise CampaignLinkCodeTaken(link.code)
        return self._repository.add(link)


class ListCampaignLinks:
    def __init__(self, repository: CampaignLinkRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[tuple[CampaignLink, int]]:
        links = self._repository.list_for_bot(bot_instance_id)
        unique_counts = self._repository.unique_open_counts(
            bot_instance_id, [link.id for link in links if link.id is not None]
        )
        return [(link, unique_counts.get(link.id or 0, 0)) for link in links]


class DeleteCampaignLink:
    def __init__(self, repository: CampaignLinkRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, link_id: int) -> CampaignLink | None:
        return self._repository.soft_delete(bot_instance_id, link_id)


class RecordAnonymousCampaignLinkOpen:
    """target: bot — bare counter increment, no identity resolved or stored (Task 026), now
    split by `touch` (Task 074): `FIRST` bumps `open_count` (unchanged meaning), `REPEAT` bumps
    the new `repeat_open_count`. A well-formed code that doesn't resolve is captured into
    `campaign_link_unmatched_opens` instead of vanishing silently; a malformed/oversized one is
    still dropped with no row written anywhere, exactly as before this task."""

    def __init__(self, repository: CampaignLinkRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, code: str, touch: CampaignLinkTouch) -> None:
        try:
            validated = validate_code(code, CampaignLinkTarget.BOT)
        except InvalidCampaignLink:
            return
        link = self._repository.record_open(bot_instance_id, validated, touch=touch)
        if link is None:
            self._repository.record_unmatched(
                bot_instance_id, validated, event_source=_BOT_TOUCH_EVENT_SOURCE[touch]
            )


class RecordIdentifiedCampaignLinkOpen:
    """target: webapp — resolves the caller's existing membership, sets first-touch source
    (Task 026). A well-formed, unresolved code is captured into
    `campaign_link_unmatched_opens` (Task 074) with no identity attached, mirroring the same
    silent-drop fix as the anonymous bot-touch path -- see that class's docstring."""

    def __init__(
        self,
        repository: CampaignLinkRepository,
        profile_gateway: ProfileGateway,
    ) -> None:
        self._repository = repository
        self._profile_gateway = profile_gateway

    def execute(self, bot_instance_id: int, code: str, user_id: int) -> None:
        try:
            validated = validate_code(code, CampaignLinkTarget.WEBAPP)
        except InvalidCampaignLink:
            return
        membership = self._profile_gateway.get_membership(bot_instance_id, user_id)
        if membership is None or membership.id is None:
            return
        link = self._repository.record_identified_open(
            bot_instance_id, validated, membership.id
        )
        if link is None:
            self._repository.record_unmatched(
                bot_instance_id, validated, event_source=UnmatchedOpenSource.WEBAPP
            )
            return
        if link.id is None:
            return
        self._profile_gateway.set_membership_campaign_source(
            bot_instance_id, user_id, link.id
        )


class ListUnmatchedCampaignLinks:
    def __init__(self, repository: CampaignLinkRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[UnmatchedCodeSummary]:
        return self._repository.list_unmatched(bot_instance_id)
