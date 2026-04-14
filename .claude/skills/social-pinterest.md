---
type: platform-subskill
platform: pinterest
parent_skills: [social-poster-1, social-poster-2]
network_value: pinterest
aspect_ratio: "2:3"
image_model: flux-2-pro
board_id: dynamic
---

# Social Pinterest — Platform Subskill

This is a **subskill** invoked by `social-poster-1` (blog repurpose) and `social-poster-2` (researcher queue). Pinterest is an SEO-first, evergreen platform — think of it as a visual search engine, not a social feed.

## Inputs (provided by the orchestrator)
- `TITLE` — blog post title or research topic
- `CONTENT_SOURCE` — blog URL (SP1) or Research Brief (SP2)
- `LINK_URL` — URL Pinterest users click through to (blog post or shop page)
- `FOCUS_KEYWORD` — (SP1 only) the RankMath focus keyword from the blog post
- `FILENAME_SLUG` — unique filename slug
- `SCHEDULE_TIME` — ISO 8601 datetime

## Platform Character Rules (Pinterest)
| Metric              | Limit |
|---------------------|-------|
| Pin title           | ≤100 chars (keyword-rich) |
| Hard max description| 500 chars |
| **Target description** | **200–250 chars** |
| Front-loaded        | First 50 chars shown in feed — put keywords here |
| Hashtags            | None (Pinterest deprioritized hashtags in 2020+) |

## Step 1: Write a Pinterest-native description
Pinterest is **search-driven and evergreen**. Write for the person typing a keyword into Pinterest's search bar 6 months from now. Structure:

**Pin Title** (≤100 chars):
- Keyword-rich, "How-to" or "Guide to" framing works best
- Include the focus keyword verbatim
- Examples: "[Topic] Guide: Everything Worth Knowing" / "Best [Product/Service] in [Location]: Local Favorites"

**Pin Description** (200–250 chars, hard max 500):
- **First 50 chars = the only thing visible in-feed** — load your strongest keywords there
- 2–3 short sentences with naturally-placed long-tail keywords
- Evergreen framing: "Discover", "Learn", "Your complete guide to…"
- Include one action phrase at the end ("Save for later", "Pin for your next trip")
- **NO hashtags** — Pinterest no longer ranks them and they eat character budget
- **NO emoji flood** — one or two tasteful emoji max

**Good example (218 chars):**
> "Complete guide to [topic]: the top 12 [items] experts swear by. Your full bucket list with insider tips and actionable advice. Save for later."

**Bad example:**
> "OMG guys we wrote a new blog post!!! 🔥🔥🔥 Check it out on our website #topic #blog #trending"

## Step 2: Generate a Pinterest-native image
Pinterest rewards **vertical (2:3) pins** with bold visuals and high contrast.

```bash
IMAGE_JSON=$(bash /home/agent/project/generate-image.sh \
  --model flux-2-pro \
  --prompt "[Pinterest-specific prompt — vertical 2:3 composition, match brand image style, bold focal subject, leave clean top/bottom third space for potential text overlay, rich saturated colors, Pinterest-optimized]" \
  --aspect-ratio "2:3" \
  --filename "${FILENAME_SLUG}" \
  --upload)

IMAGE_URL=$(echo "$IMAGE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['wp_media_url'])")
```

## Step 3: Resolve Pinterest board ID dynamically
**CRITICAL:** Metricool's Pinterest API requires a **numeric** `pinterestData.boardId` matching regex `^\d+$`. The old `username/board-slug` format NO LONGER WORKS and will error with `Code: 400 - Invalid request`.

Fetch the board list from Metricool at runtime and pick the first available board. If no boards are returned, **skip Pinterest gracefully** — do not attempt to schedule.

```bash
BLOG_ID="${METRICOOL_BLOG_ID:-}"
USER_ID="${METRICOOL_USER_ID:-}"

# Fetch live Pinterest boards from Metricool
BOARDS_JSON=$(curl -s "https://app.metricool.com/api/v2/scheduler/boards/pinterest?blogId=${BLOG_ID}&userId=${USER_ID}&integrationSource=MCP" \
  -H "X-Mc-Auth: ${METRICOOL_API_TOKEN}")

# Pick the first numeric board ID (or match by brand name if multiple exist)
BOARD_ID=$(echo "$BOARDS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
boards = data.get('data', []) if isinstance(data, dict) else data
# Prefer a board whose name matches the brand, else first available
target = None
for b in boards:
    target = b
    break
print(target.get('id','') if target else '')
")

if [ -z "$BOARD_ID" ]; then
  echo "SKIP: No Pinterest boards available in Metricool. Operator action required."
  PLATFORM_STATUS="skipped"
  PLATFORM_ERROR="no_pinterest_boards"
else
  curl -s -X POST "https://app.metricool.com/api/v2/scheduler/posts?blogId=${BLOG_ID}" \
    -H "Content-Type: application/json" \
    -H "X-Mc-Auth: ${METRICOOL_API_TOKEN}" \
    -d "{
      \"text\": \"[your 200-250 char pinterest description]\",
      \"providers\": [{\"network\": \"pinterest\"}],
      \"pinterestData\": {\"boardId\": \"${BOARD_ID}\", \"pinTitle\": \"[your pin title ≤100 chars]\", \"pinLink\": \"${LINK_URL}\", \"pinNewFormat\": false},
      \"publicationDate\": {\"dateTime\": \"${SCHEDULE_TIME}\", \"timezone\": \"${SCHEDULE_TIMEZONE}\"},
      \"draft\": false,
      \"autoPublish\": true,
      \"media\": [\"${IMAGE_URL}\"]
    }"
fi
```

## Step 4: Return result to orchestrator
Return:
- `platform`: `"pinterest"`
- `status`: `"scheduled"` | `"failed"` | `"skipped"`
- `pin_title`: the title used
- `description_preview`: full description (already short)
- `image_url`: `$IMAGE_URL`
- `link_url`: `$LINK_URL`
- `scheduled_time`: `$SCHEDULE_TIME`
- `metricool_response_code`: HTTP code

## Rules
- **Hard character cap: 500.** Target 200–250. Count before scheduling.
- **NO hashtags** — they eat budget and don't help ranking on Pinterest.
- Always vertical 2:3 format (never square, never landscape).
- **`pinterestData.boardId` MUST be numeric** (regex `^\d+$`) — fetch it dynamically from `/api/v2/scheduler/boards/pinterest`. Never hardcode `username/board-slug` strings.
- If the Metricool boards list is empty, skip Pinterest gracefully and return `status: skipped, error: no_pinterest_boards`. Operator must (a) create a board on Pinterest, (b) ensure the account is connected as a **Pinterest Business** profile in Metricool, (c) re-authorize the Pinterest integration so Metricool syncs the board list.
- Field names inside `pinterestData` are `pinTitle` and `pinLink` (not `title`/`link`). Also include `pinNewFormat: false`.
- Always include an outbound `pinLink` in `pinterestData` — that's the whole point of Pinterest.
- Front-load keywords in first 50 chars.
- Evergreen framing only — never time-sensitive ("today only", "this week") language.
