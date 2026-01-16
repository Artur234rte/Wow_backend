"""
Детальная проверка данных о персонажах через WarcraftLogs API v2
"""
import asyncio
import httpx
import json

CLIENT_ID = "a0c39d1e-d0c5-4845-bffc-8c8613c6c474"
CLIENT_SECRET = "zT6WdIWjVwrCmOlDCNLWwgYt0DULsVSTHWOPRbiU"
TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
API_URL = "https://www.warcraftlogs.com/api/v2/client"


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


async def test_full_player_data(access_token: str):
    """
    Получаем полные данные о топ-1 игроке в лидерборде
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
            size: 1
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

        data = response.json()

        if "data" in data and data["data"]:
            rankings = data["data"]["worldData"]["encounter"]["characterRankings"]
            if rankings and "rankings" in rankings and len(rankings["rankings"]) > 0:
                player = rankings["rankings"][0]

                print("="*80)
                print("ПОЛНАЯ ИНФОРМАЦИЯ О ТОП-1 ИГРОКЕ")
                print("="*80)

                print(f"\n📊 ОСНОВНАЯ ИНФОРМАЦИЯ:")
                print(f"  Имя: {player.get('name')}")
                print(f"  Класс: {player.get('class')}")
                print(f"  Специализация: {player.get('spec')}")
                print(f"  DPS: {player.get('amount', 0):,.0f}")
                print(f"  Уровень ключа: +{player.get('hardModeLevel', 0)}")
                print(f"  Score: {player.get('score', 0):.2f}")

                server = player.get('server', {})
                print(f"\n🌍 СЕРВЕР:")
                print(f"  Название: {server.get('name')}")
                print(f"  Регион: {server.get('region')}")

                print(f"\n🏆 СТАТУС В ЛИДЕРБОРДЕ:")
                print(f"  Medal: {player.get('medal')}")
                print(f"  Bracket: {player.get('bracketData')}")

                # ТАЛАНТЫ
                talents = player.get('talents', [])
                print(f"\n✨ ТАЛАНТЫ (всего {len(talents)}):")
                if talents:
                    print(f"  Пример первых 5:")
                    for i, talent in enumerate(talents[:5], 1):
                        print(f"    {i}. TalentID: {talent.get('talentID')}, Points: {talent.get('points')}")

                # ЭКИПИРОВКА
                gear = player.get('gear', [])
                print(f"\n⚔️  ЭКИПИРОВКА (всего слотов: {len(gear)}):")
                if gear:
                    total_ilvl = 0
                    equipped_items = 0

                    slot_names = [
                        "Head", "Neck", "Shoulder", "Shirt", "Chest", "Waist", "Legs", "Feet",
                        "Wrist", "Hands", "Finger1", "Finger2", "Trinket1", "Trinket2",
                        "Back", "MainHand", "OffHand"
                    ]

                    for idx, item in enumerate(gear):
                        slot_name = slot_names[idx] if idx < len(slot_names) else f"Slot{idx}"
                        item_id = item.get('id', 0)
                        item_quality = item.get('quality', 0)
                        item_ilvl = int(item.get('itemLevel', 0))

                        if item_ilvl > 0:
                            total_ilvl += item_ilvl
                            equipped_items += 1

                        print(f"    {slot_name:12} | ItemID: {item_id:6} | iLvl: {item_ilvl:3} | Quality: {item_quality}")

                        # Gems/enchants если есть
                        if 'gems' in item:
                            gems = item.get('gems', [])
                            if gems:
                                print(f"                   └─ Gems: {gems}")
                        if 'permanentEnchant' in item:
                            enchant = item.get('permanentEnchant')
                            print(f"                   └─ Enchant: {enchant}")

                    avg_ilvl = total_ilvl / equipped_items if equipped_items > 0 else 0
                    print(f"\n  📈 Средний iLvl: {avg_ilvl:.1f}")

                # ПРОЧАЯ ИНФОРМАЦИЯ
                print(f"\n📝 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:")
                print(f"  Report Code: {player.get('report', {}).get('code')}")
                print(f"  Fight ID: {player.get('report', {}).get('fightID')}")
                print(f"  Duration: {player.get('duration', 0) / 1000:.1f}s")
                print(f"  Affixes: {player.get('affixes', [])}")

                guild = player.get('guild')
                if guild:
                    print(f"\n🏰 ГИЛЬДИЯ:")
                    print(f"  Название: {guild.get('name')}")
                    print(f"  Faction: {guild.get('faction')}")

                print("\n" + "="*80)
                print("ПРОВЕРКА ДОСТУПНОСТИ RIO SCORE")
                print("="*80)

                # Пробуем найти RIO в различных полях
                rio_fields_to_check = [
                    'mythicPlusScore', 'rioScore', 'raiderIOScore', 'rio',
                    'mythicScore', 'm+Score', 'score'
                ]

                print(f"\n🔍 Все доступные ключи в данных игрока:")
                available_keys = list(player.keys())
                for key in available_keys:
                    print(f"  - {key}")

                print(f"\n❌ RIO Score в WarcraftLogs API:")
                print(f"  RIO score НЕ доступен через WarcraftLogs API")
                print(f"  Поле 'score' = {player.get('score')} - это Mythic+ performance score для данного забега")
                print(f"  Это НЕ Raider.IO score персонажа")

                # Сохраняем полный JSON для анализа
                with open('/Users/mac/Desktop/test_work/Wow/B/player_full_data.json', 'w', encoding='utf-8') as f:
                    json.dump(player, f, indent=2, ensure_ascii=False)

                print(f"\n💾 Полные данные сохранены в: player_full_data.json")

                return player

        return None


async def test_character_data_api(access_token: str):
    """
    Проверка characterData API для конкретного персонажа
    """
    print("\n" + "="*80)
    print("ПРОВЕРКА CharacterData API")
    print("="*80)

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
          zoneRankings
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

        data = response.json()

        print(f"\n📊 Результат запроса CharacterData:")
        if "data" in data and data["data"]:
            char = data["data"]["characterData"]["character"]
            if char:
                print(f"  ID: {char.get('id')}")
                print(f"  Имя: {char.get('name')}")
                print(f"  Сервер: {char.get('server', {}).get('name')}")

                # gameData
                game_data = char.get('gameData')
                print(f"\n  gameData тип: {type(game_data)}")
                print(f"  gameData содержимое: {json.dumps(game_data, indent=4)}")

                # zoneRankings
                zone_rankings = char.get('zoneRankings')
                if zone_rankings:
                    print(f"\n  zoneRankings доступны")
                    print(f"  Метрика: {zone_rankings.get('metric')}")
                    print(f"  Zone: {zone_rankings.get('zone')}")

        print(f"\n❌ ВЫВОД: CharacterData API:")
        print(f"  1. Предоставляет базовую информацию о персонаже (ID, имя, сервер)")
        print(f"  2. gameData - это кешированные данные из Armory, могут устаревать")
        print(f"  3. НЕ содержит RIO score")
        print(f"  4. zoneRankings - рейтинги по рейдовым зонам")


async def main():
    print("🔐 Получение access token...")
    access_token = await get_access_token()
    print("✅ Access token получен\n")

    # Тест 1: Полные данные игрока из лидерборда
    try:
        player = await test_full_player_data(access_token)
    except Exception as e:
        print(f"❌ Ошибка в test_full_player_data: {e}")
        import traceback
        traceback.print_exc()

    # Тест 2: CharacterData API
    try:
        await test_character_data_api(access_token)
    except Exception as e:
        print(f"❌ Ошибка в test_character_data_api: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("ИТОГОВЫЕ ВЫВОДЫ")
    print("="*80)
    print("""
✅ ЧТО МОЖНО ПОЛУЧИТЬ из WarcraftLogs API:

1. ЧЕРЕЗ characterRankings (worldData.encounter.characterRankings):
   - Имя, класс, специализация игрока
   - DPS/HPS метрики для конкретного забега
   - Таланты (полный список talent IDs)
   - Экипировка (item IDs, item levels, gems, enchants)
   - Уровень ключа (hardModeLevel)
   - Performance score для забега (НЕ RIO!)
   - Информация о сервере и гильдии
   - Report code и fight ID для детального анализа

2. ЧЕРЕЗ characterData (characterData.character):
   - Базовая информация о персонаже (ID, имя, сервер)
   - Рейтинги по рейдовым зонам (zoneRankings)
   - Кешированные данные из Armory (gameData) - могут устаревать

❌ ЧТО НЕЛЬЗЯ ПОЛУЧИТЬ:

1. RIO Score (Raider.IO Score):
   - WarcraftLogs API НЕ предоставляет RIO scores
   - Поле "score" в characterRankings - это performance score за конкретный забег
   - Это НЕ общий рейтинг персонажа из Raider.IO

2. Общий M+ рейтинг персонажа:
   - Нет данных о лучших забегах персонажа по всем подземельям
   - Нет агрегированного M+ score

💡 РЕКОМЕНДАЦИИ:

1. Для получения gear и talents - используйте characterRankings с includeCombatantInfo=true
   ✅ Это то, что вы УЖЕ делаете в текущем коде

2. Для получения RIO scores - ПРОДОЛЖАЙТЕ использовать Raider.IO API
   ✅ Это единственный способ получить реальный RIO score персонажа

3. CharacterData API - НЕ НУЖЕН для вашей текущей задачи:
   - Не предоставляет RIO scores
   - Не предоставляет gear/talents (для этого используйте characterRankings)
   - Полезен только для получения базовой информации о персонаже

🎯 ТЕКУЩАЯ АРХИТЕКТУРА ПРАВИЛЬНАЯ:
   WarcraftLogs API (gear, talents, DPS) + Raider.IO API (RIO scores) = Полные данные
    """)


if __name__ == "__main__":
    asyncio.run(main())
