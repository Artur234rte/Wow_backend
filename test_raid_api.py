"""
Тестируем API WarcraftLogs для рейдов
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.agregator.view import get_access_token, fetch_leaderboard_optimized
from app.agregator.constant import RAID
from app.agregator.quieres import QUERY_FOR_RAID_DPS
import httpx


async def test_raid_encounters():
    """Проверяем, что API возвращает данные для рейдов"""
    print("Получение access token...")
    token = await get_access_token()
    print(f"✅ Token получен\n")

    # Тестируем первый рейд босс
    test_boss_id = 2902  # Ulgrax the Devourer
    test_boss_name = RAID[test_boss_id]
    test_class = "DeathKnight"
    test_spec = "Blood"

    print(f"🔍 Тестируем босса: {test_boss_name} (ID: {test_boss_id})")
    print(f"   Класс: {test_class}, Спек: {test_spec}\n")

    async with httpx.AsyncClient(timeout=30) as client:
        # Тестируем запрос напрямую
        variables = {
            "encounterID": test_boss_id,
            "className": test_class,
            "specName": test_spec,
        }

        print("📤 Отправляем GraphQL запрос...")
        r = await client.post(
            "https://www.warcraftlogs.com/api/v2/client",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "query": QUERY_FOR_RAID_DPS,
                "variables": variables,
            },
            timeout=30
        )

        print(f"📥 Статус: {r.status_code}\n")

        if r.status_code == 200:
            data = r.json()

            # Проверяем структуру ответа
            if "errors" in data:
                print(f"❌ GraphQL ошибки:")
                for error in data["errors"]:
                    print(f"   - {error.get('message', error)}")
                return

            world_data = data.get("data", {}).get("worldData", {})
            encounter = world_data.get("encounter")

            if not encounter:
                print("❌ Encounter не найден в ответе")
                print(f"   Полный ответ: {data}")
                return

            print(f"✅ Encounter найден: {encounter.get('name')}")

            rankings_block = encounter.get("characterRankings")
            if not rankings_block:
                print("❌ characterRankings пустой или отсутствует")
                print(f"   Encounter данные: {encounter}")
                return

            rankings = rankings_block.get("rankings", [])
            print(f"✅ Получено {len(rankings)} записей в rankings")

            if rankings:
                print(f"\n📊 Первые 3 записи:")
                for i, rank in enumerate(rankings[:3]):
                    name = rank.get("name", "Unknown")
                    dps = rank.get("amount", 0)
                    print(f"   {i+1}. {name}: {dps:,.0f} DPS")
            else:
                print("⚠️  Rankings массив пустой")
                print(f"   characterRankings: {rankings_block}")

        else:
            print(f"❌ HTTP ошибка: {r.status_code}")
            print(f"   Ответ: {r.text[:500]}")


if __name__ == "__main__":
    asyncio.run(test_raid_encounters())
