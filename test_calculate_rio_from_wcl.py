"""
ТЕСТ: Можем ли мы рассчитать RIO самостоятельно из WarcraftLogs?

План:
1. Берем топ-1000 (10 страниц × 100) игроков по каждому подземелью
2. Для конкретного игрока находим его лучшие забеги
3. Считаем RIO самостоятельно
4. Сравниваем с Raider.IO
"""
import asyncio
import httpx
import json
from collections import defaultdict
from typing import Dict, List, Optional

CLIENT_ID = "a0c39d1e-d0c5-4845-bffc-8c8613c6c474"
CLIENT_SECRET = "zT6WdIWjVwrCmOlDCNLWwgYt0DULsVSTHWOPRbiU"
TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
API_URL = "https://www.warcraftlogs.com/api/v2/client"
RIO_URL = "https://raider.io/api/v1/characters/profile"

# Все подземелья сезона (раскомментируем для полного теста)
DUNGEONS = {
    62660: "Ara-Kara, City of Echoes",
    12830: "Eco-Dome Al'dani",
    62287: "Halls of Atonement",
    62773: "Operation: Floodgate",
    62649: "Priory of the Sacred Flame",
    112442: "Tazavesh: So'leah's Gambit",
    112441: "Tazavesh: Streets of Wonder",
    62662: "The Dawnbreaker"
}


async def get_access_token() -> str:
    """Получить OAuth access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(CLIENT_ID, CLIENT_SECRET)
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def get_dungeon_rankings_paginated(
    access_token: str,
    encounter_id: int,
    class_name: str = None,
    spec_name: str = None,
    max_pages: int = 10  # топ-1000 игроков
) -> List[dict]:
    """
    Получить топ-1000 игроков по подземелью используя пагинацию
    """
    all_rankings = []

    filter_str = f" ({class_name} {spec_name})" if class_name and spec_name else ""
    print(f"📊 Получение топ-{max_pages * 100} для encounter {encounter_id}{filter_str}...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(1, max_pages + 1):
            # Строим запрос динамически
            if class_name and spec_name:
                query = """
                query($encounterID: Int!, $className: String!, $specName: String!, $page: Int!) {
                  worldData {
                    encounter(id: $encounterID) {
                      name
                      characterRankings(
                        className: $className
                        specName: $specName
                        metric: dps
                        leaderboard: LogsOnly
                        page: $page
                      )
                    }
                  }
                }
                """
                variables = {
                    "encounterID": encounter_id,
                    "className": class_name,
                    "specName": spec_name,
                    "page": page
                }
            else:
                query = """
                query($encounterID: Int!, $page: Int!) {
                  worldData {
                    encounter(id: $encounterID) {
                      name
                      characterRankings(
                        metric: playerscore
                        leaderboard: LogsOnly
                        page: $page
                      )
                    }
                  }
                }
                """
                variables = {
                    "encounterID": encounter_id,
                    "page": page
                }

            try:
                response = await client.post(
                    API_URL,
                    json={"query": query, "variables": variables},
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                if response.status_code != 200:
                    print(f"   ❌ Страница {page}: Ошибка {response.status_code}")
                    break

                data = response.json()

                if "data" in data and data["data"]:
                    rankings_data = data["data"]["worldData"]["encounter"]["characterRankings"]

                    if "error" in rankings_data:
                        print(f"   ❌ Страница {page}: {rankings_data['error']}")
                        break

                    if "rankings" in rankings_data and rankings_data["rankings"]:
                        all_rankings.extend(rankings_data["rankings"])
                        print(f"   ✅ Страница {page}: +{len(rankings_data['rankings'])} игроков (всего: {len(all_rankings)})")

                        # Проверяем, есть ли еще страницы
                        has_more = rankings_data.get("hasMorePages", False)
                        if not has_more:
                            print(f"   ℹ️  Достигнут конец данных на странице {page}")
                            break
                    else:
                        print(f"   ⚠️  Страница {page}: Нет данных")
                        break

                # Небольшая задержка между запросами
                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"   ❌ Страница {page}: Исключение {e}")
                break

    print(f"   📈 Итого получено: {len(all_rankings)} игроков\n")
    return all_rankings


async def find_player_best_runs(
    access_token: str,
    player_name: str,
    server: str,
    region: str,
    class_name: str = None,
    spec_name: str = None
) -> Dict[int, dict]:
    """
    Найти лучшие забеги игрока по всем подземельям из топ-1000
    """
    print(f"{'='*80}")
    print(f"🔍 ПОИСК ЗАБЕГОВ ИГРОКА: {player_name}-{server} ({region})")
    if class_name and spec_name:
        print(f"   Фильтр: {class_name} {spec_name}")
    print(f"{'='*80}\n")

    player_runs = {}

    for encounter_id, dungeon_name in DUNGEONS.items():
        print(f"🏰 {dungeon_name}:")

        # Получаем топ-1000 игроков
        rankings = await get_dungeon_rankings_paginated(
            access_token,
            encounter_id,
            class_name=class_name,
            spec_name=spec_name,
            max_pages=10
        )

        # Ищем нашего игрока
        best_run = None
        for run in rankings:
            if (run.get("name", "").lower() == player_name.lower() and
                run.get("server", {}).get("slug", "").lower() == server.lower() and
                run.get("server", {}).get("region", "").lower() == region.lower()):

                # Берем первый найденный (он будет лучшим по score)
                if best_run is None or run.get("score", 0) > best_run.get("score", 0):
                    best_run = run

        if best_run:
            player_runs[encounter_id] = {
                "dungeon": dungeon_name,
                "score": best_run.get("score", 0),
                "hardModeLevel": best_run.get("hardModeLevel", 0),
                "duration": best_run.get("duration", 0),
                "medal": best_run.get("medal", ""),
                "affixes": best_run.get("affixes", [])
            }
            print(f"   ✅ Найден забег: +{player_runs[encounter_id]['hardModeLevel']} = {player_runs[encounter_id]['score']:.2f} points ({player_runs[encounter_id]['medal']})\n")
        else:
            print(f"   ❌ Игрок не найден в топ-1000\n")

    return player_runs


async def get_rio_from_raiderio(
    player_name: str,
    realm: str,
    region: str
) -> Optional[dict]:
    """Получить RIO данные из Raider.IO"""
    print(f"{'='*80}")
    print(f"📥 ПОЛУЧЕНИЕ ДАННЫХ ИЗ RAIDER.IO")
    print(f"{'='*80}\n")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                RIO_URL,
                params={
                    "region": region,
                    "realm": realm,
                    "name": player_name,
                    "fields": "mythic_plus_scores_by_season:current,mythic_plus_best_runs"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()

                season_data = data.get("mythic_plus_scores_by_season", [{}])[0]
                overall_score = season_data.get("scores", {}).get("all", 0)

                print(f"✅ Raider.IO Overall Score: {overall_score}\n")

                best_runs = data.get("mythic_plus_best_runs", [])
                print(f"🏆 Лучшие забеги из Raider.IO ({len(best_runs)}):")

                rio_dungeon_scores = {}
                for run in best_runs:
                    dungeon = run.get("short_name", run.get("dungeon", "Unknown"))
                    level = run.get("mythic_level", 0)
                    score = run.get("score", 0)

                    rio_dungeon_scores[dungeon] = {
                        "level": level,
                        "score": score,
                        "dungeon_full": run.get("dungeon", "")
                    }
                    print(f"   {dungeon}: +{level} = {score:.2f} points")

                return {
                    "overall_score": overall_score,
                    "dungeon_scores": rio_dungeon_scores,
                    "total_runs": len(best_runs)
                }
            else:
                print(f"❌ Ошибка: {response.status_code}")
                if response.status_code == 400:
                    print(f"   Возможно, неправильное имя сервера. Попробуйте с дефисом, например: 'tarren-mill'")
                return None

        except Exception as e:
            print(f"❌ Исключение: {e}")
            return None


def calculate_rio_from_wcl(player_runs: Dict[int, dict]) -> float:
    """
    Рассчитать RIO score из данных WCL
    Простая формула: сумма всех scores
    """
    total_score = sum(run["score"] for run in player_runs.values())
    return total_score


async def compare_results(
    wcl_runs: Dict[int, dict],
    rio_data: Optional[dict]
):
    """Сравнить результаты"""
    print(f"\n{'='*80}")
    print(f"📊 СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print(f"{'='*80}\n")

    # Расчет RIO из WCL
    wcl_calculated_rio = calculate_rio_from_wcl(wcl_runs)

    print(f"🔢 РАССЧИТАННЫЙ RIO ИЗ WCL:")
    print(f"   Количество подземелий: {len(wcl_runs)}/8")
    print(f"   Сумма scores: {wcl_calculated_rio:.2f}")

    print(f"\n📊 Детали по подземельям (WCL):")
    for encounter_id, run in wcl_runs.items():
        print(f"   {run['dungeon']}: +{run['hardModeLevel']} = {run['score']:.2f} points")

    if rio_data:
        rio_official = rio_data["overall_score"]

        print(f"\n🎯 ОФИЦИАЛЬНЫЙ RIO ИЗ RAIDER.IO:")
        print(f"   Overall Score: {rio_official}")
        print(f"   Количество лучших забегов: {rio_data['total_runs']}")

        print(f"\n{'='*80}")
        print(f"🔍 АНАЛИЗ")
        print(f"{'='*80}\n")

        difference = abs(wcl_calculated_rio - rio_official)
        percentage = (difference / rio_official * 100) if rio_official > 0 else 0

        print(f"WCL расчет:  {wcl_calculated_rio:.2f}")
        print(f"RIO official: {rio_official:.2f}")
        print(f"Разница:      {difference:.2f} ({percentage:.1f}%)")

        if percentage < 5:
            print(f"\n✅ ОТЛИЧНЫЙ РЕЗУЛЬТАТ! Разница менее 5%")
            print(f"   Мы МОЖЕМ рассчитывать RIO из WCL с хорошей точностью!")
        elif percentage < 15:
            print(f"\n⚠️  ПРИЕМЛЕМЫЙ РЕЗУЛЬТАТ. Разница {percentage:.1f}%")
            print(f"   Возможные причины:")
            print(f"   - Tyrannical/Fortified учитываются по-разному")
            print(f"   - Не все подземелья найдены в топ-1000")
        else:
            print(f"\n❌ БОЛЬШАЯ РАЗНИЦА ({percentage:.1f}%)")
            print(f"   Возможные причины:")
            print(f"   - Игрок не попал в топ-1000 по некоторым подземельям")
            print(f"   - Формулы расчета score отличаются")
            print(f"   - RIO учитывает Tyrannical и Fortified отдельно")

        # Детальное сравнение по подземельям
        print(f"\n📋 ДЕТАЛЬНОЕ СРАВНЕНИЕ ПО ПОДЗЕМЕЛЬЯМ:\n")

        for encounter_id, wcl_run in wcl_runs.items():
            dungeon_name = wcl_run["dungeon"]

            # Ищем соответствие в RIO
            rio_match = None
            for rio_dungeon, rio_info in rio_data["dungeon_scores"].items():
                # Проверяем по названию подземелья
                if (rio_dungeon.lower() in dungeon_name.lower() or
                    dungeon_name.lower() in rio_info["dungeon_full"].lower()):
                    rio_match = rio_info
                    break

            if rio_match:
                wcl_score = wcl_run["score"]
                rio_score = rio_match["score"]
                score_diff = abs(wcl_score - rio_score)

                print(f"{dungeon_name}:")
                print(f"   WCL: +{wcl_run['hardModeLevel']} = {wcl_score:.2f} points")
                print(f"   RIO: +{rio_match['level']} = {rio_score:.2f} points")
                print(f"   Разница: {score_diff:.2f} points\n")
            else:
                print(f"{dungeon_name}:")
                print(f"   WCL: +{wcl_run['hardModeLevel']} = {wcl_run['score']:.2f} points")
                print(f"   RIO: Нет соответствия\n")


async def main():
    print(f"{'='*80}")
    print(f"ТЕСТ: РАСЧЕТ RIO ИЗ WARCRAFTLOGS (топ-1000 через пагинацию)")
    print(f"{'='*80}\n")

    # Тестируем на реальном игроке
    # Выберем игрока, который скорее всего будет в топ-1000 по нескольким подземельям
    test_player = {
        "name": "Placement",  # Из предыдущих тестов видели в топе
        "server": "mal-ganis",
        "realm": "Mal'Ganis",
        "region": "us",
        "class": "Mage",
        "spec": "Fire"
    }

    print(f"🎮 Тестовый игрок: {test_player['name']}-{test_player['server']} ({test_player['region']})")
    print(f"   {test_player['class']} {test_player['spec']}\n")

    # Получаем токен
    print("🔐 Получение access token...")
    access_token = await get_access_token()
    print("✅ Access token получен\n")

    # Находим забеги игрока в WCL
    wcl_runs = await find_player_best_runs(
        access_token,
        test_player["name"],
        test_player["server"],
        test_player["region"],
        class_name=test_player["class"],
        spec_name=test_player["spec"]
    )

    # Получаем данные из RIO
    rio_data = await get_rio_from_raiderio(
        test_player["name"],
        test_player["realm"],
        test_player["region"]
    )

    # Сравниваем
    if wcl_runs and rio_data:
        await compare_results(wcl_runs, rio_data)
    elif wcl_runs and not rio_data:
        print("\n⚠️  Данные из WCL получены, но не удалось получить данные из Raider.IO")
        print(f"Рассчитанный RIO из WCL: {calculate_rio_from_wcl(wcl_runs):.2f}")
    else:
        print("\n❌ Недостаточно данных для сравнения")

    print(f"\n{'='*80}")
    print(f"ИТОГОВЫЙ ВЫВОД")
    print(f"{'='*80}\n")

    if wcl_runs:
        print(f"""
✅ ПАГИНАЦИЯ РАБОТАЕТ!
   - Мы можем получать топ-1000 игроков (10 страниц × 100)
   - Нашли {len(wcl_runs)}/8 подземелий для игрока

📊 МОЖНО ЛИ РАССЧИТАТЬ RIO?
   {"✅ ДА, если:" if len(wcl_runs) >= 6 else "⚠️  ЧАСТИЧНО:"}
   - Игрок попадает в топ-1000 по большинству подземелий
   - Сумма scores дает приблизительный RIO

⚠️  ОГРАНИЧЕНИЯ:
   1. Если игрок НЕ в топ-1000 какого-то подземелья - теряем данные
   2. Формула может отличаться от официальной Blizzard
   3. RIO учитывает Tyrannical/Fortified отдельно

💡 РЕКОМЕНДАЦИЯ:
   {"✅ Можно использовать WCL для расчета RIO с погрешностью" if len(wcl_runs) >= 6 else "❌ Лучше продолжать использовать Raider.IO API"}
   {"для игроков в топ-1000" if len(wcl_runs) >= 6 else ""}
        """)


if __name__ == "__main__":
    asyncio.run(main())
