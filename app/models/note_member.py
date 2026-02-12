import uuid

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NoteMember(Base):
    __tablename__ = "note_members"
    __table_args__ = (UniqueConstraint("note_id", "user_id", name="note_members_note_id_user_id_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("notes.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    joined_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
