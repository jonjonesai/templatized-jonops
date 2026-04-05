---
skill: link-outreach-query-researcher
version: 1.0.0
cadence: weekly (Monday)
trigger: cron
airtable_reads: [Outreach Queries]
airtable_writes: [Outreach Queries]
external_apis: [dataforseo, apify]
active: true
notes: "Discovers search queries that surface backlink/JV partner blogs. NOT B2B leads."
---

# Outreach Query Researcher Skill

## What This Skill Does (Plain English)
Every Monday, this skill figures out what to Google to find potential backlink partners. It analyzes which blogs already link to our competitors, clusters them by niche, then generates and tests search queries. Each query is scored on how many real blogs it surfaces vs. junk. The top 8-12 queries get queued in Airtable for the lead-finder skill to process throughout the week.

**Examples by business type:**
- **Bakery:** Discovers queries like "food bloggers bread recipes" and "baking influencers sourdough"
- **Landscaper:** Generates queries like "gardening blogs California" and "home improvement bloggers landscaping"
- **Lawyer:** Creates queries like "financial planning bloggers estate" and "retirement blogs legal"

---

Discover high-quality search queries for blog outreach lead generation. This skill mines competitor backlinks, expands niches via DataForSEO, validates queries against real SERP data, and queues the best performers for the Lead Finder pipeline.

## How It Works

1. **Mine competitor backlinks** — Find blogs already linking to competitors in CLAUDE.md. These are proven outreach partners.
2. **Cluster niches** — Group discovered domains by theme
3. **Expand with DataForSEO** — Related keywords API surfaces adjacent niches
4. **Generate candidate queries** — Combine niches + geographic qualifiers
5. **Validate via SERP** — Test each query: how many results are real blogs vs junk?
6. **Score and rank** — blog_yield(0-5) + diversity(0-3) + relevance(0-3) + freshness(0-2) = max 13
7. **Push to Airtable** — Queue top 8-12 queries for Lead Finder pipeline

## Execution

### Step 1: Read memory and market context
Read CLAUDE.md for competitor list and niche definition.
Read observations.md for recent context.
Read the latest **Market Intelligence** record:
```bash
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_MARKET_INTEL_TABLE}?sort%5B0%5D%5Bfield%5D=Month&sort%5B0%5D%5Bdirection%5D=desc&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Use **Top SERP Players** and **Competitor Moves** to target niches where competitors are gaining backlinks. Use **Content Gaps** to find outreach angles that align with content we plan to create.

### Step 2: Review existing query inventory
Check Airtable Outreach Queries table — what's already queued? What niches covered? What gaps remain?

### Step 3: Mine competitor backlinks
For 4-6 competitors from CLAUDE.md:
```bash
curl -s --retry 3 --retry-delay 2 --user "${DATAFORSEO_LOGIN}:${DATAFORSEO_PASSWORD}" \
  -X POST "https://api.dataforseo.com/v3/backlinks/referring_domains/live" \
  -H "Content-Type: application/json" \
  -d '[{"target":"[competitor_domain]","limit":100}]'
```
Study referring domains. Look for patterns — blog types, niches, geographic clusters.

### Step 4: Brainstorm candidate niches
Based on backlink data + niche from CLAUDE.md, brainstorm 8-12 candidate niches.
Rate each 0-3 for product/service relevance:
- 3 = Direct fit
- 2 = Adjacent
- 1 = Broad
- 0 = Skip

### Step 5: Expand seeds via DataForSEO related keywords
For top 6-8 seed terms:
```bash
curl -s --retry 3 --retry-delay 2 --user "${DATAFORSEO_LOGIN}:${DATAFORSEO_PASSWORD}" \
  -X POST "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live" \
  -H "Content-Type: application/json" \
  -d '[{"keywords":["[seed] blogs","[seed] bloggers","[seed] influencers"],"language_code":"en","location_code":2840}]'
```

### Step 6: Compose and validate candidate queries
Generate 15-20 candidate queries combining niches + geo qualifiers.
Validate top candidates via DataForSEO SERP (max 15 calls).
Skip queries with < 20% real blog yield.

### Step 7: Score and push to Airtable
For each validated query with score ≥ 6:
```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_OUTREACH_QUERIES_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Query": "[query]",
    "Niche": "[niche]",
    "Region": "[region]",
    "Score": [score],
    "Priority": "[High/Medium/Low]",
    "Status": "Queued",
    "Notes": "[yield notes]"
  }}'
```

### Step 8: Update observations.md

### Step 9: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ link-outreach-query-researcher — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ link-outreach-query-researcher — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ link-outreach-query-researcher — [skip reason]"`

```
SKILL_RESULT: success | [N] queries pushed to Outreach Queries | avg score: [X] | top query: "[query]"
```

## Budget Cap
~$0.50 per session. ONE session per week. Minimum score threshold: 6.

## Rules
- Never push duplicate queries
- This skill DISCOVERS queries — it does NOT run the lead finder
- Always check existing inventory before pushing
