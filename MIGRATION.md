# JonOps Deployment & Migration Guide

Two scenarios covered:
1. **Fresh install** — Empty Hetzner box, starting from scratch
2. **Migration** — Existing project with files you want to keep

---

## Scenario 1: Fresh Install (Empty Server)

### Prerequisites

On your Hetzner box:
```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Install Docker Compose (if not included)
apt install docker-compose-plugin -y

# Verify
docker --version
docker compose version
```

### Deploy JonOps

```bash
# Clone the repo
git clone https://github.com/jonjonesai/templatized-jonops.git /opt/jonops
cd /opt/jonops

# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Run the initialization wizard
claude /init
# Answer ~15 questions about your business

# Set up credentials
cp .env.example .env
nano .env
# Fill in: ANTHROPIC_API_KEY, WP_*, AIRTABLE_*, REPLICATE_API, TINIFY_API, TELEGRAM_*

# Create Airtable tables
pip3 install pyairtable
python3 scripts/setup/create-airtable-tables.py
# Copy the output table IDs into .env

# Launch
docker compose up -d

# Verify it's running
docker compose logs -f
```

### Add Your Brand Assets (Optional)

```bash
# Upload logos, images, fonts
scp -r ./my-brand-assets/* root@your-server:/opt/jonops/assets/

# Or create them directly
nano /opt/jonops/assets/logos/logo.png
```

---

## Scenario 2: Migration (Existing Project)

You have a Hetzner box with an old/failed project. Some files are useful (brand assets, content, API keys). Here's how to migrate cleanly.

### Step 1: SSH In and Assess

```bash
ssh root@your-hetzner-ip

# See what's there
ls -la /opt/
ls -la /opt/old-project/  # or wherever your project lives

# Check if Docker containers are running
docker ps -a
```

### Step 2: Backup Useful Files

```bash
# Create backup directory
mkdir -p /root/backup-$(date +%Y%m%d)
cd /root/backup-$(date +%Y%m%d)

# Copy useful stuff from old project (adjust paths)
cp -r /opt/old-project/assets . 2>/dev/null
cp -r /opt/old-project/images . 2>/dev/null
cp -r /opt/old-project/uploads . 2>/dev/null
cp /opt/old-project/.env ./env-old.txt 2>/dev/null
cp /opt/old-project/MEMORY.md . 2>/dev/null
cp /opt/old-project/CLAUDE.md ./claude-old.md 2>/dev/null

# Any custom content you wrote
cp -r /opt/old-project/content . 2>/dev/null

# List what you backed up
echo "=== Backed up files ==="
ls -la
```

### Step 3: Stop Old Container

```bash
# Stop and remove old containers
cd /opt/old-project
docker compose down 2>/dev/null

# Or if using standalone docker
docker stop $(docker ps -q) 2>/dev/null

# Move old project out of the way (don't delete yet)
mv /opt/old-project /opt/old-project-archived-$(date +%Y%m%d)
```

### Step 4: Clone Fresh JonOps

```bash
# Clone
git clone https://github.com/jonjonesai/templatized-jonops.git /opt/jonops
cd /opt/jonops

# Install Claude Code if not present
which claude || npm install -g @anthropic-ai/claude-code
```

### Step 5: Run Init Wizard

```bash
claude /init
# Answer questions about your business
# This creates: CLAUDE.md, email-persona.md, MEMORY.md
```

### Step 6: Set Up .env (Reuse Old Keys)

```bash
cp .env.example .env

# Open old env for reference
cat /root/backup-*/env-old.txt

# Edit new .env and copy over any keys you already had
nano .env
```

**Required keys:**
```
ANTHROPIC_API_KEY=sk-ant-...
WP_URL=https://yourdomain.com
WP_USERNAME=...
WP_PASSWORD=...
AIRTABLE_API_KEY=pat_...
AIRTABLE_BASE_ID=app...
REPLICATE_API=r8_...
TINIFY_API=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

### Step 7: Set Up Airtable

```bash
pip3 install pyairtable
python3 scripts/setup/create-airtable-tables.py

# Copy the output table IDs into .env
nano .env
# Add all the AIRTABLE_*_TABLE=tbl... lines
```

### Step 8: Restore Your Brand Assets

```bash
# Copy backed up assets into new structure
cp -r /root/backup-*/assets/* /opt/jonops/assets/ 2>/dev/null
cp -r /root/backup-*/images/* /opt/jonops/assets/images/ 2>/dev/null

# Check what you have
ls -la /opt/jonops/assets/
```

### Step 9: Merge Useful Content from Old MEMORY.md

```bash
# View old memory
cat /root/backup-*/MEMORY.md

# If there's useful info, manually add to new MEMORY.md
nano /opt/jonops/MEMORY.md

# Add a section like:
# ## Migrated from Previous System
# - [useful learning 1]
# - [useful learning 2]
```

### Step 10: Launch

```bash
cd /opt/jonops
docker compose up -d

# Watch logs
docker compose logs -f

# Verify scheduler
docker compose exec jonops python scheduler.py --status
```

### Step 11: Test

```bash
# Run a simple skill to verify everything works
docker compose exec jonops claude "Run the daily-watchdog skill"

# Check Telegram - you should get a notification
```

### Step 12: Cleanup (After Verified Working)

```bash
# Once you're confident everything works (wait a few days)
rm -rf /opt/old-project-archived-*
rm -rf /root/backup-*
```

---

## What to Keep vs. Discard

| ✅ Keep | ❌ Discard |
|---------|-----------|
| Brand assets (logos, images) | Old broken scripts |
| API keys from old .env | Old CLAUDE.md |
| Written content | Old Docker configs |
| Useful MEMORY.md learnings | Old cron/scheduler setup |
| Product images | Half-built automation |
| Custom fonts | Old skill files |

---

## Troubleshooting

### Container won't start
```bash
docker compose logs jonops
# Look for missing env vars or syntax errors
```

### Claude command not found
```bash
npm install -g @anthropic-ai/claude-code
export PATH="$PATH:/usr/local/bin"
```

### Telegram not working
```bash
# Test manually
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  -d "text=Test from JonOps"
```

### Skills failing
```bash
# Check logs
docker compose exec jonops tail -f logs/scheduler.log

# Run skill manually with verbose output
docker compose exec jonops claude "Run the daily-watchdog skill"
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Logs | `docker compose logs -f` |
| Shell into container | `docker compose exec jonops bash` |
| Run skill manually | `docker compose exec jonops claude "Run the [skill] skill"` |
| Check schedule | `docker compose exec jonops python scheduler.py --status` |
| Restart | `docker compose restart` |
| Rebuild | `docker compose build --no-cache && docker compose up -d` |

---

*Last updated: April 2026*
