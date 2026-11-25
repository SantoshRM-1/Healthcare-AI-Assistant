import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class MedicalSource(Base):
    __tablename__ = "medical_sources"
    __table_args__ = (
        UniqueConstraint("source_key", name="uq_medical_sources_source_key"),
        Index("ix_medical_sources_status_topic", "review_status", "relevant_topic"),
        CheckConstraint(
            "review_status IN ('draft', 'pending_review', 'approved', 'rejected', 'retired')",
            name="ck_medical_sources_review_status",
        ),
        CheckConstraint(
            "medical_category IN ('condition', 'symptoms', 'laboratory_test', 'medicine', 'procedure', "
            "'preventive_healthcare', 'nutrition', 'pregnancy_maternal_health', 'child_adolescent_health', "
            "'elderly_healthcare', 'emergency_first_aid', 'medical_terminology', 'specialist_department', 'patient_education')",
            name="ck_medical_sources_medical_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    organization: Mapped[str] = mapped_column(String(240), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    medical_category: Mapped[str] = mapped_column(String(80), nullable=False, default="patient_education", server_default="patient_education")
    specialty: Mapped[str | None] = mapped_column(String(120))
    specialties: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    relevant_topic: Mapped[str] = mapped_column(String(240), nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(120))
    publication_date: Mapped[str | None] = mapped_column(String(40))
    last_updated_date: Mapped[str | None] = mapped_column(String(40))
    date_retrieved: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_version: Mapped[str | None] = mapped_column(String(120))
    license_permission: Mapped[str] = mapped_column(String(500), nullable=False)
    language: Mapped[str] = mapped_column(String(30), nullable=False, default="en", server_default="en")
    review_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending_review", server_default="pending_review")
    reviewer_clerk_id: Mapped[str | None] = mapped_column(String(255))
    created_by_clerk_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    documents: Mapped[list["MedicalKnowledgeDocument"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class MedicalKnowledgeDocument(Base):
    __tablename__ = "medical_knowledge_documents"
    __table_args__ = (
        Index("ix_medical_knowledge_documents_source_created", "source_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medical_sources.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_clerk_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    source: Mapped[MedicalSource] = relationship(back_populates="documents")
    versions: Mapped[list["MedicalKnowledgeDocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class MedicalKnowledgeDocumentVersion(Base):
    __tablename__ = "medical_knowledge_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_label", name="uq_medical_knowledge_document_version"),
        UniqueConstraint("document_id", "content_sha256", name="uq_medical_knowledge_document_hash"),
        Index("ix_medical_knowledge_versions_active_review", "is_active", "approval_status", "processing_status"),
        Index(
            "uq_medical_knowledge_one_active_version_per_document",
            "document_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        CheckConstraint(
            "approval_status IN ('draft', 'pending_review', 'approved', 'rejected', 'retired')",
            name="ck_medical_knowledge_version_approval_status",
        ),
        CheckConstraint(
            "processing_status IN ('queued', 'processing', 'ready_for_review', 'index_queued', 'indexed', 'failed')",
            name="ck_medical_knowledge_version_processing_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medical_knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    version_label: Mapped[str] = mapped_column(String(120), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cloudinary_public_id: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    cloudinary_resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", server_default="queued")
    processing_error: Mapped[str | None] = mapped_column(Text)
    approval_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending_review", server_default="pending_review")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    reviewed_by_clerk_id: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_clerk_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    document: Mapped[MedicalKnowledgeDocument] = relationship(back_populates="versions")
    chunks: Mapped[list["MedicalKnowledgeChunk"]] = relationship(back_populates="version", cascade="all, delete-orphan")


class MedicalKnowledgeChunk(Base):
    __tablename__ = "medical_knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("version_id", "chunk_index", name="uq_medical_knowledge_chunk_index"),
        Index("ix_medical_knowledge_chunks_source_version", "source_id", "version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medical_sources.id", ondelete="RESTRICT"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medical_knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medical_knowledge_document_versions.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    section: Mapped[str] = mapped_column(String(240), nullable=False)
    page: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(30), nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(120))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    version: Mapped[MedicalKnowledgeDocumentVersion] = relationship(back_populates="chunks")


class MedicalKnowledgeReview(Base):
    __tablename__ = "medical_knowledge_reviews"
    __table_args__ = (
        CheckConstraint("target_type IN ('source', 'document_version')", name="ck_medical_knowledge_review_target"),
        CheckConstraint("action IN ('approved', 'rejected', 'retired')", name="ck_medical_knowledge_review_action"),
        CheckConstraint("(target_type = 'source' AND source_id IS NOT NULL AND version_id IS NULL) OR (target_type = 'document_version' AND version_id IS NOT NULL AND source_id IS NULL)", name="ck_medical_knowledge_review_target_reference"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("medical_sources.id", ondelete="CASCADE"))
    version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("medical_knowledge_document_versions.id", ondelete="CASCADE"))
    target_type: Mapped[str] = mapped_column(String(24), nullable=False)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    reviewer_clerk_id: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class KnowledgeIngestionJob(Base):
    __tablename__ = "knowledge_ingestion_jobs"
    __table_args__ = (
        Index("ix_knowledge_ingestion_jobs_status_created", "status", "created_at"),
        CheckConstraint("operation IN ('extract', 'index')", name="ck_knowledge_job_operation"),
        CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed')", name="ck_knowledge_job_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medical_knowledge_document_versions.id", ondelete="CASCADE"), nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", server_default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
