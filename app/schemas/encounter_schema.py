from pydantic import BaseModel
from typing import List


class EncounterResponse(BaseModel):
    """Схема для одного энкаунтера"""
    id: int
    name: str


class EncountersListResponse(BaseModel):
    """Схема для списка энкаунтеров"""
    name: str
    encounters: List[EncounterResponse]
