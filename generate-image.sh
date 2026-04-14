#!/usr/bin/env bash
# generate-image.sh — Direct Image Pipeline: Replicate → Tinify → WordPress
# Immutable rule: NO image reaches WordPress without Tinify compression.
#
# Usage:
#   ./generate-image.sh \
#     --prompt "Mystical celestial scene..." \
#     --aspect-ratio "16:9" \
#     --filename "daily-horoscope-2026-03-05" \
#     --upload        # optional: upload to WP media library
#     --post-id 5592  # optional: set as featured image on this post
#
# Output: JSON to stdout with pipeline results.
# Exit codes: 0 = success, 1 = pipeline failure (JSON error on stdout).

set -euo pipefail

# ── Parse arguments ──────────────────────────────────────────────────────────
PROMPT=""
ASPECT_RATIO="16:9"
FILENAME="image-$(date +%s)"
DO_UPLOAD=false
POST_ID=""
MODEL="flux-pro"  # default: flux-pro (~$0.04/image). Use flux-2-pro for premium (~$0.08/image).

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt)       PROMPT="$2"; shift 2 ;;
    --aspect-ratio) ASPECT_RATIO="$2"; shift 2 ;;
    --filename)     FILENAME="$2"; shift 2 ;;
    --upload)       DO_UPLOAD=true; shift ;;
    --post-id)      POST_ID="$2"; shift 2 ;;
    --model)        MODEL="$2"; shift 2 ;;
    *) echo '{"error":"Unknown argument: '"$1"'"}'; exit 1 ;;
  esac
done

if [[ -z "$PROMPT" ]]; then
  echo '{"error":"--prompt is required"}'
  exit 1
fi

# ── Environment ──────────────────────────────────────────────────────────────
REPLICATE_KEY="${REPLICATE_API:?REPLICATE_API not set}"
TINIFY_KEY="${TINIFY_API:?TINIFY_API not set}"
WP_URL="${WP_URL:-}"
WP_USERNAME="${WP_USERNAME:-}"
WP_PASSWORD="${WP_PASSWORD:-}"

LOCAL_PATH="/tmp/${FILENAME}.webp"

# Helper: output error JSON and exit
die() {
  python3 -c "import json,sys; print(json.dumps({'error': sys.argv[1]}))" "$1"
  exit 1
}

# ── Step 1: Generate image via Replicate ─────────────────────────────────────
# Write prompt to temp file so Python can read it without shell quoting issues.

PROMPT_FILE=$(mktemp)
echo "$PROMPT" > "$PROMPT_FILE"

REPLICATE_PAYLOAD=$(python3 - "$PROMPT_FILE" "$ASPECT_RATIO" << 'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    prompt = f.read().strip()
print(json.dumps({
    "input": {
        "prompt": prompt,
        "aspect_ratio": sys.argv[2],
        "output_format": "webp",
        "output_quality": 90,
        "safety_tolerance": 5
    }
}))
PYEOF
)
rm -f "$PROMPT_FILE"

# Resolve model to Replicate endpoint
case "$MODEL" in
  flux-pro)     REPLICATE_MODEL="black-forest-labs/flux-pro" ;;
  flux-2-pro)   REPLICATE_MODEL="black-forest-labs/flux-2-pro" ;;
  *)            REPLICATE_MODEL="black-forest-labs/flux-pro" ;;
esac

>&2 echo "Step 1/5: Generating image via Replicate (${MODEL})..."

REPLICATE_RESPONSE=$(curl -s --max-time 90 \
  -X POST "https://api.replicate.com/v1/models/${REPLICATE_MODEL}/predictions" \
  -H "Authorization: Bearer ${REPLICATE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: wait" \
  -d "$REPLICATE_PAYLOAD")

# Check for curl-level failure
if [[ -z "$REPLICATE_RESPONSE" ]]; then
  die "Replicate API request returned empty response"
fi

# Extract status and poll URL
read -r REPLICATE_STATUS PREDICTION_URL < <(echo "$REPLICATE_RESPONSE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('status','unknown'), d.get('urls',{}).get('get',''))
" 2>/dev/null || echo "unknown ")

# If not yet succeeded, poll for up to 120s
if [[ "$REPLICATE_STATUS" != "succeeded" && -n "$PREDICTION_URL" ]]; then
  >&2 echo "  Prediction processing... polling."
  for i in $(seq 1 24); do
    sleep 5
    POLL_RESPONSE=$(curl -s --max-time 15 \
      -H "Authorization: Bearer ${REPLICATE_KEY}" \
      "$PREDICTION_URL") || continue

    REPLICATE_STATUS=$(echo "$POLL_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null)

    if [[ "$REPLICATE_STATUS" == "succeeded" ]]; then
      REPLICATE_RESPONSE="$POLL_RESPONSE"
      >&2 echo "  Prediction succeeded after ${i}x5s polling."
      break
    elif [[ "$REPLICATE_STATUS" == "failed" || "$REPLICATE_STATUS" == "canceled" ]]; then
      die "Replicate prediction ${REPLICATE_STATUS}"
    fi
  done
fi

if [[ "$REPLICATE_STATUS" != "succeeded" ]]; then
  die "Replicate prediction did not succeed (status: ${REPLICATE_STATUS})"
fi

# Extract image URL from output
REPLICATE_IMAGE_URL=$(echo "$REPLICATE_RESPONSE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
output = d.get('output', '')
if isinstance(output, list):
    print(output[0] if output else '')
else:
    print(output or '')
" 2>/dev/null)

if [[ -z "$REPLICATE_IMAGE_URL" || "$REPLICATE_IMAGE_URL" == "None" ]]; then
  die "No image URL in Replicate response"
fi

>&2 echo "  Image generated: ${REPLICATE_IMAGE_URL:0:60}..."

# ── Step 2: Compress via Tinify (MANDATORY GATE) ────────────────────────────
# If this step fails, the pipeline STOPS. No uncompressed image ever reaches WP.

>&2 echo "Step 2/5: Compressing via Tinify..."

TINIFY_PAYLOAD=$(python3 -c "import json; print(json.dumps({'source': {'url': '$REPLICATE_IMAGE_URL'}}))")

TINIFY_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 60 \
  -X POST "https://api.tinify.com/shrink" \
  -u "api:${TINIFY_KEY}" \
  -H "Content-Type: application/json" \
  -d "$TINIFY_PAYLOAD")

TINIFY_HTTP_CODE=$(echo "$TINIFY_RESPONSE" | tail -1)
TINIFY_BODY=$(echo "$TINIFY_RESPONSE" | sed '$d')

if [[ "$TINIFY_HTTP_CODE" != "201" ]]; then
  ERR_MSG=$(echo "$TINIFY_BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message','unknown'))" 2>/dev/null || echo "HTTP ${TINIFY_HTTP_CODE}")
  die "Tinify compression failed: ${ERR_MSG}"
fi

# Extract compressed image URL and stats
read -r TINIFIED_URL INPUT_SIZE OUTPUT_SIZE < <(echo "$TINIFY_BODY" | python3 -c "
import json, sys
d = json.load(sys.stdin)
url = d.get('output', {}).get('url', '')
inp = d.get('input', {}).get('size', 0)
out = d.get('output', {}).get('size', 0)
print(url, inp, out)
" 2>/dev/null || echo " 0 0")

if [[ -z "$TINIFIED_URL" || "$TINIFIED_URL" == "None" ]]; then
  die "No compressed URL in Tinify response"
fi

COMPRESSION_RATIO=$(python3 -c "
i, o = int('${INPUT_SIZE}'), int('${OUTPUT_SIZE}')
print(f'{round((1-o/i)*100,1)}' if i > 0 else '0')
")

>&2 echo "  Compressed: ${INPUT_SIZE}B → ${OUTPUT_SIZE}B (${COMPRESSION_RATIO}% saved)"

# ── Step 3: Download compressed image ────────────────────────────────────────

>&2 echo "Step 3/5: Downloading compressed image..."

curl -sf --max-time 30 \
  -u "api:${TINIFY_KEY}" \
  -o "$LOCAL_PATH" \
  "$TINIFIED_URL" || die "Failed to download compressed image from Tinify"

if [[ ! -s "$LOCAL_PATH" ]]; then
  die "Downloaded file is empty: ${LOCAL_PATH}"
fi

FILE_SIZE=$(stat -c%s "$LOCAL_PATH" 2>/dev/null || stat -f%z "$LOCAL_PATH" 2>/dev/null || echo "?")
>&2 echo "  Saved to ${LOCAL_PATH} (${FILE_SIZE} bytes)"

# ── Step 4: Upload to WordPress (if --upload) ────────────────────────────────

WP_MEDIA_ID=0
WP_MEDIA_URL=""

if [[ "$DO_UPLOAD" == "true" ]]; then
  >&2 echo "Step 4/5: Uploading to WordPress..."

  if [[ -z "$WP_URL" || -z "$WP_USERNAME" || -z "$WP_PASSWORD" ]]; then
    die "WordPress credentials not set (WP_URL, WP_USERNAME, WP_PASSWORD)"
  fi

  UPLOAD_RESPONSE=$(curl -s --max-time 60 \
    -X POST "${WP_URL}/wp-json/wp/v2/media" \
    -u "${WP_USERNAME}:${WP_PASSWORD}" \
    -H "Content-Disposition: attachment; filename=\"${FILENAME}.webp\"" \
    -H "Content-Type: image/webp" \
    --data-binary "@${LOCAL_PATH}")

  read -r WP_MEDIA_ID WP_MEDIA_URL < <(echo "$UPLOAD_RESPONSE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
mid = d.get('id', '')
murl = d.get('source_url', '')
print(mid, murl)
" 2>/dev/null || echo " ")

  if [[ -z "$WP_MEDIA_ID" || "$WP_MEDIA_ID" == "None" || "$WP_MEDIA_ID" == "" ]]; then
    ERR=$(echo "$UPLOAD_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message','unknown'))" 2>/dev/null || echo "unknown")
    die "WordPress media upload failed: ${ERR}"
  fi

  >&2 echo "  Uploaded: Media ID ${WP_MEDIA_ID}"

  # ── Step 5: Set as featured image (if --post-id) ──────────────────────────

  if [[ -n "$POST_ID" ]]; then
    >&2 echo "Step 5/5: Setting featured image on post ${POST_ID}..."

    curl -s --max-time 15 \
      -X POST "${WP_URL}/wp-json/wp/v2/posts/${POST_ID}" \
      -u "${WP_USERNAME}:${WP_PASSWORD}" \
      -H "Content-Type: application/json" \
      -d "{\"featured_media\": ${WP_MEDIA_ID}}" > /dev/null

    >&2 echo "  Featured image set."
  fi
else
  >&2 echo "Step 4/5: Skipped (no --upload flag)"
  >&2 echo "Step 5/5: Skipped (no --post-id flag)"
fi

# ── Output JSON ──────────────────────────────────────────────────────────────

python3 - "$REPLICATE_IMAGE_URL" "$TINIFIED_URL" "$LOCAL_PATH" "$COMPRESSION_RATIO" "$WP_MEDIA_ID" "$WP_MEDIA_URL" << 'PYEOF'
import json, sys
result = {
    "replicate_url": sys.argv[1],
    "tinified_url": sys.argv[2],
    "local_path": sys.argv[3],
    "compression_ratio": sys.argv[4] + "%",
    "wp_media_id": int(sys.argv[5]) if sys.argv[5].isdigit() else 0,
    "wp_media_url": sys.argv[6]
}
print(json.dumps(result, indent=2))
PYEOF
