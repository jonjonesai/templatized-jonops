#!/usr/bin/env bash
# telegram-alert.sh — Send alert messages to operator via Telegram
#
# Usage:
#   bash /home/agent/project/telegram-alert.sh "✅ skill-name — summary"
#   bash /home/agent/project/telegram-alert.sh "⚠️ skill-name — warning message"
#   bash /home/agent/project/telegram-alert.sh "❌ skill-name — failure details"
#
# Env vars required: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
# Skips gracefully if env vars not set.

set -euo pipefail

MESSAGE="${1:-}"

if [[ -z "$MESSAGE" ]]; then
  echo '{"error":"No message provided. Usage: telegram-alert.sh \"message\""}' >&2
  exit 1
fi

# Credentials — from Docker-injected env vars only
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"

if [[ -z "$BOT_TOKEN" || -z "$CHAT_ID" ]]; then
  echo "WARN: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Skipping alert." >&2
  exit 0
fi

# Send message via Telegram Bot API
RESPONSE=$(curl -s --retry 3 --retry-delay 2 --max-time 10 \
  -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=${MESSAGE}" \
  -d "parse_mode=HTML" \
  -d "disable_web_page_preview=true" 2>&1)

# Check response
OK=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('ok',False))" 2>/dev/null || echo "False")

if [[ "$OK" == "True" ]]; then
  echo "Telegram alert sent."
else
  echo "Telegram alert FAILED: ${RESPONSE}" >&2
  exit 1
fi
