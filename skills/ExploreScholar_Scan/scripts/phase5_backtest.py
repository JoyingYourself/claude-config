#!/usr/bin/env python3
"""
Phase 5: 论文因子回测验证
对 Phase 4 产出的论文因子执行回测验证，包含论文因子回测和标准因子基线。
"""

import duckdb
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import json
import os
import sys
import warnings
from collections import defaultdict
warnings.filterwarnings('ignore')

# ========== Configuration ==========
DB_DIR = "/Users/junye_shi/Scholarship is a new sexy/Gildata_SecuCategory1&41_DuckDB"
OUTPUT_DIR = "/Users/junye_shi/AgentFiles/Multi-toolIntegrationAgent/Weekly_ResearchReport/中间文件/2026-07-04/backtests"
START_DATE = "2016-01-01"
END_DATE = "2026-06-30"
MIN_TRADING_DAYS = 15

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== Database Connections ==========
print("Connecting to databases...")
con_market = duckdb.connect(os.path.join(DB_DIR, "StockMarket_Main.duckdb"), read_only=True)
con_basic = duckdb.connect(os.path.join(DB_DIR, "StockBasic_Main.duckdb"), read_only=True)
con_basicdata = duckdb.connect(os.path.join(DB_DIR, "BasicData.duckdb"), read_only=True)

# ========== Step 1: Build Universe ==========
print("=" * 60)
print("Building universe...")
print("=" * 60)

a_share_codes = [r[0] for r in con_basicdata.execute("""
    SELECT innercode FROM secumain
    WHERE secucategory=1 AND listedstate=1
""").fetchall()]
print(f"Total A-shares (listedstate=1): {len(a_share_codes)}")

# Get innercode mapping
innercode_info = {}
batch_size = 1000
for i in range(0, len(a_share_codes), batch_size):
    batch = a_share_codes[i:i+batch_size]
    codes_str = ','.join(map(str, batch))
    for r in con_basicdata.execute(f"""
        SELECT innercode, companycode, secucode, chiname, listeddate
        FROM secumain
        WHERE innercode IN ({codes_str})
    """).fetchall():
        innercode_info[r[0]] = {
            'companycode': r[1], 'secucode': r[2],
            'chiname': r[3], 'listeddate': r[4]
        }
print(f"Mapped innercodes: {len(innercode_info)}")

# Get industry info
company_to_industry = {}
for r in con_basic.execute(f"""
    SELECT companycode, firstindustrycode, firstindustryname
    FROM (
        SELECT companycode, firstindustrycode, firstindustryname,
               ROW_NUMBER() OVER (PARTITION BY companycode ORDER BY infopubldate DESC) as rn
        FROM lc_exgindustry
        WHERE standard=40 AND ifperformed=1
    ) sub WHERE rn=1
""").fetchall():
    company_to_industry[r[0]] = {'industry_code': r[1], 'industry_name': r[2]}
print(f"Mapped companies to industry: {len(company_to_industry)}")

# Get ST stocks
st_codes = set()
for r in con_market.execute("""
    SELECT DISTINCT innercode FROM lc_specialtrade
    WHERE specialtradetype IN (1, 2, 3, 4, 5)
""").fetchall():
    st_codes.add(r[0])
print(f"ST flagged innercodes: {len(st_codes)}")

# Build final universe
universe = {}
for innercode, info in innercode_info.items():
    companycode = info['companycode']
    industry = company_to_industry.get(companycode, {})
    industry_name = industry.get('industry_name', '')
    if industry_name == '金融':  # 金融
        continue
    if innercode in st_codes:
        continue
    listed_date = info['listeddate']
    if listed_date is None:
        continue
    universe[innercode] = {
        'companycode': companycode,
        'secucode': info['secucode'],
        'chiname': info['chiname'],
        'listeddate': listed_date,
        'industry_name': industry_name,
        'industry_code': industry.get('industry_code', '')
    }
print(f"Final universe size (A-share, non-financial, non-ST): {len(universe)}")

# ========== Step 2: Pre-compute daily data ==========
print("\n" + "=" * 60)
print("Pre-computing daily data...")
print("=" * 60)

# Build universe codes string in chunks for SQL
def codes_to_sql(codes_dict):
    """Convert dict keys to SQL IN clause string"""
    codes = list(codes_dict.keys())
    chunks = []
    for i in range(0, len(codes), 1000):
        batch = codes[i:i+1000]
        chunks.append(','.join(map(str, batch)))
    return ','.join(chunks)

universe_sql = codes_to_sql(universe)

print("Creating daily data view...")
con_market.execute(f"""
    CREATE OR REPLACE TEMP VIEW daily_data AS
    SELECT
        d.innercode,
        d.tradingday::DATE as tradingday,
        d.closeprice,
        d.turnovervolume as volume,
        d.turnovervalue as amount,
        LAG(d.closeprice) OVER (PARTITION BY d.innercode ORDER BY d.tradingday) as prev_close,
        d.closeprice / NULLIF(LAG(d.closeprice) OVER (PARTITION BY d.innercode ORDER BY d.tradingday), 0) - 1 as daily_ret,
        strftime(d.tradingday, '%Y-%m') as ym
    FROM qt_dailyquote d
    WHERE d.tradingday >= '{START_DATE}' AND d.tradingday < '{END_DATE}'
      AND d.innercode IN ({universe_sql})
      AND d.closeprice IS NOT NULL AND d.closeprice > 0
      AND d.turnovervolume IS NOT NULL AND d.turnovervolume > 0
""")

row_count = con_market.execute("SELECT COUNT(*) FROM daily_data").fetchone()[0]
print(f"Daily data rows: {row_count}")

# Monthly aggregated data
print("Creating monthly data view...")
con_market.execute(f"""
    CREATE OR REPLACE TEMP VIEW monthly_data AS
    SELECT
        innercode, ym,
        MAX(tradingday) as month_end_date,
        LAST(closeprice ORDER BY tradingday) as month_end_close,
        (LAST(closeprice ORDER BY tradingday) / NULLIF(FIRST(closeprice ORDER BY tradingday), 0) - 1) as monthly_return,
        COUNT(*) as trading_days,
        SUM(volume) as month_total_volume,
        STDDEV(volume) as month_volume_std
    FROM daily_data
    GROUP BY innercode, ym
""")

# Get all monthly dates
monthly_dates = [r[0] for r in con_market.execute("""
    SELECT DISTINCT ym FROM monthly_data ORDER BY ym
""").fetchall()]
print(f"Monthly periods: {len(monthly_dates)} ({monthly_dates[0]} to {monthly_dates[-1]})")

# Pre-compute monthly returns
print("Computing monthly returns...")
monthly_ret_data = con_market.execute(f"""
    SELECT innercode, ym, monthly_return
    FROM monthly_data
    WHERE trading_days >= {MIN_TRADING_DAYS}
      AND monthly_return IS NOT NULL
""").fetchall()
print(f"Monthly return obs: {len(monthly_ret_data)}")

monthly_ret_dict = defaultdict(dict)
for r in monthly_ret_data:
    monthly_ret_dict[r[0]][r[1]] = r[2]

# ========== Step 3: Factor Computation ==========
print("\n" + "=" * 60)
print("Computing factors...")
print("=" * 60)

paper_factors = {}

# FACTOR_W27_001: Signed Order Flow
print("\nFACTOR_W27_001: Signed Order Flow...")
raw = con_market.execute(f"""
    SELECT innercode, ym,
           SUM(volume * SIGN(closeprice - prev_close)) as signedflow
    FROM daily_data
    WHERE prev_close IS NOT NULL AND ABS(closeprice - prev_close) > 0
    GROUP BY innercode, ym
""").fetchall()
paper_factors['FACTOR_W27_001'] = [{'innercode': r[0], 'ym': r[1], 'value': r[2]} for r in raw]
print(f"  {len(paper_factors['FACTOR_W27_001'])} obs")

# FACTOR_W27_002: Kyle's Lambda Regression
print("FACTOR_W27_002: Kyle's Lambda (regression)...")
raw = con_market.execute(f"""
    SELECT innercode, ym,
           REGR_SLOPE(closeprice - prev_close,
                      volume * SIGN(closeprice - prev_close)) as kyle_lambda
    FROM daily_data
    WHERE prev_close IS NOT NULL AND ABS(closeprice - prev_close) > 0
    GROUP BY innercode, ym
    HAVING COUNT(*) >= 15
""").fetchall()
paper_factors['FACTOR_W27_002'] = [{'innercode': r[0], 'ym': r[1], 'value': r[2]} for r in raw]
print(f"  {len(paper_factors['FACTOR_W27_002'])} obs")

# FACTOR_W27_003: Amihud-style Lambda
print("FACTOR_W27_003: Amihud-style Lambda...")
raw = con_market.execute(f"""
    SELECT innercode, ym,
           AVG(ABS(daily_ret) / NULLIF(amount, 0)) as amihud_lambda
    FROM daily_data
    WHERE daily_ret IS NOT NULL AND amount IS NOT NULL AND amount > 0
      AND ABS(daily_ret) < 0.5
    GROUP BY innercode, ym
""").fetchall()
paper_factors['FACTOR_W27_003'] = [{'innercode': r[0], 'ym': r[1], 'value': r[2]} for r in raw]
print(f"  {len(paper_factors['FACTOR_W27_003'])} obs")

# FACTOR_W27_004: Volume Volatility
print("FACTOR_W27_004: Volume Volatility...")
raw = con_market.execute(f"""
    SELECT innercode, ym,
           STDDEV(volume) as volume_volatility
    FROM daily_data
    WHERE volume IS NOT NULL AND volume > 0
    GROUP BY innercode, ym
""").fetchall()
paper_factors['FACTOR_W27_004'] = [{'innercode': r[0], 'ym': r[1], 'value': r[2]} for r in raw]
print(f"  {len(paper_factors['FACTOR_W27_004'])} obs")

# FACTOR_W27_006: Log Price
print("FACTOR_W27_006: Log Price...")
raw = con_market.execute(f"""
    SELECT innercode, ym,
           LN(month_end_close) as log_price
    FROM monthly_data
    WHERE month_end_close > 1.0
""").fetchall()
paper_factors['FACTOR_W27_006'] = [{'innercode': r[0], 'ym': r[1], 'value': r[2]} for r in raw]
print(f"  {len(paper_factors['FACTOR_W27_006'])} obs")

# FACTOR_W27_007: Annualized Volatility (rolling 12m)
print("FACTOR_W27_007: Annualized Volatility...")
stock_returns = defaultdict(list)
for r in monthly_ret_data:
    stock_returns[r[0]].append((r[1], r[2]))

results_007 = []
for innercode, returns in stock_returns.items():
    returns.sort(key=lambda x: x[0])
    for i in range(12, len(returns)):
        mrets = [r[1] for r in returns[i-12:i]]
        mrets = [r for r in mrets if r is not None]
        if len(mrets) >= 8:
            vol = np.std(mrets, ddof=1) * np.sqrt(12)
            results_007.append((innercode, returns[i][0], vol))
paper_factors['FACTOR_W27_007'] = [{'innercode': r[0], 'ym': r[1], 'value': r[2]} for r in results_007]
print(f"  {len(paper_factors['FACTOR_W27_007'])} obs")

# FACTOR_W27_009: Momentum 12-2
print("FACTOR_W27_009: Momentum 12-2...")
results_009 = []
for innercode, returns in stock_returns.items():
    returns.sort(key=lambda x: x[0])
    for i in range(13, len(returns)):
        relevant = returns[i-12:i-1]
        mrets = [r[1] for r in relevant]
        mrets = [r for r in mrets if r is not None]
        if len(mrets) >= 8:
            mom = np.prod([1 + r for r in mrets]) - 1
            results_009.append((innercode, returns[i][0], mom))
paper_factors['FACTOR_W27_009'] = [{'innercode': r[0], 'ym': r[1], 'value': r[2]} for r in results_009]
print(f"  {len(paper_factors['FACTOR_W27_009'])} obs")

# FACTOR_W27_010: Short-term Reversal
print("FACTOR_W27_010: Short-term Reversal...")
results_010 = []
for innercode, returns in stock_returns.items():
    returns.sort(key=lambda x: x[0])
    for i in range(1, len(returns)):
        results_010.append((innercode, returns[i][0], returns[i-1][1]))
paper_factors['FACTOR_W27_010'] = [{'innercode': r[0], 'ym': r[1], 'value': r[2]} for r in results_010]
print(f"  {len(paper_factors['FACTOR_W27_010'])} obs")

# Baseline factors
print("\n--- Baseline Factors ---")
baseline_factors = {}

# Log Market Cap
print("Log_Market_Cap...")
raw = con_market.execute(f"""
    SELECT innercode, ym, LN(NULLIF(totalmv, 0)) as log_mcap
    FROM (
        SELECT v.innercode, strftime(v.tradingday, '%Y-%m') as ym, v.totalmv,
               ROW_NUMBER() OVER (PARTITION BY v.innercode, strftime(v.tradingday, '%Y-%m')
                                  ORDER BY v.tradingday DESC) as rn
        FROM lc_dindicesforvaluation v
        WHERE v.tradingday >= '{START_DATE}' AND v.tradingday < '{END_DATE}'
          AND v.innercode IN ({universe_sql})
          AND v.totalmv IS NOT NULL AND v.totalmv > 0
    ) sub WHERE rn=1
""").fetchall()
baseline_factors['Log_Market_Cap'] = [{'innercode': r[0], 'ym': r[1], 'value': r[2]} for r in raw]
print(f"  {len(baseline_factors['Log_Market_Cap'])} obs")

# Book to Market
print("Book_to_Market...")
raw = con_market.execute(f"""
    SELECT innercode, ym, 1.0 / NULLIF(pe, 0) as bm_proxy
    FROM (
        SELECT v.innercode, strftime(v.tradingday, '%Y-%m') as ym, v.pe,
               ROW_NUMBER() OVER (PARTITION BY v.innercode, strftime(v.tradingday, '%Y-%m')
                                  ORDER BY v.tradingday DESC) as rn
        FROM lc_dindicesforvaluation v
        WHERE v.tradingday >= '{START_DATE}' AND v.tradingday < '{END_DATE}'
          AND v.innercode IN ({universe_sql})
          AND v.pe IS NOT NULL AND v.pe > 0 AND v.pe < 1000
    ) sub WHERE rn=1
""").fetchall()
baseline_factors['Book_to_Market'] = [{'innercode': r[0], 'ym': r[1], 'value': r[2]} for r in raw]
print(f"  {len(baseline_factors['Book_to_Market'])} obs")

# Momentum_12_2 (same as factor 009)
baseline_factors['Momentum_12_2'] = paper_factors['FACTOR_W27_009']
print(f"Momentum_12_2: {len(baseline_factors['Momentum_12_2'])} obs (reuse)")

# Short_Term_Reversal_1M (same as factor 010)
baseline_factors['Short_Term_Reversal_1M'] = paper_factors['FACTOR_W27_010']
print(f"Short_Term_Reversal_1M: {len(baseline_factors['Short_Term_Reversal_1M'])} obs (reuse)")

# ========== Step 4: Backtest Engine ==========
print("\n" + "=" * 60)
print("Running backtest engine...")
print("=" * 60)

def compute_forward_return(innercode, current_ym, ret_dict, n_months=1):
    ym_list = sorted(ret_dict.get(innercode, {}).keys())
    try:
        idx = ym_list.index(current_ym)
    except ValueError:
        return None
    if idx + n_months < len(ym_list):
        return ret_dict[innercode].get(ym_list[idx + n_months])
    return None

def winsorize(arr, lower=0.01, upper=0.99):
    a = np.array(arr, dtype=float)
    valid = ~np.isnan(a)
    if valid.sum() < 5:
        return a
    l = np.percentile(a[valid], lower * 100)
    u = np.percentile(a[valid], upper * 100)
    return np.clip(a, l, u)

def standardize(arr):
    a = np.array(arr, dtype=float)
    valid = ~np.isnan(a)
    if valid.sum() < 2:
        return a
    a[valid] = (a[valid] - np.mean(a[valid])) / np.std(a[valid])
    return a

def industry_neutralize(values, innercodes, ind_map):
    a = np.array(values, dtype=float)
    groups = defaultdict(list)
    for i, ic in enumerate(innercodes):
        groups[ind_map.get(ic, '')].append(i)
    for ind, indices in groups.items():
        if len(indices) < 2:
            continue
        vals = a[indices]
        m = np.nanmean(vals)
        if not np.isnan(m):
            a[indices] = vals - m
    return a

def run_backtest(factor_name, factor_data, ret_dict, universe_info,
                 expected_sign='negative'):
    factor_by_ym = defaultdict(dict)
    for obs in factor_data:
        factor_by_ym[obs['ym']][obs['innercode']] = obs['value']

    monthly_ics = []
    monthly_ls = []
    monthly_q_rets = []
    monthly_n = []

    all_yms = sorted(factor_by_ym.keys())

    for ym in all_yms:
        try:
            ym_idx = monthly_dates.index(ym)
        except ValueError:
            continue
        if ym_idx >= len(monthly_dates) - 1:
            continue
        next_ym = monthly_dates[ym_idx + 1]

        fvals = factor_by_ym[ym]
        ics = list(fvals.keys())
        if len(ics) < 30:
            continue

        values = np.array([fvals[ic] for ic in ics], dtype=float)
        frets = np.array([compute_forward_return(ic, ym, ret_dict) for ic in ics], dtype=float)

        valid = ~np.isnan(values) & ~np.isnan(frets) & ~np.isinf(values)
        if valid.sum() < 30:
            continue

        values = values[valid]
        frets = frets[valid]
        ics_valid = [ics[i] for i in range(len(ics)) if valid[i]]

        # Winsorize
        values = winsorize(values)
        frets = winsorize(frets, 0.005, 0.995)

        # Industry neutralize
        ind_map = {}
        for ic in ics_valid:
            cc = universe_info.get(ic, {}).get('companycode', '')
            ind_map[ic] = company_to_industry.get(cc, {}).get('industry_name', '')
        values = industry_neutralize(values, ics_valid, ind_map)

        # Standardize
        values = standardize(values)
        valid2 = ~np.isnan(values)
        if valid2.sum() < 30:
            continue

        # Rank IC
        ic, _ = stats.spearmanr(values[valid2], frets[valid2])

        # Quintile
        qvals = values[valid2]
        qrets = frets[valid2]
        sidx = np.argsort(qvals)
        qvals_sorted = qvals[sidx]
        qrets_sorted = qrets[sidx]

        nq = len(qvals_sorted) // 5
        qrets_list = []
        for q in range(5):
            s = q * nq
            e = (q + 1) * nq if q < 4 else len(qvals_sorted)
            qrets_list.append(np.mean(qrets_sorted[s:e]))

        ls = qrets_list[4] - qrets_list[0]
        if expected_sign == 'negative':
            ls = qrets_list[0] - qrets_list[4]  # Q1-Q5 for negative factors

        monthly_ics.append(ic)
        monthly_ls.append(ls)
        monthly_q_rets.append(qrets_list)
        monthly_n.append(len(qvals))

    if len(monthly_ics) == 0:
        return {'mean_ic': None, 'icir': None, 'long_short_monthly': None,
                'n_months': 0, 'n_stocks_avg': 0, 'status': 'INSUFFICIENT_DATA',
                'ic_sign_match': None}

    mic = np.mean(monthly_ics)
    sic = np.std(monthly_ics, ddof=1)
    icir = mic / sic if sic > 0 else 0
    ls_m = np.mean(monthly_ls)
    ls_s = np.std(monthly_ls, ddof=1)
    ls_t = ls_m / ls_s * np.sqrt(len(monthly_ls)) if ls_s > 0 else 0

    if abs(mic) > 0.02 or icir > 0.3:
        status = 'PASS'
    elif abs(mic) > 0.01 or icir > 0.15:
        status = 'WEAK'
    else:
        status = 'FAIL'

    ic_sign_match = (mic < 0 and expected_sign == 'negative') or \
                    (mic > 0 and expected_sign == 'positive')

    return {
        'mean_ic': round(float(mic), 6),
        'std_ic': round(float(sic), 6),
        'icir': round(float(icir), 4),
        'ic_sign_match': ic_sign_match,
        'long_short_monthly': round(float(ls_m), 6),
        'long_short_t_stat': round(float(ls_t), 4),
        'long_short_std': round(float(ls_s), 6),
        'n_months': len(monthly_ics),
        'n_stocks_avg': int(np.mean(monthly_n)),
        'status': status
    }

# ========== Step 5: Execute Backtests ==========

factor_meta = {
    'FACTOR_W27_001': {'name': 'Signed Order Flow', 'paper': 'arxiv:2607.01377v1', 'cat': 'momentum', 'rep': 'direct', 'sign': 'negative'},
    'FACTOR_W27_002': {'name': "Kyle's Lambda (Regression)", 'paper': 'arxiv:2607.01377v1', 'cat': 'momentum', 'rep': 'direct', 'sign': 'negative'},
    'FACTOR_W27_003': {'name': "Kyle's Lambda (Amihud-style)", 'paper': 'arxiv:2607.01377v1', 'cat': 'momentum', 'rep': 'direct', 'sign': 'negative'},
    'FACTOR_W27_004': {'name': 'Volume Volatility', 'paper': 'arxiv:2607.01377v1', 'cat': 'momentum', 'rep': 'direct', 'sign': 'positive'},
    'FACTOR_W27_006': {'name': 'Log Price', 'paper': 'arxiv:2606.29290v1', 'cat': 'momentum', 'rep': 'direct', 'sign': 'positive'},
    'FACTOR_W27_007': {'name': 'Annualized Volatility', 'paper': 'arxiv:2606.29290v1', 'cat': 'momentum', 'rep': 'direct', 'sign': 'positive'},
    'FACTOR_W27_009': {'name': 'Momentum 12-2', 'paper': 'arxiv:2606.29290v1', 'cat': 'momentum', 'rep': 'direct', 'sign': 'positive'},
    'FACTOR_W27_010': {'name': 'Short-term Reversal', 'paper': 'arxiv:2606.29290v1', 'cat': 'momentum', 'rep': 'direct', 'sign': 'negative'},
}

baseline_meta = {
    'Log_Market_Cap': {'name': 'Log Market Cap', 'sign': 'negative'},
    'Book_to_Market': {'name': 'Book to Market', 'sign': 'positive'},
    'Momentum_12_2': {'name': 'Momentum 12-2', 'sign': 'positive'},
    'Short_Term_Reversal_1M': {'name': 'Short-term Reversal 1M', 'sign': 'negative'},
}

print("\n" + "-" * 60)
print("Paper factor backtests")
print("-" * 60)

paper_results = []
for fid, meta in sorted(factor_meta.items()):
    if fid not in paper_factors:
        paper_results.append({
            'factor_id': fid, 'factor_name': meta['name'],
            'source_paper': meta['paper'], 'category': meta['cat'],
            'replicability': meta['rep'],
            'mean_ic': None, 'icir': None, 'long_short_monthly': None,
            'status': 'SKIPPED', 'reason': 'No factor data computed'
        })
        print(f"  {meta['name']}: SKIPPED (no data)")
        continue

    print(f"  {meta['name']}...", end=' ', flush=True)
    result = run_backtest(fid, paper_factors[fid], monthly_ret_dict, universe,
                          expected_sign=meta['sign'])
    paper_results.append({
        'factor_id': fid, 'factor_name': meta['name'],
        'source_paper': meta['paper'], 'category': meta['cat'],
        'replicability': meta['rep'],
        'mean_ic': result['mean_ic'], 'icir': result['icir'],
        'long_short_monthly': result['long_short_monthly'],
        'long_short_t_stat': result['long_short_t_stat'],
        'n_months': result['n_months'], 'n_stocks_avg': result['n_stocks_avg'],
        'ic_sign_match': result['ic_sign_match'], 'status': result['status']
    })
    print(f"IC={result['mean_ic']:.4f}, ICIR={result['icir']:.2f}, "
          f"LS={result['long_short_monthly']:.4f}, {result['status']}")

# Add proxy factors
print("\n  Network-enhanced LLM Embedding: PENDING (needs NLP+KG)")
paper_results.append({
    'factor_id': 'FACTOR_W27_005',
    'factor_name': 'Network-enhanced LLM Embedding (net_pc_5)',
    'source_paper': 'arxiv:2606.29290v1', 'category': 'alternative',
    'replicability': 'proxy',
    'mean_ic': None, 'icir': None, 'long_short_monthly': None,
    'status': 'PENDING_APPROXIMATION',
    'reason': 'Requires Chinese FinBERT NLP pipeline and supply chain KG. Est. 50+ hrs.'
})

print("  Direct LLM Embedding: PENDING (needs NLP pipeline)")
paper_results.append({
    'factor_id': 'FACTOR_W27_008',
    'factor_name': 'Direct LLM Embedding (pc_5)',
    'source_paper': 'arxiv:2606.29290v1', 'category': 'alternative',
    'replicability': 'proxy',
    'mean_ic': None, 'icir': None, 'long_short_monthly': None,
    'status': 'PENDING_APPROXIMATION',
    'reason': 'Requires Chinese FinBERT NLP pipeline for annual report MD&A. Est. 20+ hrs.'
})

print("\n" + "-" * 60)
print("Baseline factor backtests")
print("-" * 60)

baseline_results = []
for fid, meta in baseline_meta.items():
    if fid not in baseline_factors:
        baseline_results.append({
            'factor_id': fid, 'factor_name': meta['name'],
            'source_paper': 'baseline',
            'mean_ic': None, 'icir': None, 'long_short_monthly': None,
            'status': 'SKIPPED', 'reason': 'No factor data computed'
        })
        print(f"  {meta['name']}: SKIPPED (no data)")
        continue

    print(f"  {meta['name']}...", end=' ', flush=True)
    result = run_backtest(fid, baseline_factors[fid], monthly_ret_dict, universe,
                          expected_sign=meta['sign'])
    baseline_results.append({
        'factor_id': fid, 'factor_name': meta['name'],
        'source_paper': 'baseline',
        'mean_ic': result['mean_ic'], 'icir': result['icir'],
        'long_short_monthly': result['long_short_monthly'],
        'long_short_t_stat': result['long_short_t_stat'],
        'n_months': result['n_months'], 'n_stocks_avg': result['n_stocks_avg'],
        'ic_sign_match': result['ic_sign_match'], 'status': result['status']
    })
    print(f"IC={result['mean_ic']:.4f}, ICIR={result['icir']:.2f}, "
          f"LS={result['long_short_monthly']:.4f}, {result['status']}")

# ========== Step 6: Summary ==========
summary = {
    'paper_total': len(paper_results),
    'paper_backtested': sum(1 for r in paper_results if r.get('mean_ic') is not None),
    'paper_pending': sum(1 for r in paper_results if r.get('status') == 'PENDING_APPROXIMATION'),
    'paper_skipped': sum(1 for r in paper_results if r.get('status') == 'SKIPPED'),
    'paper_pass': sum(1 for r in paper_results if r.get('status') == 'PASS'),
    'paper_weak': sum(1 for r in paper_results if r.get('status') == 'WEAK'),
    'paper_fail': sum(1 for r in paper_results if r.get('status') == 'FAIL'),
    'paper_insufficient': sum(1 for r in paper_results if r.get('status') == 'INSUFFICIENT_DATA'),
    'baseline_total': len(baseline_results),
    'baseline_pass': sum(1 for r in baseline_results if r.get('status') == 'PASS'),
    'backtest_period': f"{START_DATE} to {END_DATE}",
    'generated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')
}

# ========== Step 7: Save ==========
output = {
    'paper_factors': paper_results,
    'baseline_factors': baseline_results,
    'summary': summary
}

output_path = os.path.join(OUTPUT_DIR, 'phase5_results.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)
print(f"\nResults saved to: {output_path}")

# ========== Step 8: Print Tables ==========
print(f"\n{'='*60}")
print("FINAL REPORT")
print(f"{'='*60}")

print(f"\n=== 论文因子回测 ===")
h = f"{'因子':<30} {'来源':<20} {'复现':<6} {'Mean IC':<10} {'ICIR':<8} {'多空月收益':<10} {'状态':<12}"
print(h)
print('-' * len(h))
for r in paper_results:
    ic = f"{r['mean_ic']:.4f}" if r['mean_ic'] is not None else 'N/A'
    ir = f"{r['icir']:.2f}" if r['icir'] is not None else 'N/A'
    ls = f"{r['long_short_monthly']:.4f}" if r['long_short_monthly'] is not None else 'N/A'
    rep = r.get('replicability', '')
    print(f"{r['factor_name']:<30} {r['source_paper'][:18]:<20} {rep:<6} {ic:<10} {ir:<8} {ls:<10} {r['status']:<12}")

print(f"\n=== 标准因子基线 ===")
h2 = f"{'因子':<30} {'Mean IC':<10} {'ICIR':<8} {'多空月收益':<10} {'状态':<12}"
print(h2)
print('-' * len(h2))
for r in baseline_results:
    ic = f"{r['mean_ic']:.4f}" if r['mean_ic'] is not None else 'N/A'
    ir = f"{r['icir']:.2f}" if r['icir'] is not None else 'N/A'
    ls = f"{r['long_short_monthly']:.4f}" if r['long_short_monthly'] is not None else 'N/A'
    print(f"{r['factor_name']:<30} {ic:<10} {ir:<8} {ls:<10} {r['status']:<12}")

print(f"\n=== 汇总 ===")
print(f"论文因子总数: {summary['paper_total']}")
print(f"  已回测: {summary['paper_backtested']}")
print(f"  待近似: {summary['paper_pending']}")
print(f"  跳过: {summary['paper_skipped']}")
print(f"  PASS: {summary['paper_pass']}")
print(f"  WEAK: {summary['paper_weak']}")
print(f"  FAIL: {summary['paper_fail']}")
print(f"  数据不足: {summary['paper_insufficient']}")
print(f"基线因子: {summary['baseline_total']}")
print(f"  基线PASS: {summary['baseline_pass']}")

con_market.close()
con_basic.close()
con_basicdata.close()
print(f"\nDone! Output: {output_path}")
