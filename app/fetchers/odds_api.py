import httpx
from .base import BaseFetcher

ODDS_API_BASE = "https://api.the-odds-api.com/v4"


class OddsApiFetcher(BaseFetcher):
    def __init__(self, api_key: str, cache_dir: str, ttl_seconds: int):
        super().__init__(cache_dir, ttl_seconds)
        self._api_key = api_key
        self.requests_remaining: int | None = None
        self.requests_used: int | None = None

    async def fetch(
        self,
        cache_key: str,
        sport: str,
        markets: str,
        bookmakers: str,
    ) -> dict:
        path = self._cache_path(cache_key)
        if self._is_cache_valid(path):
            return self._read_cache(path)

        if not self._api_key:
            raise ValueError("ODDS_API_KEY is not set. Add it to your .env file.")

        url = f"{ODDS_API_BASE}/sports/{sport}/odds"
        params = {
            "apiKey": self._api_key,
            "regions": "us,eu",
            "markets": markets,
            "bookmakers": bookmakers,
            "oddsFormat": "decimal",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

        remaining = response.headers.get("x-requests-remaining")
        used = response.headers.get("x-requests-used")
        if remaining is not None:
            self.requests_remaining = int(remaining)
        if used is not None:
            self.requests_used = int(used)

        data = response.json()
        self._write_cache(path, data)
        return self._read_cache(path)

    async def list_sports(self) -> list[dict]:
        """Discover available sport keys — useful for finding win total events."""
        if not self._api_key:
            raise ValueError("ODDS_API_KEY is not set.")
        url = f"{ODDS_API_BASE}/sports"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"apiKey": self._api_key})
            response.raise_for_status()
        return response.json()
