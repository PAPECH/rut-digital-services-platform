from __future__ import annotations

from typing import Protocol

from .entities import CampaignLink, CampaignLinkTouch, UnmatchedCodeSummary, UnmatchedOpenSource


class CampaignLinkRepository(Protocol):
    def add(self, link: CampaignLink) -> CampaignLink: ...

    def get(self, bot_instance_id: int, link_id: int) -> CampaignLink | None: ...

    def get_by_code(self, bot_instance_id: int, code: str) -> CampaignLink | None: ...

    def code_exists(self, bot_instance_id: int, code: str) -> bool: ...

    def list_for_bot(self, bot_instance_id: int) -> list[CampaignLink]: ...

    def soft_delete(self, bot_instance_id: int, link_id: int) -> CampaignLink | None: ...

    def unique_open_counts(self, bot_instance_id: int, link_ids: list[int]) -> dict[int, int]:
        """Lifetime COUNT(DISTINCT bot_membership_id) per link, from campaign_link_opens."""
        ...

    def record_open(
        self, bot_instance_id: int, code: str, *, touch: CampaignLinkTouch
    ) -> CampaignLink | None:
        """Increment open_count (touch=first) or repeat_open_count (touch=repeat), plus
        last_opened_at either way. Returns None for an unknown/deleted code (no counters touched)."""
        ...

    def record_identified_open(
        self,
        bot_instance_id: int,
        code: str,
        bot_membership_id: int,
    ) -> CampaignLink | None:
        """Increment open_count/last_opened_at and insert one campaign_link_opens row.

        Returns None for an unknown/deleted code (no counters touched).
        """
        ...

    # --- Unmatched-code capture (Task 074) --------------------------------------------------

    def record_unmatched(
        self, bot_instance_id: int, code: str, *, event_source: UnmatchedOpenSource
    ) -> None:
        """Append one row for a well-formed code that did not resolve to a non-deleted campaign
        link for this bot. Never raises, never deduplicates -- one row per occurrence."""
        ...

    def list_unmatched(self, bot_instance_id: int) -> list[UnmatchedCodeSummary]:
        """Lifetime, grouped by (code, event_source) -- mirrors `list_for_bot`'s own lifetime,
        unfiltered convention rather than introducing a new period-filtering shape just for this
        endpoint (the dashboard's own period-scoped unmatched count is a separate read, computed
        directly against this same table)."""
        ...
