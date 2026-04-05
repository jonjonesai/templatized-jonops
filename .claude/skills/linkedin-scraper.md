---
skill: linkedin-scraper
version: 1.0.0
type: sub-skill
trigger: called-by-parent
external_apis: [apify, hunter, leadmagic, prospeo]
notes: "Sub-skill. Called by b2b-outreach-lead-finder. Scrapes LinkedIn Sales Navigator, enriches with emails via waterfall, returns leads."
---

# LinkedIn Sales Navigator Scraper — Sub-Skill

## What This Skill Does (Plain English)
This sub-skill scrapes LinkedIn Sales Navigator search results via Apify (no LinkedIn cookies needed) to find professional contacts matching specific filters like job title, industry, or seniority. It then enriches each profile with email addresses using a waterfall: Hunter.io first, then LeadMagic, then optionally Prospeo. It returns structured leads with names, titles, companies, emails, and LinkedIn URLs — but does not write to Airtable or send outreach itself.

---

Scrape leads from LinkedIn Sales Navigator search URLs, enrich with emails via waterfall approach, and return structured leads ready for Airtable.

## Pipeline Flow
```
LinkedIn Sales Nav (Apify) → Hunter.io → LeadMagic → [Prospeo] → [Firecrawl] → return leads
```

## Input
- Sales Navigator search URL (from CLAUDE.md B2B target profile or B2B Outreach Queries)
- Max leads (default: 200)

## APIs Used
| Service | Env Var | Purpose |
|---------|---------|---------|
| Apify | APIFY_API_KEY | LinkedIn Sales Nav scraper |
| Hunter.io | HUNTER_API_KEY | Domain email lookup |
| LeadMagic | LEAD_MAGIC_API_KEY | Name-based email finder |
| Prospeo | PROSPEO_API_KEY | LinkedIn URL email lookup (optional) |
| Firecrawl | FIRECRAWL_API_KEY | Website scrape fallback (optional) |

**Apify actor:** `1MfTHQrl8mvtDOrP3` (no LinkedIn cookies required)

## How to Build a Sales Navigator URL
1. Go to LinkedIn Sales Navigator
2. Apply filters: Industry, Function, Region, Keywords, Seniority
3. Copy the full URL from browser address bar
4. Store in CLAUDE.md B2B Target Profile or B2B Outreach Queries table

## Process

### Phase 1: LinkedIn Scrape via Apify
```bash
curl -s -X POST "https://api.apify.com/v2/acts/1MfTHQrl8mvtDOrP3/runs" \
  -H "Authorization: Bearer ${APIFY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "searchUrl": "[sales nav URL]",
    "maxLeads": 200
  }'
```
Wait for completion. Results include: first name, last name, title, company, LinkedIn URL, location, company website, headline.

### Phase 2: Hunter.io Email Enrichment
For each lead with company name/domain:
```bash
curl -s "https://api.hunter.io/v2/domain-search?domain=[domain]&api_key=${HUNTER_API_KEY}"
```
Hit rate: ~40-50%

### Phase 3: LeadMagic Fallback
For leads without email after Hunter:
```bash
curl -s -X POST "https://api.leadmagic.io/v1/email-finder" \
  -H "X-API-Key: ${LEAD_MAGIC_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"[first]","last_name":"[last]","company_name":"[company]"}'
```
Hit rate: ~10-15% of remaining

### Phase 4: Prospeo (optional)
For leads still without email, using LinkedIn URL:
```bash
curl -s -X POST "https://api.prospeo.io/email-finder" \
  -H "X-API-Key: ${PROSPEO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"linkedin_url":"[linkedin_url]"}'
```

### Phase 5: Return leads
Return structured array with: first_name, last_name, full_name, title, company, email, linkedin_url, location, company_website, source.

## Email Validation Rules
Skip these domains: wix.com, squarespace.com, shopify.com, godaddy.com, wordpress.com, linkedin.com, gmail.com, outlook.com, hotmail.com
Skip these prefixes: noreply, no-reply, donotreply, mailer-daemon

## Deduplication
Maintain dedup against existing B2B Leads table — check LinkedIn URL and email before returning leads.

## Expected Results
- Scrape speed: 100-200 profiles in 2-5 minutes
- Hunter.io hit rate: ~40-50%
- LeadMagic hit rate: ~10-15% of remaining
- Total email coverage: ~50-70%

## Cost Per Run
- Apify: ~$5 per 1000 profiles
- Hunter.io: free tier (25/month) or paid
- LeadMagic: per-lookup pricing

## Rules
- Never require LinkedIn cookies — use Apify actor 1MfTHQrl8mvtDOrP3 only
- This sub-skill FINDS and ENRICHES only — no Airtable writes, no Instantly pushes
- Parent skill handles Airtable and Instantly
- Rate limits: Hunter (0.35s), LeadMagic (0.5s)
- Dedup against existing leads before returning

## Example Sales Nav Filters by Project Type

**Wellness/Health products (OlyLife, OA):**
- Industry: Health, Wellness and Fitness
- Function: Operations, Administrative
- Seniority: Owner, Manager
- Keywords: massage, wellness, spa, chiropractor

**Creative/Merch (CustomCreative, TaiwanMerch):**
- Industry: Retail, Apparel & Fashion
- Function: Purchasing, Merchandising
- Seniority: Buyer, Manager, Director
- Keywords: buyer, purchasing, merchandising

**AI Consulting (JonJones.AI):**
- Industry: Small Business, Marketing & Advertising
- Function: Operations, Marketing
- Seniority: Owner, Manager, Director
- Keywords: automation, marketing, operations
