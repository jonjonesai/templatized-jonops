---
skill: keyword-researcher
version: 1.1.0
cadence: weekly (Monday 08:00)
trigger: cron
airtable_reads: [Keywords, Market Intelligence]
airtable_writes: [Keywords]
external_apis: [dataforseo]
active: true
notes: "Runs after market-intelligence. Finds and queues 10 new SEO keywords."
---

# Keyword Researcher Skill

## What This Skill Does (Plain English)
Every Monday, this skill finds 10 new SEO keywords for blog content. It checks what competitors are ranking for, looks at trending topics in your niche, and uses the DataForSEO API to find keywords with decent search volume but low enough competition that we can realistically rank. All keywords go into the Airtable Keywords table for the content pipeline to pick up.

**Examples by business type:**
- **Bakery:** Discovers "sourdough starter troubleshooting" with 5,000 monthly searches and low difficulty
- **Landscaper:** Finds "best native plants for shade" as a high-opportunity keyword
- **Lawyer:** Queues "living trust vs will" for a future pillar post

---

## Purpose
Research and queue 10 new target keywords for content. Uses Market Intelligence insights to prioritize timely and high-opportunity keywords.

## Prerequisites
- DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD in env
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID in env
- AIRTABLE_KEYWORDS_TABLE, AIRTABLE_MARKET_INTEL_TABLE in env
- Niche seed keywords defined in CLAUDE.md

## Process

### Step 1: Read latest Market Intelligence
```bash
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_MARKET_INTEL_TABLE}?sort%5B0%5D%5Bfield%5D=Month&sort%5B0%5D%5Bdirection%5D=desc&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Use **Keyword Opportunities** and **Content Gaps** to prioritize research. Use **Key Trends** to identify timely topics.

### Step 2: Read existing keywords
```bash
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_KEYWORDS_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Note what is already Queued or Published — avoid duplicates.

### Step 3: Research keywords via DataForSEO
Use the Related Keywords API to expand from seed terms in CLAUDE.md and opportunities from Market Intelligence:
```bash
curl -s --user "${DATAFORSEO_LOGIN}:${DATAFORSEO_PASSWORD}" \
  -X POST "https://api.dataforseo.com/v3/dataforseo_labs/google/related_keywords/live" \
  -H "Content-Type: application/json" \
  -d '[{"keyword":"[seed keyword]","language_code":"en","location_code":2840,"limit":50}]'
```

Also use Keyword Suggestions:
```bash
curl -s --user "${DATAFORSEO_LOGIN}:${DATAFORSEO_PASSWORD}" \
  -X POST "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_suggestions/live" \
  -H "Content-Type: application/json" \
  -d '[{"keyword":"[seed keyword]","language_code":"en","location_code":2840,"limit":50}]'
```

### Step 4: Filter and score
Select keywords matching these criteria:
- Search volume 500–10,000
- Low-to-medium competition (keyword difficulty < 60)
- Relevant to niche (use seed keywords from CLAUDE.md as relevance guide)
- Not already in Keywords table
- Bonus: aligns with Market Intelligence keyword opportunities or trends

### Step 5: Add 10 keywords to Airtable
```bash
curl -s -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_KEYWORDS_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Keyword": "[keyword]",
    "Search Volume": [volume],
    "Difficulty": [difficulty],
    "Intent": "[informational|transactional|navigational]",
    "Status": "Queue",
    "Notes": "[why this keyword — market intel context]"
  }}'
```

### Step 6: Log to observations.md
Append the list of 10 new keywords with their volumes and rationale.

### Step 7: Telegram Alert & SKILL_RESULT

```bash
bash /home/agent/project/telegram-alert.sh "✅ keyword-researcher — [N] keywords queued to Airtable"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ keyword-researcher — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ keyword-researcher — [skip reason]"`

```
SKILL_RESULT: success | [N] keywords queued | top: [keyword1], [keyword2], [keyword3]
```

## Error Handling
- DataForSEO error → retry once, then SKILL_RESULT: fail
- All suggested keywords already exist → SKILL_RESULT: skip | All candidates already in queue
- Budget cap: max 10 DataForSEO API calls per run

## Rules
- Always check for duplicates before adding
- Keywords from Market Intelligence opportunities get priority
- Mix of timely (trending) and evergreen keywords
- Never queue keywords with volume < 500 or difficulty > 70
