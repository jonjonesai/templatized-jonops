#!/bin/bash
# ============================================================
# JonOps — Cron Dispatcher
# ============================================================
# Called by crontab every 3 hours. Determines the current task
# from schedule.json and invokes Claude Code to execute it.
#
# Usage:
#   ./cron-dispatcher.sh              # Auto-detect task from schedule
#   ./cron-dispatcher.sh --slot 00:00 # Force a specific time slot
# ============================================================

set -euo pipefail

export HOME=/home/agent
export PATH="/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/home/agent/project/logs"
LOCK_DIR="/home/agent/project/logs/locks"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$LOCK_DIR"

# Source project .env so child processes get API keys
# (ANTHROPIC_API_KEY may be set here as a fallback for OAuth)
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Timestamp for logs
TIMESTAMP=$(TZ='Asia/Makassar' date '+%Y-%m-%d_%H-%M')
WITA_TIME=$(TZ='Asia/Makassar' date '+%H:%M')
WITA_DATE=$(TZ='Asia/Makassar' date '+%Y-%m-%d')

echo "[$TIMESTAMP] Cron dispatcher starting (WITA: $WITA_TIME)"

# Determine current task
SLOT_ARGS=""
if [ "${1:-}" = "--slot" ] && [ -n "${2:-}" ]; then
    SLOT_ARGS="--slot $2"
    echo "  Forcing slot: $2"
fi

TASK_JSON=$(python3 "$SCRIPT_DIR/get-current-task.py" $SLOT_ARGS 2>/dev/null) || {
    echo "[$TIMESTAMP] No task scheduled for this slot. Exiting."
    exit 0
}

TASK_NAME=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['task'])")
SKILL_FILE=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['skill'])")
DESCRIPTION=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['description'])")

echo "[$TIMESTAMP] Task: $TASK_NAME"
echo "[$TIMESTAMP] Skill: $SKILL_FILE"
echo "[$TIMESTAMP] Description: $DESCRIPTION"

# ---------------------------------------------------------------
# Slot lock — prevent duplicate execution
# ---------------------------------------------------------------
# Both scheduler.py and host cron may dispatch the same slot.
# The lock file ensures only the FIRST dispatcher to arrive runs.
SLOT_SAFE=$(echo "$WITA_TIME" | tr ':' '-')
LOCK_FILE="$LOCK_DIR/${WITA_DATE}_${SLOT_SAFE}_${TASK_NAME}.lock"

if [ -f "$LOCK_FILE" ]; then
    echo "[$TIMESTAMP] SKIPPED: Lock file exists — task already running/completed for this slot."
    echo "[$TIMESTAMP] Lock: $LOCK_FILE"
    exit 0
fi

# Create lock file (atomic — first writer wins)
echo "$$|$TIMESTAMP" > "$LOCK_FILE"

# Clean up stale lock files from previous days
find "$LOCK_DIR" -name "*.lock" -not -name "${WITA_DATE}*" -delete 2>/dev/null || true

SKILL_PATH="/home/agent/project/.claude/skills/$SKILL_FILE"
LOG_FILE="$LOG_DIR/${TIMESTAMP}_${TASK_NAME}.log"

# Verify skill file exists
if [ ! -f "$SKILL_PATH" ]; then
    echo "[$TIMESTAMP] ERROR: Skill file not found: $SKILL_PATH"
    exit 1
fi

# ---------------------------------------------------------------
# Asana inbox check — injected into the 11:00 email slot daily
# Uses ASANA_INBOX_SECTION_GID and ASANA_DONE_SECTION_GID from .env
# ---------------------------------------------------------------
ASANA_INBOX_INSTRUCTION=""
if [ "$WITA_TIME" = "11:00" ] || [ "$WITA_TIME" = "10:58" ] || [ "$WITA_TIME" = "10:59" ] || [ "$WITA_TIME" = "11:01" ] || [ "$WITA_TIME" = "11:02" ]; then
    # Only inject if Asana env vars are configured
    if [ -n "${ASANA_INBOX_SECTION_GID:-}" ] && [ -n "${ASANA_DONE_SECTION_GID:-}" ]; then
        ASANA_INBOX_INSTRUCTION="
ADDITIONAL TASK — ASANA INBOX CHECK (do this BEFORE the email check):
Before starting the email check, check the Asana inbox section (section GID: ${ASANA_INBOX_SECTION_GID})
for any ad-hoc tasks from the operator. Use curl with the ASANA_API_KEY from .env:
  curl -s -H 'Authorization: Bearer '\$(printenv ASANA_API_KEY) \\
    'https://app.asana.com/api/1.0/tasks?section=${ASANA_INBOX_SECTION_GID}&opt_fields=name,notes,assignee,due_on,completed'
If there are any incomplete tasks in the inbox:
1. Read the task details
2. Execute the task if it's something you can do autonomously (content creation, social posts, research, etc.)
3. Move completed tasks to the Done section (GID: ${ASANA_DONE_SECTION_GID}) using:
   curl -s -X POST -H 'Authorization: Bearer '\$(printenv ASANA_API_KEY) -H 'Content-Type: application/json' \\
     -d '{\"data\":{\"task\":\"TASK_GID\",\"section\":\"${ASANA_DONE_SECTION_GID}\"}}' \\
     'https://app.asana.com/api/1.0/sections/${ASANA_DONE_SECTION_GID}/addTask'
4. If a task requires operator input or is beyond your capabilities, leave it in inbox and add a comment
After the Asana check, proceed with the email check as normal.
"
    fi
fi

# ---------------------------------------------------------------
# Task-specific overrides — injected based on task name
# ---------------------------------------------------------------
# Task-specific overrides can be injected here if needed
# To add overrides: create a file at /home/agent/project/overrides/${TASK_NAME}.md
# and the agent will read it before executing the skill
TASK_OVERRIDES=""
OVERRIDE_FILE="/home/agent/project/overrides/${TASK_NAME}.md"
if [ -f "$OVERRIDE_FILE" ]; then
    TASK_OVERRIDES="
IMPORTANT — READ OVERRIDE FILE FIRST:
Read the file at $OVERRIDE_FILE BEFORE reading the main skill file.
The overrides in that file take priority over the default skill instructions.
"
fi

# Build the instruction for Claude
INSTRUCTION="You are the JonOps autonomous agent. Execute the following task NOW.

TASK: $DESCRIPTION
TIME SLOT: $WITA_TIME WITA
DATE: $(TZ='Asia/Makassar' date '+%Y-%m-%d')
$ASANA_INBOX_INSTRUCTION$TASK_OVERRIDES
Read the skill file at $SKILL_PATH and execute the COMPLETE pipeline described in it.
Follow every step. Do not skip steps. Do not ask for confirmation — execute autonomously.

IMPORTANT RULES:
- Write content for TODAY only — never batch ahead
- All posts must use status: publish — never draft or future
- Always generate featured images before publishing
- Log completed work to Asana
- Update observations.md when done

Start by reading the skill file, then execute."

echo "[$TIMESTAMP] Invoking Claude Code..."
echo "[$TIMESTAMP] Log file: $LOG_FILE"

# Capture CLAUDECODE value BEFORE unsetting (for diagnostics)
CLAUDECODE_WAS="${CLAUDECODE:-UNSET}"

# Prevent "nested session" error when scheduler.py is restarted from
# inside an interactive Claude session (inherits CLAUDECODE env var)
unset CLAUDECODE

# ---------------------------------------------------------------
# Use real HOME so claude can use .credentials.json refresh token.
# The refresh token (sk-ant-ort01-*) auto-renews the access token.
# CLAUDE_CODE_OAUTH_TOKEN in .env is a short-lived access token
# only — no refresh mechanism. Letting claude use ~/.claude/
# .credentials.json is the correct approach for long-running cron.
# ---------------------------------------------------------------
# (Clean HOME approach removed 2026-03-14 — was preventing token refresh)

# ---------------------------------------------------------------
# Pre-flight auth check — fail fast instead of hanging for 60min
# Check OAuth token expiry from credentials file. If token is
# expired OR will expire within 2 hours, proactively refresh it.
# If no ANTHROPIC_API_KEY fallback, abort early with Telegram alert.
#
# Why 2-hour buffer: Access tokens last ~24h. Some tasks run up to
# 90 minutes. Refreshing early prevents mid-task expiry and avoids
# the window where a token expires between scheduled tasks.
# ---------------------------------------------------------------
CREDS_FILE="$HOME/.claude/.credentials.json"
AUTH_OK=true
BUFFER_MS=7200000  # 2 hours in milliseconds

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    # API key set — no expiry concern
    :
elif [ -f "$CREDS_FILE" ]; then
    EXPIRES_AT=$(python3 -c "
import json, sys, time
try:
    d = json.load(open('$CREDS_FILE'))
    exp = d.get('claudeAiOauth', {}).get('expiresAt', 0)
    print(int(exp))
except: print(0)
" 2>/dev/null)
    NOW_MS=$(python3 -c "import time; print(int(time.time() * 1000))")
    THRESHOLD=$((NOW_MS + BUFFER_MS))
    if [ "$EXPIRES_AT" -gt 0 ] && [ "$THRESHOLD" -gt "$EXPIRES_AT" ]; then
        # Token expired or expiring within 2h — proactively refresh
        # (a real API call via `claude --print -p ping` triggers the refresh flow;
        #  `claude --version` does NOT — it's metadata-only and never hits the API)
        if claude --print -p ping < /dev/null > /dev/null 2>&1; then
            # Re-read expiry after refresh attempt
            EXPIRES_AT=$(python3 -c "
import json
d = json.load(open('$CREDS_FILE'))
print(int(d.get('claudeAiOauth', {}).get('expiresAt', 0)))
" 2>/dev/null)
            if [ "$NOW_MS" -gt "$EXPIRES_AT" ]; then
                AUTH_OK=false
            fi
        else
            AUTH_OK=false
        fi
    fi
else
    AUTH_OK=false
fi

if [ "$AUTH_OK" = "false" ]; then
    {
        echo "========================================================"
        echo "DISPATCH: $TASK_NAME | $WITA_DATE $WITA_TIME WITA"
        echo "AUTH CHECK FAILED — Claude OAuth token expired and refresh failed."
        echo "Re-authenticate: claude login"
        echo "========================================================"
    } > "$LOG_FILE"
    echo "[$TIMESTAMP] ABORTED: Claude auth check failed. See $LOG_FILE"
    bash /home/agent/project/telegram-alert.sh "AUTH FAILURE — $TASK_NAME skipped. OAuth token expired. Run: claude login" 2>/dev/null || true
    exit 1
fi

# Write diagnostic header directly to the task log file
{
    echo "========================================================"
    echo "DISPATCH: $TASK_NAME | $WITA_DATE $WITA_TIME WITA"
    echo "Skill: $SKILL_PATH"
    echo "Claude: $(which claude 2>/dev/null || echo 'NOT FOUND') $(claude --version 2>&1 | head -1 || echo 'unknown')"
    echo "CLAUDECODE_WAS: $CLAUDECODE_WAS"
    echo "PID: $$"
    echo "========================================================"
} > "$LOG_FILE"

# Invoke Claude Code in non-interactive mode (append to log file)
# --print outputs the full conversation to stdout
# Disable set -e so we capture the exit code even on failure
set +e
claude --print --dangerously-skip-permissions -p "$INSTRUCTION" < /dev/null >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

# Write exit footer to task log
{
    echo ""
    echo "========================================================"
    echo "EXIT CODE: $EXIT_CODE | $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "========================================================"
} >> "$LOG_FILE"

echo "[$TIMESTAMP] Claude exited with code: $EXIT_CODE"
echo "[$TIMESTAMP] Task complete: $TASK_NAME"
echo "[$TIMESTAMP] Full log: $LOG_FILE"
