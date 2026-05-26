"""
Static mapping from Kalshi market tickers to normalized fields.

IMPORTANT: Kalshi ticker formats change each season. Before using, run:
  GET /api/kalshi/discover?query=nfl
to list available series tickers, then update this file accordingly.

Each entry maps a single Kalshi binary market to:
- sport, market: to join with Odds API data
- event: team/player name (must match Odds API event name exactly)
- yes_selection: what a YES outcome represents in sportsbook terms
- no_selection: the complement

For NFL win totals, Kalshi typically offers multiple thresholds per team.
Map the threshold closest to the consensus sportsbook line.
"""

# Keyed by Kalshi market ticker
# Format (verify against /api/kalshi/discover): series_ticker + "-" + threshold
# e.g., if Kalshi series is "NFLWINS-KC", individual markets are "NFLWINS-KC-10"

KALSHI_MARKET_MAP: dict[str, dict] = {
    # ── AFC East ──────────────────────────────────────────────────────────────
    "NFLWINS-BUF-10": {
        "sport": "nfl", "market": "win_totals",
        "event": "Buffalo Bills",
        "yes_selection": "Over 9.5", "no_selection": "Under 9.5",
    },
    "NFLWINS-MIA-9": {
        "sport": "nfl", "market": "win_totals",
        "event": "Miami Dolphins",
        "yes_selection": "Over 8.5", "no_selection": "Under 8.5",
    },
    "NFLWINS-NE-5": {
        "sport": "nfl", "market": "win_totals",
        "event": "New England Patriots",
        "yes_selection": "Over 4.5", "no_selection": "Under 4.5",
    },
    "NFLWINS-NYJ-7": {
        "sport": "nfl", "market": "win_totals",
        "event": "New York Jets",
        "yes_selection": "Over 6.5", "no_selection": "Under 6.5",
    },
    # ── AFC North ─────────────────────────────────────────────────────────────
    "NFLWINS-BAL-11": {
        "sport": "nfl", "market": "win_totals",
        "event": "Baltimore Ravens",
        "yes_selection": "Over 10.5", "no_selection": "Under 10.5",
    },
    "NFLWINS-CIN-9": {
        "sport": "nfl", "market": "win_totals",
        "event": "Cincinnati Bengals",
        "yes_selection": "Over 8.5", "no_selection": "Under 8.5",
    },
    "NFLWINS-PIT-8": {
        "sport": "nfl", "market": "win_totals",
        "event": "Pittsburgh Steelers",
        "yes_selection": "Over 7.5", "no_selection": "Under 7.5",
    },
    "NFLWINS-CLE-7": {
        "sport": "nfl", "market": "win_totals",
        "event": "Cleveland Browns",
        "yes_selection": "Over 6.5", "no_selection": "Under 6.5",
    },
    # ── AFC South ─────────────────────────────────────────────────────────────
    "NFLWINS-HOU-10": {
        "sport": "nfl", "market": "win_totals",
        "event": "Houston Texans",
        "yes_selection": "Over 9.5", "no_selection": "Under 9.5",
    },
    "NFLWINS-IND-8": {
        "sport": "nfl", "market": "win_totals",
        "event": "Indianapolis Colts",
        "yes_selection": "Over 7.5", "no_selection": "Under 7.5",
    },
    "NFLWINS-JAX-8": {
        "sport": "nfl", "market": "win_totals",
        "event": "Jacksonville Jaguars",
        "yes_selection": "Over 7.5", "no_selection": "Under 7.5",
    },
    "NFLWINS-TEN-6": {
        "sport": "nfl", "market": "win_totals",
        "event": "Tennessee Titans",
        "yes_selection": "Over 5.5", "no_selection": "Under 5.5",
    },
    # ── AFC West ──────────────────────────────────────────────────────────────
    "NFLWINS-KC-12": {
        "sport": "nfl", "market": "win_totals",
        "event": "Kansas City Chiefs",
        "yes_selection": "Over 11.5", "no_selection": "Under 11.5",
    },
    "NFLWINS-LV-6": {
        "sport": "nfl", "market": "win_totals",
        "event": "Las Vegas Raiders",
        "yes_selection": "Over 5.5", "no_selection": "Under 5.5",
    },
    "NFLWINS-LAC-9": {
        "sport": "nfl", "market": "win_totals",
        "event": "Los Angeles Chargers",
        "yes_selection": "Over 8.5", "no_selection": "Under 8.5",
    },
    "NFLWINS-DEN-7": {
        "sport": "nfl", "market": "win_totals",
        "event": "Denver Broncos",
        "yes_selection": "Over 6.5", "no_selection": "Under 6.5",
    },
    # ── NFC East ──────────────────────────────────────────────────────────────
    "NFLWINS-PHI-11": {
        "sport": "nfl", "market": "win_totals",
        "event": "Philadelphia Eagles",
        "yes_selection": "Over 10.5", "no_selection": "Under 10.5",
    },
    "NFLWINS-DAL-9": {
        "sport": "nfl", "market": "win_totals",
        "event": "Dallas Cowboys",
        "yes_selection": "Over 8.5", "no_selection": "Under 8.5",
    },
    "NFLWINS-NYG-6": {
        "sport": "nfl", "market": "win_totals",
        "event": "New York Giants",
        "yes_selection": "Over 5.5", "no_selection": "Under 5.5",
    },
    "NFLWINS-WAS-9": {
        "sport": "nfl", "market": "win_totals",
        "event": "Washington Commanders",
        "yes_selection": "Over 8.5", "no_selection": "Under 8.5",
    },
    # ── NFC North ─────────────────────────────────────────────────────────────
    "NFLWINS-DET-11": {
        "sport": "nfl", "market": "win_totals",
        "event": "Detroit Lions",
        "yes_selection": "Over 10.5", "no_selection": "Under 10.5",
    },
    "NFLWINS-MIN-10": {
        "sport": "nfl", "market": "win_totals",
        "event": "Minnesota Vikings",
        "yes_selection": "Over 9.5", "no_selection": "Under 9.5",
    },
    "NFLWINS-GB-10": {
        "sport": "nfl", "market": "win_totals",
        "event": "Green Bay Packers",
        "yes_selection": "Over 9.5", "no_selection": "Under 9.5",
    },
    "NFLWINS-CHI-7": {
        "sport": "nfl", "market": "win_totals",
        "event": "Chicago Bears",
        "yes_selection": "Over 6.5", "no_selection": "Under 6.5",
    },
    # ── NFC South ─────────────────────────────────────────────────────────────
    "NFLWINS-TB-9": {
        "sport": "nfl", "market": "win_totals",
        "event": "Tampa Bay Buccaneers",
        "yes_selection": "Over 8.5", "no_selection": "Under 8.5",
    },
    "NFLWINS-ATL-9": {
        "sport": "nfl", "market": "win_totals",
        "event": "Atlanta Falcons",
        "yes_selection": "Over 8.5", "no_selection": "Under 8.5",
    },
    "NFLWINS-CAR-5": {
        "sport": "nfl", "market": "win_totals",
        "event": "Carolina Panthers",
        "yes_selection": "Over 4.5", "no_selection": "Under 4.5",
    },
    "NFLWINS-NO-7": {
        "sport": "nfl", "market": "win_totals",
        "event": "New Orleans Saints",
        "yes_selection": "Over 6.5", "no_selection": "Under 6.5",
    },
    # ── NFC West ──────────────────────────────────────────────────────────────
    "NFLWINS-SF-10": {
        "sport": "nfl", "market": "win_totals",
        "event": "San Francisco 49ers",
        "yes_selection": "Over 9.5", "no_selection": "Under 9.5",
    },
    "NFLWINS-SEA-8": {
        "sport": "nfl", "market": "win_totals",
        "event": "Seattle Seahawks",
        "yes_selection": "Over 7.5", "no_selection": "Under 7.5",
    },
    "NFLWINS-LAR-9": {
        "sport": "nfl", "market": "win_totals",
        "event": "Los Angeles Rams",
        "yes_selection": "Over 8.5", "no_selection": "Under 8.5",
    },
    "NFLWINS-ARI-8": {
        "sport": "nfl", "market": "win_totals",
        "event": "Arizona Cardinals",
        "yes_selection": "Over 7.5", "no_selection": "Under 7.5",
    },
}

# Kalshi series tickers to fetch (and search for in discovery)
KALSHI_SERIES_TO_FETCH = ["NFLWINS"]
