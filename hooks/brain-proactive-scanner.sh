#!/usr/bin/env bash
# brain-proactive-scanner.sh — Proactive file system scanner
#
# Scans configured directories and checks for conditions that merit
# user attention. Writes suggestions to ~/.claudectl/brain/proactive-suggestions.json
# which session-briefing.sh reads and injects into new sessions.
#
# Scheduled via launchd. Each rule checks subfolder freshness against
# a configurable threshold and generates a suggestion when stale.
#
# Rules are defined in the RULES array below. Each entry:
#   rule_name|watch_path|threshold_seconds|message_template
# Template vars: {path}, {days}, {last_modified}

set -euo pipefail

SUGGESTIONS_FILE="$HOME/.claudectl/brain/proactive-suggestions.json"
SCAN_LOG="/tmp/brain-scanner.log"
TMP_DIR="${TMPDIR:-/tmp}/brain-scanner-$$"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

NOW=$(date +%s)
NOW_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SUGGESTION_COUNTER=0

# ── Config: Scan rules ──────────────────────────────────────────────
# Format: rule_name|watch_path|threshold_seconds|message_template
RULES=(
    "github_freshness|$HOME/Scholarship is a new sexy/github_related|604800|{path} 有 {days} 天没有活动了，很久没有检索 GitHub 的新项目了，是否需要运行一次？"
)

# ── Helpers ──────────────────────────────────────────────────────────

log_msg() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$SCAN_LOG"; }

emit_suggestion() {
    # $1 = rule_name, $2 = watch_path, $3 = age_days, $4 = last_seen_date, $5 = message
    local out_file="$TMP_DIR/sugg_$(printf '%04d' $SUGGESTION_COUNTER).json"
    SUGGESTION_COUNTER=$((SUGGESTION_COUNTER + 1))

    if command -v jq &>/dev/null; then
        jq -n \
            --arg rule "$1" \
            --arg watch_path "$2" \
            --argjson age_days "$3" \
            --arg last_seen "$4" \
            --arg message "$5" \
            --arg scanned_at "$NOW_ISO" \
            '{rule:$rule, watch_path:$watch_path, age_days:$age_days, last_seen:$last_seen, message:$message, scanned_at:$scanned_at}' \
            > "$out_file" 2>/dev/null
    fi
}

get_newest_mtime() {
    local dir="$1"
    [ -d "$dir" ] || { echo "0"; return; }
    # Use find + stat, take max, handle empty results
    local newest
    newest=$(find "$dir" -type f -exec stat -f '%m' {} \; 2>/dev/null | sort -rn 2>/dev/null | head -1)
    echo "${newest:-0}"
}

# ── Scan rule: subfolder_freshness ──────────────────────────────────

scan_subfolders() {
    local watch_path="$1"
    local threshold_sec="$2"
    local message_template="$3"

    [ -d "$watch_path" ] || { log_msg "path not found: $watch_path"; return; }

    for subdir in "$watch_path"/*/; do
        [ -d "$subdir" ] || continue
        local name=$(basename "$subdir")
        local mtime=$(get_newest_mtime "$subdir" | tr -d '[:space:]')
        [ -z "$mtime" ] || [ "$mtime" = "0" ] && continue

        local age_sec=$((NOW - mtime))
        local age_days=$((age_sec / 86400))
        [ "$age_sec" -le "$threshold_sec" ] && { log_msg "fresh: $name (${age_days}d)"; continue; }
        [ "$age_days" -le 0 ] && continue

        local msg="${message_template//\{path\}/$name}"
        msg="${msg//\{days\}/$age_days}"
        msg="${msg//\{last_modified\}/$(date -r "$mtime" '+%Y-%m-%d' 2>/dev/null || echo 'unknown')}"

        emit_suggestion "subfolder_freshness" "$watch_path/$name" "$age_days" \
            "$(date -r "$mtime" '+%Y-%m-%d' 2>/dev/null || echo 'unknown')" "$msg"

        log_msg "STALE: $name — ${age_days}d — suggestion generated"
    done
}

# ── Main ─────────────────────────────────────────────────────────────

log_msg "=== Scan started ==="

for rule_def in "${RULES[@]}"; do
    IFS='|' read -r rule_name watch_path threshold_sec message_template <<< "$rule_def"
    log_msg "Running rule: $rule_name on $watch_path (threshold: $((threshold_sec / 86400))d)"
    scan_subfolders "$watch_path" "$threshold_sec" "$message_template"
done

# ── Aggregate suggestions ────────────────────────────────────────────

if [ "$SUGGESTION_COUNTER" -gt 0 ]; then
    if command -v jq &>/dev/null; then
        jq -s '.' "$TMP_DIR"/sugg_*.json > "$SUGGESTIONS_FILE" 2>/dev/null || echo '[]' > "$SUGGESTIONS_FILE"
    else
        cat "$TMP_DIR"/sugg_*.json > "$SUGGESTIONS_FILE" 2>/dev/null || echo '[]' > "$SUGGESTIONS_FILE"
    fi
else
    echo '[]' > "$SUGGESTIONS_FILE"
fi

log_msg "=== Scan complete: $SUGGESTION_COUNTER suggestion(s) ==="
