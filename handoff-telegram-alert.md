# Telegram Alert System — Handoff Brief

**Project:** JonOps Template | **Status:** Fully implemented & tested

## What It Is
A lightweight Telegram notification system that pings the operator after every autonomous skill execution (cron job). Tells them what ran, whether it succeeded/failed/skipped, and a one-line summary.

## Components

### 1. Script: `/home/agent/project/telegram-alert.sh`
- Simple bash wrapper around the Telegram Bot API `sendMessage` endpoint
- Accepts a single string argument (the message)
- Supports HTML parse mode, retries 3x on failure, 10s timeout
- Requires env vars to be set; skips gracefully if missing

### 2. Env vars (injected via Docker):
- `TELEGRAM_BOT_TOKEN` — Your Telegram bot's token (from @BotFather)
- `TELEGRAM_CHAT_ID` — Your personal chat ID

### 3. Integration into skills
All skill files in `.claude/skills/*.md` include 3 Telegram alert calls each:
- `✅ skill-name — success summary`
- `❌ skill-name — failure details`
- `⚠️ skill-name — skip reason`

The alert fires as the **final action** before the `SKILL_RESULT` output line.

## Setup (New Installation)

1. **Create a Telegram bot:**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Send `/newbot` and follow prompts
   - Copy the bot token

2. **Get your chat ID:**
   - Start a chat with your new bot (send any message)
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find your `chat.id` in the response

3. **Add env vars** to your `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

4. **Restart container:**
   ```bash
   docker compose up -d --force-recreate
   ```

## How to Use in Skills

At the end of every skill, before SKILL_RESULT:
```bash
bash /home/agent/project/telegram-alert.sh "✅ skill-name — summary"
```
Include fail/skip variants where applicable:
```bash
bash /home/agent/project/telegram-alert.sh "❌ skill-name — error details"
bash /home/agent/project/telegram-alert.sh "⚠️ skill-name — skip reason"
```

## Multi-Project Setup (Optional)

If running multiple JonOps instances, you can differentiate alerts by prefix:
- Project A: `✅ [PROJ-A] skill-name — summary`
- Project B: `✅ [PROJ-B] skill-name — summary`

Same bot + chat ID works for all projects. The prefix helps identify which project sent the alert.

## Design Decisions
- **Env-var only** — Script requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID; skips gracefully if unset
- **HTML parse mode** — Allows bold/links in future if needed, but current messages are plain text with emojis
- **One-way alerts only** — Operator can't reply to trigger actions (monitoring only)
- **Graceful degradation** — If env vars missing, skill continues without alerts

## Troubleshooting

**Alerts not arriving:**
1. Verify env vars are set: `env | grep TELEGRAM`
2. Test manually: `bash /home/agent/project/telegram-alert.sh "Test message"`
3. Ensure you started a chat with your bot first
4. Check bot token and chat ID are correct
