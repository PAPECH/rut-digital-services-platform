from __future__ import annotations

import pytest

from app.modules.forms.application.ports import AttachmentDescriptor
from app.modules.forms.application.use_cases import FormAttachmentRejected, ValidateSubmission
from app.modules.forms.domain.fields import (
    FormSchemaValidationError,
    FormValueValidationError,
    validate_form_fields,
    validate_submission_values,
)


def _base(key: str, field_type: str, **extra):
    return {
        "key": key,
        "type": field_type,
        "label": key,
        "help_text": None,
        "required": True,
        "active": True,
        "profile_key": None,
        **extra,
    }


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        (_base("short", "short_text", min_length=1, max_length=10, pattern=None), "текст", "текст"),
        (_base("long", "long_text", min_length=1, max_length=100), "длинный текст", "длинный текст"),
        (_base("email", "email"), "user@example.org", "user@example.org"),
        (_base("phone", "phone", pattern=r"\+7\d{10}"), "+79990000000", "+79990000000"),
        (_base("number", "number", min=1, max=5, step=1), 3, 3),
        (_base("date", "date", min="2020-01-01", max="2030-01-01"), "2026-08-12", "2026-08-12"),
        (_base("check", "checkbox", default=False), True, True),
        (_base("select", "select", options=[{"value": "a", "label": "A"}], default=None), "a", "a"),
        (_base("radio", "radio", options=[{"value": "b", "label": "B"}], default=None), "b", "b"),
        (
            _base(
                "multiselect",
                "multiselect",
                options=[{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
                default=None,
            ),
            ["a", "b"],
            ["a", "b"],
        ),
        (
            _base("file", "file", accepted_mime_types=["application/pdf"], max_files=2, max_size_bytes=1000),
            [4],
            [4],
        ),
    ],
)
def test_every_supported_field_type_is_normalized_and_validated(field, value, expected) -> None:
    normalized_fields = validate_form_fields([field])
    values = validate_submission_values(normalized_fields, {field["key"]: value})
    assert values[field["key"]] == expected


def test_schema_rejects_unknown_properties_and_duplicate_keys() -> None:
    field = _base("same", "checkbox", default=False)
    with pytest.raises(FormSchemaValidationError):
        validate_form_fields([{**field, "script": "alert(1)"}])
    with pytest.raises(FormSchemaValidationError):
        validate_form_fields([field, field])


@pytest.mark.parametrize(
    "field",
    [
        _base("bad_type", "script"),
        _base("bad_pattern", "short_text", min_length=0, max_length=10, pattern="["),
        _base("bad_range", "number", min=10, max=1, step=1),
        _base("bad_date", "date", min="2026-99-01", max=None),
        _base(
            "duplicate_options",
            "select",
            options=[{"value": "a", "label": "A"}, {"value": "a", "label": "B"}],
            default=None,
        ),
        _base("markup", "checkbox", label="<script>bad</script>", default=False),
        _base(
            "multiselect_string_default",
            "multiselect",
            options=[{"value": "a", "label": "A"}],
            default="a",
        ),
        _base(
            "multiselect_unknown_default",
            "multiselect",
            options=[{"value": "a", "label": "A"}],
            default=["missing"],
        ),
        _base(
            "multiselect_duplicate_default",
            "multiselect",
            options=[{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
            default=["a", "a"],
        ),
        _base(
            "multiselect_bad_bounds",
            "multiselect",
            options=[{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
            default=None,
            min_selected=2,
            max_selected=1,
        ),
    ],
)
def test_invalid_constraints_and_markup_are_rejected(field) -> None:
    with pytest.raises(FormSchemaValidationError):
        validate_form_fields([field])


def test_schema_field_limit_is_enforced() -> None:
    fields = [_base(f"field_{index}", "checkbox", default=False) for index in range(101)]
    with pytest.raises(FormSchemaValidationError):
        validate_form_fields(fields)


def test_submission_rejects_unknown_field_and_required_false_checkbox() -> None:
    field = _base("consent", "checkbox", default=False)
    with pytest.raises(FormValueValidationError):
        validate_submission_values([field], {"unexpected": "value"})
    with pytest.raises(FormValueValidationError):
        validate_submission_values([field], {"consent": False})


def _multiselect_field(**extra):
    params = {
        "options": [
            {"value": "passport", "label": "Паспорт"},
            {"value": "diploma", "label": "Диплом"},
            {"value": "snils", "label": "СНИЛС"},
        ],
        "default": None,
        "required": True,
        **extra,
    }
    return _base("documents", "multiselect", **params)


def test_multiselect_accepts_valid_array_submission() -> None:
    field = _multiselect_field()
    normalized = validate_form_fields([field])
    values = validate_submission_values(normalized, {"documents": ["passport", "snils"]})
    assert values["documents"] == ["passport", "snils"]


def test_multiselect_rejects_value_outside_option_set() -> None:
    field = _multiselect_field()
    normalized = validate_form_fields([field])
    with pytest.raises(FormValueValidationError):
        validate_submission_values(normalized, {"documents": ["passport", "not_an_option"]})


def test_multiselect_rejects_empty_array_when_required() -> None:
    field = _multiselect_field()
    normalized = validate_form_fields([field])
    with pytest.raises(FormValueValidationError):
        validate_submission_values(normalized, {"documents": []})


def test_multiselect_not_required_allows_empty_array() -> None:
    field = _multiselect_field(required=False)
    normalized = validate_form_fields([field])
    values = validate_submission_values(normalized, {})
    assert "documents" not in values


def test_multiselect_enforces_min_and_max_selected_bounds() -> None:
    field = _multiselect_field(min_selected=1, max_selected=2)
    normalized = validate_form_fields([field])
    # within bounds
    values = validate_submission_values(normalized, {"documents": ["passport", "diploma"]})
    assert values["documents"] == ["passport", "diploma"]
    # exceeds max_selected
    with pytest.raises(FormValueValidationError):
        validate_submission_values(normalized, {"documents": ["passport", "diploma", "snils"]})


def test_multiselect_rejects_duplicate_values_in_submission() -> None:
    field = _multiselect_field()
    normalized = validate_form_fields([field])
    with pytest.raises(FormValueValidationError):
        validate_submission_values(normalized, {"documents": ["passport", "passport"]})


class AttachmentGateway:
    def __init__(self, attachment: AttachmentDescriptor) -> None:
        self.attachment = attachment

    def get_attachments(self, attachment_ids: set[int]):
        return {self.attachment.id: self.attachment} if self.attachment.id in attachment_ids else {}


def test_file_reference_from_another_bot_or_user_is_rejected() -> None:
    field = _base(
        "document",
        "file",
        accepted_mime_types=["application/pdf"],
        max_files=1,
        max_size_bytes=1000,
    )
    gateway = AttachmentGateway(AttachmentDescriptor(7, 2, 11, "application/pdf", 100))
    with pytest.raises(FormAttachmentRejected, match="another bot"):
        ValidateSubmission(gateway).execute(
            bot_instance_id=1,
            user_id=11,
            fields=[field],
            values={"document": [7]},
        )
    gateway = AttachmentGateway(AttachmentDescriptor(7, 1, 99, "application/pdf", 100))
    with pytest.raises(FormAttachmentRejected, match="another user"):
        ValidateSubmission(gateway).execute(
            bot_instance_id=1,
            user_id=11,
            fields=[field],
            values={"document": [7]},
        )


def test_file_mime_wildcard_accepts_matching_attachment() -> None:
    field = _base(
        "image",
        "file",
        accepted_mime_types=["image/*"],
        max_files=1,
        max_size_bytes=1000,
    )
    gateway = AttachmentGateway(AttachmentDescriptor(8, 1, 11, "image/png", 100))
    values = ValidateSubmission(gateway).execute(
        bot_instance_id=1,
        user_id=11,
        fields=[field],
        values={"image": [8]},
    )
    assert values == {"image": [8]}
