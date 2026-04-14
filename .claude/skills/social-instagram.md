---
type: platform-subskill
platform: instagram
parent_skills: [social-poster-1, social-poster-2]
network_value: instagram
aspect_ratio_image: "1:1"
aspect_ratio_reel: "9:16"
image_model: flux-2-pro
supports_video: true
---

# Social Instagram — Platform Subskill

This is a **subskill** invoked by `social-poster-1` (static image mode) and `social-poster-2` (Reel video mode). Instagram is the only platform that has two modes:

- **IMAGE mode** (SP1): Static square image + caption
- **REEL mode** (SP2): Reuses the video rendered for TikTok (one render, two platforms)

## Inputs (provided by the orchestrator)
- `MODE` — `"image"` or `"reel"`
- `TITLE` — blog post title or research topic
- `CONTENT_SOURCE` — blog URL (SP1) or Research Brief (SP2)
- `LINK_URL` — URL to link out to (Note: IG in-caption links aren't clickable, but good for context)
- `FILENAME_SLUG` — unique filename slug
- `SCHEDULE_TIME` — ISO 8601 datetime
- `VIDEO_URL` — (REEL mode only) permanent WP URL of the rendered MP4 from TikTok pipeline

## Platform Character Rules (Instagram)
| Metric              | Limit |
|---------------------|-------|
| Hard max (API)      | 2,200 chars |
| **Target length**   | **400–800 chars** |
| "…more" cutoff      | ~125 chars (first 125 chars = everything visible in feed) |
| Hashtags            | 20–30 at the end (block style) |

## Step 1: Write an Instagram-native caption
Instagram rewards **visual-first storytelling with a strong opening line**. Write a caption that:
- **Hook in first 125 chars** — this is ALL that's visible before the "…more" tap
- Body: 3–5 short paragraphs with emoji punctuation, 2–3 key insights
- CTA: "Tap the link in bio" (IG doesn't linkify caption URLs) — reference the blog/shop
- **Hashtag block at the end** — 20–30 hashtags in a dedicated block, separated from body by 3–4 dots on their own lines
- Match brand voice from CLAUDE.md

**Hashtag strategy:**
- Broad (5–7): industry-wide tags for discoverability
- Niche (10–15): specific to your topic/product area
- Brand (5–8): your brand and product hashtags

**Hook examples (first 125 chars):**
- ✅ "[Surprising fact or question that stops the scroll] Here's why it matters →"
- ❌ "We wrote a new blog post today. Check it out to learn more about..."

**Count the character total including hashtags before scheduling.**

## Step 2: Generate the media

### IMAGE mode (SP1)
Instagram square (1:1) is the safest format for feed posts.

```bash
IMAGE_JSON=$(bash /home/agent/project/generate-image.sh \
  --model flux-2-pro \
  --prompt "[Instagram-specific prompt — match brand image style, SQUARE composition with strong centered focal point, color-rich background, no text]" \
  --aspect-ratio "1:1" \
  --filename "${FILENAME_SLUG}" \
  --upload)

MEDIA_URL=$(echo "$IMAGE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['wp_media_url'])")
```

### REEL mode (SP2)
**Do NOT re-render video.** Reuse the exact same `VIDEO_URL` passed from the TikTok subskill (one render, two platforms).

```bash
MEDIA_URL="${VIDEO_URL}"
# No generation step — the orchestrator handles video production in social-tiktok.md
```

## Step 3: Schedule via Metricool

**CRITICAL:** You MUST set `instagramData.type` explicitly. Metricool does NOT auto-detect post type from media. Omitting it (or setting only `autoPublish: true`) causes the error: *"Auto publish (post) → Instagram does not allow single-video posts. Change the Instagram post type to REEL"*.

- `MODE=image` → `"instagramData": {"type": "POST", "autoPublish": true}`
- `MODE=reel`  → `"instagramData": {"type": "REEL", "showReelOnFeed": true, "autoPublish": true}`

```bash
BLOG_ID="${METRICOOL_BLOG_ID:-}"

# Build instagramData based on MODE
if [ "${MODE}" = "reel" ]; then
  INSTAGRAM_DATA='{"type": "REEL", "showReelOnFeed": true, "autoPublish": true}'
else
  INSTAGRAM_DATA='{"type": "POST", "autoPublish": true}'
fi

curl -s -X POST "https://app.metricool.com/api/v2/scheduler/posts?blogId=${BLOG_ID}" \
  -H "Content-Type: application/json" \
  -H "X-Mc-Auth: ${METRICOOL_API_TOKEN}" \
  -d "{
    \"text\": \"[your instagram caption with hashtag block]\",
    \"providers\": [{\"network\": \"instagram\"}],
    \"publicationDate\": {\"dateTime\": \"${SCHEDULE_TIME}\", \"timezone\": \"${SCHEDULE_TIMEZONE}\"},
    \"draft\": false,
    \"autoPublish\": true,
    \"media\": [\"${MEDIA_URL}\"],
    \"instagramData\": ${INSTAGRAM_DATA}
  }"
```

**Valid `instagramData.type` values:** `POST` (feed image/carousel), `REEL` (9:16 video), `STORY`.

## Step 4: Return result to orchestrator
Return:
- `platform`: `"instagram"`
- `mode`: `"image"` or `"reel"`
- `status`: `"scheduled"` | `"failed"`
- `caption_preview`: first 100 chars
- `media_url`: `$MEDIA_URL`
- `scheduled_time`: `$SCHEDULE_TIME`
- `metricool_response_code`: HTTP code

## Rules
- First 125 chars is the ONLY visible caption in-feed — put the hook there.
- Hashtag block must be 20–30, placed at the END, not sprinkled in the body.
- IMAGE mode: always 1:1, always `flux-2-pro`.
- REEL mode: NEVER re-render — always reuse `VIDEO_URL` from the TikTok pipeline.
- Always `--upload` so WP URL is permanent (image mode).
- **ALWAYS set `instagramData.type` explicitly** — `REEL` for video, `POST` for image. Metricool does NOT auto-detect. Missing this field causes the error *"Instagram does not allow single-video posts"*. `showReelOnFeed: true` is required for REEL to also appear in the main feed grid.
