---
type: platform-subskill
platform: tiktok
parent_skills: [social-poster-1, social-poster-2]
network_value: tiktok
aspect_ratio_image: "9:16"
aspect_ratio_video: "9:16"
image_model: flux-2-pro
supports_video: true
---

# Social TikTok — Platform Subskill

This is a **subskill** invoked by `social-poster-1` (static image mode) and `social-poster-2` (full video pipeline mode).

TikTok has two execution modes:

| Mode | Caller | Output |
|------|--------|--------|
| **STATIC** | SP1 | 9:16 vertical image via `generate-image.sh` |
| **VIDEO** | SP2 | 15–25s MP4 via `generate-tiktok-video.sh` (slides + BGM + voiceover) |

**VIDEO mode is the important one.** The rendered MP4 is shared with `social-instagram.md` (Reel mode) — one render, two platforms.

## Inputs (provided by the orchestrator)
- `MODE` — `"static"` or `"video"`
- `TITLE` — blog post title or research topic
- `CONTENT_SOURCE` — blog URL (SP1) or Research Brief (SP2)
- `LINK_URL` — URL referenced in caption (or LinkInBio)
- `FILENAME_SLUG` — unique slug (e.g., `sp2-tiktok-2026-04-10`)
- `SCHEDULE_TIME` — ISO 8601 datetime
- `NARRATION_TEXT` — (video mode) 2–4 sentence voiceover script (max 500 chars, cost-capped by ElevenLabs helper)
- `SLIDE_PROMPTS` — (video mode) 3–4 image prompts describing each video scene
- `MOOD` — (video mode) BGM mood tag (see Mood mapping below)

## Platform Character Rules (TikTok)
| Metric              | Limit |
|---------------------|-------|
| Hard max (API)      | 2,200 chars |
| **Target length**   | **150–300 chars** |
| Line breaks         | Avoid — TikTok API sometimes strips them |
| Hashtags            | 3–5 (trending + niche) |

## Step 1: Write a TikTok-native caption
TikTok rewards **short, punchy, trend-aware copy**. Structure:
- One hook line (curious, bold, or pattern-interrupting)
- Optional one-line payoff
- 3–5 hashtags at the end (all on the same line, no line breaks)
- Match brand voice from CLAUDE.md

**Hook examples:**
- ✅ "POV: you discover [surprising thing about your niche] 🔥"
- ✅ "[Topic] ranked by experts — #1 isn't what you think 🤯"
- ❌ "Hello everyone! Today we want to share with you our newest blog post..."

**Video mode — music attribution:** Always append `Music: [track_name] by [artist] via Jamendo` to the end of the caption (the Jamendo response provides this as `bgm.attribution`).

## Step 2: Produce the media

### STATIC mode (SP1 — simple image)
```bash
IMAGE_JSON=$(bash /home/agent/project/generate-image.sh \
  --model flux-2-pro \
  --prompt "[TikTok-specific prompt — vertical 9:16 composition, match brand image style, bold centered focal subject, high contrast, scroll-stopping colors]" \
  --aspect-ratio "9:16" \
  --filename "${FILENAME_SLUG}" \
  --upload)

MEDIA_URL=$(echo "$IMAGE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['wp_media_url'])")
VIDEO_URL=""  # static mode has no video
```

### VIDEO mode (SP2 — full pipeline)
**This is the flagship path.** Invoke `generate-tiktok-video.sh`, which chains: flux-2-pro slide generation → Jamendo BGM → ElevenLabs voiceover → render-ffmpeg.py → WP upload.

**2a — Prepare the slide prompts (3–4 recommended):**
Write each prompt to describe a distinct scene that supports the narration arc. Each slide shows for 7 seconds.
- Slide 1: Opening wide shot / scene-setter
- Slide 2: Mid-beat (main subject close-up)
- Slide 3: Payoff / reveal
- (Optional) Slide 4: CTA beat

Prompts must describe scenes matching the brand image style from CLAUDE.md: vertical 9:16 composition, no text.

**2b — Write the narration text:**
- 2–4 short sentences, natural spoken cadence
- Max ~300 chars (≈24s at 12.5 chars/sec; ElevenLabs helper caps at 500)
- Conversational, warm — not narrated like a documentary
- **Voice:** Configured in `elevenlabs-tts.sh` (default: George, voice ID `JBFqnCBsd6RMkjVDRZzb`)
- **Audio mix:** BGM is set to **20%** volume in `generate-tiktok-video.sh` (`bgMusicVolume: 0.20`). BGM auto-ducks to 8% during narration sections via `render-ffmpeg.py`.

**2c — Pick a mood for BGM:**

| Content angle | Mood tag |
|---------------|----------|
| Cultural / heritage / educational | `chill,world` |
| Food / energetic / fun | `upbeat,pop` |
| Nature / travel / landscapes | `ambient,electronic` |
| Product drop / hype | `energetic,hiphop` |

**2d — Invoke the video pipeline:**
```bash
# Build pipe-separated slide prompts
SLIDES_PIPE="[prompt1]|[prompt2]|[prompt3]|[prompt4]"

VIDEO_JSON=$(bash /home/agent/project/generate-tiktok-video.sh \
  --title "${TITLE}" \
  --subtitle "${BRAND_URL}" \
  --slides "${SLIDES_PIPE}" \
  --narration-text "${NARRATION_TEXT}" \
  --mood "${MOOD}" \
  --filename "${FILENAME_SLUG}")

# The script uploads to WP automatically — extract the permanent URL
VIDEO_URL=$(echo "$VIDEO_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('video_url',''))")
BGM_ATTRIBUTION=$(echo "$VIDEO_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('bgm',{}).get('attribution',''))")

MEDIA_URL="${VIDEO_URL}"
```

**2e — Fallback chain (VIDEO mode only):**
If `generate-tiktok-video.sh` fails or returns an empty `video_url`:
1. Fall back to STATIC mode (generate a single 9:16 image via the STATIC block above)
2. Set `VIDEO_URL=""` so the parent orchestrator knows Instagram Reels must also fall back to a 1:1 static image
3. Log the failure reason to the orchestrator

## Step 3: Schedule via Metricool
```bash
BLOG_ID="${METRICOOL_BLOG_ID:-}"

# Append Jamendo attribution to caption in video mode
if [[ -n "${BGM_ATTRIBUTION:-}" ]]; then
  FINAL_CAPTION="[your caption] ${BGM_ATTRIBUTION}"
else
  FINAL_CAPTION="[your caption]"
fi

curl -s -X POST "https://app.metricool.com/api/v2/scheduler/posts?userToken=${METRICOOL_API_TOKEN}&blogId=${BLOG_ID}" \
  -H "Content-Type: application/json" \
  -H "X-Mc-Auth: ${METRICOOL_API_TOKEN}" \
  -d "{
    \"text\": \"${FINAL_CAPTION}\",
    \"providers\": [{\"network\": \"tiktok\"}],
    \"publicationDate\": {\"dateTime\": \"${SCHEDULE_TIME}\", \"timezone\": \"${SCHEDULE_TIMEZONE}\"},
    \"draft\": false,
    \"autoPublish\": true,
    \"media\": [\"${MEDIA_URL}\"]
  }"
```

**Note:** TikTok does not support outbound links in captions (only Link-in-Bio). Don't include `LINK_URL` in the caption body.

## Step 4: Return result to orchestrator
Return the following so the parent orchestrator can pass `VIDEO_URL` to `social-instagram.md` for Reel reuse:
- `platform`: `"tiktok"`
- `mode`: `"static"` or `"video"`
- `status`: `"scheduled"` | `"failed"`
- `caption_preview`: first 100 chars
- `media_url`: `$MEDIA_URL` (image OR video URL)
- `video_url`: `$VIDEO_URL` (empty string if static or fallback)
- `bgm_attribution`: Jamendo attribution (video mode only)
- `scheduled_time`: `$SCHEDULE_TIME`
- `metricool_response_code`: HTTP code

## Rules
- **STATIC mode**: always 9:16, always `flux-2-pro`, always `--upload`.
- **VIDEO mode**: always 3–4 slides (render-script requires ≥2 but aim for 3–4 for narrative pacing).
- Narration text is cost-capped at 500 chars. Write 2–4 sentences, ~300 chars target.
- Always append Jamendo attribution to video captions — it's a license requirement for CC-BY-SA.
- **Never re-render the video for Instagram Reels** — always reuse `$VIDEO_URL`.
- If video pipeline fails, fall back to static image and set `video_url=""` so the orchestrator knows IG must also fall back.
- Caption: 150–300 chars target, 3–5 hashtags, no line breaks.
