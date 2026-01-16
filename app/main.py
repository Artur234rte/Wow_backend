from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.meta_schema import MetaBySpecMythicPlusResponse, MetaBySpecRaidResponse
from app.schemas.encounter_schema import EncountersListResponse
from app.front.crud.meta_crud import get_meta_by_encounter, get_meta_aggregated
from app.db.db import get_db
from app.agregator.constant import ENCOUNTERS, RAID
from typing import Optional, Union

app = FastAPI(
    redirect_slashes=False  # Отключаем автоматический редирект для trailing slash
)

# Настройка CORS - должна быть ПЕРЕД всеми роутами
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://wowggdev.netlify.app",
        "https://wowbackend-production.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["GET"],  # Только GET для read-only API
    allow_headers=["Content-Type", "Authorization"],
)

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Healthcheck endpoint для мониторинга состояния сервиса.
    Используется в production для автоматических проверок доступности.
    """
    return {
        "status": "healthy",
        "service": "WoW Meta API"
    }


def is_raid_encounter(encounter_id: int) -> bool:
    """Определяет, является ли encounter рейдом"""
    return encounter_id in RAID


def is_mythic_plus_encounter(encounter_id: int) -> bool:
    """Определяет, является ли encounter Mythic+"""
    return encounter_id in ENCOUNTERS

@app.get(
    "/meta/encounters/",
    response_model=Union[list[MetaBySpecMythicPlusResponse], list[MetaBySpecRaidResponse]],
    summary="Получить мету по энкаунтеру или агрегированную мету",
    description="Если указан encounter - возвращает мету для конкретного подземелья/рейда. Если не указан - возвращает среднюю мету по всем подземельям для каждого спека. Обязательно указать spec_type (dps/tank/healer). Для M+ параметр key_type позволяет выбрать: 'all' (среднее между low и high, по умолчанию), 'low' или 'high'. Для рейдов key_type игнорируется."
)
async def get_meta(
    spec_type: str = Query(..., description="Тип спека: dps, tank или healer"),
    encounter: Optional[int] = Query(None, description="Encounter ID (необязательный)"),
    key_type: str = Query("all", description="Тип ключа: all (среднее между low и high), low или high (по умолчанию all, только для M+)"),
    db: AsyncSession = Depends(get_db),
):
    if encounter is not None:
        # Определяем тип контента
        is_raid = is_raid_encounter(encounter)

        # Возвращаем данные по конкретному энкаунтеру
        data = await get_meta_by_encounter(db, encounter, spec_type, key_type, is_raid)
        return data
    else:
        # Возвращаем агрегированные данные (среднее по всем энкаунтерам M+)
        # Для агрегации используем только M+ данные
        rows = await get_meta_aggregated(db, spec_type, key_type)
        # Преобразуем результат в формат MetaBySpecMythicPlusResponse
        return [
            MetaBySpecMythicPlusResponse(
                class_name=row.class_name,
                spec=row.spec,
                meta=int(row.meta),
                spec_type=row.spec_type,
                average_dps=row.average_dps,
                max_key=row.max_key,
            )
            for row in rows
        ]


@app.get(
    "/meta/encounters_id/",
    response_model=EncountersListResponse,
    summary="Получить список всех доступных M+ подземелий",
    description="Возвращает список подземелий текущего сезона Mythic+ с их ID и названиями"
)
async def get_encounters_list():
    """
    Возвращает список подземелий Mythic+ Season 3

    Этот эндпоинт не требует параметров и возвращает список
    подземелий из константы ENCOUNTERS с их идентификаторами и названиями.
    """
    return {
        "name": "Mythic+ Season 3",
        "encounters": [
            {"id": encounter_id, "name": encounter_name}
            for encounter_id, encounter_name in ENCOUNTERS.items()
        ]
    }


@app.get(
    "/meta/raids_id/",
    response_model=EncountersListResponse,
    summary="Получить список всех рейд боссов",
    description="Возвращает список боссов текущего рейда с их ID и названиями"
)
async def get_raids_list():
    """
    Возвращает список рейд боссов

    Этот эндпоинт не требует параметров и возвращает список
    боссов из константы RAID с их идентификаторами и названиями.
    """
    return {
        "name": "Nerub-ar Palace",
        "encounters": [
            {"id": raid_id, "name": raid_name}
            for raid_id, raid_name in RAID.items()
        ]
    }

