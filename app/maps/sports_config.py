"""
Sports and markets to scan.

odds_api_key: The Odds API sport key (see https://api.the-odds-api.com/v4/sports)
markets: Comma-separated Odds API market keys to request per sport.
         Use "outrights" for futures (Super Bowl/championship/division winners).
         Use "totals" for season win totals (Over/Under X.5 wins per team).
         Win total events open ~July/August for NFL; earlier for NBA/MLB/NHL.
"""

SPORTS_CONFIG = [
    # --- Championship winner outrights ---
    {
        "sport": "nfl",
        "odds_api_key": "americanfootball_nfl_super_bowl_winner",
        "markets": "outrights",
        "description": "NFL - Super Bowl Winner",
    },
    {
        "sport": "nba",
        "odds_api_key": "basketball_nba_championship_winner",
        "markets": "outrights",
        "description": "NBA - Championship Winner",
    },
    {
        "sport": "mlb",
        "odds_api_key": "baseball_mlb_world_series_winner",
        "markets": "outrights",
        "description": "MLB - World Series Winner",
    },
    {
        "sport": "nhl",
        "odds_api_key": "icehockey_nhl_championship_winner",
        "markets": "outrights",
        "description": "NHL - Stanley Cup Winner",
    },
    {
        "sport": "ncaaf",
        "odds_api_key": "americanfootball_ncaaf_championship_winner",
        "markets": "outrights",
        "description": "NCAAF - Championship Winner",
    },
    {
        "sport": "golf",
        "odds_api_key": "golf_us_open_winner",
        "markets": "outrights",
        "description": "Golf - US Open Winner",
    },
    {
        "sport": "golf",
        "odds_api_key": "golf_the_open_championship_winner",
        "markets": "outrights",
        "description": "Golf - The Open Championship Winner",
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
