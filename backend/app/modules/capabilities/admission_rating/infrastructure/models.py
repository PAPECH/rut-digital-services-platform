from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .....db.base import Base, TimestampMixin


class AdmissionRatingPlanRecord(Base, TimestampMixin):
    __tablename__ = "admission_rating_plans"
    __table_args__ = (
        UniqueConstraint("bot_instance_id", "plan_id", name="uq_admission_rating_plan_bot_plan"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True
    )
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("capability_installations.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[int] = mapped_column(Integer)
    specialty: Mapped[str] = mapped_column(String(255))
    qualification: Mapped[str] = mapped_column(String(64))


class AdmissionRatingStateRecord(Base):
    __tablename__ = "admission_rating_states"
    __table_args__ = (
        UniqueConstraint(
            "bot_instance_id",
            "plan_id",
            "applicant_code_hash",
            "competition",
            name="uq_admission_rating_state",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True
    )
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("capability_installations.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[int] = mapped_column(Integer)
    applicant_code: Mapped[str] = mapped_column(String(64))
    applicant_code_hash: Mapped[str] = mapped_column(String(64), index=True)
    points: Mapped[float] = mapped_column(Float)
    preference: Mapped[str] = mapped_column(String(255))
    competition: Mapped[str] = mapped_column(String(255))
    group_name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer, default=0)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AdmissionRatingSubscriptionRecord(Base, TimestampMixin):
    __tablename__ = "admission_rating_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "bot_instance_id", "user_id", "applicant_code_hash", name="uq_admission_rating_subscription"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True
    )
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("capability_installations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    applicant_code: Mapped[str] = mapped_column(String(64))
    applicant_code_hash: Mapped[str] = mapped_column(String(64), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
