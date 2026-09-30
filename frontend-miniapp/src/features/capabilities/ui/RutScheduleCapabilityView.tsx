import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import type {
  CapabilityViewProps,
  RutGroupSchedule,
  RutScheduleGroup,
  RutScheduleNavigationCourse,
  RutScheduleNavigationInstitute,
  RutScheduleNavigationTree,
} from "@/entities/capability/model/types";
import { capabilityApi } from "@/features/capabilities/api/capabilityApi";

const WEEKDAY_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];

function isoWeekday(d: Date): number {
  const day = d.getDay();
  return day === 0 ? 7 : day;
}

function mondayOf(d: Date): Date {
  const monday = new Date(d);
  monday.setDate(d.getDate() - (isoWeekday(d) - 1));
  monday.setHours(0, 0, 0, 0);
  return monday;
}

function addDays(d: Date, days: number): Date {
  const next = new Date(d);
  next.setDate(next.getDate() + days);
  return next;
}

function parseIsoDate(value: string): Date {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function toIsoDate(d: Date): string {
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${day}`;
}

/** Which of the source site's "I неделя"/"II неделя" tabs a given date falls into. The site only
 * labels lessons by tab, never by date, so `semesterStart` (scraped from the same group page) is
 * the only anchor available -- verified against real data: the term's first week (starting on
 * `semesterStart`, a Tuesday) was "I неделя", and the following Mon-Fri was "II неделя". */
function weekParityFor(target: Date, semesterStart: Date): 1 | 2 {
  const weeksDiff = Math.round(
    (mondayOf(target).getTime() - mondayOf(semesterStart).getTime()) / (7 * 86_400_000),
  );
  return ((weeksDiff % 2) + 2) % 2 === 0 ? 1 : 2;
}

function monthLabel(d: Date): string {
  const label = d.toLocaleDateString("ru-RU", { month: "long", year: "numeric" });
  return label.charAt(0).toUpperCase() + label.slice(1);
}

const SUBGROUP_RE = /п\/гр\.?\s*(\d+)/i;

/** The source site marks a lesson as "for subgroup N" the same way it marks "shared with these
 * other groups" -- both render through the same `icon-community` tag, only the text differs
 * ("ВГТ-211 п/гр.2" vs "ВГТ-111; ВУП-111; ВУТ-111"). Detect the subgroup case so it can be shown
 * as its own badge instead of generic "combined groups" text. */
function subgroupLabel(combinedGroups: string | null): string | null {
  if (!combinedGroups) return null;
  const match = SUBGROUP_RE.exec(combinedGroups);
  return match ? `Подгруппа ${match[1]}` : null;
}

/** A single time slot can hold more than one lesson at once -- the group split into subgroups,
 * each with its own discipline/teacher/room (verified against a real group page). Group same-time
 * lessons together so the UI shows the time once, with each subgroup's lesson under it. */
function groupByTimeSlot(lessons: RutGroupSchedule["lessons"]) {
  const slots = new Map<string, RutGroupSchedule["lessons"]>();
  for (const lesson of lessons) {
    const key = lesson.start_time;
    const existing = slots.get(key);
    if (existing) existing.push(lesson);
    else slots.set(key, [lesson]);
  }
  return Array.from(slots.values()).sort((a, b) => a[0].start_time.localeCompare(b[0].start_time));
}

type Step =
  | { kind: "institutes" }
  | { kind: "courses"; institute: RutScheduleNavigationInstitute }
  | { kind: "groups"; institute: RutScheduleNavigationInstitute; course: RutScheduleNavigationCourse }
  | {
      kind: "schedule";
      institute: RutScheduleNavigationInstitute;
      course: RutScheduleNavigationCourse;
      group: RutScheduleGroup;
    };

function BackLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" className="news-detail__back" onClick={onClick}>
      <span className="ico" aria-hidden="true">
        <Icon.ArrowLeft />
      </span>
      {label}
    </button>
  );
}

function ListCard({ title, onClick }: { title: string; onClick: () => void }) {
  return (
    <button type="button" className="btn btn-secondary" onClick={onClick}>
      {title}
    </button>
  );
}

export function RutScheduleCapabilityView({ capability }: CapabilityViewProps) {
  const config = capability.public_config as { title?: string };
  const [step, setStep] = useState<Step>({ kind: "institutes" });
  const [tree, setTree] = useState<RutScheduleNavigationTree | null>(null);
  const [schedule, setSchedule] = useState<RutGroupSchedule | null>(null);
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The whole institutes->courses->groups catalog is fetched once (Task 046) -- selecting an
  // institute, then a course, then a group filters this already-loaded tree client-side; only a
  // group's actual schedule (below) triggers a further request.
  useEffect(() => {
    if (tree) return;
    setBusy(true);
    setError(null);
    capabilityApi.rutSchedule
      .navigationTree()
      .then(setTree)
      .catch((reason: Error) => setError(reason.message || "Не удалось загрузить справочник"))
      .finally(() => setBusy(false));
  }, [tree]);

  const openInstitute = (institute: RutScheduleNavigationInstitute) => {
    setStep({ kind: "courses", institute });
  };

  const openCourse = (institute: RutScheduleNavigationInstitute, course: RutScheduleNavigationCourse) => {
    setStep({ kind: "groups", institute, course });
  };

  const openGroup = (
    institute: RutScheduleNavigationInstitute,
    course: RutScheduleNavigationCourse,
    group: RutScheduleGroup,
  ) => {
    setStep({ kind: "schedule", institute, course, group });
    setSchedule(null);
    setSelectedDate(new Date());
    setBusy(true);
    setError(null);
    capabilityApi.rutSchedule
      .schedule(group.external_id)
      .then(setSchedule)
      .catch((reason: Error) => setError(reason.message || "Не удалось загрузить расписание"))
      .finally(() => setBusy(false));
  };

  return (
    <div className="capability-rut-schedule">
      {step.kind !== "schedule" ? (
        <header>
          <h1 className="screen-title">{config.title || "Расписание"}</h1>
        </header>
      ) : null}

      {error ? <div className="form-error">{error}</div> : null}
      {busy ? <div className="muted">Загрузка…</div> : null}

      {step.kind === "institutes" && tree ? (
        <ul className="capability-rut-schedule__list">
          {tree.institutes.map((institute) => (
            <li key={institute.external_id}>
              <ListCard title={institute.name} onClick={() => openInstitute(institute)} />
            </li>
          ))}
        </ul>
      ) : null}

      {step.kind === "courses" ? (
        <>
          <BackLink label="Назад к институтам" onClick={() => setStep({ kind: "institutes" })} />
          <ul className="capability-rut-schedule__list">
            {step.institute.courses.map((course) => (
              <li key={course.course_number}>
                <ListCard
                  title={`${course.course_number} курс`}
                  onClick={() => openCourse(step.institute, course)}
                />
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {step.kind === "groups" ? (
        <>
          <BackLink
            label="Назад к курсам"
            onClick={() => setStep({ kind: "courses", institute: step.institute })}
          />
          <ul className="capability-rut-schedule__list">
            {step.course.groups.map((group) => (
              <li key={group.external_id}>
                <ListCard
                  title={group.name}
                  onClick={() => openGroup(step.institute, step.course, group)}
                />
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {step.kind === "schedule" && schedule ? (
        <ScheduleDayView
          schedule={schedule}
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
          onBack={() => setStep({ kind: "groups", institute: step.institute, course: step.course })}
        />
      ) : null}
    </div>
  );
}

function ScheduleDayView({
  schedule,
  selectedDate,
  onSelectDate,
  onBack,
}: {
  schedule: RutGroupSchedule;
  selectedDate: Date;
  onSelectDate: (d: Date) => void;
  onBack: () => void;
}) {
  const semesterStart = schedule.semester_start ? parseIsoDate(schedule.semester_start) : null;
  const monday = mondayOf(selectedDate);
  const weekDays = Array.from({ length: 6 }, (_, i) => addDays(monday, i));
  // Falls back to parity 1 when the term's date range couldn't be scraped -- a known, documented
  // gap (see MiitTimetableProvider), not silently wrong data: without it there's no way to tell
  // which of the two alternating weeks a given date belongs to.
  const parity = semesterStart ? weekParityFor(selectedDate, semesterStart) : 1;
  const weekday = isoWeekday(selectedDate);
  const selectedIso = toIsoDate(selectedDate);
  // A "Разовое" (one-off, explicitly dated) session carries its own lesson_date and must be
  // matched against the selected calendar date directly -- week_parity/weekday are meaningless
  // for it (see RutScheduleLesson.lesson_date). Every ordinary recurring lesson has no
  // lesson_date and keeps matching by weekday/week_parity exactly as before.
  const dayLessons = schedule.lessons
    .filter((lesson) =>
      lesson.lesson_date
        ? lesson.lesson_date === selectedIso
        : lesson.week_parity === parity && lesson.weekday === weekday,
    )
    .sort((a, b) => a.start_time.localeCompare(b.start_time));

  return (
    <div className="capability-rut-schedule__schedule">
      <div className="capability-rut-schedule__schedule-header">
        <BackLink label="Назад к группам" onClick={onBack} />
        <h2>{schedule.group.name}</h2>
      </div>

      <div className="capability-rut-schedule__month-nav">
        <button
          type="button"
          className="capability-rut-schedule__week-arrow"
          aria-label="Предыдущая неделя"
          onClick={() => onSelectDate(addDays(selectedDate, -7))}
        >
          <Icon.ArrowLeft />
        </button>
        <span>{monthLabel(selectedDate)}</span>
        <button
          type="button"
          className="capability-rut-schedule__week-arrow"
          aria-label="Следующая неделя"
          onClick={() => onSelectDate(addDays(selectedDate, 7))}
        >
          <Icon.ArrowRight />
        </button>
      </div>

      <div className="capability-rut-schedule__day-strip">
        {weekDays.map((day) => (
          <button
            type="button"
            key={day.toISOString()}
            className={`capability-rut-schedule__day-cell${sameDay(day, selectedDate) ? " capability-rut-schedule__day-cell--active" : ""}`}
            onClick={() => onSelectDate(day)}
          >
            <span className="capability-rut-schedule__day-cell-weekday">{WEEKDAY_SHORT[day.getDay() === 0 ? 6 : day.getDay() - 1]}</span>
            <span className="capability-rut-schedule__day-cell-date">{day.getDate()}</span>
          </button>
        ))}
      </div>

      {dayLessons.length ? (
        groupByTimeSlot(dayLessons).map((slot) => (
          <section className="capability-rut-schedule__slot" key={slot[0].start_time}>
            <div className="capability-rut-schedule__lesson-time">
              <Icon.Clock />
              {slot[0].period_label
                ? `${slot[0].period_label}, ${slot[0].start_time}–${slot[0].end_time}`
                : `${slot[0].start_time}–${slot[0].end_time}`}
            </div>
            {slot.map((lesson, index) => {
              const subgroup = subgroupLabel(lesson.combined_groups);
              return (
                <article className="capability-rut-schedule__lesson" key={index}>
                  <div className="capability-rut-schedule__lesson-head">
                    <span className="capability-rut-schedule__lesson-kind">{lesson.lesson_kind}</span>
                    {subgroup ? (
                      <span className="capability-rut-schedule__subgroup-badge">{subgroup}</span>
                    ) : null}
                  </div>
                  <div className="capability-rut-schedule__lesson-discipline">
                    <Icon.Book />
                    {lesson.discipline}
                  </div>
                  {lesson.teachers ? (
                    <div className="capability-rut-schedule__lesson-meta">
                      <Icon.User />
                      {lesson.teachers}
                    </div>
                  ) : null}
                  {lesson.room ? (
                    <div className="capability-rut-schedule__lesson-meta">
                      <Icon.Map />
                      {lesson.room}
                    </div>
                  ) : null}
                  {!subgroup && lesson.combined_groups ? (
                    <div className="capability-rut-schedule__lesson-meta muted">
                      Совместно: {lesson.combined_groups}
                    </div>
                  ) : null}
                </article>
              );
            })}
          </section>
        ))
      ) : (
        <div className="card content-empty-state">В этот день занятий нет.</div>
      )}
    </div>
  );
}
