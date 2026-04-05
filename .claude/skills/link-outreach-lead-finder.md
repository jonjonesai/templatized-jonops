---
skill: link-outreach-lead-finder
version: 2.0.0
cadence: daily (14:00 WITA)
trigger: cron
airtable_reads: [Link Outreach Queries]
airtable_writes: [Outreach Leads]
external_apis: [apify, firecrawl, millionverifier, bounceban]
sub_skills: [google-serp-scraper.md, email-verifier.md]
active: true
notes: "Finds blog/site leads for backlinks, guest posts, PR. Uses google-serp-scraper sub-skill. ONE query per session."
---

# Link Outreach Lead Finder Skill

## What This Skill Does (Plain English)
This skill finds real people to email about backlinks. It picks a search query from the Outreach Queries queue (populated by the query-researcher skill), Googles it, filters out junk sites, then scrapes the remaining blogs for contact emails. Those emails get verified for deliverability and pushed into the Outreach Leads table in Airtable. The outreach-conductor skill later picks them up and sends the actual emails. One query per run, up to 30 domains scraped.

**Examples by business type:**
- **Bakery:** Query "food bloggers sourdough" surfaces recipe blogs to pitch for backlinks
- **Landscaper:** Query "gardening blogs native plants" finds potential link partners
- **Lawyer:** Query "financial planning bloggers estate" discovers related content creators

---

Find leads for backlinks, guest posts, sponsored posts, product reviews, and JV partnerships. Reads a search query from the Outreach Queries queue, finds relevant blogs and sites, extracts contact emails, verifies deliverability, and pushes to Airtable.

## How It Works

1. Pick next Queued query from Airtable Outreach Queries table
2. Use .claude/skills/google-serp-scraper.md sub-skill to find sites (50 results)
3. Filter junk — remove social media, aggregators, large media, platforms
4. Scrape emails via Firecrawl (max 3 pages per domain)
5. Push to Airtable Outreach Leads
6. Verify emails via .claude/skills/email-verifier.md sub-skill
7. Update Final Status in Airtable

## Execution

### Step 1: Read context
Read CLAUDE.md for niche and link outreach target profile.

### Step 2: Pick next query from Outreach Queries
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_OUTREACH_QUERIES_TABLE}?filterByFormula=AND(Status='Queued',Type='Link')&sort[0][field]=Priority&sort[0][direction]=asc&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
If no queued queries: SKILL_RESULT: skip | No link outreach queries in queue.
Mark selected query as Running.

### Step 3: Scrape Google SERP
Reference sub-skill: .claude/skills/google-serp-scraper.md
Pass the query, get back list of filtered domains.

### Step 4: Extract emails via Firecrawl
For each filtered domain (max 30), scrape /contact, /about, homepage:
```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.firecrawl.dev/v1/scrape" \
  -H "Authorization: Bearer ${FIRECRAWL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"url":"[domain]/contact","formats":["markdown"]}'
```

### Step 5: Push to Outreach Leads table
```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_OUTREACH_LEADS_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Website": "[url]",
    "Blog Name": "[name]",
    "Email": "[primary email]",
    "All Emails": "[all emails]",
    "Email Source Page": "[page]",
    "Niche": "[niche from query]",
    "Track": "Link Outreach",
    "Final Status": "Pending"
  }}'
```

### Step 6: Verify emails
Reference sub-skill: .claude/skills/email-verifier.md
Update Final Status: Verified / Risky / Invalid.

### Step 7: Mark query Done
Update Outreach Queries record: Status: Done, Leads Found: [count].

### Step 8: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ link-outreach-lead-finder — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ link-outreach-lead-finder — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ link-outreach-lead-finder — [skip reason]"`

```
SKILL_RESULT: success | Query: "[query]" | SERP: [N] → Filtered: [N] → Emails: [N] | Verified: [N] Risky: [N] Invalid: [N]
```

## Budget
- Firecrawl: ~70-90 credits/run
- MillionVerifier: ~15-20/run
- Bounce Ban: ~3-5/run (catch-alls only)

## Rules
- ONE query per session
- Never send emails — FIND and VERIFY only
- Max 3 Firecrawl pages per domain
- Always verify before marking done
