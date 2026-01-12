from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model import MetaBySpec

async def get_meta_by_encounter(
    session: AsyncSession,
    encounter_id: int
):
    stmt = (
        select(MetaBySpec)
        .where(MetaBySpec.encounter_id == encounter_id)
    )
    result = await session.execute(stmt)
    return result.scalars().all()
