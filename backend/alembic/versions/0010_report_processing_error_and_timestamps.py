"""Add missing report error and lifecycle timestamp fields."""
from alembic import op
import sqlalchemy as sa

revision = "0010_report_error_tracking"
down_revision = "0009_report_processing_stage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploaded_reports", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column("uploaded_reports", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))
    op.add_column("uploaded_reports", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))
    op.execute("UPDATE uploaded_reports SET created_at = upload_date, updated_at = upload_date WHERE created_at IS NULL")
    op.alter_column("uploaded_reports", "created_at", nullable=False, server_default=sa.func.now())
    op.alter_column("uploaded_reports", "updated_at", nullable=False, server_default=sa.func.now())


def downgrade() -> None:
    op.drop_column("uploaded_reports", "updated_at")
    op.drop_column("uploaded_reports", "created_at")
    op.drop_column("uploaded_reports", "processing_error")
