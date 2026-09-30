from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base, TimestampMixin


class AdmissionPlan(Base, TimestampMixin):
    """План приёма по конкретному направлению (plan_id из planReceptionUrl)."""

    __tablename__ = "admission_plans"

    plan_id: Mapped[int] = mapped_column(primary_key=True)
    plan_reception_url: Mapped[str] = mapped_column(String(255), nullable=False)
    spec_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    spec_qualifier: Mapped[str] = mapped_column(String(64), nullable=False)

    all_: Mapped[int] = mapped_column("all", Integer, default=0)
    budget: Mapped[int] = mapped_column(Integer, default=0)
    concourse: Mapped[int] = mapped_column(Integer, default=0)
    crimea: Mapped[int] = mapped_column(Integer, default=0)
    paid: Mapped[int] = mapped_column(Integer, default=0)
    paid_concourse: Mapped[int] = mapped_column(Integer, default=0)
    paid_crimea: Mapped[int] = mapped_column(Integer, default=0)
    quota_05: Mapped[int] = mapped_column(Integer, default=0)
    quota_07: Mapped[int] = mapped_column(Integer, default=0)
    special_quota: Mapped[int] = mapped_column(Integer, default=0)
    target_quota: Mapped[int] = mapped_column(Integer, default=0)

    level: Mapped[str] = mapped_column(String(16), nullable=False)
    training: Mapped[str] = mapped_column(String(16), nullable=False)


class RatingState(Base):
    __tablename__ = "rating_states"

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("admission_plans.plan_id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    competition_name: Mapped[str] = mapped_column(String(255), primary_key=True)  # добавили в PK

    points: Mapped[float] = mapped_column(Float, nullable=False)
    preference_index_display: Mapped[str] = mapped_column(String(255), nullable=False)
    group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rating_index: Mapped[int] = mapped_column(Integer, nullable=False)

    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RatingSubscription(Base, TimestampMixin):
    """Подписка пользователя на изменения позиции по displayName (по всем plan_id)."""

    __tablename__ = "rating_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "display_name", name="uq_rating_sub_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
