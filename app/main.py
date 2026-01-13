from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.meta_schema import MetaBySpecResponse
from app.schemas.encounter_schema import EncountersListResponse
from app.front.crud.meta_crud import get_meta_by_encounter, get_meta_aggregated
from app.db.db import get_db
from typing import Optional

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
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(
    "/meta/encounters/",
    response_model=list[MetaBySpecResponse],
    summary="Получить мету по энкаунтеру или агрегированную мету",
    description="Если указан encounter_id - возвращает мету для конкретного подземелья. Если не указан - возвращает среднюю мету по всем подземельям для каждого спека. Обязательно указать spec_type (dps/tank/healer)."
)
async def get_meta(
    spec_type: str = Query(..., description="Тип спека: dps, tank или healer"),
    encounter: Optional[int] = Query(None, description="Encounter ID (необязательный)"),
    db: AsyncSession = Depends(get_db),
):
    if encounter is not None:
        # Возвращаем данные по конкретному энкаунтеру
        data = await get_meta_by_encounter(db, encounter, spec_type)
        return data
    else:
        # Возвращаем агрегированные данные (среднее по всем энкаунтерам)
        rows = await get_meta_aggregated(db, spec_type)
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
    "/meta/encounters_id/",
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

