import asyncio
import functools
import json
import time
from datetime import datetime, timezone
from pathlib import Path


class DraftKingsScraper:
    """
    Fetches DraftKings odds via headless Chrome (undetected-chromedriver).
    Navigates to the target page to establish a Cloudflare session, then
    calls DraftKings' internal JSON API from the browser context.
    Results are disk-cached like other fetchers.
    """

    NFL_EVENTGROUP_ID = 88808

    def __init__(self, cache_dir: str, ttl_seconds: int = 3600):
        self._cache_dir = Path(cache_dir)
        self._ttl_seconds = ttl_seconds
        self._driver = None

    # --- cache helpers ---

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / f"dk_{key}.json"

    def _is_cache_valid(self, path: Path) -> bool:
        if not path.exists():
            return False
        age = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
        return age < self._ttl_seconds

    def _read_cache(self, path: Path) -> dict:
        return json.loads(path.read_text())

    def _write_cache(self, path: Path, data: dict) -> None:
        self._cache_dir.mkdir(exist_ok=True)
        path.write_text(json.dumps(data))

    # --- browser management ---

    def _get_driver(self):
        if self._driver is not None:
            try:
                _ = self._driver.current_url
                return self._driver
            except Exception:
                self._driver = None

        try:
            import undetected_chromedriver as uc
        except ImportError:
            raise RuntimeError(
                "undetected-chromedriver not installed. "
                "Run: pip install undetected-chromedriver"
            )

        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        # Reduce memory footprint on small VPS
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")

        self._driver = uc.Chrome(options=options, version_main=148)
        self._driver.set_script_timeout(30)
        return self._driver

    # --- fetching ---

    def _fetch_sync(self, event_group_id: int, landing_url: str) -> dict:
        driver = self._get_driver()

        # Navigate to the landing page first to warm up the Cloudflare session
        driver.get(landing_url)
        time.sleep(5)

        # Navigate directly to the API URL — Chrome handles Cloudflare natively
        api_url = (
            f"https://sportsbook.draftkings.com"
            f"/sites/US-SB/api/v5/eventgroups/{event_group_id}?format=json"
        )
        driver.get(api_url)
        time.sleep(3)

        # Check for Cloudflare block
        source = driver.page_source
        if "cf_chl" in source or "Just a moment" in source:
            raise RuntimeError("Cloudflare challenge not resolved — IP may be blocked")

        # Chrome renders JSON as plain text in <body> or <pre>
        body_text = driver.execute_script("return document.body.innerText")
        if not body_text:
            raise RuntimeError("Empty response from DraftKings API URL")

        try:
            return json.loads(body_text)
        except json.JSONDecodeError:
            preview = body_text[:200]
            raise RuntimeError(f"DraftKings returned non-JSON: {preview}")

    async def fetch(self, cache_key: str, event_group_id: int, landing_url: str) -> dict:
        path = self._cache_path(cache_key)
        if self._is_cache_valid(path):
            return self._read_cache(path)

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None,
            functools.partial(self._fetch_sync, event_group_id, landing_url),
        )
        wrapper = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": raw,
        }
        self._write_cache(path, wrapper)
        return wrapper

    def cache_age_seconds(self, key: str) -> int:
        path = self._cache_path(key)
        if not path.exists():
            return -1
        return int(datetime.now(timezone.utc).timestamp() - path.stat().st_mtime)

    def invalidate(self, key: str) -> None:
        path = self._cache_path(key)
        if path.exists():
            path.unlink()

    def close(self) -> None:
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
