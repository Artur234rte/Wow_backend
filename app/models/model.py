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
        UniqueConstraint('class_name', 'spec', 'encounter_id', name='uix_class_spec_encounter'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_name: Mapped[str] = mapped_column(String(30))
    spec: Mapped[str] = mapped_column(String(30))
    meta: Mapped[float] = mapped_column(Float)
    spec_type: Mapped[str] = mapped_column(String(30))
    encounter_id: Mapped[int] = mapped_column(Integer)
