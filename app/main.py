from fastapi import FastAPI, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.meta_schema import MetaBySpecResponse
from crud.meta_crud import get_meta_by_encounter
from view import get_db

app = FastAPI()

@app.get(
    "/meta",
    response_model=list[MetaBySpecResponse]
)
async def get_meta(
    encounter: int = Query(..., description="Encounter ID"),
    db: AsyncSession = Depends(get_db),
):
    data = await get_meta_by_encounter(db, encounter)
    return data

