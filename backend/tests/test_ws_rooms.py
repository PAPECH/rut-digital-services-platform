from app.services.ws_hub import platform_admin_room, staff_room, user_room


def test_form_realtime_rooms_are_tenant_scoped() -> None:
    assert staff_room(1) != staff_room(2)
    assert user_room(7, 1) != user_room(7, 2)
    assert staff_room(1) == "staff:bot:1"
    assert user_room(7, 1) == "user:bot:1:7"


def test_platform_admin_room_is_tenant_scoped_and_distinct_from_staff_room() -> None:
    """See Task 045: rut_schedule manual-sync events must reach only platform admins, never a
    bot admin connected to the (broader) staff_room for the same bot."""
    assert platform_admin_room(1) != platform_admin_room(2)
    assert platform_admin_room(1) != staff_room(1)
    assert platform_admin_room(1) == "platform_admin:bot:1"
