from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NormalizedOdds(BaseModel):
    sport: str
    market: str
    event: str
    selection: str
    book: str
    decimal_odds: float
    american_odds: int
    fetched_at: datetime


class EVResult(BaseModel):
    odds: NormalizedOdds
    ev_vs_pinnacle: Optional[float] = None
    ev_vs_best: Optional[float] = None
    fair_prob_pinnacle: Optional[float] = None
    fair_prob_best: Optional[float] = None
    best_available_decimal: Optional[float] = None


class ScanResult(BaseModel):
    results: list[EVResult]
    scan_time: datetime
    cache_ages: dict[str, int]
    requests_remaining: Optional[int] = None
