import pytest
from app.calculator import multiplicative_devig, ev_percentage, calculate_ev, _find_complement
from app.models import NormalizedOdds
from datetime import datetime, timezone


def make_odds(book, selection, decimal_odds, sport="nfl", market="win_totals", event="Team A"):
    return NormalizedOdds(
        sport=sport,
        market=market,
        event=event,
        selection=selection,
        book=book,
        decimal_odds=decimal_odds,
        american_odds=int((decimal_odds - 1) * 100) if decimal_odds >= 2 else int(-100 / (decimal_odds - 1)),
        fetched_at=datetime.now(timezone.utc),
    )


class TestMultiplicativeDevig:
    def test_even_money(self):
        # -110/-110 two-way market: each has 10/21 implied prob
        outcomes = [("Over", 1.909), ("Under", 1.909)]
        result = multiplicative_devig(outcomes)
        assert abs(result["Over"] - 0.5) < 0.001
        assert abs(result["Under"] - 0.5) < 0.001
        assert abs(sum(result.values()) - 1.0) < 1e-9

    def test_asymmetric_market(self):
        # -200/+170: 2/3 implied for fav, 10/27 for dog
        outcomes = [("Team A", 1.5), ("Team B", 2.70)]
        result = multiplicative_devig(outcomes)
        assert sum(result.values()) == pytest.approx(1.0, abs=1e-9)
        assert result["Team A"] > result["Team B"]

    def test_nway_market(self):
        # Three-way: fair probs sum to 1
        outcomes = [("A", 3.0), ("B", 3.5), ("C", 4.5)]
        result = multiplicative_devig(outcomes)
        assert sum(result.values()) == pytest.approx(1.0, abs=1e-9)
        assert result["A"] > result["B"] > result["C"]


class TestEvPercentage:
    def test_zero_ev(self):
        # If fair prob = 1/decimal_odds, EV = 0
        fair_prob = 1 / 1.909
        assert ev_percentage(fair_prob, 1.909) == pytest.approx(0.0, abs=0.01)

    def test_positive_ev(self):
        # Fair prob 50% but book offers +110 (2.10) => positive EV
        assert ev_percentage(0.5, 2.10) == pytest.approx(5.0, abs=0.01)

    def test_negative_ev(self):
        # Fair prob 50% but book offers -110 (1.909) => negative EV
        assert ev_percentage(0.5, 1.909) == pytest.approx(-4.55, abs=0.01)


class TestFindComplement:
    def test_over_finds_under(self):
        selections = {"Over 10.5", "Under 10.5"}
        assert _find_complement("Over 10.5", selections) == "Under 10.5"

    def test_under_finds_over(self):
        selections = {"Over 7.5", "Under 7.5"}
        assert _find_complement("Under 7.5", selections) == "Over 7.5"

    def test_two_way_h2h(self):
        selections = {"Team A", "Team B"}
        result = _find_complement("Team A", selections)
        assert result == "Team B"

    def test_nway_returns_none(self):
        selections = {"Team A", "Team B", "Team C"}
        assert _find_complement("Team A", selections) is None


class TestCalculateEV:
    def _market(self):
        # Pinnacle at 2.00/2.00 = vig-free, fair prob exactly 0.5 each side.
        # DK Over at 2.10 => EV = 0.5 * 2.10 - 1 = +5%.
        return [
            make_odds("pinnacle", "Over 10.5", 2.00),
            make_odds("pinnacle", "Under 10.5", 2.00),
            make_odds("draftkings", "Over 10.5", 2.10),
            make_odds("draftkings", "Under 10.5", 1.87),
            make_odds("fanduel", "Over 10.5", 1.95),
            make_odds("fanduel", "Under 10.5", 1.95),
        ]

    def test_pinnacle_ev_computed(self):
        market = self._market()
        target = next(o for o in market if o.book == "draftkings" and o.selection == "Over 10.5")
        result = calculate_ev(target, market)
        assert result.ev_vs_pinnacle is not None
        assert result.fair_prob_pinnacle is not None
        # Pinnacle vig-free 50/50; DK Over at 2.10 => +5% EV
        assert result.ev_vs_pinnacle == pytest.approx(5.0, abs=0.01)

    def test_no_pinnacle_gives_null(self):
        market = [
            make_odds("draftkings", "Over 10.5", 2.00),
            make_odds("draftkings", "Under 10.5", 1.87),
            make_odds("fanduel", "Over 10.5", 1.95),
            make_odds("fanduel", "Under 10.5", 1.95),
        ]
        target = market[0]
        result = calculate_ev(target, market)
        assert result.ev_vs_pinnacle is None
        assert result.ev_vs_best is not None  # best-line still works

    def test_best_ev_uses_best_odds(self):
        market = self._market()
        # Best Over = 2.10 (DK), best Under = 2.00 (Pinnacle)
        target = next(o for o in market if o.book == "fanduel" and o.selection == "Over 10.5")
        result = calculate_ev(target, market)
        assert result.ev_vs_best is not None
        assert result.best_available_decimal == pytest.approx(2.10, abs=0.001)

    def test_ev_vs_best_negative_for_worst_line(self):
        market = self._market()
        # Best Over = 2.10 (DK); best Under = 2.00 (Pinnacle).
        # Fair Under = devig(Over=2.10, Under=2.00): implied over=0.4762, under=0.5, sum=0.9762
        # fair_under = 0.5/0.9762 = 0.5122
        # FanDuel Under = 1.95 => EV = 0.5122 * 1.95 - 1 = -0.013% (slightly negative)
        target = next(o for o in market if o.book == "fanduel" and o.selection == "Under 10.5")
        result = calculate_ev(target, market)
        assert result.ev_vs_best is not None
        assert result.ev_vs_best < 0  # FanDuel Under is not the best available Under
