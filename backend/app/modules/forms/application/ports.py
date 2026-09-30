from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AttachmentDescriptor:
    id: int
    bot_instance_id: int
    uploaded_by_user_id: int | None
    mime: str
    size_bytes: int


class FormAttachmentGateway(Protocol):
    def get_attachments(self, attachment_ids: set[int]) -> dict[int, AttachmentDescriptor]: ...
