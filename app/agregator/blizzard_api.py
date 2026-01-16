"""
Модуль для работы с Blizzard Battle.net API
Получение иконок подземелий и рейдов
"""

import os
import base64
import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Blizzard API credentials
BLIZZARD_CLIENT_ID = os.getenv("BLIZZARD_CLIENT_ID")
BLIZZARD_CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET")

# Blizzard API endpoints
BLIZZARD_TOKEN_URL = "https://oauth.battle.net/token"
BLIZZARD_API_BASE = "https://us.api.blizzard.com"  # Можно менять регион: us, eu, kr, tw

# Кеш для access token
_blizzard_token_cache: Optional[Dict[str, Any]] = None
_blizzard_token_lock = asyncio.Lock()


async def get_blizzard_access_token() -> str:
    """
    Получение access token от Blizzard API с кешированием

    Документация: https://develop.battle.net/documentation/guides/using-oauth
    """
    global _blizzard_token_cache

    async with _blizzard_token_lock:
        # Проверяем кеш
        if _blizzard_token_cache and _blizzard_token_cache.get("expires_at", 0) > asyncio.get_event_loop().time():
            logger.debug("Используется закешированный Blizzard access token")
            return _blizzard_token_cache["token"]

        logger.info("Получение нового access token от Blizzard API...")

        if not BLIZZARD_CLIENT_ID or not BLIZZARD_CLIENT_SECRET:
            logger.error("❌ BLIZZARD_CLIENT_ID или BLIZZARD_CLIENT_SECRET не установлены в .env файле")
            raise ValueError("BLIZZARD_CLIENT_ID и BLIZZARD_CLIENT_SECRET должны быть установлены")

        # Создаем Basic Auth заголовок
        auth = base64.b64encode(
            f"{BLIZZARD_CLIENT_ID}:{BLIZZARD_CLIENT_SECRET}".encode()
        ).decode()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    BLIZZARD_TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {auth}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"grant_type": "client_credentials"},
                )
                r.raise_for_status()
                data = r.json()

                # Кешируем токен (обычно живет 24 часа)
                expires_in = data.get("expires_in", 86400)
                _blizzard_token_cache = {
                    "token": data["access_token"],
                    "expires_at": asyncio.get_event_loop().time() + expires_in - 3600
                }

                logger.info(f"✅ Blizzard access token получен, истекает через {expires_in // 3600} часов")
                return _blizzard_token_cache["token"]

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP ошибка при получении Blizzard токена: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ Ошибка сети при получении Blizzard токена: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при получении Blizzard токена: {e}", exc_info=True)
            raise


async def get_journal_encounter_icon(journal_id: int, locale: str = "en_US") -> Optional[str]:
    """
    Получение URL иконки encounter из Blizzard Journal API

    Args:
        journal_id: ID encounter в Journal (получаем из WarcraftLogs)
        locale: Локализация (en_US, ru_RU, etc.)

    Returns:
        URL иконки или None если не найдена

    API Docs: https://develop.battle.net/documentation/world-of-warcraft/game-data-apis
    Endpoint: /data/wow/journal-encounter/{journalEncounterId}
    """
    try:
        token = await get_blizzard_access_token()

        url = f"{BLIZZARD_API_BASE}/data/wow/journal-encounter/{journal_id}"
        params = {
            "namespace": "static-us",  # static-us, static-eu, static-kr, static-tw
            "locale": locale
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params
            )
            r.raise_for_status()
            data = r.json()

            # Структура ответа:
            # {
            #   "id": 2898,
            #   "name": "Sikran, Captain of the Sureki",
            #   "creatures": [{
            #     "id": 214503,
            #     "creature_display": {
            #       "id": 119394
            #     }
            #   }],
            #   ...
            # }

            # Пытаемся найти иконку
            # Вариант 1: Из creatures -> creature_display
            creatures = data.get("creatures", [])
            if creatures and len(creatures) > 0:
                creature = creatures[0]
                display_id = creature.get("creature_display", {}).get("id")
                if display_id:
                    # URL иконки creature display
                    icon_url = f"https://render.worldofwarcraft.com/us/npcs/zoom/creature-display-{display_id}.jpg"
                    logger.info(f"✅ Получена иконка для journal_id={journal_id}: {icon_url}")
                    return icon_url

            # Вариант 2: Если есть прямая ссылка на иконку в данных
            if "icon" in data:
                return data["icon"]

            logger.warning(f"⚠️  Не удалось найти иконку для journal_id={journal_id}")
            return None

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"⚠️  Journal encounter не найден: journal_id={journal_id}")
        else:
            logger.error(f"❌ HTTP ошибка при получении иконки для journal_id={journal_id}: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка при получении иконки для journal_id={journal_id}: {e}", exc_info=True)
        return None


async def get_journal_instance_icon(instance_id: int, locale: str = "en_US") -> Optional[str]:
    """
    Получение URL иконки подземелья (instance) из Blizzard Journal API

    Args:
        instance_id: ID подземелья в Journal
        locale: Локализация

    Returns:
        URL иконки или None

    Endpoint: /data/wow/journal-instance/{journalInstanceId}
    """
    try:
        token = await get_blizzard_access_token()

        url = f"{BLIZZARD_API_BASE}/data/wow/journal-instance/{instance_id}"
        params = {
            "namespace": "static-us",
            "locale": locale
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params
            )
            r.raise_for_status()
            data = r.json()

            # Структура ответа:
            # {
            #   "id": 1176,
            #   "name": "Ara-Kara, City of Echoes",
            #   "media": {
            #     "key": {...},
            #     "id": 1176
            #   }
            # }

            # Получаем media ID и запрашиваем иконку
            media = data.get("media", {})
            media_id = media.get("id")

            if media_id:
                media_url = f"{BLIZZARD_API_BASE}/data/wow/media/journal-instance/{media_id}"
                r2 = await client.get(
                    media_url,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params
                )
                r2.raise_for_status()
                media_data = r2.json()

                # Структура media ответа:
                # {
                #   "assets": [
                #     {"key": "tile", "value": "https://..."},
                #     {"key": "icon", "value": "https://..."}
                #   ]
                # }

                assets = media_data.get("assets", [])
                for asset in assets:
                    if asset.get("key") in ("icon", "tile"):
                        icon_url = asset.get("value")
                        logger.info(f"✅ Получена иконка для instance_id={instance_id}: {icon_url}")
                        return icon_url

            logger.warning(f"⚠️  Не удалось найти иконку для instance_id={instance_id}")
            return None

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"⚠️  Journal instance не найден: instance_id={instance_id}")
        else:
            logger.error(f"❌ HTTP ошибка при получении иконки для instance_id={instance_id}: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка при получении иконки для instance_id={instance_id}: {e}", exc_info=True)
        return None


async def test_blizzard_api():
    """Тестовая функция для проверки работы Blizzard API"""
    logger.info("=== Тест Blizzard API ===")

    # Тест 1: Получение токена
    try:
        token = await get_blizzard_access_token()
        logger.info(f"✅ Token получен: {token[:20]}...")
    except Exception as e:
        logger.error(f"❌ Не удалось получить токен: {e}")
        return

    # Тест 2: Получение иконки для рейд босса (пример: Sikran - journal_id может отличаться)
    # Нужно сначала получить journal_id из WarcraftLogs
    test_journal_id = 2898  # Примерный ID, нужно проверить
    icon = await get_journal_encounter_icon(test_journal_id)
    if icon:
        logger.info(f"✅ Иконка encounter получена: {icon}")
    else:
        logger.warning("⚠️  Иконка encounter не получена")

    # Тест 3: Получение иконки подземелья
    test_instance_id = 1176  # Примерный ID для Ara-Kara
    icon2 = await get_journal_instance_icon(test_instance_id)
    if icon2:
        logger.info(f"✅ Иконка instance получена: {icon2}")
    else:
        logger.warning("⚠️  Иконка instance не получена")


if __name__ == "__main__":
    # Для тестирования
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_blizzard_api())
