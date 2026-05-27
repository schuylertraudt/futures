import httpx
from .base import BaseFetcher

ODDSBLAZE_FUTURES_BASE = "https://futures.oddsblaze.com/"


class OddsBlazeFetcher(BaseFetcher):
    def __init__(self, api_key: str, cache_dir: str, ttl_seconds: int):
        super().__init__(cache_dir, ttl_seconds)
        self._api_key = api_key

    async def fetch(self, cache_key: str, league: str, sportsbook: str | None = None) -> dict:
        path = self._cache_path(cache_key)
        if self._is_cache_valid(path):
            return self._read_cache(path)

        if not self._api_key:
            raise ValueError("ODDSBLAZE_API_KEY is not set. Add it to your .env file.")

        data = await self._raw_futures(league, sportsbook)
        self._write_cache(path, data)
        return self._read_cache(path)

    async def _raw_futures(self, league: str, sportsbook: str | None = None) -> dict | list:
        params: dict = {"key": self._api_key}
        if league:
            params["league"] = league
        if sportsbook:
            params["sportsbook"] = sportsbook

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(ODDSBLAZE_FUTURES_BASE, params=params)
            response.raise_for_status()
        return response.json()

    async def discover(self, league: str, sportsbook: str | None = None) -> dict | list:
        """Raw pass-through for discovery — bypasses cache, returns exactly what OddsBlaze sends."""
        if not self._api_key:
            raise ValueError("ODDSBLAZE_API_KEY is not set. Add it to your .env file.")
        return await self._raw_futures(league, sportsbook)
