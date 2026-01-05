from fastapi import APIRouter

from app.api import health
from app.api.v1 import meta

router = APIRouter()
router.include_router(health.router)
router.include_router(meta.router)
