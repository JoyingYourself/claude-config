"""
Factor combination engine for ResearchGil_Factor_Combine.

Methods:
  - equal_weight: rank each factor, then equal-weight sum
  - ic_weighted: weight by historical IC IR
  - score_weighted: weight by IC IR × (1 - max |pairwise corr|), penalizing redundancy
  - pca_first_pc: PCA first principal component as weight

All methods output a composite factor JSON compatible with save_factor format,
ready for Strategy_Backtest consumption.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Import TrialsDB from sister skill
_TRIALS_PATH = os.path.expanduser("~/.claude/skills/ResearchGil_Factor_Validate/scripts")
if _TRIALS_PATH not in sys.path:
    sys.path.insert(0, _TRIALS_PATH)
from trials_db import TrialsDB

FACTOR_DIR = os.path.expanduser("~/.gil_factors")
DATASET_DIR = os.path.expanduser("~/.gil_datasets")


@dataclass
class FactorInfo:
    """Loaded factor metadata."""
    name: str
    expression: str
    label: str = ""
    dataset_path: str = ""
    ic_mean: float = 0.0
    ic_ir: float = 0.0
    ic_series: list[float] = field(default_factory=list)
    sharpe: float = 0.0
    raw_returns: list[float] = field(default_factory=list)


def load_accepted_factors() -> list[FactorInfo]:
    """Load all accepted factors from trials.db, enriched with factor JSON details."""
    db = TrialsDB()
    accepted = db.accepted_factors()
    db.close()

    factors = []
    for a in accepted:
        name = a["factor_name"]
        info = FactorInfo(
            name=name,
            expression=a["expression"],
            ic_mean=a.get("ic_mean", 0.0),
            ic_ir=a.get("ic_ir", 0.0),
            sharpe=a.get("sharpe", 0.0),
        )

        # Enrich from factor JSON
        factor_path = os.path.join(FACTOR_DIR, f"{name}.json")
        if os.path.exists(factor_path):
            with open(factor_path, 'r', encoding='utf-8') as f:
                fj = json.load(f)
            info.label = fj.get("label", name)
            info.dataset_path = fj.get("dataset_path", "")
            stats = fj.get("stats", {})
            info.ic_mean = stats.get("ic_mean", info.ic_mean)
            info.ic_ir = stats.get("ic_ir", info.ic_ir)

        # Enrich with raw returns from test_results
        test_path = os.path.join(FACTOR_DIR, "test_results", f"{name}.json")
        if os.path.exists(test_path):
            with open(test_path, 'r', encoding='utf-8') as f:
                tr = json.load(f)
            raw = tr.get("raw_returns", {})
            info.raw_returns = raw.get("long_short", [])
            info.ic_series = tr.get("ic_stats", {}).get("series", [])

        factors.append(info)

    return factors


def validate_same_dataset(factors: list[FactorInfo]) -> str | None:
    """All factors must share the same Dataset. Returns None if OK, error message if not."""
    datasets = set(f.dataset_path for f in factors if f.dataset_path)
    if len(datasets) > 1:
        return f"因子使用不同 Dataset: {datasets}。所有子因子必须使用同一 Dataset 以保证日期对齐。"
    if len(datasets) == 0:
        return "无法确定因子 Dataset 路径。"
    return None


def combine_equal_weight(factors: list[FactorInfo]) -> tuple[str, dict[str, float], dict]:
    """
    Equal-weight rank combination.

    expression = (1/n) * rank(f1) + (1/n) * rank(f2) + ...
    """
    n = len(factors)
    w = 1.0 / n
    weights = {f.name: w for f in factors}
    terms = [f"{w:.4f} * rank({f.expression})" for f in factors]
    expression = " + ".join(terms)

    meta = {
        "method": "equal_weight",
        "description": f"{n} 因子等权合成",
        "n_factors": n,
        "weights": {f.name: round(w, 4) for f in factors},
    }
    return expression, weights, meta


def combine_ic_weighted(factors: list[FactorInfo]) -> tuple[str, dict[str, float], dict]:
    """
    Weight by absolute IC IR (information ratio).

    expression = sum( w_i * rank(f_i) )  where w_i ∝ |IC_IR_i|
    """
    irs = np.array([abs(f.ic_ir) for f in factors])
    if irs.sum() < 1e-12:
        # Fallback to equal weight if all IRs are zero
        return combine_equal_weight(factors)

    raw_w = irs / irs.sum()
    weights = {f.name: float(raw_w[i]) for i, f in enumerate(factors)}
    terms = [f"{weights[f.name]:.4f} * rank({f.expression})" for f in factors]
    expression = " + ".join(terms)

    meta = {
        "method": "ic_weighted",
        "description": f"{len(factors)} 因子按 IC IR 加权",
        "n_factors": len(factors),
        "ic_irs": {f.name: round(f.ic_ir, 4) for f in factors},
        "weights": {f.name: round(weights[f.name], 4) for f in factors},
    }
    return expression, weights, meta


def combine_score_weighted(factors: list[FactorInfo]) -> tuple[str, dict[str, float], dict]:
    """
    Weight by: IC_IR × (1 - max |pairwise corr|)

    This penalizes factors that are highly correlated with other factors,
    rewarding unique alpha sources.
    """
    n = len(factors)
    if n <= 1:
        return combine_equal_weight(factors)

    # Compute pairwise correlation matrix from IC series
    ic_matrix = {}
    for f in factors:
        if f.ic_series:
            ic_matrix[f.name] = f.ic_series
        elif f.raw_returns:
            ic_matrix[f.name] = f.raw_returns

    corr_penalty = {}
    if len(ic_matrix) == n:
        series_list = []
        names = []
        for f in factors:
            if f.name in ic_matrix:
                s = pd.Series(ic_matrix[f.name])
                series_list.append(s)
                names.append(f.name)
        if len(series_list) >= 2:
            corr_df = pd.concat(series_list, axis=1)
            corr_df.columns = names
            corr_mat = corr_df.corr().abs().fillna(0.0)  # NaN (constant series) → 0 corr
            for i, f in enumerate(factors):
                if f.name in corr_mat.index:
                    corr_row = corr_mat.loc[f.name].drop(f.name, errors='ignore')
                    max_corr = float(corr_row.max()) if len(corr_row) > 0 else 0.0
                    corr_penalty[f.name] = max_corr

    # Score = |IC_IR| × (1 - max|corr|)
    scores = {}
    for f in factors:
        ir = abs(f.ic_ir) if f.ic_ir else 0.01
        penalty = corr_penalty.get(f.name, 0.0)
        scores[f.name] = ir * (1.0 - min(penalty, 0.9))

    total = sum(scores.values())
    if total < 1e-12:
        return combine_equal_weight(factors)

    weights = {f.name: scores[f.name] / total for f in factors}
    terms = [f"{weights[f.name]:.4f} * rank({f.expression})" for f in factors]
    expression = " + ".join(terms)

    meta = {
        "method": "score_weighted",
        "description": f"{n} 因子按 IC IR × (1-max|corr|) 加权（惩罚冗余）",
        "n_factors": n,
        "corr_penalties": {k: round(v, 4) for k, v in corr_penalty.items()},
        "scores": {k: round(v, 4) for k, v in scores.items()},
        "weights": {k: round(v, 4) for k, v in weights.items()},
    }
    return expression, weights, meta


def combine_pca_first_pc(factors: list[FactorInfo]) -> tuple[str, dict[str, float], dict]:
    """
    Use PCA first principal component loadings as weights.

    Requires raw_returns (long_short) for each factor.
    Falls back to IC-weighted if raw_returns unavailable.
    """
    n = len(factors)
    if n <= 1:
        return combine_equal_weight(factors)

    # Build return matrix
    ret_data = {}
    min_len = float('inf')
    for f in factors:
        if f.raw_returns:
            ret_data[f.name] = f.raw_returns
            min_len = min(min_len, len(f.raw_returns))

    if len(ret_data) < 2 or min_len < 10:
        # Fallback: not enough data for PCA
        expr, w, meta = combine_ic_weighted(factors)
        meta["method"] = "pca_first_pc (fallback: ic_weighted — 样本不足)"
        return expr, w, meta

    # Trim to common length
    arrays = {}
    for name, rets in ret_data.items():
        arrays[name] = np.array(rets[:min_len])

    matrix = np.column_stack([arrays[f.name] for f in factors if f.name in arrays])
    if matrix.shape[1] < 2:
        return combine_ic_weighted(factors)

    # Standardize and PCA
    from numpy.linalg import eigh
    matrix_std = (matrix - matrix.mean(axis=0)) / (matrix.std(axis=0, ddof=1) + 1e-12)
    cov = np.cov(matrix_std.T)
    eigenvalues, eigenvectors = eigh(cov)
    # First PC is the eigenvector with largest eigenvalue
    pc1 = eigenvectors[:, -1]
    # Ensure positive weights (if PC1 is negative, flip)
    if pc1.sum() < 0:
        pc1 = -pc1
    pc1 = np.abs(pc1)  # All positive for interpretable weights

    raw_w = pc1 / pc1.sum()
    weights = {}
    idx = 0
    for f in factors:
        if f.name in arrays:
            weights[f.name] = float(raw_w[idx])
            idx += 1
        else:
            weights[f.name] = 1.0 / n  # fallback for factors without returns

    # Renormalize
    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}

    terms = [f"{weights[f.name]:.4f} * rank({f.expression})" for f in factors]
    expression = " + ".join(terms)

    explained_var = float(eigenvalues[-1] / eigenvalues.sum())
    meta = {
        "method": "pca_first_pc",
        "description": f"{n} 因子 PCA 第一主成分 ({explained_var:.1%} 方差解释)",
        "n_factors": n,
        "pc1_explained_variance": round(explained_var, 4),
        "pc1_loadings": {f.name: round(float(pc1[i]), 4) for i, f in enumerate(factors) if f.name in arrays},
        "weights": {k: round(v, 4) for k, v in weights.items()},
    }
    return expression, weights, meta


def combine(
    factor_names: list[str],
    method: str = "equal_weight",
    composite_name: str = "composite",
    composite_label: str = "",
) -> dict:
    """
    Main entry point: combine named factors into a composite.

    Args:
        factor_names: list of factor names (must be in trials.db with accepted=1)
        method: "equal_weight" | "ic_weighted" | "score_weighted" | "pca_first_pc"
        composite_name: output factor name
        composite_label: Chinese label for the composite factor

    Returns:
        Composite factor dict ready for JSON serialization (save_factor format).
    """
    all_accepted = load_accepted_factors()
    accepted_names = {f.name for f in all_accepted}

    # Validate
    not_accepted = [n for n in factor_names if n not in accepted_names]
    if not_accepted:
        return {
            "error": f"以下因子未通过三闸门验证: {not_accepted}",
            "accepted_factors": list(accepted_names),
        }

    selected = [f for f in all_accepted if f.name in factor_names]
    if len(selected) < 2:
        return {
            "error": f"至少需要 2 个因子进行合成，当前仅 {len(selected)} 个",
        }

    # Validate same dataset
    ds_error = validate_same_dataset(selected)
    if ds_error:
        return {"error": ds_error}

    # Compute combination
    methods = {
        "equal_weight": combine_equal_weight,
        "ic_weighted": combine_ic_weighted,
        "score_weighted": combine_score_weighted,
        "pca_first_pc": combine_pca_first_pc,
    }
    combiner = methods.get(method)
    if not combiner:
        return {"error": f"未知合成方法: {method}。可选: {list(methods.keys())}"}

    expression, weights, meta = combiner(selected)

    # Build composite factor JSON
    composite = {
        "name": composite_name,
        "label": composite_label or f"{len(selected)}因子合成({method})",
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "ResearchGil_Factor_Combine",
        "expression": expression,
        "composite_method": method,
        "sub_factors": [
            {
                "name": f.name,
                "weight": round(weights[f.name], 4),
                "ic_ir": round(f.ic_ir, 4) if f.ic_ir else 0.0,
                "expression": f.expression,
            }
            for f in selected
        ],
        "dataset_path": selected[0].dataset_path,
        "stats": {
            "n_factors": len(selected),
            "combination_meta": meta,
        },
    }

    return composite


def save_composite(composite: dict, save_path: str | None = None) -> str:
    """Save composite factor JSON to disk. Returns file path."""
    if "error" in composite:
        raise ValueError(f"Cannot save: {composite['error']}")

    file_path = save_path or os.path.join(FACTOR_DIR, f"{composite['name']}.json")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(composite, f, ensure_ascii=False, indent=2)

    return file_path


# ── CLI ──
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="ResearchGil Factor Combination Engine")
    parser.add_argument('factors', nargs='*', help='Factor names to combine')
    parser.add_argument('--method', '-m', default='equal_weight',
                        choices=['equal_weight', 'ic_weighted', 'score_weighted', 'pca_first_pc'])
    parser.add_argument('--name', '-n', default='composite', help='Composite factor name')
    parser.add_argument('--label', '-l', default='', help='Chinese label')
    parser.add_argument('--save', '-s', default='', help='Save path (default: ~/.gil_factors/{name}.json')
    parser.add_argument('--list-accepted', action='store_true', help='List all accepted factors')

    args = parser.parse_args()

    if args.list_accepted:
        factors = load_accepted_factors()
        if not factors:
            print("(无已通过验证的因子)")
        for f in factors:
            print(f"  ✅ {f.name}: IC_IR={f.ic_ir:.3f}, Sharpe={f.sharpe:.3f}, expr={f.expression}")
        sys.exit(0)

    result = combine(
        factor_names=args.factors,
        method=args.method,
        composite_name=args.name,
        composite_label=args.label,
    )

    if "error" in result:
        print(f"❌ {result['error']}")
        sys.exit(1)

    # Save
    path = save_composite(result, save_path=args.save or None)
    print(f"✅ 复合因子已保存: {path}")
    print(f"   表达式: {result['expression']}")
    print(f"   方法: {result['composite_method']}")
    print(f"   子因子权重:")
    for sf in result['sub_factors']:
        print(f"     {sf['name']}: {sf['weight']:.4f} (IC_IR={sf['ic_ir']:.3f})")
