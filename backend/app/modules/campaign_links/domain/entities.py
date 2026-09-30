from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

_CODE_RE = re.compile(r"^[A-Za-z0-9_-]+$")
WEBAPP_CODE_MAX_LENGTH = 512
BOT_CODE_MAX_LENGTH = 128


class CampaignLinkTarget(StrEnum):
    BOT = "bot"
    WEBAPP = "webapp"


class CampaignLinkTouch(StrEnum):
    """Distinguishes a `target: bot` open report's origin (Task 074): `FIRST` is MAX's
    `bot_started` update (fires once, on a person's very first ever contact with the bot);
    `REPEAT` is a plain `/start <code>` text message from someone who has already contacted the
    bot before, which MAX delivers identically to any other message -- previously silently
    dropped by `on_start`, now reported and counted separately."""

    FIRST = "first"
    REPEAT = "repeat"


class UnmatchedOpenSource(StrEnum):
    """Which open-report surface/touch produced a well-formed but unresolvable code (Task 074)."""

    BOT_STARTED = "bot_started"
    BOT_REPEAT = "bot_repeat"
    WEBAPP = "webapp"


class InvalidCampaignLink(ValueError):
    pass


class CampaignLinkCodeTooLongForBotTarget(InvalidCampaignLink):
    pass


def validate_code(code: str, target: CampaignLinkTarget) -> str:
    normalized = code.strip()
    if not normalized:
        raise InvalidCampaignLink("Code cannot be empty")
    if not _CODE_RE.fullmatch(normalized):
        raise InvalidCampaignLink(
            "Code may only contain letters, digits, '_' and '-'",
        )
    limit = BOT_CODE_MAX_LENGTH if target == CampaignLinkTarget.BOT else WEBAPP_CODE_MAX_LENGTH
    if len(normalized) > limit:
        if target == CampaignLinkTarget.BOT:
            raise CampaignLinkCodeTooLongForBotTarget(
                f"Code exceeds {BOT_CODE_MAX_LENGTH} characters allowed for target=bot",
            )
        raise InvalidCampaignLink(
            f"Code exceeds {WEBAPP_CODE_MAX_LENGTH} characters allowed for target=webapp",
        )
    return normalized


@dataclass(frozen=True, slots=True)
class CampaignLink:
    id: int | None
    bot_instance_id: int
    code: str
    campaign: str
    source: str
    placement: str
    target: CampaignLinkTarget
    created_by_admin_id: int | None
    created_at: datetime | None = None
    open_count: int = 0
    # Meaningful only for `target: bot` rows -- a `target: webapp` row's value stays 0 forever,
    # since that path's own counting is untouched by Task 074. `open_count` keeps its existing
    # meaning unchanged for both targets (see Task 074's Data and migration impact).
    repeat_open_count: int = 0
    last_opened_at: datetime | None = None
    deleted_at: datetime | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __post_init__(self) -> None:
        normalized_code = validate_code(self.code, self.target)
        object.__setattr__(self, "code", normalized_code)
        for label_field in ("campaign", "source", "placement"):
            value = getattr(self, label_field).strip()
            if not value:
                raise InvalidCampaignLink(f"{label_field} cannot be empty")
            object.__setattr__(self, label_field, value)


MAX_WEB_BASE_URL = "https://max.ru"


def build_deep_link(bot_username: str, code: str, target: CampaignLinkTarget) -> str:
    param = "startapp" if target == CampaignLinkTarget.WEBAPP else "start"
    return f"{MAX_WEB_BASE_URL}/{bot_username}?{param}={code}"


@dataclass(frozen=True, slots=True)
class UnmatchedCodeSummary:
    """One (code, event_source) group from `campaign_link_unmatched_opens` (Task 074) -- the raw,
    un-decomposed code exactly as received, never parsed into campaign/source/placement (see
    Task 074's Non-goals)."""

    code: str
    event_source: UnmatchedOpenSource
    hit_count: int
    last_seen_at: datetime
