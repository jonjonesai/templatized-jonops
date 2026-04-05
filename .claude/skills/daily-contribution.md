---
skill: daily-contribution
version: 3.0.0
cadence: daily 07:00
trigger: cron
airtable_reads: []
airtable_writes: []
external_apis: [wordpress, rankmath, replicate, tinify, asana]
active: true
notes: "Daily short-form value content. Format configurable via CLAUDE.md. Publishes to WordPress with featured image."
---

# Daily Contribution Skill — Short-Form Value Content (v3.0)

## What This Skill Does (Plain English)
Every morning, this skill publishes a short, helpful blog post that serves your audience with quick, actionable value. The format is configured in CLAUDE.md based on your business type. Unlike long-form SEO content, these posts are warm, approachable, and create a daily touchpoint with your readers. They also give social-poster-1 fresh content to share.

**Examples by business type:**
- **Bakery:** Daily baking tip — "Today's tip: Let your butter come to room temperature for 30 minutes before creaming. Cold butter won't incorporate air properly, leading to dense cookies."
- **Landscaper:** Seasonal garden reminder — "April 5th: Time to fertilize your lawn! Apply slow-release nitrogen fertilizer before the spring growth spurt kicks in."
- **Lawyer:** Legal awareness fact — "Did you know? In most states, a will must be witnessed by at least two people who won't inherit anything. Self-proving affidavits save time in probate."
- **Astrology site:** Daily horoscope — Full zodiac readings based on real planetary data.

---

> **Version:** 3.0.0 | **Last Updated:** 2026-04
> **Schedule:** Daily at 07:00 (configurable)
> **Output:** One published WordPress post — short-form (300-800 words)
> **Format:** Configured via CLAUDE.md `DAILY_CONTENT_FORMAT` section

---

## Prerequisites

### Environment Variables
```
WP_URL=<your WordPress URL>
WP_USERNAME=<WordPress username>
WP_PASSWORD=<WordPress app password>
REPLICATE_API=<Replicate API token>
TINIFY_API=<Tinify API key>
ASANA_API_KEY=<Asana personal access token>
```

### CLAUDE.md Configuration Required
The skill reads the following from CLAUDE.md:
- `DAILY_CONTENT_FORMAT` — which format to use (see Section 1)
- `DAILY_CONTENT_CATEGORY_ID` — WordPress category ID for daily posts
- `BRAND_VOICE` — tone and style guidelines
- `TARGET_AUDIENCE` — who we're writing for

---

## Section 1: Content Format Selection

Read `DAILY_CONTENT_FORMAT` from CLAUDE.md. This determines what kind of daily content to produce.

### Format A: Quick Tips
Short, actionable tips related to your product or service area.

**Structure:**
- Title: "Daily [Niche] Tip: [Topic]" or "[Day]'s [Niche] Tip"
- Length: 150-300 words
- Format: 1 main tip + brief explanation + why it matters
- Optional: "Pro tip" sidebar or quick FAQ

**Example (Bakery):**
```html
<h1>Today's Baking Tip: The Cold Butter Exception</h1>
<p>We always say room temperature butter — but there's one exception...</p>
<p>For flaky pie crusts and biscuits, you actually WANT cold butter. Here's why...</p>
<p><strong>The takeaway:</strong> Match your butter temperature to your goal. Creaming = room temp. Flaky layers = cold.</p>
```

### Format B: Educational Facts
Interesting facts about your industry that build authority and engagement.

**Structure:**
- Title: "Did You Know? [Fact]" or "[Niche] Fact of the Day"
- Length: 200-400 words
- Format: Surprising fact + context + practical application
- Cite sources when relevant

**Example (Lawyer):**
```html
<h1>Did You Know? Most Wills Fail This Simple Test</h1>
<p>Here's a sobering statistic: roughly 60% of Americans don't have a will at all...</p>
<p>Of those who do, many fail basic validity requirements. The most common issue?...</p>
<p><strong>Action step:</strong> If you have a will, check that it was properly witnessed...</p>
```

### Format C: Seasonal Reminders
Timely reminders tied to seasons, holidays, deadlines, or events.

**Structure:**
- Title: "[Month/Season] Reminder: [Topic]" or "This Week: [Timely Topic]"
- Length: 200-400 words
- Format: What to do + why now + how to do it
- Include relevant dates/deadlines

**Example (Landscaper):**
```html
<h1>April Garden Checklist: 5 Things to Do This Week</h1>
<p>Spring is officially here, and your garden is waking up. Here's what needs attention right now...</p>
<ol>
<li><strong>Fertilize your lawn</strong> — Apply slow-release nitrogen before the growth spurt...</li>
...
</ol>
```

### Format D: Themed Days
Rotating themed content (Tip Tuesday, FAQ Friday, etc.)

**Structure:**
- Title: "[Theme] [Day]: [Topic]"
- Length: 300-500 words
- Format: Varies by theme — tips, Q&A, spotlight, etc.
- Consistent day-of-week pattern

**Example themes:**
- Monday Motivation / Monday Myth-Busting
- Tip Tuesday / Tool Tuesday
- Wednesday Wisdom / What's New Wednesday
- Thursday Throwback / Thank You Thursday
- FAQ Friday / Feature Friday
- Saturday Spotlight / Saturday Shortcuts
- Sunday Summary / Sunday Setup

### Format E: Daily Horoscope (Astrology niche only)
Full zodiac readings based on real astronomical data.

**Structure:**
- Title: "Daily Horoscope: [Date] — [Tagline based on headline aspect]"
- Length: 2,400-3,000 words
- Format: Opening + Best Time to Act + 12 sign readings + Cosmic Takeaway
- **Requires astronomical data** — see Appendix A for full Kerykeion/ephem workflow

### Format F: Custom
A custom format defined in CLAUDE.md with specific structure guidelines.

---

## Section 2: Gather Context

### 2a. Read CLAUDE.md
Extract:
- `DAILY_CONTENT_FORMAT` — which format (A-F) to use
- `DAILY_CONTENT_CATEGORY_ID` — WordPress category ID
- `BRAND_VOICE` — tone guidelines
- `TARGET_AUDIENCE` — who we're writing for
- Any format-specific config (e.g., themed day schedule for Format D)

### 2b. Read observations.md (tail ~30 lines)
Check for:
- Recent daily posts (avoid topic repetition)
- Notes about what's resonating with the audience
- Any seasonal context or events mentioned

### 2c. Check for topic freshness
```bash
# Get recent daily posts to avoid repetition
curl -s "${WP_URL}/wp-json/wp/v2/posts?categories=${DAILY_CONTENT_CATEGORY_ID}&per_page=7&status=publish" \
  -u "${WP_USERNAME}:${WP_PASSWORD}" | python3 -c "
import json, sys
for p in json.load(sys.stdin):
    print(f'{p[\"date\"][:10]}: {p[\"title\"][\"rendered\"]}')"
```

Don't repeat a topic covered in the last 7 days.

---

## Section 3: Generate Content

Based on the format from Section 1, generate today's content.

### Topic Selection
For Formats A-D, choose a topic that:
1. Is relevant to your niche and audience
2. Hasn't been covered in the last 7 days
3. Is seasonally appropriate (if applicable)
4. Aligns with brand voice

### Writing Guidelines (All Formats)
- **Warm, helpful tone** — like a knowledgeable friend
- **Get to the value quickly** — no long preambles
- **One clear takeaway** — readers should learn something specific
- **Encourage action** — end with a CTA or next step
- **Stay in brand voice** — reference CLAUDE.md guidelines

### Internal Links
Link to at least 1 existing post when naturally relevant:
```bash
# Find related posts to link to
curl -s "${WP_URL}/wp-json/wp/v2/posts?search=[TOPIC_KEYWORD]&per_page=3&status=publish" \
  -u "${WP_USERNAME}:${WP_PASSWORD}" | python3 -c "
import json, sys
for p in json.load(sys.stdin):
    print(f'{p[\"id\"]}: {p[\"title\"][\"rendered\"]} — {p[\"link\"]}')"
```

---

## Section 4: Generate Featured Image

Use generate-image.sh to create a featured image:

```bash
# Generate + compress + upload to WP
IMAGE_JSON=$(bash /home/agent/project/generate-image.sh \
  --prompt "[DESCRIPTIVE_PROMPT_FOR_TOPIC]" \
  --aspect-ratio "16:9" \
  --filename "daily-[topic-slug]-$(date +%Y%m%d)" \
  --upload)

MEDIA_ID=$(echo "$IMAGE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['wp_media_id'])")
```

**Image prompt guidelines by format:**
- **Tips:** Visual of the technique or ingredient being discussed
- **Facts:** Abstract or conceptual illustration of the topic
- **Seasonal:** Seasonal imagery relevant to the reminder
- **Themed:** Consistent visual style for the theme

---

## Section 5: Publish to WordPress

```bash
PUBLISH_RESPONSE=$(curl -s -X POST "${WP_URL}/wp-json/wp/v2/posts" \
  -u "${WP_USERNAME}:${WP_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "POST_TITLE",
    "slug": "daily-[topic]-'"$(date +%Y-%m-%d)"'",
    "content": "FULL_HTML_CONTENT",
    "status": "publish",
    "categories": [DAILY_CONTENT_CATEGORY_ID],
    "featured_media": MEDIA_ID
  }')

POST_ID=$(echo "$PUBLISH_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
POST_URL=$(echo "$PUBLISH_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['link'])")
```

**CRITICAL:** Status MUST be `"publish"` — never draft, never future.

---

## Section 6: Set SEO Meta (Rank Math)

```bash
curl -s -X POST "${WP_URL}/wp-json/rankmath/v1/updateMeta" \
  -u "${WP_USERNAME}:${WP_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "objectType": "post",
    "objectID": POST_ID,
    "meta": {
      "rank_math_focus_keyword": "[TOPIC_KEYWORD]",
      "rank_math_title": "[POST_TITLE] %sep% %sitename%",
      "rank_math_description": "[CONCISE_DESCRIPTION_WITH_KEYWORD]"
    }
  }'
```

---

## Section 7: Post-Publish Logging

### Log to Asana (Done section)
```bash
curl -s -X POST "https://app.asana.com/api/1.0/tasks" \
  -H "Authorization: Bearer ${ASANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "Daily Contribution [DATE] — Published",
      "notes": "Format: [FORMAT_NAME]\nTopic: [TOPIC]\nWP Post ID: [ID]\nURL: [URL]\nWord count: [COUNT]\nCompleted: [TIMESTAMP]",
      "projects": ["'"${ASANA_PROJECT_GID}"'"],
      "memberships": [{"project": "'"${ASANA_PROJECT_GID}"'", "section": "'"${ASANA_DONE_SECTION_GID}"'"}]
    }
  }'
```

### Update observations.md
Append:
```
## YYYY-MM-DD HH:MM — Daily Contribution

**Format:** [Format Name]
**Topic:** [Topic]
**Title:** [Full Title]
**Word Count:** [count]
**Post ID:** [id]
**URL:** [url]
**Notes:** [any observations about the content or process]
```

---

## Section 8: Telegram Alert & SKILL_RESULT

**On success:**
```bash
bash /home/agent/project/telegram-alert.sh "✅ daily-contribution — Published: [Title] | [word count] words | [url]"
```

**On failure:**
```bash
bash /home/agent/project/telegram-alert.sh "❌ daily-contribution — [error details]"
```

**On skip:**
```bash
bash /home/agent/project/telegram-alert.sh "⚠️ daily-contribution — [skip reason]"
```

```
SKILL_RESULT: success | Daily contribution published: [Title] | WP ID: [id] | [word count] words | [url]
```

---

## Error Handling

| Failure | Action |
|---------|--------|
| CLAUDE.md missing `DAILY_CONTENT_FORMAT` | STOP. Create Asana task. This must be configured. |
| Image generation fails | Retry once. If still failing, publish without image and create Asana task. |
| WordPress publish fails | Retry once. Log error. Create Asana task. |
| Can't find fresh topic (all recent topics exhausted) | Use a "roundup" or "reminder" format. Note in observations.md. |

---

## Appendix A: Daily Horoscope Format (Astrology Niche Only)

If `DAILY_CONTENT_FORMAT` is set to `horoscope`, use the full astronomical data workflow:

### A1. Data Gathering with Kerykeion

```python
python3 << 'PYEOF'
import json, warnings
from datetime import datetime, timezone, timedelta
warnings.filterwarnings("ignore", category=DeprecationWarning)

from kerykeion import AstrologicalSubject, NatalAspects

# Current time in operator's timezone (from env)
import os
tz_offset = int(os.environ.get('TZ_OFFSET_HOURS', 0))
tz = timezone(timedelta(hours=tz_offset))
now = datetime.now(tz)

# Transit chart for the current moment — tropical zodiac
sky = AstrologicalSubject(
    "Today",
    now.year, now.month, now.day,
    now.hour, now.minute,
    lng=0.0, lat=0.0,
    tz_str="UTC",
    online=False
)

# Planetary positions
planet_attrs = [
    'sun', 'moon', 'mercury', 'venus', 'mars',
    'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
    'chiron', 'true_north_lunar_node'
]
planets = {}
for name in planet_attrs:
    p = getattr(sky, name, None)
    if p:
        planets[name] = {
            'sign': p.sign,
            'position_in_sign': round(p.position, 2),
            'abs_position': round(p.abs_pos, 2),
            'retrograde': bool(p.retrograde)
        }

# Moon phase
moon_data = {
    'sign': sky.moon.sign,
    'position': round(sky.moon.position, 2),
    'phase_name': sky.lunar_phase.moon_phase_name,
    'degrees_sun_moon': round(sky.lunar_phase.degrees_between_s_m, 2)
}

# Aspects
na = NatalAspects(sky)
aspects = []
for a in na.relevant_aspects:
    aspects.append({
        'p1': a.p1_name,
        'p2': a.p2_name,
        'aspect': a.aspect,
        'orb': round(a.orbit, 2),
        'exact_degrees': a.aspect_degrees,
        'movement': a.aspect_movement
    })
aspects.sort(key=lambda x: x['orb'])

output = {
    'source': 'kerykeion_v5_swiss_ephemeris',
    'zodiac': 'tropical',
    'date': now.strftime('%Y-%m-%d'),
    'planets': planets,
    'moon': moon_data,
    'aspects': aspects
}
print(json.dumps(output, indent=2))
PYEOF
```

### A2. Moon Illumination with ephem

```python
python3 << 'PYEOF'
import ephem, json
from datetime import datetime, timezone, timedelta
import os

tz_offset = int(os.environ.get('TZ_OFFSET_HOURS', 0))
tz = timezone(timedelta(hours=tz_offset))
now = datetime.now(tz)
d = ephem.Date(now)
moon = ephem.Moon(d)

phase_pct = moon.phase
prev_new = ephem.previous_new_moon(d)
prev_full = ephem.previous_full_moon(d)
is_waxing = float(prev_new) > float(prev_full)

if phase_pct < 1:
    phase_name = "New Moon"
elif phase_pct >= 99:
    phase_name = "Full Moon"
elif 45 <= phase_pct <= 55:
    phase_name = f"{'First' if is_waxing else 'Third'} Quarter ({phase_pct:.1f}%)"
elif phase_pct < 45:
    phase_name = f"{'Waxing' if is_waxing else 'Waning'} Crescent ({phase_pct:.1f}%)"
else:
    phase_name = f"{'Waxing' if is_waxing else 'Waning'} Gibbous ({phase_pct:.1f}%)"

print(json.dumps({
    'moon_illumination_pct': round(phase_pct, 1),
    'moon_phase_name': phase_name
}))
PYEOF
```

### A3. Horoscope Writing Structure

**Verification Gate:** The Sky Brief must pass before writing:
- At least 8 planets with positions
- At least 3 aspects with orb < 5°
- Headline aspect identified

**Content Structure:**
1. Opening (150-200 words) — Lead with headline aspect
2. Best Time to Act (50-75 words) — Applying vs separating aspects
3. 12 Sign Readings (175-225 words each) — Must cite specific aspects and house placements
4. Cosmic Takeaway (75-100 words) — Synthesis and CTA

**Writing Rules:**
- Every sign must name at least one specific aspect
- Every sign must reference its house placement
- Every sign's ruling planet status must inform the reading
- Use whole-sign house system (lookup table in CLAUDE.md if needed)

---

*Run: Daily at 07:00 per schedule.json*
*Prompt version: 3.0.0 — Rewritten for multi-vertical support*
