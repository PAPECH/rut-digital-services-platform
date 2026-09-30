from __future__ import annotations

from typing import Any

from .entities import SharedProfile

_IDENTITY_KEYS = {"external_user_id", "max_user_id", "max_id", "provider", "user_id"}


def build_submission_profile_snapshot(
    profile: SharedProfile,
    local_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the profile state that was used when a form was submitted.

    Provider identifiers are deliberately excluded: a submission needs the
    business profile values, not another copy of the MAX identity binding.
    """

    return {
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "patronymic": profile.patronymic,
        "phone": profile.phone,
        "phone_verified": profile.phone_verified,
        "email": profile.email,
        "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
        "job_title": profile.job_title,
        "structural_unit": profile.structural_unit,
        "shared_data": {
            key: value for key, value in profile.shared_data.items() if key not in _IDENTITY_KEYS
        },
        "bot_local_data": dict(local_data or {}),
    }
