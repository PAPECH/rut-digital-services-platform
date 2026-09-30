from __future__ import annotations

CONSENT_DOCUMENT_LINK_PLACEHOLDER = "{{consent_document_link}}"

MAX_CONSENT_DOCUMENT_TITLE_LENGTH = 300
MAX_CONSENT_DOCUMENT_BODY_LENGTH = 200_000
MAX_CONSENT_CHECKBOX_TEXT_LENGTH = 2000


def validate_consent_document_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise ValueError("Consent document title cannot be empty")
    if len(cleaned) > MAX_CONSENT_DOCUMENT_TITLE_LENGTH:
        raise ValueError("Consent document title is too long")
    return cleaned


def validate_consent_document_body(body_html: str) -> str:
    if not body_html.strip():
        raise ValueError("Consent document content cannot be empty")
    if len(body_html) > MAX_CONSENT_DOCUMENT_BODY_LENGTH:
        raise ValueError("Consent document content is too long")
    return body_html


def consent_checkbox_text_is_valid(text: str) -> bool:
    """Publish-time completeness check for the checkbox label: it must actually contain the
    click-inserted document-link placeholder exactly once, mirroring `domain/template.py`'s
    placeholder-presence discipline for the result template. A published consent checkbox with no
    way to reach the referenced document would not be informed consent."""
    cleaned = text.strip()
    if not cleaned or len(cleaned) > MAX_CONSENT_CHECKBOX_TEXT_LENGTH:
        return False
    return cleaned.count(CONSENT_DOCUMENT_LINK_PLACEHOLDER) == 1
