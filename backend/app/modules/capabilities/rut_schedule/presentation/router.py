from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .....api.deps import CurrentPrincipal, require_student
from .....core.errors import not_found, service_unavailable
from .....db.session import get_db
from .....modules.bot_instances.domain.entities import BotInstance
from .....modules.maintenance.presentation.dependencies import enforce_user_access_available
from .....modules.tenancy.presentation.dependencies import require_tenant_access
from .....services.log_action import ActionType, log_action
from .....services.rate_limit import rate_limit
from ...application.use_cases import CapabilityDisabled, CapabilityNotInstalled, GetEnabledCapability
from ...domain.entities import UnknownCapability
from ...infrastructure.catalog import capability_registry
from ...infrastructure.repositories import SqlAlchemyCapabilityInstallationRepository
from ..application.use_cases import GetGroupSchedule, GetNavigationTree, GroupNotFound, ScheduleNotYetSynced
from ..domain.config import InvalidRutScheduleConfig, parse_rut_schedule_config
from ..infrastructure.repositories import SqlAlchemyRutScheduleRepository
from ..infrastructure.tree_cache import RedisScheduleTreeCache
from .schemas import (
    GroupResponse,
    GroupScheduleResponse,
    LessonResponse,
    NavigationCourseResponse,
    NavigationInstituteResponse,
    NavigationTreeResponse,
)

router = APIRouter()
_schedule_limit = rate_limit("capability_rut_schedule_lookup", limit=60, window_seconds=60)


def _bot_id(bot: BotInstance) -> int:
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    return bot.id


def _enabled(db: Session, bot_id: int):
    try:
        installation, _ = GetEnabledCapability(
            SqlAlchemyCapabilityInstallationRepository(db), capability_registry
        ).execute(bot_id, "rut_schedule")
        assert installation.id is not None
        return installation, parse_rut_schedule_config(installation.config)
    except (
        CapabilityNotInstalled,
        CapabilityDisabled,
        UnknownCapability,
        InvalidRutScheduleConfig,
    ) as exc:
        raise not_found("Capability is unavailable", code="capability_disabled") from exc


@router.get(
    "/navigation-tree",
    response_model=NavigationTreeResponse,
    dependencies=[Depends(enforce_user_access_available)],
)
def navigation_tree(
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> NavigationTreeResponse:
    bot_id = _bot_id(bot)
    _installation, _ = _enabled(db, bot_id)
    tree = GetNavigationTree(SqlAlchemyRutScheduleRepository(db), RedisScheduleTreeCache()).execute()
    return NavigationTreeResponse(
        institutes=[
            NavigationInstituteResponse(
                external_id=institute.external_id,
                name=institute.name,
                courses=[
                    NavigationCourseResponse(
                        course_number=course.course_number,
                        groups=[
                            GroupResponse(
                                external_id=group.external_id,
                                name=group.name,
                                institute_external_id=group.institute_external_id,
                                course_number=group.course_number,
                            )
                            for group in course.groups
                        ],
                    )
                    for course in institute.courses
                ],
            )
            for institute in tree.institutes
        ]
    )


@router.get(
    "/groups/{group_external_id}/schedule",
    response_model=GroupScheduleResponse,
    dependencies=[Depends(_schedule_limit), Depends(enforce_user_access_available)],
)
def group_schedule(
    group_external_id: str,
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> GroupScheduleResponse:
    bot_id = _bot_id(bot)
    installation, _config = _enabled(db, bot_id)
    try:
        result = GetGroupSchedule(SqlAlchemyRutScheduleRepository(db)).execute(group_external_id)
    except GroupNotFound as exc:
        raise not_found("Group not found", code="group_not_found") from exc
    except ScheduleNotYetSynced as exc:
        # The source site is reachable only once a night (see infrastructure/sync_worker.py) --
        # a group with nothing synced yet is a defined, temporary state, not an error to fetch
        # live and paper over.
        raise service_unavailable(
            "Расписание для этой группы ещё не синхронизировано, попробуйте позже",
            code="schedule_not_synced_yet",
        ) from exc
    log_action(
        db,
        bot_instance_id=bot_id,
        user_id=principal.user_id,
        action_type=ActionType.CAPABILITY_LOOKUP_COMPLETE,
        capability_installation_id=installation.id,
        capability_key="rut_schedule",
        capability_view_key="browse",
        outcome_code="found" if result.lessons else "empty",
    )
    db.commit()
    return GroupScheduleResponse(
        group=GroupResponse(
            external_id=result.group.external_id,
            name=result.group.name,
            institute_external_id=result.group.institute_external_id,
            course_number=result.group.course_number,
        ),
        lessons=[
            LessonResponse(
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
                lesson_date=lesson.lesson_date.isoformat() if lesson.lesson_date else None,
            )
            for lesson in result.lessons
        ],
        synced_at=result.synced_at.isoformat(),
        semester_start=result.semester_start.isoformat() if result.semester_start else None,
        semester_end=result.semester_end.isoformat() if result.semester_end else None,
    )
