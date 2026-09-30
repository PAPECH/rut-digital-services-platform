from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..domain.entities import ContentCategory, ContentDraft

FormDependencyStatus = Literal[
    "resolved",
    "copy_available",
    "mapping_required",
    "unavailable",
]
FormResolutionAction = Literal["use_existing", "copy_shared"]


@dataclass(frozen=True, slots=True)
class FormDependencyTarget:
    id: int
    slug: str
    label: str


@dataclass(frozen=True, slots=True)
class FormDependency:
    source_id: int
    source_slug: str | None
    label: str
    status: FormDependencyStatus
    source_is_shared: bool
    matched_target_id: int | None = None
    matched_target_ready: bool = False


@dataclass(frozen=True, slots=True)
class DependencyBlocker:
    kind: Literal["file"]
    code: Literal["file_copy_not_supported"]
    count: int


@dataclass(frozen=True, slots=True)
class SharedContentDependencyReport:
    form_dependencies: list[FormDependency] = field(default_factory=list)
    form_targets: list[FormDependencyTarget] = field(default_factory=list)
    blockers: list[DependencyBlocker] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FormDependencyResolution:
    source_id: int
    action: FormResolutionAction
    target_id: int | None = None


@dataclass(frozen=True, slots=True)
class ResolvedFormDependency:
    source_id: int
    target_id: int
    action: Literal["matched_slug", "use_existing", "copy_shared"]
    target_ready: bool


@dataclass(frozen=True, slots=True)
class ContentDependencyResolutionResult:
    blocks: list[dict]
    form_dependencies: list[ResolvedFormDependency] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SharedContentImportResult:
    category: ContentCategory
    draft: ContentDraft
    form_dependencies: list[ResolvedFormDependency] = field(default_factory=list)


class ContentDependencyResolutionInvalid(RuntimeError):
    pass


class ContentDependencyCopyForbidden(RuntimeError):
    pass
