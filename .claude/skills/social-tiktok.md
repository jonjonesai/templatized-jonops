---
type: platform-subskill
platform: tiktok
parent_skills: [social-poster-1, social-poster-2]
network_value: tiktok
aspect_ratio_image: "9:16"
aspect_ratio_video: "9:16"
image_model: flux-2-pro
video_engine: almanac
supports_video: true
version: 3.0.0
---

# Social TikTok — Platform Subskill (Almanac edition)

This is a **subskill** invoked by `social-poster-1` (static image mode) and `social-poster-2` (full video pipeline mode).

TikTok has two execution modes:

| Mode | Caller | Engine | Output |
|------|--------|--------|--------|
| **STATIC** | SP1 | flux-2-pro | 9:16 vertical image via `generate-image.sh` |
| **VIDEO** | SP2 | **Almanac (HyperFrames + GSAP)** | 25–55s MP4 with karaoke captions via `almanac/almanac_pipeline.py` |

**VIDEO mode is the flagship.** Almanac generates a 7-beat warm-hug script (per-beat content contract + `verified_facts` injection), renders with HyperFrames karaoke captions, AI-generated BGM via Replicate MusicGen, and word-level timing via Replicate WhisperX. The rendered MP4 is shared with `social-instagram.md` (Reel mode) — one render, two platforms.

> **Migration note (2026-05-16):** This skill v3 replaces the previous Remotion-based path (`generate-tiktok-video.sh` + `remotion/render-ffmpeg.py` + Jamendo BGM). Almanac brings karaoke captions, beat-synced cuts, the warm-hug doctrine, and a per-brand visual identity loaded from `almanac/<brand-slug>/brand.json` + `DESIGN.md`.

## Inputs (provided by the orchestrator)
- `MODE` — `"static"` or `"video"`
- `TITLE` — research topic title (becomes the topic_title on the title card)
- `CONTENT_SOURCE` — Research Brief from Airtable (Almanac extracts `verified_facts` block if present)
- `LINK_URL` — URL referenced in caption (or LinkInBio)
- `FILENAME_SLUG` — unique slug (e.g., `sp2-tiktok-2026-04-10`)
- `SCHEDULE_TIME` — ISO 8601 datetime
- `BRAND_SLUG` — must match the per-container brand dir at `almanac/<BRAND_SLUG>/`

**Inputs no longer needed in VIDEO mode** (Almanac derives these from brand.json / DESIGN.md / its own script-gen):
- ~~`NARRATION_TEXT`~~ — Almanac generates the 7-beat script from the brief
- ~~`SLIDE_PROMPTS`~~ — Almanac generates per-beat Freepik/FLUX queries
- ~~`MOOD`~~ — Almanac uses brand.json `music_prompt` for MusicGen

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
- Match brand voice from `almanac/<brand-slug>/brand.json` + CLAUDE.md

**Hook examples:**
- ✅ "POV: you discover [surprising thing about your niche] 🔥"
- ✅ "[Topic] ranked by experts — #1 isn't what you think 🤯"
- ❌ "Hello everyone! Today we want to share with you our newest blog post..."

**No music attribution needed.** Almanac uses Replicate MusicGen (AI-generated original score per video). Unlike Jamendo, no caption credit is required.

## Step 2: Produce the media

### STATIC mode (SP1 — simple image)
```bash
IMAGE_JSON=$(bash /home/agent/project/generate-image.sh \
  --model flux-2-pro \
  --prompt "[TikTok-specific prompt — vertical 9:16 composition, match brand image style, bold centered focal subject, high contrast, scroll-stopping colors]" \
  --aspect-ratio "9:16" \
  --filename "${FILENAME_SLUG}" \
  --upload)

MEDIA_URL=$(echo "$IMAGE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['cdn_url'])")
VIDEO_URL=""  # static mode has no video
```

### VIDEO mode (SP2 — Almanac pipeline)
**This is the flagship path.** Invoke Almanac with the Research Brief as `--angle-override`. Almanac internally chains: Claude (7-beat script with warm-hug doctrine + `verified_facts`) → Freepik / FLUX (per-beat imagery) → ElevenLabs (voiceover with brand `voice_id`) → Replicate WhisperX (word-level timing for karaoke) → Replicate MusicGen (AI BGM from brand `music_prompt`) → HyperFrames + GSAP composition → render → Cloudinary upload.

The `--skip-metricool` flag tells Almanac NOT to schedule its own Metricool post; we'll do that ourselves in Step 3 below with TikTok-specific caption + hashtags.

```bash
# Invoke Almanac with the orchestrator-provided topic + brief
ALMANAC_RESULT="/tmp/almanac-${FILENAME_SLUG}.json"

python3 /opt/jonops/almanac/almanac_pipeline.py \
  --brand "${BRAND_SLUG}" \
  --topic-override "${TITLE}" \
  --angle-override "${CONTENT_SOURCE}" \
  --skip-metricool \
  --json-output "${ALMANAC_RESULT}"

# Extract cloudinary URL from structured result
VIDEO_URL=$(python3 -c "import json; d=json.load(open('${ALMANAC_RESULT}')); print(d.get('video_url',''))")
TOPIC_TITLE=$(python3 -c "import json; d=json.load(open('${ALMANAC_RESULT}')); print(d.get('topic_title',''))")
HERO_STILL_URL=$(python3 -c "import json; d=json.load(open('${ALMANAC_RESULT}')); print(d.get('hero_still_url',''))")

MEDIA_URL="${VIDEO_URL}"
```

**Verified_facts (recommended):** if the Research Brief from Airtable contains a delimited `[VERIFIED_FACTS_JSON_START]` … `[VERIFIED_FACTS_JSON_END]` block (the brand's topic researcher embedded it), Almanac will extract it automatically and require Claude to quote literal values from it. This is how drift on numerical claims gets eliminated. See `almanac/docs/VERIFIED_FACTS.md`.

**2e — Fallback chain (VIDEO mode only):**
If Almanac exits non-zero or `video_url` is empty:
1. Log Almanac's stderr/stdout to the orchestrator (visible in container logs)
2. Fall back to STATIC mode (single 9:16 image via the STATIC block above)
3. Set `VIDEO_URL=""` so the parent orchestrator knows Instagram Reels must also fall back to a 1:1 static image

## Step 3: Schedule via Metricool
```bash
BLOG_ID="${METRICOOL_BLOG_ID:-}"
FINAL_CAPTION="[your caption — no music attribution needed; MusicGen is original-per-video]"

curl -s -X POST "https://app.metricool.com/api/v2/scheduler/posts?userToken=${METRICOOL_API_TOKEN}&blogId=${BLOG_ID}" \
  -H "Content-Type: application/json" \
  -H "X-Mc-Auth: ${METRICOOL_API_TOKEN}" \
  -d "{
    \"text\": \"${FINAL_CAPTION}\",
    \"providers\": [{\"network\": \"tiktok\"}],
    \"publicationDate\": {\"dateTime\": \"${SCHEDULE_TIME}\", \"timezone\": \"${SCHEDULE_TIMEZONE}\"},
    \"draft\": false,
    \"autoPublish\": true,
    \"media\": [\"${MEDIA_URL}\"],
    \"videoCoverMilliseconds\": 3000,
    \"tiktokData\": {\"privacyOption\": \"PUBLIC_TO_EVERYONE\", \"disableComment\": false, \"disableDuet\": false, \"disableStitch\": false, \"commercialContentOwnBrand\": false, \"commercialContentThirdParty\": false, \"isAigc\": false}
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
- `topic_title`: `$TOPIC_TITLE` (Almanac's framed title — useful for IG caption)
- `hero_still_url`: `$HERO_STILL_URL` (for FB / Pinterest reuse if present)
- `scheduled_time`: `$SCHEDULE_TIME`
- `metricool_response_code`: HTTP code

## Rules
- **STATIC mode**: always 9:16, always `flux-2-pro`, always `--upload`. Use `cdn_url` for Metricool `media` field.
- **VIDEO mode (Almanac)**: brand-slug must match a directory at `almanac/<slug>/` containing `brand.json` + `DESIGN.md` + `scripts/build-karaoke-html.py`. If missing, see `almanac/docs/BRAND_ONBOARDING.md`.
- **No music attribution** in video captions — MusicGen output is original and unencumbered.
- **Never re-render the video for Instagram Reels** — always reuse `$VIDEO_URL`.
- If Almanac fails, fall back to static image and set `video_url=""` so the orchestrator knows IG must also fall back.
- Caption: 150–300 chars target, 3–5 hashtags, no line breaks.
- Almanac handles its own script generation, media, voice, music, render, and Cloudinary upload — do not try to pre-generate any of those from the orchestrator. Only pass the topic title + Research Brief.
