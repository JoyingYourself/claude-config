#!/usr/bin/env python3
"""
brain_anomaly_common.py — P2 异常检测共享逻辑（单一事实源）

被 brain-anomaly-baseline.py 和 brain-anomaly-detector.py 共同 import，
集中管理：破坏性命令黑名单、会话级指标提取、统计工具函数。

设计原则（源自 secretary-agent/README.md §4 踩坑记录）:
  - Python 逐行 json.loads 解析 JSONL，禁 jq -s（坑9）
  - 路径含空格用 os.path 拼接，不裸拼字符串（坑5）
  - 纯函数，无副作用，便于两处复用与单测
"""

import os
import re
import json
import math
from collections import defaultdict

# ── 路径常量 ──────────────────────────────────────────────────────────
BRAIN_DIR = os.path.expanduser("~/.claudectl/brain")
DECISIONS_LOG = os.path.join(BRAIN_DIR, "decisions.jsonl")
SESSION_SUMMARIES_DIR = os.path.join(BRAIN_DIR, "session-summaries")
BASELINE_FILE = os.path.join(BRAIN_DIR, "anomaly-baseline.json")
ANOMALIES_LOG = os.path.join(BRAIN_DIR, "anomalies.jsonl")

# ── 破坏性命令黑名单（正则，忽略大小写）─────────────────────────────
# 命中任一即为高危信号。与 brain-fewshot-bridge.sh 的 "Immediately Deny"
# 规则保持语义一致，但这里用于事后会话审计而非实时拦截。
DESTRUCTIVE_PATTERNS = [
    (r"\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+(/|~|/\*|\$HOME)", "递归强删根/家目录"),
    (r"\brm\s+-[a-z]*f[a-z]*r[a-z]*\s+(/|~|/\*|\$HOME)", "递归强删根/家目录"),
    (r"\bsudo\s+rm\b", "sudo 删除"),
    (r"\bgit\s+reset\s+--hard\b", "git 硬重置"),
    (r"\bgit\s+push\s+.*--force\b", "git 强推"),
    (r"\bgit\s+push\s+-f\b", "git 强推"),
    (r"\bchmod\s+-R?\s*777\b", "chmod 777 提权"),
    (r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", "数据库删除"),
    (r"\bTRUNCATE\s+TABLE\b", "数据库清空"),
    (r"\bmkfs\b", "格式化磁盘"),
    (r"\bdd\s+if=.*\bof=/dev/", "dd 写裸设备"),
    (r">\s*/dev/sd[a-z]", "重定向到裸磁盘"),
    (r"\bof=/dev/sd[a-z]", "写入裸磁盘"),
    (r"(curl|wget)\s+.*\|\s*(sudo\s+)?(ba)?sh\b", "管道下载执行"),
    (r"\bdocker\s+system\s+prune\s+-a", "docker 全清理"),
    (r"\bdocker\s+rm\s+-f\b", "docker 强删容器"),
    (r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", "fork 炸弹"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), label) for p, label in DESTRUCTIVE_PATTERNS]

# 参与基线统计的最小会话规模（过滤掉只有 1-2 次调用的碎片会话）
MIN_SESSION_CALLS = 3
# 视为"低置信基线"的会话数下限（冷启动保护）
LOW_CONFIDENCE_SESSIONS = 10
# 排除的伪会话前缀/值（seed 种子数据 + 无 session_id 的历史聚合）
_EXCLUDED_SIDS = ("unknown", "")


def is_seed_or_unknown(sid):
    """判断 session_id 是否为伪会话（种子/未知），应排除出基线。"""
    if sid in _EXCLUDED_SIDS:
        return True
    if sid.startswith("seed-"):
        return True
    return False


def match_destructive(command):
    """返回命令命中的破坏性标签列表（可能多个），无命中返回空列表。"""
    if not command:
        return []
    hits = []
    for rx, label in _COMPILED:
        if rx.search(command):
            hits.append(label)
    return hits


def load_decisions(path=DECISIONS_LOG):
    """逐行解析 decisions.jsonl（禁 jq -s，坑9），返回 dict 列表。"""
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def metrics_for_decisions(decision_rows):
    """
    从一组决策行（同一会话）计算会话级指标。
    输入: 该会话的 decision dict 列表
    输出: {n_gated, deny_ask_rate, bash_ratio, destructive_count, destructive_labels}
    """
    n = len(decision_rows)
    if n == 0:
        return {
            "n_gated": 0, "deny_ask_rate": 0.0, "bash_ratio": 0.0,
            "destructive_count": 0, "destructive_labels": [],
        }
    deny_ask = sum(1 for d in decision_rows if d.get("action") in ("deny", "ask"))
    bash = sum(1 for d in decision_rows if d.get("tool") == "Bash")
    destr_labels = []
    for d in decision_rows:
        destr_labels.extend(match_destructive(d.get("command", "")))
    return {
        "n_gated": n,
        "deny_ask_rate": deny_ask / n,
        "bash_ratio": bash / n,
        "destructive_count": len(destr_labels),
        "destructive_labels": destr_labels,
    }


def group_by_session(decision_rows, exclude_pseudo=True):
    """按 session_id 分组决策行。exclude_pseudo=True 时剔除种子/未知会话。"""
    groups = defaultdict(list)
    for d in decision_rows:
        sid = d.get("session_id", "unknown")
        if exclude_pseudo and is_seed_or_unknown(sid):
            continue
        groups[sid].append(d)
    return groups


def mean_std(values):
    """样本均值与总体标准差（n<2 时 std=0）。"""
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mu = sum(values) / n
    if n < 2:
        return mu, 0.0
    var = sum((v - mu) ** 2 for v in values) / n
    return mu, math.sqrt(var)


def percentile(values, pct):
    """线性插值分位数。values 无需预排序。pct ∈ [0,100]。"""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * (pct / 100.0)
    lo = int(math.floor(k))
    hi = int(math.ceil(k))
    if lo == hi:
        return float(s[lo])
    return s[lo] * (hi - k) + s[hi] * (k - lo)


def zscore(x, stat):
    """
    针对基线 stat={mean,std} 计算 x 的 z 分数。
    std≈0（历史无波动）时退化：x 不超过均值→0；超过均值 2 倍→给一个中等分 3.0，
    否则 0，避免除零同时保留"明显超出"的检测力。
    """
    mu = stat.get("mean", 0.0)
    sd = stat.get("std", 0.0)
    if sd <= 1e-9:
        if x <= mu:
            return 0.0
        return 3.0 if x > max(mu * 2.0, mu + 1) else 0.0
    return (x - mu) / sd
