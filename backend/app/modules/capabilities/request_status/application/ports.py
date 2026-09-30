from typing import Protocol

from ..domain.config import RequestStatusConfig


class RequestStatusProvider(Protocol):
    def read_statuses(self, config: RequestStatusConfig) -> dict[str, str]: ...
