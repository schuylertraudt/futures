import json
import httpx
from datetime import datetime, timezone
from pathlib import Path
from .base import BaseFetcher

KALSHI_BASE = "https://trading-api.kalshi.com/trade-api/v2"


class KalshiFetcher(BaseFetcher):
    def __init__(
        self,
        api_key: str,
        email: str,
        password: str,
        cache_dir: str,
        ttl_seconds: int,
    ):
        super().__init__(cache_dir, ttl_seconds)
        self._api_key = api_key
        self._email = email
        self._password = password
        self._token: str | None = None
        self._token_path = Path(cache_dir) / ".kalshi_token.json"

    def _api_key_headers(self) -> dict:
        # Kalshi API keys use a dedicated header, not Authorization Bearer
        return {"KALSHI-ACCESS-KEY": self._api_key}

    def _token_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _load_token(self) -> str | None:
        if not self._token_path.exists():
            return None
        try:
            data = json.loads(self._token_path.read_text())
            expires = datetime.fromisoformat(data["expires_at"])
            if datetime.now(timezone.utc) < expires:
                return data["token"]
        except (KeyError, ValueError, OSError):
            pass
        return None

    def _save_token(self, token: str) -> None:
        from datetime import timedelta
        expires = datetime.now(timezone.utc) + timedelta(hours=23)
        self._token_path.write_text(
            json.dumps({"token": token, "expires_at": expires.isoformat()})
        )

    async def _authenticate(self) -> str:
        if not self._email or not self._password:
            raise ValueError(
                "No Kalshi credentials found. Set KALSHI_API_KEY (from Kalshi account "
                "settings) or KALSHI_EMAIL + KALSHI_PASSWORD in your .env file."
            )
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{KALSHI_BASE}/log_in",
                json={"email": self._email, "password": self._password},
            )
            response.raise_for_status()
        token = response.json().get("token")
        if not token:
            raise ValueError("Kalshi login did not return a token.")
        self._save_token(token)
        return token

    async def _get_headers(self) -> dict:
        if self._api_key:
            return self._api_key_headers()
        if self._token:
            return self._token_headers(self._token)
        cached = self._load_token()
        if cached:
            self._token = cached
            return self._token_headers(self._token)
        self._token = await self._authenticate()
        return self._token_headers(self._token)

    async def _request(self, client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
        """Make a request, trying both auth header formats if the first returns 401."""
        headers = await self._get_headers()
        response = await client.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401 and self._api_key:
            # Try the other header format as a fallback
            alt_headers = {"Authorization": f"Bearer {self._api_key}"}
            response = await client.request(method, url, headers=alt_headers, **kwargs)
            if response.status_code == 200:
                # Remember which format worked by patching _api_key_headers
                print("[Kalshi] API key works with Authorization: Bearer format")
                self.__class__._api_key_headers = lambda self: {"Authorization": f"Bearer {self._api_key}"}

        if response.status_code == 401 and not self._api_key:
            # JWT expired — re-authenticate once
            self._token = None
            self._token_path.unlink(missing_ok=True)
            headers = await self._get_headers()
            response = await client.request(method, url, headers=headers, **kwargs)

        return response

    async def fetch(self, cache_key: str, series_ticker: str, **kwargs) -> dict:
        path = self._cache_path(cache_key)
        if self._is_cache_valid(path):
            return self._read_cache(path)

        markets = await self._fetch_markets(series_ticker)
        self._write_cache(path, markets)
        return self._read_cache(path)

    async def _fetch_markets(self, series_ticker: str) -> list[dict]:
        markets = []
        cursor = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                params: dict = {"series_ticker": series_ticker, "status": "open", "limit": 100}
                if cursor:
                    params["cursor"] = cursor

                response = await self._request(client, "GET", f"{KALSHI_BASE}/markets", params=params)
                response.raise_for_status()

                body = response.json()
                markets.extend(body.get("markets", []))
                cursor = body.get("cursor")
                if not cursor:
                    break

        return markets

    async def discover_series(self, query: str = "") -> list[dict]:
        """List available Kalshi series, optionally filtered by query string."""
        params: dict = {"limit": 100}
        if query:
            params["search"] = query
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request(client, "GET", f"{KALSHI_BASE}/series", params=params)
            response.raise_for_status()
        return response.json().get("series", [])
