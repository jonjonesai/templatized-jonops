---
skill: b2b-outreach-conductor
version: 1.0.0
cadence: weekly (Wednesday 10:00)
trigger: cron
airtable_reads: [B2B Leads]
airtable_writes: [B2B Leads, B2B Outreach Log]
external_apis: [instantly]
active: false
notes: "Pushes verified B2B leads to Instantly B2B campaign. Monitors replies. Escalates positives to Asana."
---

# B2B Outreach Conductor Skill

## What This Skill Does (Plain English)
This skill takes verified B2B leads from Airtable and pushes them into an Instantly.ai email campaign. It also checks for campaign replies — positive replies (interested prospects) get escalated as Asana tasks for the operator to follow up personally, while negative replies are marked accordingly. It is the sending and monitoring step of the B2B pipeline; it does not find leads itself.

---

## Purpose
Take verified B2B leads from the B2B Leads table and push them to the Instantly.ai B2B campaign. Monitor campaign replies. Log positive replies to Asana as sales opportunities for the operator to follow up on.

This is the SENDING skill — it does not find or verify leads. That's done by b2b-outreach-lead-finder.

## Prerequisites
- INSTANTLY_API_KEY in .env
- ASANA_API_KEY, ASANA_PROJECT_GID, ASANA_INBOX_GID, ASANA_DONE_GID in .env
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_B2B_LEADS_TABLE in .env
- B2B Instantly campaign name defined in CLAUDE.md

## Process

### Step 1: Read B2B campaign name from CLAUDE.md
Find "Instantly campaign (B2B)" in CLAUDE.md. If not configured → SKILL_RESULT: skip | B2B Instantly campaign not configured in CLAUDE.md.

### Step 2: Get Instantly campaign ID
```bash
curl -s "https://api.instantly.ai/api/v1/campaign/list?api_key=${INSTANTLY_API_KEY}&limit=20"
```
Find campaign matching name from CLAUDE.md. Extract campaign ID.

### Step 3: Pull verified B2B leads not yet contacted
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_B2B_LEADS_TABLE}?filterByFormula=AND(Status='Verified',{Outreach Status}='Not Started')&maxRecords=20" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Limit 20 leads per run — don't flood the campaign.

If no verified leads → SKILL_RESULT: skip | No verified B2B leads ready. b2b-outreach-lead-finder needs to run.

### Step 4: Push leads to Instantly campaign
For each lead:
```bash
curl -s -X POST "https://api.instantly.ai/api/v1/lead/add" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "'${INSTANTLY_API_KEY}'",
    "campaign_id": "'${CAMPAIGN_ID}'",
    "skip_if_in_workspace": true,
    "leads": [{
      "email": "[email]",
      "first_name": "[first_name]",
      "last_name": "[last_name]",
      "company_name": "[company]",
      "custom_variables": {
        "title": "[title]",
        "location": "[location]",
        "industry": "[industry]"
      }
    }]
  }'
```

Update Airtable B2B Leads: Outreach Status → Contacted.

### Step 5: Check campaign replies
```bash
curl -s "https://api.instantly.ai/api/v1/unibox/emails?api_key=${INSTANTLY_API_KEY}&campaign_id=${CAMPAIGN_ID}&reply_to_uuid=&limit=20"
```
For each reply received this week — classify:
- **Positive** (interested, asking for info, wants to talk) → Create Asana task in Inbox
- **Negative** (not interested, unsubscribe) → Update lead Status: Not Interested
- **Auto-reply / OOO** → Ignore, do not update status

### Step 6: Create Asana tasks for positive replies
```bash
curl -s -X POST "https://app.asana.com/api/1.0/tasks" \
  -H "Authorization: Bearer ${ASANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"data": {
    "name": "🔥 B2B Reply: [company] — [first line of reply]",
    "notes": "Email: [email]\nCompany: [company]\nReply: [full reply text]\n\nAction needed: Follow up within 24 hours.",
    "projects": ["'${ASANA_PROJECT_GID}'"],
    "memberships": [{"project": "'${ASANA_PROJECT_GID}'", "section": "'${ASANA_INBOX_GID}'"}]
  }}'
```

Update lead Outreach Status: Replied.

### Step 7: Update B2B Outreach Log
Create one log record per session:
- Leads pushed: [N]
- Replies checked: [N]
- Positives found: [N]
- Negatives: [N]

### Step 8: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ b2b-outreach-conductor — [N] leads pushed | [N] positive replies → Asana"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ b2b-outreach-conductor — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ b2b-outreach-conductor — [skip reason]"`

```
SKILL_RESULT: success | [N] B2B leads pushed to Instantly | [N] positive replies escalated to Asana
```

## Rules
- Never push unverified leads — Status must be Verified
- Max 20 leads per run — don't flood campaigns
- Always use skip_if_in_workspace: true — prevents duplicates in Instantly
- Positive replies go to Asana Inbox immediately — operator follows up personally
- Never respond to leads on operator's behalf — escalate only
- If Instantly API returns 524 timeout: retry once with smaller batch (10 leads), log warning
