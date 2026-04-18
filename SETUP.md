# JonOps Setup Guide

This guide walks you through setting up JonOps for your business. By the end, you'll have an autonomous marketing agent running on your server.

**Estimated time:** 30-60 minutes

---

## Prerequisites

Before starting, make sure you have:

- [ ] A Linux server (VPS) with Docker and Docker Compose installed
- [ ] Claude Code CLI installed on the server
- [ ] A WordPress website (if using content features)
- [ ] An Airtable account (free tier works)

**Server requirements:**
- Ubuntu 22.04+ or similar Linux distribution
- 2GB+ RAM recommended
- Docker Engine 24+
- Python 3.10+

---

## Step 1: Clone the Repository

```bash
# SSH into your server
ssh user@your-server

# Clone the repo
git clone https://github.com/your-org/templatized-jonops.git /opt/jonops
cd /opt/jonops
```

---

## Step 2: Run the Initialization Wizard

The wizard generates your configuration files by asking questions about your business.

```bash
claude /init
```

Answer the prompts. The wizard will create:
- `CLAUDE.md` — Your agent's identity and configuration
- `email-persona.md` — Email reply persona
- `MEMORY.md` — Agent's learning memory
- `.env.example` — Environment variables template

---

## Step 3: Set Up API Keys

Copy the generated example and fill in your credentials:

```bash
cp .env.example .env
nano .env  # or your preferred editor
```

### Required API Keys

#### WordPress

**Where to get it:** WordPress Admin → Users → Your Profile → Application Passwords

```
WP_URL=https://yourdomain.com
WP_USERNAME=your_wordpress_username
WP_PASSWORD=your_application_password
```

**Note:** Use an Application Password, not your regular login password. Generate one at `/wp-admin/profile.php`.

#### Airtable

**Where to get it:** [airtable.com/create/tokens](https://airtable.com/create/tokens)

1. Click "Create new token"
2. Name it "JonOps"
3. Add scopes: `data.records:read`, `data.records:write`, `schema.bases:read`, `schema.bases:write`
4. Add your base under "Access"
5. Copy the token

```
AIRTABLE_API_KEY=pat_xxxxxxxxxxxxxx
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
```

**Base ID:** Open your base in Airtable, look at the URL: `airtable.com/appXXXXXXXXXXXXXX/...`

#### Replicate (AI Image Generation)

**Where to get it:** [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens)

```
REPLICATE_API=r8_xxxxxxxxxxxxxx
```

**Cost:** ~$0.05-0.10 per image. Budget ~$5-10/month for daily images.

#### Tinify (Image Compression)

**Where to get it:** [tinypng.com/developers](https://tinypng.com/developers)

```
TINIFY_API=xxxxxxxxxxxxxx
```

**Free tier:** 500 images/month. More than enough for most use cases.

#### Cloudinary (Social Media Image CDN)

**Where to get it:** [console.cloudinary.com](https://console.cloudinary.com)

1. Sign up for a free account
2. Go to Dashboard → copy your Cloud Name, API Key, and API Secret

```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

**Why it's needed:** Meta's APIs (Facebook, Instagram) need to fetch images from a URL when Metricool schedules posts. WordPress often auto-converts uploaded images to WebP, which Meta rejects. Cloudinary serves permanent JPEG URLs that Meta can always fetch.

**Free tier:** 25,000 transformations + 25GB storage per month. More than enough for daily social posting.

### Recommended API Keys

#### Telegram (Operator Notifications + Chat Interface)

Set up a Telegram bot to receive alerts and talk to your agent directly from your phone.

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow prompts
3. Copy the bot token
4. Start a chat with your new bot
5. Send any message to it
6. Get your chat ID: `https://api.telegram.org/bot<TOKEN>/getUpdates`

```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
TELEGRAM_DAILY_TOKEN_BUDGET=500000
TELEGRAM_DAEMON_ENABLED=true
```

**Telegram Chat Interface (Optional but Recommended)**

The Telegram chat interface lets you talk to your agent like a team member — ask questions, assign tasks, review content, all from your phone.

- **Daily token budget:** Controls how much you can chat per day (~$5 worth at 500k tokens). Resets at midnight.
- **Enable/disable:** Set `TELEGRAM_DAEMON_ENABLED=false` to disable the chat daemon entirely (alerts still work).
- **Commands:** Send `/reset` to start a fresh conversation, `/status` to see token usage.
- **Security:** Only messages from your `TELEGRAM_CHAT_ID` are accepted; all others are silently dropped.

See `TELEGRAM-INTERFACE-SPEC.md` for technical details.

#### Asana (Task Management)

**Where to get it:** [app.asana.com/0/developer-console](https://app.asana.com/0/developer-console)

1. Click "Create new token"
2. Copy the Personal Access Token

```
ASANA_API_KEY=1/1234567890:abcdef
ASANA_PROJECT_GID=1234567890123456
ASANA_INBOX_SECTION_GID=1234567890123456
ASANA_TODO_SECTION_GID=1234567890123456
ASANA_DONE_SECTION_GID=1234567890123456
```

**Getting Section GIDs:**
```bash
# List sections in your project
curl -s "https://app.asana.com/api/1.0/projects/YOUR_PROJECT_GID/sections" \
  -H "Authorization: Bearer YOUR_ASANA_API_KEY"
```

### Optional API Keys

#### Gmail (Email Management)

Gmail requires OAuth2 setup. This is more complex — only set up if you want the email-checker skill.

1. Create a Google Cloud project
2. Enable Gmail API
3. Create OAuth2 credentials (Desktop app)
4. Run the OAuth flow to get refresh token

```
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxx
GOOGLE_REFRESH_TOKEN=xxxx
```

See [Google's OAuth2 guide](https://developers.google.com/gmail/api/quickstart/python) for detailed steps.

#### Sendy (Newsletters)

If you use Sendy for self-hosted email newsletters:

```
SENDY_URL=https://your-sendy-install.com
SENDY_API_KEY=xxxx
SENDY_LIST_MAIN=list_id
SENDY_FROM_NAME=Your Business Name
SENDY_FROM_EMAIL=newsletter@yourdomain.com
SENDY_REPLY_TO=hello@yourdomain.com
```

#### Metricool (Social Media Scheduling)

**Where to get it:** Metricool dashboard → Settings → API

```
METRICOOL_API_TOKEN=xxxx
METRICOOL_BLOG_ID=xxxx
```

#### Instantly (Email Outreach)

**Where to get it:** Instantly dashboard → Settings → API

```
INSTANTLY_API_KEY=xxxx
INSTANTLY_CAMPAIGN_ID=xxxx
INSTANTLY_FROM_EMAIL=outreach@yourdomain.com
```

#### DataForSEO (Keyword Research)

**Where to get it:** [dataforseo.com](https://dataforseo.com) → Dashboard → API Access

```
DATAFORSEO_LOGIN=xxxx
DATAFORSEO_PASSWORD=xxxx
```

**Cost:** Pay-per-use. Budget ~$20-50/month for moderate usage.

#### Firecrawl (Web Scraping)

**Where to get it:** [firecrawl.dev](https://firecrawl.dev)

```
FIRECRAWL_API_KEY=fc-xxxx
```

#### ScrapeCreators (Reddit/Social Discovery)

**Where to get it:** [scrapecreators.com](https://scrapecreators.com)

```
SCRAPECREATORS_API_KEY=xxxx
```

---

## Step 4: Set Up Airtable Tables

Run the setup script to create all required tables:

```bash
# Make sure .env has AIRTABLE_API_KEY and AIRTABLE_BASE_ID
python3 scripts/setup/create-airtable-tables.py
```

The script outputs table IDs. Add them to your `.env`:

```
AIRTABLE_KEYWORDS_TABLE=tblXXXXXXXXXXXXXX
AIRTABLE_CONTENT_TABLE=tblXXXXXXXXXXXXXX
AIRTABLE_RESEARCH_TABLE=tblXXXXXXXXXXXXXX
# ... etc
```

**Tables created:**

| Table | Purpose |
|-------|---------|
| Keywords | SEO keyword queue |
| Content Calendar | Blog post planning |
| Research | Scraped SERP content |
| Published Posts | Published blog log |
| Generated Images | AI image history |
| Reference Images | Reference image library |
| Social Queue | Social post topics |
| Social Posts Log | Published social log |
| Social Mining Queue | Reddit posts to engage |
| Social Mining Drafts | Draft replies |
| Social Mining Log | Conversation tracking |
| Newsletter Queue | Newsletter planning |
| Newsletter Log | Sent newsletters |
| Leads | Subscriber list |
| Outreach Queries | Backlink search queries |
| Outreach Leads | Verified outreach targets |
| B2B Queries | B2B search queries |
| B2B Leads | B2B lead list |
| Market Intelligence | Weekly competitor data |

---

## Step 5: Configure Asana Project (Recommended)

If using Asana for task management:

1. Create a new project in Asana (e.g., "My Business Ops")
2. Create these sections:
   - 📥 Inbox
   - 📋 Agent To-Do (for ad hoc tasks you assign to the agent)
   - 🔄 In Progress
   - ✅ Done
3. Get the project GID from the URL: `app.asana.com/0/PROJECT_GID/...`
4. Get section GIDs via API (see Step 3)
5. Add to `.env`

---

## Step 6: Build and Launch

```bash
# Build the Docker image
docker compose build

# Start in background
docker compose up -d

# View logs
docker compose logs -f
```

---

## Step 7: Verify Everything Works

### Check Scheduler Status

```bash
python scheduler.py --status
```

Should show upcoming scheduled skills.

### Run a Test Skill

```bash
# Run the daily watchdog to test everything
claude "Run the asana-check skill"
```

### Check Telegram Alerts

You should receive a Telegram message when the skill completes.

---

## Customization

### Disable Skills

Edit `schedule.json` to disable skills you don't need:

```json
{
  "skill": "b2b-outreach-lead-finder",
  "enabled": false
}
```

### Change Schedule Times

All times are in your configured timezone:

```json
{
  "skill": "daily-contribution",
  "time": "06:00"  // Changed from 07:00
}
```

### WordPress Category IDs

Find your category IDs:

```bash
curl -s "https://yourdomain.com/wp-json/wp/v2/categories" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f'{c[\"id\"]}: {c[\"name\"]}')"
```

Add to CLAUDE.md in the WordPress section.

---

## Troubleshooting

### "Missing environment variable"

Check your `.env` file has all required variables. Compare against `.env.example`.

### WordPress publish fails

1. Verify WP_URL is correct (include https://)
2. Check WP_USERNAME and WP_PASSWORD are correct
3. Ensure the user has `edit_posts` and `publish_posts` capabilities
4. Verify Application Password is enabled (some hosts disable it)

### Airtable "table not found"

1. Re-run `create-airtable-tables.py`
2. Copy ALL the `AIRTABLE_*_TABLE=tblXXX` lines to `.env`
3. Restart the container

### Telegram alerts not working

1. Make sure you started a chat with your bot
2. Verify TELEGRAM_CHAT_ID is your chat, not the bot's
3. Test manually:
   ```bash
   curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
     -d "chat_id=$TELEGRAM_CHAT_ID" \
     -d "text=Test message"
   ```

### Agent not running on schedule

1. Check scheduler is running: `ps aux | grep scheduler`
2. Check logs: `tail -f logs/scheduler.log`
3. Restart: `docker compose restart`

### Image generation fails

1. Verify REPLICATE_API is correct
2. Check Replicate account has credits
3. Test manually:
   ```bash
   bash generate-image.sh --prompt "test image" --aspect-ratio "16:9" --filename "test"
   ```

---

## Maintenance

### Update JonOps

```bash
cd /opt/jonops
git pull
docker compose build
docker compose up -d
```

### Backup

Important files to backup:
- `.env` — API credentials
- `CLAUDE.md` — Agent configuration
- `MEMORY.md` — Agent's learned knowledge
- `email-persona.md` — Email persona

Airtable data is stored in Airtable's cloud.

### Monitoring

Set up log rotation:

```bash
# /etc/logrotate.d/jonops
/opt/jonops/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

---

## Getting Help

1. Check the skill files in `.claude/skills/` — they have detailed documentation
2. Read `CLAUDE.md` for the agent's full configuration
3. Review logs in `/opt/jonops/logs/`
4. Open an issue on GitHub

---

## Next Steps

Once JonOps is running:

1. **Monitor for a few days** — Watch Telegram alerts and check Airtable
2. **Review draft responses** — The social-miner creates drafts for you to review before posting
3. **Seed the keyword queue** — Add some keywords to the Keywords table to kickstart content
4. **Customize content angles** — Update CLAUDE.md with your specific content strategy
5. **Tune the schedule** — Adjust times and disable skills as needed

Good luck with your autonomous marketing agent! 🚀
