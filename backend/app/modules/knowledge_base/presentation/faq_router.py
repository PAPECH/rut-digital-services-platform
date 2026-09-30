from dataclasses import replace

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, get_current_principal, require_admin, require_student
from ....core.errors import not_found
from ....db.session import get_db
from ....services.log_action import ActionType, log_action
from ...bot_instances.domain.entities import BotInstance
from ...tenancy.presentation.dependencies import require_tenant_access
from ..application.use_cases import create_faq_mirror, sync_faq_mirror
from ..domain.entities import KbFaq
from ..infrastructure.embedding import FastEmbedEmbeddingPort
from ..infrastructure.repositories import SqlAlchemyKbDocumentRepository, SqlAlchemyKbFaqRepository
from .schemas import FaqIn, FaqOut, FaqPatch

router = APIRouter()


@router.get("", response_model=list[FaqOut])
def list_faq(
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(get_current_principal),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[KbFaq]:
    return SqlAlchemyKbFaqRepository(db).list_all(bot.id, active_only=p.role == "student")


@router.post("/events/open", status_code=status.HTTP_204_NO_CONTENT)
def record_faq_open(
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> Response:
    if p.user_id is not None and bot.id is not None:
        log_action(
            session=db,
            bot_instance_id=bot.id,
            user_id=p.user_id,
            action_type=ActionType.FAQ_OPEN,
            commit=True,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=FaqOut, status_code=201)
def create_faq(
    payload: FaqIn,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
) -> KbFaq:
    faq = SqlAlchemyKbFaqRepository(db).add(
        KbFaq(id=None, bot_instance_id=bot.id, **payload.model_dump())
    )
    # Зеркало в kb_documents — тем же путём (эмбеддинг), что и обычный документ,
    # чтобы вопрос из FAQ участвовал в семантическом матчинге. См. docs/tasks/052.
    create_faq_mirror(
        faq,
        SqlAlchemyKbDocumentRepository(db),
        FastEmbedEmbeddingPort(),
        uploaded_by=p.admin_id,
    )
    db.commit()
    return faq


@router.patch("/{faq_id}", response_model=FaqOut)
def patch_faq(
    faq_id: int,
    payload: FaqPatch,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
) -> KbFaq:
    repository = SqlAlchemyKbFaqRepository(db)
    current = repository.get(faq_id, bot.id)
    if current is None:
        raise not_found("FAQ не найден")
    updated = replace(current, **payload.model_dump(exclude_unset=True))
    faq = repository.update(updated)
    # Держим зеркало в kb_documents в актуальном состоянии — единственное место, где
    # можно менять его содержимое, это здесь, через /faq (см. presentation/router.py).
    sync_faq_mirror(faq, SqlAlchemyKbDocumentRepository(db), FastEmbedEmbeddingPort())
    db.commit()
    return faq


@router.delete("/{faq_id}", status_code=204)
def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
):
    repository = SqlAlchemyKbFaqRepository(db)
    if repository.get(faq_id, bot.id) is None:
        raise not_found("FAQ не найден")
    repository.delete(faq_id, bot.id)
    db.commit()
