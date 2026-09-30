from datetime import date as date_
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .....db.base import Base, TimestampMixin


class RutScheduleInstituteRecord(Base, TimestampMixin):
    """The institute/group/lesson catalog is platform-wide, not per-bot -- miit.ru's public
    schedule is the same regardless of which bot asks (see docs/tasks/045's "Follow-up,
    2026-09-02: shared platform-wide data"). No `bot_instance_id`/`installation_id` here on
    purpose: every enabled `rut_schedule` installation, on any bot, reads and is kept fresh by
    the same rows, so N bots enabling this never means N independent crawls of the same site.
    Per-bot config (title/subtitle/intervals/auto-sync toggle) stays on `capability_installations`
    as before -- only the crawled data moved."""

    __tablename__ = "rut_schedule_institutes"
    __table_args__ = (UniqueConstraint("external_id", name="uq_rut_schedule_institute_external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255))


class RutScheduleGroupRecord(Base, TimestampMixin):
    __tablename__ = "rut_schedule_groups"
    __table_args__ = (UniqueConstraint("external_id", name="uq_rut_schedule_group_external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(64))
    institute_external_id: Mapped[str] = mapped_column(String(32), index=True)
    course_number: Mapped[int] = mapped_column(Integer)


class RutScheduleLessonRecord(Base):
    __tablename__ = "rut_schedule_lessons"
    # No natural-key uniqueness here on purpose: `save_schedule` fully deletes and re-inserts a
    # group's rows on every sync (see infrastructure/repositories.py), and a single time slot can
    # legitimately hold two lessons with the same discipline/weekday/week_parity/start_time --
    # different subgroups, split by "<hr>" on the source page, differing only in teacher/room/
    # subgroup label. A composite unique constraint here would (and did) reject that.
    id: Mapped[int] = mapped_column(primary_key=True)
    group_external_id: Mapped[str] = mapped_column(String(32), index=True)
    weekday: Mapped[int] = mapped_column(Integer)
    week_parity: Mapped[int] = mapped_column(Integer)
    period_label: Mapped[str] = mapped_column(String(32))
    start_time: Mapped[str] = mapped_column(String(8))
    end_time: Mapped[str] = mapped_column(String(8))
    lesson_kind: Mapped[str] = mapped_column(String(120))
    discipline: Mapped[str] = mapped_column(String(255))
    room: Mapped[str | None] = mapped_column(String(500), nullable=True)
    teachers: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    combined_groups: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Reserved for the future Oracle provider's `idk_periodicity`; unused by the scraper. See
    # ScheduleLesson.periodicity_code in domain/entities.py for why this stays null for now.
    periodicity_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Set only for a "Разовое" (one-off, explicitly dated) session scraped from a `type=2` group
    # page. See ScheduleLesson.lesson_date in domain/entities.py; null for every ordinary
    # recurring (weekday/week_parity) lesson.
    lesson_date: Mapped[date_ | None] = mapped_column(Date, nullable=True)


class RutScheduleManualSyncRequestRecord(Base):
    """Platform-admin manual sync trigger + live log (Task 045). Never written by the nightly
    cron -- only an explicit admin-triggered run creates a row here. The log itself is also
    platform-wide (same reasoning as the catalog above) -- `bot_instance_id`/`installation_id`
    stay only as informational context ("which bot's panel was this triggered from"), never as a
    read filter; see `SqlAlchemyRutScheduleSyncLogRepository.list_recent`."""

    __tablename__ = "rut_schedule_manual_sync_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True
    )
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("capability_installations.id", ondelete="CASCADE"), index=True
    )
    requested_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(16))
    group_external_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    # Set only for scope="institute" -- mutually exclusive with group_external_id.
    institute_external_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    groups_synced: Mapped[int | None] = mapped_column(Integer, nullable=True)
    groups_failed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class RutScheduleGroupSyncRecord(Base):
    __tablename__ = "rut_schedule_group_sync"
    __table_args__ = (
        UniqueConstraint("group_external_id", name="uq_rut_schedule_group_sync_group_external_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    group_external_id: Mapped[str] = mapped_column(String(32), index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    semester_start: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    semester_end: Mapped[date_ | None] = mapped_column(Date, nullable=True)
