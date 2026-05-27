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


@router.get("/api/oddsblaze/active-futures")
async def oddsblaze_active_futures():
    """
    Return what futures markets OddsBlaze currently has active, and which sportsbooks
    have lines for each. Use this to discover valid league IDs, market IDs, and book names.
    """
    import httpx
    from app.config import settings

    key = settings.oddsblaze_api_key
    if not key:
        raise HTTPException(status_code=400, detail="ODDSBLAZE_API_KEY not set")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                "https://active.futures.markets.oddsblaze.com/",
                params={"key": key},
            )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text[:300])
        return r.json()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/api/oddsblaze/probe")
async def oddsblaze_probe():
    """
    Verify OddsBlaze API key and probe available futures markets.
    Hits the sportsbooks endpoint first to confirm the key is valid,
    then fetches the active-futures manifest to see what's really available.
    """
    import asyncio
    import httpx
    from app.config import settings

    key = settings.oddsblaze_api_key
    if not key:
        raise HTTPException(status_code=400, detail="ODDSBLAZE_API_KEY not set")

    results = {}

    async def get_raw(url, params=None):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url, params=params)
            return r.status_code, r.text
        except Exception as exc:
            return None, str(exc)

    # Step 1: sanity check — leagues endpoint requires no auth
    status, text = await get_raw("https://api.oddsblaze.com/v2/leagues.json")
    if status == 200:
        try:
            leagues = __import__("json").loads(text)
            results["discovery/leagues_no_auth"] = f"HTTP 200 — {len(leagues)} leagues"
        except Exception:
            results["discovery/leagues_no_auth"] = f"HTTP 200 — (parse error)"
    else:
        results["discovery/leagues_no_auth"] = f"HTTP {status}: {text[:150]}"

    # Step 2: sportsbooks endpoint — requires key, confirms key is valid
    status, text = await get_raw("https://sportsbooks.oddsblaze.com/", {"key": key})
    if status == 200:
        try:
            books = __import__("json").loads(text)
            book_names = [b.get("name") or b.get("id") or str(b) for b in (books if isinstance(books, list) else books.get("sportsbooks", []))]
            results["discovery/sportsbooks"] = f"HTTP 200 — {len(book_names)} books: {book_names}"
        except Exception:
            results["discovery/sportsbooks"] = f"HTTP 200 — {text[:300]}"
    else:
        results["discovery/sportsbooks"] = f"HTTP {status}: {text[:150]}"

    # Step 3: active futures manifest — shows every live market + which books have lines
    status, text = await get_raw(
        "https://active.futures.markets.oddsblaze.com/", {"key": key}
    )
    if status == 200:
        try:
            body = __import__("json").loads(text)
            leagues = body.get("leagues", [])
            summary = {}
            for lg in leagues:
                markets = lg.get("markets", [])
                summary[lg["id"]] = {
                    "name": lg.get("name"),
                    "market_count": len(markets),
                    "markets": [
                        {
                            "id": m.get("id"),
                            "name": m.get("name"),
                            "sportsbooks": m.get("sportsbooks", []),
                        }
                        for m in markets
                    ],
                }
            results["active_futures"] = summary
        except Exception as exc:
            results["active_futures"] = f"HTTP 200 — parse error: {exc} — {text[:300]}"
    else:
        results["active_futures"] = f"HTTP {status}: {text[:150]}"

    # Step 4: spot-check one futures fetch per league from active manifest
    # (only if we successfully parsed it)
    if isinstance(results.get("active_futures"), dict):
        active = results["active_futures"]
        spot_checks = []
        for league_id, info in active.items():
            for market in info.get("markets", []):
                books_for_market = market.get("sportsbooks", [])
                if books_for_market:
                    # Use first listed book for the spot check
                    spot_checks.append((league_id, books_for_market[0].lower().replace(" ", "")))
                    break  # one per league is enough

        async def fetch_futures(league, book_slug):
            s, t = await get_raw(
                "https://futures.oddsblaze.com/",
                {"key": key, "league": league, "sportsbook": book_slug},
            )
            if s == 200:
                try:
                    body = __import__("json").loads(t)
                    futures = body.get("futures", [])
                    return f"HTTP 200 — {len(futures)} futures"
                except Exception:
                    return f"HTTP 200 — parse error"
            return f"HTTP {s}: {t[:100]}"

        tasks = {f"{league}/{book}": fetch_futures(league, book) for league, book in spot_checks}
        responses = await asyncio.gather(*tasks.values())
        for label, res in zip(tasks.keys(), responses):
            results[f"spot_check/{label}"] = res

    return results
