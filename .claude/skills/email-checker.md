---
skill: email-checker
version: 2.0.0
cadence: daily 11:00 + 21:00
trigger: cron
airtable_reads: []
airtable_writes: []
external_apis: [gmail, asana]
active: true
notes: "Twice-daily email check. Categorizes, labels, drafts replies as email persona. Finance emails escalated to Asana."
---

# Email Checker Skill — Gmail (v2.0)

## What This Skill Does (Plain English)
Twice a day, this skill checks your business Gmail inbox for unread emails, categorizes each one (customer question, partnership inquiry, finance, or misc), applies color-coded Gmail labels, and drafts replies as your email persona for customer and partnership emails. Finance emails are never replied to — instead, they get escalated to the operator as an Asana task.

**Examples by business type:**
- **Bakery:** Reader asking "How do I fix a flat sourdough?" gets a warm, helpful draft reply
- **Landscaper:** "When should I plant tulip bulbs?" gets an expert response
- **Lawyer:** Invoice from a vendor gets flagged for operator review (no reply drafted)

---

You are the **email persona** defined in CLAUDE.md. Before drafting any reply, read the persona file (path defined in CLAUDE.md as `EMAIL_PERSONA_FILE`) to internalize the tone, style, and boundaries.

---

## Prerequisites
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN in env (Gmail OAuth)
- ASANA_API_KEY in env (for Category 3/4 task escalation)
- ASANA_PROJECT_GID and ASANA_INBOX_SECTION_GID in env (for task creation)
- Email persona file must exist at path defined in CLAUDE.md (read before drafting replies)

---

## Step 1: Authenticate with Gmail API

Get a fresh access token using the OAuth refresh token:

```bash
ACCESS_TOKEN=$(curl -s -X POST "https://oauth2.googleapis.com/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${GOOGLE_CLIENT_ID}&client_secret=${GOOGLE_CLIENT_SECRET}&refresh_token=${GOOGLE_REFRESH_TOKEN}&grant_type=refresh_token" \
  | jq -r '.access_token')
```

Verify token works:
```bash
curl -s "https://gmail.googleapis.com/gmail/v1/users/me/profile" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

---

## Step 2: Fetch Unread Emails

Get all unread messages from the last 24 hours:

```bash
curl -s "https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is:unread+newer_than:1d&maxResults=20" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

For each message ID returned, fetch the full message:

```bash
curl -s "https://gmail.googleapis.com/gmail/v1/users/me/messages/{MESSAGE_ID}?format=full" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

Extract from each message:
- **From** (sender name + email)
- **Subject**
- **Date**
- **Body** (check `payload.parts` for text/plain or text/html, base64-decode the body)

To decode the body:
```bash
echo "BASE64_BODY_DATA" | base64 -d
```

---

## Step 3: Categorize Each Email

Read each email carefully and assign ONE category:

### Category 1 — Customer (Label: `Agent/Customer`)
- Questions about your content, products, orders, shipping, refunds
- Reader questions about your domain expertise (e.g., "How do I fix my sourdough starter?")
- Subscription or account inquiries

### Category 2 — Partnership (Label: `Agent/Partnership`)
- Collaboration requests, guest post pitches, newsletter swap offers
- SEO/marketing service offers, influencer outreach
- Media or press inquiries

### Category 3 — Finance (Label: `Agent/Finance`)
- Payment confirmations, invoices, subscription renewal notices
- Billing issues, refund requests involving money
- Any email mentioning specific dollar amounts, payments, or charges

### Category 4 — Miscellaneous (Label: `Agent/Misc`)
- Anything that doesn't cleanly fit above
- Automated notifications that need human review
- Ambiguous emails

---

## Step 4: Apply Gmail Labels

First, check if the Agent labels exist. If not, create them:

```bash
# List existing labels
EXISTING_LABELS=$(curl -s "https://gmail.googleapis.com/gmail/v1/users/me/labels" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

# For each Agent label, check if it exists. If not, create it. If it exists, update its color.
# Label colors:
#   Agent/Customer    — green  (#16a765)
#   Agent/Partnership — blue   (#4986e7)
#   Agent/Finance     — red    (#cc3a21)
#   Agent/Misc        — yellow (#fad165)

# Example: check if Agent/Customer exists
LABEL_ID=$(echo "$EXISTING_LABELS" | jq -r '.labels[] | select(.name=="Agent/Customer") | .id')

if [ -z "$LABEL_ID" ]; then
  # Create with color
  curl -s -X POST "https://gmail.googleapis.com/gmail/v1/users/me/labels" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "Agent/Customer", "labelListVisibility": "labelShow", "messageListVisibility": "show", "color": {"backgroundColor": "#16a765", "textColor": "#ffffff"}}'
else
  # Update color on existing label
  curl -s -X PATCH "https://gmail.googleapis.com/gmail/v1/users/me/labels/$LABEL_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"color": {"backgroundColor": "#16a765", "textColor": "#ffffff"}}'
fi

# Repeat for Agent/Partnership (#4986e7), Agent/Finance (#cc3a21), Agent/Misc (#fad165)
```

Apply the label to each message:

```bash
curl -s -X POST "https://gmail.googleapis.com/gmail/v1/users/me/messages/{MESSAGE_ID}/modify" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"addLabelIds": ["LABEL_ID"]}'
```

---

## Step 5: Draft Replies (Categories 1 & 2 Only)

**IMPORTANT:** Read the email persona file (path from CLAUDE.md) before drafting. You ARE the email persona.

### For Category 1 (Customer) and Category 2 (Partnership):

Draft a reply in Gmail. The draft must be a reply to the original message (use `threadId`).

Build the raw RFC 2822 email, then base64url encode it:

```bash
# Build the raw email (use FROM_EMAIL and sign-off from CLAUDE.md/persona file)
RAW_EMAIL=$(cat <<'EMAILEOF'
From: ${FROM_EMAIL}
To: SENDER_EMAIL
Subject: Re: ORIGINAL_SUBJECT
In-Reply-To: ORIGINAL_MESSAGE_ID_HEADER
References: ORIGINAL_MESSAGE_ID_HEADER
Content-Type: text/plain; charset="UTF-8"

YOUR REPLY TEXT HERE

[Sign-off from persona file]
EMAILEOF
)

# Base64url encode it
ENCODED=$(echo -n "$RAW_EMAIL" | base64 -w 0 | tr '+/' '-_' | tr -d '=')

# Create the draft as a reply in the same thread
curl -s -X POST "https://gmail.googleapis.com/gmail/v1/users/me/drafts" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\": {\"raw\": \"$ENCODED\", \"threadId\": \"THREAD_ID\"}}"
```

### Draft Content Rules:
- **3-5 sentences max** unless the inquiry genuinely requires more detail
- **Reference their specific question** — no generic "thanks for reaching out" without substance
- **Stay in character as the email persona** — match the tone from the persona file
- **Link to relevant site content** when it naturally fits
- **Never commit to pricing, timelines, or partnerships** — express interest, ask a question, let operator decide
- **Category 2 replies:** Always ask exactly ONE qualifying question

### For Category 3 (Finance):
- **DO NOT draft a reply**
- Create an Asana task in Inbox section (use ASANA_INBOX_SECTION_GID from env) flagged High priority:

```bash
curl -s -X POST "https://app.asana.com/api/1.0/tasks" \
  -H "Authorization: Bearer $ASANA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "[FINANCE] Subject of email — from Sender Name",
      "notes": "Email from: sender@email.com\nDate: DATE\nSubject: SUBJECT\n\nSummary: Brief summary of the financial matter.\n\nAmount: $X (if visible)\nAction needed: Operator to review and respond.",
      "projects": ["'${ASANA_PROJECT_GID}'"],
      "memberships": [{"project": "'${ASANA_PROJECT_GID}'", "section": "'${ASANA_INBOX_SECTION_GID}'"}]
    }
  }'
```

### For Category 4 (Misc):
- If it's a genuine question from a reader in your domain: draft a helpful reply as the email persona
- If it's spam or automated junk: mark as read, skip
- If it's ambiguous or potentially important: create an Asana task for operator:

```bash
curl -s -X POST "https://app.asana.com/api/1.0/tasks" \
  -H "Authorization: Bearer $ASANA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "[MISC] Subject of email — needs review",
      "notes": "Email from: sender@email.com\nDate: DATE\nSubject: SUBJECT\n\nSummary: Brief description of the email content.\n\nSuggested action: [your recommendation]",
      "projects": ["'${ASANA_PROJECT_GID}'"],
      "memberships": [{"project": "'${ASANA_PROJECT_GID}'", "section": "'${ASANA_INBOX_SECTION_GID}'"}]
    }
  }'
```

---

## Step 6: Mark Processed Emails as Read

After categorizing, labeling, and drafting (if applicable), mark each email as read:

```bash
curl -s -X POST "https://gmail.googleapis.com/gmail/v1/users/me/messages/{MESSAGE_ID}/modify" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"removeLabelIds": ["UNREAD"]}'
```

---

## Step 7: Log Summary

Append a summary to `/home/agent/project/observations.md`:

```
## YYYY-MM-DD HH:MM — Email Check

**Emails processed:** X
- Category 1 (Customer): X — drafted replies
- Category 2 (Partnership): X — drafted replies
- Category 3 (Finance): X — escalated to Asana
- Category 4 (Misc): X — [action taken]

**Notable items:**
- [Any emails the operator should specifically review]
```

Also update MEMORY.md if any email reveals something the agent should remember long-term (e.g., a recurring partner, a customer complaint pattern, a new business inquiry).

---

## Checklist Before Finishing
- [ ] All unread emails from last 24h fetched and read
- [ ] Each email categorized into exactly one category
- [ ] Gmail labels applied to every processed email
- [ ] Draft replies created for Category 1 and Category 2 emails
- [ ] Category 3 emails escalated to Asana (no draft reply)
- [ ] Category 4 handled appropriately (reply, skip, or Asana)
- [ ] All processed emails marked as read
- [ ] Summary logged to observations.md

---

## Telegram Alert

Before finishing, send a Telegram alert summarizing the result:

**On success:**
```bash
bash /home/agent/project/telegram-alert.sh "✅ email-checker — [N] emails processed: [N] customer, [N] partnership, [N] finance, [N] misc"
```

**On failure:**
```bash
bash /home/agent/project/telegram-alert.sh "❌ email-checker — [error details]"
```

**On skip:**
```bash
bash /home/agent/project/telegram-alert.sh "⚠️ email-checker — [skip reason]"
```

---

## SKILL_RESULT

```
SKILL_RESULT: success | [N] emails processed: [N] customer, [N] partnership, [N] finance, [N] misc
```

On skip: `SKILL_RESULT: skip | No unread emails | inbox empty`
On fail: `SKILL_RESULT: fail | [error details]`

---

Run: As scheduled in schedule.json (12:00 and 21:00 WITA daily)
