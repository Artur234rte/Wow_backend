from fastapi import FastAPI, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.meta_schema import MetaBySpecResponse
from app.front.crud.meta_crud import get_meta_by_encounter
from app.db.db import get_db

app = FastAPI()

@app.get(
    "/meta/encounters/",
    response_model=list[MetaBySpecResponse]
)
async def get_meta(
    encounter: int = Query(..., description="Encounter ID"),
    db: AsyncSession = Depends(get_db),
):
    data = await get_meta_by_encounter(db, encounter)
    return data

