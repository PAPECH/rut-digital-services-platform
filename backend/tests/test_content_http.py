from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, require_student
from app.db.session import get_db
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.content.application.use_cases import ContentAttachmentInUse, ContentAttachmentNotFound
from app.modules.content.domain.entities import (
    AttachmentReference,
    ContentAttachment,
    ContentAttachmentPage,
    ContentCategory,
    ContentDraft,
    ContentTestOption,
    ContentVersion,
    DeletedAttachment,
    PublishedContent,
)
from app.modules.content.presentation.dependencies import (
    ContentManagerContext,
    require_content_manager,
)
from app.modules.content.presentation.router import router
from app.modules.maintenance.presentation.dependencies import enforce_user_access_available
from app.modules.tenancy.presentation.dependencies import require_tenant_access
from app.services.content_preview_tokens import make_preview_token


class FakeAttachmentCatalog:
    def __init__(
        self,
        *,
        expected_bot_id: int = 2,
        page: ContentAttachmentPage | None = None,
        delete_result: DeletedAttachment | None = None,
        delete_error: Exception | None = None,
        tests: list[ContentTestOption] | None = None,
    ) -> None:
        self._expected_bot_id = expected_bot_id
        self._page = page
        self._delete_result = delete_result
        self._delete_error = delete_error
        self._tests = tests if tests is not None else []
        self.delete_calls: list[tuple[int, int]] = []

    def list_admin_attachments(self, bot_instance_id: int, *, limit, offset, mime_family=None, search=None):
        assert bot_instance_id == self._expected_bot_id
        return self._page

    def delete_admin_attachment(self, bot_instance_id: int, attachment_id: int):
        assert bot_instance_id == self._expected_bot_id
        self.delete_calls.append((bot_instance_id, attachment_id))
        if self._delete_error is not None:
            raise self._delete_error
        return self._delete_result

    def list_published_tests(self, bot_instance_id: int) -> list[ContentTestOption]:
        assert bot_instance_id == self._expected_bot_id
        return self._tests


class TenantScopedDraftRepository:
    def get_draft(self, bot_instance_id: int, category_id: int):
        # Category 41 belongs to bot 1 and must look absent from bot 2.
        assert bot_instance_id == 2
        assert category_id == 41


class TenantScopedCatalogRepository:
    def list_published(self, bot_instance_id: int):
        assert bot_instance_id == 2
        return []


class DummySession:
    def rollback(self) -> None:
        pass

    def commit(self) -> None:
        pass


class RecordingSession(DummySession):
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


def _principal(*, bot_instance_id: int) -> CurrentPrincipal:
    return CurrentPrincipal(
        sub="u:17",
        role="student",
        system="max",
        user_id=17,
        admin_id=None,
        bot_instance_id=bot_instance_id,
        bot_slug=f"bot-{bot_instance_id}",
    )


def test_admin_category_from_another_bot_is_hidden_at_http_boundary(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/content")
    bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    admin = CurrentPrincipal(
        sub="a:5",
        role="platform_admin",
        system="max",
        user_id=None,
        admin_id=5,
        bot_instance_id=None,
    )
    app.dependency_overrides[require_content_manager] = lambda: ContentManagerContext(bot, admin)
    app.dependency_overrides[get_db] = lambda: DummySession()
    router_module = import_module("app.modules.content.presentation.router")
    monkeypatch.setattr(
        router_module,
        "SqlAlchemyContentRepository",
        lambda _: TenantScopedDraftRepository(),
    )

    response = TestClient(app).get("/content/admin/categories/41/draft")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "content_not_found"


def test_content_analytics_rejects_free_form_or_personal_metadata() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/content")
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app.dependency_overrides[require_student] = lambda: _principal(bot_instance_id=1)
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[enforce_user_access_available] = lambda: None
    app.dependency_overrides[get_db] = lambda: DummySession()

    response = TestClient(app).post(
        "/content/events/category-open",
        json={
            "category_id": 3,
            "version_id": 8,
            "name": "Иван Иванов",
            "description": "Произвольный текст",
        },
    )

    assert response.status_code == 422


def test_shared_content_import_rejects_untyped_or_ambiguous_resolution() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/content")
    bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    admin = CurrentPrincipal(
        sub="a:5",
        role="platform_admin",
        system="max",
        user_id=None,
        admin_id=5,
        bot_instance_id=None,
    )
    app.dependency_overrides[require_content_manager] = lambda: ContentManagerContext(bot, admin)
    app.dependency_overrides[get_db] = lambda: DummySession()

    response = TestClient(app).post(
        "/content/admin/shared-drafts/4/import",
        json={
            "slug": "copy-page",
            "parent_id": None,
            "order": 0,
            "resolutions": [
                {
                    "kind": "form",
                    "source_id": 9,
                    "action": "copy_shared",
                    "target_id": 12,
                }
            ],
        },
    )

    assert response.status_code == 422


def test_published_catalog_is_scoped_to_resolved_tenant(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/content")
    bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[enforce_user_access_available] = lambda: None
    app.dependency_overrides[get_db] = lambda: DummySession()
    router_module = import_module("app.modules.content.presentation.router")
    monkeypatch.setattr(
        router_module,
        "SqlAlchemyContentRepository",
        lambda _: TenantScopedCatalogRepository(),
    )

    response = TestClient(app).get("/content/catalog")

    assert response.status_code == 200
    assert response.json() == []


def test_direct_navigation_to_a_shortcut_slug_returns_a_stable_404_not_a_500(monkeypatch) -> None:
    """Regression test: `_raise_content_error`'s `ContentIsCapabilityShortcut` branch called
    `not_found(..., capability_key=..., view_key=...)`, but `not_found()` didn't accept `**extra`
    kwargs (unlike `bad_request`/`conflict`/`service_unavailable`) -- every direct navigation to a
    shortcut's own slug crashed with an unhandled 500 instead of the documented, stable 404. Only
    caught by exercising the real router (a use-case-level test can't see this class of bug)."""
    app = FastAPI()
    app.include_router(router, prefix="/content")
    bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[enforce_user_access_available] = lambda: None
    app.dependency_overrides[get_db] = lambda: DummySession()

    shortcut = ContentCategory(
        id=42,
        bot_instance_id=2,
        slug="schedule-shortcut",
        icon="calendar",
        capability_key="rut_schedule",
        capability_view_key="browse",
        title="Расписание",
    )

    class ShortcutSlugRepository:
        def get_published_by_slug(self, bot_instance_id: int, slug: str):
            return None

        def get_category_by_slug(self, bot_instance_id: int, slug: str):
            assert bot_instance_id == 2
            assert slug == "schedule-shortcut"
            return shortcut

    router_module = import_module("app.modules.content.presentation.router")
    monkeypatch.setattr(
        router_module,
        "SqlAlchemyContentRepository",
        lambda _: ShortcutSlugRepository(),
    )

    response = TestClient(app).get("/content/categories/schedule-shortcut")

    assert response.status_code == 404
    body = response.json()["detail"]
    assert body["code"] == "content_is_capability_shortcut"
    assert body["capability_key"] == "rut_schedule"
    assert body["view_key"] == "browse"


def test_home_category_resolves_only_for_the_tenant_that_owns_it(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/content")
    bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[enforce_user_access_available] = lambda: None
    app.dependency_overrides[get_db] = lambda: DummySession()

    home_category = ContentCategory(
        id=99,
        bot_instance_id=2,
        slug="system-home-screen",
        icon="home",
        is_home=True,
        published_version_id=7,
        last_published_revision=1,
    )
    published = PublishedContent(
        category=home_category,
        version=ContentVersion(
            id=7,
            category_id=99,
            version=1,
            source_revision=1,
            title="Главный экран",
            subtitle="Добро пожаловать!",
            language="ru",
            blocks=[],
            is_filled=False,
            image_url=None,
            header_visible=True,
            published_by=None,
            published_at=datetime.now(tz=UTC),
        ),
    )

    class HomeCategoryRepository:
        def get_home_category(self, bot_instance_id: int):
            # The handler must always ask for *this resolved tenant's* home category, never a
            # client-supplied bot id -- asserting the argument here is the actual tenant-scoping
            # guarantee under test.
            assert bot_instance_id == 2
            return home_category

        def get_draft(self, bot_instance_id: int, category_id: int):
            assert bot_instance_id == 2
            assert category_id == 99
            return published.version  # unused field-for-field by the handler; presence is enough

        def get_published_by_category(self, bot_instance_id: int, category_id: int):
            assert bot_instance_id == 2
            assert category_id == 99
            return published

    router_module = import_module("app.modules.content.presentation.router")
    monkeypatch.setattr(
        router_module,
        "SqlAlchemyContentRepository",
        lambda _: HomeCategoryRepository(),
    )

    response = TestClient(app).get("/content/categories/home")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 99
    assert body["title"] == "Главный экран"
    assert body["header_visible"] is True


def test_resolve_content_preview_builds_a_valid_response(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/content")
    app.dependency_overrides[get_db] = lambda: DummySession()

    category = ContentCategory(id=99, bot_instance_id=2, slug="system-home-screen", icon="home", is_home=True)
    draft = ContentDraft(
        category_id=99,
        title="Главный экран",
        subtitle="Добро пожаловать!",
        blocks=[],
        revision=3,
        header_visible=False,
    )

    class PreviewRepository:
        def get_category(self, bot_instance_id: int, category_id: int):
            assert bot_instance_id == 2
            assert category_id == 99
            return category

        def get_draft(self, bot_instance_id: int, category_id: int):
            assert bot_instance_id == 2
            assert category_id == 99
            return draft

    router_module = import_module("app.modules.content.presentation.router")
    monkeypatch.setattr(router_module, "SqlAlchemyContentRepository", lambda _: PreviewRepository())
    monkeypatch.setattr(router_module, "get_available_bot_slug", lambda _db, _bid: "bot-2")

    token, _ = make_preview_token(bot_instance_id=2, category_id=99)
    response = TestClient(app).get(f"/content/preview/{token}")

    assert response.status_code == 200
    assert response.json()["bot_slug"] == "bot-2"
    body = response.json()["content"]
    assert body["id"] == 99
    assert body["title"] == "Главный экран"
    assert body["header_visible"] is False


def test_user_token_for_another_bot_is_denied_before_content_read() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/content")
    bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    principal = _principal(bot_instance_id=1)

    app.dependency_overrides[require_tenant_access] = lambda: require_tenant_access(
        bot=bot, principal=principal, db=None
    )
    app.dependency_overrides[get_db] = lambda: DummySession()

    response = TestClient(app).get("/content/categories")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "tenant_mismatch"


def test_user_token_for_another_bot_is_denied_before_catalog_read() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/content")
    bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    principal = _principal(bot_instance_id=1)

    app.dependency_overrides[enforce_user_access_available] = lambda: None
    app.dependency_overrides[require_tenant_access] = lambda: require_tenant_access(
        bot=bot, principal=principal, db=None
    )
    app.dependency_overrides[get_db] = lambda: DummySession()

    response = TestClient(app).get("/content/catalog")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "tenant_mismatch"


def _content_manager_app(catalog: FakeAttachmentCatalog, *, db=None) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/content")
    bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    admin = CurrentPrincipal(
        sub="a:5",
        role="platform_admin",
        system="max",
        user_id=None,
        admin_id=5,
        bot_instance_id=None,
    )
    app.dependency_overrides[require_content_manager] = lambda: ContentManagerContext(bot, admin)
    app.dependency_overrides[get_db] = lambda: db if db is not None else DummySession()
    router_module = import_module("app.modules.content.presentation.router")
    router_module.SqlAlchemyContentAssetCatalog = lambda _: catalog
    return TestClient(app)


def test_list_admin_attachments_returns_paginated_items_with_references_and_permanent_urls() -> None:
    page = ContentAttachmentPage(
        items=[
            ContentAttachment(
                id=9,
                name="hero.png",
                mime="image/png",
                size_bytes=1024,
                created_at=datetime(2026, 8, 21, tzinfo=UTC),
                referenced_by_draft=(AttachmentReference(category_id=3, usage="card_image"),),
                referenced_by_published=(),
            )
        ],
        total=1,
    )
    client = _content_manager_app(FakeAttachmentCatalog(page=page))

    response = client.get("/content/admin/attachments")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == 9
    assert item["referenced_by_draft"] == [{"category_id": 3, "usage": "card_image"}]
    assert item["referenced_by_published"] == []
    # ttl_seconds=-1 -> exp=-1 in the signed URL: content attachments never expire (Task 025).
    assert "exp=-1" in item["url"]


def test_list_admin_tests_returns_only_the_resolved_bots_tests() -> None:
    """Regression test (Task 070): `GET /content/admin/tests` backs the `test_action` block
    editor's picker the same way `/content/admin/forms` backs `form_action`'s -- the catalog
    method already scopes by the resolved `bot_instance_id`, asserted here at the HTTP boundary."""
    client = _content_manager_app(
        FakeAttachmentCatalog(tests=[ContentTestOption(id=9, name="СПТ 2026")])
    )

    response = client.get("/content/admin/tests")

    assert response.status_code == 200
    assert response.json() == [{"id": 9, "name": "СПТ 2026"}]


def test_delete_admin_attachment_succeeds_and_writes_an_audit_entry() -> None:
    catalog = FakeAttachmentCatalog(
        delete_result=DeletedAttachment(id=9, name="instruction.pdf", mime="application/pdf", size_bytes=2048)
    )
    session = RecordingSession()
    client = _content_manager_app(catalog, db=session)

    response = client.delete("/content/admin/attachments/9")

    assert response.status_code == 204
    assert catalog.delete_calls == [(2, 9)]
    assert len(session.added) == 1
    audit = session.added[0]
    assert audit.meta["action"] == "content_attachment_deleted"
    assert audit.meta["attachment_id"] == 9
    assert audit.meta["bot_instance_id"] == 2


def test_delete_admin_attachment_in_use_by_published_content_returns_409() -> None:
    catalog = FakeAttachmentCatalog(delete_error=ContentAttachmentInUse([7, 8]))
    client = _content_manager_app(catalog)

    response = client.delete("/content/admin/attachments/9")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "content_attachment_in_use"
    assert detail["category_ids"] == [7, 8]


def test_delete_admin_attachment_from_another_bot_is_404() -> None:
    catalog = FakeAttachmentCatalog(delete_error=ContentAttachmentNotFound("9"))
    client = _content_manager_app(catalog)

    response = client.delete("/content/admin/attachments/9")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "content_attachment_not_found"
