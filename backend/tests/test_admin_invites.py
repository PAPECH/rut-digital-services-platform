from __future__ import annotations

from datetime import timedelta

import pytest

from app.modules.admin_invites.application.commands import (
    CreateAdminInviteCommand,
    RedeemAdminInviteCommand,
    RevokeAdminInviteCommand,
)
from app.modules.admin_invites.application.ports import InviteeInactive
from app.modules.admin_invites.application.use_cases import (
    AdminInviteInvalid,
    AdminInviteNotFound,
    CreateAdminInvite,
    RedeemAdminInvite,
    RevokeAdminInvite,
)
from app.modules.admin_invites.domain.entities import AdminInvite
from app.modules.admin_invites.domain.start_param import invite_start_param, parse_invite_token
from app.modules.bot_instances.domain.staff_access import StaffPermissions

from .admin_invites_fakes import (
    NOW,
    InMemoryInviteRepository,
    RecordingGrants,
    SequentialInviteCodec,
)


def _create(
    repository: InMemoryInviteRepository,
    codec: SequentialInviteCodec,
    *,
    kind: str = "bot_staff",
    bot_instance_id: int | None = 1,
    max_uses: int = 1,
    ttl_hours: int = 24,
):
    return CreateAdminInvite(repository, codec).execute(
        CreateAdminInviteCommand(
            kind=kind,  # type: ignore[arg-type]
            bot_instance_id=bot_instance_id,
            full_name="  Петров   Пётр ",
            staff_role="employee" if kind == "bot_staff" else None,
            permissions=StaffPermissions(can_manage_forms=True) if kind == "bot_staff" else None,
            ttl_hours=ttl_hours,
            max_uses=max_uses,
            created_by_admin_id=5,
        ),
        now=NOW,
    )


def _redeem(repository, codec, grants, raw_token: str, *, max_user_id: str = "max-7", now=NOW):
    return RedeemAdminInvite(repository, codec, grants).execute(
        RedeemAdminInviteCommand(raw_token=raw_token, max_user_id=max_user_id),
        now=now,
    )


def test_start_param_round_trip_and_rejects_garbage() -> None:
    token = "A" * 43
    assert parse_invite_token(invite_start_param(token)) == token
    assert len(invite_start_param(token)) <= 256
    assert parse_invite_token("admin_login") is None
    assert parse_invite_token("inv_short") is None
    assert parse_invite_token("inv_" + "a" * 20 + "!") is None
    assert parse_invite_token(None) is None


def test_invite_status_order() -> None:
    invite = AdminInvite(
        id=1,
        kind="platform",
        bot_instance_id=None,
        full_name="Иван",
        staff_role=None,
        permissions=None,
        max_uses=2,
        used_count=0,
        expires_at=NOW + timedelta(hours=1),
        created_by_admin_id=None,
    )
    assert invite.status(NOW) == "active"
    assert invite.status(NOW + timedelta(hours=1)) == "expired"
    exhausted = AdminInvite(**{**_fields(invite), "used_count": 2})
    assert exhausted.status(NOW) == "exhausted"
    revoked = AdminInvite(**{**_fields(invite), "used_count": 2, "revoked_at": NOW})
    assert revoked.status(NOW) == "revoked"


def _fields(invite: AdminInvite) -> dict:
    return {name: getattr(invite, name) for name in invite.__dataclass_fields__}


@pytest.mark.parametrize(
    "overrides",
    [
        {"kind": "platform", "bot_instance_id": 1},
        {"kind": "bot_staff", "bot_instance_id": None},
        {"max_uses": 0},
        {"max_uses": 101},
        {"full_name": "   "},
    ],
)
def test_invite_invariants(overrides: dict) -> None:
    base = {
        "id": None,
        "kind": "bot_staff",
        "bot_instance_id": 1,
        "full_name": "Иван",
        "staff_role": "employee",
        "permissions": StaffPermissions(),
        "max_uses": 1,
        "used_count": 0,
        "expires_at": NOW,
        "created_by_admin_id": None,
    }
    if overrides.get("kind") == "platform":
        base.update(staff_role=None, permissions=None)
    with pytest.raises(ValueError):
        AdminInvite(**{**base, **overrides})


def test_create_normalizes_name_and_stores_only_digest() -> None:
    repository, codec = InMemoryInviteRepository(), SequentialInviteCodec()

    created = _create(repository, codec, ttl_hours=48)

    assert created.invite.full_name == "Петров Пётр"
    assert created.invite.expires_at == NOW + timedelta(hours=48)
    assert list(repository.hashes) == [f"digest:{created.raw_token}"]


def test_create_rejects_out_of_range_ttl() -> None:
    with pytest.raises(ValueError):
        _create(InMemoryInviteRepository(), SequentialInviteCodec(), ttl_hours=721)


def test_redeem_bot_invite_grants_stored_bot_and_permissions() -> None:
    repository, codec, grants = InMemoryInviteRepository(), SequentialInviteCodec(), RecordingGrants()
    created = _create(repository, codec, bot_instance_id=3)

    redeemed = _redeem(repository, codec, grants, created.raw_token)

    assert grants.bot_staff == [
        (3, "max-7", "Петров Пётр", "employee", StaffPermissions(can_manage_forms=True))
    ]
    assert grants.platform == []
    assert redeemed.created is True
    assert redeemed.invite.used_count == 1


def test_redeem_platform_invite_uses_platform_grant() -> None:
    repository, codec, grants = InMemoryInviteRepository(), SequentialInviteCodec(), RecordingGrants()
    created = _create(repository, codec, kind="platform", bot_instance_id=None)

    _redeem(repository, codec, grants, created.raw_token)

    assert grants.platform == [("max-7", "Петров Пётр")]
    assert grants.bot_staff == []


def test_single_use_invite_cannot_be_redeemed_twice() -> None:
    repository, codec, grants = InMemoryInviteRepository(), SequentialInviteCodec(), RecordingGrants()
    created = _create(repository, codec)
    _redeem(repository, codec, grants, created.raw_token)

    with pytest.raises(AdminInviteInvalid):
        _redeem(repository, codec, grants, created.raw_token, max_user_id="max-8")

    assert len(grants.bot_staff) == 1


def test_multi_use_invite_serves_several_people_until_exhausted() -> None:
    repository, codec, grants = InMemoryInviteRepository(), SequentialInviteCodec(), RecordingGrants()
    created = _create(repository, codec, max_uses=2)

    _redeem(repository, codec, grants, created.raw_token, max_user_id="a")
    _redeem(repository, codec, grants, created.raw_token, max_user_id="b")
    with pytest.raises(AdminInviteInvalid):
        _redeem(repository, codec, grants, created.raw_token, max_user_id="c")


def test_expired_revoked_and_unknown_tokens_are_invalid() -> None:
    repository, codec, grants = InMemoryInviteRepository(), SequentialInviteCodec(), RecordingGrants()
    expired = _create(repository, codec, ttl_hours=1)
    revoked = _create(repository, codec)
    RevokeAdminInvite(repository).execute(
        RevokeAdminInviteCommand(invite_id=revoked.invite.id, kind="bot_staff", bot_instance_id=1),
        now=NOW,
    )

    for token, now in (
        (expired.raw_token, NOW + timedelta(hours=1)),
        (revoked.raw_token, NOW),
        ("unknown-token-value", NOW),
    ):
        with pytest.raises(AdminInviteInvalid):
            _redeem(repository, codec, grants, token, now=now)

    assert grants.bot_staff == []
    assert all(item.used_count == 0 for item in repository.items.values())


def test_inactive_invitee_does_not_consume_invite() -> None:
    repository, codec = InMemoryInviteRepository(), SequentialInviteCodec()
    grants = RecordingGrants(inactive={"max-7"})
    created = _create(repository, codec)

    with pytest.raises(InviteeInactive):
        _redeem(repository, codec, grants, created.raw_token)

    assert repository.items[created.invite.id].used_count == 0


def test_revoke_is_scoped_by_bot_and_kind() -> None:
    repository, codec = InMemoryInviteRepository(), SequentialInviteCodec()
    bot_invite = _create(repository, codec, bot_instance_id=1)
    platform_invite = _create(repository, codec, kind="platform", bot_instance_id=None)
    use_case = RevokeAdminInvite(repository)

    with pytest.raises(AdminInviteNotFound):
        use_case.execute(
            RevokeAdminInviteCommand(invite_id=bot_invite.invite.id, kind="bot_staff", bot_instance_id=2),
            now=NOW,
        )
    with pytest.raises(AdminInviteNotFound):
        use_case.execute(
            RevokeAdminInviteCommand(invite_id=platform_invite.invite.id, kind="bot_staff", bot_instance_id=1),
            now=NOW,
        )
    assert all(item.revoked_at is None for item in repository.items.values())


def test_revoke_is_idempotent() -> None:
    repository, codec = InMemoryInviteRepository(), SequentialInviteCodec()
    created = _create(repository, codec)
    command = RevokeAdminInviteCommand(invite_id=created.invite.id, kind="bot_staff", bot_instance_id=1)

    first = RevokeAdminInvite(repository).execute(command, now=NOW)
    second = RevokeAdminInvite(repository).execute(command, now=NOW + timedelta(hours=1))

    assert first.revoked_at == second.revoked_at == NOW
