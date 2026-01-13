
from sqlalchemy.exc import SQLAlchemyError
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from dotenv import load_dotenv

load_dotenv()
raw_url = os.getenv("DATABASE_URL",  "postgresql+asyncpg://wow_user:wow_password@localhost:5432/wow_db")

DATABASE_URL = raw_url.replace(
    "postgresql://",
    "postgresql+asyncpg://",
)


engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
