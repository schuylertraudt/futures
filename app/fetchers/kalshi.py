import json
import httpx
from datetime import datetime, timezone
from pathlib import Path
from .base import BaseFetcher

KALSHI_BASE = "https://trading-api.kalshi.com/trade-api/v2"


class KalshiFetcher(BaseFetcher):
    def __init__(
        self,
        email: str,
        password: str,
        cache_dir: str,
        ttl_seconds: int,
    ):
        super().__init__(cache_dir, ttl_seconds)
        self._email = email
        self._password = password
        self._token: str | None = None
        self._token_path = Path(cache_dir) / ".kalshi_token.json"

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
                "KALSHI_EMAIL and KALSHI_PASSWORD are not set. Add them to your .env file."
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

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        cached = self._load_token()
        if cached:
            self._token = cached
            return self._token
        self._token = await self._authenticate()
        return self._token

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    async def fetch(self, cache_key: str, series_ticker: str, **kwargs) -> dict:
        path = self._cache_path(cache_key)
        if self._is_cache_valid(path):
            return self._read_cache(path)

        token = await self._get_token()
        markets = await self._fetch_markets(token, series_ticker)

        self._write_cache(path, markets)
        return self._read_cache(path)

    async def _fetch_markets(
        self, token: str, series_ticker: str
    ) -> list[dict]:
        headers = self._auth_headers(token)
        markets = []
        cursor = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                params: dict = {"series_ticker": series_ticker, "status": "open", "limit": 100}
                if cursor:
                    params["cursor"] = cursor

                response = await client.get(
                    f"{KALSHI_BASE}/markets",
                    headers=headers,
                    params=params,
                )
                if response.status_code == 401:
                    # Token expired — re-authenticate once
                    self._token = None
                    self._token_path.unlink(missing_ok=True)
                    token = await self._get_token()
                    headers = self._auth_headers(token)
                    response = await client.get(
                        f"{KALSHI_BASE}/markets",
                        headers=headers,
                        params=params,
                    )
                response.raise_for_status()

                body = response.json()
                markets.extend(body.get("markets", []))
                cursor = body.get("cursor")
                if not cursor:
                    break

        return markets

    async def discover_series(self, query: str = "") -> list[dict]:
        """List available Kalshi series, optionally filtered by query string."""
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30.0) as client:
            params: dict = {"limit": 100}
            if query:
                params["search"] = query
            response = await client.get(
                f"{KALSHI_BASE}/series",
                headers=self._auth_headers(token),
                params=params,
            )
            response.raise_for_status()
        return response.json().get("series", [])
