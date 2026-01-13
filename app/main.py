from fastapi import FastAPI, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.meta_schema import MetaBySpecResponse
from app.schemas.encounter_schema import EncountersListResponse
from app.front.crud.meta_crud import get_meta_by_encounter, get_meta_aggregated
from app.db.db import get_db
from typing import Optional

app = FastAPI()

@app.get(
    "/meta/encounters/",
    response_model=list[MetaBySpecResponse],
    summary="Получить мету по энкаунтеру или агрегированную мету",
    description="Если указан encounter_id - возвращает мету для конкретного подземелья. Если не указан - возвращает среднюю мету по всем подземельям для каждого спека."
)
async def get_meta(
    encounter: Optional[int] = Query(None, description="Encounter ID (необязательный)"),
    db: AsyncSession = Depends(get_db),
):
    if encounter is not None:
        # Возвращаем данные по конкретному энкаунтеру
        data = await get_meta_by_encounter(db, encounter)
        return data
    else:
        # Возвращаем агрегированные данные (среднее по всем энкаунтерам)
        rows = await get_meta_aggregated(db)
        # Преобразуем результат в формат MetaBySpecResponse
        return [
            MetaBySpecResponse(
                class_name=row.class_name,
                spec=row.spec,
                meta=int(row.meta),
                spec_type=row.spec_type
            )
            for row in rows
        ]


@app.get(
    "/meta/encounters_id",
    response_model=EncountersListResponse,
    summary="Получить список всех доступных энкаунтеров",
    description="Возвращает список энкаунтеров текущего сезона Mythic+ с их ID и названиями"
)
async def get_encounters_list():
    """
    Возвращает список энкаунтеров Mythic+ Season 3

    Этот эндпоинт не требует параметров и возвращает статический список
    энкаунтеров с их идентификаторами и названиями.
    """
    return {
        "name": "Mythic+ Season 3",
        "encounters": [
            {
                "id": 62660,
                "name": "Ara-Kara, City of Echoes"
            },
            {
                "id": 12830,
                "name": "Eco-Dome Al'dani"
            },
            {
                "id": 62287,
                "name": "Halls of Atonement"
            },
            {
                "id": 62773,
                "name": "Operation: Floodgate"
            },
            {
                "id": 62649,
                "name": "Priory of the Sacred Flame"
            },
            {
                "id": 112442,
                "name": "Tazavesh: So'leah's Gambit"
            },
            {
                "id": 112441,
                "name": "Tazavesh: Streets of Wonder"
            },
            {
                "id": 62662,
                "name": "The Dawnbreaker"
            }
        ]
    }

