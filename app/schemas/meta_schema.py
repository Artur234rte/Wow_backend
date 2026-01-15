from pydantic import BaseModel
from typing import Optional


class MetaBySpecBaseResponse(BaseModel):
    """Базовый класс с общими полями для M+ и Raid"""
    class_name: str
    spec: str
    meta: int | None
    spec_type: str
    encounter_id: Optional[int] = None
    average_dps: Optional[float] = None

    class Config:
        from_attributes = True


class MetaBySpecMythicPlusResponse(MetaBySpecBaseResponse):
    """Схема для Mythic+ данных"""
    max_key: Optional[int] = None  # Максимальный уровень ключа (только для high)


class MetaBySpecRaidResponse(MetaBySpecBaseResponse):
    """Схема для Raid данных"""
    pass

