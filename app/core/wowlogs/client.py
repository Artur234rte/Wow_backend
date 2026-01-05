from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import httpx
from httpx import HTTPStatusError, Response
from redis.asyncio import Redis
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings


class WowLogsClient:
    """Client for Warcraft Logs GraphQL API with Redis-backed token caching and locking."""

    def __init__(self, redis_client: Redis):
        self.settings = get_settings()
        self.redis = redis_client
        base_url = f"{self.settings.wowlogs_base_url}{self.settings.wowlogs_api_path}"
        self._client = httpx.AsyncClient(base_url=base_url, timeout=self.settings.request_timeout_seconds)
        self._token_url = f"{self.settings.wowlogs_base_url}{self.settings.wowlogs_token_path}"
        self._token_cache_key = "wowlogs:token"
        self._token_lock_key = "wowlogs:token:lock"

    async def _store_token(self, access_token: str, expires_in: int) -> None:
        ttl = max(expires_in - 60, 60)
        await self.redis.set(self._token_cache_key, access_token, ex=ttl)

    async def _fetch_token(self) -> str:
        if not self.settings.wowlogs_client_id or not self.settings.wowlogs_client_secret:
            raise RuntimeError("WOWLOGS_CLIENT_ID and WOWLOGS_CLIENT_SECRET must be set")

        data = {"grant_type": "client_credentials"}
        auth = (self.settings.wowlogs_client_id, self.settings.wowlogs_client_secret)

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.settings.request_retries),
            wait=wait_exponential(multiplier=self.settings.request_retry_backoff, min=1, max=10),
            retry=retry_if_exception_type(httpx.HTTPError),
        ):
            with attempt:
                async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                    response = await client.post(self._token_url, data=data, auth=auth)
                response.raise_for_status()
                payload = response.json()
                access_token = payload.get("access_token")
                expires_in = int(payload.get("expires_in", 3600))
                if not access_token:
                    raise RuntimeError("Invalid token response from Warcraft Logs")

                await self._store_token(access_token, expires_in)
                return access_token

        raise RuntimeError("Failed to fetch access token from Warcraft Logs")

    async def get_access_token(self) -> str:
        cached = await self.redis.get(self._token_cache_key)
        if cached:
            return str(cached)

        lock = self.redis.lock(self._token_lock_key, timeout=30, blocking_timeout=10)
        acquired = await lock.acquire(blocking=True)
        if not acquired:
            await asyncio.sleep(1)
            token_retry = await self.redis.get(self._token_cache_key)
            if token_retry:
                return str(token_retry)
            raise RuntimeError("Unable to acquire token lock")

        try:
            cached = await self.redis.get(self._token_cache_key)
            if cached:
                return str(cached)
            return await self._fetch_token()
        finally:
            with contextlib.suppress(Exception):
                await lock.release()

    async def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await self.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.settings.request_retries),
            wait=wait_exponential(multiplier=self.settings.request_retry_backoff, min=1, max=10),
            retry=retry_if_exception_type((httpx.HTTPError, HTTPStatusError)),
        ):
            with attempt:
                response: Response = await self._client.post(
                    "",
                    json={"query": query, "variables": variables or {}},
                    headers=headers,
                )
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "1"))
                    await asyncio.sleep(retry_after)
                    raise HTTPStatusError("Rate limited", request=response.request, response=response)
                response.raise_for_status()
                payload = response.json()
                if "errors" in payload:
                    raise RuntimeError(f"Warcraft Logs API errors: {payload['errors']}")
                return payload.get("data", {})

        raise RuntimeError("Warcraft Logs request failed after retries")

    async def aclose(self) -> None:
        await self._client.aclose()
