import uuid

from sqlalchemy import Float, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Hospital(Base):
    __tablename__ = "hospitals"
    __table_args__ = (Index("ix_hospitals_city_specialization", "city", "specialization"), UniqueConstraint("name", "city", "specialization", name="uq_hospitals_name_city_specialty"))

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    specialization: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(80))
    website: Mapped[str | None] = mapped_column(String(500))
    rating: Mapped[float | None] = mapped_column(Float)
