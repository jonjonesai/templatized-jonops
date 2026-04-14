---
skill: social-poster-2
version: 2.0.0
cadence: daily
trigger: cron
source: Airtable Social Queue (researcher topics)
airtable_reads: [Social Queue]
airtable_writes: [Social Queue, Social Posts Log]
external_apis: [metricool, replicate, tinify, wordpress-media, jamendo, elevenlabs]
image_model: flux-2-pro
architecture: orchestrator
supports_video: true
active: true
notes: "v2: Orchestrator that delegates to per-platform subskill files. TikTok + Instagram Reels share ONE rendered video (one render, two platforms). Facebook + Pinterest get unique static images."
---

# Social Poster 2 — Researcher Queue Orchestrator (v2)

## What This Skill Does (Plain English)
Pulls the next topic from the Social Queue in Airtable (populated by the social-researcher skill) and creates original social media content for it — not blog repurpose. This is the **flagship** video pipeline:

- **TikTok** gets a fully rendered 20-25s MP4 with slides, Jamendo BGM, and ElevenLabs voiceover
- **Instagram Reels** reuses the EXACT SAME video (one render, two platforms)
- **Facebook** gets a unique 16:9 static image
- **Pinterest** gets a unique 2:3 static image with SEO-optimized description

Each platform's caption, image prompt, and scheduling time are unique — delegated to platform-specific subskill files in `.claude/skills/social-[platform].md`.

**Examples by business type:**
- **Bakery:** Trending topic "Sourdough vs commercial bread" → video of artisan process, static images for FB/Pinterest
- **Landscaper:** Research topic "Native plants for pollinators" → visual slideshow video + platform images
- **E-commerce:** Researched trend "Gift ideas for [occasion]" → product-adjacent video content + static posts

---

## Architecture

```
┌─────────────────────┐
│   social-poster-2   │  ← this file (orchestrator)
└──────────┬──────────┘
           │
           ├── Read social-facebook.md   → execute (static 16:9)
           ├── Read social-pinterest.md  → execute (static 2:3)
           ├── Read social-tiktok.md     → execute in VIDEO mode
           │     └── generate-tiktok-video.sh
           │           ├── generate-image.sh × N  (slides)
           │           ├── jamendo-download.sh    (BGM)
           │           ├── elevenlabs-tts.sh      (voiceover)
           │           └── remotion/render-ffmpeg.py
           │
           └── Read social-instagram.md  → execute in REEL mode
                 └── reuses $VIDEO_URL from tiktok step (NO re-render)
```

Each subskill is a Markdown file that this orchestrator reads (via the `Read` tool) and follows as an inline instruction set. **Do not spawn nested Claude sessions.**

---

## Prerequisites
- WP_URL, WP_USERNAME, WP_PASSWORD in env
- METRICOOL_API_TOKEN, METRICOOL_BLOG_ID in env
- REPLICATE_API, TINIFY_API in env
- JAMENDO_CLIENT_ID in env (for BGM)
- ELEVENLABS_API in env (for voiceover)
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_SOCIAL_QUEUE_TABLE, AIRTABLE_SOCIAL_POSTS_LOG_TABLE in env
- Social Queue must have at least one Status: Queued row (populated by social-researcher)
- Active platforms from CLAUDE.md

---

## Process

### Step 1: Read the next queued topic
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_QUEUE_TABLE}?filterByFormula=Status='Queued'&sort[0][field]=Priority&sort[0][direction]=desc&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
If no Queued rows:
```bash
bash /home/agent/project/telegram-alert.sh "⚠️ social-poster-2 skipped — Social Queue empty. social-researcher needs to run."
```
Exit with `SKILL_RESULT: skip | Social Queue empty`.

Extract: `record_id`, `Topic`, `Research Brief`, `Platform Fit` (optional — if blank, use all 4 platforms).

### Step 2: Mark the record as In Progress
```bash
curl -s --retry 3 --retry-delay 2 -X PATCH "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_QUEUE_TABLE}/${RECORD_ID}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"Status": "In Progress"}}'
```

### Step 3: Prepare common context
Build the common context object you'll feed into each subskill:
- `TITLE` = Topic from the queue
- `CONTENT_SOURCE` = Research Brief (full text)
- `LINK_URL` = Your shop/homepage URL from CLAUDE.md (SP2 is not blog-tied)
- `TOMORROW` = tomorrow's date in `YYYY-MM-DD` (this skill runs in the evening, posts go out tomorrow)

**Scheduling stagger** (all for TOMORROW, using timezone from CLAUDE.md):
| Platform  | Time  | Format |
|-----------|-------|--------|
| Facebook  | 10:00 | Static 16:9 image |
| Pinterest | 13:00 | Static 2:3 image |
| TikTok    | 16:00 | VIDEO (MP4) |
| Instagram | 19:00 | REEL (same MP4) |

### Step 4: Delegate to static-image subskills
Do these **first**, in parallel where possible, so they're done before the slow video render.

#### 4a — Facebook (static 16:9)
1. `Read` tool → `.claude/skills/social-facebook.md`
2. Execute Step 1 (write a 300–480 char caption from the Research Brief), Step 2 (generate 16:9 image with `FILENAME_SLUG=sp2-facebook-${TOMORROW}`), Step 3 (schedule via Metricool at `${TOMORROW}T10:00:00`)
3. Capture the result object

#### 4b — Pinterest (static 2:3)
1. `Read` → `.claude/skills/social-pinterest.md`
2. Execute Step 1 (write a 200–250 char keyword-dense description from the Research Brief), Step 2 (2:3 image, `FILENAME_SLUG=sp2-pinterest-${TOMORROW}`), Step 3 (schedule at `${TOMORROW}T13:00:00` with `pinterestData.boardId`)
3. Capture the result

### Step 5: Delegate to TikTok (VIDEO mode) — the flagship render
1. `Read` tool → `.claude/skills/social-tiktok.md`
2. `MODE="video"`
3. Execute the subskill's video pipeline:
   - **Write the narration text** (`NARRATION_TEXT`) — 2–4 short sentences, ~300 chars target, max 500. Natural spoken cadence. Pull the strongest hook + payoff from the Research Brief.
   - **Write 3–4 slide prompts** (`SLIDE_PROMPTS`) — each describes a distinct vertical 9:16 scene matching brand image style from CLAUDE.md. Narrative arc: opening wide shot → subject close-up → payoff → optional CTA beat.
   - **Pick the mood** (`MOOD`) based on the Topic's angle (see the mood table in social-tiktok.md)
   - **Write a TikTok caption** (150–300 chars, 3–5 hashtags, no line breaks)
   - **Invoke** `generate-tiktok-video.sh` with `FILENAME_SLUG=sp2-tiktok-${TOMORROW}` and all the above params
   - **Extract** `VIDEO_URL` (permanent WP URL) AND `BGM_ATTRIBUTION` (Jamendo license credit — must append to caption)
   - **Schedule** via Metricool at `${TOMORROW}T16:00:00`
4. Capture the result including `VIDEO_URL` (critical — Instagram reuses it)

**If video pipeline fails** (empty `VIDEO_URL`): the subskill falls back to a 9:16 static image. In that case `VIDEO_URL=""` and the Instagram step must also fall back to a 1:1 static image (see Step 6 fallback).

### Step 6: Delegate to Instagram (REEL mode) — reuses the TikTok video
1. `Read` → `.claude/skills/social-instagram.md`
2. If `VIDEO_URL` is non-empty:
   - `MODE="reel"`
   - Pass `VIDEO_URL` as input — **do NOT re-render**. The subskill's REEL block simply sets `MEDIA_URL="${VIDEO_URL}"`.
   - Write an Instagram-native caption (400–800 chars, hook in first 125 chars, 20–30 hashtag block at end) from the Research Brief
   - Schedule via Metricool at `${TOMORROW}T19:00:00`
3. If `VIDEO_URL` is empty (video pipeline failed):
   - `MODE="image"` (fallback)
   - Generate a fresh 1:1 image via the subskill's IMAGE block with `FILENAME_SLUG=sp2-instagram-${TOMORROW}`
   - Schedule at `${TOMORROW}T19:00:00`
4. Capture the result

### Step 7: Update the Social Queue record
On full/partial success, mark the source record as Used:
```bash
curl -s --retry 3 --retry-delay 2 -X PATCH "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_QUEUE_TABLE}/${RECORD_ID}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"Status": "Used"}}'
```

On full failure (all 4 platforms failed), revert to Queued so the next run can retry:
```bash
-d '{"fields": {"Status": "Queued"}}'
```

### Step 8: Log every scheduled post to Social Posts Log
For each successful platform, create a Social Posts Log record:
```bash
curl -s -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_POSTS_LOG_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Platform": "[facebook|instagram|pinterest|tiktok]",
    "Post Type": "Research Queue",
    "Caption Preview": "[first 100 chars]",
    "Scheduled Time": "[ISO datetime]",
    "Image URL": "[wp_media_url or video_url]"
  }}'
```

For the TikTok (video) and Instagram (reel) records, use the same `VIDEO_URL` — that's the point of one-render-two-platforms.

### Step 9: Telegram alert & SKILL_RESULT
Success (all 4):
```bash
bash /home/agent/project/telegram-alert.sh "✅ social-poster-2 — scheduled 4/4 platforms for '${TOPIC}' (FB static, Pin static, TikTok video, IG Reel) | video: ${VIDEO_URL}"
```

Partial success (some failed): use ⚠ and list which ones failed.

Full failure: use ❌ with details, and ensure the Social Queue record is reverted to Queued.

```
SKILL_RESULT: success | SP2 scheduled [N] posts for "[Topic]" across [platforms] — [video rendered | video fallback] | [video_url if applicable]
```

---

## Error Handling
- **Empty queue** → `SKILL_RESULT: skip | Social Queue empty` + ⚠ Telegram
- **Single subskill fails** → continue with others, partial-success report
- **Video pipeline fails** → TikTok falls back to static 9:16, Instagram falls back to static 1:1 (both platforms still get posts — just no video)
- **Metricool auth error** → revert queue record to Queued, `SKILL_RESULT: fail | Metricool auth error`
- **ElevenLabs fails** → video renders without voiceover (BGM + visuals only) — the pipeline handles this gracefully
- **Jamendo fails** → video renders with cached fallback BGM
- **All 4 platforms fail** → revert queue record to Queued, `SKILL_RESULT: fail | All 4 platforms failed`

---

## Rules
- **ONE topic per session** — pick highest-priority Queued record
- **TikTok VIDEO mode is the default** — SP2 is the video skill; only fall back to static if the pipeline errors
- **NEVER re-render the video for Instagram** — always pass `VIDEO_URL` from the TikTok step to the Instagram subskill
- Always use `flux-2-pro` for all images (static AND video slides)
- Always use `--upload` so images get permanent WP URLs
- Always generate a **unique** image per platform (static platforms) — never reuse
- Always append Jamendo `BGM_ATTRIBUTION` to TikTok and Instagram Reel captions (CC-BY-SA license requirement)
- Schedule everything for TOMORROW with the staggered times above
- Mark the Social Queue record as Used only after at least one platform succeeded
- Only link to live URLs — never drafts
- Always count caption characters before scheduling (platform limits in each subskill)
- Never invent topics — only use what social-researcher queued
