"""Add session language, isolated memory, and recommendation history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_language_memory"
down_revision = "0005_report_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("language_mode", sa.String(length=20), server_default="auto", nullable=False))
    op.create_table(
        "session_memories",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_session_memories_user_id", "session_memories", ["user_id"])
    op.create_table(
        "recommendation_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recommendation_history_user_id", "recommendation_history", ["user_id"])
    op.create_index("ix_recommendation_history_session_id", "recommendation_history", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendation_history_session_id", table_name="recommendation_history")
    op.drop_index("ix_recommendation_history_user_id", table_name="recommendation_history")
    op.drop_table("recommendation_history")
    op.drop_index("ix_session_memories_user_id", table_name="session_memories")
    op.drop_table("session_memories")
    op.drop_column("chat_sessions", "language_mode")
