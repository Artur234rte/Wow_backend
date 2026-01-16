"""
Утилиты для работы с encounters и raids
Предоставляют обратную совместимость со старым форматом
"""

from typing import Dict, Any, List
from app.agregator.constant import ENCOUNTERS, RAID


def get_encounter_name(encounter_id: int) -> str:
    """
    Получить имя encounter по ID

    Args:
        encounter_id: ID encounter

    Returns:
        Имя encounter или "Unknown"
    """
    encounter = ENCOUNTERS.get(encounter_id) or RAID.get(encounter_id)
    if isinstance(encounter, dict):
        return encounter.get("name", "Unknown")
    return encounter if encounter else "Unknown"


def get_encounter_icon(encounter_id: int) -> str | None:
    """
    Получить URL иконки encounter по ID

    Args:
        encounter_id: ID encounter

    Returns:
        URL иконки или None
    """
    encounter = ENCOUNTERS.get(encounter_id) or RAID.get(encounter_id)
    if isinstance(encounter, dict):
        return encounter.get("icon")
    return None


def get_encounter_journal_id(encounter_id: int) -> int | None:
    """
    Получить journal_id encounter по ID

    Args:
        encounter_id: ID encounter

    Returns:
        journal_id или None
    """
    encounter = ENCOUNTERS.get(encounter_id) or RAID.get(encounter_id)
    if isinstance(encounter, dict):
        return encounter.get("journal_id")
    return None


def get_encounter_data(encounter_id: int) -> Dict[str, Any]:
    """
    Получить полные данные encounter по ID

    Args:
        encounter_id: ID encounter

    Returns:
        Словарь с данными: {id, name, icon, journal_id}
    """
    encounter = ENCOUNTERS.get(encounter_id) or RAID.get(encounter_id)

    if isinstance(encounter, dict):
        return {
            "id": encounter_id,
            "name": encounter.get("name", "Unknown"),
            "icon": encounter.get("icon"),
            "journal_id": encounter.get("journal_id")
        }

    # Обратная совместимость со старым форматом (строка вместо dict)
    return {
        "id": encounter_id,
        "name": encounter if encounter else "Unknown",
        "icon": None,
        "journal_id": None
    }


def get_all_encounters_data() -> List[Dict[str, Any]]:
    """
    Получить список всех подземелий (M+) с данными

    Returns:
        Список словарей: [{id, name, icon, journal_id}, ...]
    """
    return [get_encounter_data(enc_id) for enc_id in ENCOUNTERS.keys()]


def get_all_raids_data() -> List[Dict[str, Any]]:
    """
    Получить список всех рейд боссов с данными

    Returns:
        Список словарей: [{id, name, icon, journal_id}, ...]
    """
    return [get_encounter_data(raid_id) for raid_id in RAID.keys()]


def is_raid(encounter_id: int) -> bool:
    """
    Проверить, является ли encounter рейдом

    Args:
        encounter_id: ID encounter

    Returns:
        True если это рейд, False если M+
    """
    return encounter_id in RAID


def is_mythic_plus(encounter_id: int) -> bool:
    """
    Проверить, является ли encounter M+ подземельем

    Args:
        encounter_id: ID encounter

    Returns:
        True если это M+, False если рейд
    """
    return encounter_id in ENCOUNTERS
