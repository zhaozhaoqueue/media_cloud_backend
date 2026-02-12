import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NoteShareCode(Base):
    __tablename__ = "note_share_codes"
    __table_args__ = (UniqueConstraint("share_code", name="note_share_codes_share_code_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("notes.id"), nullable=False)
    share_code: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
