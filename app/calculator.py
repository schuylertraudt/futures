from app.models import NormalizedOdds, EVResult


def multiplicative_devig(outcomes: list[tuple[str, float]]) -> dict[str, float]:
    """
    Removes bookmaker margin using the multiplicative method.
    fair_prob_i = implied_prob_i / sum(all implied_probs)
    where implied_prob = 1 / decimal_odds
    """
    implied = {sel: 1.0 / dec for sel, dec in outcomes if dec > 1.0}
    if not implied:
        return {}
    total = sum(implied.values())
    return {sel: p / total for sel, p in implied.items()}


def ev_percentage(fair_prob: float, decimal_odds: float) -> float:
    return (fair_prob * decimal_odds - 1) * 100


def _find_complement(selection: str, all_selections: set[str]) -> str | None:
    lower = selection.lower()
    if lower.startswith("over "):
        threshold = selection[5:]
        comp = f"Under {threshold}"
        return comp if comp in all_selections else None
    if lower.startswith("under "):
        threshold = selection[6:]
        comp = f"Over {threshold}"
        return comp if comp in all_selections else None
    # Two-way market (h2h)
    if len(all_selections) == 2:
        others = all_selections - {selection}
        return others.pop() if others else None
    return None


def calculate_ev(
    target: NormalizedOdds,
    market_odds: list[NormalizedOdds],
) -> EVResult:
    """
    Calculates both EV methods for a single target line given all lines
    for that (sport, market, event, selection) group.
    """
    all_selections = {o.selection for o in market_odds}

    # --- Method 1: vs Pinnacle ---
    ev_vs_pinnacle = None
    fair_prob_pinnacle = None

    pinnacle = [o for o in market_odds if o.book == "pinnacle"]
    if len(pinnacle) >= 2:
        pairs = [(o.selection, o.decimal_odds) for o in pinnacle]
        fair_probs = multiplicative_devig(pairs)
        fair_p = fair_probs.get(target.selection)
        if fair_p is not None:
            fair_prob_pinnacle = round(fair_p, 6)
            ev_vs_pinnacle = round(ev_percentage(fair_p, target.decimal_odds), 4)
    elif len(pinnacle) == 1 and len(all_selections) > 2:
        # n-way outright: Pinnacle has each team as a separate row; devig all Pinnacle rows
        # market_odds includes all selections — gather all Pinnacle rows from caller context
        pass  # handled via the full market group in scanner.py

    # --- Method 2: vs Next Best Line ---
    ev_vs_best = None
    fair_prob_best = None
    best_available_decimal = None

    complement = _find_complement(target.selection, all_selections)

    if complement is not None:
        # 2-outcome market: devig best available pair
        this_best = max(
            (o.decimal_odds for o in market_odds if o.selection == target.selection),
            default=None,
        )
        comp_best = max(
            (o.decimal_odds for o in market_odds if o.selection == complement),
            default=None,
        )
        if this_best is not None and comp_best is not None:
            pairs = [(target.selection, this_best), (complement, comp_best)]
            fair_probs = multiplicative_devig(pairs)
            fair_p = fair_probs.get(target.selection)
            if fair_p is not None:
                best_available_decimal = this_best
                fair_prob_best = round(fair_p, 6)
                ev_vs_best = round(ev_percentage(fair_p, target.decimal_odds), 4)
    elif len(all_selections) > 2:
        # n-way outright: best available for this selection vs Pinnacle devig of all
        # (Method 2 not meaningful without Pinnacle; skip)
        pass

    return EVResult(
        odds=target,
        ev_vs_pinnacle=ev_vs_pinnacle,
        ev_vs_best=ev_vs_best,
        fair_prob_pinnacle=fair_prob_pinnacle,
        fair_prob_best=fair_prob_best,
        best_available_decimal=best_available_decimal,
    )


def calculate_ev_nway_vs_best(
    target: NormalizedOdds,
    all_event_odds: list[NormalizedOdds],
) -> tuple[float | None, float | None, float | None]:
    """
    For n-way outrights: devig using the best (highest) available price for each
    selection across all books, then compute EV for the target line.
    Returns (ev_vs_best, fair_prob_best, best_available_decimal_for_target).
    """
    if not all_event_odds:
        return None, None, None

    best_by_selection: dict[str, float] = {}
    for o in all_event_odds:
        if o.decimal_odds > best_by_selection.get(o.selection, 0.0):
            best_by_selection[o.selection] = o.decimal_odds

    if len(best_by_selection) < 2:
        return None, None, None

    fair_probs = multiplicative_devig(list(best_by_selection.items()))
    fair_p = fair_probs.get(target.selection)
    if fair_p is None:
        return None, None, None

    best_for_target = best_by_selection.get(target.selection)
    return (
        round(ev_percentage(fair_p, target.decimal_odds), 4),
        round(fair_p, 6),
        best_for_target,
    )


def calculate_ev_nway_vs_pinnacle(
    target: NormalizedOdds,
    all_pinnacle_outcomes: list[NormalizedOdds],
) -> tuple[float | None, float | None]:
    """
    For n-way outrights (championship futures): devig all Pinnacle outcomes
    across the whole market event, then compute EV for the target line.
    Returns (ev_vs_pinnacle, fair_prob_pinnacle).
    """
    if len(all_pinnacle_outcomes) < 2:
        return None, None
    pairs = [(o.selection, o.decimal_odds) for o in all_pinnacle_outcomes]
    fair_probs = multiplicative_devig(pairs)
    fair_p = fair_probs.get(target.selection)
    if fair_p is None:
        return None, None
    return round(ev_percentage(fair_p, target.decimal_odds), 4), round(fair_p, 6)
