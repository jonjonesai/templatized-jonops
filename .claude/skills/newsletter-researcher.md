---
skill: newsletter-researcher
version: 1.0.0
cadence: weekly (Thursday)
trigger: cron
airtable_reads: [Published Posts, Social Posts Log]
airtable_writes: [Newsletter Queue]
external_apis: []
active: true
notes: "Runs Thursday. newsletter-writer reads this on Friday."
---

# Newsletter Researcher Skill

## What This Skill Does (Plain English)
Every Thursday, this skill reviews the past week's published blog posts and picks the best one to anchor Friday's newsletter. It writes a research brief with three subject line options, key talking points, and a recommended CTA, then queues the brief in Airtable. The newsletter-writer skill reads this brief the next day and turns it into the actual email that goes out to subscribers.

---

## Purpose
Review last week's published content and social performance, pick the best angle for this week's newsletter, write a research brief with subject line options, and queue it for newsletter-writer to execute on Friday.

## Prerequisites
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID in .env
- WP_URL, WP_USERNAME, WP_PASSWORD in .env

## Process

### Step 1: Check Newsletter Queue — avoid double-queueing
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_NEWSLETTER_QUEUE_TABLE}?filterByFormula=Status='Queued'" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
If a Queued item already exists for this week: skip, fire ⚠️ Telegram, exit.

### Step 2: Get last 7 days of published posts
```bash
curl -s "${WP_URL}/wp-json/wp/v2/posts?after=[7_days_ago_ISO]&status=publish&orderby=date&order=desc" \
  -u "${WP_USERNAME}:${WP_PASSWORD}"
```
List titles, URLs, categories, word counts.

### Step 3: Pick best newsletter angle
Consider:
- Which post topic has the broadest appeal to the audience?
- What's timely or seasonal right now?
- What hasn't been featured in the last 3 newsletters?
- What pairs well with a product mention or CTA?

Pick ONE featured post as the anchor.

### Step 4: Write newsletter brief
Produce:
- **3 subject line options** — each under 50 chars, curiosity-driven, no clickbait
- **Pre-header text** — 40-50 chars, complements subject line
- **Main topic summary** — what the newsletter covers in 2-3 sentences
- **Key points** — 3 bullet points the reader will get from this issue
- **Featured post URL** — the anchor post
- **CTA** — what action should the reader take? (read post / shop product / join community)
- **Tone note** — any special angle for this week (seasonal, industry event, holiday tie-in, etc.)

### Step 5: Push to Newsletter Queue
```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_NEWSLETTER_QUEUE_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Main Topic": "[topic]",
    "Subject Line Options": "[3 options, one per line]",
    "Research Brief": "[full brief]",
    "Featured Post URL": "[url]",
    "CTA": "[cta description]",
    "Status": "Queued",
    "Week Target": "[this Friday date]"
  }}'
```

### Step 6: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ newsletter-researcher — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ newsletter-researcher — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ newsletter-researcher — [skip reason]"`

```
SKILL_RESULT: success | Newsletter brief queued for "[main topic]" | Friday send target
```

## Rules
- ONE brief per week — don't queue multiple
- Subject lines must be under 50 chars
- Never feature a post already used in the last 3 newsletters (check Newsletter Log)
