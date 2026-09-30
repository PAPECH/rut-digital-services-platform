from dataclasses import dataclass, replace

from ..domain.entities import RatingEntry, RatingSubscription
from ..domain.identity import applicant_code_hash, normalize_applicant_code
from ..domain.repositories import AdmissionRatingRepository


@dataclass(frozen=True, slots=True)
class RatingLookupResult:
    applicant_code: str
    entries: list[RatingEntry]
    is_subscribed: bool


def rating_change_notification_payload(installation_id: int) -> dict[str, int]:
    if installation_id <= 0:
        raise ValueError("Installation id must be positive")
    return {"installation_id": installation_id}


class LookupAdmissionRating:
    def __init__(self, repository: AdmissionRatingRepository) -> None:
        self._repository = repository

    def execute(self, *, bot_instance_id: int, user_id: int, applicant_code: str) -> RatingLookupResult:
        code = normalize_applicant_code(applicant_code)
        code_hash = applicant_code_hash(bot_instance_id, code)
        subscription = self._repository.get_subscription(bot_instance_id, user_id, code_hash)
        return RatingLookupResult(
            applicant_code=code,
            entries=self._repository.list_entries(bot_instance_id, code_hash),
            is_subscribed=bool(subscription and subscription.is_active),
        )


class GetAdmissionRatingSubscription:
    def __init__(self, repository: AdmissionRatingRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, user_id: int) -> RatingSubscription | None:
        value = self._repository.get_subscription(bot_instance_id, user_id)
        return value if value and value.is_active else None


class SetAdmissionRatingSubscription:
    def __init__(self, repository: AdmissionRatingRepository) -> None:
        self._repository = repository

    def execute(
        self, *, bot_instance_id: int, installation_id: int, user_id: int, applicant_code: str, active: bool
    ) -> RatingSubscription:
        code = normalize_applicant_code(applicant_code)
        code_hash = applicant_code_hash(bot_instance_id, code)
        current = self._repository.get_subscription(bot_instance_id, user_id, code_hash)
        value = (
            replace(current, is_active=active)
            if current
            else RatingSubscription(
                id=None,
                bot_instance_id=bot_instance_id,
                installation_id=installation_id,
                user_id=user_id,
                applicant_code=code,
                applicant_code_hash=code_hash,
                is_active=active,
            )
        )
        return self._repository.save_subscription(value)
