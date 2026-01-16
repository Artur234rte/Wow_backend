from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model import MetaBySpec
from app.schemas.meta_schema import MetaBySpecMythicPlusResponse, MetaBySpecRaidResponse
from typing import Union

async def get_meta_by_encounter(
    session: AsyncSession,
    encounter_id: int,
    spec_type: str,
    key_type: str = "all",
    is_raid: bool = False
) -> Union[list[MetaBySpecMythicPlusResponse], list[MetaBySpecRaidResponse]]:
    """
    Получить мету по конкретному encounter

    Args:
        session: AsyncSession
        encounter_id: ID encounter
        spec_type: Тип спека (dps/tank/healer)
        key_type: Тип ключа ("all", "low" или "high", по умолчанию "all", игнорируется для рейдов)
        is_raid: Является ли encounter рейдом
    """
    if is_raid:
        # Для рейдов key=None
        stmt = (
            select(MetaBySpec)
            .where(
                MetaBySpec.encounter_id == encounter_id,
                MetaBySpec.spec_type == spec_type,
                MetaBySpec.key.is_(None)
            )
            .order_by(MetaBySpec.meta.desc())
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

        return [
            MetaBySpecRaidResponse(
                class_name=row.class_name,
                spec=row.spec,
                meta=int(row.meta) if row.meta else None,
                spec_type=row.spec_type,
                encounter_id=row.encounter_id,
                average_dps=row.average_dps
            )
            for row in rows
        ]
    else:
        # Для M+ используем key_type
        if key_type == "all":
            # Агрегируем данные между low и high ключами
            stmt = (
                select(
                    MetaBySpec.class_name,
                    MetaBySpec.spec,
                    MetaBySpec.spec_type,
                    func.avg(MetaBySpec.meta).label('meta'),
                    func.avg(MetaBySpec.average_dps).label('average_dps'),
                    func.max(MetaBySpec.max_key_level).label('max_key')
                )
                .where(
                    MetaBySpec.encounter_id == encounter_id,
                    MetaBySpec.spec_type == spec_type,
                    MetaBySpec.key.in_(["low", "high"])
                )
                .group_by(MetaBySpec.class_name, MetaBySpec.spec, MetaBySpec.spec_type)
                .order_by(func.avg(MetaBySpec.meta).desc())
            )
            result = await session.execute(stmt)
            rows = result.all()

            return [
                MetaBySpecMythicPlusResponse(
                    class_name=row.class_name,
                    spec=row.spec,
                    meta=int(row.meta) if row.meta else None,
                    spec_type=row.spec_type,
                    encounter_id=encounter_id,
                    average_dps=row.average_dps,
                    max_key=row.max_key
                )
                for row in rows
            ]
        else:
            # Для конкретного low или high
            stmt = (
                select(MetaBySpec)
                .where(
                    MetaBySpec.encounter_id == encounter_id,
                    MetaBySpec.spec_type == spec_type,
                    MetaBySpec.key == key_type
                )
                .order_by(MetaBySpec.meta.desc())
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

            return [
                MetaBySpecMythicPlusResponse(
                    class_name=row.class_name,
                    spec=row.spec,
                    meta=int(row.meta) if row.meta else None,
                    spec_type=row.spec_type,
                    encounter_id=row.encounter_id,
                    average_dps=row.average_dps,
                    max_key=row.max_key_level
                )
                for row in rows
            ]


async def get_meta_aggregated(
    session: AsyncSession,
    spec_type: str,
    key_type: str = "all"
):
    """
    Получить агрегированные данные по всем энкаунтерам.
    Возвращает среднее значение meta для каждого спека по всем подземельям.
    Результаты отфильтрованы по spec_type и отсортированы по убыванию среднего значения meta.

    Args:
        session: AsyncSession
        spec_type: Тип спека (dps/tank/healer)
        key_type: Тип ключа ("all", "low" или "high", по умолчанию "all")
    """
    if key_type == "all":
        # Агрегируем данные между low и high ключами по всем подземельям
        stmt = (
            select(
                MetaBySpec.class_name,
                MetaBySpec.spec,
                MetaBySpec.spec_type,
                func.avg(MetaBySpec.meta).label('meta'),
                func.avg(MetaBySpec.average_dps).label('average_dps'),
                func.max(MetaBySpec.max_key_level).label('max_key')
            )
            .where(
                MetaBySpec.spec_type == spec_type,
                MetaBySpec.key.in_(["low", "high"])
            )
            .group_by(MetaBySpec.class_name, MetaBySpec.spec, MetaBySpec.spec_type)
            .order_by(func.avg(MetaBySpec.meta).desc())
        )
    else:
        # Для конкретного low или high
        stmt = (
            select(
                MetaBySpec.class_name,
                MetaBySpec.spec,
                MetaBySpec.spec_type,
                func.avg(MetaBySpec.meta).label('meta'),
                func.avg(MetaBySpec.average_dps).label('average_dps'),
                func.max(MetaBySpec.max_key_level).label('max_key')
            )
            .where(
                MetaBySpec.spec_type == spec_type,
                MetaBySpec.key == key_type
            )
            .group_by(MetaBySpec.class_name, MetaBySpec.spec, MetaBySpec.spec_type)
            .order_by(func.avg(MetaBySpec.meta).desc())
        )
    result = await session.execute(stmt)
    return result.all()
