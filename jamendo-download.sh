#!/usr/bin/env bash
# jamendo-download.sh — Download royalty-free BGM from Jamendo API.
#
# Usage:
#   bash jamendo-download.sh --mood "upbeat" --output /tmp/bgm.mp3 [--no-cache] [--exclude "id1,id2"]
#
# Flags:
#   --mood      Jamendo tag(s), comma-separated (e.g. "upbeat,pop"). Default: "upbeat".
#   --output    Path to write the downloaded MP3. REQUIRED.
#   --no-cache  Skip the cache lookup and always hit the Jamendo API. The track
#               is still cached after download so it can act as an offline
#               fallback. Production video runs should ALWAYS pass this so each
#               video ships with a fresh, different BGM track.
#   --exclude   Comma-separated list of Jamendo track IDs to skip. Useful for
#               rotating through new tracks after the first pick gets stale.
#
# Behaviour:
#   1. If --no-cache is NOT set, checks local cache at remotion/public/jamendo-cache/{mood}/.
#      If a cached track <7 days old exists, reuses it (no API call).
#   2. Otherwise calls Jamendo API with a randomized offset, filters for
#      commercial-safe CC licenses, skips any track IDs already in the cache
#      dir or passed via --exclude, and picks a RANDOM candidate from the
#      results (not just the first one) so consecutive runs get variety.
#   3. Downloads the track, caches it with sidecar metadata, copies to --output.
#   4. Falls back to remotion/public/bgm-upbeat-newyear.mp3 on any failure.
#
# Output: JSON to stdout with track metadata.
# Exit codes: 0 = success (may be fallback), 1 = fatal error (no fallback available).

set -euo pipefail

MOOD="upbeat"
OUTPUT=""
CACHE_MAX_AGE_DAYS=7
NO_CACHE=0
EXCLUDE_IDS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mood)     MOOD="$2"; shift 2 ;;
    --output)   OUTPUT="$2"; shift 2 ;;
    --no-cache) NO_CACHE=1; shift ;;
    --exclude)  EXCLUDE_IDS="$2"; shift 2 ;;
    *) echo '{"error":"Unknown argument: '"$1"'"}'; exit 1 ;;
  esac
done

if [[ -z "$OUTPUT" ]]; then
  echo '{"error":"--output is required"}'
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_DIR="${SCRIPT_DIR}/remotion/public/jamendo-cache/${MOOD}"
FALLBACK_BGM="${SCRIPT_DIR}/remotion/public/bgm-upbeat-newyear.mp3"
mkdir -p "$CACHE_DIR"

# Helper: emit fallback JSON and copy fallback BGM
use_fallback() {
  local reason="$1"
  if [[ -f "$FALLBACK_BGM" ]]; then
    cp "$FALLBACK_BGM" "$OUTPUT"
    # Pass values via argv so quotes inside $reason never break the Python literal.
    python3 - "$OUTPUT" "$reason" <<'PYEOF'
import json, sys
print(json.dumps({
    'track_id': 'fallback',
    'track_name': 'bgm-upbeat-newyear',
    'artist': 'local',
    'license': 'local',
    'local_path': sys.argv[1],
    'source': 'fallback',
    'fallback_reason': sys.argv[2],
}, indent=2))
PYEOF
    exit 0
  fi
  python3 - "$reason" <<'PYEOF'
import json, sys
print(json.dumps({"error": f"Jamendo failed and no fallback BGM available: {sys.argv[1]}"}))
PYEOF
  exit 1
}

# ── Step 1: Check cache ──────────────────────────────────────────────────────
# When --no-cache is set, skip the cache lookup entirely and always hit Jamendo.
# Cached files are still written after a fresh download so they can serve as
# an offline fallback inside use_fallback() if the API ever goes down.
if [[ "$NO_CACHE" -eq 1 ]]; then
  CACHED_FILE=""
  >&2 echo "Cache disabled (--no-cache), fetching fresh track from Jamendo..."
else
  # Look for any .mp3 file in cache dir newer than CACHE_MAX_AGE_DAYS
  CACHED_FILE=$(find "$CACHE_DIR" -maxdepth 1 -name "*.mp3" -mtime -${CACHE_MAX_AGE_DAYS} -type f 2>/dev/null | head -1 || true)
fi

if [[ -n "$CACHED_FILE" && -s "$CACHED_FILE" ]]; then
  cp "$CACHED_FILE" "$OUTPUT"
  TRACK_ID=$(basename "$CACHED_FILE" .mp3)
  # Try to load metadata from sidecar file if exists
  META_FILE="${CACHED_FILE%.mp3}.json"
  if [[ -f "$META_FILE" ]]; then
    python3 -c "
import json, sys
with open('$META_FILE') as f:
    meta = json.load(f)
meta['local_path'] = '$OUTPUT'
meta['source'] = 'cache'
print(json.dumps(meta, indent=2))
"
  else
    python3 -c "
import json
print(json.dumps({
    'track_id': '$TRACK_ID',
    'track_name': 'cached',
    'artist': 'unknown',
    'license': 'CC-BY',
    'local_path': '$OUTPUT',
    'source': 'cache'
}, indent=2))
"
  fi
  exit 0
fi

# ── Step 2: Query Jamendo API ────────────────────────────────────────────────
JAMENDO_KEY="${JAMENDO_CLIENT_ID:-}"
if [[ -z "$JAMENDO_KEY" ]]; then
  use_fallback "JAMENDO_CLIENT_ID not set"
fi

>&2 echo "Querying Jamendo for mood='${MOOD}'..."

# URL-encode the mood tag (replace comma with %2C for multi-tag)
MOOD_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$MOOD'))")

# Build exclude-IDs list: default to every track we've already cached for this
# mood so --no-cache runs actually pick a different track each time. Caller can
# also pass --exclude "id1,id2" to force-skip specific tracks.
AUTO_EXCLUDE=""
if [[ -d "$CACHE_DIR" ]]; then
  AUTO_EXCLUDE=$(find "$CACHE_DIR" -maxdepth 1 -name "*.mp3" -type f 2>/dev/null \
    | sed 's|.*/||; s|\.mp3$||' | paste -sd, -)
fi
COMBINED_EXCLUDE="$EXCLUDE_IDS"
if [[ -n "$AUTO_EXCLUDE" ]]; then
  if [[ -n "$COMBINED_EXCLUDE" ]]; then
    COMBINED_EXCLUDE="${COMBINED_EXCLUDE},${AUTO_EXCLUDE}"
  else
    COMBINED_EXCLUDE="$AUTO_EXCLUDE"
  fi
fi

# Pull a wide window (limit=200) so the commercial-safe filter has a large
# candidate pool. Commercial-safe CC tracks (BY / BY-SA) are a small minority
# of Jamendo's catalog — randomizing the offset alone often returns a page
# with zero usable tracks. Instead, pull the top 200 and let the parser pick
# a random candidate from the pool.
API_URL="https://api.jamendo.com/v3.0/tracks/?client_id=${JAMENDO_KEY}&format=json&limit=200&tags=${MOOD_ENCODED}&order=popularity_total&audioformat=mp31&include=musicinfo"

RESPONSE=$(curl -s --max-time 30 "$API_URL")

if [[ -z "$RESPONSE" ]]; then
  use_fallback "empty Jamendo response"
fi

# Parse response, find first downloadable track WITH commercial-safe license.
# Taiwan Merch is a commercial brand, so we must exclude:
#   - NC (Non-Commercial) licenses
#   - ND (No-Derivatives) licenses (we're using the track in a derivative video)
# Accept: CC-BY, CC-BY-SA (attribution required, but commercially usable)
TRACK_JSON=$(echo "$RESPONSE" | EXCLUDE_IDS="$COMBINED_EXCLUDE" python3 -c "
import json, os, random, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print('', end=''); sys.exit(0)

exclude = set(i.strip() for i in (os.environ.get('EXCLUDE_IDS') or '').split(',') if i.strip())
results = data.get('results', [])
candidates = []
for t in results:
    tid = str(t.get('id', ''))
    if not tid or tid in exclude:
        continue
    if not (t.get('audiodownload_allowed') and t.get('audiodownload')):
        continue
    license_url = (t.get('license_ccurl') or '').lower()
    # Reject non-commercial and no-derivatives
    if '/nc' in license_url or '-nc' in license_url:
        continue
    if '/nd' in license_url or '-nd' in license_url:
        continue
    # Must be a CC license (has 'creativecommons' in URL) or public domain
    if 'creativecommons' not in license_url and 'publicdomain' not in license_url:
        continue
    candidates.append(t)

if not candidates:
    # If everything was excluded, fall back to the full list ignoring exclude.
    for t in results:
        if not (t.get('audiodownload_allowed') and t.get('audiodownload')):
            continue
        license_url = (t.get('license_ccurl') or '').lower()
        if '/nc' in license_url or '-nc' in license_url: continue
        if '/nd' in license_url or '-nd' in license_url: continue
        if 'creativecommons' not in license_url and 'publicdomain' not in license_url: continue
        candidates.append(t)

if not candidates:
    sys.exit(0)

t = random.choice(candidates)
print(json.dumps({
    'track_id': str(t.get('id', 'unknown')),
    'track_name': t.get('name', 'Untitled'),
    'artist': t.get('artist_name', 'Unknown Artist'),
    'license': t.get('license_ccurl', 'CC-BY'),
    'audiodownload': t.get('audiodownload'),
    'duration': t.get('duration', 0),
    'shareurl': t.get('shareurl', '')
}))
" 2>/dev/null || echo "")

if [[ -z "$TRACK_JSON" ]]; then
  use_fallback "no downloadable tracks found for mood='${MOOD}'"
fi

TRACK_ID=$(echo "$TRACK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['track_id'])")
TRACK_URL=$(echo "$TRACK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['audiodownload'])")

# ── Step 3: Download track ───────────────────────────────────────────────────
>&2 echo "Downloading track ${TRACK_ID}..."

CACHED_PATH="${CACHE_DIR}/${TRACK_ID}.mp3"
META_PATH="${CACHE_DIR}/${TRACK_ID}.json"

if ! curl -sfL --max-time 120 -o "$CACHED_PATH" "$TRACK_URL"; then
  use_fallback "download failed for track ${TRACK_ID}"
fi

if [[ ! -s "$CACHED_PATH" ]]; then
  rm -f "$CACHED_PATH"
  use_fallback "downloaded file empty for track ${TRACK_ID}"
fi

# Write sidecar metadata file for future cache hits
echo "$TRACK_JSON" > "$META_PATH"

# Copy to output
cp "$CACHED_PATH" "$OUTPUT"

# ── Step 4: Output success JSON ──────────────────────────────────────────────
echo "$TRACK_JSON" | python3 -c "
import json, sys
meta = json.load(sys.stdin)
meta['local_path'] = '$OUTPUT'
meta['source'] = 'jamendo'
meta.pop('audiodownload', None)
print(json.dumps(meta, indent=2))
"
