"""Oracle-backed `ScheduleHierarchyProvider` (Task 044 follow-up).

Same protocol shape as `MiitTimetableProvider` (see `.provider`), so switching
`settings.RUT_SCHEDULE_PROVIDER` from "miit_web" to "oracle" changes nothing for any consumer
(`SyncGroupSchedule`, the nightly hierarchy crawl) -- only where the data comes from.

The connection plumbing below is real and ready to use once `settings.RUT_SCHEDULE_ORACLE_DSN`/
`_USER`/`_PASSWORD` are filled in -- see the Oracle section of `.env.example`.

Schema knowledge status (2026-09-02, from two queries the user supplied against the real schema --
`Расписание группы для бота.sql` and `Список групп с расписанием по id_e из профиля студента.sql`):

- `_read_group_lessons_sync` below is a real, working query (adapted from the first file: same
  CTEs, only the three `env` literals became bind parameters) -- NOT a guess. Known limitation,
  documented inline: the query's own output can't distinguish an every-single-week lesson
  (`idk_periodicity = 3`) from a genuine one-time event (`idk_periodicity = 6`) -- both come out
  with a NULL `num_week` -- so both are treated as "recurring on both weeks." A one-time event
  (holiday makeup class, single guest lecture, etc.) will therefore show up as if permanently
  recurring until corrected. Fixing this needs `idk_periodicity` added to the final SELECT list
  and an explicit branch on it here -- flagged rather than silently accepted.
- Neither supplied file exposes the institute -> course -> group hierarchy needed for
  `_read_hierarchy_sync` (the second file only resolves *one already-identified student's own*
  group, via `students_`/`educational_group_`, not the full public catalog every institute/course
  drill-down needs) or a semester date-range source (`ProviderGroupLessons.semester_start`/
  `semester_end` stay `None` from this provider for now -- unlike the miit.ru scraper, which reads
  a real date range off the page). Both remain open questions for whoever has broader Oracle schema
  access; don't invent table names for either.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from .....core.config import settings
from ..application.ports import ProviderGroupLessons, ProviderHierarchy, ProviderLesson


class OracleTimetableProviderError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def provider_error_code(error: BaseException) -> str:
    if isinstance(error, OracleTimetableProviderError):
        return error.code
    return "provider_unavailable"


# Adapted from the user-supplied "Расписание группы для бота.sql" -- structurally unchanged (same
# CTEs, same join shape); only the three `env` literals (`d_start`, `d_end`, `id_ed_group`) became
# bind parameters, and `id_e` is hardcoded NULL since this method is group-only (a future
# teacher-schedule feature could reuse the same CTE shape with `id_e` bound instead).
_GROUP_LESSONS_SQL = """
with env as (
  select :d_start as d_start, :d_end as d_end, :id_ed_group as id_ed_group, to_number(null) as id_e
  from dual
)
, sh as (
  select trim(to_char(s.d_start, 'd')) as d
         , to_char(s.d_start, 'hh24:mi') as hs
         , s.d_start
         , s.d_end
         , e.id_template_grid_time
         , s.id_schedule
         , decode(env.id_e, null, env.id_ed_group, 0) as id_ed_for_dates
         , (select min(se.id_ed_group) from schedule_eg_ se where se.id_schedule = s.id_schedule) as id_ed_group
         , s.idk_periodicity
         , s.d_opening
         , s.d_closing
         , (select max(seg.semester) from schedule_eg_ seg where seg.id_schedule = s.id_schedule) as semester
         , decode(s.idk_periodicity, 4, 1, 5, 2, null) as num_week
  from eg_schedule_p_ e, schedule_ s, env
  where s.id_paragraph = e.id_paragraph
        and (env.id_ed_group is null or exists (
              select 'x' from schedule_eg_ se
              where se.id_schedule = s.id_schedule and se.id_ed_group = env.id_ed_group
            ))
        and env.d_end >= s.d_opening
        and env.d_start <= nvl(s.d_closing, env.d_start)
        and (env.id_e is null or exists (
              select 'x' from employees_schedule_ es
              where es.id_e = env.id_e and es.id_schedule = s.id_schedule
            ))
)
, dis as (
  select se.id_schedule
         , d.name as dis_name
         , kl.name
           || case when kl2.idk_lesson is not null and kl2.idk_lesson <> kl.idk_lesson
                    then ' (' || kl2.name || ')' end as kl_name
         , se.subgroup
         , se.id_ed_group
         , (select listagg(eh.surname || ' ' || substr(eh.name, 1, 1) || '.'
                   || nvl2(eh.patronymic, substr(eh.patronymic, 1, 1) || '.', ''), '; ')
              within group (order by 1)
            from employees_schedule_ es, employees_ eh
            where es.id_schedule = se.id_schedule and es.id_e = eh.id_e) as mans
         , (select listagg(pr.name, '; ') within group (order by psh.index_record)
            from premises_schedule_ psh, premises_ pr
            where psh.id_schedule = sh.id_schedule and psh.id_premises = pr.id_premises) as pr_name
         , (select listagg(nvl(eg2.abbreviation,
                   (select ag2.abbreviation from abbreviation_groups_ ag2
                    where ag2.id_d_specialitie = eg2.id_d_specialitie
                      and ag2.d_start = (select max(ag3.d_start) from abbreviation_groups_ ag3
                                          where ag3.id_d_specialitie = ag2.id_d_specialitie)))
                   || '-' || eg2.name, '; ') within group (order by 1)
            from schedule_eg_ se2, educational_group_ eg2
            where se2.id_schedule = se.id_schedule and se2.id_ed_group = eg2.id_ed_group) as egs
  from schedule_eg_ se, disciplines_ d, kind_lesson_ kl, kind_lesson_ kl2, sh
  where se.id_schedule = sh.id_schedule
        and se.id_discipline = d.id_discipline
        and se.idk_lesson = kl.idk_lesson
        and se.id_ed_group = sh.id_ed_group
        and se.idk_l_detail = kl2.idk_lesson(+)
)
, dh as (
  select sdt.id_template_grid_time
         , to_char(sdt.d_start, 'hh24:mi') as hs
         , to_char(sdt.d_end, 'hh24:mi') as he
         , sdt.name
  from (select sh.id_template_grid_time from sh group by sh.id_template_grid_time) t
       , structure_distribution_time_ sdt
  where t.id_template_grid_time = sdt.id_template_grid_time
)
, dates as (
  select sh.id_ed_for_dates, d.curr_date, to_char(d.curr_date, 'd') as d
  from (select env.d_start + level - 1 as curr_date from env connect by level <= env.d_end - env.d_start + 1) d
       , (select sh.id_ed_for_dates from sh group by sh.id_ed_for_dates) sh
  where to_char(d.curr_date, 'd') <> 7
)
, dt_dh as (
  select dates.id_ed_for_dates, dates.curr_date, to_char(dates.curr_date, 'd') as d
         , trim(to_char(dates.curr_date, 'day')) as week_name, dh.*
  from dates, dh
)
, sh_dates as (
  select dates.curr_date, sh.*, 0 as period_index, 0 as edu_week
  from sh, dates
  where sh.idk_periodicity = 3
        and dates.curr_date between sh.d_opening and sh.d_closing
        and sh.d = dates.d and sh.id_ed_for_dates = dates.id_ed_for_dates
  union
  select t.* from (
    select dates.curr_date, sh.*, kpe.period_index
           , decode(mod(dense_rank() over (partition by sh.semester order by trunc(dates.curr_date, 'IW')), 2), 0, 2, 1) as edu_week
    from sh, kind_periodicity_ kpe, dates
    where kpe.idk_periodicity = sh.idk_periodicity
          and kpe.idk_periodicity in (4, 5)
          and dates.curr_date between sh.d_opening and sh.d_closing
          and sh.d = dates.d and sh.id_ed_for_dates = dates.id_ed_for_dates
  ) t
  where t.edu_week = t.period_index
  union all
  select sh.d_start as curr_date, sh.*, 0 as period_index, 0 as edu_week
  from sh
  where sh.idk_periodicity = 6
)
select dt_dh.curr_date
       , dt_dh.name as period_name
       , dt_dh.hs
       , dt_dh.he
       , sh.num_week
       , dis.dis_name
       , dis.kl_name
       , dis.subgroup
       , dis.mans
       , dis.pr_name
       , dis.egs
from dt_dh, sh_dates sh, dis
where dt_dh.id_template_grid_time = sh.id_template_grid_time(+)
      and dt_dh.id_ed_for_dates = sh.id_ed_for_dates(+)
      and dt_dh.d = sh.d(+)
      and dt_dh.hs = sh.hs(+)
      and sh.id_schedule = dis.id_schedule(+)
order by 1, 3
"""


class OracleTimetableProvider:
    """Reads the institute/group hierarchy and per-group lessons from an Oracle DB.

    Uses the synchronous `oracledb` driver (thin mode -- no Oracle Instant Client required) via
    `asyncio.to_thread`, matching how the rest of this codebase keeps blocking DB calls off the
    event loop (see `..sync_worker`'s use of `SessionLocal()`, a sync SQLAlchemy session, inside
    an `async def`).
    """

    def _connection(self):
        import oracledb  # local import: only worth requiring this dependency when actually used

        if not settings.RUT_SCHEDULE_ORACLE_DSN:
            raise OracleTimetableProviderError("oracle_not_configured")
        return oracledb.connect(
            dsn=settings.RUT_SCHEDULE_ORACLE_DSN,
            user=settings.RUT_SCHEDULE_ORACLE_USER,
            password=settings.RUT_SCHEDULE_ORACLE_PASSWORD,
        )

    def _read_hierarchy_sync(self) -> ProviderHierarchy:
        # TODO(oracle-schema): neither SQL file supplied so far exposes the full institute ->
        # course -> group catalog (only a single already-identified student's own group, via
        # students_/educational_group_ -- not the public browse-menu listing). Replace once that
        # source is known. Each row is expected to map to one of:
        #   ProviderInstitute(external_id: str, name: str)
        #   ProviderGroup(external_id: str, name: str, institute_external_id: str, course_number: int)
        raise NotImplementedError(
            "OracleTimetableProvider.read_hierarchy: institute/course/group catalog source not known yet"
        )

    def _read_group_lessons_sync(self, group_external_id: str) -> ProviderGroupLessons:
        connection = self._connection()
        try:
            cursor = connection.cursor()
            # A 14-day window -- exactly two ISO weeks -- starting from this week's Monday, so
            # every alternating-week lesson (num_week 1 and 2) shows up at least once. Oracle's
            # own `num_week` is authoritative per lesson (unlike the miit.ru scraper, which has no
            # such flag and must infer parity from a scraped semester start date), so this
            # provider doesn't need a semester-start anchor to assign week_parity correctly --
            # only to let the mini-app report *which* calendar dates are week 1 vs week 2, which
            # this provider currently can't supply (see module docstring).
            today = date.today()
            window_start = today - timedelta(days=today.isoweekday() - 1)
            window_end = window_start + timedelta(days=13)
            cursor.execute(
                _GROUP_LESSONS_SQL,
                {
                    "d_start": window_start,
                    "d_end": window_end,
                    "id_ed_group": int(group_external_id),
                },
            )
            columns = [col[0].lower() for col in cursor.description]
            lessons: list[ProviderLesson] = []
            for raw_row in cursor.fetchall():
                row = dict(zip(columns, raw_row))
                if not row["dis_name"]:
                    continue  # an empty grid slot (outer join miss), not an actual lesson
                curr_date = row["curr_date"]
                weekday = curr_date.isoweekday() if hasattr(curr_date, "isoweekday") else None
                if weekday is None:
                    continue
                num_week = row["num_week"]
                # NULL num_week covers both "every single week" (idk_periodicity=3) and a
                # genuine one-time event (idk_periodicity=6) -- this query's output can't tell
                # them apart (see module docstring). Treated as "every week" (both parities),
                # the far more common real case; a one-time event will incorrectly look
                # permanent until `idk_periodicity` is added to the SELECT and branched on here.
                parities = (1, 2) if num_week is None else (int(num_week),)
                for parity in parities:
                    lessons.append(
                        ProviderLesson(
                            weekday=weekday,
                            week_parity=parity,
                            period_label=row["period_name"] or "",
                            start_time=row["hs"] or "",
                            end_time=row["he"] or "",
                            lesson_kind=row["kl_name"] or "",
                            discipline=row["dis_name"] or "",
                            room=row["pr_name"],
                            teachers=row["mans"],
                            combined_groups=row["egs"],
                        )
                    )
            # TODO(oracle-schema): no semester date-range source found in the supplied files yet
            # (unlike the miit.ru scraper, which reads one off the group page) -- the mini-app
            # falls back to always showing week_parity 1 until this is filled in (see
            # RutScheduleCapabilityView's documented fallback).
            return ProviderGroupLessons(lessons=tuple(lessons), semester_start=None, semester_end=None)
        finally:
            connection.close()

    async def read_hierarchy(self) -> ProviderHierarchy:
        return await asyncio.to_thread(self._read_hierarchy_sync)

    async def read_group_lessons(self, group_external_id: str) -> ProviderGroupLessons:
        return await asyncio.to_thread(self._read_group_lessons_sync, group_external_id)

    async def probe(self) -> None:
        def _probe_sync() -> None:
            connection = self._connection()
            try:
                connection.ping()
            finally:
                connection.close()

        await asyncio.to_thread(_probe_sync)
