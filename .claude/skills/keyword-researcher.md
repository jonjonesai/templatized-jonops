---
skill: keyword-researcher
version: 1.2.1
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
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_MARKET_INTEL_TABLE}?sort%5B0%5D%5Bfield%5D=Scan%20Date&sort%5B0%5D%5Bdirection%5D=desc&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Use **Keyword Opportunities** and **Content Gaps** to prioritize research. Use **Key Trends** to identify timely topics.

### Step 2: Read existing keywords (for cross-run dedup)
```bash
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_KEYWORDS_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Note what is already in `Queue` or `Published`. Cross-run dedup is mandatory. A new candidate is a duplicate of an existing keyword if any of the following are true:

- They target the same Google SERP (e.g., `shopify vs woocommerce` and `woocommerce vs shopify`).
- They target the same intent with different phrasing (e.g., `shopify print-on-demand` and `print on demand for shopify`).
- They are minor variations that would produce overlapping content (e.g., `print on demand business` and `print on demand for business`).

For obvious dupes, drop the new candidate. For ambiguous pairs (a candidate that *might* dup an existing entry but isn't certain, e.g., subniche vs broad, app-specific vs general guide), defer the decision to Step 4.5's SERP-confirm tiebreaker. Distinct subintents may stay separate (e.g., `print on demand t-shirt business` is a real subniche, not a phrasing variant of `print on demand business`). Use SERP overlap as the test, not lexical similarity alone.

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

### Step 4.5: Same-run dedup (mandatory)

Before pushing candidates to Airtable, dedup the picks against each other. Group them into clusters of near-duplicates using the same test as Step 2 (SERP overlap / same intent / phrasing variation).

For obvious dupe pairs, collapse immediately. For ambiguous pairs, run a SERP-confirm tiebreaker:
```bash
curl -s --user "${DATAFORSEO_LOGIN}:${DATAFORSEO_PASSWORD}" \
  -X POST "https://api.dataforseo.com/v3/serp/google/organic/live/advanced" \
  -H "Content-Type: application/json" \
  -d '[{"keyword":"[candidate_a]","language_code":"en","location_code":2840,"device":"desktop","depth":5}]'
```
Run for each candidate in the ambiguous pair, extract top-5 organic URLs, and compare. If they share at least 3 of 5 URLs, treat as same cluster. Otherwise treat as distinct.

Cache SERP results within the run. If you've already pulled the SERP for a keyword, reuse it (do not re-call DataForSEO for the same keyword).

Within each confirmed cluster, **keep the keyword with the lowest Difficulty score**. If Difficulty ties, prefer the higher Search Volume. Drop the losers and backfill from the broader DataForSEO candidate pool (Step 3 results) until you have up to 10 distinct keywords or the pool is exhausted.

Budget for SERP-confirm: cap at 6 SERP calls per run (covers up to 3 ambiguous pairs after caching). If more candidates are ambiguous than the SERP-confirm budget allows, **default to drop** rather than keep. Bias toward queue cleanliness, not output volume.

### Step 5: Add up to 10 keywords to Airtable
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
If Step 4.5 dedup leaves fewer than 10 distinct keywords, push fewer. Do not pad with dupes to hit 10. The "10/week" is a target, not a floor.

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
- Budget cap: max 16 DataForSEO API calls per run (up to 10 for Steps 1-3 keyword research, up to 6 for Step 4.5 SERP-confirm)

## Rules
- Cross-run dedup (Step 2) and same-run dedup (Step 4.5) are both mandatory. Writing multiple blog posts targeting near-duplicate keywords is keyword stuffing. Google penalizes it. It also wastes the content budget downstream.
- When a near-duplicate cluster is identified, the lowest-Difficulty member wins. Drop losers (do not push them to the queue). Tied Difficulty: higher Search Volume wins.
- Distinct subintents may stay separate (e.g., `t-shirt business` vs broad `business`). Use SERP overlap as the test, not lexical similarity alone.
- Keywords from Market Intelligence opportunities get priority.
- Mix of timely (trending) and evergreen keywords.
- Never queue keywords with volume < 500 or difficulty > 70.
- Push fewer than 10 if dedup leaves fewer. Do not pad to hit a count.
