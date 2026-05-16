#!/usr/bin/env bash
# ============================================================
# JonOps — Claude OAuth Auth Canary
# ============================================================
# Long-running supervisord-managed loop. Once per day at 03:00
# WITA, invokes a real `claude --print` call to verify the OAuth
# refresh chain is healthy end-to-end. Alerts via Telegram on
# non-zero exit so a broken refresh chain is caught before the
# operator-facing slots start failing.
#
# This replaces the deleted refresh_token_if_needed() shim in
# scheduler.py and the preflight block in cron-dispatcher.sh.
# Real slots auto-refresh on use; the canary just catches the
# pathological case where refresh is permanently broken.
# ============================================================

set -uo pipefail

export HOME=/home/agent
export PATH="/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin"

PROJECT_DIR=/home/agent/project
LOG_FILE="$PROJECT_DIR/logs/auth-canary.log"
mkdir -p "$(dirname "$LOG_FILE")"

if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.env"
    set +a
fi

BRAND="${PROJECT_NAME:-unknown}"

log() {
    echo "[$(TZ=Asia/Makassar date '+%Y-%m-%d %H:%M:%S WITA')] $1" >> "$LOG_FILE"
}

sleep_until_next_canary() {
    local now_secs target_secs sleep_secs
    now_secs=$(TZ=Asia/Makassar date +%s)
    target_secs=$(TZ=Asia/Makassar date -d 'today 03:00' +%s)
    if [ "$now_secs" -ge "$target_secs" ]; then
        target_secs=$(TZ=Asia/Makassar date -d 'tomorrow 03:00' +%s)
    fi
    sleep_secs=$((target_secs - now_secs))
    log "Sleeping ${sleep_secs}s until next 03:00 WITA canary"
    sleep "$sleep_secs"
}

run_canary() {
    log "Running auth canary"
    local output exit_code
    output=$(claude --print --dangerously-skip-permissions -p "respond with the single word: ok" < /dev/null 2>&1)
    exit_code=$?
    if [ "$exit_code" -eq 0 ]; then
        log "Canary OK"
    else
        log "Canary FAILED (exit $exit_code): $output"
        bash "$PROJECT_DIR/telegram-alert.sh" "⚠️ AUTH CANARY FAILURE — $BRAND — claude --print exited $exit_code. Run: claude login on container jonops-$BRAND" 2>/dev/null || true
    fi
}

# Initial run at startup seeds health, then daily at 03:00 WITA.
run_canary
while true; do
    sleep_until_next_canary
    run_canary
done
