from datetime import datetime

from pydantic import BaseModel, Field


class FaqOut(BaseModel):
    id: int
    question: str
    answer: str
    is_active: bool
    order: int

    model_config = {"from_attributes": True}


class FaqIn(BaseModel):
    question: str
    answer: str
    is_active: bool = True
    order: int = 0


class FaqPatch(BaseModel):
    question: str | None = None
    answer: str | None = None
    is_active: bool | None = None
    order: int | None = None


class KbDocumentOut(BaseModel):
    id: int
    topic: str
    content: str
    tags: list[str] | None = None
    is_active: bool
    created_at: datetime
    # Не-null для зеркал, автосозданных из FAQ (Task 052) — frontend-admin рендерит их
    # как read-only с пометкой «из FAQ» и не даёт редактировать напрямую.
    source_faq_id: int | None = None

    model_config = {"from_attributes": True}


class KbDocumentIn(BaseModel):
    topic: str
    content: str
    tags: list[str] | None = None
    is_active: bool = True


class KbDocumentPatch(BaseModel):
    topic: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    is_active: bool | None = None


class KbBulkIn(BaseModel):
    """Загрузка JSON-базы знаний (§5.9 ТЗ). Каждый элемент — KbDocumentIn."""

    documents: list[KbDocumentIn]
    replace: bool = False  # если true — старые документы удалить


class KbTestMatchIn(BaseModel):
    """Тестовый запрос для песочницы релевантности (admin-only, ничего не сохраняет)."""

    text: str = Field(min_length=1, max_length=2000)


class KbTestMatchHit(BaseModel):
    document_id: int
    topic: str
    content: str
    score: float


class KbTestMatchCandidate(BaseModel):
    document_id: int
    topic: str
    score: float


class KbTestMatchOut(BaseModel):
    tier: str
    hit: KbTestMatchHit | None = None  # только для tier="auto"
    candidates: list[KbTestMatchCandidate] | None = None  # только для tier="candidates"
    note: str | None = None  # пояснение для no_match/escalate/skip
