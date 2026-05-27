from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from app.models import ScanResult
from app.maps.sports_config import SPORTS_CONFIG, BOOK_DISPLAY_NAMES
import app.scanner as scanner

router = APIRouter()

# Rate-limit state for /api/refresh
_last_refresh: datetime | None = None
_REFRESH_MIN_INTERVAL_SECONDS = 3600


@router.get("/api/scan", response_model=ScanResult)
async def get_scan(
    sport: str | None = Query(None, description="Filter by sport, e.g. 'nfl'"),
    positive_only: bool = Query(False, description="Return only lines with any positive EV"),
    min_ev: float | None = Query(None, description="Minimum EV% threshold (applies to either method)"),
    method: str = Query("both", description="'pinnacle', 'best', or 'both'"),
):
    result = await scanner.run_scan()

    rows = result.results

    if sport:
        rows = [r for r in rows if r.odds.sport == sport.lower()]

    if positive_only or min_ev is not None:
        threshold = min_ev if min_ev is not None else 0.0
        filtered = []
        for r in rows:
            evs: list[float] = []
            if method in ("pinnacle", "both") and r.ev_vs_pinnacle is not None:
                evs.append(r.ev_vs_pinnacle)
            if method in ("best", "both") and r.ev_vs_best is not None:
                evs.append(r.ev_vs_best)
            if evs and max(evs) >= threshold:
                filtered.append(r)
        rows = filtered

    return ScanResult(
        results=rows,
        scan_time=result.scan_time,
        cache_ages=result.cache_ages,
        requests_remaining=result.requests_remaining,
    )


@router.post("/api/refresh")
async def force_refresh():
    global _last_refresh
    now = datetime.now(timezone.utc)
    if _last_refresh is not None:
        elapsed = (now - _last_refresh).total_seconds()
        if elapsed < _REFRESH_MIN_INTERVAL_SECONDS:
            wait = int(_REFRESH_MIN_INTERVAL_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Refresh rate-limited. Try again in {wait}s to preserve API credits.",
            )
    scanner.invalidate_caches()
    _last_refresh = now
    result = await scanner.run_scan()
    return {"ok": True, "scan_time": result.scan_time, "requests_remaining": result.requests_remaining}


@router.get("/api/sports")
async def get_sports():
    return {
        "sports": [
            {"key": s["sport"], "description": s["description"]}
            for s in SPORTS_CONFIG
        ],
        "books": BOOK_DISPLAY_NAMES,
    }


@router.get("/api/kalshi/discover")
async def kalshi_discover(query: str = Query("nfl", description="Search term for Kalshi series")):
    """List available Kalshi series to help identify correct ticker prefixes."""
    from app.scanner import _kalshi_fetcher
    try:
        series = await _kalshi_fetcher.discover_series(query)
        return {"series": series}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/api/odds-api/sports")
async def odds_api_sports():
    """List all Odds API sport keys — useful for finding win total event keys."""
    from app.scanner import _odds_fetcher
    try:
        sports = await _odds_fetcher.list_sports()
        return {"sports": sports}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/api/odds-api/bookmakers")
async def odds_api_bookmakers(sport: str = "americanfootball_nfl", markets: str = "outrights"):
    """List all bookmaker slugs available for a sport — helps find correct keys for Fanatics, theScore, etc."""
    from app.scanner import _odds_fetcher
    try:
        books = await _odds_fetcher.list_bookmakers(sport, markets)
        return {"bookmakers": books, "sport": sport, "markets": markets}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/api/oddsblaze/discover")
async def oddsblaze_discover(
    league: str = Query("pga", description="League ID to try, e.g. pga, nba, NBA, mlb, nhl, nfl"),
    sportsbook: str = Query("fanduel", description="Sportsbook ID, e.g. fanduel, draftkings, betmgm"),
):
    """Raw OddsBlaze futures response — use to verify data and find valid league/book IDs."""
    from app.config import settings
    from app.fetchers.oddsblaze import OddsBlazeFetcher
    fetcher = OddsBlazeFetcher(
        api_key=settings.oddsblaze_api_key,
        cache_dir=settings.cache_dir,
        ttl_seconds=300,
    )
    try:
        data = await fetcher.discover(league=league, sportsbook=sportsbook)
        return {"league": league, "sportsbook": sportsbook, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/api/oddsblaze/probe")
async def oddsblaze_probe():
    """
    Verify OddsBlaze API key and probe available futures markets.
    Hits the sportsbooks endpoint first to confirm the key is valid.
    """
    import asyncio
    import httpx
    from app.config import settings

    key = settings.oddsblaze_api_key
    if not key:
        raise HTTPException(status_code=400, detail="ODDSBLAZE_API_KEY not set")

    results = {}

    async def get(url):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url)
            if r.status_code == 200:
                body = r.json()
                if isinstance(body, list):
                    return f"HTTP 200 — {len(body)} items"
                futures = body.get("futures", [])
                return f"HTTP 200 — {len(futures)} futures"
            return f"HTTP {r.status_code}: {r.text[:150]}"
        except Exception as exc:
            return f"ERROR: {exc}"

    # Step 1: verify key is valid via sportsbooks endpoint
    results["sportsbooks_endpoint"] = await get(
        f"https://sportsbooks.oddsblaze.com/?key={key}"
    )

    # Step 2: probe futures with confirmed sportsbook IDs from their docs
    futures_candidates = [
        ("draftkings", "mlb"),
        ("draftkings", "nba"),
        ("draftkings", "nhl"),
        ("draftkings", "nfl"),
        ("betmgm", "mlb"),
        ("betmgm", "nba"),
        ("caesars", "mlb"),
        ("betrivers", "nba"),
        ("fanatics", "mlb"),
    ]

    tasks = {
        f"{book}/{league}": get(
            f"https://futures.oddsblaze.com/?key={key}&sportsbook={book}&league={league}"
        )
        for book, league in futures_candidates
    }
    responses = await asyncio.gather(*tasks.values())
    for label, result in zip(tasks.keys(), responses):
        results[f"futures/{label}"] = result

    return results
