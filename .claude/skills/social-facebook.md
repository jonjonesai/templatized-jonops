---
type: platform-subskill
platform: facebook
parent_skills: [social-poster-1, social-poster-2]
network_value: facebook
aspect_ratio: "16:9"
image_model: flux-2-pro
---

# Social Facebook — Platform Subskill

This is a **subskill** invoked by `social-poster-1` (blog repurpose) and `social-poster-2` (researcher queue). It owns all Facebook-specific logic.

## Inputs (provided by the orchestrator)
- `TITLE` — blog post title or research topic
- `CONTENT_SOURCE` — either a blog URL (SP1) or a Research Brief (SP2)
- `LINK_URL` — the URL to link out to (blog post for SP1, shop/homepage for SP2)
- `FILENAME_SLUG` — unique filename slug (e.g., `sp1-facebook-2026-04-10`)
- `SCHEDULE_TIME` — ISO 8601 datetime for Metricool scheduling

## Platform Character Rules (Facebook)
| Metric              | Limit |
|---------------------|-------|
| Hard max (API)      | 16,192 chars |
| **Target length**   | **300–480 chars** |
| "See More" cutoff   | ~480 chars |
| Hook length         | First 80 chars must grab attention |
| Hashtags            | 5–8 relevant |

## Step 1: Write a Facebook-native caption
Facebook rewards **storytelling, engagement hooks, and shareable insights**. Write a caption that:
- **Starts with an emotional hook** (first 80 chars) — ask a question, share a surprising fact, or paint a vivid scene
- Contains 3–5 key insights from the blog/brief
- Ends with a soft CTA to the `LINK_URL` ("Read the full story →")
- Includes 5–8 hashtags at the end (mix of broad + niche for your industry)
- Matches brand voice from CLAUDE.md
- Never uses hard-sell language

**Hook examples:**
- ✅ "Ever wondered why [topic] works this way?"
- ✅ "[Surprising fact] — here's the real story."
- ❌ "Check out our new blog post about [topic]!"

**Count the character total before scheduling.** If over 480, trim.

## Step 2: Generate a unique Facebook image
Facebook performs best with **landscape (16:9)** images that carry text-free visual weight.

```bash
IMAGE_JSON=$(bash /home/agent/project/generate-image.sh \
  --model flux-2-pro \
  --prompt "[Facebook-specific prompt — match brand image style from CLAUDE.md, landscape composition with focal subject centered, no text overlays]" \
  --aspect-ratio "16:9" \
  --filename "${FILENAME_SLUG}" \
  --upload)

IMAGE_URL=$(echo "$IMAGE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['cdn_url'])")
```

Always use `cdn_url` (Cloudinary) for Metricool scheduling — never `wp_media_url`. WordPress may auto-convert uploads to WebP, which Meta's API rejects. `cdn_url` is a permanent JPEG on Cloudinary's CDN.

## Step 3: Schedule via Metricool
```bash
BLOG_ID="${METRICOOL_BLOG_ID:-}"

curl -s -X POST "https://app.metricool.com/api/v2/scheduler/posts?userToken=${METRICOOL_API_TOKEN}&blogId=${BLOG_ID}" \
  -H "Content-Type: application/json" \
  -H "X-Mc-Auth: ${METRICOOL_API_TOKEN}" \
  -d "{
    \"text\": \"[your facebook caption]\",
    \"providers\": [{\"network\": \"facebook\"}],
    \"publicationDate\": {\"dateTime\": \"${SCHEDULE_TIME}\", \"timezone\": \"${SCHEDULE_TIMEZONE}\"},
    \"draft\": false,
    \"autoPublish\": true,
    \"media\": [\"${IMAGE_URL}\"]
  }"
```

## Step 4: Return result to orchestrator
Return (to the parent orchestrator):
- `platform`: `"facebook"`
- `status`: `"scheduled"` | `"failed"`
- `caption_preview`: first 100 chars
- `image_url`: `$IMAGE_URL`
- `scheduled_time`: `$SCHEDULE_TIME`
- `metricool_response_code`: HTTP code from the API call

## Rules
- **One call per invocation** — this subskill posts ONE image-based Facebook post.
- Always use `flux-2-pro` for premium quality (the orchestrator pays for it).
- Always `--upload` so both WP and Cloudinary URLs are generated.
- Always use `cdn_url` (not `wp_media_url`) for the Metricool `media` field — Meta APIs reject WebP.
- Caption must be 300–480 chars. Count before scheduling.
- Hook must fit in first 80 chars.
- Never hard-sell. Never use `{{placeholder}}` text.
