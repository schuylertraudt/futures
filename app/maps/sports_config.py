"""
Sports and markets to scan.

odds_api_key: The Odds API sport key (see https://api.the-odds-api.com/v4/sports)
markets: Comma-separated Odds API market keys to request per sport.
         Use "outrights" for futures (Super Bowl/championship/division winners).
         Win totals may appear as a separate event — run /api/discover to inspect
         what's available once you have a key.
"""

SPORTS_CONFIG = [
    {
        "sport": "nfl",
        "odds_api_key": "americanfootball_nfl",
        "markets": "outrights",
        "description": "NFL Futures",
    },
    {
        "sport": "nba",
        "odds_api_key": "basketball_nba",
        "markets": "outrights",
        "description": "NBA Futures",
    },
    {
        "sport": "mlb",
        "odds_api_key": "baseball_mlb",
        "markets": "outrights",
        "description": "MLB Futures",
    },
    {
        "sport": "nhl",
        "odds_api_key": "icehockey_nhl",
        "markets": "outrights",
        "description": "NHL Futures",
    },
]

# Display name overrides for book slugs
BOOK_DISPLAY_NAMES = {
    "draftkings": "DraftKings",
    "fanduel": "FanDuel",
    "betmgm": "BetMGM",
    "caesars": "Caesars",
    "betrivers": "BetRivers",
    "fanatics": "Fanatics",
    "thescore_bet": "theScore Bet",
    "pinnacle": "Pinnacle",
    "kalshi": "Kalshi",
}
