from datetime import datetime, timezone
from app.models import NormalizedOdds


def decimal_to_american(decimal_odds: float) -> int:
    if decimal_odds >= 2.0:
        return round((decimal_odds - 1) * 100)
    else:
        return round(-100 / (decimal_odds - 1))


_SPORT_MAP = {
    "americanfootball_nfl": "nfl",
    "basketball_nba": "nba",
    "baseball_mlb": "mlb",
    "icehockey_nhl": "nhl",
}

_MARKET_MAP = {
    "outrights": "outrights",
    "h2h": "h2h",
    "spreads": "spreads",
    "totals": "totals",
    "alternate_totals": "alternate_totals",
}


def normalize(raw_response: dict) -> list[NormalizedOdds]:
    """
    Convert a cached Odds API wrapper dict (with "fetched_at" + "data" keys)
    into a flat list of NormalizedOdds, one per (bookmaker, outcome) pair.
    """
    fetched_at_str = raw_response.get("fetched_at", datetime.now(timezone.utc).isoformat())
    fetched_at = datetime.fromisoformat(fetched_at_str)
    events: list[dict] = raw_response.get("data", [])

    results: list[NormalizedOdds] = []

    for event in events:
        sport_key = event.get("sport_key", "")
        sport = _SPORT_MAP.get(sport_key, sport_key)

        # For outrights the event name is typically "sport_title" or a synthetic name;
        # for game markets it's home_team vs away_team.
        event_name = (
            event.get("name")
            or event.get("home_team")
            or event.get("sport_title", "Unknown")
        ).strip()

        for bookmaker in event.get("bookmakers", []):
            book = bookmaker["key"]
            for market in bookmaker.get("markets", []):
                market_key = _MARKET_MAP.get(market["key"], market["key"])
                for outcome in market.get("outcomes", []):
                    name = outcome["name"].strip()
                    point = outcome.get("point")
                    if point is not None:
                        # Win total / game total: "Over 10.5" / "Under 10.5"
                        selection = f"{name.title()} {point}"
                    else:
                        # Outright winner: team/player name
                        selection = name.title()

                    decimal_odds = float(outcome["price"])
                    if decimal_odds <= 1.0:
                        continue  # invalid odds

                    results.append(
                        NormalizedOdds(
                            sport=sport,
                            market=market_key,
                            event=event_name.title(),
                            selection=selection,
                            book=book,
                            decimal_odds=decimal_odds,
                            american_odds=decimal_to_american(decimal_odds),
                            fetched_at=fetched_at,
                        )
                    )

    return results
