#!/usr/bin/env python3
"""
brain-file-watcher.py — 文件感知监控 + macOS 桌面通知

监控固定路径下的数据文件，检测过期状态并通过 osascript 弹窗提醒。

监控规则:
  1. DuckDB 数据库: 文件 mtime > 14 天 → 查询库内最新数据日期 → 提醒更新
  2. github_related: 最新活跃子文件夹 > 14 天 → 提醒检索新项目

调度: launchd 每 6 小时执行一次。同一提醒 48h 内不重复发送。
"""

import os
import glob
import json
import time
import subprocess
from datetime import datetime, timezone

# ── 配置 ──────────────────────────────────────────────────────────────

DAYS_THRESHOLD = 14           # 超过此天数触发提醒
DEDUP_HOURS = 48              # 同一条提醒 48h 内不重复
STATE_FILE = os.path.expanduser("~/.claudectl/brain/watcher-state.json")
LOG_FILE = "/tmp/brain-file-watcher.log"

# DuckDB 监控路径
DUCKDB_PATHS = [
    "/Users/junye_shi/Scholarship is a new sexy/Gildata_SecuCategory1&41_DuckDB",
    "/Users/junye_shi/Scholarship is a new sexy/Gildata_SecuCategory8_DuckDB",
]

# GitHub 项目检索路径
GITHUB_RELATED = "/Users/junye_shi/Scholarship is a new sexy/github_related"

NOW = time.time()
NOW_ISO = datetime.now(timezone.utc).isoformat()

# ── 去重逻辑 ──────────────────────────────────────────────────────────

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def should_notify(key):
    """检查 key 是否在冷却期内"""
    state = load_state()
    last_time = state.get(key, 0)
    if NOW - last_time < DEDUP_HOURS * 3600:
        return False
    # 标记已通知
    state[key] = NOW
    save_state(state)
    return True

# ── 通知 ──────────────────────────────────────────────────────────────

def notify(title, message):
    """macOS 桌面通知，转义特殊字符"""
    # 转义双引号和反斜杠
    msg_escaped = message.replace('\\', '\\\\').replace('"', '\\"')
    title_escaped = title.replace('\\', '\\\\').replace('"', '\\"')
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{msg_escaped}" with title "{title_escaped}" sound name "Pop"'
        ], timeout=5, capture_output=True)
        return True
    except Exception:
        return False

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")

# ── DuckDB 查询 ───────────────────────────────────────────────────────

def get_latest_date(db_path):
    """
    查询 DuckDB 数据库中最新的数据日期。
    按优先级尝试常见表/列组合，返回 (日期字符串, 表名) 或 None。
    """
    # (表名, 日期列) 优先级列表
    priority = [
        ("qt_dailyquote",     "TradingDay"),
        ("qt_performance",    "TradingDay"),
        ("qt_indexquote",     "tradingday"),
        ("MF_NETVALUE",       "TradingDay"),
        ("MF_FUNDNETVALUERE", "TRADINGDAY"),
        ("MF_MFNETVALUE",     "TRADINGDAY"),
        ("lc_balancesheetall","enddate"),
        ("lc_incomestatementall", "enddate"),
        ("lc_cashflowstatementall", "enddate"),
        ("LC_MAINDATANEW",    "EndDate"),
        ("lc_mainindexnew",   "EndDate"),
    ]

    try:
        import duckdb
        con = duckdb.connect(db_path, read_only=True)
        tables = {t[0] for t in con.execute(
            "SELECT table_name FROM duckdb_tables();"
        ).fetchall()}

        for table, column in priority:
            if table not in tables:
                continue
            try:
                result = con.execute(
                    f'SELECT MAX("{column}") FROM {table};'
                ).fetchone()
                if result and result[0]:
                    date_val = result[0]
                    if hasattr(date_val, "strftime"):
                        return date_val.strftime("%Y-%m-%d"), table
                    s = str(date_val)[:10]
                    if s and s != "None":
                        return s, table
            except Exception:
                continue
        con.close()
    except Exception as e:
        log(f"  DuckDB query error [{db_path}]: {e}")
    return None, None

# ══════════════════════════════════════════════════════════════════════
# 扫描 1: DuckDB 文件
# ══════════════════════════════════════════════════════════════════════

log("=== File watcher scan started ===")
notifications = []

for watch_path in DUCKDB_PATHS:
    if not os.path.isdir(watch_path):
        log(f"  Path not found: {watch_path}")
        continue

    path_label = os.path.basename(watch_path)
    db_files = sorted(glob.glob(os.path.join(watch_path, "*.duckdb")))

    # 取所有 db 文件的 mtime 中最新者作为整体新鲜度指标
    newest_db_mtime = max((os.path.getmtime(f) for f in db_files), default=0)
    path_age_days = int((NOW - newest_db_mtime) / 86400)

    if path_age_days <= DAYS_THRESHOLD:
        log(f"  [{path_label}] fresh ({path_age_days}d) — skip")
        continue

    # 过期: 查询每个 DB 的最新数据日期, 找出整体的最新值
    overall_latest_date = ""
    overall_latest_db = ""
    db_details = []

    for db_file in db_files:
        db_name = os.path.basename(db_file).replace(".duckdb", "")
        file_age = int((NOW - os.path.getmtime(db_file)) / 86400)
        latest_date, source_table = get_latest_date(db_file)

        if latest_date:
            db_details.append(f"{db_name}: {latest_date}")
            if not overall_latest_date or latest_date > overall_latest_date:
                overall_latest_date = latest_date
                overall_latest_db = db_name
        else:
            db_details.append(f"{db_name}: 无法读取日期")

    # 生成通知
    if overall_latest_date:
        msg = (
            f"目前【{path_label}】路径下的数据库"
            f"最新数据截止于【{overall_latest_date}】"
            f"（{path_age_days}天前更新），可以考虑更新一下了"
        )
    else:
        msg = (
            f"目前【{path_label}】路径下的数据库"
            f"已 {path_age_days} 天未更新，建议检查"
        )

    dedup_key = f"duckdb:{path_label}"
    log(f"  [{path_label}] {path_age_days}d stale → {msg[:80]}...")

    if should_notify(dedup_key):
        notifications.append(("🤖 秘书提醒 · 数据过期", msg))
    else:
        log(f"    (dedup: notified within {DEDUP_HOURS}h, skipped)")

# ══════════════════════════════════════════════════════════════════════
# 扫描 2: github_related 子文件夹
# ══════════════════════════════════════════════════════════════════════

if os.path.isdir(GITHUB_RELATED):
    newest_subdir_mtime = 0
    newest_subdir_name = ""

    for entry in os.listdir(GITHUB_RELATED):
        subpath = os.path.join(GITHUB_RELATED, entry)
        if not os.path.isdir(subpath) or entry.startswith("."):
            continue
        # 取子文件夹的最新文件 mtime
        sub_mtime = 0
        for root, dirs, files in os.walk(subpath):
            for f in files:
                try:
                    mt = os.path.getmtime(os.path.join(root, f))
                    if mt > sub_mtime:
                        sub_mtime = mt
                except OSError:
                    pass
        if sub_mtime > newest_subdir_mtime:
            newest_subdir_mtime = sub_mtime
            newest_subdir_name = entry

    gh_age_days = int((NOW - newest_subdir_mtime) / 86400) if newest_subdir_mtime else 999

    if gh_age_days > DAYS_THRESHOLD:
        msg = "超过半个月未检索github的新项目了，可以考虑学习一下了"
        dedup_key = "github_related"
        log(f"  [github_related] newest={newest_subdir_name} ({gh_age_days}d) → stale")

        if should_notify(dedup_key):
            notifications.append(("🤖 秘书提醒 · GitHub", msg))
        else:
            log(f"    (dedup: notified within {DEDUP_HOURS}h, skipped)")
    else:
        log(f"  [github_related] newest={newest_subdir_name} ({gh_age_days}d) — fresh")
else:
    log(f"  [github_related] path not found")

# ══════════════════════════════════════════════════════════════════════
# 发送通知
# ══════════════════════════════════════════════════════════════════════

if notifications:
    log(f"Sending {len(notifications)} notification(s)...")
    for title, msg in notifications:
        ok = notify(title, msg)
        log(f"  {'✅' if ok else '❌'} {title}: {msg[:80]}...")
else:
    log("No new notifications (all fresh or in cooldown)")

log("=== Scan complete ===\n")
