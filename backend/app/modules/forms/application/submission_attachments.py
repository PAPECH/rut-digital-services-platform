from __future__ import annotations

from typing import Any, Mapping

from ..domain.repositories import FormRepository
from ..domain.submission_attachments import submission_attachment_fields


class ResolveSubmissionAttachmentFields:
    """Resolve file fields from the immutable snapshot, with a version fallback.

    The fallback keeps submissions created during the additive migration readable
    without ever consulting a mutable form draft or another tenant's version.
    """

    def __init__(self, forms: FormRepository) -> None:
        self._forms = forms

    def execute(
        self,
        *,
        bot_instance_id: int,
        form_id: int,
        version_id: int,
        form_snapshot: Mapping[str, Any],
        values: Mapping[str, Any],
    ) -> dict[int, str]:
        resolved = submission_attachment_fields(form_snapshot, values)
        if resolved:
            return resolved
        published = self._forms.get_version(bot_instance_id, form_id, version_id)
        if published is None:
            return {}
        return submission_attachment_fields(
            {"fields": published.version.fields},
            values,
        )
