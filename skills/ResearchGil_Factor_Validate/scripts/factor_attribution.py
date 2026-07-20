"""Factor attribution and PCA-based diversification analysis.

The naive correlation gate kills strategies with high pairwise |corr|. That's
not enough: ten strategies can all be pairwise OK and yet all load on the
same first principal component. When that component flips (a momentum crash,
a vol regime change), the whole "diversified" book draws down together.

Source: adapted from zostaff/ai-quant-researcher (MIT License)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PCAResult:
    """Output of `pca_decompose`."""

    eigenvalues: np.ndarray              # sorted descending
    eigenvectors: np.ndarray             # columns = principal components
    explained_variance_ratio: np.ndarray
    top_loadings: pd.Series              # strategy -> loading on PC1

    def top_concentration(self) -> float:
        """% of total variance explained by the largest principal component."""
        return float(self.explained_variance_ratio[0]) if self.explained_variance_ratio.size else 0.0


def pca_decompose(returns_matrix: pd.DataFrame) -> PCAResult:
    """Eigendecompose the covariance of a (time × strategy) return matrix.

    Args:
        returns_matrix: DataFrame indexed by time, columns = strategy id.
            NaN rows are dropped.

    Returns:
        PCAResult sorted so that eigenvalues[0] is the largest.

    The "first principal component" is the linear combination of strategies
    that explains the most joint variance — the dominant common driver of
    the portfolio. A diversified book has this number well below 50%.
    """
    if returns_matrix.shape[1] < 2:
        raise ValueError("Need at least 2 strategies for PCA.")
    cleaned = returns_matrix.dropna()
    if len(cleaned) < 30:
        raise ValueError("Need at least 30 aligned observations.")

    cov = np.cov(cleaned.to_numpy().T, ddof=1)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    # eigh returns ascending; flip to descending
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    total = float(eigenvalues.sum())
    explained = eigenvalues / total if total > 0 else np.zeros_like(eigenvalues)

    top_loadings = pd.Series(
        eigenvectors[:, 0], index=returns_matrix.columns, name="pc1_loading"
    )
    return PCAResult(
        eigenvalues=eigenvalues,
        eigenvectors=eigenvectors,
        explained_variance_ratio=explained,
        top_loadings=top_loadings,
    )


def factor_concentration_score(
    new_returns: pd.Series,
    survivor_returns: list[pd.Series],
    *,
    min_observations: int = 60,
) -> float:
    """Fraction of `new_returns` variance projected onto the survivor set's PC1.

    Args:
        new_returns: candidate strategy returns.
        survivor_returns: list of accepted strategy returns.
        min_observations: minimum aligned bars; below this the score is 0.

    Returns:
        Score in [0, 1]. 0 = orthogonal to PC1; 1 = full overlap with PC1.

    Use as a gate: reject if score > 0.5 even when pairwise |corr| is below
    the regular threshold. Catches "stealthy" duplication.
    """
    if not survivor_returns:
        return 0.0

    matrix = pd.concat(survivor_returns, axis=1)
    matrix.columns = [s.name or f"s{i}" for i, s in enumerate(survivor_returns)]
    joined = pd.concat([new_returns.rename("__new"), matrix], axis=1, join="inner").dropna()
    if len(joined) < min_observations:
        return 0.0
    if joined.shape[1] < 3:
        # Need PC1 from at least 2 survivors AND the new candidate.
        return 0.0

    pc1 = pca_decompose(joined.drop(columns="__new")).eigenvectors[:, 0]
    survivor_matrix = joined.drop(columns="__new").to_numpy()
    pc1_series = survivor_matrix @ pc1

    new_arr = joined["__new"].to_numpy()
    if new_arr.std(ddof=1) == 0 or pc1_series.std(ddof=1) == 0:
        return 0.0
    correlation = float(np.corrcoef(new_arr, pc1_series)[0, 1])
    return float(correlation**2)  # R² interpretation: variance share along PC1
