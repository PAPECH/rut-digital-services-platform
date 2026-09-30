from __future__ import annotations


class InvalidSyncRequest(ValueError):
    def __init__(self, message: str, *, path: str = "scope") -> None:
        super().__init__(message)
        self.path = path


def validate_manual_sync_scope(
    scope: str,
    group_external_id: str | None,
    institute_external_id: str | None,
    known_group_external_ids: set[str],
    known_institute_external_ids: set[str],
) -> None:
    """Pure validation for a manual-sync request's scope (Task 045/follow-up) -- no I/O, so the
    "known group"/"known institute" sets are passed in already resolved rather than looked up
    here. Exactly one of `group_external_id`/`institute_external_id` may be set, and only for the
    matching scope -- "либо институт целиком, либо конкретная группа" (either a whole institute,
    or one specific group), never both at once."""
    if scope not in ("group", "institute", "all"):
        raise InvalidSyncRequest("scope must be 'group', 'institute' or 'all'", path="scope")

    if scope == "group":
        if not group_external_id:
            raise InvalidSyncRequest(
                "group_external_id is required when scope='group'", path="group_external_id"
            )
        if group_external_id not in known_group_external_ids:
            raise InvalidSyncRequest("Unknown group_external_id", path="group_external_id")
        if institute_external_id:
            raise InvalidSyncRequest(
                "institute_external_id must not be set when scope='group'",
                path="institute_external_id",
            )
    elif scope == "institute":
        if not institute_external_id:
            raise InvalidSyncRequest(
                "institute_external_id is required when scope='institute'",
                path="institute_external_id",
            )
        if institute_external_id not in known_institute_external_ids:
            raise InvalidSyncRequest("Unknown institute_external_id", path="institute_external_id")
        if group_external_id:
            raise InvalidSyncRequest(
                "group_external_id must not be set when scope='institute'", path="group_external_id"
            )
    else:
        if group_external_id:
            raise InvalidSyncRequest(
                "group_external_id must not be set when scope='all'", path="group_external_id"
            )
        if institute_external_id:
            raise InvalidSyncRequest(
                "institute_external_id must not be set when scope='all'", path="institute_external_id"
            )
