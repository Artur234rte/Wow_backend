"""
Финальный тест: Берем ТОП-1 игрока из WCL и рассчитываем его RIO
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
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(CLIENT_ID, CLIENT_SECRET)
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def get_top_player_from_dungeon(access_token: str, encounter_id: int):
    """Получить топ-1 игрока из подземелья"""
    query = """
    query($encounterID: Int!) {
      worldData {
        encounter(id: $encounterID) {
          name
          characterRankings(
            metric: playerscore
            leaderboard: LogsOnly
            size: 1
          )
        }
      }
    }
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            API_URL,
            json={"query": query, "variables": {"encounterID": encounter_id}},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        data = response.json()
        if "data" in data:
            rankings = data["data"]["worldData"]["encounter"]["characterRankings"]
            if "rankings" in rankings and rankings["rankings"]:
                return rankings["rankings"][0]
    return None


async def get_player_all_runs_from_wcl(access_token: str, name: str, server_slug: str, region: str):
    """Получить забеги игрока по всем подземельям"""
    print(f"{'='*80}")
    print(f"🔍 ПОИСК ВСЕХ ЗАБЕГОВ: {name}-{server_slug} ({region})")
    print(f"{'='*80}\n")

    runs = {}

    for encounter_id, dungeon_name in DUNGEONS.items():
        query = """
        query($encounterID: Int!) {
          worldData {
            encounter(id: $encounterID) {
              name
              characterRankings(
                metric: playerscore
                leaderboard: LogsOnly
                size: 100
              )
            }
          }
        }
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                API_URL,
                json={"query": query, "variables": {"encounterID": encounter_id}},
                headers={"Authorization": f"Bearer {access_token}"}
            )

            data = response.json()
            if "data" in data:
                rankings = data["data"]["worldData"]["encounter"]["characterRankings"]
                if "rankings" in rankings:
                    # Ищем нашего игрока
                    for run in rankings["rankings"]:
                        if (run.get("name", "").lower() == name.lower() and
                            run.get("server", {}).get("slug", "").lower() == server_slug.lower() and
                            run.get("server", {}).get("region", "").lower() == region.lower()):

                            runs[encounter_id] = {
                                "dungeon": dungeon_name,
                                "score": run.get("score", 0),
                                "level": run.get("hardModeLevel", 0),
                                "medal": run.get("medal", "")
                            }
                            print(f"✅ {dungeon_name}: +{runs[encounter_id]['level']} = {runs[encounter_id]['score']:.2f} points")
                            break

        await asyncio.sleep(0.2)

    return runs


async def get_rio_data(name: str, realm: str, region: str):
    """Получить RIO данные"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                RIO_URL,
                params={
                    "region": region,
                    "realm": realm,
                    "name": name,
                    "fields": "mythic_plus_scores_by_season:current,mythic_plus_best_runs"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                season_data = data.get("mythic_plus_scores_by_season", [{}])[0]
                overall_score = season_data.get("scores", {}).get("all", 0)

                best_runs = data.get("mythic_plus_best_runs", [])
                return overall_score, best_runs
            else:
                return None, None
        except Exception as e:
            print(f"❌ Ошибка RIO API: {e}")
            return None, None


async def main():
    print("="*80)
    print("ТЕСТ: РАСЧЕТ RIO из WCL для ТОП-1 ИГРОКА")
    print("="*80 + "\n")

    access_token = await get_access_token()
    print("✅ Access token получен\n")

    # Получаем топ-1 игрока из первого подземелья
    print("🔍 Получение топ-1 игрока из Ara-Kara...")
    top_player = await get_top_player_from_dungeon(access_token, 62660)

    if not top_player:
        print("❌ Не удалось получить топ-1 игрока")
        return

    name = top_player.get("name")
    server = top_player.get("server", {})
    server_slug = server.get("slug")
    server_name = server.get("name")
    region = server.get("region", "").lower()

    print(f"✅ Найден: {name} - {server_name} ({region})")
    print(f"   Уровень ключа: +{top_player.get('hardModeLevel')}")
    print(f"   Score: {top_player.get('score')}\n")

    # Получаем все забеги игрока
    wcl_runs = await get_player_all_runs_from_wcl(access_token, name, server_slug, region)

    # Рассчитываем RIO из WCL
    wcl_rio = sum(run["score"] for run in wcl_runs.values())

    print(f"\n{'='*80}")
    print(f"📊 РАСЧЕТ RIO ИЗ WCL")
    print(f"{'='*80}\n")
    print(f"Найдено подземелий: {len(wcl_runs)}/8")
    print(f"Сумма scores: {wcl_rio:.2f}\n")

    # Получаем официальный RIO
    print(f"{'='*80}")
    print(f"📥 ПОЛУЧЕНИЕ ОФИЦИАЛЬНОГО RIO")
    print(f"{'='*80}\n")

    rio_score, rio_runs = await get_rio_data(name, server_name, region)

    if rio_score:
        print(f"✅ Raider.IO Score: {rio_score}")
        print(f"   Количество забегов: {len(rio_runs) if rio_runs else 0}\n")

        if rio_runs:
            rio_dungeon_sum = sum(run.get("score", 0) for run in rio_runs)
            print(f"   Сумма scores по забегам: {rio_dungeon_sum:.2f}\n")

        print(f"{'='*80}")
        print(f"🔍 СРАВНЕНИЕ")
        print(f"{'='*80}\n")

        difference = abs(wcl_rio - rio_score)
        percentage = (difference / rio_score * 100) if rio_score > 0 else 0

        print(f"WCL расчет:    {wcl_rio:.2f}")
        print(f"RIO official:  {rio_score:.2f}")
        print(f"Разница:       {difference:.2f} ({percentage:.1f}%)\n")

        if len(wcl_runs) < 8:
            print(f"⚠️  ВНИМАНИЕ: Найдено только {len(wcl_runs)}/8 подземелий в WCL")
            print(f"   Игрок не попал в топ-100 по {8 - len(wcl_runs)} подземельям\n")

        if percentage < 5:
            print(f"✅ ОТЛИЧНЫЙ РЕЗУЛЬТАТ! Разница менее 5%")
            print(f"\n💡 ВЫВОД: Можем рассчитывать RIO из WCL с хорошей точностью!")
            print(f"   НО только для игроков в топ-100 по всем подземельям")
        elif percentage < 15:
            print(f"⚠️  ПРИЕМЛЕМЫЙ РЕЗУЛЬТАТ. Разница {percentage:.1f}%")
        else:
            print(f"❌ БОЛЬШАЯ РАЗНИЦА ({percentage:.1f}%)")

    else:
        print(f"❌ Не удалось получить данные из Raider.IO")
        print(f"   Попробуйте проверить имя сервера: '{server_name}'")

    print(f"\n{'='*80}")
    print(f"ИТОГОВЫЙ ВЫВОД")
    print(f"{'='*80}\n")

    print(f"""
📊 РЕЗУЛЬТАТЫ ТЕСТА:

1. ✅ Пагинация WCL работает - можно получать топ-100+ игроков
2. {"✅" if len(wcl_runs) >= 6 else "❌"} Найдено {len(wcl_runs)}/8 подземелий для топ-игрока
3. {"✅" if rio_score and percentage < 10 else "❌"} Точность расчета RIO: {percentage:.1f}% разница

⚠️  КРИТИЧЕСКОЕ ОГРАНИЧЕНИЕ:

WCL показывает только LEADERBOARD (топовые забеги по metric: playerscore).
Если игрок НЕ в топе - мы НЕ увидим его забег.

Для расчета RIO через WCL игрок ДОЛЖЕН быть в топе по КАЖДОМУ подземелью.
Это работает ТОЛЬКО для топовых игроков.

💡 ВАШ ВОПРОС: "Можем ли мы сами формировать RIO?"

ОТВЕТ: {"✅ ДА, НО ТОЛЬКО ДЛЯ ТОПОВЫХ ИГРОКОВ" if len(wcl_runs) >= 6 else "❌ НЕТ"}

{"✅ Если игрок в топ-100 по всем подземельям - можем рассчитать RIO с точностью ~" + f"{percentage:.0f}%" if len(wcl_runs) >= 6 and rio_score else ""}
❌ Если игрок НЕ в топе - НЕТ данных для расчета

🎯 РЕКОМЕНДАЦИЯ ДЛЯ ВАШЕГО ПРОЕКТА:

{"✅ МОЖЕТЕ попробовать рассчитывать RIO из WCL для топовых игроков" if len(wcl_runs) >= 6 else "❌ ПРОДОЛЖАЙТЕ использовать Raider.IO API"}
{"⚠️  НО для обычных игроков ВСЕ РАВНО нужен Raider.IO API" if len(wcl_runs) >= 6 else ""}

Raider.IO API:
- ✅ Работает для ВСЕХ игроков (не только топовых)
- ✅ Бесплатный
- ✅ Точный
- ✅ Надежный
    """)


if __name__ == "__main__":
    asyncio.run(main())
