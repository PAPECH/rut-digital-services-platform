from ..domain.entities import CapabilityDescriptor, CapabilityView
from .domain.config import project_rut_schedule_public_config, validate_rut_schedule_config

RUT_SCHEDULE_DESCRIPTOR = CapabilityDescriptor(
    key="rut_schedule",
    version="1.0.0",
    name="Расписание",
    description="Просмотр расписания занятий по институту, курсу и группе.",
    admin_editor_key="rut_schedule",
    views=(
        CapabilityView(
            key="browse",
            title="Расписание",
            subtitle="Институт → курс → группа.",
            icon="calendar",
        ),
    ),
    validate_config=validate_rut_schedule_config,
    public_config=project_rut_schedule_public_config,
)
