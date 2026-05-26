import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from app.config import settings
from app.models import NormalizedOdds, EVResult, ScanResult
from app.fetchers.odds_api import OddsApiFetcher
from app.fetchers.kalshi import KalshiFetcher
from app.normalizers import odds_api as odds_normalizer
from app.normalizers import kalshi as kalshi_normalizer
from app.calculator import calculate_ev, calculate_ev_nway_vs_pinnacle
from app.maps.sports_config import SPORTS_CONFIG
from app.maps.kalshi_market_map import KALSHI_SERIES_TO_FETCH

# Module-level fetcher instances (reused across requests to share cache state)
_odds_fetcher = OddsApiFetcher(
    api_key=settings.odds_api_key,
    cache_dir=settings.cache_dir,
    ttl_seconds=settings.cache_ttl_seconds,
)
_kalshi_fetcher = KalshiFetcher(
    api_key=settings.kalshi_api_key,
    email=settings.kalshi_email,
    password=settings.kalshi_password,
    cache_dir=settings.cache_dir,
    ttl_seconds=settings.kalshi_cache_ttl_seconds,
)

# In-memory L2 cache for processed results
_result_cache: ScanResult | None = None
_result_cache_time: datetime | None = None
_L2_TTL_SECONDS = 60


async def _fetch_odds_api() -> list[NormalizedOdds]:
    all_odds: list[NormalizedOdds] = []
    bookmakers = ",".join(settings.books)

    for sport_cfg in SPORTS_CONFIG:
        cache_key = f"odds_api_{sport_cfg['sport']}_{sport_cfg['markets']}"
        try:
            raw = await _odds_fetcher.fetch(
                cache_key=cache_key,
                sport=sport_cfg["odds_api_key"],
                markets=sport_cfg["markets"],
                bookmakers=bookmakers,
            )
            all_odds.extend(odds_normalizer.normalize(raw))
        except Exception as exc:
            print(f"[OddsAPI] Failed to fetch {sport_cfg['sport']}: {exc}")

    return all_odds


async def _fetch_kalshi() -> list[NormalizedOdds]:
    all_odds: list[NormalizedOdds] = []

    for series in KALSHI_SERIES_TO_FETCH:
        cache_key = f"kalshi_{series.lower()}"
        try:
            raw = await _kalshi_fetcher.fetch(cache_key=cache_key, series_ticker=series)
            all_odds.extend(kalshi_normalizer.normalize(raw))
        except Exception as exc:
            print(f"[Kalshi] Failed to fetch {series}: {exc}")

    return all_odds


def _group_key(o: NormalizedOdds) -> tuple:
    return (o.sport, o.market, o.event, o.selection)


def _compute_ev(all_odds: list[NormalizedOdds]) -> list[EVResult]:
    """
    Group odds by (sport, market, event, selection) and compute EV for each line.

    For n-way outrights (e.g. Super Bowl winner), Pinnacle devig requires
    all selections within the same event to share a denominator, so we group
    at the event level first to gather all Pinnacle rows.
    """
    # Build event-level Pinnacle index for n-way outrights
    pinnacle_by_event: dict[tuple, list[NormalizedOdds]] = defaultdict(list)
    for o in all_odds:
        if o.book == "pinnacle" and o.market == "outrights":
            pinnacle_by_event[(o.sport, o.market, o.event)].append(o)

    # Group by (sport, market, event, selection) for per-line EV
    groups: dict[tuple, list[NormalizedOdds]] = defaultdict(list)
    for o in all_odds:
        groups[_group_key(o)].append(o)

    results: list[EVResult] = []
    for key, lines in groups.items():
        sport, market, event, selection = key
        for target in lines:
            ev_result = calculate_ev(target, lines)

            # For n-way outrights, override Method 1 with full-event Pinnacle devig
            if market == "outrights":
                event_pinnacle = pinnacle_by_event.get((sport, market, event), [])
                ev_pin, fair_pin = calculate_ev_nway_vs_pinnacle(target, event_pinnacle)
                ev_result = EVResult(
                    odds=ev_result.odds,
                    ev_vs_pinnacle=ev_pin,
                    ev_vs_best=ev_result.ev_vs_best,
                    fair_prob_pinnacle=fair_pin,
                    fair_prob_best=ev_result.fair_prob_best,
                    best_available_decimal=ev_result.best_available_decimal,
                )

            results.append(ev_result)

    return results


def _build_cache_ages() -> dict[str, int]:
    ages: dict[str, int] = {}
    for sport_cfg in SPORTS_CONFIG:
        key = f"odds_api_{sport_cfg['sport']}_{sport_cfg['markets']}"
        ages[f"odds_api_{sport_cfg['sport']}"] = _odds_fetcher.cache_age_seconds(key)
    for series in KALSHI_SERIES_TO_FETCH:
        key = f"kalshi_{series.lower()}"
        ages[f"kalshi_{series}"] = _kalshi_fetcher.cache_age_seconds(key)
    return ages


async def run_scan() -> ScanResult:
    global _result_cache, _result_cache_time

    now = datetime.now(timezone.utc)
    if (
        _result_cache is not None
        and _result_cache_time is not None
        and (now - _result_cache_time).total_seconds() < _L2_TTL_SECONDS
    ):
        return _result_cache

    odds_odds, kalshi_odds = await asyncio.gather(
        _fetch_odds_api(),
        _fetch_kalshi(),
    )

    all_odds = odds_odds + kalshi_odds
    ev_results = _compute_ev(all_odds)

    result = ScanResult(
        results=ev_results,
        scan_time=now,
        cache_ages=_build_cache_ages(),
        requests_remaining=_odds_fetcher.requests_remaining,
    )
    _result_cache = result
    _result_cache_time = now
    return result


def invalidate_caches() -> None:
    global _result_cache, _result_cache_time
    _result_cache = None
    _result_cache_time = None
    for sport_cfg in SPORTS_CONFIG:
        key = f"odds_api_{sport_cfg['sport']}_{sport_cfg['markets']}"
        _odds_fetcher.invalidate(key)
    for series in KALSHI_SERIES_TO_FETCH:
        key = f"kalshi_{series.lower()}"
        _kalshi_fetcher.invalidate(key)
