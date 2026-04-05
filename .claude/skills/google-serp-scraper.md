---
skill: google-serp-scraper
version: 1.0.0
type: sub-skill
trigger: called-by-parent
external_apis: [apify]
notes: "Sub-skill. Called by link-outreach-lead-finder. Scrapes Google SERP via Apify, filters junk, returns clean domain list."
---

# Google SERP Scraper — Sub-Skill

## What This Skill Does (Plain English)
This sub-skill runs a Google search for a given query via Apify and returns a clean list of independent websites and blogs — filtering out social media, large media outlets, directories, and platform sites. For example, searching "astrology blog guest post" would return smaller niche blogs suitable for outreach. It only finds sites; it does not extract emails or write to Airtable.

---

Scrape Google search results for a given query via Apify, filter out junk domains, and return a clean list of independent blogs and websites.

## Purpose
This sub-skill is a reusable tool. It can be called by:
- link-outreach-lead-finder (finding blog/PR partners)
- Any other skill that needs to find websites via Google search

## Input
- Search query (string)
- Max results (default: 50)

## Process

### Step 1: Run Apify Google Search Scraper
```bash
curl -s -X POST "https://api.apify.com/v2/acts/apify~google-search-scraper/runs" \
  -H "Authorization: Bearer ${APIFY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": "[search query]",
    "maxPagesPerQuery": 5,
    "resultsPerPage": 10,
    "languageCode": "en",
    "countryCode": "us"
  }'
```

Wait for run to complete, fetch results:
```bash
curl -s "https://api.apify.com/v2/acts/apify~google-search-scraper/runs/last/dataset/items?token=${APIFY_API_KEY}"
```

### Step 2: Filter junk domains
Remove results matching these patterns:
- Social media: facebook.com, twitter.com, instagram.com, pinterest.com, tiktok.com, youtube.com, linkedin.com
- Large media: forbes.com, huffpost.com, buzzfeed.com, nytimes.com, theguardian.com, medium.com
- Aggregators/directories: yelp.com, tripadvisor.com, yellowpages.com, angi.com
- Platforms: shopify.com, wix.com, squarespace.com, wordpress.com, blogger.com
- Q&A: reddit.com, quora.com, answers.com
- Wikis: wikipedia.org, wikihow.com

Keep: independent blogs, small-medium websites, niche sites with real authors.

### Step 3: Return clean domain list
Return array of unique root domains from filtered results.

## Output
List of clean domains ready for email scraping.

## Budget
~$0.01-0.05 per run depending on result count.

## Rules
- Never return more than 50 domains per call
- Always deduplicate domains
- This skill FINDS sites only — no email extraction, no Airtable writes
