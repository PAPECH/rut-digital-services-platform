from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.main import app
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.forms.application.submission_attachments import ResolveSubmissionAttachmentFields
from app.modules.forms.domain.entities import FormDefinition, FormVersion, PublishedForm
from app.modules.forms.domain.submission_attachments import submission_attachment_fields
from app.modules.maintenance.presentation.dependencies import enforce_user_access_available
from app.modules.tenancy.presentation.dependencies import resolve_tenant


class _NoAccessResult:
    def scalar_one_or_none(self) -> None:
        return None

    def one_or_none(self) -> None:
        return None


class _NoAccessSession:
    def execute(self, _query: object) -> _NoAccessResult:
        return _NoAccessResult()


class _ScalarResult:
    def __init__(self, *, scalar: object | None = None, rows: list[object] | None = None) -> None:
        self._scalar = scalar
        self._rows = rows or []

    def scalar_one_or_none(self) -> object | None:
        return self._scalar

    def scalars(self) -> list[object]:
        return self._rows


class _SubmissionAttachmentSession:
    def __init__(self, submission: object, attachments: list[object]) -> None:
        self.submission = submission
        self.attachments = attachments
        self.calls = 0

    def execute(self, _query: object) -> _ScalarResult:
        self.calls += 1
        if self.calls == 1:
            return _ScalarResult(scalar=self.submission)
        return _ScalarResult(rows=self.attachments)


class _VersionRepository:
    def get_version(self, bot_instance_id: int, form_id: int, version_id: int):
        if (bot_instance_id, form_id, version_id) != (7, 20, 31):
            return None
        return PublishedForm(
            definition=FormDefinition(
                id=20,
                bot_instance_id=7,
                slug="legacy-form",
            ),
            version=FormVersion(
                id=31,
                form_definition_id=20,
                version=1,
                source_revision=1,
                name="Legacy form",
                description=None,
                reply_on_accept=None,
                fields=[{"key": "photo", "type": "file"}],
                published_by=None,
                published_at=datetime.now(tz=UTC),
            ),
        )


def test_only_file_fields_from_published_snapshot_expose_attachments() -> None:
    snapshot = {
        "fields": [
            {"key": "documents", "type": "file"},
            {"key": "comment", "type": "long_text"},
        ],
    }
    values = {
        "documents": [12, 15, True, -1, "18"],
        "comment": [99],
        "injected": [100],
    }

    assert submission_attachment_fields(snapshot, values) == {
        12: "documents",
        15: "documents",
    }


def test_attachment_fields_fall_back_to_same_tenant_immutable_form_version() -> None:
    resolver = ResolveSubmissionAttachmentFields(_VersionRepository())

    result = resolver.execute(
        bot_instance_id=7,
        form_id=20,
        version_id=31,
        form_snapshot={"name": "Legacy form"},
        values={"photo": [44]},
    )
    cross_tenant = resolver.execute(
        bot_instance_id=8,
        form_id=20,
        version_id=31,
        form_snapshot={"name": "Legacy form"},
        values={"photo": [44]},
    )

    assert result == {44: "photo"}
    assert cross_tenant == {}


def test_staff_without_tenant_access_cannot_list_submission_attachments() -> None:
    selected_bot = BotInstance(id=2, slug="other", name="Other")
    principal = CurrentPrincipal(
        sub="a:7",
        role="admin",
        system=None,
        user_id=None,
        admin_id=7,
    )
    app.dependency_overrides[resolve_tenant] = lambda: selected_bot
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_db] = _NoAccessSession
    try:
        response = TestClient(app).get("/api/submissions/10/attachments")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "tenant_access_denied"


def test_submission_owner_can_list_own_attachments() -> None:
    selected_bot = BotInstance(id=7, slug="hr", name="HR")
    principal = CurrentPrincipal(
        sub="u:17",
        role="student",
        system="max",
        user_id=17,
        admin_id=None,
        bot_instance_id=7,
        bot_slug="hr",
    )
    submission = SimpleNamespace(
        id=10,
        user_id=17,
        form_template_id=20,
        form_version_id=31,
        form_snapshot={"fields": [{"key": "photo", "type": "file"}]},
        values={"photo": [5]},
    )
    attachment = SimpleNamespace(
        id=5,
        original_name="photo.jpg",
        mime="image/jpeg",
        size_bytes=123,
    )
    session = _SubmissionAttachmentSession(submission, [attachment])
    app.dependency_overrides[resolve_tenant] = lambda: selected_bot
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[enforce_user_access_available] = lambda: None
    try:
        response = TestClient(app).get("/api/submissions/10/attachments")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 5,
            "field_key": "photo",
            "name": "photo.jpg",
            "mime": "image/jpeg",
            "size_bytes": 123,
            "preview_url": "/submissions/10/attachments/5",
            "download_url": "/submissions/10/attachments/5?download=true",
        },
    ]


def test_student_cannot_list_another_users_submission_attachments() -> None:
    selected_bot = BotInstance(id=7, slug="hr", name="HR")
    principal = CurrentPrincipal(
        sub="u:18",
        role="student",
        system="max",
        user_id=18,
        admin_id=None,
        bot_instance_id=7,
        bot_slug="hr",
    )
    submission = SimpleNamespace(id=10, user_id=17)
    session = _SubmissionAttachmentSession(submission, [])
    app.dependency_overrides[resolve_tenant] = lambda: selected_bot
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[enforce_user_access_available] = lambda: None
    try:
        response = TestClient(app).get("/api/submissions/10/attachments")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert session.calls == 1


def test_student_cannot_list_submission_attachments_in_another_bot() -> None:
    selected_bot = BotInstance(id=7, slug="hr", name="HR")
    principal = CurrentPrincipal(
        sub="u:17",
        role="student",
        system="max",
        user_id=17,
        admin_id=None,
        bot_instance_id=8,
        bot_slug="other",
    )
    app.dependency_overrides[resolve_tenant] = lambda: selected_bot
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[enforce_user_access_available] = lambda: None
    try:
        response = TestClient(app).get("/api/submissions/10/attachments")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "tenant_mismatch"
