import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UploadedReport(Base):
    __tablename__ = "uploaded_reports"
    __table_args__ = (
        Index("ix_uploaded_reports_session_upload_date", "session_id", "upload_date"),
        Index("ix_uploaded_reports_status_upload_date", "processing_status", "upload_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    cloudinary_public_id: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    cloudinary_resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_extracted_text: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    processing_stage: Mapped[str] = mapped_column(String(40), nullable=False, default="queued", server_default="queued")
    processing_error: Mapped[str | None] = mapped_column(Text)
    chunks_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    embeddings_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    vectors_saved: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary_data: Mapped[dict | None] = mapped_column(JSONB)
    summary_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    session: Mapped["ChatSession"] = relationship(back_populates="reports")
