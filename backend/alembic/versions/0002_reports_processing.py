"""Add report ownership, metadata and OCR processing fields."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_reports"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploaded_reports", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("uploaded_reports", sa.Column("file_type", sa.String(length=100), nullable=False, server_default="application/octet-stream"))
    op.add_column("uploaded_reports", sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("uploaded_reports", sa.Column("cloudinary_public_id", sa.String(length=512), nullable=True))
    op.add_column("uploaded_reports", sa.Column("cloudinary_resource_type", sa.String(length=20), nullable=False, server_default="raw"))
    op.add_column("uploaded_reports", sa.Column("raw_extracted_text", sa.Text(), nullable=True))
    op.add_column("uploaded_reports", sa.Column("processing_status", sa.String(length=20), nullable=False, server_default="pending"))
    op.add_column("uploaded_reports", sa.Column("upload_date", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE uploaded_reports SET user_id = chat_sessions.user_id, cloudinary_public_id = uploaded_reports.id::text, upload_date = uploaded_reports.created_at FROM chat_sessions WHERE chat_sessions.id = uploaded_reports.session_id")
    op.alter_column("uploaded_reports", "user_id", nullable=False)
    op.alter_column("uploaded_reports", "cloudinary_public_id", nullable=False)
    op.alter_column("uploaded_reports", "upload_date", nullable=False, server_default=sa.func.now())
    op.create_foreign_key("fk_uploaded_reports_user_id_users", "uploaded_reports", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_uploaded_reports_user_id", "uploaded_reports", ["user_id"])
    op.create_unique_constraint("uq_uploaded_reports_cloudinary_public_id", "uploaded_reports", ["cloudinary_public_id"])
    op.drop_column("uploaded_reports", "created_at")


def downgrade() -> None:
    op.add_column("uploaded_reports", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE uploaded_reports SET created_at = upload_date")
    op.alter_column("uploaded_reports", "created_at", nullable=False, server_default=sa.func.now())
    op.drop_constraint("uq_uploaded_reports_cloudinary_public_id", "uploaded_reports", type_="unique")
    op.drop_index("ix_uploaded_reports_user_id", table_name="uploaded_reports")
    op.drop_constraint("fk_uploaded_reports_user_id_users", "uploaded_reports", type_="foreignkey")
    for column in ("upload_date", "processing_status", "raw_extracted_text", "cloudinary_resource_type", "cloudinary_public_id", "file_size", "file_type", "user_id"):
        op.drop_column("uploaded_reports", column)
