from app.agregator.constant import TOKEN_URL, CLIENT_ID, CLIENT_SECRET, WOW_CLASS_SPECS, SPEC_ROLE_METRIC, API_URL, RIO_URL
from app.agregator.quieres import q_with_gear_and_talent, q_balance, q_simple
import base64
import httpx
import json
import asyncio
import re
import unicodedata
from app.models.model import MetaBySpec, Base
from sqlalchemy.exc import SQLAlchemyError

from typing import Optional, List, Dict, Any
from app.db.db import engine, AsyncSessionLocal


# Глобальный кеш для access token
_token_cache: Optional[Dict[str, Any]] = None
_token_lock = asyncio.Lock()

# Семафоры для rate limiting
_api_semaphore = asyncio.Semaphore(10)  # Макс 10 одновременных запросов к WarcraftLogs
_rio_semaphore = asyncio.Semaphore(30)  # Макс 30 одновременных запросов к RaiderIO


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def batch_add_meta_by_spec(objects: List[MetaBySpec]) -> List[MetaBySpec]:
    """Батчинг для вставки записей в БД - намного быстрее чем по одной"""
    if not objects:
        return []

    async with AsyncSessionLocal() as session:
        try:
            session.add_all(objects)
            await session.commit()
            for obj in objects:
                await session.refresh(obj)
            return objects
        except SQLAlchemyError as e:
            await session.rollback()
            print(f"Database error: {e}")
            raise


async def get_access_token() -> str:
    """Получение access token с кешированием"""
    global _token_cache

    async with _token_lock:
        # Проверяем, есть ли действующий токен в кеше
        if _token_cache and _token_cache.get("expires_at", 0) > asyncio.get_event_loop().time():
            return _token_cache["token"]

        # Получаем новый токен
        auth = base64.b64encode(
            f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
        ).decode()

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
            r.raise_for_status()
            data = r.json()

            # Кешируем токен (обычно живет 24 часа, ставим 23 для безопасности)
            _token_cache = {
                "token": data["access_token"],
                "expires_at": asyncio.get_event_loop().time() + data.get("expires_in", 82800) - 3600
            }
            return _token_cache["token"]


async def balance():
    token = await get_access_token()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={"query": q_balance},
        )
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))


def normalize_region(region: str) -> str:
    """
    EU / eu / Europe -> eu
    US / us / America -> us
    """
    region = region.strip().lower()

    if region in ("eu", "europe"):
        return "eu"
    if region in ("us", "america", "na"):
        return "us"
    if region in ("kr", "korea"):
        return "kr"
    if region in ("tw", "taiwan"):
        return "tw"

    raise ValueError(f"Unknown region: {region}")


def normalize_realm(realm: str) -> str:
    """
    'Tarren Mill' -> 'tarren-mill'
    'Twisting Nether' -> 'twisting-nether'
    'Quel'Thalas' -> 'quel-thalas'
    """
    realm = realm.strip().lower()
    realm = unicodedata.normalize("NFKD", realm)
    realm = realm.encode("ascii", "ignore").decode("ascii")
    realm = re.sub(r"[^a-z0-9\s-]", "", realm)
    realm = re.sub(r"[\s-]+", "-", realm)
    return realm


async def fetch_rio_with_retry(
    client: httpx.AsyncClient,
    region: str,
    realm: str,
    name: str,
    max_retries: int = 3
) -> Optional[float]:
    """Получение RIO score с retry механизмом и rate limiting"""
    params = {
        "region": region,
        "realm": realm,
        "name": name,
        "fields": "mythic_plus_scores_by_season:current"
    }

    for attempt in range(max_retries):
        try:
            async with _rio_semaphore:
                r = await client.get(RIO_URL, params=params, timeout=10)
                r.raise_for_status()
                data = r.json()

                seasons = data.get("mythic_plus_scores_by_season", [])
                if not seasons:
                    return None

                scores = seasons[0]["scores"]
                return scores.get("all")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None  # Игрок не найден
            if attempt < max_retries - 1:
                await asyncio.sleep(0.1 * (attempt + 1))  # Экспоненциальный backoff
            else:
                return None
        except (httpx.TimeoutException, httpx.RequestError):
            if attempt < max_retries - 1:
                await asyncio.sleep(0.1 * (attempt + 1))
            else:
                return None
    return None


async def fetch_leaderboard_optimized(
    client: httpx.AsyncClient,
    token: str,
    encounter_id: int,
    class_name: str,
    spec_name: str
) -> Optional[float]:
    """Оптимизированная версия fetch_leaderboard - возвращает только среднее RIO"""
    variables = {
        "encounterID": encounter_id,
        "className": class_name,
        "specName": spec_name,
    }

    try:
        async with _api_semaphore:
            r = await client.post(
                API_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "query": q_simple,
                    "variables": variables,
                },
                timeout=30
            )
            r.raise_for_status()
            data = r.json()

        rankings_block = data.get("data", {}).get("worldData", {}).get("encounter", {}).get("characterRankings")
        if not rankings_block or "rankings" not in rankings_block:
            return None

        # Собираем задачи для параллельного получения RIO
        rio_tasks = []
        for item in rankings_block["rankings"]:
            hidden = item.get("hidden", False)
            server_obj = item.get("server") or {}
            server_name = server_obj.get("name", "")
            server_region = server_obj.get("region", "")

            if not hidden and server_name and server_region and item.get("name") != "Anonymous":
                server = normalize_realm(server_name)
                region = server_region.lower()
                rio_tasks.append(fetch_rio_with_retry(client, region, server, item["name"]))

        # Параллельное выполнение всех RIO запросов
        rio_results = await asyncio.gather(*rio_tasks, return_exceptions=True)

        # Подсчет среднего
        total_score = 0.0
        counter_players_with_score = 0

        for rio_result in rio_results:
            if isinstance(rio_result, (int, float)) and rio_result is not None:
                total_score += float(rio_result)
                counter_players_with_score += 1

        if counter_players_with_score == 0:
            return None

        average_score = total_score / counter_players_with_score
        return average_score

    except Exception as e:
        print(f"Error fetching leaderboard for {class_name} {spec_name} on encounter {encounter_id}: {e}")
        return None


async def fetch_single_spec_meta(
    client: httpx.AsyncClient,
    token: str,
    encounter_id: int,
    class_name: str,
    spec_name: str
) -> Optional[MetaBySpec]:
    """Получение меты для одной спеки одного босса"""
    meta_average_value = await fetch_leaderboard_optimized(
        client, token, encounter_id, class_name, spec_name
    )

    if meta_average_value is None:
        print(f"No data for {class_name} {spec_name} on encounter {encounter_id}")
        return None

    return MetaBySpec(
        class_name=class_name,
        spec=spec_name,
        meta=meta_average_value,
        spec_type=SPEC_ROLE_METRIC[spec_name][0],
        encounter_id=encounter_id
    )


async def test_leaderboard():
    """Основная функция сбора данных - ОПТИМИЗИРОВАННАЯ"""
    token = await get_access_token()

    # ID боссов
    encounters = [
        62660,   # Ulgrax the Devourer
        12830,   # The Bloodbound Horror
        62287,   # Sikran
        62773,   # Rasha'nan
        62649,   # Broodtwister Ovi'nax
        112442,  # Nexus-Princess Ky'veza
        112441,  # The Silken Court
        62662    # Queen Ansurek
    ]

    async with httpx.AsyncClient(timeout=60) as client:
        # Создаем все задачи для параллельного выполнения
        tasks = []
        for encounter_id in encounters:
            for class_name, specs in WOW_CLASS_SPECS.items():
                for spec_name in specs:
                    task = fetch_single_spec_meta(
                        client, token, encounter_id, class_name, spec_name
                    )
                    tasks.append(task)

        print(f"Запускаем {len(tasks)} задач параллельно...")

        # Выполняем ВСЕ запросы параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Фильтруем успешные результаты
        valid_objects = []
        for result in results:
            if isinstance(result, MetaBySpec):
                valid_objects.append(result)
            elif isinstance(result, Exception):
                print(f"Task failed: {result}")

        print(f"Получено {len(valid_objects)} валидных записей из {len(tasks)}")

        # Батчинг для записи в БД
        if valid_objects:
            batch_size = 50
            for i in range(0, len(valid_objects), batch_size):
                batch = valid_objects[i:i + batch_size]
                try:
                    await batch_add_meta_by_spec(batch)
                    print(f"Сохранено {len(batch)} записей в БД (batch {i//batch_size + 1})")
                except Exception as e:
                    print(f"Error saving batch: {e}")

        print(f"Всего сохранено {len(valid_objects)} записей")
        return valid_objects


async def main():
    await test_leaderboard()
    await balance()


import time
if __name__ == "__main__":
    start = time.perf_counter()
    asyncio.run(main())
    end = time.perf_counter()
    print(f"Время выполнения: {end - start:.6f} сек")
