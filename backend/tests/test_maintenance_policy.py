from datetime import datetime, timedelta, timezone

from app.modules.maintenance.domain.policies import (
    MaintenanceMode,
    MaintenancePolicy,
    resolve_effective_policy,
)


def test_global_maintenance_has_priority_over_bot_policy() -> None:
    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    global_policy = MaintenancePolicy(
        scope_key="global",
        bot_instance_id=None,
        mode=MaintenanceMode.informational,
    )
    bot_policy = MaintenancePolicy(
        scope_key="bot:2",
        bot_instance_id=2,
        mode=MaintenanceMode.full_stop,
    )

    assert resolve_effective_policy(global_policy, bot_policy, now=now) == global_policy


def test_scheduled_policy_is_effective_only_inside_window() -> None:
    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    policy = MaintenancePolicy(
        scope_key="bot:2",
        bot_instance_id=2,
        mode=MaintenanceMode.read_only,
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
    )

    assert not policy.is_effective(now)
    assert policy.is_effective(now + timedelta(hours=1, minutes=1))
    assert not policy.is_effective(now + timedelta(hours=2))
    assert policy.blocks_user_writes
    assert not policy.blocks_user_access
