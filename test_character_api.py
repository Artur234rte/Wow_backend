"""
Тестовый скрипт для проверки CharacterData API WarcraftLogs v2
"""
import asyncio
import httpx
import json
from typing import Optional, Dict, Any

CLIENT_ID = "a0c39d1e-d0c5-4845-bffc-8c8613c6c474"
CLIENT_SECRET = "zT6WdIWjVwrCmOlDCNLWwgYt0DULsVSTHWOPRbiU"
TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
API_URL = "https://www.warcraftlogs.com/api/v2/client"


async def get_access_token() -> str:
    """Получить OAuth access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials"
            },
            auth=(CLIENT_ID, CLIENT_SECRET)
        )
        response.raise_for_status()
        token_data = response.json()
        return token_data["access_token"]


async def test_character_query(access_token: str):
    """
    Тест 1: Проверка Character через characterData
    Пытаемся получить данные о конкретном персонаже
    """
    query = """
    query {
      characterData {
        character(name: "Gingi", serverSlug: "tarren-mill", serverRegion: "eu") {
          id
          name
          server {
            name
            region {
              name
            }
          }
          # Попытка получить различные данные
          zoneRankings
          encounterRankings
          # gameData - это JSON поле, можно только получить как есть
          gameData
        }
      }
    }
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            API_URL,
            json={"query": query},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print("\n=== TEST 1: Character Query ===")
        print(f"Status: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
        return response.json()


async def test_character_rankings_with_combatant_info(access_token: str):
    """
    Тест 2: Проверка characterRankings с includeCombatantInfo=true
    Это то, что мы используем сейчас для получения gear/talents
    """
    query = """
    query($encounterID: Int!, $className: String!, $specName: String!) {
      worldData {
        encounter(id: $encounterID) {
          name
          characterRankings(
            className: $className
            specName: $specName
            metric: dps
            leaderboard: LogsOnly
            includeCombatantInfo: true
          )
        }
      }
    }
    """

    variables = {
        "encounterID": 62660,  # Ara-Kara
        "className": "Mage",
        "specName": "Fire"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            API_URL,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print("\n=== TEST 2: CharacterRankings with CombatantInfo ===")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")

        # Проверяем структуру данных
        if "data" in data and data["data"]:
            rankings = data["data"]["worldData"]["encounter"]["characterRankings"]
            if rankings and "rankings" in rankings:
                print("\n=== Первый игрок в рейтинге ===")
                first_player = rankings["rankings"][0]
                print(f"Имя: {first_player.get('name')}")
                print(f"Сервер: {first_player.get('server')}")
                print(f"DPS: {first_player.get('amount')}")
                print(f"Есть combatantInfo: {'combatantInfo' in first_player}")
                if 'combatantInfo' in first_player:
                    print(f"CombatantInfo ключи: {first_player['combatantInfo'].keys()}")

        return data


async def test_character_from_rankings(access_token: str):
    """
    Тест 3: Получить данные персонажа из rankings, затем запросить его через characterData
    """
    # Сначала получаем топ игрока
    rankings_query = """
    query {
      worldData {
        encounter(id: 62660) {
          name
          characterRankings(
            className: "Mage"
            specName: "Fire"
            metric: dps
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
            json={"query": rankings_query},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        data = response.json()

        print("\n=== TEST 3: Get Character Details from Rankings ===")

        if "data" in data and data["data"]:
            rankings = data["data"]["worldData"]["encounter"]["characterRankings"]
            if rankings and "rankings" in rankings and len(rankings["rankings"]) > 0:
                player = rankings["rankings"][0]
                name = player.get("name")
                server = player.get("server", {}).get("slug")
                region = player.get("server", {}).get("region")

                print(f"\nТоп игрок: {name} - {server} ({region})")

                # Теперь пытаемся получить детали через characterData
                if name and server and region:
                    character_query = f"""
                    query {{
                      characterData {{
                        character(name: "{name}", serverSlug: "{server}", serverRegion: "{region}") {{
                          id
                          name
                          zoneRankings
                        }}
                      }}
                    }}
                    """

                    char_response = await client.post(
                        API_URL,
                        json={"query": character_query},
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    print(f"\nОтвет characterData:\n{json.dumps(char_response.json(), indent=2)}")


async def test_mythic_plus_score_availability(access_token: str):
    """
    Тест 4: Проверка доступности Mythic+ Score / RIO в WarcraftLogs
    """
    # Попробуем разные варианты запроса M+ данных
    queries_to_test = [
        {
            "name": "Character mythicPlusScore",
            "query": """
            query {
              characterData {
                character(name: "Gingi", serverSlug: "tarren-mill", serverRegion: "eu") {
                  name
                  mythicPlusScore
                }
              }
            }
            """
        },
        {
            "name": "Character gameData (JSON field)",
            "query": """
            query {
              characterData {
                character(name: "Gingi", serverSlug: "tarren-mill", serverRegion: "eu") {
                  name
                  gameData
                }
              }
            }
            """
        },
        {
            "name": "WorldData player mythic+",
            "query": """
            query {
              worldData {
                mythicPlusRankings(
                  playerName: "Gingi"
                  serverSlug: "tarren-mill"
                  serverRegion: "eu"
                )
              }
            }
            """
        }
    ]

    print("\n=== TEST 4: Mythic+ Score / RIO Availability ===")

    async with httpx.AsyncClient() as client:
        for test in queries_to_test:
            print(f"\n--- Тест: {test['name']} ---")
            response = await client.post(
                API_URL,
                json={"query": test["query"]},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            result = response.json()
            print(f"Status: {response.status_code}")

            # Проверяем на ошибки GraphQL
            if "errors" in result:
                print(f"❌ Ошибка: {result['errors'][0]['message']}")
            else:
                print(f"✅ Успех: {json.dumps(result, indent=2)}")


async def main():
    print("🔐 Получение access token...")
    access_token = await get_access_token()
    print("✅ Access token получен")

    # Запускаем все тесты
    await test_character_query(access_token)
    await test_character_rankings_with_combatant_info(access_token)
    await test_character_from_rankings(access_token)
    await test_mythic_plus_score_availability(access_token)

    print("\n" + "="*80)
    print("ВЫВОДЫ:")
    print("="*80)
    print("""
1. CharacterData API позволяет получать данные о конкретных персонажах
2. Через characterRankings с includeCombatantInfo=true мы получаем gear/talents
3. RIO Score (Mythic+ Score) - проверяем доступность через API
4. Если RIO недоступен в WarcraftLogs - необходимо продолжить использовать Raider.IO API
    """)


if __name__ == "__main__":
    asyncio.run(main())
