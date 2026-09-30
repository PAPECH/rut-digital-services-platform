from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.config import settings
from .models import ConsentNoticeRecord

# Platform-wide (not per-bot) admin-editable text, all stored as extra rows in this same
# key/value table -- app_settings (bot_instances module) hard-requires a bot_instance_id and
# is deliberately not reused here since consent (and its prompt/policy text) is the same
# across every bot. "ru"/"en" are the consent-prompt notice text (see router.py); the policy
# document itself is a single value regardless of language (Task 066's own scope decision --
# see docs/tasks/066), holding the full document as admin-authored HTML, rendered on our own
# page rather than linking to an external URL or an uploaded file (both tried and dropped in
# the same session -- see render_policy_document_page's docstring for why).
POLICY_DOCUMENT_HTML_KEY = "policy_document_html"


class SqlAlchemyConsentNoticeRepository:
    """Thin CRUD, same shape as bot_instances' SqlAlchemySettingRepository -- no use-case
    layer on top since there's no behavior here beyond read/upsert of a text blob."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, key: str) -> str | None:
        record = self._session.get(ConsentNoticeRecord, key)
        return record.value if record else None

    def list_all(self) -> dict[str, str]:
        rows = self._session.execute(select(ConsentNoticeRecord)).scalars()
        return {row.key: row.value for row in rows}

    def upsert(self, key: str, value: str) -> str:
        record = self._session.get(ConsentNoticeRecord, key)
        if record is None:
            record = ConsentNoticeRecord(key=key, value=value)
            self._session.add(record)
        else:
            record.value = value
        self._session.flush()
        return record.value

    def delete(self, key: str) -> None:
        record = self._session.get(ConsentNoticeRecord, key)
        if record is not None:
            self._session.delete(record)
            self._session.flush()


def effective_policy_url() -> str:
    """The URL every consent surface (bot chat, mini-app gate, support-chat fallback) should
    link to -- always our own rendered policy-document page (GET /consent/policy-document),
    never an external URL or an uploaded file. Always absolute (PUBLIC_API_URL-prefixed),
    unlike other attachment URLs in this codebase (relative, same-origin via proxy -- fine
    inside a webview): this value is also embedded directly into bot chat messages
    (bot/app/main.py) with no browser/origin context to resolve a relative path against, and
    a real address-bar navigation (not a WebView-opened "_blank" tab) is exactly what's needed
    for the page to render at all -- see render_policy_document_page's docstring.
    """
    return f"{settings.PUBLIC_API_URL}/api/consent/policy-document"


_PAGE_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Положение о работе с персональными данными</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    max-width: 720px;
    margin: 0 auto;
    padding: 24px 16px 48px;
    line-height: 1.55;
    color: #1a1a1a;
  }}
  a {{ color: #2563eb; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""

_EMPTY_PLACEHOLDER = "<p>Документ ещё не заполнен администратором платформы.</p>"


def render_policy_document_page(html: str | None) -> str:
    """Wraps the admin-authored HTML (policy_document_html) into a standalone page.

    An earlier iteration of this same feature linked to an external URL, then to an uploaded
    file served from our own storage -- both dropped: a browser needs a correct Content-Type
    to render an uploaded file, and MAX's own in-app "_blank" target didn't reliably provide
    one (confirmed: blank white screen, fixed only by copying the URL into a real address bar
    -- i.e. only a genuine top-level navigation worked, not whatever MAX opens "_blank" as).
    Rendering our own admin-authored HTML page sidesteps the whole class of problem: no
    upload, no MIME type to get right, nothing but a normal page at a stable URL.
    `html` is trusted admin-authored markup (platform-admin write-gated, same trust level as
    the consent notice text) -- not escaped.
    """
    return _PAGE_TEMPLATE.format(body=html if html else _EMPTY_PLACEHOLDER)
