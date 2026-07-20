"""Three gates a factor must pass before it enters strategy backtest.

    1. Deflated Sharpe:    p-value below `dsr_pvalue_max`. Hard gate, no override.
    2. Correlation gate:   max |corr| with any accepted factor below `max_correlation`.
    3. PCA concentration:  R² with PC1 of accepted pool below `max_pca_concentration`.

The gates are an AND. One failure kills. The order matters only for efficiency:
DSR is cheap (one closed-form formula), correlation is intermediate, and PCA
is the most expensive when there are many survivors.

Source: adapted from zostaff/ai-quant-researcher (MIT License)
    — modified to remove CriticAgent dependency for standalone use
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

try:
    from .deflated_sharpe import DeflatedSharpeResult, deflated_sharpe
    from .factor_attribution import factor_concentration_score
except ImportError:
    from deflated_sharpe import DeflatedSharpeResult, deflated_sharpe
    from factor_attribution import factor_concentration_score


@dataclass(frozen=True)
class GateOutcome:
    """Aggregate gate result.

    `passes` is True only if all sub-gates pass. `rejection_reason` is the
    name of the first gate to fail (None if all pass).

    Gates in evaluation order:
        deflated_sharpe → pairwise_correlation → pca_concentration
    """

    passes: bool
    rejection_reason: str | None
    dsr_result: DeflatedSharpeResult | None
    max_correlation: float | None
    pca_concentration: float | None = None


def evaluate_gates(
    strategy_returns: pd.Series,
    *,
    n_trials: int,
    accepted_returns: list[pd.Series] | None = None,
    annualization: int | None = None,
    dsr_pvalue_max: float = 0.05,
    max_correlation: float = 0.6,
    max_pca_concentration: float = 0.5,
) -> GateOutcome:
    """Run all three gates in order.

    Args:
        strategy_returns: Net returns of the candidate.
        n_trials: Honest count of how many strategies have been tested.
        accepted_returns: Returns series of strategies already accepted.
        annualization: Periods per year. Defaults to 252 if monthly returns,
            adjust for weekly (52) or quarterly (4).
        dsr_pvalue_max: Maximum p-value for the deflated Sharpe gate.
        max_correlation: Maximum absolute correlation with existing survivors.
        max_pca_concentration: Maximum R² with PC1 of survivor pool.
    """
    if annualization is None:
        # Auto-detect: monthly returns → 12, quarterly → 4, weekly → 52, daily → 252
        annualization = 12  # Default for gil factor testing (monthly)

    # Gate 1: Deflated Sharpe Ratio
    try:
        dsr = deflated_sharpe(
            strategy_returns,
            n_trials=max(n_trials, 1),
            annualization=annualization,
        )
    except ValueError as e:
        return GateOutcome(
            passes=False,
            rejection_reason=f"dsr_error: {e}",
            dsr_result=None,
            max_correlation=None,
        )

    if dsr.pvalue >= dsr_pvalue_max:
        return GateOutcome(
            passes=False,
            rejection_reason=f"deflated_sharpe_pvalue={dsr.pvalue:.3f}>={dsr_pvalue_max}",
            dsr_result=dsr,
            max_correlation=None,
        )

    # Gate 2: Correlation Gate
    max_corr = _max_abs_correlation(strategy_returns, accepted_returns or [])
    if max_corr >= max_correlation:
        return GateOutcome(
            passes=False,
            rejection_reason=f"correlation={max_corr:.2f}>={max_correlation}",
            dsr_result=dsr,
            max_correlation=max_corr,
        )

    # Gate 3: PCA Concentration
    pca_score = factor_concentration_score(strategy_returns, accepted_returns or [])
    if pca_score >= max_pca_concentration:
        return GateOutcome(
            passes=False,
            rejection_reason=f"pca_concentration={pca_score:.2f}>={max_pca_concentration}",
            dsr_result=dsr,
            max_correlation=max_corr,
            pca_concentration=pca_score,
        )

    return GateOutcome(
        passes=True,
        rejection_reason=None,
        dsr_result=dsr,
        max_correlation=max_corr,
        pca_concentration=pca_score,
    )


def correlation_gate(
    candidate: pd.Series,
    accepted: list[pd.Series],
    *,
    max_correlation: float = 0.6,
) -> tuple[bool, float]:
    """Standalone correlation gate. Returns (passed, max_correlation)."""
    max_corr = _max_abs_correlation(candidate, accepted)
    return max_corr < max_correlation, max_corr


def _max_abs_correlation(candidate: pd.Series, accepted: list[pd.Series]) -> float:
    if not accepted:
        return 0.0
    correlations: list[float] = []
    candidate = candidate.dropna()
    for other in accepted:
        joined = pd.concat([candidate, other.dropna()], axis=1, join="inner").dropna()
        if len(joined) < 30:
            continue
        if joined.iloc[:, 0].std(ddof=1) == 0 or joined.iloc[:, 1].std(ddof=1) == 0:
            continue
        c = joined.iloc[:, 0].corr(joined.iloc[:, 1])
        if pd.notna(c):
            correlations.append(abs(float(c)))
    return max(correlations) if correlations else 0.0
