#!/usr/bin/env bash
# brain-outcome-reaper.sh — Match pending outcomes to decisions, compute accuracy
#
# Reads pending-outcomes/ and decisions.jsonl, matches them by
# (tool, command, approximate timestamp), computes accuracy metrics,
# and archives processed outcomes to outcomes/.
#
# Scheduled via launchd (every 15 min) + Stop hook.
# Idempotent — safe to run multiple times.

set -euo pipefail

BRAIN_DIR="$HOME/.claudectl/brain"
PENDING_DIR="$BRAIN_DIR/pending-outcomes"
OUTCOMES_DIR="$BRAIN_DIR/outcomes"
ORPHANED_DIR="$BRAIN_DIR/outcomes-orphaned"
DECISIONS_LOG="$BRAIN_DIR/decisions.jsonl"
STATS_FILE="/tmp/brain-reaper-stats.json"
LOG_FILE="/tmp/brain-reaper.log"

mkdir -p "$OUTCOMES_DIR" "$ORPHANED_DIR"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# ── Load decisions into lookup ───────────────────────────────────────
# Build a map from (tool, command_prefix, approximate_ts) -> decision

DECISION_MAP=""
if [ -f "$DECISIONS_LOG" ] && [ -s "$DECISIONS_LOG" ]; then
    if command -v jq &>/dev/null; then
        DECISION_MAP=$(jq -s '
            map({
                key: (.tool + "::" + (.command // "" | split(" ")[0:2] | join(" "))),
                decision_id: .decision_id,
                tool: .tool,
                command: .command,
                action: .action,
                confidence: .confidence,
                timestamp: .timestamp
            })
        ' "$DECISIONS_LOG" 2>/dev/null || echo "[]")
    fi
fi

# ── Process pending outcomes ─────────────────────────────────────────

MATCHED=0
ORPHANED=0
ERRORS=0
TOTAL=0
APPROVE_CORRECT=0
APPROVE_WRONG=0
DENY_COUNT=0

# Process each pending outcome
for po_file in "$PENDING_DIR"/po_*.json; do
    [ -f "$po_file" ] || continue
    TOTAL=$((TOTAL + 1))

    # Parse the pending outcome
    if command -v jq &>/dev/null; then
        po_tool=$(jq -r '.tool // "unknown"' "$po_file" 2>/dev/null)
        po_cmd=$(jq -r '.command // ""' "$po_file" 2>/dev/null)
        po_exit=$(jq -r '.exit_code // 0' "$po_file" 2>/dev/null)
        po_ts=$(jq -r '.ts // 0' "$po_file" 2>/dev/null)
        po_stderr=$(jq -r '.stderr_tail // ""' "$po_file" 2>/dev/null)
    else
        po_tool=$(sed -n 's/.*"tool" *: *"\([^"]*\)".*/\1/p' "$po_file")
        po_cmd=$(sed -n 's/.*"command" *: *"\([^"]*\)".*/\1/p' "$po_file")
        po_exit=$(sed -n 's/.*"exit_code" *: *\([0-9-]*\).*/\1/p' "$po_file")
        po_ts=$(sed -n 's/.*"ts" *: *\([0-9]*\).*/\1/p' "$po_file")
        po_stderr=""
    fi

    # Try to find matching decision
    # Match by: same tool + command prefix overlap
    matched_decision=""
    cmd_prefix=$(echo "$po_cmd" | cut -d' ' -f1-2 2>/dev/null || echo "")

    if [ -n "$DECISION_MAP" ] && [ "$DECISION_MAP" != "[]" ]; then
        matched_decision=$(echo "$DECISION_MAP" | jq -r \
            --arg tool "$po_tool" \
            --arg prefix "$cmd_prefix" \
            'first(.[] | select(.tool == $tool and (.command | startswith($prefix)))) | @base64' \
            2>/dev/null)
    fi

    # Build resolved outcome
    if [ -n "$matched_decision" ]; then
        MATCHED=$((MATCHED + 1))

        # Decode decision
        dec_json=$(echo "$matched_decision" | base64 -d 2>/dev/null || echo "{}")
        dec_action=$(echo "$dec_json" | jq -r '.action // "unknown"' 2>/dev/null)
        dec_id=$(echo "$dec_json" | jq -r '.decision_id // "unknown"' 2>/dev/null)
        dec_conf=$(echo "$dec_json" | jq -r '.confidence // 0' 2>/dev/null)

        # Compute accuracy
        if [ "$dec_action" = "approve" ]; then
            if [ "$po_exit" = "0" ]; then
                APPROVE_CORRECT=$((APPROVE_CORRECT + 1))
            else
                APPROVE_WRONG=$((APPROVE_WRONG + 1))
            fi
        elif [ "$dec_action" = "deny" ]; then
            DENY_COUNT=$((DENY_COUNT + 1))
        fi

        # Write resolved outcome
        if command -v jq &>/dev/null; then
            jq -n \
                --arg decision_id "$dec_id" \
                --arg brain_action "$dec_action" \
                --argjson brain_confidence "$dec_conf" \
                --arg tool "$po_tool" \
                --arg command "$po_cmd" \
                --argjson exit_code "$po_exit" \
                --arg stderr_tail "$po_stderr" \
                --argjson ts "$po_ts" \
                --arg matched_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
                '{
                    decision_id: $decision_id,
                    brain_action: $brain_action,
                    brain_confidence: $brain_confidence,
                    tool: $tool,
                    command: $command,
                    exit_code: $exit_code,
                    stderr_tail: $stderr_tail,
                    ts: $ts,
                    matched_at: $matched_at
                }' > "$OUTCOMES_DIR/resolved_${dec_id}.json" 2>/dev/null
        fi
    else
        # Orphan: no matching decision found
        # Check if older than 24h, then archive
        age_sec=$(( $(date +%s) - po_ts ))
        if [ "$age_sec" -gt 86400 ]; then
            cp "$po_file" "$ORPHANED_DIR/$(basename "$po_file")" 2>/dev/null || true
            ORPHANED=$((ORPHANED + 1))
        fi
    fi

    # Remove processed pending outcome
    rm -f "$po_file"
done

# ── Generate stats ───────────────────────────────────────────────────

if command -v jq &>/dev/null; then
    total_decisions=$(wc -l < "$DECISIONS_LOG" 2>/dev/null | tr -d ' ' || echo 0)
    jq -n \
        --argjson total_pending "$TOTAL" \
        --argjson matched "$MATCHED" \
        --argjson orphaned "$ORPHANED" \
        --argjson errors "$ERRORS" \
        --argjson approve_correct "$APPROVE_CORRECT" \
        --argjson approve_wrong "$APPROVE_WRONG" \
        --argjson deny_count "$DENY_COUNT" \
        --argjson total_decisions "$total_decisions" \
        --arg reaped_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --arg pending_dir_count "$(ls "$PENDING_DIR" 2>/dev/null | wc -l | tr -d ' ')" \
        '{
            total_pending_processed: $total_pending,
            matched_to_decision: $matched,
            orphaned_24h: $orphaned,
            errors: $errors,
            accuracy: {
                approve_correct: $approve_correct,
                approve_wrong: $approve_wrong,
                deny_count: $deny_count,
                approve_accuracy: (if ($approve_correct + $approve_wrong) > 0 then
                    ($approve_correct / ($approve_correct + $approve_wrong) * 100 | floor) / 100
                else null end)
            },
            total_decisions: $total_decisions,
            remaining_pending: $pending_dir_count,
            reaped_at: $reaped_at
        }' > "$STATS_FILE" 2>/dev/null
fi

log_msg "Reaped: total=$TOTAL matched=$MATCHED orphaned=$ORPHANED errors=$ERRORS"
log_msg "Accuracy: approve_correct=$APPROVE_CORRECT approve_wrong=$APPROVE_WRONG"
