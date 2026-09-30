from ..domain.entities import CapabilityDescriptor, CapabilityView
from .domain.config import (
    project_request_status_public_config,
    validate_request_status_config,
)

REQUEST_STATUS_DESCRIPTOR = CapabilityDescriptor(
    key="request_status",
    version="1.0.0",
    name="Статус заявления",
    description="Поиск статуса по номеру и уведомления об изменениях.",
    admin_editor_key="request_status",
    views=(
        CapabilityView(
            key="lookup",
            title="Проверить статус заявления",
            subtitle="Введите номер заявления, чтобы узнать актуальный статус.",
            icon="search",
        ),
    ),
    validate_config=validate_request_status_config,
    public_config=project_request_status_public_config,
)
