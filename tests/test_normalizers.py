import json
import pytest
from pathlib import Path
from app.normalizers import odds_api as odds_norm
from app.normalizers import kalshi as kalshi_norm

FIXTURES = Path(__file__).parent / "fixtures"


class TestOddsApiNormalizer:
    def setup_method(self):
        self.raw = json.loads((FIXTURES / "odds_api_sample.json").read_text())

    def test_returns_list(self):
        result = odds_norm.normalize(self.raw)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_all_fields_present(self):
        result = odds_norm.normalize(self.raw)
        for r in result:
            assert r.sport
            assert r.market
            assert r.event
            assert r.selection
            assert r.book
            assert r.decimal_odds > 1.0
            assert r.fetched_at

    def test_sport_mapped(self):
        result = odds_norm.normalize(self.raw)
        assert all(r.sport == "nfl" for r in result)

    def test_pinnacle_present(self):
        result = odds_norm.normalize(self.raw)
        books = {r.book for r in result}
        assert "pinnacle" in books

    def test_american_odds_conversion(self):
        result = odds_norm.normalize(self.raw)
        for r in result:
            # +500 at decimal 6.0 => american +500
            if abs(r.decimal_odds - 6.5) < 0.01:
                assert r.american_odds == 550

    def test_outright_selection_is_team_name(self):
        result = odds_norm.normalize(self.raw)
        outrights = [r for r in result if r.market == "outrights"]
        assert all("Over" not in r.selection and "Under" not in r.selection for r in outrights)


class TestKalshiNormalizer:
    def setup_method(self):
        self.raw = json.loads((FIXTURES / "kalshi_sample.json").read_text())

    def test_returns_list(self):
        result = kalshi_norm.normalize(self.raw)
        assert isinstance(result, list)

    def test_unknown_tickers_skipped(self):
        result = kalshi_norm.normalize(self.raw)
        tickers_in_results = {r.odds.book for r in [type('', (), {'odds': r})() for r in result]}
        # NFLWINS-UNKNOWN-99 should not produce output
        events = {r.event for r in result}
        assert not any("Unknown" in e for e in events)

    def test_known_ticker_produces_two_rows(self):
        result = kalshi_norm.normalize(self.raw)
        kc = [r for r in result if r.event == "Kansas City Chiefs"]
        assert len(kc) == 2
        selections = {r.selection for r in kc}
        assert "Over 11.5" in selections
        assert "Under 11.5" in selections

    def test_book_is_kalshi(self):
        result = kalshi_norm.normalize(self.raw)
        assert all(r.book == "kalshi" for r in result)

    def test_decimal_odds_from_midpoint(self):
        result = kalshi_norm.normalize(self.raw)
        kc_over = next(r for r in result if r.event == "Kansas City Chiefs" and r.selection == "Over 11.5")
        # yes_mid = (42+46)/2 = 44; decimal = 100/44
        expected = 100 / 44
        assert abs(kc_over.decimal_odds - expected) < 0.001
