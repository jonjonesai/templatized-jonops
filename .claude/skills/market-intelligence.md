---
skill: market-intelligence
version: 1.0.0
cadence: weekly (Monday 02:30)
trigger: cron
airtable_reads: []
airtable_writes: [Market Intelligence]
external_apis: [dataforseo, firecrawl]
active: true
notes: "Weekly market scan. Feeds keyword-researcher, content-researcher, social-researcher, link-outreach-query-researcher."
---

# Market Intelligence Skill

## What This Skill Does (Plain English)
Once a week on Monday morning, this skill scans your niche to see what competitors are doing, which keywords are trending, and where content gaps exist. For example, it might discover that a trending topic is surging in search volume but no competitor has a comprehensive guide yet. The findings feed directly into the keyword-researcher, content pipeline, social strategy, and outreach planning for the week ahead.

**Examples by business type:**
- **Bakery:** Discovers "sourdough discard recipes" trending but competitors lack comprehensive guides
- **Landscaper:** Finds "native plant landscaping" surging with low competition
- **Lawyer:** Identifies "estate planning checklist 2026" as an emerging opportunity

---

## Purpose
Run a weekly market scan to understand what's trending in the niche, who's dominating search, what content gaps exist, and what keyword opportunities are emerging. Results feed keyword-researcher, content-researcher, social-researcher, and link-outreach-query-researcher.

This is NOT competitor stalking. It's strategic market awareness.

## Prerequisites
- DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD in .env
- FIRECRAWL_API_KEY in .env
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID in .env
- Competitor list and niche seed terms in CLAUDE.md

## Process

### Step 1: Top competitor keyword scan
For top 2 competitors from CLAUDE.md:
```bash
curl -s --user "${DATAFORSEO_LOGIN}:${DATAFORSEO_PASSWORD}" \
  -X POST "https://api.dataforseo.com/v3/dataforseo_labs/google/competitors_domain/live" \
  -H "Content-Type: application/json" \
  -d '[{"target":"[competitor_domain]","language_code":"en","location_code":2840,"limit":20}]'
```
Extract their top 20 ranking keywords. Note which are new vs last month.

### Step 2: SERP trend check on niche seeds
For 3-5 seed terms from CLAUDE.md:
```bash
curl -s --user "${DATAFORSEO_LOGIN}:${DATAFORSEO_PASSWORD}" \
  -X POST "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live" \
  -H "Content-Type: application/json" \
  -d '[{"keywords":["[seed1]","[seed2]","[seed3]"],"language_code":"en","location_code":2840}]'
```
Note volume trends — rising, falling, stable.

### Step 3: Competitor content scan
Firecrawl scrape of competitor homepage + blog listing page (2 pages per competitor, max 2 competitors):
```bash
curl -s -X POST "https://api.firecrawl.dev/v1/scrape" \
  -H "Authorization: Bearer ${FIRECRAWL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"url":"[competitor_blog_url]","formats":["markdown"]}'
```
Extract: recent post titles, topics covered this month, content formats used.

### Step 4: Synthesize findings
Produce structured analysis:

**Trending Topics** — what topics are appearing frequently across competitors and SERP?
**Top SERP Players** — who's dominating this month and why?
**Content Gaps** — what topics have low competition but decent volume?
**Keyword Opportunities** — 5 specific keywords worth targeting next month
**Competitor Moves** — any significant changes (new content types, new angles, new products)?
**Action Items** — specific recommendations for blog-writer and keyword-researcher next month

### Step 5: Push to Market Intelligence table
```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_MARKET_INTEL_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Month": "[YYYY-MM-01]",
    "Key Trends": "[trends text]",
    "Top SERP Players": "[players text]",
    "Content Gaps": "[gaps text]",
    "Keyword Opportunities": "[opportunities text]",
    "Competitor Moves": "[moves text]",
    "Action Items": "[action items text]"
  }}'
```

### Step 6: Update MEMORY.md
Append key findings to MEMORY.md "Market Context" section so they persist for future sessions.

### Step 7: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ market-intelligence — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ market-intelligence — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ market-intelligence — [skip reason]"`

```
SKILL_RESULT: success | Market intelligence for [Month] logged | [N] keyword opportunities identified
```

## Error Handling
- Budget cap: max 15 DataForSEO calls + 4 Firecrawl scrapes per run (~$0.50 total)
- If DataForSEO fails: skip competitor keyword scan, run content scan only

## Rules
- This runs ONCE per week (Monday morning) — do not re-run mid-week
- Focus on actionable insights, not raw data dumps
- Always update MEMORY.md with key findings
