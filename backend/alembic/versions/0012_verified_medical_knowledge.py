"""Add verified medical source registry, versions, review log, and ingestion jobs."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_verified_medical_knowledge"
down_revision = "0011_report_processing_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "medical_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_key", sa.String(120), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("organization", sa.String(240), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("medical_category", sa.String(80), server_default="patient_education", nullable=False),
        sa.Column("specialty", sa.String(120)),
        sa.Column("specialties", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("relevant_topic", sa.String(240), nullable=False),
        sa.Column("jurisdiction", sa.String(120)),
        sa.Column("publication_date", sa.String(40)),
        sa.Column("last_updated_date", sa.String(40)),
        sa.Column("date_retrieved", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("review_date", sa.DateTime(timezone=True)),
        sa.Column("source_version", sa.String(120)),
        sa.Column("license_permission", sa.String(500), nullable=False),
        sa.Column("language", sa.String(30), server_default="en", nullable=False),
        sa.Column("review_status", sa.String(24), server_default="pending_review", nullable=False),
        sa.Column("reviewer_clerk_id", sa.String(255)),
        sa.Column("created_by_clerk_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_key", name="uq_medical_sources_source_key"),
        sa.CheckConstraint("review_status IN ('draft', 'pending_review', 'approved', 'rejected', 'retired')", name="ck_medical_sources_review_status"),
        sa.CheckConstraint("medical_category IN ('condition', 'symptoms', 'laboratory_test', 'medicine', 'procedure', 'preventive_healthcare', 'nutrition', 'pregnancy_maternal_health', 'child_adolescent_health', 'elderly_healthcare', 'emergency_first_aid', 'medical_terminology', 'specialist_department', 'patient_education')", name="ck_medical_sources_medical_category"),
    )
    op.create_index("ix_medical_sources_status_topic", "medical_sources", ["review_status", "relevant_topic"])

    op.create_table(
        "medical_knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medical_sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("created_by_clerk_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_medical_knowledge_documents_source_created", "medical_knowledge_documents", ["source_id", "created_at"])

    op.create_table(
        "medical_knowledge_document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medical_knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_label", sa.String(120), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("original_file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("cloudinary_public_id", sa.String(512), nullable=False, unique=True),
        sa.Column("cloudinary_resource_type", sa.String(20), nullable=False),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("processing_status", sa.String(24), server_default="queued", nullable=False),
        sa.Column("processing_error", sa.Text()),
        sa.Column("approval_status", sa.String(24), server_default="pending_review", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("reviewed_by_clerk_id", sa.String(255)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_clerk_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "version_label", name="uq_medical_knowledge_document_version"),
        sa.UniqueConstraint("document_id", "content_sha256", name="uq_medical_knowledge_document_hash"),
        sa.CheckConstraint("approval_status IN ('draft', 'pending_review', 'approved', 'rejected', 'retired')", name="ck_medical_knowledge_version_approval_status"),
        sa.CheckConstraint("processing_status IN ('queued', 'processing', 'ready_for_review', 'index_queued', 'indexed', 'failed')", name="ck_medical_knowledge_version_processing_status"),
    )
    op.create_index("ix_medical_knowledge_versions_active_review", "medical_knowledge_document_versions", ["is_active", "approval_status", "processing_status"])
    op.create_index("uq_medical_knowledge_one_active_version_per_document", "medical_knowledge_document_versions", ["document_id"], unique=True, postgresql_where=sa.text("is_active"))

    op.create_table(
        "medical_knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medical_sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medical_knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medical_knowledge_document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("vector_id", sa.String(200), nullable=False, unique=True),
        sa.Column("section", sa.String(240), nullable=False),
        sa.Column("page", sa.Integer()),
        sa.Column("language", sa.String(30), nullable=False),
        sa.Column("jurisdiction", sa.String(120)),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("version_id", "chunk_index", name="uq_medical_knowledge_chunk_index"),
    )
    op.create_index("ix_medical_knowledge_chunks_source_version", "medical_knowledge_chunks", ["source_id", "version_id"])

    op.create_table(
        "medical_knowledge_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medical_sources.id", ondelete="CASCADE")),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medical_knowledge_document_versions.id", ondelete="CASCADE")),
        sa.Column("target_type", sa.String(24), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("reviewer_clerk_id", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_type IN ('source', 'document_version')", name="ck_medical_knowledge_review_target"),
        sa.CheckConstraint("action IN ('approved', 'rejected', 'retired')", name="ck_medical_knowledge_review_action"),
        sa.CheckConstraint("(target_type = 'source' AND source_id IS NOT NULL AND version_id IS NULL) OR (target_type = 'document_version' AND version_id IS NOT NULL AND source_id IS NULL)", name="ck_medical_knowledge_review_target_reference"),
    )

    op.create_table(
        "knowledge_ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medical_knowledge_document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operation", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("operation IN ('extract', 'index')", name="ck_knowledge_job_operation"),
        sa.CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed')", name="ck_knowledge_job_status"),
    )
    op.create_index("ix_knowledge_ingestion_jobs_status_created", "knowledge_ingestion_jobs", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_ingestion_jobs_status_created", table_name="knowledge_ingestion_jobs")
    op.drop_table("knowledge_ingestion_jobs")
    op.drop_table("medical_knowledge_reviews")
    op.drop_index("ix_medical_knowledge_chunks_source_version", table_name="medical_knowledge_chunks")
    op.drop_table("medical_knowledge_chunks")
    op.drop_index("ix_medical_knowledge_versions_active_review", table_name="medical_knowledge_document_versions")
    op.drop_index("uq_medical_knowledge_one_active_version_per_document", table_name="medical_knowledge_document_versions")
    op.drop_table("medical_knowledge_document_versions")
    op.drop_index("ix_medical_knowledge_documents_source_created", table_name="medical_knowledge_documents")
    op.drop_table("medical_knowledge_documents")
    op.drop_index("ix_medical_sources_status_topic", table_name="medical_sources")
    op.drop_table("medical_sources")
