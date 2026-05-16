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

## Padding layers (read FIRST, before any topic selection)

This skill is **generic** — the brand-specific judgment comes from the per-brand padding files at the container root. Read in this order before doing anything else:

1. **`/home/agent/project/brand-rules.md`** — REQUIRED. Defines ICP, mission, doctrine. The chosen newsletter topic must serve the ICP defined here. If this file is missing → SKILL_RESULT: fail | brand-rules.md missing — operator must scaffold (see `templates/brand-rules.template.md`). Fire ❌ Telegram.
2. **`/home/agent/project/brand-voice.md`** — REQUIRED. Defines tone, banned phrases, voice attributes. The subject lines + brief tone-note must obey this. If missing → fall back to voice notes in `CLAUDE.md` + fire ⚠️ Telegram warning.
3. **`/home/agent/project/knowledge-base.md`** OR **`/home/agent/project/knowledge_base/`** — OPTIONAL. If present, use it as the fact source-of-truth for any claims in the brief. If the brand has a `knowledge_base/` directory, scan the index (this file at root or `knowledge_base/README.md`) for relevant subdirectories.

After reading the padding, proceed to the steps below.

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
Consider, in priority order:
- Which post topic best serves the **ICP defined in `brand-rules.md`**?
- Which post topic best embodies the **brand doctrine** from `brand-rules.md` (e.g., warm hug doctrine)?
- What's timely or seasonal right now?
- What hasn't been featured in the last 3 newsletters?
- What pairs well with the **CTA defined for newsletters in `brand-rules.md`**?

Pick ONE featured post as the anchor.

### Step 4: Write newsletter brief
Produce:
- **3 subject line options** — each under 50 chars, curiosity-driven, no clickbait. **Must pass `brand-voice.md` banned-phrases check.**
- **Pre-header text** — 40-50 chars, complements subject line
- **Main topic summary** — what the newsletter covers in 2-3 sentences, in `brand-voice.md` voice
- **Key points** — 3 bullet points the reader will get from this issue
- **Featured post URL** — the anchor post
- **CTA** — pull from `brand-rules.md` § "CTAs by surface — Newsletter"
- **Tone note** — any special angle for this week (seasonal, industry event, holiday tie-in, etc.)
- **Padding-layer trace** — one line: "ICP served: [from brand-rules.md]. Voice rules applied: [key rules from brand-voice.md]. KB references: [files consulted, or N/A]."

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
- **Never bake brand-specifics into this skill body.** If you find yourself wanting to add "for Taiwan content..." or "for horoscope content..." — that belongs in the brand's `brand-rules.md` or `brand-voice.md`, not here.
