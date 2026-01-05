from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.aggregation.dps import DpsAggregator
from app.core.config import get_settings
from app.infrastructure.database import get_session
from app.infrastructure.redis import get_redis
from app.models.meta_snapshot import MetaSnapshot

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])


class MetaItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rank: int
    wow_class: str = Field(..., alias="class", validation_alias="class")
    spec: str
    spec_name: str
    score: int
    trend: str
    color: str


class MetaResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    role: str
    updated_at: datetime
    items: list[MetaItem]


async def _fetch_latest_snapshot(session: AsyncSession) -> list[MetaSnapshot]:
    latest_ts_stmt = (
        select(MetaSnapshot.updated_at)
        .where(MetaSnapshot.role == "dps")
        .order_by(desc(MetaSnapshot.updated_at))
        .limit(1)
    )
    latest_ts_result = await session.execute(latest_ts_stmt)
    latest_ts_row = latest_ts_result.scalar_one_or_none()
    if not latest_ts_row:
        return []

    snapshot_stmt = (
        select(MetaSnapshot)
        .where(MetaSnapshot.role == "dps", MetaSnapshot.updated_at == latest_ts_row)
        .order_by(MetaSnapshot.rank.asc())
    )
    snapshot_result = await session.execute(snapshot_stmt)
    return list(snapshot_result.scalars().all())


async def _previous_ranks(session: AsyncSession) -> dict[str, int]:
    timestamps_stmt = (
        select(MetaSnapshot.updated_at)
        .where(MetaSnapshot.role == "dps")
        .distinct()
        .order_by(desc(MetaSnapshot.updated_at))
        .limit(2)
    )
    timestamps = [row[0] for row in (await session.execute(timestamps_stmt)).all()]
    if len(timestamps) < 2:
        return {}
    previous_ts = timestamps[1]
    prev_stmt = select(MetaSnapshot.spec, MetaSnapshot.rank).where(
        MetaSnapshot.role == "dps", MetaSnapshot.updated_at == previous_ts
    )
    prev_rows = await session.execute(prev_stmt)
    return {spec: rank for spec, rank in prev_rows.all()}


def _trend(current_rank: int, previous_rank: int | None) -> str:
    if previous_rank is None:
        return "same"
    if previous_rank > current_rank:
        return "up"
    if previous_rank < current_rank:
        return "down"
    return "same"


@router.get("/dps", response_model=MetaResponse)
async def get_dps_meta(
    session: AsyncSession = Depends(get_session),
    redis_client: redis.Redis = Depends(get_redis),
) -> MetaResponse:
    settings = get_settings()
    cache_key = "meta:dps:latest"
    cached = await redis_client.get(cache_key)
    if cached:
        return MetaResponse.model_validate_json(cached)

    rows = await _fetch_latest_snapshot(session)
    if not rows:
        raise HTTPException(status_code=404, detail="No meta snapshot available")

    previous = await _previous_ranks(session)
    aggregator_colors = DpsAggregator.color_for_class

    items = [
        MetaItem(
            rank=row.rank,
            wow_class=row.wow_class,
            spec=row.spec,
            spec_name=row.spec_name,
            score=row.score,
            trend=_trend(row.rank, previous.get(row.spec)),
            color=aggregator_colors(row.wow_class),
        )
        for row in rows
    ]

    response = MetaResponse(role="dps", updated_at=rows[0].updated_at, items=items)
    await redis_client.set(cache_key, response.model_dump_json(by_alias=True), ex=settings.cache_ttl_seconds)
    return response
