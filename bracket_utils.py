"""
Утилиты для работы с bracket фильтрацией в WarcraftLogs API

Позволяет разделять запросы на:
- Low keys (M+1 до M+12)
- High keys (M+12 до M+22)
"""
import asyncio
import httpx
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


async def fetch_rankings_with_bracket_filter(
    client: httpx.AsyncClient,
    token: str,
    api_url: str,
    encounter_id: int,
    class_name: str,
    spec_name: str,
    min_bracket: Optional[int] = None,
    max_bracket: Optional[int] = None,
    query_template: str = None
) -> List[Dict[str, Any]]:
    """
    Получение rankings с фильтрацией по диапазону bracket

    Args:
        client: httpx AsyncClient
        token: Access token для API
        api_url: URL WarcraftLogs API
        encounter_id: ID энкаунтера
        class_name: Название класса
        spec_name: Название специализации
        min_bracket: Минимальный уровень ключа (включительно), None = без ограничения
        max_bracket: Максимальный уровень ключа (включительно), None = без ограничения
        query_template: Кастомный GraphQL запрос (опционально)

    Returns:
        List[Dict]: Список rankings, отфильтрованный по bracket диапазону

    Примеры:
        # Все ключи
        rankings = await fetch_rankings_with_bracket_filter(
            client, token, api_url, 62660, "Priest", "Shadow"
        )

        # Low keys (M+1 до M+12)
        low_keys = await fetch_rankings_with_bracket_filter(
            client, token, api_url, 62660, "Priest", "Shadow",
            min_bracket=1, max_bracket=12
        )

        # High keys (M+12+)
        high_keys = await fetch_rankings_with_bracket_filter(
            client, token, api_url, 62660, "Priest", "Shadow",
            min_bracket=12, max_bracket=None
        )
    """

    if query_template is None:
        query_template = """
        query(
          $encounterID: Int!,
          $className: String!,
          $specName: String!,
          $bracket: Int
        ) {
          worldData {
            encounter(id: $encounterID) {
              name
              characterRankings(
                className: $className
                specName: $specName
                metric: playerscore
                bracket: $bracket
              )
            }
          }
        }
        """

    variables = {
        "encounterID": encounter_id,
        "className": class_name,
        "specName": spec_name,
    }

    # API фильтрует только по минимальному значению
    if min_bracket is not None:
        variables["bracket"] = min_bracket

    r = await client.post(
        api_url,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": query_template,
            "variables": variables,
        },
        timeout=30
    )
    r.raise_for_status()
    data = r.json()

    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")

    char_rankings = data.get("data", {}).get("worldData", {}).get("encounter", {}).get("characterRankings")

    if not char_rankings or "rankings" not in char_rankings:
        return []

    rankings = char_rankings["rankings"]

    # Фильтруем по max_bracket вручную (API не поддерживает upper bound)
    if max_bracket is not None:
        rankings = [r for r in rankings if r.get("bracketData", 0) <= max_bracket]

    return rankings


async def fetch_low_and_high_keys(
    client: httpx.AsyncClient,
    token: str,
    api_url: str,
    encounter_id: int,
    class_name: str,
    spec_name: str,
    low_threshold: int = 12,
    query_template: str = None
) -> Tuple[List[Dict], List[Dict]]:
    """
    Получает rankings разделенные на low keys и high keys

    Args:
        client: httpx AsyncClient
        token: Access token
        api_url: API URL
        encounter_id: ID энкаунтера
        class_name: Название класса
        spec_name: Название специализации
        low_threshold: Граница между low и high keys (по умолчанию 12)
        query_template: Кастомный GraphQL запрос (опционально)

    Returns:
        Tuple[List[Dict], List[Dict]]: (low_keys, high_keys)

    Пример:
        low_keys, high_keys = await fetch_low_and_high_keys(
            client, token, api_url, 62660, "Priest", "Shadow"
        )
    """

    # Запускаем оба запроса параллельно
    low_task = fetch_rankings_with_bracket_filter(
        client, token, api_url, encounter_id, class_name, spec_name,
        min_bracket=1, max_bracket=low_threshold, query_template=query_template
    )

    high_task = fetch_rankings_with_bracket_filter(
        client, token, api_url, encounter_id, class_name, spec_name,
        min_bracket=low_threshold, max_bracket=None, query_template=query_template
    )

    low_keys, high_keys = await asyncio.gather(low_task, high_task)

    return low_keys, high_keys


def calculate_bracket_statistics(rankings: List[Dict]) -> Dict[str, Any]:
    """
    Вычисляет статистику по bracket для списка rankings

    Args:
        rankings: Список rankings из API

    Returns:
        Dict со статистикой:
        - total: общее количество записей
        - by_bracket: распределение по уровням {bracket: count}
        - avg_score: средний score
        - max_score: максимальный score
        - min_score: минимальный score
        - avg_bracket: средний уровень ключа

    Пример:
        stats = calculate_bracket_statistics(rankings)
        print(f"Средний score: {stats['avg_score']:.2f}")
    """

    if not rankings:
        return {
            "total": 0,
            "by_bracket": {},
            "avg_score": 0,
            "max_score": 0,
            "min_score": 0,
            "avg_bracket": 0
        }

    bracket_counts = defaultdict(int)
    total_score = 0
    total_bracket = 0
    scores = []

    for rank in rankings:
        bracket = rank.get("bracketData", 0)
        score = rank.get("score", 0)

        bracket_counts[bracket] += 1
        total_score += score
        total_bracket += bracket
        scores.append(score)

    return {
        "total": len(rankings),
        "by_bracket": dict(bracket_counts),
        "avg_score": total_score / len(rankings),
        "max_score": max(scores),
        "min_score": min(scores),
        "avg_bracket": total_bracket / len(rankings)
    }


def get_bracket_range_name(min_bracket: Optional[int], max_bracket: Optional[int]) -> str:
    """
    Возвращает человеко-читаемое название диапазона

    Примеры:
        get_bracket_range_name(1, 12) -> "M+1-12"
        get_bracket_range_name(12, None) -> "M+12+"
        get_bracket_range_name(None, None) -> "All brackets"
    """
    if min_bracket is None and max_bracket is None:
        return "All brackets"
    elif min_bracket is None:
        return f"M+1-{max_bracket}"
    elif max_bracket is None:
        return f"M+{min_bracket}+"
    else:
        return f"M+{min_bracket}-{max_bracket}"


# ============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ В ВАШЕМ ПРОЕКТЕ
# ============================================================================

async def example_usage():
    """
    Пример интеграции в существующий код
    """
    from app.agregator.constant import API_URL, CLIENT_ID, CLIENT_SECRET, TOKEN_URL
    import base64

    # Получаем токен (из вашего кода)
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        token = r.json()["access_token"]

        # ВАРИАНТ 1: Получить low и high keys отдельно
        low_keys, high_keys = await fetch_low_and_high_keys(
            client=client,
            token=token,
            api_url=API_URL,
            encounter_id=62660,
            class_name="Priest",
            spec_name="Shadow",
            low_threshold=12  # Граница между low и high
        )

        print(f"Low keys: {len(low_keys)} записей")
        print(f"High keys: {len(high_keys)} записей")

        # Статистика для low keys
        low_stats = calculate_bracket_statistics(low_keys)
        print(f"Low keys средний score: {low_stats['avg_score']:.2f}")

        # Статистика для high keys
        high_stats = calculate_bracket_statistics(high_keys)
        print(f"High keys средний score: {high_stats['avg_score']:.2f}")

        # ВАРИАНТ 2: Кастомные диапазоны
        beginner_keys = await fetch_rankings_with_bracket_filter(
            client, token, API_URL, 62660, "Priest", "Shadow",
            min_bracket=1, max_bracket=10
        )

        elite_keys = await fetch_rankings_with_bracket_filter(
            client, token, API_URL, 62660, "Priest", "Shadow",
            min_bracket=20, max_bracket=None
        )

        print(f"Beginner (M+1-10): {len(beginner_keys)} записей")
        print(f"Elite (M+20+): {len(elite_keys)} записей")


if __name__ == "__main__":
    asyncio.run(example_usage())
