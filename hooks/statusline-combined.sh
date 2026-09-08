#!/bin/bash
# ============================================================
# statusline-combined.sh — 项目类型 + DeepSeek Token + 行情播报 + context-bar 桌面组件
#
# Claude Code 通过 stdin pipe JSON → 脚本输出 status line 文本
# 同时将数据喂给 context-bar（供 macOS 桌面小组件读取）
# ============================================================

# --- 项目类型三态行(与 market-ticker.sh 保持一致, 读状态文件) ---
ptype_line() {
    local state
    state=$(bash "$HOME/.claude/scripts/project-type.sh" get 2>/dev/null || true)
    case "$state" in
        complex) printf "\033[32m🔧 复杂任务\033[0m" ;;
        simple)  printf "\033[90m⚡ 普通\033[0m" ;;
        *)       printf "\033[33m⚠️ 待确认\033[0m" ;;
    esac
}

# --- DeepSeek 定价（USD/1M tokens，按实际 API 修改）---
DEEPSEEK_INPUT_PRICE=0.28
DEEPSEEK_OUTPUT_PRICE=0.42

# --- 行情缓存 ---
TICKER_FILE="$HOME/.cache/market-dash/ticker.txt"
NAV_LINE_FILE="$HOME/.cache/market-dash/nav_line.txt"

# --- 第 1 行：DeepSeek Token 追踪（从 CC status line JSON 读取）---
RAW=$(cat)

MODEL=$(echo "$RAW" | jq -r '.model.display_name // "DeepSeek"')
PCT=$(echo "$RAW" | jq -r '.context_window.used_percentage // 0')
PCT_INT=$(echo "$PCT" | cut -d. -f1)
IN_TOK=$(echo "$RAW" | jq -r '.context_window.total_input_tokens // 0')
OUT_TOK=$(echo "$RAW" | jq -r '.context_window.total_output_tokens // 0')
DURATION_MS=$(echo "$RAW" | jq -r '.cost.total_duration_ms // 0')
TOTAL_TOK=$((IN_TOK + OUT_TOK))

# --- DeepSeek 费用计算 ---
COST_USD=$(echo "scale=4; ($IN_TOK * $DEEPSEEK_INPUT_PRICE + $OUT_TOK * $DEEPSEEK_OUTPUT_PRICE) / 1000000" | bc)
if (( $(echo "$COST_USD < 0.01" | bc -l) )); then
    COST_FMT="\$0$(printf "%.4f" "$COST_USD")"
else
    COST_FMT=$(printf "\$%.3f" "$COST_USD")
fi

# --- 进度条 ---
FILLED=$((PCT_INT / 10))
[ $FILLED -gt 10 ] && FILLED=10
EMPTY=$((10 - FILLED))
printf -v FILL "%${FILLED}s"
printf -v PAD "%${EMPTY}s"
BAR="${FILL// /▓}${PAD// /░}"

# --- 阈值颜色 ---
if [ "$PCT_INT" -ge 90 ]; then
    BAR_COLOR='\033[31m'
elif [ "$PCT_INT" -ge 70 ]; then
    BAR_COLOR='\033[33m'
else
    BAR_COLOR='\033[32m'
fi
NC='\033[0m'

# --- 时长 ---
MINS=$((DURATION_MS / 60000))
SECS=$(((DURATION_MS % 60000) / 1000))

# --- token 千分位 ---
TOK_FMT=$(printf "%'d" $TOTAL_TOK 2>/dev/null || echo "$TOTAL_TOK")

# --- 输出项目类型行 + DeepSeek 行 ---
echo "$(ptype_line)"
printf "🐳 ${BAR_COLOR}%s${NC} %s%% | 📊 %s tok | 💰 %s | ⏱ %dm%02ds" \
    "$BAR" "$PCT_INT" "$TOK_FMT" "$COST_FMT" "$MINS" "$SECS"

# --- 第 2-3 行：行情播报（从缓存读）---
if [ -f "$TICKER_FILE" ]; then
    echo ""
    cat "$TICKER_FILE"
fi
if [ -f "$NAV_LINE_FILE" ]; then
    echo ""
    cat "$NAV_LINE_FILE"
fi

# --- 后台：喂数据给 context-bar（供桌面小组件使用）---
# context-bar 用其内置定价引擎，我们通过 ccusage.json 覆盖 DeepSeek 价格
(context-bar claude-statusline <<< "$RAW" > /dev/null 2>&1) &
disown 2>/dev/null
