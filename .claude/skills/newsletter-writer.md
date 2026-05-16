---
skill: newsletter-writer
version: 1.0.0
cadence: weekly (Friday)
trigger: cron
airtable_reads: [Newsletter Queue]
airtable_writes: [Newsletter Queue, Newsletter Log]
external_apis: [sendy, replicate, tinify]
sub_skills: [email-verifier.md]
active: true
notes: "Reads from newsletter-researcher brief. Sends via Sendy."
---

# Newsletter Writer Skill

## What This Skill Does (Plain English)
Every Friday, this skill takes the research brief prepared by newsletter-researcher, writes a complete HTML email newsletter, generates a hero image, and sends it to the full subscriber list via Sendy. The newsletter includes a warm greeting, a featured blog post summary with a "Read More" button, three quick takeaways, and a product or community CTA — all in the brand voice defined in CLAUDE.md, signed by your email persona.

---

## Purpose
Take the queued newsletter brief from the Newsletter Queue, write a complete email newsletter, and send it via Sendy to the main subscriber list. Runs every Friday.

## Prerequisites
- SENDY_URL, SENDY_API_KEY, SENDY_LIST_MAIN, SENDY_BRAND_ID in .env
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID in .env
- REPLICATE_API, TINIFY_API in .env

## Padding layers (read FIRST, before drafting any HTML)

This skill is **generic** — the brand's voice, north star, persona, and facts come entirely from the per-brand padding files at the container root. Read in this order before drafting:

1. **`/home/agent/project/brand-rules.md`** — REQUIRED. ICP, mission, doctrine, allowed/disallowed claims, newsletter CTA. The whole newsletter must serve the ICP and obey the claims policy. If missing → SKILL_RESULT: fail | brand-rules.md missing. Fire ❌ Telegram.
2. **`/home/agent/project/brand-voice.md`** — REQUIRED. Tone, banned phrases, signature moves, surface rules (Oxford comma / em dashes / exclamations). Every sentence must pass these. If missing → fall back to CLAUDE.md voice section + fire ⚠️ Telegram warning.
3. **`/home/agent/project/email-persona.md`** — REQUIRED. Sender persona (name, role, sign-off, signature voice). The newsletter is signed by this persona; opener and sign-off pull from here. If missing → SKILL_RESULT: fail | email-persona.md missing. Fire ❌ Telegram.
4. **`/home/agent/project/knowledge-base.md`** OR **`/home/agent/project/knowledge_base/`** — OPTIONAL but strongly recommended. Any factual claim in the newsletter (product mechanism, ingredient, study citation, evidence) must be backed by the KB. If a needed fact is missing from KB, escalate ("KB gap: I need X to write claim Y") — do not fabricate.

After reading the padding, proceed to the steps below.

## Process

### Step 1: Read Newsletter Queue
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_NEWSLETTER_QUEUE_TABLE}?filterByFormula=Status='Queued'&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
If empty: SKILL_RESULT: skip | Newsletter Queue empty — researcher hasn't run yet. Fire ⚠️ Telegram.

Extract: Subject Line Options, Research Brief, Featured Post URL, CTA, Tone Note.

### Step 2: Mark as In Progress
Update Airtable record Status: In Progress.

### Step 3: Pick best subject line
From the 3 options in the brief, pick the one most likely to get opens based on:
- Curiosity gap
- Specificity
- Relevance to current events, season, or industry trends

### Step 4: Generate hero image

**CRITICAL — IMAGE URL RULE:**
- `tinified_url` = TEMPORARY Tinify CDN link. **Expires within hours. NEVER use in emails.**
- `wp_media_url` = PERMANENT WordPress media URL. **This is the ONLY URL safe for newsletters.**

```bash
IMAGE_JSON=$(bash /home/agent/project/generate-image.sh \
  --prompt "[mystical, on-brand image relevant to newsletter topic]" \
  --aspect-ratio "16:9" \
  --filename "newsletter-[slug]-[date]" \
  --upload)

# Extract the PERMANENT WordPress URL — the ONLY URL safe for emails
HERO_IMAGE_URL=$(echo "$IMAGE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['wp_media_url'])")
```

**Before writing the HTML, verify the URL is your WordPress domain (from WP_URL env var):**
```bash
echo "$HERO_IMAGE_URL" | grep -q "${WP_URL#https://}" || echo "ERROR: Hero image URL is not a WordPress URL!"
```
If the URL contains `tinify`, `api.tinify.com`, or `replicate.delivery` — STOP. Something went wrong. Re-extract `wp_media_url` from the JSON.

### Step 5: Write full newsletter HTML
Structure:
```html
<!-- Header: brand logo + tagline (tagline from brand-rules.md "Tagline energy") -->
<!-- Hero image -->
<!-- Opening paragraph: 40-60 words, in brand-voice.md voice, addressed by email-persona.md sender -->
<!-- Featured section: post title as H2, 100-word summary, "Read More" button -->
<!-- 3 Quick Takeaways: bullet list, each 1-2 sentences, banned-phrase-free per brand-voice.md -->
<!-- Mid-section CTA: pull from brand-rules.md § "CTAs by surface — Newsletter" -->
<!-- Closing: sign-off per email-persona.md "Sign-Off" section -->
<!-- Footer: unsubscribe link, social links, brand address -->
```

**Voice/claims validation before render:**
- Scan draft against `brand-voice.md` § "Banned phrases" — if any present, rewrite
- Scan claims against `brand-rules.md` § "Allowed claims / disallowed claims" — if any disallowed claim present, rewrite or remove
- Surface rules (Oxford comma, em dash, exclamation cap, English variant) per `brand-voice.md` § "Surface rules"

### Step 6: Send via Sendy
**IMPORTANT:** `SENDY_URL` env var is just the domain (no protocol). Always prefix with `https://`.
Use `--data-urlencode` for HTML fields to handle special characters.
```bash
# Use email persona name and brand details from CLAUDE.md
curl -s -X POST "https://${SENDY_URL}/api/campaigns/create.php" \
  --data-urlencode "api_key=${SENDY_API_KEY}" \
  --data-urlencode "from_name=${SENDY_FROM_NAME}" \
  --data-urlencode "from_email=${SENDY_FROM_EMAIL}" \
  --data-urlencode "reply_to=${SENDY_REPLY_TO}" \
  --data-urlencode "title=[subject line]" \
  --data-urlencode "subject=[subject line]" \
  --data-urlencode "plain_text=[plain text version]" \
  --data-urlencode "html_text=[full HTML]" \
  --data-urlencode "list_ids=${SENDY_LIST_MAIN}" \
  --data-urlencode "brand_id=${SENDY_BRAND_ID}" \
  --data-urlencode "send_campaign=1"
```

### Step 7: Log to Newsletter Log
Create Airtable record in Newsletter Log:
- Subject, Send Date, Sendy Campaign ID, List Sent To

Update Newsletter Queue record Status: Sent.

### Step 8: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ newsletter-writer — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ newsletter-writer — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ newsletter-writer — [skip reason]"`

```
SKILL_RESULT: success | Newsletter sent — "[subject line]" to [list_name]
```

## Error Handling
- Sendy API error → SKILL_RESULT: fail | Sendy error — check SENDY credentials
- Keep HTML email under 100KB
- Always include plain text version

## Rules
- Always read .claude/skills/email-verifier.md sub-skill before sending if list health is in question
- Never send without a subject line
- Always include unsubscribe link
- Sign off per `email-persona.md` § "Sign-Off"
- **Never bake brand-specifics into this skill body.** If you find yourself wanting to add brand-specific tone rules — that belongs in `brand-voice.md`, not here.
- **No backfill on miss.** If this skill is run for a slot it already completed, exit cleanly. Forward-only — see `feedback_backfill_default_off` policy.
