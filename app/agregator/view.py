from app.agregator.constant import TOKEN_URL, CLIENT_ID, CLIENT_SECRET, WOW_CLASS_SPECS, SPEC_ROLE_METRIC, API_URL, RIO_URL
from app.agregator.quieres import q_with_gear_and_talent, q_balance, q_simple
import base64
import httpx
import json
import asyncio
import re
import unicodedata
import logging
from app.models.model import MetaBySpec, Base
from sqlalchemy.exc import SQLAlchemyError

from typing import Optional, List, Dict, Any
from app.db.db import engine, AsyncSessionLocal

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wow_aggregator.log')
    ]
)
logger = logging.getLogger(__name__)

# Глобальный кеш для access token
_token_cache: Optional[Dict[str, Any]] = None
_token_lock = asyncio.Lock()

# Семафоры для rate limiting
_api_semaphore = asyncio.Semaphore(5)  # Макс 5 одновременных запросов к WarcraftLogs
_rio_semaphore = asyncio.Semaphore(5)  # Макс 3 одновременных запроса к RaiderIO (строгий лимит)

# Глобальный rate limit для RaiderIO
_rio_last_request_time = 0.0
_rio_min_interval = 0.3  # Минимум 500мс между запросами


async def init_models():
    """Инициализация таблиц в БД"""
    try:
        logger.info("Инициализация моделей базы данных...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Модели успешно инициализированы")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации моделей: {e}", exc_info=True)
        raise


async def batch_add_meta_by_spec(objects: List[MetaBySpec]) -> List[MetaBySpec]:
    """Батчинг для вставки записей в БД - намного быстрее чем по одной"""
    if not objects:
        logger.warning("Попытка сохранить пустой список объектов")
        return []

    logger.info(f"Сохранение {len(objects)} записей в БД...")

    async with AsyncSessionLocal() as session:
        try:
            session.add_all(objects)
            await session.commit()
            logger.debug(f"Коммит выполнен, обновляем {len(objects)} объектов...")

            for obj in objects:
                await session.refresh(obj)

            logger.info(f"✅ Успешно сохранено {len(objects)} записей")
            return objects

        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"❌ Ошибка базы данных при сохранении {len(objects)} записей: {e}", exc_info=True)
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Неожиданная ошибка при сохранении в БД: {e}", exc_info=True)
            raise


async def get_access_token() -> str:
    """Получение access token с кешированием"""
    global _token_cache

    async with _token_lock:
        # Проверяем, есть ли действующий токен в кеше
        if _token_cache and _token_cache.get("expires_at", 0) > asyncio.get_event_loop().time():
            logger.debug("Используется закешированный access token")
            return _token_cache["token"]

        logger.info("Получение нового access token от WarcraftLogs API...")

        if not CLIENT_ID or not CLIENT_SECRET:
            logger.error("❌ CLIENT_ID или CLIENT_SECRET не установлены в .env файле")
            raise ValueError("CLIENT_ID и CLIENT_SECRET должны быть установлены")

        # Получаем новый токен
        auth = base64.b64encode(
            f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
        ).decode()

        try:
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
                expires_in = data.get("expires_in", 82800)
                _token_cache = {
                    "token": data["access_token"],
                    "expires_at": asyncio.get_event_loop().time() + expires_in - 3600
                }

                logger.info(f"✅ Access token получен, истекает через {expires_in // 3600} часов")
                return _token_cache["token"]

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP ошибка при получении токена: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ Ошибка сети при получении токена: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при получении токена: {e}", exc_info=True)
            raise


async def balance():
    """Проверка баланса API rate limit"""
    logger.info("Проверка баланса WarcraftLogs API...")

    try:
        token = await get_access_token()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                },
                json={"query": q_balance},
            )
            r.raise_for_status()
            balance_data = r.json()
            logger.info(f"API Balance: {json.dumps(balance_data, indent=2, ensure_ascii=False)}")
            return balance_data

    except Exception as e:
        logger.error(f"❌ Ошибка при проверке баланса API: {e}", exc_info=True)
        raise


def normalize_region(region: str) -> Optional[str]:
    """
    Нормализация региона
    EU / eu / Europe -> eu
    US / us / America -> us
    CN / cn / China -> None (RaiderIO не поддерживает CN)
    """
    if not region:
        logger.warning("Пустое значение региона")
        return None

    region = region.strip().lower()

    if region in ("eu", "europe"):
        return "eu"
    if region in ("us", "america", "na"):
        return "us"
    if region in ("kr", "korea"):
        return "kr"
    if region in ("tw", "taiwan"):
        return "tw"
    if region in ("cn", "china"):
        logger.debug(f"Регион CN пропущен (RaiderIO не поддерживает китайские сервера)")
        return None  # RaiderIO не поддерживает китайские сервера

    logger.warning(f"Неизвестный регион: {region}")
    return None  # Возвращаем None вместо исключения


def normalize_realm(realm: str) -> str:
    """
    Нормализация названия реалма
    'Tarren Mill' -> 'tarren-mill'
    'Twisting Nether' -> 'twisting-nether'
    'Quel'Thalas' -> 'quel-thalas'
    """
    if not realm:
        logger.warning("Пустое значение реалма")
        return ""

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
    """Получение RIO score с retry механизмом и строгим rate limiting"""
    global _rio_last_request_time

    params = {
        "region": region,
        "realm": realm,
        "name": name,
        "fields": "mythic_plus_scores_by_season:current"
    }

    for attempt in range(max_retries):
        try:
            async with _rio_semaphore:
                # Глобальный rate limiting - минимум 500мс между запросами
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - _rio_last_request_time
                if time_since_last < _rio_min_interval:
                    sleep_time = _rio_min_interval - time_since_last
                    await asyncio.sleep(sleep_time)

                _rio_last_request_time = asyncio.get_event_loop().time()

                r = await client.get(RIO_URL, params=params, timeout=10)
                r.raise_for_status()
                data = r.json()

                seasons = data.get("mythic_plus_scores_by_season", [])
                if not seasons:
                    logger.debug(f"Нет RIO данных для {name}-{realm}-{region}")
                    return None

                scores = seasons[0].get("scores")
                if not scores:
                    logger.debug(f"Нет scores для {name}-{realm}-{region}")
                    return None

                rio_score = scores.get("all")
                if rio_score:
                    logger.debug(f"RIO score для {name}: {rio_score}")
                return rio_score

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"Игрок не найден в RIO: {name}-{realm}-{region}")
                return None
            elif e.response.status_code == 429:
                # Rate limit - значительно увеличиваем задержку
                backoff_time = 2.0 * (2 ** attempt)  # Экспоненциальный backoff: 2s, 4s, 8s
                logger.warning(f"⚠️  Rate limit RIO API для {name} (попытка {attempt + 1}/{max_retries}), ожидание {backoff_time:.1f}s")
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(f"❌ Превышен rate limit RIO для {name} после {max_retries} попыток")
                    return None
            else:
                logger.warning(f"HTTP {e.response.status_code} для {name} (попытка {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.3 * (attempt + 1))
                else:
                    return None

        except httpx.TimeoutException:
            logger.warning(f"Timeout при запросе RIO для {name} (попытка {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(0.3 * (attempt + 1))
            else:
                return None

        except httpx.RequestError as e:
            logger.warning(f"Ошибка сети RIO для {name}: {e} (попытка {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(0.3 * (attempt + 1))
            else:
                return None

        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка RIO для {name}: {e}", exc_info=True)
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

    logger.debug(f"Запрос leaderboard для {class_name} {spec_name} на encounter {encounter_id}")

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

        # Проверка на ошибки GraphQL
        if "errors" in data:
            logger.error(f"❌ GraphQL ошибка для {class_name} {spec_name}: {data['errors']}")
            return None

        rankings_block = data.get("data", {}).get("worldData", {}).get("encounter", {}).get("characterRankings")

        if not rankings_block:
            logger.warning(f"Нет characterRankings для {class_name} {spec_name} на encounter {encounter_id}")
            return None

        if "rankings" not in rankings_block:
            logger.warning(f"Нет rankings для {class_name} {spec_name} на encounter {encounter_id}")
            return None

        rankings = rankings_block["rankings"]
        logger.info(f"Получено {len(rankings)} игроков для {class_name} {spec_name} на encounter {encounter_id}")

        # Собираем задачи для параллельного получения RIO
        rio_tasks = []
        valid_players = 0

        for item in rankings:
            hidden = item.get("hidden", False)
            server_obj = item.get("server") or {}
            server_name = server_obj.get("name", "")
            server_region = server_obj.get("region", "")
            player_name = item.get("name")

            if not hidden and server_name and server_region and player_name and player_name != "Anonymous":
                try:
                    server = normalize_realm(server_name)
                    region = normalize_region(server_region) if server_region else None

                    if region:
                        rio_tasks.append(fetch_rio_with_retry(client, region, server, player_name))
                        valid_players += 1
                except Exception as e:
                    logger.debug(f"Ошибка нормализации для {player_name}/{server_name}/{server_region}: {e}")
                    continue

        if not rio_tasks:
            logger.warning(f"Нет валидных игроков для запроса RIO ({class_name} {spec_name})")
            return None

        logger.info(f"Запрос RIO для {valid_players} игроков ({class_name} {spec_name})...")

        # Параллельное выполнение всех RIO запросов
        rio_results = await asyncio.gather(*rio_tasks, return_exceptions=True)

        # Подсчет среднего
        total_score = 0.0
        counter_players_with_score = 0

        for rio_result in rio_results:
            if isinstance(rio_result, (int, float)) and rio_result is not None and rio_result > 0:
                total_score += float(rio_result)
                counter_players_with_score += 1
            elif isinstance(rio_result, Exception):
                logger.debug(f"RIO задача вернула исключение: {rio_result}")

        if counter_players_with_score == 0:
            logger.warning(f"Нет RIO scores для {class_name} {spec_name} на encounter {encounter_id}")
            return None

        average_score = total_score / counter_players_with_score
        logger.info(f"✅ Средний RIO для {class_name} {spec_name}: {average_score:.2f} ({counter_players_with_score}/{valid_players} игроков)")

        return average_score

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP ошибка для {class_name} {spec_name}: {e.response.status_code}")
        return None
    except httpx.TimeoutException:
        logger.error(f"❌ Timeout для {class_name} {spec_name} на encounter {encounter_id}")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка fetch_leaderboard для {class_name} {spec_name} на encounter {encounter_id}: {e}", exc_info=True)
        return None


async def fetch_single_spec_meta(
    client: httpx.AsyncClient,
    token: str,
    encounter_id: int,
    class_name: str,
    spec_name: str
) -> Optional[MetaBySpec]:
    """Получение меты для одной спеки одного босса"""
    logger.debug(f"Обработка {class_name} {spec_name} для encounter {encounter_id}")

    try:
        meta_average_value = await fetch_leaderboard_optimized(
            client, token, encounter_id, class_name, spec_name
        )

        if meta_average_value is None:
            logger.debug(f"Нет данных для {class_name} {spec_name} на encounter {encounter_id}")
            return None

        # Проверка на существование spec в SPEC_ROLE_METRIC
        if spec_name not in SPEC_ROLE_METRIC:
            logger.error(f"❌ Spec {spec_name} не найден в SPEC_ROLE_METRIC!")
            return None

        meta_obj = MetaBySpec(
            class_name=class_name,
            spec=spec_name,
            meta=int(meta_average_value),
            spec_type=SPEC_ROLE_METRIC[spec_name][0],
            encounter_id=encounter_id
        )

        logger.debug(f"✅ Создан объект меты для {class_name} {spec_name}: {meta_average_value:.2f}")
        return meta_obj

    except KeyError as e:
        logger.error(f"❌ KeyError для {class_name} {spec_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка создания объекта меты для {class_name} {spec_name}: {e}", exc_info=True)
        return None


async def test_leaderboard():
    """Основная функция сбора данных - ОПТИМИЗИРОВАННАЯ"""
    logger.info("=" * 80)
    logger.info("НАЧАЛО СБОРА ДАННЫХ WOW META")
    logger.info("=" * 80)

    try:
        token = await get_access_token()
    except Exception as e:
        logger.error(f"❌ Не удалось получить access token: {e}")
        return []

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

    logger.info(f"Обработка {len(encounters)} боссов...")

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

        logger.info(f"Запускаем {len(tasks)} задач параллельно (с rate limiting)...")

        # Выполняем ВСЕ запросы параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Фильтруем успешные результаты
        valid_objects = []
        failed_count = 0
        exception_count = 0

        for result in results:
            if isinstance(result, MetaBySpec):
                valid_objects.append(result)
            elif result is None:
                failed_count += 1
            elif isinstance(result, Exception):
                exception_count += 1
                logger.error(f"Задача завершилась с исключением: {result}")

        logger.info(f"Результаты: {len(valid_objects)} успешных, {failed_count} без данных, {exception_count} ошибок")

        # Батчинг для записи в БД
        if valid_objects:
            batch_size = 50
            total_batches = (len(valid_objects) + batch_size - 1) // batch_size
            logger.info(f"Сохранение в БД: {len(valid_objects)} записей в {total_batches} батчах...")

            for i in range(0, len(valid_objects), batch_size):
                batch = valid_objects[i:i + batch_size]
                try:
                    await batch_add_meta_by_spec(batch)
                    logger.info(f"✅ Batch {i//batch_size + 1}/{total_batches}: сохранено {len(batch)} записей")
                except Exception as e:
                    logger.error(f"❌ Ошибка сохранения batch {i//batch_size + 1}: {e}")

        logger.info("=" * 80)
        logger.info(f"ЗАВЕРШЕНО: Всего сохранено {len(valid_objects)} из {len(tasks)} записей")
        logger.info("=" * 80)

        return valid_objects


async def main():
    try:
        await init_models()
        await test_leaderboard()
        # await balance()
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в main(): {e}", exc_info=True)
        raise


import time
if __name__ == "__main__":
    start = time.perf_counter()
    asyncio.run(main())
    # asyncio.run(balance())
    end = time.perf_counter()
    logger.info(f"⏱️  Общее время выполнения: {end - start:.2f} сек")
