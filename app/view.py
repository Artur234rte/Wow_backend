from constant import TOKEN_URL, CLIENT_ID, CLIENT_SECRET, WOW_CLASS_SPECS, SPEC_ROLE_METRIC, API_URL, RIO_URL
from quieres import q_with_gear_and_talent, q_balance, q_simple
import base64
import httpx
import json
import asyncio
import re
import unicodedata
from models.model import MetaBySpec, Base
from sqlalchemy.exc import SQLAlchemyError

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

DATABASE_URL = "postgresql+asyncpg://wow_user:wow_password@localhost:5432/wow_db"


engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def add_meta_by_spec(obj: MetaBySpec) -> MetaBySpec:
    async with AsyncSessionLocal() as session:
        try:
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj
        except SQLAlchemyError:
            await session.rollback()
            raise


async def get_access_token():
    auth = base64.b64encode(
        f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
    ).decode()

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        r.raise_for_status()
        return r.json()["access_token"]
async def balance():
    token = await get_access_token()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={"query": q_balance},
        )
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
def normalize_region(region: str) -> str:
    """
    EU / eu / Europe -> eu
    US / us / America -> us
    """
    region = region.strip().lower()

    if region in ("eu", "europe"):
        return "eu"
    if region in ("us", "america", "na"):
        return "us"
    if region in ("kr", "korea"):
        return "kr"
    if region in ("tw", "taiwan"):
        return "tw"

    raise ValueError(f"Unknown region: {region}")
def normalize_realm(realm: str) -> str:
    """
    'Tarren Mill' -> 'tarren-mill'
    'Twisting Nether' -> 'twisting-nether'
    'Quel’Thalas' -> 'quel-thalas'
    """
    realm = realm.strip().lower()
    realm = unicodedata.normalize("NFKD", realm)
    realm = realm.encode("ascii", "ignore").decode("ascii")
    realm = re.sub(r"[^a-z0-9\s-]", "", realm)
    realm = re.sub(r"[\s-]+", "-", realm)
    return realm



async def fetch_rio(client: httpx.AsyncClient, region: str, realm: str, name: str):
    params = {
        "region": region,
        "realm": realm,
        "name": name,
        "fields": "mythic_plus_scores_by_season:current"
    }

    try:
        r = await client.get(RIO_URL, params=params)
        r.raise_for_status()
        data = r.json()

        seasons = data.get("mythic_plus_scores_by_season", [])
        if not seasons:
            return None

        scores = seasons[0]["scores"]
        return {
            "rio_all": scores.get("all"),
        }

    except httpx.HTTPError:
        return None




async def fetch_leaderboard(client, token, encounter_id, class_name, spec_name):
    variables = {
        "encounterID": encounter_id,
        "className": class_name,
        "specName": spec_name,
    }
    r = await client.post(
        API_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": q_simple,
            "variables": variables,
        },
    )
    r.raise_for_status()
    data = r.json()
    rankings_block = data["data"]["worldData"]["encounter"]["characterRankings"]
    if not rankings_block or "rankings" not in rankings_block:
        return []
    players = []
    counter_players_with_score = 0
    total_score = 0
    for item in rankings_block["rankings"]:
        hidden = item.get("hidden", False)
        server_obj = item.get("server") or {}
        server_name = server_obj.get("name", "")
        server_region = server_obj.get("region", "")
        server = normalize_realm(server_name) if server_name else ""
        region = server_region.lower() if server_region else ""
        rio = None
        if not hidden and server and region and item.get("name") != "Anonymous":
            try:
                rio_data = await fetch_rio(
                    client,
                    region=region,
                    realm=server,
                    name=item["name"]
                )
                if rio_data:
                    rio = rio_data.get("rio_all")
                    total_score += float(rio)
                    counter_players_with_score += 1
            except Exception as e:
                print(f"RIO error for {item.get('name')}: {e}")

        players.append({
            "name": item.get("name", "Anonymous"),
            "class": item.get("class"),
            "spec": item.get("spec"),
            "rio": rio,
            "hardModeLevel": item.get("hardModeLevel"),
            "server_region": server_region or None,
            "server_name": server_name or None,
            "faction": item.get("faction"),
            "leaderboard": item.get("leaderboard"),
            "hidden": hidden,
        })
    # return [
    #     {
    #         "name": item.get("name", "Anonymous"),
    #         "class": item.get("class"),
    #         "spec": item.get("spec"),
    #         "score": item.get("score"),
    #     }
    #     for item in rankings_block["rankings"]
    # ]
    average_score = total_score // counter_players_with_score
    return average_score

async def test_leaderboard():
    token = await get_access_token()
    all_rankings = []
    async with httpx.AsyncClient(timeout=30) as client:
        #r = await fetch_leaderboard(client, token, encounter_id=62660, class_name="DeathKnight", spec_name="Blood")
        #print(json.dumps(r,indent=2, ensure_ascii=False))
        encounters = [
                    62660,
                    12830,
                    62287,
                    62773,
                    62649,
                    112442,
                    112441,
                    62662
                    ]
        for encounter in encounters:
            for class_name, specs in WOW_CLASS_SPECS.items():
                for spec_name in specs:
                    meta_average_value = await fetch_leaderboard(
                        client, token, encounter, class_name, spec_name
                    )   
                    meta = {
                        "class_name": class_name,
                        "spec": spec_name,
                        "meta": meta_average_value,
                        "spec_type": SPEC_ROLE_METRIC[spec_name][0],
                        "encounter_id": encounter
                    }
                    obj = MetaBySpec(**meta)
                    all_rankings.append(meta)
                    saved_obj = await add_meta_by_spec(obj)
            #     print(saved_obj)
            # print(len(all_rankings))
    print(json.dumps(all_rankings, indent=2, ensure_ascii=False))

async def main():
    try:
        await init_models()
    except Exception as e:
        print("❌ Init failed, aborting startup")
        raise
    await test_leaderboard()
    await balance()




import time
if __name__ == "__main__":
    start = time.perf_counter()
    asyncio.run(main())
    end = time.perf_counter()
    print(f"Время выполнения: {end - start:.6f} сек")
