from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..domain.entities import (
    GroupSchedule,
    GroupWithLastSync,
    ScheduleGroup,
    ScheduleInstitute,
    ScheduleLesson,
)
from .models import (
    RutScheduleGroupRecord,
    RutScheduleGroupSyncRecord,
    RutScheduleInstituteRecord,
    RutScheduleLessonRecord,
)


def _group(row: RutScheduleGroupRecord) -> ScheduleGroup:
    return ScheduleGroup(
        external_id=row.external_id,
        name=row.name,
        institute_external_id=row.institute_external_id,
        course_number=row.course_number,
    )


def _lesson(row: RutScheduleLessonRecord) -> ScheduleLesson:
    return ScheduleLesson(
        weekday=row.weekday,
        week_parity=row.week_parity,
        period_label=row.period_label,
        start_time=row.start_time,
        end_time=row.end_time,
        lesson_kind=row.lesson_kind,
        discipline=row.discipline,
        room=row.room,
        teachers=row.teachers,
        combined_groups=row.combined_groups,
        periodicity_code=row.periodicity_code,
        lesson_date=row.lesson_date,
    )


class SqlAlchemyRutScheduleRepository:
    """The institute/group/lesson catalog this repository reads and writes is platform-wide, not
    per-bot (see infrastructure/models.py's module docstring) -- no method here takes
    `bot_instance_id`/`installation_id`. Callers (routers, use cases, the sync worker) still
    resolve tenant context for *other* reasons (capability-enabled check, config, audit, rate
    limiting), they just no longer thread it into these particular calls."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_institutes(self) -> list[ScheduleInstitute]:
        rows = self._session.execute(
            select(RutScheduleInstituteRecord).order_by(RutScheduleInstituteRecord.name)
        ).scalars()
        return [ScheduleInstitute(external_id=row.external_id, name=row.name) for row in rows]

    def hierarchy_last_synced_at(self) -> datetime | None:
        """Platform-wide "when was the catalog last refreshed" -- derived from the institute
        table's own `created_at` rather than a dedicated tracking row/table, since
        `replace_hierarchy` always fully deletes and re-inserts every institute row on every
        refresh, so the newest `created_at` among them *is* exactly the last refresh time."""
        return self._session.execute(select(func.max(RutScheduleInstituteRecord.created_at))).scalar_one()

    def get_group(self, group_external_id: str) -> ScheduleGroup | None:
        row = self._session.execute(
            select(RutScheduleGroupRecord).where(RutScheduleGroupRecord.external_id == group_external_id)
        ).scalar_one_or_none()
        return _group(row) if row else None

    def list_all_groups(self) -> list[ScheduleGroup]:
        rows = self._session.execute(
            select(RutScheduleGroupRecord).order_by(RutScheduleGroupRecord.name)
        ).scalars()
        return [_group(row) for row in rows]

    def list_groups_by_institute(self, institute_external_id: str) -> list[ScheduleGroup]:
        rows = self._session.execute(
            select(RutScheduleGroupRecord)
            .where(RutScheduleGroupRecord.institute_external_id == institute_external_id)
            .order_by(RutScheduleGroupRecord.name)
        ).scalars()
        return [_group(row) for row in rows]

    def list_groups_with_last_sync(self, *, limit: int, offset: int) -> list[GroupWithLastSync]:
        rows = self._session.execute(
            select(RutScheduleGroupRecord, RutScheduleGroupSyncRecord.synced_at)
            .outerjoin(
                RutScheduleGroupSyncRecord,
                RutScheduleGroupSyncRecord.group_external_id == RutScheduleGroupRecord.external_id,
            )
            .order_by(RutScheduleGroupRecord.name)
            .limit(limit)
            .offset(offset)
        ).all()
        return [
            GroupWithLastSync(group=_group(group_row), last_synced_at=synced_at)
            for group_row, synced_at in rows
        ]

    def get_cached_schedule(self, group_external_id: str, max_age_seconds: int) -> GroupSchedule | None:
        sync_row = self._session.execute(
            select(RutScheduleGroupSyncRecord).where(
                RutScheduleGroupSyncRecord.group_external_id == group_external_id,
            )
        ).scalar_one_or_none()
        if sync_row is None:
            return None
        synced_at = sync_row.synced_at
        if synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=UTC)
        if datetime.now(tz=UTC) - synced_at > timedelta(seconds=max_age_seconds):
            return None
        group = self.get_group(group_external_id)
        if group is None:
            return None
        lesson_rows = self._session.execute(
            select(RutScheduleLessonRecord)
            .where(RutScheduleLessonRecord.group_external_id == group_external_id)
            .order_by(
                RutScheduleLessonRecord.week_parity,
                RutScheduleLessonRecord.weekday,
                RutScheduleLessonRecord.start_time,
            )
        ).scalars()
        return GroupSchedule(
            group=group,
            lessons=tuple(_lesson(row) for row in lesson_rows),
            synced_at=synced_at,
            semester_start=sync_row.semester_start,
            semester_end=sync_row.semester_end,
        )

    def save_schedule(
        self,
        group_external_id: str,
        lessons: list[ScheduleLesson],
        synced_at: datetime,
        semester_start: date | None,
        semester_end: date | None,
    ) -> None:
        self._session.execute(
            RutScheduleLessonRecord.__table__.delete().where(
                RutScheduleLessonRecord.group_external_id == group_external_id,
            )
        )
        for lesson in lessons:
            self._session.add(
                RutScheduleLessonRecord(
                    group_external_id=group_external_id,
                    weekday=lesson.weekday,
                    week_parity=lesson.week_parity,
                    period_label=lesson.period_label,
                    start_time=lesson.start_time,
                    end_time=lesson.end_time,
                    lesson_kind=lesson.lesson_kind,
                    discipline=lesson.discipline,
                    room=lesson.room,
                    teachers=lesson.teachers,
                    combined_groups=lesson.combined_groups,
                    periodicity_code=lesson.periodicity_code,
                    lesson_date=lesson.lesson_date,
                )
            )
        sync_row = self._session.execute(
            select(RutScheduleGroupSyncRecord).where(
                RutScheduleGroupSyncRecord.group_external_id == group_external_id,
            )
        ).scalar_one_or_none()
        if sync_row is None:
            sync_row = RutScheduleGroupSyncRecord(
                group_external_id=group_external_id,
                synced_at=synced_at,
                semester_start=semester_start,
                semester_end=semester_end,
            )
            self._session.add(sync_row)
        else:
            sync_row.synced_at = synced_at
            sync_row.semester_start = semester_start
            sync_row.semester_end = semester_end
        self._session.flush()

    def replace_hierarchy(
        self,
        institutes: list[ScheduleInstitute],
        groups: list[ScheduleGroup],
    ) -> None:
        self._session.execute(RutScheduleInstituteRecord.__table__.delete())
        self._session.execute(RutScheduleGroupRecord.__table__.delete())
        for institute in institutes:
            self._session.add(
                RutScheduleInstituteRecord(external_id=institute.external_id, name=institute.name)
            )
        for group in groups:
            self._session.add(
                RutScheduleGroupRecord(
                    external_id=group.external_id,
                    name=group.name,
                    institute_external_id=group.institute_external_id,
                    course_number=group.course_number,
                )
            )
        self._session.flush()
