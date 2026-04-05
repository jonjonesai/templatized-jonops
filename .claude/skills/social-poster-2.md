---
skill: social-poster-2
version: 1.1.0
cadence: daily
trigger: cron
source: Airtable Social Queue (researcher topics)
airtable_reads: [Social Queue]
airtable_writes: [Social Queue, Social Posts Log]
external_apis: [metricool, replicate, tinify]
active: true
notes: "Posts based on social-researcher queue. SP1 handles blog repurpose."
---

# Social Poster 2 — Researcher Queue Skill

## What This Skill Does (Plain English)
This skill pulls the next topic from the Social Queue in Airtable (populated by the social-researcher skill) and creates original social media posts from it — not repurposed blog content. It generates unique images, writes platform-specific captions, and schedules them via Metricool. Think of it as the companion to Social Poster 1: SP1 promotes blog posts, while SP2 posts standalone content based on researched trending topics.

---

## Purpose
Pull the next queued topic from the Social Queue (populated by social-researcher) and create platform-specific social content for it. This content is independent from blog posts — it's based on researched niche topics.

## Prerequisites
- Same as social-poster-1
- Social Queue must have Status: Queued rows (populated by social-researcher)

## Process

### Step 1: Read Social Queue
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_QUEUE_TABLE}?filterByFormula=Status='Queued'&sort[0][field]=Priority&sort[0][direction]=desc&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
If no Queued rows: fire ⚠️ Telegram "SP2 skipped — Social Queue empty. social-researcher needs to run.", then exit gracefully.

Extract: Topic, Research Brief, Platform Fit, record ID.

### Step 2: Mark as In Progress
```bash
curl -s --retry 3 --retry-delay 2 -X PATCH "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_QUEUE_TABLE}/[RECORD_ID]" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"Status": "In Progress"}}'
```

### Step 3: Generate content per platform
Use the Research Brief as the content foundation.
Only post to platforms marked in Platform Fit field AND active in CLAUDE.md.

The content angle comes from the Research Brief — use it fully.
Do NOT just repurpose a blog post — this is original researched content.

#### Platform Character Limits (MANDATORY — same as SP1)

| Platform    | Hard Max (API)  | Target Length     | Truncation Point                  |
|-------------|-----------------|-------------------|-----------------------------------|
| Pinterest   | 500 chars       | **200-250 chars** | Only 50-60 chars visible in feed  |
| Facebook    | 16,192 chars    | 300-480 chars     | "See More" at ~480 chars          |
| Instagram   | 2,200 chars     | 400-800 chars     | "...more" at ~125 chars           |
| Twitter/X   | 280 chars       | 70-100 chars      | Hard cutoff — no truncation       |

**Pinterest is the critical one:** Pin descriptions MUST stay under 500 chars (target 200-250). Front-load keywords in the first 50 chars. No long paragraphs.

**Facebook:** Hook under 80 chars. Full post under 480 to avoid "See More."

**Instagram:** First 125 chars must contain the hook — that's all visible before "...more."

**Twitter/X:** Hard 280 limit. Sweet spot is 70-100 chars.

### Step 4: Generate images
Generate a unique image for each platform post via generate-image.sh. Each post gets its own image with a distinct prompt — write a different prompt per platform.
Always use `--upload` so images get permanent WordPress URLs.
```bash
IMAGE_JSON=$(bash /home/agent/project/generate-image.sh \
  --prompt "[unique prompt per platform]" \
  --aspect-ratio "1:1" \
  --filename "sp2-[platform]-[date]" \
  --upload)

IMAGE_URL=$(echo "$IMAGE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['wp_media_url'])")
```
Always use `wp_media_url` (permanent). Do not use `tinified_url` (temporary).

### Step 5: Schedule via Metricool
Schedule one post per platform for today 20:00 WITA (this skill runs at 20:00).

### Step 6: Update Airtable
Mark Social Queue record Status: Used.
Log each scheduled post to Social Posts Log (Post Type: "Research Queue").

### Step 7: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ social-poster-2 — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ social-poster-2 — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ social-poster-2 — [skip reason]"`

```
SKILL_RESULT: success | SP2 scheduled [N] posts for "[Topic]" across [platforms]
```

## Error Handling
- Empty queue → skip gracefully with ⚠️ Telegram
- Metricool error → SKILL_RESULT: fail | Metricool error
- Mark Airtable record back to Queued if posting fails

## Rules
- ONE topic per session — pick oldest high-priority queued item
- Never invent topics — only use what social-researcher queued
- Always mark record as Used after successful posting
- Always count characters before scheduling — respect platform limits
- Pinterest descriptions MUST be under 500 chars (target 200-250)
