from fastapi import APIRouter

from ..modules.admin_invites.presentation.bot_router import router as bot_invites_router
from ..modules.admin_invites.presentation.platform_router import router as platform_invites_router
from ..modules.admin_sessions.presentation.router import router as admin_session_router
from ..modules.admins.presentation.router import router as admins_router
from ..modules.analytics.presentation.router import router as analytics_router
from ..modules.analytics.presentation.stats_router import router as stats_router
from ..modules.audit.presentation.router import router as audit_router
from ..modules.bot_instances.presentation.router import router as bot_instances_router
from ..modules.bot_instances.presentation.runtime_router import router as bot_runtime_router
from ..modules.bot_instances.presentation.settings_router import router as bot_settings_router
from ..modules.bot_instances.presentation.staff_access_router import router as staff_access_router
from ..modules.campaign_links.presentation.router import router as campaign_links_router
from ..modules.capabilities.admission_rating.presentation.router import (
    router as admission_rating_router,
)
from ..modules.capabilities.presentation.router import router as capabilities_router
from ..modules.capabilities.request_status.presentation.router import (
    router as request_status_router,
)
from ..modules.capabilities.rut_schedule.presentation.admin_router import (
    router as rut_schedule_admin_router,
)
from ..modules.capabilities.rut_schedule.presentation.router import (
    router as rut_schedule_router,
)
from ..modules.consent.presentation.router import router as consent_router
from ..modules.content.presentation.router import router as content_router
from ..modules.form_tests.presentation.admin_router import router as form_tests_admin_router
from ..modules.form_tests.presentation.router import router as form_tests_router
from ..modules.forms.presentation.submissions_router import router as submissions_router
from ..modules.knowledge_base.presentation.faq_router import router as faq_router
from ..modules.knowledge_base.presentation.router import router as kb_router
from ..modules.maintenance.presentation.router import router as maintenance_router
from ..modules.news.presentation.router import router as news_router
from ..modules.platform_admins.presentation.router import router as platform_admins_router
from ..modules.profiles.presentation.admin_router import router as users_admin_router
from ..modules.profiles.presentation.auth_router import router as student_auth_router
from ..modules.profiles.presentation.router import router as profile_router
from ..modules.support_chat.presentation.messages_router import router as messages_router
from ..modules.support_chat.presentation.tickets_router import router as tickets_router
from ..modules.support_chat.presentation.ws_router import router as ws_router
from .routes import (
    files,
    forms,
    monitoring,
    rating,
)

api_router = APIRouter()
api_router.include_router(admin_session_router, prefix="/auth", tags=["auth"])
api_router.include_router(student_auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(forms.router, prefix="/forms", tags=["forms"])
api_router.include_router(submissions_router, prefix="/submissions", tags=["submissions"])
# Admin must be registered before the student router: its bare "" route resolves to
# /form-tests/admin, which would otherwise be shadowed by the student router's /{test_id}
# (Starlette matches routes in registration order, and "admin" is a syntactically valid --
# if later 422-rejected -- value for a path segment matched against {test_id}). Verified with
# a minimal repro during implementation; forms/submissions avoid this class of bug entirely by
# using disjoint prefixes instead of nesting admin under the same prefix as a catch-all id route.
api_router.include_router(
    form_tests_admin_router, prefix="/form-tests/admin", tags=["form-tests-admin"]
)
api_router.include_router(form_tests_router, prefix="/form-tests", tags=["form-tests"])
api_router.include_router(tickets_router, prefix="/tickets", tags=["tickets"])
api_router.include_router(messages_router, prefix="/messages", tags=["messages"])
api_router.include_router(users_admin_router, prefix="/users", tags=["users"])
api_router.include_router(profile_router, prefix="/profile", tags=["profile"])
api_router.include_router(faq_router, prefix="/faq", tags=["faq"])
api_router.include_router(kb_router, prefix="/kb", tags=["kb"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(stats_router, prefix="/stats", tags=["stats"])
api_router.include_router(bot_settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(admins_router, prefix="/admins", tags=["admins"])
api_router.include_router(
    platform_admins_router,
    prefix="/platform-admins",
    tags=["platform-admins"],
)
api_router.include_router(
    platform_invites_router,
    prefix="/platform-admins",
    tags=["admin-invites"],
)
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(rating.router, prefix="/rating", tags=["rating"])
api_router.include_router(ws_router, tags=["ws"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(bot_instances_router, prefix="/instances", tags=["instances"])
api_router.include_router(staff_access_router, prefix="/instances", tags=["staff-access"])
api_router.include_router(bot_invites_router, prefix="/instances", tags=["admin-invites"])
api_router.include_router(bot_runtime_router, prefix="/instances", tags=["bot-runtime"])
api_router.include_router(maintenance_router, tags=["maintenance"])
api_router.include_router(consent_router, prefix="/consent", tags=["consent"])
api_router.include_router(content_router, prefix="/content", tags=["content"])
api_router.include_router(news_router, prefix="/news", tags=["news"])
api_router.include_router(
    campaign_links_router, prefix="/campaign-links", tags=["campaign-links"]
)
api_router.include_router(capabilities_router, prefix="/capabilities", tags=["capabilities"])
api_router.include_router(
    admission_rating_router,
    prefix="/capabilities/admission-rating",
    tags=["admission-rating"],
)
api_router.include_router(
    request_status_router,
    prefix="/capabilities/request-status",
    tags=["request-status"],
)
api_router.include_router(
    rut_schedule_router,
    prefix="/capabilities/rut-schedule",
    tags=["rut-schedule"],
)
api_router.include_router(
    rut_schedule_admin_router,
    prefix="/capabilities/rut-schedule/admin",
    tags=["rut-schedule-admin"],
)
