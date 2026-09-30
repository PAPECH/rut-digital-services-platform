from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ....models.enums import SystemEnum
from ..domain.entities import ConsentState


class ConsentBotIdentityIn(BaseModel):
    """Body for the bot-channel consent endpoints -- MAX identity only, bot-runtime
    authenticated the same way /messages/ingress is. Does not create a `User` row (see
    ConsentGate on messages_router.py / auth_router.py for where that happens)."""

    user_id: str
    system: SystemEnum


class ConsentStatusOut(BaseModel):
    is_active: bool
    given_at: datetime | None = None
    revoked_at: datetime | None = None
    deletion_due_at: datetime | None = None
    deleted_at: datetime | None = None
    policy_version: str | None = None
    policy_url: str

    @classmethod
    def from_state(cls, state: ConsentState | None, *, policy_url: str) -> "ConsentStatusOut":
        if state is None:
            return cls(is_active=False, policy_url=policy_url)
        return cls(
            is_active=state.is_active,
            given_at=state.given_at,
            revoked_at=state.revoked_at,
            deletion_due_at=state.deletion_due_at,
            deleted_at=state.deleted_at,
            policy_version=state.policy_version,
            policy_url=policy_url,
        )


class ConsentEventOut(BaseModel):
    event_type: str
    occurred_at: datetime
    policy_version: str | None = None


class ErasureRegisterEntryOut(BaseModel):
    external_user_id: str
    system: str
    given_at: datetime | None = None
    revoked_at: datetime | None = None
    deleted_at: datetime | None = None
    events: list[ConsentEventOut]


class ConsentNoticeOut(BaseModel):
    key: str
    value: str | None = None


class ConsentNoticeIn(BaseModel):
    value: str


class PolicyDocumentHtmlIn(BaseModel):
    """The full policy document, as admin-authored HTML rendered on our own page
    (GET /consent/policy-document) -- same request/response shape both ways, mirrors
    ConsentNoticeIn."""

    value: str


class PolicyDocumentContentOut(BaseModel):
    """Public read of the raw HTML (no page shell), for the mini-app's in-app policy screen.
    `None` when unset, mirrors ConsentNoticeOut."""

    value: str | None = None
