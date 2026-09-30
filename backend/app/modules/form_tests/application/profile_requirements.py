from __future__ import annotations

from ...profiles.domain.entities import SharedProfile
from ...profiles.domain.requirements import find_missing_required_fields


def find_missing_test_participation_fields(profile: SharedProfile) -> list[str]:
    """`form_tests`-only requirement layered on top of the platform's shared profile-completeness
    check (Task 080): birth date and email must also be present to start or resume a test, since
    the anketa no longer asks for them as separate questions -- they're sourced from the profile
    instead. Deliberately does not touch `profiles.domain.requirements.CORE_REQUIREMENTS`, which
    `modules/forms` also relies on and which must keep both fields optional there -- confirmed
    with the requester that this stricter requirement is `form_tests`-only."""
    missing = find_missing_required_fields(profile, schema=[])
    if not profile.birth_date:
        missing.append("Дата рождения")
    if not (profile.email and profile.email.strip()):
        missing.append("Email")
    return missing
