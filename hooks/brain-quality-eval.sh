#!/usr/bin/env bash
# claudectl brain quality eval — automated weekly assessment
# Triggered by launchd timer: com.claudectl.brain-eval.plist
# Writes results to /tmp/claudectl-quality-report.txt
# session-briefing.sh reads this file to surface quality trends.

set -euo pipefail

REPORT_FILE="/tmp/claudectl-quality-report.txt"
DATE=$(date -Iseconds)

{
    echo "=== claudectl Brain Quality Report ==="
    echo "Timestamp: $DATE"
    echo ""

    # Check brain process
    if pgrep -f "claudectl --brain" >/dev/null 2>&1; then
        echo "Brain: RUNNING"
    else
        echo "Brain: STOPPED"
    fi

    echo ""

    # Run brain evaluation
    echo "--- Brain Eval ---"
    EVAL_OUT=$(claudectl --brain-eval 2>&1) || true
    if [ -n "$EVAL_OUT" ]; then
        echo "$EVAL_OUT"
    else
        echo "(not enough data for evaluation yet — need ≥50 decisions)"
    fi

    echo ""

    # Run scorecard
    echo "--- Scorecard ---"
    SCORE_OUT=$(claudectl --brain-stats scorecard 2>&1) || true
    if [ -n "$SCORE_OUT" ]; then
        echo "$SCORE_OUT"
    else
        echo "(not enough data for scorecard yet)"
    fi

    echo ""

    # Impact stats
    echo "--- Impact Stats ---"
    IMPACT_OUT=$(claudectl --brain-stats impact 2>&1) || true
    echo "$IMPACT_OUT"

    echo ""
    echo "=========================================="
} > "$REPORT_FILE" 2>/dev/null

# Also append a one-line summary for quick injection
SUMMARY=""
if [ -n "$EVAL_OUT" ] && ! echo "$EVAL_OUT" | grep -q "not enough"; then
    SUMMARY="Brain quality eval completed: see $REPORT_FILE"
else
    DECISIONS=$(echo "$IMPACT_OUT" | grep -o '[0-9]\+ decisions' | grep -o '[0-9]\+' || echo "0")
    SUMMARY="Brain decisions accumulated: ${DECISIONS}. Not enough for full eval yet (need ≥50)."
fi

echo "$SUMMARY"

exit 0
