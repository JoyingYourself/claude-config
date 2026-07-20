#!/usr/bin/env bash
# brain-stats-local.sh — Read claudectl decisions.jsonl and output stats.
# Bridge for claudectl v0.64.0 where --brain-stats reads from an internal
# store that isn't populated by hook-based decisions yet.
# Once upstream reconciles hook_events -> decisions, this can be retired.

set -euo pipefail

DECISIONS_LOG="$HOME/.claudectl/brain/decisions.jsonl"

if [ ! -f "$DECISIONS_LOG" ]; then
    echo "0 decisions (no log file yet)"
    exit 0
fi

# Count decisions using jq if available, otherwise grep
if command -v jq &>/dev/null; then
    TOTAL=$(jq -s 'length' "$DECISIONS_LOG" 2>/dev/null || echo 0)
    APPROVE=$(jq -s '[.[] | select(.action == "approve")] | length' "$DECISIONS_LOG" 2>/dev/null || echo 0)
    DENY=$(jq -s '[.[] | select(.action == "deny")] | length' "$DECISIONS_LOG" 2>/dev/null || echo 0)
    ASK=$(jq -s '[.[] | select(.action == "ask")] | length' "$DECISIONS_LOG" 2>/dev/null || echo 0)
    AVG_CONF=$(jq -s '[.[] | .confidence] | add / length * 100 | floor / 100' "$DECISIONS_LOG" 2>/dev/null || echo "0")
    LATEST=$(jq -s 'max_by(.timestamp) | .timestamp' "$DECISIONS_LOG" 2>/dev/null || echo "unknown")
    BRAIN_SRC=$(jq -s '[.[] | select(.source == "brain")] | length' "$DECISIONS_LOG" 2>/dev/null || echo 0)
    FEWSHOT=$(jq -s 'max_by(.timestamp) | .few_shot_count // 0' "$DECISIONS_LOG" 2>/dev/null || echo 0)
    PROJECTS=$(jq -s '[.[] | .project] | unique | join(", ")' "$DECISIONS_LOG" 2>/dev/null || echo "unknown")
    # Per-tool breakdown
    TOOLS=$(jq -s 'group_by(.tool) | map({tool: .[0].tool, count: length})' "$DECISIONS_LOG" 2>/dev/null || echo "[]")
else
    TOTAL=$(wc -l < "$DECISIONS_LOG" | tr -d ' ')
    APPROVE=$(grep -c '"action":"approve"' "$DECISIONS_LOG" 2>/dev/null || echo 0)
    DENY=$(grep -c '"action":"deny"' "$DECISIONS_LOG" 2>/dev/null || echo 0)
    ASK=$(grep -c '"action":"ask"' "$DECISIONS_LOG" 2>/dev/null || echo 0)
    AVG_CONF="N/A (install jq)"
    LATEST="N/A (install jq)"
    BRAIN_SRC="N/A (install jq)"
    FEWSHOT="N/A (install jq)"
    PROJECTS="N/A (install jq)"
    TOOLS="N/A (install jq)"
fi

# Output
echo "Brain Decision Stats (local decisions.jsonl)"
echo "============================================"
echo "  Total decisions:    $TOTAL"
echo "  Approve:            $APPROVE"
echo "  Deny:               $DENY"
echo "  Ask/Other:          $ASK"
echo "  Brain-sourced:      $BRAIN_SRC"
echo "  Avg confidence:     $AVG_CONF"
echo "  Few-shot count:     $FEWSHOT (latest query)"
echo "  Latest:             $LATEST"
echo "  Projects:           $PROJECTS"
if [ "$TOOLS" != "N/A (install jq)" ] && [ "$TOOLS" != "[]" ]; then
    echo "  By tool:"
    echo "$TOOLS" | jq -r '.[] | "    \(.tool): \(.count)"' 2>/dev/null || true
fi

# For CLAUDE.md inline display
echo ""
echo "SHORT: ${TOTAL} decisions · ${APPROVE} approved · ${DENY} denied"

# Check hook_events count for pipeline health
HOOK_EVENTS=0
if [ -f "$HOME/.claudectl/coord/coord.db" ] && command -v sqlite3 &>/dev/null; then
    HOOK_EVENTS=$(sqlite3 "$HOME/.claudectl/coord/coord.db" "SELECT COUNT(*) FROM hook_events;" 2>/dev/null || echo 0)
fi
echo "  Hook events:        $HOOK_EVENTS (coord.db)"

# Check pending outcomes
PENDING=0
if [ -d "$HOME/.claudectl/brain/pending-outcomes" ]; then
    PENDING=$(ls "$HOME/.claudectl/brain/pending-outcomes" 2>/dev/null | wc -l | tr -d ' ')
fi
echo "  Pending outcomes:   $PENDING"
