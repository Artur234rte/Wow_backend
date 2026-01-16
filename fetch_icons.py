#!/usr/bin/env python3
"""
Скрипт для получения иконок подземелий и рейдов из Blizzard API
Обновляет файл constant.py с журнал ID и URL иконок

Использование:
    python fetch_icons.py

После выполнения скрипт обновит ENCOUNTERS и RAID в constant.py
"""

import asyncio
import httpx
import logging
from pathlib import Path

from app.agregator.view import get_access_token
from app.agregator.quieres import QUERY_GET_JOURNAL_ID
from app.agregator.constant import API_URL, ENCOUNTERS, RAID
from app.agregator.blizzard_api import (
    get_journal_encounter_icon,
    get_blizzard_access_token
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def fetch_journal_id_from_warcraftlogs(encounter_id: int) -> tuple[str, int | None]:
    """
    Получение journalID и имени encounter из WarcraftLogs API

    Returns:
        (name, journal_id) - кортеж с именем и journal_id
    """
    try:
        token = await get_access_token()

        variables = {"encounterID": encounter_id}

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                API_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "query": QUERY_GET_JOURNAL_ID,
                    "variables": variables,
                },
            )
            r.raise_for_status()
            data = r.json()

            if "errors" in data:
                logger.error(f"❌ GraphQL ошибка для encounter {encounter_id}: {data['errors']}")
                return None, None

            encounter = data.get("data", {}).get("worldData", {}).get("encounter", {})
            name = encounter.get("name", "Unknown")
            journal_id = encounter.get("journalID")

            logger.info(f"✅ {name} (encounter={encounter_id}): journal_id={journal_id}")
            return name, journal_id

    except Exception as e:
        logger.error(f"❌ Ошибка получения journal_id для encounter {encounter_id}: {e}")
        return None, None


async def fetch_all_icons():
    """Основная функция для получения всех иконок"""
    logger.info("=" * 80)
    logger.info("НАЧАЛО ПОЛУЧЕНИЯ ИКОНОК ДЛЯ ПОДЗЕМЕЛИЙ И РЕЙДОВ")
    logger.info("=" * 80)

    # Проверяем наличие Blizzard credentials
    try:
        await get_blizzard_access_token()
        logger.info("✅ Blizzard API токен получен успешно")
    except Exception as e:
        logger.error(f"❌ Не удалось получить Blizzard токен: {e}")
        logger.error("Убедитесь, что BLIZZARD_CLIENT_ID и BLIZZARD_CLIENT_SECRET установлены в .env")
        return

    # Собираем данные
    encounters_data = {}
    raids_data = {}

    # Обрабатываем подземелья (M+)
    logger.info(f"\n📦 Обработка {len(ENCOUNTERS)} подземелий (M+)...")
    for encounter_id in ENCOUNTERS.keys():
        name, journal_id = await fetch_journal_id_from_warcraftlogs(encounter_id)

        icon_url = None
        if journal_id:
            icon_url = await get_journal_encounter_icon(journal_id)
            await asyncio.sleep(0.5)  # Rate limiting для Blizzard API

        encounters_data[encounter_id] = {
            "name": name,
            "journal_id": journal_id,
            "icon": icon_url
        }

        await asyncio.sleep(0.3)  # Rate limiting для WarcraftLogs

    # Обрабатываем рейды
    logger.info(f"\n🏰 Обработка {len(RAID)} рейд боссов...")
    for encounter_id in RAID.keys():
        name, journal_id = await fetch_journal_id_from_warcraftlogs(encounter_id)

        icon_url = None
        if journal_id:
            icon_url = await get_journal_encounter_icon(journal_id)
            await asyncio.sleep(0.5)  # Rate limiting для Blizzard API

        raids_data[encounter_id] = {
            "name": name,
            "journal_id": journal_id,
            "icon": icon_url
        }

        await asyncio.sleep(0.3)  # Rate limiting для WarcraftLogs

    # Обновляем constant.py
    logger.info("\n📝 Обновление constant.py...")
    update_constant_file(encounters_data, raids_data)

    logger.info("=" * 80)
    logger.info("✅ ЗАВЕРШЕНО")
    logger.info("=" * 80)

    # Выводим статистику
    encounters_with_icons = sum(1 for v in encounters_data.values() if v["icon"])
    raids_with_icons = sum(1 for v in raids_data.values() if v["icon"])

    logger.info(f"Подземелья: {encounters_with_icons}/{len(encounters_data)} с иконками")
    logger.info(f"Рейды: {raids_with_icons}/{len(raids_data)} с иконками")


def update_constant_file(encounters_data: dict, raids_data: dict):
    """Обновляет constant.py с новыми данными"""
    constant_file = Path("app/agregator/constant.py")

    if not constant_file.exists():
        logger.error(f"❌ Файл {constant_file} не найден")
        return

    # Читаем текущий файл
    content = constant_file.read_text(encoding="utf-8")

    # Формируем новый ENCOUNTERS блок
    encounters_lines = ["ENCOUNTERS = {"]
    for encounter_id, data in encounters_data.items():
        icon_str = f'"{data["icon"]}"' if data["icon"] else "None"
        journal_str = data["journal_id"] if data["journal_id"] else "None"
        encounters_lines.append(f'    {encounter_id}: {{')
        encounters_lines.append(f'        "name": "{data["name"]}",')
        encounters_lines.append(f'        "icon": {icon_str},')
        encounters_lines.append(f'        "journal_id": {journal_str}')
        encounters_lines.append('    },')
    encounters_lines.append("}")

    # Формируем новый RAID блок
    raid_lines = ["RAID = {"]
    for encounter_id, data in raids_data.items():
        icon_str = f'"{data["icon"]}"' if data["icon"] else "None"
        journal_str = data["journal_id"] if data["journal_id"] else "None"
        raid_lines.append(f'    {encounter_id}: {{')
        raid_lines.append(f'        "name": "{data["name"]}",')
        raid_lines.append(f'        "icon": {icon_str},')
        raid_lines.append(f'        "journal_id": {journal_str}')
        raid_lines.append('    },')
    raid_lines.append("}")

    # Заменяем старые блоки на новые
    import re

    # Заменяем ENCOUNTERS
    encounters_pattern = r'ENCOUNTERS = \{[^}]*(?:\{[^}]*\}[^}]*)*\}'
    new_encounters = '\n'.join(encounters_lines)
    content = re.sub(encounters_pattern, new_encounters, content, flags=re.DOTALL)

    # Заменяем RAID
    raid_pattern = r'RAID = \{[^}]*(?:\{[^}]*\}[^}]*)*\}'
    new_raid = '\n'.join(raid_lines)
    content = re.sub(raid_pattern, new_raid, content, flags=re.DOTALL)

    # Сохраняем файл
    constant_file.write_text(content, encoding="utf-8")
    logger.info(f"✅ Файл {constant_file} обновлен")


async def main():
    try:
        await fetch_all_icons()
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
