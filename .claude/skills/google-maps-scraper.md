---
skill: google-maps-scraper
version: 1.0.0
type: sub-skill
trigger: called-by-parent
external_apis: [apify, hunter, firecrawl]
notes: "Sub-skill. Called by b2b-outreach-lead-finder (and optionally link-outreach-lead-finder). Scrapes Google Maps for local businesses, enriches with emails, returns leads."
---

# Google Maps Lead Scraper — Sub-Skill

## What This Skill Does (Plain English)
This sub-skill scrapes Google Maps for local businesses matching a search query (e.g., "yoga studio Austin TX"), then enriches them with contact emails using a waterfall approach: first Hunter.io for domain-based lookup, then Firecrawl as a fallback to scrape the business website directly. It returns a structured list of leads with names, emails, phones, and addresses — but does not write to Airtable or send outreach itself. The parent skill handles that.

---

Discover local businesses from Google Maps, enrich with contact emails via waterfall approach, and return structured leads ready for Airtable.

## Pipeline Flow
```
Google Maps (Apify) → Hunter.io → Firecrawl scrape + regex → return leads
```

## Input
- Search queries (array of "business type city STATE" strings)
- Max leads (default: 200)
- Budget cap (default: $5.00 Apify abort threshold)

These come from CLAUDE.md B2B Target Profile or from the B2B Outreach Queries table.

## APIs Used
| Service | Env Var | Purpose |
|---------|---------|---------|
| Apify | APIFY_API_KEY | Google Maps scraper actor |
| Hunter.io | HUNTER_API_KEY | Domain email lookup |
| Firecrawl | FIRECRAWL_API_KEY | Website scrape + regex fallback |

**Apify actor:** `compass~crawler-google-places`

## Process

### Phase 1: Google Maps Discovery
```bash
curl -s -X POST "https://api.apify.com/v2/acts/compass~crawler-google-places/runs" \
  -H "Authorization: Bearer ${APIFY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "searchStringsArray": ["yoga studio Austin TX", "wellness spa Dallas TX"],
    "maxCrawledPlacesPerSearch": 18,
    "language": "en",
    "includeWebResults": false
  }'
```

Wait for run, fetch results. Filter out leads without websites. Filter out social media links as "websites". Triple dedup: business name, phone, email.

Cost abort: if Apify spend > $5.00, abort run and work with what you have.

### Phase 2: Hunter.io Email Enrichment
For each lead with a website domain:
```bash
curl -s "https://api.hunter.io/v2/domain-search?domain=[domain]&api_key=${HUNTER_API_KEY}"
```

Score emails: +50 if title = owner/manager/director/buyer/founder, +20 if personal type, +30 if verified valid. Pick highest scoring email.

### Phase 3: Firecrawl Fallback
For leads still without email after Hunter:
```bash
curl -s -X POST "https://api.firecrawl.dev/v1/scrape" \
  -H "Authorization: Bearer ${FIRECRAWL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"url":"[domain]/contact","formats":["markdown"]}'
```
Scrape homepage + /contact (max 2 pages per domain).
Regex extract emails. Filter junk domains and prefixes.

### Phase 4: Return leads
Return structured array of leads with: name, company, email, phone, address, city, state, category, website, rating, reviews, email source.

## Email Validation Rules
Skip these email domains: squarespace.com, wix.com, shopify.com, godaddy.com, wordpress.com, sentry.io, cloudflare.com, google.com, facebook.com
Skip these prefixes: noreply, no-reply, donotreply, mailer-daemon

## Expected Results
- Phone coverage: ~95%
- Website coverage: ~60-70%
- Hunter.io hit rate: ~30-40%
- Firecrawl hit rate: ~10-15% of remaining
- Total email coverage: ~40-55%

## Cost Per Run
- Apify: ~$2-4 for 200-400 leads
- Hunter.io: free tier (25/month) or paid
- Firecrawl: ~1-2 credits per site

## Rules
- Never exceed $5.00 Apify spend — abort and return what you have
- Triple dedup: name, phone, email
- This sub-skill FINDS and ENRICHES only — no Airtable writes, no Instantly pushes
- Parent skill handles Airtable and Instantly
- Rate limits: Hunter (0.3s), Firecrawl (0.3s)
