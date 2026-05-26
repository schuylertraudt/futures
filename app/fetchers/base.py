import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class BaseFetcher(ABC):
    def __init__(self, cache_dir: str, ttl_seconds: int):
        self._cache_dir = Path(cache_dir)
        self._ttl_seconds = ttl_seconds
        self._cache_dir.mkdir(exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        safe_key = key.replace("/", "_").replace(" ", "_")
        return self._cache_dir / f"{safe_key}.json"

    def _is_cache_valid(self, path: Path) -> bool:
        if not path.exists():
            return False
        try:
            wrapper = json.loads(path.read_text())
            fetched_at = datetime.fromisoformat(wrapper["fetched_at"])
            age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
            return age < self._ttl_seconds
        except (KeyError, ValueError):
            return False

    def _read_cache(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cache(self, path: Path, data: Any) -> None:
        wrapper = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        path.write_text(json.dumps(wrapper, indent=2))

    def cache_age_seconds(self, cache_key: str) -> int:
        path = self._cache_path(cache_key)
        if not path.exists():
            return -1
        try:
            wrapper = json.loads(path.read_text())
            fetched_at = datetime.fromisoformat(wrapper["fetched_at"])
            return int((datetime.now(timezone.utc) - fetched_at).total_seconds())
        except (KeyError, ValueError):
            return -1

    def invalidate(self, cache_key: str) -> None:
        path = self._cache_path(cache_key)
        if path.exists():
            path.unlink()

    @abstractmethod
    async def fetch(self, cache_key: str, **kwargs) -> dict:
        ...
