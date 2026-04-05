---
skill: social-poster-1
version: 1.1.0
cadence: daily
trigger: cron
source: most recent published blog post
airtable_reads: [Published Posts]
airtable_writes: [Social Posts Log]
external_apis: [metricool, replicate, tinify, wordpress-media]
active: true
notes: "Posts based on most recent blog. SP2 handles researcher queue topics."
---

# Social Poster 1 — Blog Repurpose Skill

## What This Skill Does (Plain English)
This skill takes the most recently published blog post and turns it into social media content for every active platform (Facebook, Instagram, Twitter/X, Pinterest). It generates unique images for each platform, writes platform-appropriate captions respecting character limits, and schedules everything via Metricool.

**Examples by business type:**
- **Bakery:** Blog post "Sourdough Starter Guide" → tailored social posts for each platform
- **Landscaper:** Blog post "Spring Lawn Care Tips" → platform-specific content with seasonal imagery
- **Lawyer:** Blog post "Estate Planning Basics" → professional social content across platforms

---

## Purpose
Take the most recently published blog post and create platform-specific social content for it. Schedule 2 posts per active platform (morning + evening) via Metricool. This runs daily and always sources from the latest published post.

## Prerequisites
- WP_URL, WP_USERNAME, WP_PASSWORD in .env
- METRICOOL_API_TOKEN, METRICOOL_BLOG_ID in .env
- REPLICATE_API, TINIFY_API in .env
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID in .env
- Active platforms defined in CLAUDE.md

## Process

### Step 1: Get most recent published post
```bash
curl -s "${WP_URL}/wp-json/wp/v2/posts?per_page=1&status=publish&orderby=date&order=desc" \
  -u "${WP_USERNAME}:${WP_PASSWORD}"
```
Extract: title, URL, excerpt, featured image URL, categories, focus keyword.

### Step 2: Check Social Posts Log
Query Airtable Social Posts Log — has this post URL already been posted to socials?
If yes: skip gracefully, fire ⚠️ Telegram "SP1 skipped — already posted for [title]", exit.

### Step 3: Generate content per platform

#### Platform Character Limits (MANDATORY)
Count characters BEFORE scheduling. Posts exceeding these limits will be truncated or rejected by the platform.

| Platform    | Hard Max (API)  | Target Length     | Truncation Point                  |
|-------------|-----------------|-------------------|-----------------------------------|
| Pinterest   | 500 chars       | **200-250 chars** | Only 50-60 chars visible in feed  |
| Facebook    | 16,192 chars    | 300-480 chars     | "See More" at ~480 chars          |
| Instagram   | 2,200 chars     | 400-800 chars     | "...more" at ~125 chars           |
| Twitter/X   | 280 chars       | 70-100 chars      | Hard cutoff — no truncation       |

For each ACTIVE platform in CLAUDE.md, write platform-specific content:

**Facebook** (target: 300-480 chars — stay under 480 to avoid "See More")
- Emotional hook in first line (under 80 chars for max engagement)
- 3-5 key insights from the post
- CTA linking to post URL
- 5-8 relevant hashtags
- Tone: Match brand voice from CLAUDE.md

**Instagram** (target: 400-800 chars, max 2,200)
- Hook MUST be in first 125 chars (that's all visible before "...more")
- 3-5 key insights from the post
- CTA linking to post URL
- 5-8 relevant hashtags
- Tone: Match brand voice from CLAUDE.md

**Twitter/X** (HARD max: 280 chars per tweet — no exceptions)
- Tweet 1 (hook): ≤280 chars — punchy question or bold statement
- Tweet 2: key insight from post
- Tweet 3: CTA with URL
- Tone: punchy, curiosity-driven
- Sweet spot: 70-100 chars gets highest engagement

**Pinterest** (target: 200-250 chars — MUST be under 500 chars total)
- Pin title: keyword-rich, under 100 chars (include focus keyword)
- Pin description: **200-250 characters MAX** — concise, keyword-dense, evergreen
- Front-load most important keywords in first 50 chars (that's all visible in feed)
- "How-to" or "Guide to" angle where possible
- 3-5 keyword hashtags (counted WITHIN the character limit)
- NO long paragraphs or multi-sentence descriptions

**Example Pinterest descriptions by business type:**
- *Bakery (221 chars):* "Master the art of sourdough with our complete beginner's guide. Starter tips, feeding schedule, and your first loaf recipe. #sourdough #breadbaking #homemade #bakingguide"
- *Landscaper (215 chars):* "Your complete spring lawn care checklist for Zone 7. Timing, fertilizer tips, and common mistakes to avoid. #lawncare #springgardening #landscaping #homeowner"

### Step 4: Generate images
Generate a unique image for each platform post via generate-image.sh. Each post gets its own image with a distinct prompt — write a different prompt per platform.
Always use `--upload` so images get permanent WordPress URLs.
```bash
IMAGE_JSON=$(bash /home/agent/project/generate-image.sh \
  --prompt "[unique prompt per platform]" \
  --aspect-ratio "1:1" \
  --filename "sp1-[platform]-[date]" \
  --upload)

IMAGE_URL=$(echo "$IMAGE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['wp_media_url'])")
```
Always use `wp_media_url` (permanent). Do not use `tinified_url` (temporary).

### Step 5: Schedule via Metricool
Schedule one post per platform for tomorrow 09:00 WITA (this skill runs at 09:00).
```bash
curl -s -X POST "https://app.metricool.com/api/v2/scheduler" \
  -H "X-Mc-Auth: ${METRICOOL_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "blogId": "'${METRICOOL_BLOG_ID}'",
    "networks": ["instagram"],
    "text": "[caption]",
    "date": "[tomorrow 09:00 WITA in UTC]",
    "mediaUrls": ["[image_url]"]
  }'
```

### Step 6: Log to Airtable Social Posts Log
For each scheduled post, create Airtable record:
- Platform, Post Type: "Blog Repurpose", Caption Preview (first 100 chars)
- Scheduled Time, Source Post URL, Image URL

### Step 7: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert (use your project slug from CLAUDE.md):
```bash
bash /home/agent/project/telegram-alert.sh "✅ social-poster-1 — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ social-poster-1 — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ social-poster-1 — [skip reason]"`

```
SKILL_RESULT: success | SP1 scheduled [N] posts for "[Post Title]" across [platforms] | [post_url]
```

## Error Handling
- No published posts found → SKILL_RESULT: skip | No published posts found
- Metricool auth error → SKILL_RESULT: fail | Metricool auth error — check METRICOOL_API_TOKEN
- Image generation fails → use post featured image as fallback, log warning

## Rules
- Never post directly — always schedule via Metricool
- Always generate unique image per post — never reuse
- Only link to live published URLs — never drafts
- Skip gracefully if already posted today
- Always count characters before scheduling — respect platform limits
- Pinterest descriptions MUST be under 500 chars (target 200-250)
