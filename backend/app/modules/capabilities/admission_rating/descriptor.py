from ..domain.entities import CapabilityDescriptor, CapabilityView
from .domain.config import (
    project_admission_rating_public_config,
    validate_admission_rating_config,
)

ADMISSION_RATING_DESCRIPTOR = CapabilityDescriptor(
    key="admission_rating",
    version="1.0.0",
    name="Место в рейтинге",
    description="Поиск позиции поступающего и уведомления об изменениях рейтинга.",
    admin_editor_key="admission_rating",
    views=(
        CapabilityView(
            key="lookup",
            title="Найти место в рейтинге",
            subtitle="Введите уникальный код поступающего.",
            icon="chart",
        ),
    ),
    validate_config=validate_admission_rating_config,
    public_config=project_admission_rating_public_config,
)
