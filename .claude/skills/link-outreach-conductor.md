---
skill: link-outreach-conductor
version: 1.0.0
cadence: daily 18:00
trigger: cron
airtable_reads: [Outreach Leads]
airtable_writes: [Outreach Leads]
external_apis: [instantly, asana]
active: true
notes: "Daily backlink outreach. Pushes verified leads to Instantly campaign, monitors replies."
---

# Outreach Conductor — Instantly Backlink Campaign

## What This Skill Does (Plain English)
This skill runs the email outreach machine for getting backlinks. Every day at 18:00, it takes up to 5 verified blog-owner leads from Airtable and pushes them into the Instantly email campaign, which then automatically sends a 3-email sequence pitching your content as a resource worth linking to. It also checks for replies — positive ones become Asana tasks for the operator to follow up on, and negative ones get marked accordingly. Think of it as the "send and monitor" half of the backlink outreach pipeline.

---

You are the outreach agent. Your job is to push verified leads into the Instantly campaign and monitor replies.

**Campaign ID:** Read from `INSTANTLY_CAMPAIGN_ID` env var (set up in Instantly first)
**Sending from:** Read from `INSTANTLY_FROM_EMAIL` env var
**Daily volume:** 5 leads max (trickle strategy)
**Angle:** Backlink outreach — we pitch evergreen content as a resource worth linking to

---

## Schedule Context

This prompt runs **daily at 18:00 WITA**. Each run: push up to 5 verified leads to Instantly + monitor replies + review campaign performance.

---

## Airtable Field Reference (Outreach Leads table)
- **MV Status** (singleSelect): Valid, Catch-All, Invalid, Pending
- **BB Status** (singleSelect): Valid, Risky, Invalid, Skipped
- **Final Status** (singleSelect): Verified, Risky, Invalid, Pending
- **Outreach Status** (singleSelect): Not Started, Contacted, Replied, No Response, Not Interested, Converted

---

## Step 1: Load Context

1. Read `MEMORY.md` and `observations.md`
2. Source `.env` for API keys: `INSTANTLY_API_KEY`, `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`
3. **IMPORTANT:** Use `INSTANTLY_API_KEY` raw — just strip whitespace. Do NOT base64-decode it.
   ```bash
   API_KEY=$(printenv INSTANTLY_API_KEY | tr -d '\n\r ')
   ```

---

## Step 2: Check Campaign Status (Every Run)

```bash
API_KEY=$(printenv INSTANTLY_API_KEY | tr -d '\n\r ')
CAMPAIGN_ID=$(printenv INSTANTLY_CAMPAIGN_ID)

# Check campaign status
curl -s "https://api.instantly.ai/api/v2/campaigns/$CAMPAIGN_ID" \
  -H "Authorization: Bearer $API_KEY"

# Check for replies — look for Interested leads
curl -s -X POST "https://api.instantly.ai/api/v2/leads/list" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"campaign_id\": \"$CAMPAIGN_ID\", \"limit\": 50, \"lead_status\": \"Interested\"}"
```

If auth fails, log the error and create an Asana task for the operator. Do NOT retry endlessly.

---

## Step 3: Push Verified Leads (Daily 18:00)

Before pushing leads to Instantly, verify all emails using the Email Verifier sub-skill 
at .claude/skills/email-verifier.md — follow it completely for each batch of leads.

1. Pull leads from Airtable `Outreach Leads` table (`AIRTABLE_OUTREACH_LEADS_TABLE`) where `Final Status = Verified` and `Outreach Status = Not Started` (max **5** per run)
2. Before pushing, match each lead to the best content resource from your site based on their niche:

### Lead-to-Content Matching

Match leads to your most relevant, evergreen content. Read CLAUDE.md for your content categories and top resources. Examples by business type:

| Your Business | Lead Type | Best Resource to Pitch |
|--------------|-----------|----------------------|
| Bakery | Food blogger | Comprehensive sourdough guide |
| Bakery | Recipe site | Ingredient substitution chart |
| Landscaper | Home improvement blog | Native plants guide |
| Landscaper | Gardening influencer | Seasonal planting calendar |
| Lawyer | Financial planning blog | Estate planning checklist |

If the lead's website has a blog or resources page, note that URL as `their_page` for personalization.

3. Push each lead to Instantly:

```bash
curl -s -X POST "https://api.instantly.ai/api/v2/leads" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "'"$CAMPAIGN_ID"'",
    "email": "lead@example.com",
    "first_name": "Name",
    "company_name": "Business Name",
    "website": "https://their-site.com",
    "custom_variables": {
      "their_page": "URL of their relevant page",
      "our_resource": "URL of our matching article",
      "resource_title": "Title of our article"
    }
  }'
```

4. Update Airtable Outreach Leads: set `Outreach Status` → `Contacted`
5. Log count and any errors

---

## Step 4: Handle Replies

Check for replies every run. Categorize and act:

### Positive (Interested, link added, wants to collaborate)
- Create Asana task in **Inbox** section (use `ASANA_INBOX_SECTION_GID` from env):
  - Title: `Outreach Reply: [Business Name] — Interested`
  - Notes: Full reply text, lead email, what we pitched, their website
- Update Airtable Outreach Leads: set `Outreach Status` → `Replied`

### Negative (Not interested, unsubscribe request)
- Update Airtable Outreach Leads: set `Outreach Status` → `Not Interested`
- No Asana task needed

### Bounce / Error
- Update Airtable Outreach Leads: set `Outreach Status` → `No Response` and add bounce note to `Notes` field
- If 3+ bounces from same domain, note in observations.md

---

## Step 5: Performance Review

After pushing leads and handling replies, review analytics:
1. Pull campaign stats from Instantly (sends, opens, replies, bounces)
2. Calculate: open rate, reply rate, bounce rate
3. Log performance summary to `observations.md`
4. If reply rate < 2% after 50+ sends → create Asana task to revise sequences
5. If bounce rate > 5% → flag email verification quality issue

---

## Step 6: Log to observations.md

Append after every run:
```
## Outreach — [DATE] [TIME] WITA
- Leads pushed: X (total in campaign: X)
- Replies: X positive, X negative
- Bounces: X
- Notes: [anything notable]
```

---

## Email Sequences (For Reference — Configure in Instantly)

The 3-touch sequence is set up inside Instantly's campaign editor. The agent pushes leads with custom variables that the templates use for personalization. **Customize these templates for your brand before launching.**

### Email 1 — Day 0: The Resource Pitch
```
Subject: Quick question about {{their_page}}

Hi {{first_name}},

I was browsing {{company_name}} and came across {{their_page}} — really great content.

I noticed your readers might also find this useful: {{our_resource}}

It's a comprehensive guide we put together — {{resource_title}}. Could be a nice addition to your resources or a helpful link for your readers.

Either way, keep up the great work!

Best,
[Your email persona name]
[Your site]
```

### Email 2 — Day 3: The Value Add
```
Subject: Re: Quick question about {{their_page}}

Hi {{first_name}},

Just following up — I also wanted to share that we'd be happy to return the favor. If you have any content you'd like us to reference or link to from our site, we're totally open to that.

We get a solid audience of [your niche] enthusiasts visiting daily — so there's a nice reader overlap with your work.

Let me know if you're interested!

Best,
[Your email persona name]
```

### Email 3 — Day 7: The Soft Close
```
Subject: Re: Quick question about {{their_page}}

Hi {{first_name}},

Last note from me! Just wanted to make sure this didn't get buried.

If linking to our resource makes sense for your readers, we'd love that. And if not, no worries at all — I genuinely enjoy your content either way.

Have a wonderful week!

[Your email persona name]
[Your site]
```

---

## Telegram Alert

Before ending each run, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ link-outreach-conductor — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ link-outreach-conductor — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ link-outreach-conductor — [skip reason]"`

Then output:
```
SKILL_RESULT: success | [N] leads pushed, [N] replies handled | [date]
```

## Hard Rules
- NEVER exceed 5 leads per day
- NEVER push a lead with `Outreach Status` other than `Not Started` — skip `Contacted`, `Replied`, `No Response`, `Not Interested`, `Converted`
- NEVER send emails directly — Instantly handles the sequence automatically
- Always match leads to our best content before pushing
- Always update Airtable status after every action
- If Instantly API fails, log error + create Asana task — don't retry in a loop
- Sign all outreach as your email persona (consistent with brand)
