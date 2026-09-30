from typing import Protocol

from .entities import RatingEntry, RatingSubscription


class AdmissionRatingRepository(Protocol):
    def list_entries(self, bot_instance_id: int, code_hash: str) -> list[RatingEntry]: ...

    def get_subscription(
        self, bot_instance_id: int, user_id: int, code_hash: str | None = None
    ) -> RatingSubscription | None: ...

    def save_subscription(self, subscription: RatingSubscription) -> RatingSubscription: ...
