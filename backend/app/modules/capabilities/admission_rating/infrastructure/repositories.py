from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.entities import RatingEntry, RatingSubscription
from .models import AdmissionRatingPlanRecord, AdmissionRatingStateRecord, AdmissionRatingSubscriptionRecord


def _subscription(row: AdmissionRatingSubscriptionRecord) -> RatingSubscription:
    return RatingSubscription(
        row.id,
        row.bot_instance_id,
        row.installation_id,
        row.user_id,
        row.applicant_code,
        row.applicant_code_hash,
        row.is_active,
    )


class SqlAlchemyAdmissionRatingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_entries(self, bot_instance_id: int, code_hash: str) -> list[RatingEntry]:
        rows = self._session.execute(
            select(AdmissionRatingStateRecord, AdmissionRatingPlanRecord)
            .join(
                AdmissionRatingPlanRecord,
                (AdmissionRatingPlanRecord.bot_instance_id == AdmissionRatingStateRecord.bot_instance_id)
                & (AdmissionRatingPlanRecord.plan_id == AdmissionRatingStateRecord.plan_id),
            )
            .where(
                AdmissionRatingStateRecord.bot_instance_id == bot_instance_id,
                AdmissionRatingStateRecord.applicant_code_hash == code_hash,
            )
            .order_by(AdmissionRatingStateRecord.position)
        ).all()
        return [
            RatingEntry(
                state.plan_id,
                state.applicant_code,
                plan.specialty,
                plan.qualification,
                state.points,
                state.preference,
                state.competition,
                state.group_name,
                state.position,
                state.total,
                state.checked_at,
            )
            for state, plan in rows
        ]

    def get_subscription(
        self, bot_instance_id: int, user_id: int, code_hash: str | None = None
    ) -> RatingSubscription | None:
        query = select(AdmissionRatingSubscriptionRecord).where(
            AdmissionRatingSubscriptionRecord.bot_instance_id == bot_instance_id,
            AdmissionRatingSubscriptionRecord.user_id == user_id,
        )
        query = (
            query.where(AdmissionRatingSubscriptionRecord.applicant_code_hash == code_hash)
            if code_hash
            else query.order_by(AdmissionRatingSubscriptionRecord.updated_at.desc()).limit(1)
        )
        row = self._session.execute(query).scalar_one_or_none()
        return _subscription(row) if row else None

    def save_subscription(self, value: RatingSubscription) -> RatingSubscription:
        row = self._session.execute(
            select(AdmissionRatingSubscriptionRecord).where(
                AdmissionRatingSubscriptionRecord.bot_instance_id == value.bot_instance_id,
                AdmissionRatingSubscriptionRecord.user_id == value.user_id,
                AdmissionRatingSubscriptionRecord.applicant_code_hash == value.applicant_code_hash,
            )
        ).scalar_one_or_none()
        if row is None:
            row = AdmissionRatingSubscriptionRecord(
                **{
                    "bot_instance_id": value.bot_instance_id,
                    "installation_id": value.installation_id,
                    "user_id": value.user_id,
                    "applicant_code": value.applicant_code,
                    "applicant_code_hash": value.applicant_code_hash,
                    "is_active": value.is_active,
                }
            )
            self._session.add(row)
        else:
            row.is_active = value.is_active
            row.installation_id = value.installation_id
        self._session.flush()
        return _subscription(row)
