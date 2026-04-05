---
skill: email-verifier
version: 1.0.0
type: sub-skill
trigger: called-by-parent
external_apis: [millionverifier, bounceban]
notes: "Sub-skill. Called by link-outreach-lead-finder, b2b-outreach-lead-finder, newsletter-writer, sendy-sync. Verifies email deliverability via MillionVerifier + BounceBan waterfall."
---

# Email Verifier — Sub-Skill

## What This Skill Does (Plain English)
This is a helper skill (not run on its own) that checks whether email addresses are real and deliverable before we send to them. It runs each address through MillionVerifier first; if the result is "catch-all" (meaning the server accepts everything, so we cannot tell if the mailbox exists), it sends it to BounceBan for a second opinion. Each email comes back as Verified, Risky, or Invalid. Other skills like the outreach lead finder and newsletter writer call this to clean their email lists.

---

Verify email deliverability using MillionVerifier as primary and BounceBan as catch-all fallback. Returns verified status for each email. Called by other skills — never runs standalone.

## Input
Array of email addresses to verify.

## APIs Used
| Service | Env Var | Purpose |
|---------|---------|---------|
| MillionVerifier | MILLIONVERIFIER_API_KEY | Primary verification |
| BounceBan | BOUNCEBAN_API_KEY | Catch-all verification |

## Process

### Phase 1: MillionVerifier
For each email:
```bash
curl -s --retry 3 --retry-delay 2 "https://api.millionverifier.com/api/v3/?api=${MILLIONVERIFIER_API_KEY}&email=[email]&timeout=10"
```

Response quality values:
- `good` → **Verified** ✅
- `catch_all` → send to Phase 2 (BounceBan)
- `bad` / `unknown` / `disposable` → **Invalid** ❌

### Phase 2: BounceBan (catch-alls only)
For emails that returned `catch_all` from MillionVerifier:
```bash
curl -s --retry 3 --retry-delay 2 "https://api-waterfall.bounceban.com/v1/verify/single?email=[email]" \
  -H "Authorization: ${BOUNCEBAN_API_KEY}"
```

BounceBan result mapping:
- `deliverable` → **Verified** ✅
- `risky` → **Risky** ⚠️
- `undeliverable` → **Invalid** ❌

## Output
For each email, return one of:
- **Verified** — safe to send
- **Risky** — catch-all, may or may not deliver, use with caution
- **Invalid** — do not send

## Rules
- Never send to Invalid emails
- Risky emails can be pushed to Airtable but flagged — parent skill decides whether to use them
- Rate limit: add 0.2s delay between MillionVerifier calls
- BounceBan is only called for catch-alls — don't waste credits on already-classified emails
- This sub-skill ONLY verifies — it does not write to Airtable. Parent skill handles all Airtable updates.
