from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.wowlogs.client import WowLogsClient
from app.core.config import get_settings


RANKINGS_QUERY = """
query($page: Int!) {
  worldData {
    classRankings(page: $page, role: DPS) {
      page
      hasMorePages
      rankings {
        className
        classSlug
        specName
        specSlug
        total
        color
      }
    }
  }
}
"""


CLASS_COLORS: dict[str, str] = {
    "death_knight": "#C41E3A",
    "demon_hunter": "#A330C9",
    "druid": "#FF7C0A",
    "evoker": "#33937F",
    "hunter": "#AAD372",
    "mage": "#3FC7EB",
    "monk": "#00FF98",
    "paladin": "#F48CBA",
    "priest": "#FFFFFF",
    "rogue": "#FFF468",
    "shaman": "#0070DD",
    "warlock": "#8788EE",
    "warrior": "#C69B6D",
}


class DpsAggregator:
    """Aggregates DPS meta information from Warcraft Logs."""

    def __init__(self, client: WowLogsClient):
        self.client = client
        self.settings = get_settings()

    async def fetch_rankings(self) -> list[dict[str, Any]]:
        page = 1
        rankings: list[dict[str, Any]] = []

        while True:
            data = await self.client.execute(RANKINGS_QUERY, {"page": page})
            class_rankings = (
                data.get("worldData", {})
                .get("classRankings", {})
            )
            page_rankings = class_rankings.get("rankings") or []
            rankings.extend(page_rankings)

            if not class_rankings.get("hasMorePages"):
                break

            page += 1

        if not rankings:
            raise RuntimeError("No rankings received from Warcraft Logs")

        return rankings

    def normalize(self, raw_rankings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sorted_rankings = sorted(raw_rankings, key=lambda item: int(item.get("total", 0)), reverse=True)
        normalized: list[dict[str, Any]] = []
        for idx, item in enumerate(sorted_rankings, start=1):
            class_slug = (item.get("classSlug") or "").lower()
            spec_slug = (item.get("specSlug") or "").lower()
            normalized.append(
                {
                    "role": "dps",
                    "wow_class": class_slug,
                    "spec": spec_slug,
                    "spec_name": item.get("specName") or spec_slug.title(),
                    "score": int(item.get("total", 0)),
                    "rank": idx,
                    "patch": self.settings.current_patch,
                }
            )
        return normalized

    async def build_snapshot(self) -> list[dict[str, Any]]:
        raw = await self.fetch_rankings()
        normalized = self.normalize(raw)
        now = datetime.now(timezone.utc)
        for item in normalized:
            item["updated_at"] = now
        return normalized

    @staticmethod
    def color_for_class(class_slug: str) -> str:
        return CLASS_COLORS.get(class_slug.lower(), "#FFFFFF")
