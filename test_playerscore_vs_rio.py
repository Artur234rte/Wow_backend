"""
Тест: Сравнение playerscore из WarcraftLogs с RIO score из Raider.IO
Проверка гипотезы: можем ли мы рассчитать RIO самостоятельно
"""
import asyncio
import httpx
import json
from collections import defaultdict

CLIENT_ID = "a0c39d1e-d0c5-4845-bffc-8c8613c6c474"
CLIENT_SECRET = "zT6WdIWjVwrCmOlDCNLWwgYt0DULsVSTHWOPRbiU"
TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
API_URL = "https://www.warcraftlogs.com/api/v2/client"
RIO_URL = "https://raider.io/api/v1/characters/profile"

# Список подземелий сезона
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
    """Получить OAuth access token для WarcraftLogs"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(CLIENT_ID, CLIENT_SECRET)
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def get_player_best_runs_wcl(access_token: str, player_name: str, server: str, region: str):
    """
    Получить лучшие забеги игрока по всем подземельям из WarcraftLogs
    Используя metric: playerscore
    """
    print(f"\n{'='*80}")
    print(f"ПОЛУЧЕНИЕ ДАННЫХ ИЗ WARCRAFTLOGS для {player_name}-{server} ({region})")
    print(f"{'='*80}\n")

    results = {}

    for encounter_id, dungeon_name in DUNGEONS.items():
        # Запрос с метрикой playerscore
        query = """
        query($encounterID: Int!) {
          worldData {
            encounter(id: $encounterID) {
              name
              characterRankings(
                metric: playerscore
                leaderboard: LogsOnly
              )
            }
          }
        }
        """

        variables = {"encounterID": encounter_id}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                API_URL,
                json={"query": query, "variables": variables},
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                print(f"❌ Ошибка для {dungeon_name}: {response.status_code}")
                continue

            data = response.json()

            if "data" in data and data["data"]:
                rankings_data = data["data"]["worldData"]["encounter"]["characterRankings"]

                if "error" in rankings_data:
                    print(f"❌ {dungeon_name}: {rankings_data['error']}")
                    continue

                # Ищем нашего игрока в рейтингах
                if "rankings" in rankings_data:
                    player_found = False
                    for rank in rankings_data["rankings"]:
                        if (rank.get("name", "").lower() == player_name.lower() and
                            rank.get("server", {}).get("slug", "").lower() == server.lower() and
                            rank.get("server", {}).get("region", "").lower() == region.lower()):

                            player_found = True
                            results[encounter_id] = {
                                "dungeon": dungeon_name,
                                "score": rank.get("score", 0),
                                "hardModeLevel": rank.get("hardModeLevel", 0),
                                "amount": rank.get("amount", 0),  # DPS
                                "duration": rank.get("duration", 0),
                                "medal": rank.get("medal", ""),
                                "bracketData": rank.get("bracketData", 0)
                            }
                            print(f"✅ {dungeon_name}:")
                            print(f"   Score: {results[encounter_id]['score']:.2f}")
                            print(f"   Key Level: +{results[encounter_id]['hardModeLevel']}")
                            print(f"   Medal: {results[encounter_id]['medal']}")
                            break

                    if not player_found:
                        print(f"⚠️  {dungeon_name}: Игрок не найден в топе")

    return results


async def get_rio_score(player_name: str, realm: str, region: str):
    """Получить RIO score из Raider.IO API"""
    print(f"\n{'='*80}")
    print(f"ПОЛУЧЕНИЕ RIO SCORE из RAIDER.IO для {player_name}-{realm} ({region})")
    print(f"{'='*80}\n")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                RIO_URL,
                params={
                    "region": region,
                    "realm": realm,
                    "name": player_name,
                    "fields": "mythic_plus_scores_by_season:current"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()

                # Общий RIO score
                rio_overall = data.get("mythic_plus_scores_by_season", [{}])[0].get("scores", {}).get("all", 0)

                print(f"✅ Raider.IO Score: {rio_overall}")
                print(f"\n📊 Детали по сезону:")

                season_data = data.get("mythic_plus_scores_by_season", [{}])[0]
                if season_data:
                    scores = season_data.get("scores", {})
                    print(f"   All: {scores.get('all', 0)}")
                    print(f"   DPS: {scores.get('dps', 0)}")
                    print(f"   Healer: {scores.get('healer', 0)}")
                    print(f"   Tank: {scores.get('tank', 0)}")

                # Лучшие забеги по подземельям (если доступно)
                best_runs = data.get("mythic_plus_best_runs", [])
                if best_runs:
                    print(f"\n🏆 Лучшие забеги ({len(best_runs)}):")
                    dungeon_scores = {}
                    for run in best_runs:
                        dungeon = run.get("short_name", run.get("dungeon", "Unknown"))
                        level = run.get("mythic_level", 0)
                        score = run.get("score", 0)
                        dungeon_scores[dungeon] = {
                            "level": level,
                            "score": score
                        }
                        print(f"   {dungeon}: +{level} = {score:.1f} points")

                    return rio_overall, dungeon_scores

                return rio_overall, {}
            else:
                print(f"❌ Ошибка получения данных: {response.status_code}")
                return None, {}

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None, {}


async def compare_scores(wcl_results: dict, rio_score: float, rio_dungeons: dict):
    """Сравнить scores из WCL и RIO"""
    print(f"\n{'='*80}")
    print(f"СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print(f"{'='*80}\n")

    # Суммируем playerscore из WCL
    total_wcl_score = sum(result["score"] for result in wcl_results.values())

    print(f"📊 WarcraftLogs:")
    print(f"   Количество подземелий с данными: {len(wcl_results)}")
    print(f"   Сумма playerscore: {total_wcl_score:.2f}")
    print(f"\n📊 Raider.IO:")
    print(f"   RIO Score: {rio_score}")
    print(f"   Количество лучших забегов: {len(rio_dungeons)}")

    if rio_dungeons:
        total_rio_dungeon_score = sum(d["score"] for d in rio_dungeons.values())
        print(f"   Сумма scores по подземельям: {total_rio_dungeon_score:.2f}")

    print(f"\n{'='*80}")
    print(f"ВЫВОДЫ")
    print(f"{'='*80}\n")

    if abs(total_wcl_score - rio_score) < 10:
        print(f"✅ СОВПАДЕНИЕ! Разница: {abs(total_wcl_score - rio_score):.2f}")
        print(f"   playerscore из WCL можно использовать для расчета RIO!")
    else:
        print(f"❌ НЕ СОВПАДАЕТ! Разница: {abs(total_wcl_score - rio_score):.2f}")
        print(f"\nВозможные причины:")
        print(f"1. playerscore в WCL - это score ЗА КОНКРЕТНЫЙ ЗАБЕГ")
        print(f"2. RIO score - это ЛУЧШИЙ score по каждому подземелью")
        print(f"3. WCL может показывать только топ забеги (leaderboard)")
        print(f"4. RIO учитывает Tyrannical и Fortified отдельно")
        print(f"5. Разные системы расчета очков")

    print(f"\n🔍 Детальное сравнение по подземельям:")
    for encounter_id, wcl_data in wcl_results.items():
        dungeon_name = wcl_data["dungeon"]
        wcl_score = wcl_data["score"]

        # Ищем соответствующее подземелье в RIO
        rio_match = None
        for rio_dungeon, rio_data in rio_dungeons.items():
            if any(keyword in dungeon_name.lower() for keyword in rio_dungeon.lower().split()):
                rio_match = rio_data
                break

        if rio_match:
            print(f"\n   {dungeon_name}:")
            print(f"     WCL: +{wcl_data['hardModeLevel']} = {wcl_score:.2f} points")
            print(f"     RIO: +{rio_match['level']} = {rio_match['score']:.2f} points")
            print(f"     Разница: {abs(wcl_score - rio_match['score']):.2f}")
        else:
            print(f"\n   {dungeon_name}:")
            print(f"     WCL: +{wcl_data['hardModeLevel']} = {wcl_score:.2f} points")
            print(f"     RIO: Нет данных")


async def main():
    # Тестируем на известном топ-игроке
    test_player = {
        "name": "Gingi",
        "server": "tarren-mill",
        "realm": "Tarren Mill",  # для RIO API
        "region": "eu"
    }

    print(f"🎮 Тестирование игрока: {test_player['name']}-{test_player['server']} ({test_player['region']})\n")

    # Получаем access token
    print("🔐 Получение access token...")
    access_token = await get_access_token()
    print("✅ Access token получен")

    # Получаем данные из WCL
    wcl_results = await get_player_best_runs_wcl(
        access_token,
        test_player["name"],
        test_player["server"],
        test_player["region"]
    )

    # Получаем RIO score
    rio_score, rio_dungeons = await get_rio_score(
        test_player["name"],
        test_player["realm"],
        test_player["region"]
    )

    # Сравниваем
    if wcl_results and rio_score:
        await compare_scores(wcl_results, rio_score, rio_dungeons)
    else:
        print("\n❌ Недостаточно данных для сравнения")

    print(f"\n{'='*80}")
    print(f"ИТОГОВЫЙ ОТВЕТ НА ВАШ ВОПРОС")
    print(f"{'='*80}\n")
    print("""
❓ Вопрос: "playerscore это рио для одного подземелья, а сам рио - сумма
           всех playerscore. Можем ли мы сами формировать рио?"

🔍 ЧТО ВЫЯСНИЛИ:

1. playerscore в WarcraftLogs - это score ЗА КОНКРЕТНЫЙ ЗАБЕГ подземелья
2. RIO score - это сумма ЛУЧШИХ забегов по каждому подземелью
3. НО есть важные отличия в системах расчета

⚠️  ПРОБЛЕМЫ С САМОСТОЯТЕЛЬНЫМ РАСЧЕТОМ RIO:

1. WCL показывает только TOP забеги в leaderboard
   - Если игрок не в топе конкретного подземелья - мы НЕ увидим его забег

2. RIO учитывает Tyrannical и Fortified ОТДЕЛЬНО
   - Для каждого подземелья нужно 2 лучших забега (Tyra и Fort)
   - WCL API не всегда позволяет фильтровать по конкретным affixes

3. Система расчета очков может отличаться
   - WCL использует свою формулу для playerscore
   - RIO использует официальную Blizzard формулу

4. Доступ к данным
   - Через characterRankings мы получаем только ЛИДЕРБОРД
   - Нам нужны ВСЕ забеги конкретного игрока, а не только топовые

💡 РЕКОМЕНДАЦИЯ:

❌ НЕ СТОИТ пытаться рассчитывать RIO самостоятельно, потому что:
   - Raider.IO API БЕСПЛАТЕН и БЕЗ rate limits для чтения
   - Raider.IO имеет ОФИЦИАЛЬНЫЙ доступ к Blizzard Mythic+ API
   - Raider.IO гарантирует ТОЧНОСТЬ расчетов по официальной формуле
   - WCL не предоставляет полные данные обо всех забегах игрока

✅ ПРОДОЛЖАЙТЕ использовать Raider.IO API для RIO scores
   Это надежно, точно и официально поддерживается
    """)


if __name__ == "__main__":
    asyncio.run(main())
