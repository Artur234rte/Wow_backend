from pydantic import BaseModel
from typing import List, Optional


class EncounterResponse(BaseModel):
    """Схема для одного энкаунтера"""
    id: int
    name: str
    icon: Optional[str] = None  # URL иконки из Blizzard API (опционально)


class EncountersListResponse(BaseModel):
    """Схема для списка энкаунтеров"""
    name: str
    encounters: List[EncounterResponse]
