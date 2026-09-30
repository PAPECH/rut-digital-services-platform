"""Persistent idempotency records for one-way legacy data imports.

The records contain only technical source identifiers.  They let an operator
resume an interrupted import without duplicating attachment or status-history
rows, which do not have a natural legacy idempotency field in the target model.
"""

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base, TimestampMixin


class LegacyImportReference(Base, TimestampMixin):
    __tablename__ = "legacy_import_references"
    __table_args__ = (
        UniqueConstraint(
            "bot_instance_id",
            "source_key",
            "entity_type",
            "source_record_id",
            name="uq_legacy_import_reference_source",
        ),
        Index(
            "ix_legacy_import_references_bot_source",
            "bot_instance_id",
            "source_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_key: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_id: Mapped[int | None] = mapped_column(Integer)
