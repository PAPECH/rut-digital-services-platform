"""Compatibility aliases for modules awaiting the forms bounded-context migration."""

from ..modules.forms.infrastructure.models import (
    FormDefinitionRecord,
    FormDraftRecord,
    FormVersionRecord,
    LegacyFormFieldRecord,
)

FormTemplate = FormDefinitionRecord
FormField = LegacyFormFieldRecord

__all__ = [
    "FormDraftRecord",
    "FormField",
    "FormTemplate",
    "FormVersionRecord",
]
