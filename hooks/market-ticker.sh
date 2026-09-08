#!/bin/bash
# Claude Code statusline — 项目类型 + 三行行情播报
# Line 0: 项目类型三态(⚠️ 待确认黄 / 🔧 复杂任务绿 / ⚡ 普通灰, 读 ~/.claude/project-type/)
# Line 1: 上证/深证/创业板/科创50/伦敦金现
# Line 2: 价值100/自由现金流/优势成长/南方原油/中国海油
# Line 3: 中邮价值1号 估算净值 (60s 刷新)

TICKER_FILE="$HOME/.cache/market-dash/ticker.txt"
NAV_LINE_FILE="$HOME/.cache/market-dash/nav_line.txt"
PID_FILE="$HOME/.cache/market-dash/ticker.pid"
NAV_PID_FILE="$HOME/.cache/market-dash/nav_estimator.pid"
DAEMON_DIR="/Users/junye_shi/中邮资管/中邮金市/产品投后维护/产品净值/market-data"

# --- 项目类型三态行(读状态文件, 与 hook 判定联动) ---
ptype_line() {
    local state
    state=$(bash "$HOME/.claude/scripts/project-type.sh" get 2>/dev/null || true)
    case "$state" in
        complex) printf "\033[32m🔧 复杂任务\033[0m" ;;
        simple)  printf "\033[90m⚡ 普通\033[0m" ;;
        *)       printf "\033[33m⚠️ 待确认\033[0m" ;;
    esac
}

# 快速路径：缓存存在且新鲜（< 10 秒）
if [ -f "$TICKER_FILE" ]; then
    NOW=$(date +%s)
    FILE_MTIME=$(stat -f %m "$TICKER_FILE" 2>/dev/null || echo 0)
    if [ $((NOW - FILE_MTIME)) -lt 10 ]; then
        echo "$(ptype_line)"
        cat "$TICKER_FILE"
        if [ -f "$NAV_LINE_FILE" ]; then
            echo ""
            cat "$NAV_LINE_FILE"
        fi
        exit 0
    fi
fi

# 检查行情守护进程
daemon_alive=false
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    kill -0 "$PID" 2>/dev/null && daemon_alive=true
fi

# 需要启动？
if ! $daemon_alive; then
    cd "$DAEMON_DIR" && python3 -m src.ticker_daemon --daemon --interval 5 > /dev/null 2>&1 &
    disown 2>/dev/null
fi

# 检查 NAV 估算守护进程
nav_alive=false
if [ -f "$NAV_PID_FILE" ]; then
    NAV_PID=$(cat "$NAV_PID_FILE")
    kill -0 "$NAV_PID" 2>/dev/null && nav_alive=true
fi

if ! $nav_alive; then
    cd "$DAEMON_DIR" && /opt/anaconda3/bin/python3 -m src.nav_estimator --daemon > /dev/null 2>&1 &
    disown 2>/dev/null
fi

# 返回缓存
echo "$(ptype_line)"
if [ -f "$TICKER_FILE" ]; then
    cat "$TICKER_FILE"
    [ -f "$NAV_LINE_FILE" ] && cat "$NAV_LINE_FILE"
else
    echo "⏳ 行情加载中..."
    [ -f "$NAV_LINE_FILE" ] && cat "$NAV_LINE_FILE"
fi
