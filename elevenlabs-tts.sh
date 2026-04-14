#!/usr/bin/env bash
# elevenlabs-tts.sh — Convert text to speech via ElevenLabs API.
#
# Usage:
#   bash elevenlabs-tts.sh --text "Taiwan's night markets..." --output /tmp/voiceover.mp3
#   bash elevenlabs-tts.sh --text-file /tmp/caption.txt --output /tmp/voiceover.mp3
#
# Defaults:
#   Voice: George (JBFqnCBsd6RMkjVDRZzb)
#   Model: eleven_multilingual_v2
#   Max chars: 500 (cost control — truncated if exceeded)
#
# Output: JSON to stdout with metadata.
# Exit codes: 0 = success, 1 = error (JSON error on stdout).

set -euo pipefail

TEXT=""
TEXT_FILE=""
OUTPUT=""
VOICE_ID="${ELEVENLABS_VOICE_ID:-JBFqnCBsd6RMkjVDRZzb}"  # Default: George. Override via env or --voice-id.
MAX_CHARS=500

while [[ $# -gt 0 ]]; do
  case "$1" in
    --text)      TEXT="$2"; shift 2 ;;
    --text-file) TEXT_FILE="$2"; shift 2 ;;
    --output)    OUTPUT="$2"; shift 2 ;;
    --voice-id)  VOICE_ID="$2"; shift 2 ;;
    --max-chars) MAX_CHARS="$2"; shift 2 ;;
    *) echo '{"error":"Unknown argument: '"$1"'"}'; exit 1 ;;
  esac
done

die() {
  python3 -c "import json,sys; print(json.dumps({'error': sys.argv[1]}))" "$1"
  exit 1
}

if [[ -z "$OUTPUT" ]]; then
  die "--output is required"
fi

# Load text from file if provided
if [[ -n "$TEXT_FILE" ]]; then
  if [[ ! -f "$TEXT_FILE" ]]; then
    die "text file not found: ${TEXT_FILE}"
  fi
  TEXT=$(cat "$TEXT_FILE")
fi

if [[ -z "$TEXT" ]]; then
  die "either --text or --text-file is required"
fi

# Truncate to MAX_CHARS (cost control)
TEXT=$(python3 -c "
import sys
text = sys.argv[1]
max_c = int(sys.argv[2])
if len(text) > max_c:
    # Truncate at word boundary near max_c
    truncated = text[:max_c].rsplit(' ', 1)[0]
    if not truncated.endswith(('.', '!', '?')):
        truncated += '.'
    print(truncated, end='')
else:
    print(text, end='')
" "$TEXT" "$MAX_CHARS")

CHAR_COUNT=${#TEXT}

# ── Environment ──────────────────────────────────────────────────────────────
ELEVENLABS_KEY="${ELEVENLABS_API:?ELEVENLABS_API not set}"

>&2 echo "Calling ElevenLabs TTS (voice=${VOICE_ID}, chars=${CHAR_COUNT})..."

# Build JSON payload safely via Python (avoid shell escaping issues)
PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({
    'text': sys.argv[1],
    'model_id': 'eleven_multilingual_v2',
    'voice_settings': {
        'stability': 0.5,
        'similarity_boost': 0.75,
        'style': 0.3,
        'use_speaker_boost': True
    }
}))
" "$TEXT")

# ── Call ElevenLabs API ──────────────────────────────────────────────────────
# Response body = raw MP3 bytes. Save to output path.
# Use -w to capture HTTP status separately.

HTTP_CODE=$(curl -s --max-time 120 \
  -w "%{http_code}" \
  -X POST "https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}" \
  -H "xi-api-key: ${ELEVENLABS_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: audio/mpeg" \
  -d "$PAYLOAD" \
  -o "$OUTPUT")

if [[ "$HTTP_CODE" != "200" ]]; then
  # On error, output file contains error JSON, not audio
  ERR_MSG=$(python3 -c "
import json, sys
try:
    with open('$OUTPUT') as f:
        d = json.load(f)
    detail = d.get('detail', {})
    if isinstance(detail, dict):
        print(detail.get('message', 'unknown error'))
    else:
        print(str(detail))
except Exception:
    print('HTTP ${HTTP_CODE}')
" 2>/dev/null || echo "HTTP ${HTTP_CODE}")
  rm -f "$OUTPUT"
  die "ElevenLabs API error (HTTP ${HTTP_CODE}): ${ERR_MSG}"
fi

if [[ ! -s "$OUTPUT" ]]; then
  die "ElevenLabs returned empty audio file"
fi

FILE_SIZE=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null || echo "0")

# Rough duration estimate: ~150 words/min ≈ 750 chars/min ≈ 12.5 chars/sec for natural speech
DURATION_EST=$(python3 -c "print(round(${CHAR_COUNT} / 12.5, 1))")

>&2 echo "  Saved ${FILE_SIZE} bytes (~${DURATION_EST}s audio)"

# ── Output success JSON ──────────────────────────────────────────────────────
python3 -c "
import json
print(json.dumps({
    'local_path': '$OUTPUT',
    'voice_id': '$VOICE_ID',
    'voice_name': 'George',
    'characters_used': $CHAR_COUNT,
    'duration_estimate_sec': $DURATION_EST,
    'file_size_bytes': $FILE_SIZE,
    'model_id': 'eleven_multilingual_v2'
}, indent=2))
"
