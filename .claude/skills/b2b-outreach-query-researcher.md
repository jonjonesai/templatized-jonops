---
skill: b2b-outreach-query-researcher
version: 1.0.0
cadence: weekly (Monday 13:00)
trigger: cron
airtable_reads: [B2B Outreach Queries]
airtable_writes: [B2B Outreach Queries]
external_apis: [dataforseo, firecrawl]
active: false
notes: "Finds and queues B2B target search queries. Feeds b2b-outreach-lead-finder. Activate per project when B2B is ready."
---

# B2B Outreach Query Researcher Skill

## What This Skill Does (Plain English)
This skill generates and queues search queries that will be used to find B2B leads. For example, if the project sells wellness devices, it might generate queries like "chiropractor Denver CO" or "wellness spa Nashville TN" for Google Maps scraping. It validates queries using DataForSEO search volume data, scores them, and pushes the top 8 to Airtable. The b2b-outreach-lead-finder later reads these queries and runs the actual scraping.

---

## Purpose
Research and queue search queries that will surface the right B2B targets for this project. The b2b-outreach-lead-finder reads these queries and uses them to scrape Google Maps or LinkedIn.

This is NOT the same as link-outreach-query-researcher — that finds blogs for backlinks. This finds potential wholesale buyers, service clients, or bulk purchasers.

## Prerequisites
- DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD in .env
- FIRECRAWL_API_KEY in .env
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_B2B_QUERIES_TABLE in .env
- B2B Target Profile defined in CLAUDE.md

## Process

### Step 1: Read B2B Target Profile from CLAUDE.md
Find the "B2B Target Profile" section. Extract:
- **Who:** business type or job title
- **Where:** platform preference (Google Maps / LinkedIn)
- **Why they need this:** value proposition
- **Search criteria:** any specific terms, industries, locations

If CLAUDE.md says "B2B not applicable" → SKILL_RESULT: skip | B2B not configured for this project.

### Step 2: Check existing query inventory
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_B2B_QUERIES_TABLE}?filterByFormula=OR(Status='Queued',Status='Running')" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
If 5+ queries already queued → skip, queue is full enough.

### Step 3: Generate candidate queries

**For Google Maps targets** (local businesses):
Combine business type + city + state combinations:
- "[business type] [city] [STATE]"
- "[business type] near [city]"
- Rotate through cities from CLAUDE.md or generate based on target market

Example for a PEMF device seller:
- "massage therapist Austin TX"
- "chiropractor Denver CO"
- "wellness spa Nashville TN"
- "physical therapy clinic Seattle WA"

**For LinkedIn targets** (professional contacts):
Build Sales Navigator search URLs using:
- Industry filters from target profile
- Job title / function filters
- Seniority level filters
- Geographic filters
- Keyword filters

Use DataForSEO to validate that the business type has meaningful search volume in target locations:
```bash
curl -s --retry 3 --retry-delay 2 --user "${DATAFORSEO_LOGIN}:${DATAFORSEO_PASSWORD}" \
  -X POST "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live" \
  -H "Content-Type: application/json" \
  -d '[{"keywords":["massage therapist austin tx","chiropractor denver co"],"language_code":"en","location_code":2840}]'
```
Prioritize queries with meaningful local search volume.

### Step 4: Score queries
Score each candidate 1-10:
- **10:** High local density + perfect product fit + hasn't been scraped
- **7-9:** Good fit, moderate density
- **4-6:** Broad or tangential fit
- **1-3:** Skip — too generic or low relevance

### Step 5: Push top 8 queries to B2B Outreach Queries table
```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_B2B_QUERIES_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Query": "massage therapist Austin TX",
    "Target Type": "Google Maps",
    "Business Category": "Wellness",
    "Region": "Austin TX",
    "Score": 9,
    "Priority": "High",
    "Status": "Queued",
    "Notes": "High density, perfect PEMF fit"
  }}'
```

**Target Type values:** Google Maps | LinkedIn | Both

### Step 6: Update observations.md

### Step 7: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ b2b-outreach-query-researcher — [N] queries queued | top: [best query]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ b2b-outreach-query-researcher — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ b2b-outreach-query-researcher — [skip reason]"`

```
SKILL_RESULT: success | [N] B2B queries queued | top query: "[query]" | target type: [Maps/LinkedIn]
```

## Rules
- Read CLAUDE.md B2B target profile BEFORE generating queries
- Never queue queries for B2B types not in the target profile
- Google Maps queries: always include city + state (not just category)
- LinkedIn queries: always build as Sales Navigator URL, not freeform
- ONE session per week — don't overload the queue
- Budget cap: max 10 DataForSEO calls (~$0.10)
