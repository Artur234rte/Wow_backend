from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model import MetaBySpec

async def get_meta_by_encounter(
    session: AsyncSession,
    encounter_id: int
):
    stmt = (
        select(MetaBySpec)
        .where(MetaBySpec.encounter_id == encounter_id)
        .order_by(MetaBySpec.meta.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_meta_aggregated(
    session: AsyncSession
):
    """
    Получить агрегированные данные по всем энкаунтерам.
    Возвращает среднее значение meta для каждого спека по всем подземельям.
    Результаты отсортированы по убыванию среднего значения meta.
    """
    stmt = (
        select(
            MetaBySpec.class_name,
            MetaBySpec.spec,
            MetaBySpec.spec_type,
            func.avg(MetaBySpec.meta).label('meta')
        )
        .group_by(MetaBySpec.class_name, MetaBySpec.spec, MetaBySpec.spec_type)
        .order_by(func.avg(MetaBySpec.meta).desc())
    )
    result = await session.execute(stmt)
    return result.all()
