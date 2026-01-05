import contextlib
from typing import AsyncIterator

from fastapi import FastAPI

from app.api import routes
from app.core.config import get_settings
from app.infrastructure.database import init_models, close_engine


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_models()
    yield
    await close_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    app.include_router(routes.router)
    return app


app = create_app()
