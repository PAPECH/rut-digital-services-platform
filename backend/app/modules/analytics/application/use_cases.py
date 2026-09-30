from ..domain.events import AnalyticsEvent
from .ports import AnalyticsEventRepository


class RecordAnalyticsEvent:
    def __init__(self, repository: AnalyticsEventRepository) -> None:
        self._repository = repository

    def execute(self, event: AnalyticsEvent) -> bool:
        self._repository.validate_context(event)
        return self._repository.add(event)
