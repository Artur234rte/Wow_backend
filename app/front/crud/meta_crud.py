from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model import MetaBySpec

async def get_meta_by_encounter(
    session: AsyncSession,
    encounter_id: int,
    spec_type: str
):
    stmt = (
        select(MetaBySpec)
        .where(
            MetaBySpec.encounter_id == encounter_id,
            MetaBySpec.spec_type == spec_type
        )
        .order_by(MetaBySpec.meta.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_meta_aggregated(
    session: AsyncSession,
    spec_type: str
):
    """
    Получить агрегированные данные по всем энкаунтерам.
    Возвращает среднее значение meta для каждого спека по всем подземельям.
    Результаты отфильтрованы по spec_type и отсортированы по убыванию среднего значения meta.
    """
    stmt = (
        select(
            MetaBySpec.class_name,
            MetaBySpec.spec,
            MetaBySpec.spec_type,
            func.avg(MetaBySpec.meta).label('meta')
        )
        .where(MetaBySpec.spec_type == spec_type)
        .group_by(MetaBySpec.class_name, MetaBySpec.spec, MetaBySpec.spec_type)
        .order_by(func.avg(MetaBySpec.meta).desc())
    )
    result = await session.execute(stmt)
    return result.all()
