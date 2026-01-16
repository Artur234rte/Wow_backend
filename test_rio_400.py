import httpx
import asyncio

async def test():
    """Тестируем, почему некоторые имена дают 400 ошибку"""
    # Примеры из ваших логов
    test_cases = [
        ('us', 'area-52', 'Bubbledan'),
        ('us', 'illidan', 'Teddytwo'),
        ('us', 'tichondrius', 'Hustlin'),
    ]

    async with httpx.AsyncClient() as client:
        for region, realm, name in test_cases:
            try:
                print(f"\n🔍 Тестирую: {name} на {realm}-{region}")
                r = await client.get(
                    'https://raider.io/api/v1/characters/profile',
                    params={
                        'region': region,
                        'realm': realm,
                        'name': name,
                        'fields': 'mythic_plus_scores_by_season:current'
                    },
                    timeout=10
                )
                print(f"✅ {name}: {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    print(f"   Данные получены: {data.get('name')}")
            except httpx.HTTPStatusError as e:
                print(f"❌ {name}: HTTP {e.response.status_code}")
                print(f"   URL: {e.request.url}")
                print(f"   Response: {e.response.text[:500]}")
            except Exception as e:
                print(f"❌ {name}: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
