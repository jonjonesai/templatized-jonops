---
skill: b2b-outreach-lead-finder
version: 1.0.0
cadence: weekly (Tuesday)
trigger: cron
airtable_reads: [B2B Outreach Queries]
airtable_writes: [B2B Leads]
external_apis: [apify, firecrawl, millionverifier, bounceban]
sub_skills: [google-maps-scraper.md, linkedin-scraper.md, email-verifier.md]
active: false
notes: "Orchestrator. Reads B2B target profile from CLAUDE.md, picks appropriate sub-skill(s), finds and verifies leads."
---

# B2B Outreach Lead Finder Skill

## What This Skill Does (Plain English)
This skill is an orchestrator that finds and verifies B2B leads. It reads the target buyer profile from CLAUDE.md, picks the next queued search query from Airtable, and delegates the actual scraping to sub-skills — Google Maps Scraper for local businesses or LinkedIn Scraper for professional contacts. After scraping, it verifies all emails and pushes verified leads into the B2B Leads table for the outreach conductor to send.

---

Find bulk buyer, wholesale, or service client leads. Reads the B2B target profile from CLAUDE.md to understand WHO to find and HOW to find them, then calls the appropriate sub-skill(s).

This is an orchestrator — it does NOT scrape directly. It delegates to:
- .claude/skills/google-maps-scraper.md — for local businesses
- .claude/skills/linkedin-scraper.md — for professional contacts

## How It Works

1. Read B2B target profile from CLAUDE.md
2. Pick next queued query from B2B Outreach Queries table
3. Determine which sub-skill(s) to use based on target type
4. Execute sub-skill(s) to find leads
5. Verify emails via email-verifier sub-skill
6. Push verified leads to B2B Leads table

## Execution

### Step 1: Read B2B target profile from CLAUDE.md
Find the "B2B Target Profile" section. It defines:
- Who: job title, business type, or community type
- Where: platform (Google Maps / LinkedIn / other)
- Why they need this: value proposition
- Search criteria: specific queries or filters

### Step 2: Pick next query from B2B Outreach Queries
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_B2B_QUERIES_TABLE}?filterByFormula=Status='Queued'&sort[0][field]=Priority&sort[0][direction]=asc&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
If no queued queries: SKILL_RESULT: skip | No B2B queries in queue — b2b-outreach-query-researcher needs to run.

### Step 3: Choose sub-skill based on target type

**Use google-maps-scraper.md when:**
- Target is a local business (salon, spa, clinic, restaurant, studio, shop)
- Location-based search is relevant
- Physical address matters

**Use linkedin-scraper.md when:**
- Target is a professional by job title
- Company size or industry filter needed
- No geographic restriction or broad geographic scope

**Use both when:**
- CLAUDE.md specifies both channels for this target profile

Reference the appropriate sub-skill file and follow its instructions completely.

### Step 4: Verify emails
After scraping, reference sub-skill: .claude/skills/email-verifier.md
Only Verified and Risky leads proceed to B2B Leads table.

### Step 5: Push to B2B Leads table
```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_B2B_LEADS_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Company": "[name]",
    "Contact Name": "[name if found]",
    "Email": "[email]",
    "Title / Role": "[job title if found]",
    "Phone": "[phone if found]",
    "Location": "[city, state/country]",
    "Source": "[Google Maps / LinkedIn]",
    "Industry": "[industry]",
    "Status": "Raw"
  }}'
```

### Step 6: Mark query Done
Update B2B Outreach Queries record: Status: Done, Leads Found: [count].

### Step 7: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ b2b-outreach-lead-finder — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ b2b-outreach-lead-finder — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ b2b-outreach-lead-finder — [skip reason]"`

```
SKILL_RESULT: success | B2B leads found: [N] | Source: [sub-skill used] | Verified: [N] Risky: [N] Invalid: [N]
```

## Rules
- Read CLAUDE.md B2B target profile BEFORE choosing sub-skill
- Never send emails — FIND and VERIFY only
- Always verify before pushing to B2B Leads
- ONE query per session
- If CLAUDE.md says "B2B not applicable" — SKILL_RESULT: skip gracefully
