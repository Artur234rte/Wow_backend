import uuid
from datetime import datetime

from sqlalchemy import UUID, Integer, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.db import Base


class MetaSnapshot(Base):
    __tablename__ = "meta_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    role: Mapped[str] = mapped_column(String(length=16), nullable=False, index=True)
    wow_class: Mapped[str] = mapped_column(String(length=64), nullable=False)
    spec: Mapped[str] = mapped_column(String(length=64), nullable=False)
    spec_name: Mapped[str] = mapped_column(String(length=128), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    patch: Mapped[str] = mapped_column(String(length=32), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
