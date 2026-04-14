#!/usr/bin/env bash
# generate-tiktok-video.sh — End-to-end TikTok / Instagram Reel video pipeline.
#
# Pipeline:
#   1. Generate N slide images via Replicate (flux-2-pro, 9:16)
#   2. Download royalty-free BGM from Jamendo (commercial-safe CC licenses only)
#   3. Generate voiceover narration via ElevenLabs (George voice)
#   4. Render final MP4 via remotion/render-ffmpeg.py
#   5. Upload to WordPress media library
#   6. Return JSON with video URL + metadata
#
# Usage:
#   bash generate-tiktok-video.sh \
#     --title "Night Market Magic" \
#     --subtitle "Shilin after dark" \
#     --slides "Bustling Shilin market at night|Grilled squid sizzling on grill|Bubble tea vendor in neon light|Neon-lit food stalls with crowds" \
#     --narration-text "Taiwan's night markets are legendary..." \
#     --mood "upbeat" \
#     --filename "tiktok-2026-04-10"
#
# Output: JSON with video_url, wp_media_id, local_path, duration, file_size, etc.
# Exit codes: 0 = success, 1 = fatal failure (caller should fall back to static image).

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────────
TITLE="JonOps Video"
TITLE_EN=""
SUBTITLE=""
SLIDES=""
NARRATION_TEXT=""
MOOD="upbeat"
FILENAME="tiktok-$(date +%s)"
SLIDE_DURATION=7
IMAGE_STYLE=""  # optional: extra style instructions appended to each slide prompt
DO_UPLOAD=true  # upload to WP by default

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title)           TITLE="$2"; shift 2 ;;
    --title-en)        TITLE_EN="$2"; shift 2 ;;
    --subtitle)        SUBTITLE="$2"; shift 2 ;;
    --slides)          SLIDES="$2"; shift 2 ;;
    --narration-text)  NARRATION_TEXT="$2"; shift 2 ;;
    --mood)            MOOD="$2"; shift 2 ;;
    --filename)        FILENAME="$2"; shift 2 ;;
    --slide-duration)  SLIDE_DURATION="$2"; shift 2 ;;
    --image-style)     IMAGE_STYLE="$2"; shift 2 ;;
    --no-upload)       DO_UPLOAD=false; shift ;;
    *) echo '{"error":"Unknown argument: '"$1"'"}'; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLIC_DIR="${SCRIPT_DIR}/remotion/public"
OUT_DIR="${SCRIPT_DIR}/remotion/out"
mkdir -p "$PUBLIC_DIR" "$OUT_DIR"

die() {
  python3 -c "import json,sys; print(json.dumps({'error': sys.argv[1]}))" "$1"
  exit 1
}

if [[ -z "$SLIDES" ]]; then
  die "--slides is required (pipe-separated image prompts)"
fi

# Split slides into array (pipe-delimited)
IFS='|' read -r -a SLIDE_PROMPTS <<< "$SLIDES"
NUM_SLIDES=${#SLIDE_PROMPTS[@]}

if [[ $NUM_SLIDES -lt 2 ]]; then
  die "need at least 2 slides (got ${NUM_SLIDES})"
fi

>&2 echo "🎬 Video pipeline starting: ${TITLE}"
>&2 echo "  Slides:     ${NUM_SLIDES}"
>&2 echo "  Mood:       ${MOOD}"
>&2 echo "  Filename:   ${FILENAME}"

# ── Step 1: Generate slide images ────────────────────────────────────────────
>&2 echo ""
>&2 echo "Step 1/5: Generating ${NUM_SLIDES} slide images via Replicate flux-2-pro..."

SLIDE_FILES=()
SLIDE_PROMPTS_USED=()

for i in "${!SLIDE_PROMPTS[@]}"; do
  num=$((i + 1))
  prompt="${SLIDE_PROMPTS[$i]}"
  if [[ -n "$IMAGE_STYLE" ]]; then
    prompt="${prompt}. ${IMAGE_STYLE}"
  fi

  slide_filename="${FILENAME}-slide-${num}"
  >&2 echo "  [${num}/${NUM_SLIDES}] Generating: ${prompt:0:60}..."

  slide_json=$(bash "${SCRIPT_DIR}/generate-image.sh" \
    --model flux-2-pro \
    --prompt "$prompt" \
    --aspect-ratio "9:16" \
    --filename "$slide_filename" 2>&2) || {
      >&2 echo "  ⚠ Slide ${num} generation failed — skipping"
      continue
    }

  # Copy generated image to remotion/public/ so render-ffmpeg.py can find it
  slide_local=$(echo "$slide_json" | python3 -c "import json,sys; print(json.load(sys.stdin).get('local_path',''))")
  if [[ -z "$slide_local" || ! -f "$slide_local" ]]; then
    >&2 echo "  ⚠ Slide ${num} local file missing — skipping"
    continue
  fi

  public_name="${slide_filename}.webp"
  cp "$slide_local" "${PUBLIC_DIR}/${public_name}"
  SLIDE_FILES+=("$public_name")
  SLIDE_PROMPTS_USED+=("$prompt")
done

if [[ ${#SLIDE_FILES[@]} -lt 2 ]]; then
  die "generated fewer than 2 slides (${#SLIDE_FILES[@]}) — cannot render video"
fi

>&2 echo "  ✓ Generated ${#SLIDE_FILES[@]} slides"

# ── Step 2: Download BGM from Jamendo ────────────────────────────────────────
>&2 echo ""
>&2 echo "Step 2/5: Downloading BGM from Jamendo (mood=${MOOD})..."

BGM_PUBLIC_NAME="${FILENAME}-bgm.mp3"
BGM_LOCAL="${PUBLIC_DIR}/${BGM_PUBLIC_NAME}"

BGM_JSON=$(bash "${SCRIPT_DIR}/jamendo-download.sh" \
  --mood "$MOOD" \
  --no-cache \
  --output "$BGM_LOCAL" 2>&2) || {
    >&2 echo "  ⚠ Jamendo failed — using fallback BGM"
    cp "${PUBLIC_DIR}/bgm-upbeat-newyear.mp3" "$BGM_LOCAL" 2>/dev/null || die "no fallback BGM available"
    BGM_JSON='{"track_id":"fallback","track_name":"bgm-upbeat-newyear","artist":"local","license":"local","source":"fallback"}'
  }

BGM_TRACK_NAME=$(echo "$BGM_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('track_name','unknown'))" 2>/dev/null || echo "unknown")
BGM_ARTIST=$(echo "$BGM_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('artist','unknown'))" 2>/dev/null || echo "unknown")
BGM_LICENSE=$(echo "$BGM_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('license','unknown'))" 2>/dev/null || echo "unknown")

>&2 echo "  ✓ BGM: ${BGM_TRACK_NAME} by ${BGM_ARTIST}"

# ── Step 3: Generate voiceover narration ─────────────────────────────────────
NARRATION_PUBLIC_NAME=""
HAS_VOICEOVER=false

if [[ -n "$NARRATION_TEXT" ]]; then
  >&2 echo ""
  >&2 echo "Step 3/5: Generating voiceover via ElevenLabs (George voice)..."

  NARRATION_PUBLIC_NAME="${FILENAME}-voiceover.mp3"
  NARRATION_LOCAL="${PUBLIC_DIR}/${NARRATION_PUBLIC_NAME}"

  if bash "${SCRIPT_DIR}/elevenlabs-tts.sh" \
       --text "$NARRATION_TEXT" \
       --output "$NARRATION_LOCAL" 1>&2; then
    HAS_VOICEOVER=true
    >&2 echo "  ✓ Voiceover generated"
  else
    >&2 echo "  ⚠ ElevenLabs failed — rendering without voiceover"
    NARRATION_PUBLIC_NAME=""
    rm -f "$NARRATION_LOCAL"
  fi
else
  >&2 echo ""
  >&2 echo "Step 3/5: Skipped (no --narration-text provided)"
fi

# ── Step 4: Build render config and render video ────────────────────────────
>&2 echo ""
>&2 echo "Step 4/5: Rendering video via render-ffmpeg.py..."

CONFIG_FILE="/tmp/${FILENAME}-config.json"
OUTPUT_MP4="${FILENAME}.mp4"

# Build config JSON via Python so JSON is well-formed.
# Also splits the narration text into per-slide caption chunks so the
# subtitle bar at the bottom of the video stays in rough sync with what
# George's voiceover is saying.
python3 - "$CONFIG_FILE" "$TITLE" "$TITLE_EN" "$SUBTITLE" "$OUTPUT_MP4" \
         "$BGM_PUBLIC_NAME" "$NARRATION_PUBLIC_NAME" "$SLIDE_DURATION" \
         "$NARRATION_TEXT" \
         "${SLIDE_FILES[@]}" << 'PYEOF'
import json, re, sys
config_path = sys.argv[1]
title = sys.argv[2]
title_en = sys.argv[3]
subtitle = sys.argv[4]
output_file = sys.argv[5]
bgm = sys.argv[6]
narration = sys.argv[7]
slide_dur = int(sys.argv[8])
narration_text = sys.argv[9]
slide_files = sys.argv[10:]

# Split narration into sentence-ish chunks and distribute evenly across slides
# so each slide gets a subtitle line roughly matching what's being spoken.
def split_narration_for_slides(text, n_slides):
    if not text or n_slides <= 0:
        return [""] * n_slides
    # Split on sentence boundaries (., !, ?) while keeping the punctuation.
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
    if not sentences:
        return [""] * n_slides
    # Distribute sentences into n_slides roughly-equal buckets.
    buckets = [[] for _ in range(n_slides)]
    per = max(1, len(sentences) / n_slides)
    for i, sent in enumerate(sentences):
        idx = min(int(i / per), n_slides - 1)
        buckets[idx].append(sent)
    # If some buckets ended up empty (fewer sentences than slides), leave them empty.
    return [" ".join(b).strip() for b in buckets]

slide_captions = split_narration_for_slides(narration_text, len(slide_files))

slides = []
for i, sf in enumerate(slide_files):
    slide = {
        "file": sf,
        "durationSec": slide_dur,
        "zoom": "in" if i % 2 == 0 else "out",
    }
    if slide_captions[i]:
        slide["caption"] = slide_captions[i]
    slides.append(slide)

config = {
    "composition": "ReelShort",
    "title": title,
    "title_en": title_en,
    "subtitle": subtitle,
    "outputFile": output_file,
    "slides": slides,
    "bgMusicFile": bgm,
    "bgMusicVolume": 0.20,  # 20% — keeps George's voiceover clearly audible over BGM (ducks to 8% during narration)
    "showIntro": True,
    "showOutro": True,
    "outroDuration": 3,
    "logoFile": "logo.png",
}

if narration:
    config["narrationFile"] = narration
    config["narrationDelay"] = 3.0

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
PYEOF

if ! python3 "${SCRIPT_DIR}/remotion/render-ffmpeg.py" \
       --config "$CONFIG_FILE" \
       --public-dir "$PUBLIC_DIR" \
       --out-dir "$OUT_DIR" 1>&2; then
  die "render-ffmpeg.py failed"
fi

OUTPUT_PATH="${OUT_DIR}/${OUTPUT_MP4}"

if [[ ! -s "$OUTPUT_PATH" ]]; then
  die "rendered video is empty: ${OUTPUT_PATH}"
fi

FILE_SIZE=$(stat -c%s "$OUTPUT_PATH" 2>/dev/null || stat -f%z "$OUTPUT_PATH" 2>/dev/null || echo "0")
DURATION=$(python3 -c "
import subprocess
r = subprocess.run(['${SCRIPT_DIR}/remotion/node_modules/@remotion/compositor-linux-x64-gnu/ffprobe',
                   '-v','error','-show_entries','format=duration',
                   '-of','default=noprint_wrappers=1:nokey=1','${OUTPUT_PATH}'],
                   capture_output=True, text=True)
try:
    print(round(float(r.stdout.strip()), 1))
except:
    print(0)
")

>&2 echo "  ✓ Rendered: ${OUTPUT_PATH} (${FILE_SIZE} bytes, ${DURATION}s)"

# ── Step 5: Upload to WordPress (optional) ──────────────────────────────────
WP_MEDIA_ID=0
WP_MEDIA_URL=""

if [[ "$DO_UPLOAD" == "true" ]]; then
  >&2 echo ""
  >&2 echo "Step 5/5: Uploading to WordPress media library..."

  WP_USER="${WP_USERNAME:-}"
  WP_PASS="${WP_PASSWORD:-}"
  WP_BASE="${WP_URL:-}"

  if [[ -z "$WP_BASE" || -z "$WP_USER" || -z "$WP_PASS" ]]; then
    >&2 echo "  ⚠ WordPress credentials not set — skipping upload"
  else
    UPLOAD_RESPONSE=$(curl -s --max-time 180 \
      -X POST "${WP_BASE}/wp-json/wp/v2/media" \
      -u "${WP_USER}:${WP_PASS}" \
      -H "Content-Disposition: attachment; filename=${FILENAME}.mp4" \
      -H "Content-Type: video/mp4" \
      --data-binary "@${OUTPUT_PATH}" || echo '')

    read -r WP_MEDIA_ID WP_MEDIA_URL < <(echo "$UPLOAD_RESPONSE" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('id',''), d.get('source_url',''))
except Exception:
    print('', '')
" 2>/dev/null || echo " ")

    if [[ -z "$WP_MEDIA_ID" || "$WP_MEDIA_ID" == "None" || "$WP_MEDIA_ID" == "" ]]; then
      ERR=$(echo "$UPLOAD_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message','unknown'))" 2>/dev/null || echo "unknown")
      >&2 echo "  ⚠ WP upload failed: ${ERR} — video available locally only"
      WP_MEDIA_ID=0
    else
      >&2 echo "  ✓ Uploaded to WP: media ID ${WP_MEDIA_ID}"
    fi
  fi
else
  >&2 echo ""
  >&2 echo "Step 5/5: Skipped (--no-upload)"
fi

# ── Output JSON ──────────────────────────────────────────────────────────────

python3 - \
  "$OUTPUT_PATH" "$WP_MEDIA_URL" "$WP_MEDIA_ID" "$FILE_SIZE" "$DURATION" \
  "$BGM_TRACK_NAME" "$BGM_ARTIST" "$BGM_LICENSE" "$HAS_VOICEOVER" \
  "${#SLIDE_FILES[@]}" "$CONFIG_FILE" << 'PYEOF'
import json, sys
result = {
    "local_path": sys.argv[1],
    "video_url": sys.argv[2],  # WP URL (empty if not uploaded)
    "wp_media_id": int(sys.argv[3]) if sys.argv[3].isdigit() else 0,
    "file_size_bytes": int(sys.argv[4]),
    "duration_sec": float(sys.argv[5]) if sys.argv[5] else 0,
    "bgm": {
        "track_name": sys.argv[6],
        "artist": sys.argv[7],
        "license": sys.argv[8],
        "attribution": f"Music: {sys.argv[6]} by {sys.argv[7]} via Jamendo"
    },
    "has_voiceover": sys.argv[9] == "true",
    "slides_count": int(sys.argv[10]),
    "config_path": sys.argv[11],
}
print(json.dumps(result, indent=2))
PYEOF
