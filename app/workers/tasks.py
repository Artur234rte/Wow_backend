import asyncio

import redis.asyncio as redis
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.aggregation.dps import DpsAggregator
from app.core.config import get_settings
from app.core.wowlogs.client import WowLogsClient
from app.infrastructure.database import AsyncSessionLocal, init_models
from app.models.meta_snapshot import MetaSnapshot


settings = get_settings()


async def _persist_snapshot(session: AsyncSession, snapshot: list[dict]) -> None:
    records = [MetaSnapshot(**item) for item in snapshot]
    session.add_all(records)
    await session.commit()


async def _aggregate_and_store() -> None:
    await init_models()
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    async with AsyncSessionLocal() as session:
        client = WowLogsClient(redis_client)
        aggregator = DpsAggregator(client)
        snapshot = await aggregator.build_snapshot()
        await _persist_snapshot(session, snapshot)
        await redis_client.delete("meta:dps:latest")
        await client.aclose()
    await redis_client.aclose()


@shared_task(name="app.workers.tasks.refresh_dps_meta")
def refresh_dps_meta() -> None:
    asyncio.run(_aggregate_and_store())
