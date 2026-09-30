import pytest

from app.core.errors import ApiError
from app.modules.tenancy.presentation.dependencies import resolve_tenant


@pytest.mark.parametrize("header_value", [None, "", "   "])
def test_resolve_tenant_rejects_missing_or_blank_header(header_value: str | None) -> None:
    """No implicit default bot: a caller that forgets to name a bot must fail loudly, not be
    silently served/writing another tenant's data (Task 035). `db=None` is safe here -- the guard
    must raise before the DB-backed repository lookup is ever constructed."""
    with pytest.raises(ApiError) as error:
        resolve_tenant(x_bot_slug=header_value, db=None)  # type: ignore[arg-type]

    assert error.value.status_code == 400
    assert error.value.detail["code"] == "bot_slug_required"
