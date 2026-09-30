from typing import Protocol

from ..domain.entities import (
    ContentAttachmentPage,
    ContentFormOption,
    ContentTestOption,
    DeletedAttachment,
)
from .dependencies import (
    ContentDependencyResolutionResult,
    FormDependencyResolution,
    SharedContentDependencyReport,
)


class ContentReferenceGateway(Protocol):
    def missing_form_ids(self, bot_instance_id: int, form_ids: set[int]) -> set[int]: ...

    def unready_form_ids(self, bot_instance_id: int, form_ids: set[int]) -> set[int]: ...

    def missing_test_ids(self, bot_instance_id: int, test_ids: set[int]) -> set[int]: ...

    def unready_test_ids(self, bot_instance_id: int, test_ids: set[int]) -> set[int]: ...

    def missing_attachment_ids(
        self,
        bot_instance_id: int,
        attachment_ids: set[int],
    ) -> set[int]: ...

    def attachment_mime_types(
        self,
        bot_instance_id: int,
        attachment_ids: set[int],
    ) -> dict[int, str]: ...

    def missing_capability_views(
        self,
        bot_instance_id: int,
        references: set[tuple[str, str]],
    ) -> set[tuple[str, str]]: ...


class ContentAssetCatalog(Protocol):
    def list_admin_attachments(
        self,
        bot_instance_id: int,
        *,
        limit: int,
        offset: int,
        mime_family: str | None = None,
        search: str | None = None,
    ) -> ContentAttachmentPage: ...

    def delete_admin_attachment(self, bot_instance_id: int, attachment_id: int) -> DeletedAttachment: ...

    def list_published_forms(self, bot_instance_id: int) -> list[ContentFormOption]: ...

    def list_published_tests(self, bot_instance_id: int) -> list[ContentTestOption]: ...


class ContentTemplateDependencyGateway(Protocol):
    def inspect(
        self,
        *,
        source_bot_instance_id: int,
        target_bot_instance_id: int,
        blocks: list[dict],
    ) -> SharedContentDependencyReport: ...

    def resolve(
        self,
        *,
        source_bot_instance_id: int,
        target_bot_instance_id: int,
        blocks: list[dict],
        form_resolutions: tuple[FormDependencyResolution, ...],
        created_by: int | None,
    ) -> ContentDependencyResolutionResult: ...


class ContentAnalyticsGateway(Protocol):
    def record_category_open(
        self,
        *,
        bot_instance_id: int,
        user_id: int,
        category_id: int,
        version_id: int,
    ) -> None: ...

    def record_tab_open(
        self,
        *,
        bot_instance_id: int,
        user_id: int,
        category_id: int,
        version_id: int,
        tab_key: str,
    ) -> None: ...
