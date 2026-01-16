from sqlalchemy import (
    String, Integer, SmallInteger, Numeric, DateTime, func, Float, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class MetaBySpec(Base):
    __tablename__ = "meta_by_spec"
    __table_args__ = (
        UniqueConstraint('class_name', 'spec', 'encounter_id', 'key', name='uix_class_spec_encounter_key'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_name: Mapped[str] = mapped_column(String(30))
    spec: Mapped[str] = mapped_column(String(30))
    meta: Mapped[float] = mapped_column(Float)
    spec_type: Mapped[str] = mapped_column(String(30))
    encounter_id: Mapped[int] = mapped_column(Integer)

    # Новые поля для разделения low/high keys
    key: Mapped[str] = mapped_column(String(10), nullable=False)  # "low" или "high" или "raid" для рейдов
    average_dps: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)  # Средний DPS
    max_key_level: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)  # Максимальный уровень ключа (только для high keys)
