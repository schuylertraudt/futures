from datetime import datetime, timezone
from app.models import NormalizedOdds
from app.normalizers.odds_api import decimal_to_american
from app.maps.kalshi_market_map import KALSHI_MARKET_MAP


def normalize(raw_response: dict) -> list[NormalizedOdds]:
    """
    Convert a cached Kalshi wrapper dict into NormalizedOdds.
    Only markets present in KALSHI_MARKET_MAP are included.
    """
    fetched_at_str = raw_response.get("fetched_at", datetime.now(timezone.utc).isoformat())
    fetched_at = datetime.fromisoformat(fetched_at_str)
    markets: list[dict] = raw_response.get("data", [])

    results: list[NormalizedOdds] = []

    for market in markets:
        ticker = market.get("ticker", "")
        mapping = KALSHI_MARKET_MAP.get(ticker)
        if mapping is None:
            continue  # Not in our map — skip

        yes_bid = market.get("yes_bid", 0) or 0
        yes_ask = market.get("yes_ask", 0) or 0
        no_bid = market.get("no_bid", 0) or 0
        no_ask = market.get("no_ask", 0) or 0

        # Use midpoint (cents) as fair price
        yes_mid = (yes_bid + yes_ask) / 2
        no_mid = (no_bid + no_ask) / 2

        if yes_mid <= 0 or yes_mid >= 100:
            continue
        if no_mid <= 0 or no_mid >= 100:
            continue

        yes_decimal = 100.0 / yes_mid
        no_decimal = 100.0 / no_mid

        base = {
            "sport": mapping["sport"],
            "market": mapping["market"],
            "event": mapping["event"],
            "book": "kalshi",
            "fetched_at": fetched_at,
        }

        results.append(
            NormalizedOdds(
                **base,
                selection=mapping["yes_selection"],
                decimal_odds=yes_decimal,
                american_odds=decimal_to_american(yes_decimal),
            )
        )
        results.append(
            NormalizedOdds(
                **base,
                selection=mapping["no_selection"],
                decimal_odds=no_decimal,
                american_odds=decimal_to_american(no_decimal),
            )
        )

    return results
