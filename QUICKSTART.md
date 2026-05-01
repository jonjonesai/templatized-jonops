# JonOps Quick Start

Get your autonomous marketing agent running in 15 minutes.

## Prerequisites

- Linux server (Ubuntu 22.04+ recommended) with Docker installed
- API keys ready: Anthropic, WordPress, Airtable, Replicate, Tinify

## Steps

```bash
# 1. Clone
git clone https://github.com/jonjonesai/templatized-jonops.git /opt/jonops
cd /opt/jonops

# 2. Initialize (answer ~15 questions about your business)
npx @anthropic-ai/claude-code /init

# 3. Set up credentials
cp .env.example .env
nano .env  # Fill in your API keys

# 4. Create Airtable tables
pip3 install pyairtable
python3 scripts/setup/create-airtable-tables.py
# Copy the output table IDs into .env

# 5. Fix volume permissions (chown to UID 1001:jonops-shared so the container can write)
sudo bash scripts/setup/fix-perms.sh

# 6. Launch
docker compose up -d

# 7. Verify
docker compose logs -f
```

## Minimum Required API Keys

| Service | Get it at | Purpose |
|---------|-----------|---------|
| Anthropic | [console.anthropic.com](https://console.anthropic.com) | Powers the AI agent |
| WordPress | Your WP Admin → Users → Application Passwords | Publish content |
| Airtable | [airtable.com/create/tokens](https://airtable.com/create/tokens) | Data storage |
| Replicate | [replicate.com/account](https://replicate.com/account) | AI images |
| Tinify | [tinypng.com/developers](https://tinypng.com/developers) | Compress images |
| Telegram | [@BotFather](https://t.me/botfather) | Notifications + chat |

## Test It

```bash
# Check scheduler status
docker compose exec jonops python scheduler.py --status

# Run a skill manually
docker compose exec jonops claude "Run the daily-watchdog skill"

# Chat with your agent via Telegram
# Just message your bot!
```

## Troubleshooting

**Container won't start:** Check `docker compose logs` for errors. Usually a missing env var, or a `PermissionError` writing logs/PID — re-run `sudo bash scripts/setup/fix-perms.sh`.

**Skills failing:** Check `logs/scheduler.log` inside the container.

**Telegram not working:** Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are correct.

---

For detailed setup, see [SETUP.md](SETUP.md).
