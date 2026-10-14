"""Track recoverable report OCR and vector-index attempts."""
from alembic import op
import sqlalchemy as sa

revision = "0005_report_attempts"
down_revision = "0004_ai_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploaded_reports", sa.Column("processing_attempts", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("uploaded_reports", "processing_attempts")
