from app.agregator.constant import TOKEN_URL, CLIENT_ID, CLIENT_SECRET, WOW_CLASS_SPECS, SPEC_ROLE_METRIC, API_URL, RIO_URL, ENCOUNTERS, RAID
from app.agregator.quieres import q_with_gear_and_talent, q_balance, \
    QUERY_FOR_MYTHIC_PLUS_LOW_KEYS, QUERY_FOR_MYTHIC_PLUS_HIGH_KEYS, \
    QUERY_FOR_RAID_DPS, QUERY_FOR_RAID_HPS
import base64
import httpx
import json
import asyncio
import re
import unicodedata
import logging
from app.models.model import MetaBySpec, Base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from typing import Optional, List, Dict, Any
from app.db.db import engine, AsyncSessionLocal

# Настройка логирования с ротацией файлов
from logging.handlers import RotatingFileHandler

# Создаем handler с ротацией (10 MB на файл, максимум 5 файлов)
file_handler = RotatingFileHandler(
    'wow_aggregator.log',
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        file_handler
    ]
)
logger = logging.getLogger(__name__)

# Отключаем HTTP Request логи от httpx (они логируются на INFO уровне)
# Устанавливаем WARNING чтобы скрыть INFO и DEBUG сообщения от httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Глобальный кеш для access token
_token_cache: Optional[Dict[str, Any]] = None
_token_lock = asyncio.Lock()

# Семафоры для rate limiting
_api_semaphore = asyncio.Semaphore(5)  # Макс 5 одновременных запросов к WarcraftLogs
_rio_semaphore = asyncio.Semaphore(2)  # Макс 3 одновременных запроса к RaiderIO (строгий лимит)

# Глобальный rate limit для RaiderIO
_rio_last_request_time = 0.0
_rio_min_interval = 0.5  # Минимум 500мс между запросами

# Кеш для RIO scores игроков (region-realm-name -> score)
_rio_cache: Dict[str, Optional[float]] = {}
_rio_cache_lock = asyncio.Lock()


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
    """
    Батчинг для вставки/обновления записей в БД (upsert) с использованием PostgreSQL ON CONFLICT.
    Это намного быстрее чем проверка каждой записи отдельным SELECT.
    Вместо N SELECT + N INSERT/UPDATE выполняется всего 1 запрос.
    """
    if not objects:
        logger.warning("Попытка сохранить пустой список объектов")
        return []

    logger.info(f"Сохранение/обновление {len(objects)} записей в БД через ON CONFLICT...")

    async with AsyncSessionLocal() as session:
        try:
            values = [
                {
                    "class_name": obj.class_name,
                    "spec": obj.spec,
                    "meta": obj.meta,
                    "spec_type": obj.spec_type,
                    "encounter_id": obj.encounter_id,
                    "key": obj.key,
                    "average_dps": obj.average_dps,
                    "max_key_level": obj.max_key_level,
                }
                for obj in objects
            ]

            # PostgreSQL INSERT ... ON CONFLICT DO UPDATE
            stmt = insert(MetaBySpec).values(values)

            # При конфликте по уникальному индексу (class_name, spec, encounter_id, key)
            # обновляем все поля кроме id
            stmt = stmt.on_conflict_do_update(
                index_elements=['class_name', 'spec', 'encounter_id', 'key'],
                set_={
                    'meta': stmt.excluded.meta,
                    'spec_type': stmt.excluded.spec_type,
                    'average_dps': stmt.excluded.average_dps,
                    'max_key_level': stmt.excluded.max_key_level,
                }
            )

            await session.execute(stmt)
            await session.commit()

            logger.info(f"✅ Успешно обработано {len(objects)} записей в одном запросе (INSERT ON CONFLICT)")
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
    name: str
) -> Optional[float]:
    """Получение RIO score с кешированием и строгим rate limiting (без retry)"""
    global _rio_last_request_time, _rio_cache

    # Создаем ключ для кеша (нормализованный)
    cache_key = f"{region.lower()}-{realm.lower()}-{name.lower()}"

    # Проверяем кеш
    async with _rio_cache_lock:
        if cache_key in _rio_cache:
            cached_score = _rio_cache[cache_key]
            logger.debug(f"💾 Cache hit для {name}: {cached_score}")
            return cached_score

    params = {
        "region": region,
        "realm": realm,
        "name": name,
        "fields": "mythic_plus_scores_by_season:current"
    }

    try:
        async with _rio_semaphore:
            # Глобальный rate limiting - минимум 500мс между запросами
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - _rio_last_request_time
            if time_since_last < _rio_min_interval:
                sleep_time = _rio_min_interval - time_since_last
                await asyncio.sleep(sleep_time)

            _rio_last_request_time = asyncio.get_event_loop().time()

            r = await client.get(RIO_URL, params=params, timeout=5)
            r.raise_for_status()
            data = r.json()

            seasons = data.get("mythic_plus_scores_by_season", [])
            if not seasons:
                logger.debug(f"Нет RIO данных для {name}-{realm}-{region}")
                # Кешируем отсутствие данных
                async with _rio_cache_lock:
                    _rio_cache[cache_key] = None
                return None

            scores = seasons[0].get("scores")
            if not scores:
                logger.debug(f"Нет scores для {name}-{realm}-{region}")
                async with _rio_cache_lock:
                    _rio_cache[cache_key] = None
                return None

            rio_score = scores.get("all")
            logger.debug(f"RIO score для {name}: {rio_score}")

            # Сохраняем в кеш
            async with _rio_cache_lock:
                _rio_cache[cache_key] = rio_score

            return rio_score

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.debug(f"Игрок не найден в RIO: {name}-{realm}-{region}")
            # Кешируем 404 как None
            async with _rio_cache_lock:
                _rio_cache[cache_key] = None
            return None
        elif e.response.status_code == 429:
            logger.warning(f"⚠️ Rate limit RIO API для {name}")
            return None
        else:
            logger.warning(f"HTTP {e.response.status_code} для {name}")
            return None

    except httpx.TimeoutException:
        logger.warning(f"Timeout при запросе RIO для {name}")
        return None

    except httpx.RequestError as e:
        logger.warning(f"Ошибка сети RIO для {name}: {e}")
        return None

    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка RIO для {name}: {e}", exc_info=True)
        return None


async def fetch_leaderboard_optimized(
    client: httpx.AsyncClient,
    token: str,
    encounter_id: int,
    class_name: str,
    spec_name: str,
    query: str = None,
    key_type: str = "high",
    is_raid: bool = False
) -> Optional[Dict[str, Any]]:
    """Оптимизированная версия fetch_leaderboard - возвращает среднее RIO, DPS и max_key"""
    if query is None:
        query = QUERY_FOR_MYTHIC_PLUS_HIGH_KEYS

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
                    "query": query,
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
        logger.info(f"📥 Получено {len(rankings)} игроков для класса={class_name}, спека={spec_name}, encounter={encounter_id}")

        # Подсчет DPS и max_key
        total_dps = 0.0
        valid_dps_entries = 0
        max_key = 0

        # Собираем уникальных игроков для RIO (только для M+, не для рейдов)
        unique_players = set()  # set для хранения уникальных (region, realm, name)

        for item in rankings:
            # Извлекаем DPS
            dps = item.get("amount")
            if dps and dps > 0:
                total_dps += dps
                valid_dps_entries += 1

            # Извлекаем bracket (key level) - только для M+
            if not is_raid:
                bracket_data = item.get("bracketData", 0)
                if bracket_data > max_key:
                    max_key = bracket_data

            # Собираем уникальных игроков для RIO (только для M+, не для рейдов)
            if not is_raid:
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
                            # Добавляем уникальную комбинацию (region, realm, name)
                            unique_players.add((region, server, player_name))
                    except Exception as e:
                        logger.debug(f"Ошибка нормализации для {player_name}/{server_name}/{server_region}: {e}")
                        continue

        # Создаем задачи только для уникальных игроков
        rio_tasks = [fetch_rio_with_retry(client, region, server, name) for region, server, name in unique_players]
        valid_players = len(unique_players)

        # Формируем результат
        result = {}

        # Средний DPS
        if valid_dps_entries > 0:
            result["average_dps"] = int(total_dps / valid_dps_entries)
        else:
            result["average_dps"] = None

        # Максимальный ключ только для high keys M+
        if not is_raid and key_type == "high":
            result["max_key_level"] = max_key if max_key > 0 else None
        else:
            result["max_key_level"] = None

        # Вычисляем RIO только для M+, не для рейдов
        if not is_raid:
            if not rio_tasks:
                logger.warning(f"Нет валидных игроков для запроса RIO (класс={class_name}, спек={spec_name}, encounter={encounter_id})")
                result["average_rio"] = None
            else:
                logger.info(f"🔍 Запрос RIO для {valid_players} игроков (класс={class_name}, спек={spec_name}, encounter={encounter_id})")

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
                    logger.warning(f"Нет RIO scores (класс={class_name}, спек={spec_name}, encounter={encounter_id})")
                    result["average_rio"] = None
                else:
                    average_score = total_score / counter_players_with_score
                    logger.info(f"✅ Средний RIO={average_score:.2f} для класса={class_name}, спека={spec_name}, encounter={encounter_id} ({counter_players_with_score}/{valid_players} игроков)")
                    result["average_rio"] = average_score
        else:
            # Для рейдов RIO не вычисляется
            result["average_rio"] = None

        return result

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
    spec_name: str,
    key_type: str = "high",
    query: str = None,
    is_raid: bool = False
) -> Optional[MetaBySpec]:
    """Получение меты для одной спеки одного босса (M+ или Raid)"""
    if is_raid:
        logger.info(f"📊 Обработка рейда: класс={class_name}, спек={spec_name}, encounter={encounter_id}")
    else:
        logger.info(f"📊 Обработка: класс={class_name}, спек={spec_name}, encounter={encounter_id}, ключ={key_type}")

    # Автоматический выбор запроса на основе key_type и is_raid
    if query is None:
        if is_raid:
            # Для рейдов определяем роль спека
            spec_role = SPEC_ROLE_METRIC.get(spec_name, ("dps", "playerscore"))[0]
            if spec_role == "healer":
                query = QUERY_FOR_RAID_HPS
            else:
                query = QUERY_FOR_RAID_DPS
        elif key_type == "low":
            query = QUERY_FOR_MYTHIC_PLUS_LOW_KEYS
        else:
            query = QUERY_FOR_MYTHIC_PLUS_HIGH_KEYS

    try:
        result_data = await fetch_leaderboard_optimized(
            client, token, encounter_id, class_name, spec_name,
            query=query,
            key_type=key_type,
            is_raid=is_raid
        )

        if result_data is None:
            logger.debug(f"Нет данных для {class_name} {spec_name} на encounter {encounter_id}")
            return None

        # Извлекаем данные из результата
        average_rio = result_data.get("average_rio")
        average_dps = result_data.get("average_dps")
        max_key_level = result_data.get("max_key_level")

        # Для M+ приоритет: RIO, затем DPS. Для рейдов используется DPS или HPS
        if average_rio:
            meta_value = int(average_rio)
        elif average_dps:
            meta_value = int(average_dps)
        else:
            logger.debug(f"Нет meta данных (ни RIO, ни DPS/HPS) для {class_name} {spec_name} на encounter {encounter_id}")
            return None

        meta_obj = MetaBySpec(
            class_name=class_name,
            spec=spec_name,
            meta=meta_value,
            spec_type=SPEC_ROLE_METRIC[spec_name][0],
            encounter_id=encounter_id,
            key=key_type if not is_raid else None,
            average_dps=average_dps,
            max_key_level=max_key_level
        )

        logger.debug(f"✅ Создан объект меты для {class_name} {spec_name}: meta={meta_value}, dps={average_dps}, max_key={max_key_level}")
        return meta_obj

    except KeyError as e:
        logger.error(f"❌ KeyError для {class_name} {spec_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка создания объекта меты для {class_name} {spec_name}: {e}", exc_info=True)
        return None


async def test_leaderboard():
    """Основная функция сбора данных - ОПТИМИЗИРОВАННАЯ с поддержкой LOW/HIGH keys и RAID"""
    logger.info("=" * 80)
    logger.info("НАЧАЛО СБОРА ДАННЫХ WOW META")
    logger.info("=" * 80)

    try:
        token = await get_access_token()
    except Exception as e:
        logger.error(f"❌ Не удалось получить access token: {e}")
        return []

    logger.info(f"Обработка {len(ENCOUNTERS)} подземелий и {len(RAID)} рейд боссов...")

    async with httpx.AsyncClient(timeout=60) as client:
        # Создаем все задачи для параллельного выполнения
        tasks = []

        # M+ задачи
        for encounter_id in ENCOUNTERS.keys():
            for class_name, specs in WOW_CLASS_SPECS.items():
                for spec_name in specs:
                    # LOW KEYS задача
                    task_low = fetch_single_spec_meta(
                        client, token, encounter_id, class_name, spec_name,
                        key_type="low",
                        query=QUERY_FOR_MYTHIC_PLUS_LOW_KEYS,
                        is_raid=False
                    )
                    tasks.append(task_low)

                    # HIGH KEYS задача
                    task_high = fetch_single_spec_meta(
                        client, token, encounter_id, class_name, spec_name,
                        key_type="high",
                        query=QUERY_FOR_MYTHIC_PLUS_HIGH_KEYS,
                        is_raid=False
                    )
                    tasks.append(task_high)

        # RAID задачи
        for raid_id in RAID.keys():
            for class_name, specs in WOW_CLASS_SPECS.items():
                for spec_name in specs:
                    task_raid = fetch_single_spec_meta(
                        client, token, raid_id, class_name, spec_name,
                        is_raid=True
                    )
                    tasks.append(task_raid)

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

        # Статистика кеша RIO
        cache_size = len(_rio_cache)
        cache_with_scores = sum(1 for v in _rio_cache.values() if v is not None and v > 0)
        cache_nulls = sum(1 for v in _rio_cache.values() if v is None)
        logger.info(f"💾 Cache статистика: {cache_size} записей ({cache_with_scores} с RIO, {cache_nulls} без данных)")

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
    asyncio.run(balance())
    end = time.perf_counter()
    logger.info(f"⏱️  Общее время выполнения: {end - start:.2f} сек")
