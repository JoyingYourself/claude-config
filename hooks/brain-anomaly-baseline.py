#!/usr/bin/env python3
"""
brain-anomaly-baseline.py — P2 异常检测 · Phase 1 基线构建器

遍历 decisions.jsonl，按 session_id 聚合出每个历史会话的指标
（调用量 n_gated、deny+ask 风险率、bash 占比、破坏性命令数），
计算各指标的 mean/std/max/p95，写入 anomaly-baseline.json 供检测器比对。

冷启动保护：合格会话 < LOW_CONFIDENCE_SESSIONS 时标记 low_confidence=true，
检测器据此放宽 z-score 阈值，避免小样本误报。

调用方式:
  python3 brain-anomaly-baseline.py            # 构建并写入 baseline 文件
  python3 brain-anomaly-baseline.py --stdout   # 只打印，不写文件（调试）

设计原则: Fail-open — 任何异常打到 stderr 并 exit 0，不阻塞调用方。
"""

import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_anomaly_common as common  # noqa: E402

LOG_FILE = "/tmp/brain-anomaly.log"
# 参与统计的指标（destructive_count 也纳入均值，但检测端主要靠绝对命中）
METRIC_KEYS = ["n_gated", "deny_ask_rate", "bash_ratio", "destructive_count"]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [baseline] {msg}\n")
    except Exception:
        pass


def build_baseline():
    decisions = common.load_decisions()
    groups = common.group_by_session(decisions, exclude_pseudo=True)

    # 每个合格会话（调用量 >= MIN_SESSION_CALLS）算一组指标
    per_session = []
    for sid, rows in groups.items():
        m = common.metrics_for_decisions(rows)
        if m["n_gated"] >= common.MIN_SESSION_CALLS:
            per_session.append(m)

    n_sessions = len(per_session)
    metrics = {}
    for key in METRIC_KEYS:
        vals = [s[key] for s in per_session]
        mu, sd = common.mean_std(vals)
        metrics[key] = {
            "mean": round(mu, 4),
            "std": round(sd, 4),
            "max": round(max(vals), 4) if vals else 0.0,
            "p95": round(common.percentile(vals, 95), 4),
        }

    baseline = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "n_sessions": n_sessions,
        "n_decisions_total": len(decisions),
        "low_confidence": n_sessions < common.LOW_CONFIDENCE_SESSIONS,
        "min_session_calls": common.MIN_SESSION_CALLS,
        "metrics": metrics,
        "blacklist_size": len(common.DESTRUCTIVE_PATTERNS),
    }
    return baseline


def main():
    to_stdout = "--stdout" in sys.argv
    try:
        baseline = build_baseline()
    except Exception as e:  # fail-open
        log(f"build failed: {e}")
        # 即便失败也返回一个安全的空基线，检测器可据 low_confidence 走保守路径
        baseline = {
            "built_at": datetime.now(timezone.utc).isoformat(),
            "n_sessions": 0, "n_decisions_total": 0,
            "low_confidence": True, "metrics": {}, "error": str(e),
        }

    text = json.dumps(baseline, ensure_ascii=False, indent=2)
    if to_stdout:
        print(text)
    else:
        try:
            os.makedirs(common.BRAIN_DIR, exist_ok=True)
            with open(common.BASELINE_FILE, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            log(f"baseline built: {baseline['n_sessions']} sessions, "
                f"low_confidence={baseline['low_confidence']} → {common.BASELINE_FILE}")
            print(f"✅ baseline written: {baseline['n_sessions']} sessions "
                  f"(low_confidence={baseline['low_confidence']})")
        except Exception as e:
            log(f"write failed: {e}")
            print(text)
    sys.exit(0)


if __name__ == "__main__":
    main()
