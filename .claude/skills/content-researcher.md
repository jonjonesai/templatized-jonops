---
skill: content-researcher
version: 1.1.1
cadence: weekly (Monday)
trigger: cron
airtable_reads: [Keywords]
airtable_writes: [Content Calendar]
external_apis: [firecrawl, dataforseo]
active: true
notes: "Runs after keyword-researcher. Populates Content Calendar with angles."
---

# Content Researcher Skill

## What This Skill Does (Plain English)
This skill takes the top queued keywords and researches what the top Google results are saying about each one. It scrapes competitor articles, identifies content gaps they all miss, and writes a detailed content brief with a unique angle, suggested outline, and word count target. These briefs get queued in Airtable so the blog-writer skill can pick them up and turn them into full posts.

**Examples by business type:**
- **Bakery:** Keyword "sourdough starter troubleshooting" → finds competitors miss "altitude adjustments" → creates brief with that angle
- **Landscaper:** Keyword "native plants for pollinators" → identifies gap in "regional variety recommendations" → queues focused brief
- **Lawyer:** Keyword "estate planning checklist" → spots missing "digital assets" section → creates differentiated brief

---

## Purpose
Take the top queued keywords from the Keywords table and research content angles for each. Find what competitors are writing, identify gaps, and queue blog post ideas with unique angles in the Content Calendar. This feeds the blog-writer.

## Prerequisites
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID in .env
- FIRECRAWL_API_KEY in .env
- DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD in .env

## Process

### Step 1: Read latest Market Intelligence
```bash
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_MARKET_INTEL_TABLE}?sort%5B0%5D%5Bfield%5D=Scan%20Date&sort%5B0%5D%5Bdirection%5D=desc&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Use **Content Gaps**, **Key Trends**, and **Competitor Moves** to shape content angles. Prioritize angles that fill gaps competitors are covering but we aren't.

### Step 2: Read top 10 queued keywords (read more than you need so Step 2.5 can dedup)
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_KEYWORDS_TABLE}?filterByFormula=Status='Queue'&sort[0][field]=Search%20Volume&sort[0][direction]=desc&maxRecords=10" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```

### Step 2.5: Deduplicate candidates by SERP overlap and intent

This step is mandatory. Group the 10 candidates into clusters of near-duplicates. Two keywords belong in the same cluster if any of the following are true:

- They target the same Google SERP (e.g., `shopify vs woocommerce` and `woocommerce vs shopify` literally hit identical results).
- They target the same intent with different phrasing (e.g., `shopify print-on-demand` and `print on demand for shopify`).
- They are minor variations that would produce overlapping content (e.g., `print on demand business` and `print on demand for business`).

Within each cluster, **keep the keyword with the lowest Difficulty score**. If Difficulty ties, prefer the higher Search Volume. Intuition: when two keywords serve the same audience, win the one Google considers easier to rank for.

For every losing cluster member, **mark its row in the Keywords table as Status=`Skipped`** with a Note explaining why:
```bash
curl -s --retry 3 --retry-delay 2 -X PATCH "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_KEYWORDS_TABLE}/[record_id]" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"Status": "Skipped", "Notes": "Skipped: near-duplicate of [winner_keyword] (lower difficulty wins)"}}'
```

This is mandatory because writing multiple blog posts on near-duplicate keywords is keyword stuffing. Google penalizes it. It also wastes the content budget. Distinct subintents may stay separate (e.g., `print on demand t-shirt business` is a distinct subniche from `print on demand business`) but obvious phrasing variants must be deduped.

After dedup, you will have between 3 and 10 distinct keywords. Pick the top 5 by Search Volume for the rest of this run.

### Step 3: Check Content Calendar — avoid duplicates against what is already queued for writing
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_CONTENT_TABLE}?fields[]=Keyword" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Skip any deduped keyword that already exists in Content Calendar (a previous run already queued it). Step 2.5 handles same-run dedup; this step handles cross-run dedup.

### Step 4: For each keyword — SERP research
DataForSEO SERP organic results for the keyword:
```bash
curl -s --user "${DATAFORSEO_LOGIN}:${DATAFORSEO_PASSWORD}" \
  -X POST "https://api.dataforseo.com/v3/serp/google/organic/live/advanced" \
  -H "Content-Type: application/json" \
  -d '[{"keyword":"[keyword]","language_code":"en","location_code":2840,"device":"desktop","depth":5}]'
```
Extract top 5 URLs.

### Step 5: Scrape top 3 results via Firecrawl
```bash
curl -s -X POST "https://api.firecrawl.dev/v1/scrape" \
  -H "Authorization: Bearer ${FIRECRAWL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"url":"[competitor_url]","formats":["markdown"]}'
```
For each result: extract H2 headings, main angles covered, word count estimate.

### Step 6: Identify content gap
Based on what the top 3 cover, answer:
- What angle is MISSING from all top results?
- What question do searchers likely have that isn't answered?
- What unique perspective fits this brand's voice?

### Step 7: Write content brief
For each keyword, produce:
- Working title (includes keyword naturally)
- Unique angle (the gap you identified)
- 5-7 H2 section ideas
- Suggested word count (2,500-3,500)
- Internal link opportunities (existing posts on this site)

### Step 8: Push to Content Calendar
```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_CONTENT_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Title": "[working title]",
    "Keyword": "[keyword]",
    "Status": "Queued",
    "Category": "[category from CLAUDE.md WP_CATEGORIES]",
    "Notes": "[gap analysis + H2 outline + word count + internal links + CTA]"
  }}'
```

### Step 9: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ content-researcher — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ content-researcher — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ content-researcher — [skip reason]"`

```
SKILL_RESULT: success | [N] content briefs added to Content Calendar | keywords: [list]
```

## Error Handling
- DataForSEO error → skip that keyword, continue with others
- Firecrawl error → use DataForSEO snippet text instead of full scrape
- Budget cap: max 10 DataForSEO SERP calls + 15 Firecrawl scrapes per run

## Rules
- Never add duplicate keywords to Content Calendar.
- Never produce briefs for near-duplicate keywords in the same run. Step 2.5 dedup is mandatory. Writing multiple blog posts on near-duplicate keywords is keyword stuffing, and Google penalizes it.
- When a near-duplicate cluster exists in the queue, the lowest-Difficulty member wins. Mark losers as `Skipped` with a Note pointing to the winner.
- Always identify a genuine content gap. Do not just summarize what competitors wrote.
- Read up to 10 candidates per run. Produce up to 5 briefs per run after dedup.
