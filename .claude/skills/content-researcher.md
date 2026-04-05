---
skill: content-researcher
version: 1.0.0
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
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_MARKET_INTEL_TABLE}?sort%5B0%5D%5Bfield%5D=Month&sort%5B0%5D%5Bdirection%5D=desc&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Use **Content Gaps**, **Key Trends**, and **Competitor Moves** to shape content angles. Prioritize angles that fill gaps competitors are covering but we aren't.

### Step 2: Read top 5 queued keywords
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_KEYWORDS_TABLE}?filterByFormula=Status='Queue'&sort[0][field]=Score&sort[0][direction]=desc&maxRecords=5" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```

### Step 3: Check Content Calendar — avoid duplicates
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_CONTENT_TABLE}?fields[]=Keyword" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Skip any keyword already in Content Calendar.

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
    "Status": "Queue",
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
- Never add duplicate keywords to Content Calendar
- Always identify a genuine gap — don't just summarize what competitors wrote
- Cap at 5 keywords per run
