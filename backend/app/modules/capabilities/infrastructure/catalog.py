from ..admission_rating.descriptor import ADMISSION_RATING_DESCRIPTOR
from ..domain.entities import CapabilityRegistry
from ..request_status.descriptor import REQUEST_STATUS_DESCRIPTOR
from ..rut_schedule.descriptor import RUT_SCHEDULE_DESCRIPTOR

capability_registry = CapabilityRegistry(
    (ADMISSION_RATING_DESCRIPTOR, REQUEST_STATUS_DESCRIPTOR, RUT_SCHEDULE_DESCRIPTOR)
)
