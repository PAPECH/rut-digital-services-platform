from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.content.domain.entities import ContentCategory
from app.modules.content.infrastructure.repositories import (
    SqlAlchemyContentRepository,
    _sync_attachment_references,
)


@dataclass
class _FakeCategoryRecord:
    """Mirrors the real (mutable) attribute set of ContentCategoryRecord -- no `is_filled`,
    which lives only on ContentDraftRecord/ContentVersionRecord. `title`/`subtitle`/`image_url`
    are the Task 044 capability-shortcut card fields (unused/None for an ordinary category)."""

    id: int
    bot_instance_id: int
    slug: str
    icon: str
    parent_id: int | None
    order: int
    is_active: bool
    published_version_id: int | None
    last_published_revision: int
    is_home: bool
    capability_key: str | None = None
    capability_view_key: str | None = None
    title: str | None = None
    subtitle: str | None = None
    image_url: str | None = None


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one(self) -> object:
        return self._value


class _FakeSession:
    def __init__(self, record: _FakeCategoryRecord) -> None:
        self._record = record

    def execute(self, _stmt: object) -> _ScalarResult:
        return _ScalarResult(self._record)

    def flush(self) -> None:
        pass


def test_update_category_does_not_read_draft_only_fields_off_the_domain_entity() -> None:
    """Regression test: `update_category` used to do `record.is_filled = category.is_filled`
    and `record.image_url = category.image_url`, but `ContentCategory` has neither field (they
    belong to `ContentDraft`) -- every category PATCH crashed with AttributeError."""
    record = _FakeCategoryRecord(
        id=1,
        bot_instance_id=3,
        slug="priemnaya-komissiya",
        icon="folder",
        parent_id=None,
        order=1,
        is_active=True,
        published_version_id=None,
        last_published_revision=0,
        is_home=False,
    )
    repository = SqlAlchemyContentRepository(_FakeSession(record))
    category = ContentCategory(
        id=1,
        bot_instance_id=3,
        slug="priemnaya-komissiya",
        icon="star",
        parent_id=None,
        order=1,
        is_active=False,
        published_version_id=None,
        last_published_revision=0,
        is_home=False,
    )

    updated = repository.update_category(category)

    assert updated.is_active is False
    assert updated.icon == "star"
    assert record.is_active is False
    assert record.icon == "star"


@dataclass
class _RecordingSession:
    """Records `add()` calls and no-ops everything else -- enough to exercise
    `_sync_attachment_references`'s pure "replace this scope's rows" logic without a real DB."""

    added: list = field(default_factory=list)
    executed: list = field(default_factory=list)

    def execute(self, stmt: object) -> None:
        self.executed.append(stmt)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        pass


def test_sync_attachment_references_records_file_list_and_card_image_usages() -> None:
    """Regression coverage for Task 025's reference table: a `file_list` item and the category's
    own `image_url` must both produce rows, and an attachment used both ways collapses to two
    distinct (attachment_id, usage) rows rather than being deduplicated away entirely."""
    session = _RecordingSession()
    blocks = [
        {
            "id": "files",
            "type": "file_list",
            "items": [
                {"attachment_id": 5, "title": "Заявление", "display_mode": "tile"},
                {"attachment_id": 6, "title": "Фото", "display_mode": "inline_image"},
            ],
        }
    ]

    _sync_attachment_references(
        session,
        bot_instance_id=1,
        category_id=10,
        scope="draft",
        blocks=blocks,
        image_url="/api/files/5?exp=-1&sig=abc",
    )

    usages = {(row.attachment_id, row.usage) for row in session.added}
    assert usages == {(5, "file_list_item"), (6, "file_list_item"), (5, "card_image")}
    assert all(row.scope == "draft" for row in session.added)
    assert all(row.category_id == 10 for row in session.added)
    assert all(row.bot_instance_id == 1 for row in session.added)
    # The scope's existing rows are cleared before the fresh set is inserted -- exactly one
    # DELETE precedes the batch of adds.
    assert len(session.executed) == 1


def test_sync_attachment_references_with_no_references_only_clears_the_scope() -> None:
    session = _RecordingSession()

    _sync_attachment_references(
        session,
        bot_instance_id=1,
        category_id=10,
        scope="published",
        blocks=[],
        image_url=None,
    )

    assert session.added == []
    assert len(session.executed) == 1
