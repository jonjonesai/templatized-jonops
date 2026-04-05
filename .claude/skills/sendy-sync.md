---
skill: sendy-sync
version: 1.0.0
cadence: weekly (Sunday)
trigger: cron
airtable_reads: []
airtable_writes: []
external_apis: [fluent-crm, sendy]
sub_skills: [email-verifier.md]
active: true
notes: "Syncs new Fluent CRM contacts to Sendy lists weekly. Bridges form funnels to newsletter."
---

# Sendy Sync Skill

## What This Skill Does (Plain English)
Every Sunday, this skill bridges the gap between the website's form system and the newsletter platform. When someone fills out a "Join Our Cosmic Community" form on the blog, they land in Fluent CRM (WordPress). This skill grabs those new contacts, verifies their email addresses are real, and subscribes the valid ones to the appropriate Sendy newsletter list so they start receiving the weekly email.

---

## Purpose
Sync new contacts from Fluent CRM to the appropriate Sendy newsletter lists. This bridges the form funnel pipeline (Fluent Forms → Fluent CRM) to the newsletter platform (Sendy). Runs every Sunday to catch the week's new subscribers.

## How the pipeline works
Visitor fills Fluent Form → Fluent CRM tags them → This skill syncs tagged contacts to Sendy list

## Prerequisites
- WP_URL, WP_USERNAME, WP_PASSWORD in .env (Fluent CRM uses WP REST API)
- SENDY_URL, SENDY_API_KEY in .env
- SENDY_LIST_MAIN (and other list IDs) in .env
- Fluent CRM tag names defined in CLAUDE.md

## Process

### Step 1: Fetch new Fluent CRM contacts (last 7 days)
```bash
curl -s "${WP_URL}/wp-json/fluent-crm/v2/subscribers?status=subscribed&sort_by=created_at&sort_order=DESC&per_page=100" \
  -u "${WP_USERNAME}:${WP_PASSWORD}"
```
Filter for contacts created in the last 7 days.

### Step 2: Verify emails before syncing
For each batch of emails, apply email-verifier sub-skill logic:
- Skip emails marked Invalid
- Flag Risky emails for operator review
- Only sync Verified emails to Sendy

Reference: .claude/skills/email-verifier.md for verification process.

### Step 3: Map tags to Sendy lists
Per tag mapping defined in CLAUDE.md:
- Tag "newsletter-subscriber" → SENDY_LIST_MAIN
- Tag "abandoned-cart" → SENDY_LIST_ABANDONED_CART (if applicable)
- Tag "customer" → SENDY_LIST_CUSTOMERS (if applicable)

### Step 4: Subscribe to Sendy list
For each verified contact:
```bash
curl -s -X POST "${SENDY_URL}/subscribe" \
  -d "api_key=${SENDY_API_KEY}" \
  -d "list=[LIST_ID]" \
  -d "email=[email]" \
  -d "name=[name]" \
  -d "boolean=true"
```

### Step 5: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ sendy-sync — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ sendy-sync — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ sendy-sync — [skip reason]"`

```
SKILL_RESULT: success | [N] contacts synced to Sendy | [N] skipped (invalid) | [N] flagged (risky)
```

## Error Handling
- Fluent CRM API error → SKILL_RESULT: fail | Fluent CRM connection error
- Sendy API error → log failed emails, retry next week
- Always verify before syncing — never push unverified emails to Sendy

## Rules
- Never sync Invalid emails
- Never sync duplicates — Sendy handles deduplication but check anyway
- Always use email-verifier sub-skill before syncing
