"""
Простой тест: что возвращает WarcraftLogs с metric: playerscore
"""
import asyncio
import httpx
import json

CLIENT_ID = "a0c39d1e-d0c5-4845-bffc-8c8613c6c474"
CLIENT_SECRET = "zT6WdIWjVwrCmOlDCNLWwgYt0DULsVSTHWOPRbiU"
TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
API_URL = "https://www.warcraftlogs.com/api/v2/client"


async def test_playerscore():
    # Получаем токен
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(CLIENT_ID, CLIENT_SECRET)
        )
        token = resp.json()["access_token"]

        # Тест 1: playerscore для M+
        print("="*80)
        print("ТЕСТ 1: metric: playerscore для M+ подземелья")
        print("="*80)

        query1 = """
        query {
          worldData {
            encounter(id: 62660) {
              name
              characterRankings(
                metric: playerscore
                leaderboard: LogsOnly
                size: 5
              )
            }
          }
        }
        """

        resp1 = await client.post(
            API_URL,
            json={"query": query1},
            headers={"Authorization": f"Bearer {token}"}
        )

        data1 = resp1.json()
        print(f"\nСтатус: {resp1.status_code}")
        print(f"Ответ:\n{json.dumps(data1, indent=2)}\n")

        if "data" in data1:
            rankings = data1["data"]["worldData"]["encounter"]["characterRankings"]
            if "rankings" in rankings and rankings["rankings"]:
                print(f"✅ Получено {len(rankings['rankings'])} топ игроков с playerscore")
                print(f"\nПример топ-1:")
                top1 = rankings["rankings"][0]
                print(f"  Имя: {top1.get('name')}")
                print(f"  Класс: {top1.get('class')}")
                print(f"  Spec: {top1.get('spec')}")
                print(f"  Score: {top1.get('score')}")
                print(f"  Amount (DPS): {top1.get('amount')}")
                print(f"  Key Level: +{top1.get('hardModeLevel')}")
                print(f"  Все ключи:")
                for key, value in top1.items():
                    print(f"    {key}: {value}")

        # Тест 2: DPS для сравнения
        print("\n" + "="*80)
        print("ТЕСТ 2: metric: dps для M+ подземелья (для сравнения)")
        print("="*80)

        query2 = """
        query {
          worldData {
            encounter(id: 62660) {
              name
              characterRankings(
                metric: dps
                className: "Mage"
                specName: "Fire"
                leaderboard: LogsOnly
                size: 3
              )
            }
          }
        }
        """

        resp2 = await client.post(
            API_URL,
            json={"query": query2},
            headers={"Authorization": f"Bearer {token}"}
        )

        data2 = resp2.json()
        print(f"\nСтатус: {resp2.status_code}")

        if "data" in data2:
            rankings2 = data2["data"]["worldData"]["encounter"]["characterRankings"]
            if "rankings" in rankings2 and rankings2["rankings"]:
                print(f"✅ Получено {len(rankings2['rankings'])} топ игроков с DPS")
                print(f"\nПример топ-1:")
                top1_dps = rankings2["rankings"][0]
                print(f"  Имя: {top1_dps.get('name')}")
                print(f"  Score: {top1_dps.get('score')}")
                print(f"  Amount (DPS): {top1_dps.get('amount')}")
                print(f"  Key Level: +{top1_dps.get('hardModeLevel')}")

        # Тест 3: Проверка наличия RIO в ответе
        print("\n" + "="*80)
        print("ВЫВОД")
        print("="*80)

        print(f"""
📊 ЧТО ТАКОЕ 'score' В WARCRAFTLOGS:

Поле 'score' в ответе characterRankings - это PERFORMANCE SCORE за конкретный забег.
Это оценка производительности игрока в данном конкретном M+ забеге.

Это НЕ RIO score (Raider.IO score).

RIO Score - это СУММА лучших забегов по всем подземельям сезона,
с учетом Tyrannical и Fortified affixes отдельно.

🔍 МЕТРИКА playerscore:
- Возвращает рейтинги игроков по "player score" метрике
- Это все еще performance score за конкретный забег
- НЕ является агрегированным RIO score персонажа

❌ ПОЧЕМУ НЕЛЬЗЯ РАССЧИТАТЬ RIO ИЗ WCL:

1. WCL показывает только ТОПОВЫЕ забеги (leaderboard)
2. Для расчета RIO нужны ВСЕ лучшие забеги игрока по каждому подземелью
3. Если игрок не в топе конкретного подземелья - мы не увидим его данные
4. RIO требует учета Tyrannical и Fortified отдельно
5. Формулы расчета могут отличаться

✅ РЕШЕНИЕ: Использовать Raider.IO API
        """)


asyncio.run(test_playerscore())
