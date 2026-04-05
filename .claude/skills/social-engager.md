---
skill: social-engager
version: 1.2.0
cadence: daily (16:00 WITA)
trigger: cron
source: Airtable Social Mining tables + Reddit .json API (free, primary) with ScrapeCreators fallback
airtable_reads: [Social Mining Queue, Social Mining Drafts, Social Mining Log]
airtable_writes: [Social Mining Drafts, Social Mining Log, Social Mining Queue]
external_apis: [reddit-json, scrapecreators, kerykeion, ephem]
active: true
phase: 1 (manual posting — all posting is done by human/VA from Airtable)
notes: "Monitors conversations where we have responded, tracks engagement, detects new replies, drafts follow-ups when warranted, manages conversation lifecycle, and flags ready drafts for manual posting."
---

# Social Engager — Conversation Monitoring & Follow-Up Skill

## What This Skill Does (Plain English)

After the social-miner discovers Reddit posts and drafts responses (queued in Airtable), a human manually posts the best ones. This skill picks up from there:

1. **Detects newly posted drafts** — when a human changes a draft's status to "Posted" in Airtable, this skill notices and creates a Log record to start tracking that conversation.
2. **Monitors active conversations** — checks each tracked Reddit thread for new replies to our comment using the free Reddit .json API (no paid API needed).
3. **Categorizes replies** — determines if a reply is a question (draft follow-up), a thank-you (log and move on), hostile (ignore), or a service request (soft CTA with human review).
4. **Drafts follow-up responses** — when someone asks a follow-up question, this skill pulls fresh niche data and drafts a reply, again with full Data Reasoning evidence.
5. **Manages lifecycle** — expires old conversations after 7 days, retires stale queue items, and reports how many drafts are waiting for a human to post.

This skill does NOT post anything. In Phase 1, all posting is manual. This skill is the monitoring and intelligence layer.

**How the three tables connect:**
```
Social Mining Queue (discovered posts)
    ↓ Queue Record ID
Social Mining Drafts (our responses — initial + follow-ups)
    ↓ Draft Record ID + Queue Record ID
Social Mining Log (conversation tracking — metrics, replies, lifecycle)
```

---

## Prerequisites

| Requirement | Env Var / Location | Purpose |
|---|---|---|
| Airtable credentials | `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID` | Read/write all 3 tables |
| Queue table ID | `AIRTABLE_SOCIAL_MINING_QUEUE_TABLE` | Look up original post data |
| Drafts table ID | `AIRTABLE_SOCIAL_MINING_DRAFTS_TABLE` | Check for newly posted items, create follow-ups |
| Log table ID | `AIRTABLE_SOCIAL_MINING_LOG_TABLE` | Track conversations, update metrics |
| Niche data hook | Varies by niche (e.g., kerykeion, ephem) | Enrich follow-up responses with real data |
| Reddit .json API | No auth needed — free, public | Primary monitoring channel for replies and metrics |
| ScrapeCreators API | `SCRAPECREATORS_API_KEY` | Fallback when Reddit .json returns 403 (VPS IPs often blocked) |

**Python libraries required:** `requests`, `kerykeion`, `ephem` (installed via post-start.sh)

---

## Follow-Up Rules

These rules prevent over-engagement and protect the brand from looking spammy or aggressive.

```yaml
follow_up_rules:
  max_depth: 3            # Original response + 2 follow-ups maximum
  max_per_thread: 3       # Never post more than 3 comments in one thread
  cooldown_hours: 12      # Minimum gap between checking the same conversation
  skip_after_days: 7      # Mark conversation expired after 1 week
  cta_allowed_after: 2    # Only mention our site after 2+ genuine value exchanges
  cta_requires_review: true  # Any draft containing a link stays in "Draft" status for human review
```

---

## Reply Decision Matrix

When new replies to our comments are detected, categorize each reply and take the appropriate action:

| Reply Type | Example | Action |
|---|---|---|
| **Direct question** | "What about Scorpio?" / "How much fertilizer?" | Draft a follow-up response with fresh data enrichment |
| **Sharing experience** | "OMG same, I'm a Cancer too" / "I tried that, worked great" | Draft brief warm acknowledgment (1-2 sentences) |
| **Thank you / agreement** | "This is so helpful!" / "Thanks!" | No follow-up needed — log as healthy engagement |
| **Hostile / trolling** | "Astrology is fake" / "This is garbage advice" | Skip entirely — do not engage under any circumstances |
| **Service request** | "Can you do my chart?" / "Do you offer consultations?" | Warm redirect with soft CTA — only if depth >= 2, requires human review |
| **Expert correction** | "Actually, Mercury is in Pisces, not Aries" | Draft gracious response acknowledging their point, verify our data |

---

## Process (Step by Step)

### Step 1: Load Context

1. **CLAUDE.md** — niche keywords, brand voice, data hook config
2. **observations.md** (tail ~30 lines) — recent social mining activity, any notes from previous engager runs

---

### Step 2: Check for Newly Posted Drafts → Create Log Records

When a human posts a draft (changes its status to "Posted" in Airtable), this step detects it and starts tracking the conversation.

**2a. Find drafts that have been posted but don't have a Log record yet:**
```bash
curl -s --retry 3 --retry-delay 2 \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_DRAFTS_TABLE}?filterByFormula=AND({Status}='Posted',{Log Record ID}='')" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```

**2b. For each newly posted draft, look up the original post URL from the Queue table:**
```bash
curl -s --retry 3 --retry-delay 2 \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_QUEUE_TABLE}/QUEUE_RECORD_ID" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```

**2c. Create a Log record to start tracking the conversation:**

| Field | Value | Notes |
|-------|-------|-------|
| Draft Record ID | From the draft record | Links back to draft |
| Queue Record ID | From the draft's Queue Record ID field | Links back to original post |
| Platform | "Reddit" | Single select |
| Original Post URL | From Queue record's Post URL | Used for Reddit .json monitoring |
| Response Permalink | From draft's Response Permalink field | URL of our posted comment |
| Posted By | From draft's Posted By field | Who posted (Operator, VA, etc.) |
| Posted Date | From draft's Posted Date field | When it was posted |
| Upvotes | 0 | Will be updated during monitoring |
| Reply Count | 0 | Will be updated during monitoring |
| Follow-Up Needed | false | Updated if replies are detected |
| Follow-Up Done | false | Updated after follow-up is posted |
| Follow-Up Count | 0 | Incremented with each follow-up |
| Conversation Status | "Active" | Active → Complete or Expired |
| Last Checked | Today's date | YYYY-MM-DD |
| Days Monitored | 0 | Incremented daily |

```bash
LOG_RESPONSE=$(curl -s --retry 3 --retry-delay 2 -X POST \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_LOG_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  --data-raw '{"typecast": true, "records": [{"fields": { ... }}]}')

LOG_RECORD_ID=$(echo "$LOG_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['records'][0]['id'])")
```

**2d. Link the Log record back to the Draft:**
```bash
curl -s --retry 3 --retry-delay 2 -X PATCH \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_DRAFTS_TABLE}/DRAFT_RECORD_ID" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"Log Record ID": "LOG_RECORD_ID"}}'
```

---

### Step 3: Fetch Active Conversations from Log

```bash
curl -s --retry 3 --retry-delay 2 \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_LOG_TABLE}?filterByFormula={Conversation Status}='Active'" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```

If no active conversations AND no newly posted drafts from Step 2, skip to Step 6.

---

### Step 4: Monitor Each Active Conversation

For each active conversation in the Log:

**4a. Check cooldown:**
If `Last Checked` is within the last 12 hours, skip this conversation. Since the engager runs once daily at 16:00, each conversation is typically checked once per day.

**4b. Check expiry:**
Calculate days since `Posted Date`. If >= 7 days:
- Update Log: `Conversation Status` → "Expired", update `Last Checked` and `Days Monitored`
- Skip to next conversation

**4c. Fetch current thread state (Reddit .json primary, ScrapeCreators fallback):**

Try the free Reddit .json API first. If it returns 403 (Reddit blocks many VPS/datacenter IPs), fall back to ScrapeCreators. Use Python `requests` — curl returns 401 with ScrapeCreators.

```python
import os, requests

url = ORIGINAL_POST_URL.rstrip("/")

# Primary: Reddit .json (free, no auth)
r = requests.get(f"{url}.json", headers={"User-Agent": "JonOpsAgent/1.0"}, timeout=15)

if r.status_code == 403:
    # Fallback: ScrapeCreators Reddit Post Comments endpoint
    sc = requests.get(
        "https://api.scrapecreators.com/v1/reddit/post/comments",
        headers={"x-api-key": os.environ["SCRAPECREATORS_API_KEY"]},
        params={"url": url, "trim": "false"},
        timeout=20,
    )
    sc.raise_for_status()
    data = sc.json()
    # Log fallback usage + credits_remaining in observations.md
    post_data = data.get("post", {})
    comments = data.get("comments", [])
    thread_locked = post_data.get("locked", False)
else:
    r.raise_for_status()
    listing = r.json()
    post_data = listing[0]["data"]["children"][0]["data"]
    comments = listing[1]["data"]["children"]
    thread_locked = post_data.get("locked", False)
```

Parse the returned data to find our comment (match by Response Permalink or by matching comment text). Extract:
- Current upvote count (score) for our comment
- Direct replies to our comment (new since last check)
- Whether the thread is locked

**Note:** ScrapeCreators response shape differs slightly from Reddit's native JSON — the fallback wraps comments in a flat array under `comments` (with nested `replies`), while Reddit .json wraps them under `data.children[*].data`. Handle both shapes when extracting our comment.

**4d. Update metrics in the Log record:**
```bash
curl -s --retry 3 --retry-delay 2 -X PATCH \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_LOG_TABLE}/LOG_RECORD_ID" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {
    "Upvotes": CURRENT_SCORE,
    "Reply Count": CURRENT_REPLY_COUNT,
    "Last Checked": "YYYY-MM-DD",
    "Days Monitored": DAYS_SINCE_POSTED
  }}'
```

**4e. If thread is locked:** Mark conversation as "Complete" with note "Thread locked by moderators". Skip to next.

---

### Step 5: Handle New Replies

Compare the current reply count to the stored `Reply Count`. If there are new replies to our comment:

**5a. Read each new reply's text.**

**5b. Categorize each reply** using the Reply Decision Matrix (see table above).

**5c. Check limits before drafting a follow-up:**
- If `Follow-Up Count` >= 3 (max_per_thread): set `Follow-Up Needed: false`, skip
- If latest draft's `Thread Depth` >= 3 (max_depth): set `Follow-Up Needed: false`, skip
- If the reply doesn't warrant a follow-up (thanks, hostile, etc.): log the reply type but don't draft

**5d. If a follow-up IS warranted — pull fresh niche data:**
Use the same data enrichment method as social-miner Step 4 (kerykeion/ephem for astrology, or the relevant niche data hook). Get current, real data relevant to the reply's question.

**5e. Draft the follow-up response:**
- 2-4 sentences (shorter than the initial response)
- Reference what the replier specifically said
- Add NEW data or perspective — don't repeat the initial response
- Include Data Reasoning (same format as social-miner Step 6)
- **CTA rules:** If `Thread Depth` >= 2 AND the reply is asking for more resources → may include a soft, natural CTA (e.g., "I actually wrote about this recently if you want to dig deeper"). Mark `Contains CTA: true` and set Status to "Draft" (requires human review).
- If no CTA: set Status to "Ready"

**5f. Create a Drafts record for the follow-up:**

| Field | Value |
|-------|-------|
| Queue Record ID | Same as the original Queue Record ID |
| Platform | "Reddit" |
| Draft Response | The follow-up text |
| Astrology Data Used | Brief data summary |
| Data Reasoning | Full evidence chain (SOURCE, RAW DATA, WHY THIS DATA, VERIFICATION) |
| Is Follow-Up | true |
| Parent Comment URL | URL of the reply we're responding to |
| Thread Depth | Previous depth + 1 |
| Contains CTA | true/false |
| Status | "Ready" (no CTA) or "Draft" (has CTA — needs human review) |
| Log Record ID | The conversation's Log Record ID |

**5g. Update the Log record:**
- Set `Follow-Up Needed: true`
- Increment `Follow-Up Count`

---

### Step 6: Report Ready Drafts Count

Count all drafts currently in "Ready" status (waiting for a human to post):

```bash
curl -s --retry 3 --retry-delay 2 \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_DRAFTS_TABLE}?filterByFormula={Status}='Ready'" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```

This count is included in the Telegram alert so the operator/VA knows items are waiting for manual posting.

---

### Step 7: Expire Old Queue Items

Check for Queue items older than 7 days that were never posted (Status is still "New" or "Drafted"):

```bash
curl -s --retry 3 --retry-delay 2 \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_QUEUE_TABLE}?filterByFormula=AND(OR({Status}='New',{Status}='Drafted'),IS_BEFORE({Found Date},'$(date -d '7 days ago' +%Y-%m-%d)'))" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```

For each expired Queue record:
1. Update Queue record: Status → "Expired"
2. Find any linked Drafts that are still "Ready" or "Draft": update to "Skipped"

This keeps the tables clean and prevents humans from accidentally posting stale content.

---

### Step 8: Update observations.md

Append a structured summary:

```
## YYYY-MM-DD HH:MM — Social Engager

**Skill:** social-engager | **Status:** SUCCESS
**Log records created (newly posted):** N
**Active conversations monitored:** N
**Conversations expired (7+ days):** N
**New replies detected:** N
  - [Post Title] — reply type: question → follow-up drafted
  - [Post Title] — reply type: thanks → no action
**Follow-up drafts created:** N
**Drafts ready for manual posting:** N (total in Ready status)
**Queue items expired:** N
**Reddit .json API calls:** ~N
```

---

### Step 9: Telegram Alert & SKILL_RESULT

**On success:**
```bash
bash /home/agent/project/telegram-alert.sh "✅ social-engager — Monitored N conversations, N new replies, N follow-ups drafted, N ready for posting"
```

**On failure:**
```bash
bash /home/agent/project/telegram-alert.sh "❌ social-engager — [error details]"
```

**On skip (nothing to do):**
```bash
bash /home/agent/project/telegram-alert.sh "⚠️ social-engager — No active conversations or ready drafts"
```

**Final line of output (required by dispatcher):**
```
SKILL_RESULT: success | Monitored N active, N replies detected, N follow-ups drafted, N ready for posting | N/A
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Reddit .json returns 403 (VPS IP blocked) | Fall back to ScrapeCreators `/v1/reddit/post/comments` for this and remaining conversations this run. Log fallback + `credits_remaining` in observations.md. |
| Reddit .json returns 429 (rate limited) | Wait 60 seconds, retry once. If still fails, skip remaining conversations and report partial results. |
| Reddit .json returns 404 (post deleted) | Mark Log conversation as "Complete", add note "Post deleted by author or mods". |
| Reddit .json returns empty/malformed data | Skip that conversation, note in observations.md, try again tomorrow. |
| ScrapeCreators also fails (fallback exhausted) | Skip that conversation, note in observations.md, try again tomorrow. |
| Thread is locked | Mark conversation as "Complete", add note "Thread locked". |
| Airtable write fails | SKILL_RESULT: fail — check API key and table IDs. |
| No activity (no posted drafts, no active conversations) | SKILL_RESULT: skip — this is normal early on. |

---

## Rules (Non-Negotiable)

1. **NEVER post anything directly in Phase 1.** All posting is manual via Airtable.
2. **NEVER exceed follow-up limits:** max_depth 3, max_per_thread 3.
3. **NEVER check a conversation more than once per 12 hours.**
4. **NEVER include CTAs before 2+ genuine value exchanges.**
5. **Any draft with Contains CTA = true MUST stay in "Draft" status** (human review required).
6. **Prefer Reddit .json API (free) for monitoring. Fall back to ScrapeCreators only when Reddit .json returns 403.** Log every fallback + `credits_remaining` in observations.md so we can track paid usage.
7. **ALWAYS populate Data Reasoning** on follow-up drafts (same standard as social-miner).
8. Keep follow-up responses shorter than initial responses (2-4 sentences).
9. Always update `Last Checked` and `Days Monitored` after checking a conversation.
10. **NEVER engage with hostile or trolling replies.**
11. If a thread has only positive engagement (upvotes, thanks), note it as healthy but don't force a follow-up.

---

## Niche Adaptation Guide

This skill adapts to any business niche via CLAUDE.md configuration:

| Variable | What Changes |
|----------|-------------|
| Data hook for follow-ups | Same as social-miner (kerykeion/ephem for astrology, USDA for landscaping, etc.) |
| Reply tone | Matches niche culture (casual for lifestyle, precise for technical, careful for legal) |
| Follow-up rules | Adjustable per project (e.g., longer cooldown for sensitive niches) |
| Liability level | High-liability niches (legal, medical) should set `human_review_required: true` for ALL drafts |
| skip_after_days | 7 for most niches, shorter for fast-moving topics, longer for evergreen advice |
| CTA style | Niche-appropriate (astrology: "I wrote about this", landscaping: "we have a guide", bakery: "here's our recipe") |

---

## Airtable Field Reference

**Social Mining Log table:**
| Field | Type | Description |
|-------|------|-------------|
| Draft Record ID | singleLineText | Links to the Draft record for our response |
| Queue Record ID | singleLineText | Links to the Queue record for the original post |
| Platform | singleSelect | "Reddit" |
| Original Post URL | url | The Reddit post we responded to |
| Response Permalink | url | Direct URL to our posted comment |
| Posted By | singleSelect | Who posted: Operator, VA, Agent |
| Posted Date | date | When the response was posted |
| Upvotes | number | Current upvote count on our comment (updated each check) |
| Reply Count | number | Number of direct replies to our comment (updated each check) |
| Follow-Up Needed | checkbox | True if a reply warrants a follow-up response |
| Follow-Up Done | checkbox | True if all warranted follow-ups have been posted |
| Follow-Up Count | number | Total follow-up responses in this thread |
| Conversation Status | singleSelect | Active → Complete / Expired |
| Last Checked | date | Date of most recent monitoring check |
| Days Monitored | number | Total days since Posted Date |
| Notes | multilineText | Free-form notes (locked reason, deletion, etc.) |

---

## Phase 2 Notes (Future — Automated Posting)

When automated posting is enabled in a future phase:

- **Step 6 changes:** Instead of just reporting the Ready count, the engager picks up Ready drafts and posts them via PRAW (Reddit API) or browser-use.com (cloud browser automation).
- **After posting:** Update Draft (Status → "Posted", fill Posted Date, Posted By → "Agent", fill Response Permalink) and create a Log record.
- **Rate limits for auto-posting:** Max 3-5 posts per run, minimum 30 minutes between posts, randomize timing.
- **New env vars needed:** `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` (for PRAW).
- **Browser-use.com alternative:** For platforms where API access is restricted (Instagram). Uses persistent cookie profiles and custom Chromium fork for bot detection resistance. ~$0.10-0.30/session.
