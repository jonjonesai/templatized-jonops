---
skill: social-poster-1
version: 2.0.0
cadence: daily
trigger: cron
source: most recent published blog post
airtable_reads: [Published Posts]
airtable_writes: [Social Posts Log]
external_apis: [metricool, replicate, tinify, wordpress-media]
image_model: flux-2-pro
architecture: orchestrator
active: true
notes: "v2: Orchestrator that delegates to per-platform subskill files. Static images only — no video (see SP2 for video)."
---

# Social Poster 1 — Blog Repurpose Orchestrator (v2)

## What This Skill Does (Plain English)
Takes the most recently published blog post and schedules a **unique** static social post for each active platform (Facebook, Instagram, Pinterest, TikTok). Each platform gets its own caption, its own image (in its own aspect ratio), and its own scheduling time — delegated to platform-specific subskill files in `.claude/skills/social-[platform].md`.

SP1 = **static images only**. SP2 handles video (TikTok + Instagram Reels).

**Examples by business type:**
- **Bakery:** Blog post "Sourdough Starter Guide" → tailored social posts for each platform with unique images
- **Landscaper:** Blog post "Spring Lawn Care Tips" → platform-specific content with seasonal imagery
- **E-commerce:** Blog post "Gift Guide" → unique image per platform (16:9 FB, 1:1 IG, 2:3 Pinterest, 9:16 TikTok)

---

## Architecture

```
┌─────────────────────┐
│   social-poster-1   │  ← this file (orchestrator)
└──────────┬──────────┘
           │
           ├── Read social-facebook.md   → execute for this blog
           ├── Read social-instagram.md  → execute in IMAGE mode
           ├── Read social-pinterest.md  → execute for this blog
           └── Read social-tiktok.md     → execute in STATIC mode
```

Each subskill is a Markdown file that this orchestrator reads (via the `Read` tool) and follows as an inline instruction set. **Do not spawn nested Claude sessions.** Just read the subskill file, execute its steps for the current content, and continue.

---

## Prerequisites
- WP_URL, WP_USERNAME, WP_PASSWORD in env
- METRICOOL_API_TOKEN, METRICOOL_BLOG_ID in env
- REPLICATE_API, TINIFY_API in env
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_SOCIAL_POSTS_LOG_TABLE in env
- Active platforms defined in CLAUDE.md

---

## Process

### Step 1: Get the most recent published post
```bash
curl -s "${WP_URL}/wp-json/wp/v2/posts?per_page=1&status=publish&orderby=date&order=desc" \
  -u "${WP_USERNAME}:${WP_PASSWORD}"
```
Extract: `title`, `link` (URL), `excerpt`, `focus_keyword` (from RankMath meta if available), `featured_media`, `id`.

### Step 2: Dedup check against Social Posts Log
Query Airtable:
```bash
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_POSTS_LOG_TABLE}?filterByFormula=AND({Source+Post+URL}='${POST_URL}',{Post+Type}='Blog+Repurpose')&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
If a record exists: skip gracefully, fire `⚠️ SP1 skipped — already posted for [title]` via `telegram-alert.sh`, exit with `SKILL_RESULT: skip`.

### Step 3: Prepare common inputs for all subskills
Build the common context object mentally (you'll plug these into each subskill invocation):
- `TITLE` = blog post title
- `CONTENT_SOURCE` = blog URL
- `LINK_URL` = blog URL
- `FOCUS_KEYWORD` = RankMath focus keyword (for Pinterest SEO)
- `TOMORROW` = tomorrow's date in `YYYY-MM-DD` (this skill runs in the morning, posts go out tomorrow)

**Scheduling stagger** (all for TOMORROW, using timezone from CLAUDE.md):
| Platform  | Time  |
|-----------|-------|
| Facebook  | 09:00 |
| Instagram | 12:00 |
| Pinterest | 15:00 |
| TikTok    | 18:00 |

### Step 4: Delegate to each platform subskill
For each active platform, **read the subskill file** and execute its steps:

#### 4a — Facebook
1. `Read` tool → `.claude/skills/social-facebook.md`
2. Follow its Step 1 (write caption), Step 2 (generate 16:9 image with `FILENAME_SLUG=sp1-facebook-${TOMORROW}`), Step 3 (schedule via Metricool at `${TOMORROW}T09:00:00`)
3. Capture the result object

#### 4b — Instagram (IMAGE mode)
1. `Read` → `.claude/skills/social-instagram.md`
2. `MODE="image"`
3. Execute Step 1 (caption with hashtag block), Step 2 IMAGE mode (generate 1:1 image, `FILENAME_SLUG=sp1-instagram-${TOMORROW}`), Step 3 (schedule at `${TOMORROW}T12:00:00`)
4. Capture the result

#### 4c — Pinterest
1. `Read` → `.claude/skills/social-pinterest.md`
2. Execute Step 1 (keyword-dense 200–250 char description), Step 2 (2:3 image, `FILENAME_SLUG=sp1-pinterest-${TOMORROW}`), Step 3 (schedule at `${TOMORROW}T15:00:00` with `pinterestData.boardId`)
3. Capture the result

#### 4d — TikTok (STATIC mode)
1. `Read` → `.claude/skills/social-tiktok.md`
2. `MODE="static"` (SP1 does NOT render video — that's SP2's job)
3. Execute STATIC block: 9:16 image, `FILENAME_SLUG=sp1-tiktok-${TOMORROW}`, schedule at `${TOMORROW}T18:00:00`
4. Capture the result

### Step 5: Log everything to Airtable Social Posts Log
For each successful platform, create a Social Posts Log record:
```bash
curl -s -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_POSTS_LOG_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Platform": "[facebook|instagram|pinterest|tiktok]",
    "Post Type": "Blog Repurpose",
    "Caption Preview": "[first 100 chars]",
    "Scheduled Time": "[ISO datetime]",
    "Source Post URL": "[blog url]",
    "Image URL": "[wp_media_url]"
  }}'
```

### Step 6: Telegram alert & SKILL_RESULT
```bash
bash /home/agent/project/telegram-alert.sh "✅ social-poster-1 — scheduled N/4 platforms for '[title]' (FB/IG/Pin/TikTok static)"
```

On partial success (some platforms failed): use ⚠ and list which ones failed.
On full failure: use ❌ with details.

```
SKILL_RESULT: success | SP1 scheduled [N] static posts for "[Post Title]" across [platforms] | [blog_url]
```

---

## Error Handling
- **No published posts** → `SKILL_RESULT: skip | No published posts found`
- **Already posted** → `SKILL_RESULT: skip | Already posted for [title]`
- **Single platform fails** → continue with others, report partial success
- **All platforms fail** → `SKILL_RESULT: fail | All 4 platforms failed — check logs`
- **generate-image.sh fails for a platform** → that platform is skipped; log the error and continue
- **Metricool auth error** → `SKILL_RESULT: fail | Metricool auth error — check METRICOOL_API_TOKEN`

---

## Rules
- Static images ONLY — if the task calls for video, it's a bug (video is SP2's job)
- Always use `flux-2-pro` (premium model)
- Always use `--upload` so images get permanent WP URLs
- Always generate a **unique** image per platform — never reuse
- Each platform gets its own caption written from scratch (per its subskill rules)
- Schedule everything for TOMORROW with the staggered times above
- Skip gracefully if dedup check finds existing log record
- Only link to live published URLs — never drafts
- Always count characters before scheduling (platform limits in each subskill)
