from datetime import date

from app.modules.profiles.domain.entities import SharedProfile
from app.modules.profiles.domain.snapshots import build_submission_profile_snapshot


def test_submission_profile_snapshot_is_serializable_and_excludes_identity_binding() -> None:
    snapshot = build_submission_profile_snapshot(
        SharedProfile(
            user_id=7,
            external_user_id="max-secret-id",
            provider="max",
            first_name="Анна",
            birth_date=date(2000, 1, 2),
            shared_data={
                "personnel_number": "123",
                "provider": "max",
                "external_user_id": "duplicate-secret",
            },
        )
    )
    assert snapshot["birth_date"] == "2000-01-02"
    assert snapshot["shared_data"] == {"personnel_number": "123"}
    assert "external_user_id" not in snapshot
    assert "provider" not in snapshot
    assert "provider" not in snapshot["shared_data"]
    assert "external_user_id" not in snapshot["shared_data"]
