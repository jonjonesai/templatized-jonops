---
skill: social-miner
version: 1.1.0
cadence: daily (12:00 WITA)
trigger: cron
source: Reddit via ScrapeCreators API + Reddit .json fallback
airtable_reads: [Social Mining Queue, Social Mining Drafts, Social Mining Log]
airtable_writes: [Social Mining Queue, Social Mining Drafts]
external_apis: [scrapecreators, kerykeion, ephem]
active: true
phase: 1 (manual posting — drafts queued in Airtable for human/VA to copy-paste)
notes: "Discovers Reddit posts with engagement opportunities, enriches with real niche-specific data, drafts genuine community responses, and queues everything to Airtable with a full evidence trail."
---

# Social Miner — Community Engagement Discovery Skill

## What This Skill Does (Plain English)

This skill searches Reddit for posts where a genuine, knowledgeable response from our brand would add real value — without ever mentioning the brand. It finds 3-5 promising posts, pulls real data from authoritative sources to back up the response, drafts helpful replies, and saves everything to Airtable. A human then reviews the drafts and manually posts the best ones. The goal is thought leadership through genuine helpfulness, not promotion.

**Example (astrology niche):** Someone on r/AskAstrologers asks "Why do I keep attracting emotionally distant partners?" The skill finds this post, pulls today's real planetary positions (Venus square Pluto at 0.27° orb), drafts a 4-sentence response connecting their pattern to current transits, logs exactly where the data came from and why it's relevant, and queues it for a human to post.

**Example (landscaping niche):** Someone on r/landscaping asks "My azaleas are turning yellow." The skill would find the post, pull data from an authoritative gardening source about iron chlorosis in alkaline soil, draft a helpful reply, and log the source.

This framework is **niche-agnostic** — it reads keywords, subreddits, data sources, and tone from CLAUDE.md and adapts to any small business.

---

## Prerequisites

| Requirement | Env Var / Location | Purpose |
|---|---|---|
| ScrapeCreators API key | `SCRAPECREATORS_API_KEY` | Reddit post discovery |
| Airtable credentials | `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID` | Read/write queue and drafts |
| Queue table ID | `AIRTABLE_SOCIAL_MINING_QUEUE_TABLE` | Store discovered posts |
| Drafts table ID | `AIRTABLE_SOCIAL_MINING_DRAFTS_TABLE` | Store draft responses |
| Log table ID | `AIRTABLE_SOCIAL_MINING_LOG_TABLE` | Dedup against active conversations |
| Niche data hook | Varies by niche (e.g., `ASTROLOGY_API_KEY`, kerykeion, ephem) | Real data for response enrichment |
| Niche config | CLAUDE.md sections: "Niche Keywords", "Target Subreddits", "Brand Voice" | What to search, where, and how to write |

**Python libraries required:** `requests`, `kerykeion`, `ephem` (installed via post-start.sh)

---

## Follow-Up Rules (Reference — Enforced by social-engager)

These rules govern the full conversation lifecycle. Listed here for context; the social-engager skill enforces them.

```yaml
follow_up_rules:
  max_depth: 3          # Original response + 2 follow-ups max
  max_per_thread: 3     # Never dominate a conversation
  cooldown_hours: 12    # Minimum gap between checking same thread
  skip_after_days: 7    # Mark conversation complete after 1 week
  cta_allowed_after: 2  # Only mention our site after 2+ genuine value exchanges
  cta_requires_review: true  # Human must approve any post containing a link
```

---

## Target Subreddits

Read from CLAUDE.md → "Social Mining Config" section. Example for an astrology site:

| Subreddit | Why | Tone |
|---|---|---|
| r/astrology | Main hub, high volume | Knowledgeable but conversational |
| r/AskAstrologers | Question-heavy — ideal for value-add replies | More technical, precise |
| r/zodiacsigns | Casual, relatable | Warm, accessible, lighter |

**Examples for other verticals:**
- **Bakery:** r/Baking, r/Breadit, r/cakedecorating
- **Landscaping:** r/landscaping, r/gardening, r/lawncare
- **Legal:** r/legaladvice, r/smallbusiness, r/Entrepreneur

---

## Process (Step by Step)

### Step 0: Load Context

Read these files to understand what to search and how to write:

1. **CLAUDE.md** — extract:
   - Niche seed keywords (under "Niche Keywords" section)
   - Target subreddits (under "Social Mining Config" section)
   - Brand voice guidelines (under "Brand Voice" section — adapt for Reddit: less mystical, more direct)
   - Data hook type (under "Social Mining Config" → data hook)

2. **observations.md** (tail ~50 lines) — check for:
   - Keywords used in the last run (rotate to avoid repetition)
   - Recent astronomical events or niche-relevant developments
   - Any notes or patterns from previous social-miner runs

3. **Pick 2-3 seed keywords** for today's search. Rotate from the full keyword list. Do not repeat the exact same keywords as the previous run.

---

### Step 1: Dedup Check

Before searching, build a "seen URLs" set to avoid re-discovering posts we've already found or responded to.

**Query 1 — Recent queue entries (last 14 days):**
```bash
curl -s --retry 3 --retry-delay 2 \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_QUEUE_TABLE}?filterByFormula=IS_AFTER({Found Date},'$(date -d '14 days ago' +%Y-%m-%d)')&fields%5B%5D=Post%20URL&fields%5B%5D=Post%20Title" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```

**Query 2 — Active/complete conversations in the log:**
```bash
curl -s --retry 3 --retry-delay 2 \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_LOG_TABLE}?filterByFormula=OR({Conversation Status}='Active',{Conversation Status}='Complete')&fields%5B%5D=Original%20Post%20URL" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```

Combine all Post URLs from both queries into a set. **Never queue a post that appears in this set.**

---

### Step 2: Search Reddit via ScrapeCreators

**IMPORTANT: Use Python `requests` for all ScrapeCreators API calls.** The `curl` client returns 401 errors in this container environment. This is a known issue — `requests` works correctly with the same API key.

**Keyword searches (1 API call per keyword):**
```python
import os, requests

SC_KEY = os.environ['SCRAPECREATORS_API_KEY']
SC_HEADERS = {'x-api-key': SC_KEY}

# Search Reddit for posts matching a keyword (last 24 hours)
r = requests.get(
    'https://api.scrapecreators.com/v1/reddit/search',
    params={'query': 'KEYWORD', 'sort': 'relevance', 'time': 'day'},
    headers=SC_HEADERS
)
data = r.json()
posts = data.get('posts', [])
credits_remaining = data.get('credits_remaining', '?')
```

**Subreddit hot posts (1 API call per subreddit):**
```python
for sub in ['astrology', 'AskAstrologers', 'zodiacsigns']:
    r = requests.get(
        'https://api.scrapecreators.com/v1/reddit/subreddit',
        params={'subreddit': sub, 'sort': 'hot', 'limit': 15},
        headers=SC_HEADERS
    )
    sub_posts = r.json().get('posts', [])
    posts.extend(sub_posts)
```

**Budget: ~5-6 ScrapeCreators API calls total per run.** Monitor `credits_remaining` in the response and log it.

---

### Step 3: Score and Filter

From all results, evaluate each post against these criteria:

| Criteria | Weight | How to Assess |
|----------|--------|---------------|
| **Reply opportunity** | Highest | Is this a question? A request for advice? Can we genuinely help? |
| **Engagement** | High | Upvotes + comments signal a live, active thread |
| **Recency** | High | Posts < 12 hours old are best. < 24h acceptable. > 48h skip. |
| **Keyword relevance** | High | How closely does the post match our niche keywords? |
| **Comment gap** | Medium | Are there few/no quality replies yet? Opportunity to be the first helpful voice. |
| **Risk level** | Medium | Avoid locked threads, mod-heavy subs, crisis posts, medical questions |

Assign each post a composite score 1-10. Select the top 3-5.

**Auto-disqualify any post that:**
- Is locked or archived
- Is a mod announcement or meta/rules post
- Discusses personal medical/mental health crisis (liability risk)
- Already has a comprehensive, well-received top reply covering our angle
- Was posted by a known competitor account
- Is older than 48 hours

---

### Step 4: Pull Real Data from Authoritative Sources

This is the core differentiator. Every response must contain at least one specific, verifiable data point from a real source. The data source depends on the niche — read from CLAUDE.md.

**Example: Astrology niche — use kerykeion + ephem:**

```python
from kerykeion import AstrologicalSubject
from datetime import datetime, timezone
import ephem

# Current planetary positions via kerykeion
now = datetime.now(timezone.utc)
sky = AstrologicalSubject(
    "Now", now.year, now.month, now.day, now.hour, now.minute,
    lng=0, lat=0, city="Greenwich"
)

# Access planet data: sky.sun, sky.moon, sky.mercury, sky.venus, etc.
# Each has .sign, .position (degrees), .retrograde, etc.

# Moon phase via ephem
moon = ephem.Moon(now.strftime('%Y/%m/%d'))
moon_phase = moon.phase  # 0-100% illumination
```

**How to choose which data to use for each post:**
- Question about Mercury retrograde → exact Mercury position, retrograde status, affected signs
- Question about relationships/attraction → current Venus position, relevant aspects (squares, conjunctions)
- Question about career/challenges → current Saturn and Jupiter positions, relevant transits
- Question about emotions/energy → current Moon sign and phase
- General question → today's most notable aspect (tightest orb), moon phase

**Niche adaptation examples (for other businesses):**
- Landscaping: USDA Plant Hardiness Zone data, soil pH requirements from university extension services
- Baking: Ingredient ratios from established references (King Arthur, Serious Eats)
- Legal: Statutory citations, court rulings, bar association guidelines
- Health/beauty: Dermatology references (AAD, PubMed), ingredient safety data (EWG, CIR)

**The data must be real and verifiable. Never fabricate data points.**

---

### Step 5: Draft Responses

For each qualifying post (3-5), draft a genuine, helpful response.

**Response structure (3-6 sentences):**
1. **Acknowledge** the poster's question or experience (empathetic hook — show you read their post)
2. **Provide real data** with at least one specific, verifiable fact (planetary position, ingredient ratio, statute number, etc.)
3. **Explain practically** what this means for their specific situation
4. **Add insight** (optional) — share something they might not have considered
5. **Close warmly** — no sign-off signature, no links, no self-promotion

**Response rules:**
- 3-6 sentences maximum. Concise but substantial.
- Must include at least one specific, verifiable data point from Step 4
- Write as a knowledgeable community member, NOT as a brand or business
- NO links to our website or any website
- NO self-identification as a business ("as an astrologer at...", "at our company...")
- NO disclaimers or hedging — speak with warm authority
- Match the subreddit's tone and culture
- Adapt brand voice from CLAUDE.md for Reddit (typically less polished, more direct)

---

### Step 6: Queue to Airtable

For each post+draft pair, create two linked records.

**6a. Create a Social Mining Queue record (the discovered post):**

| Field | Value | Notes |
|-------|-------|-------|
| Post Title | Post title from Reddit | Plain text |
| Platform | "Reddit" | Single select |
| Post URL | Full Reddit permalink | URL |
| Post Body Preview | First 300 chars of post body | Truncate cleanly |
| Author | "u/username" | From Reddit data |
| Subreddit/Account | "r/astrology" | Include r/ prefix |
| Engagement Score | Upvote count | Number |
| Comment Count | From Reddit data | Number |
| Keyword Match | Which seed keyword matched | Text |
| Relevance Score | Your 1-10 composite score | Number |
| Found Date | Today's date (YYYY-MM-DD) | Date |
| Status | "Drafted" | Single select |

```bash
QUEUE_RESPONSE=$(curl -s --retry 3 --retry-delay 2 -X POST \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_QUEUE_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  --data-raw '{"typecast": true, "records": [{"fields": { ... }}]}')

QUEUE_RECORD_ID=$(echo "$QUEUE_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['records'][0]['id'])")
```

**6b. Create a Social Mining Drafts record (the response + evidence):**

| Field | Value | Notes |
|-------|-------|-------|
| Queue Record ID | Record ID from 6a | Links draft to its source post |
| Original Post Title | Post Title from the Queue record | Human-readable thread title |
| Original Post URL | Post URL from the Queue record | Direct link to the original thread |
| Platform | "Reddit" | Single select |
| Draft Response | Full draft text from Step 5 | The actual reply to post |
| Astrology Data Used | Brief data summary (e.g., "Venus 5.54° Tau sq Pluto 5.27° Aqu, orb 0.27°") | Quick reference |
| Data Reasoning | Full evidence chain (see below) | **The audit trail** |
| Is Follow-Up | false | This is an initial response |
| Thread Depth | 1 | First response in thread |
| Contains CTA | false | No links or self-promotion |
| Status | "Ready" | Ready for human to post |

**The "Data Reasoning" field — this is critical.** It must contain a complete, readable evidence chain that anyone can follow:

```
SOURCE: [Tool/library/API that produced the data]
Example: "kerykeion v5.10.1 + ephem v4.2.1 (Python astronomical libraries using Swiss Ephemeris)"
Example: "USDA Plant Hardiness Zone Map (planthardiness.ars.usda.gov)"
Example: "King Arthur Baking ratio guide (kingarthurbaking.com/learn/resources)"
Example: "AAD Acne Treatment Guidelines (aad.org/public/diseases/acne)"

RAW DATA: [The exact values pulled from the source]
Example: "Venus 5.54° Taurus, Pluto 5.27° Aquarius. Square aspect, orb 0.27° separating."
Example: "Azaleas require soil pH 4.5-6.0. Iron chlorosis occurs above pH 6.5."
Example: "Standard butter-to-flour ratio for pie crust: 2:3 by weight."

WHY THIS DATA: [Why this specific data was chosen for this specific post]
Example: "Poster asks about attraction to older partners — Venus-Pluto is the textbook
attraction/obsession aspect. Current transit is nearly exact, directly amplifying their pattern."
Example: "Poster's azaleas are yellowing between veins — classic iron chlorosis symptom.
They mentioned clay soil which tends alkaline, preventing iron uptake."

VERIFICATION: [How someone could independently check this]
Example: "Cross-reference astro.com ephemeris for April 4, 2026."
Example: "Compare USDA soil pH maps for poster's stated location (Zone 7b, Georgia)."
Example: "King Arthur guide: kingarthurbaking.com/learn/resources/ingredient-weight-chart"
```

This field is not optional. Every draft must have it. The standard applies regardless of niche.

```bash
curl -s --retry 3 --retry-delay 2 -X POST \
  "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_MINING_DRAFTS_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  --data-raw '{"typecast": true, "records": [{"fields": { ... }}]}'
```

Repeat Steps 6a-6b for each qualifying post (3-5 total).

---

### Step 7: Update observations.md

Append a structured summary so the next run can learn from this one:

```
## YYYY-MM-DD HH:MM — Social Miner

**Skill:** social-miner | **Status:** SUCCESS
**Keywords used:** [keyword1], [keyword2], [keyword3]
**Subreddits scanned:** r/astrology, r/AskAstrologers, r/zodiacsigns
**ScrapeCreators credits used:** ~N calls (N remaining)
**Raw candidates found:** N
**Posts queued (with drafts):** N
1. [Post Title] — r/subreddit, Score: N, Comments: N, Keyword: [match]
2. ...
**Data sources used:** [kerykeion/ephem for planetary positions, etc.]
**Notable pattern:** [Any interesting trend — e.g., "3 of 4 posts were about Venus-Pluto themes"]
```

---

### Step 8: Telegram Alert & SKILL_RESULT

**On success:**
```bash
bash /home/agent/project/telegram-alert.sh "✅ social-miner — Queued N posts with drafts from r/sub1, r/sub2. N credits remaining."
```

**On failure:**
```bash
bash /home/agent/project/telegram-alert.sh "❌ social-miner — [error details]"
```

**On skip (no qualifying posts):**
```bash
bash /home/agent/project/telegram-alert.sh "⚠️ social-miner — No qualifying posts found across N subreddits"
```

**Final line of output (required by dispatcher):**
```
SKILL_RESULT: success | Social miner queued N posts with N drafts from N subreddits | N/A
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| ScrapeCreators API down or out of credits | Fall back to Reddit .json API (append `.json` to subreddit URLs, e.g., `https://www.reddit.com/r/astrology/hot.json`). Free, ~60 req/min. Use Python `requests` with `User-Agent: JonOpsAgent/1.0` header. |
| ScrapeCreators returns 401 via curl | Use Python `requests` instead (known container issue). |
| Niche data hook fails (API down) | Use local libraries only (kerykeion/ephem for astrology). If ALL data sources fail, SKIP the run — never draft without real data. |
| Zero qualifying posts found | SKILL_RESULT: skip — this is normal on slow days. |
| Airtable write fails | SKILL_RESULT: fail — check API key and table IDs. |

---

## Rules (Non-Negotiable)

1. **NEVER draft a response without real, verifiable data.** If data sources are down, skip the run.
2. **NEVER include links** to our website or any website in draft responses.
3. **NEVER include self-promotional language** or business identity.
4. **NEVER respond to posts about** mental health crises, medical emergencies, or suicide.
5. **NEVER respond to locked or archived posts.**
6. **NEVER queue duplicate posts** — always run the dedup check in Step 1.
7. **ALWAYS populate the Data Reasoning field** with source, raw data, reasoning, and verification method.
8. **ALWAYS use Python `requests`** for ScrapeCreators API calls (not curl).
9. Aim for 3-5 posts per run. 2 is acceptable if quality is low.
10. Budget ~5-6 ScrapeCreators API calls per run.
11. All responses must read like a helpful community member, not a brand.
12. Keep responses to 3-6 sentences — Reddit penalizes walls of text.
13. Prefer posts < 12 hours old for maximum visibility.

---

## Niche Adaptation Guide

This skill is designed to work for any small business. When deploying on a different project, these variables change:

| Variable | Where Configured | Astrology Example | Landscaping Example | Bakery Example |
|----------|-----------------|-------------------|--------------------|-|
| Seed keywords | CLAUDE.md → "Niche Keywords" | mercury retrograde, birth chart | lawn care tips, tree pruning | sourdough starter, cake recipe |
| Target subreddits | CLAUDE.md → "Social Mining Config" | r/astrology, r/AskAstrologers | r/landscaping, r/gardening | r/Baking, r/Breadit |
| Data hook | CLAUDE.md → data hook config | kerykeion + ephem | USDA zones, extension services | Established recipe ratios |
| Liability level | CLAUDE.md | Low | Low | Low |
| Response tone | CLAUDE.md → "Brand Voice" | Warm, mystical, accessible | Practical, helpful, experienced | Friendly, enthusiastic, precise |
| human_review_required | CLAUDE.md | false (except CTAs) | false (except CTAs) | false (except CTAs) |

**High-liability niches** (legal, medical, financial): Set `human_review_required: true` for ALL drafts, not just CTAs. Add appropriate disclaimers. The Data Reasoning field becomes even more critical.

---

## Airtable Field Reference

**Social Mining Queue table:**
| Field | Type | Description |
|-------|------|-------------|
| Post Title | singleLineText | Title of the Reddit post (primary field) |
| Platform | singleSelect | "Reddit" (or "Instagram" in future) |
| Post URL | url | Full permalink to the post |
| Post Body Preview | multilineText | First 300 chars of the post body |
| Author | singleLineText | Reddit username (u/name) |
| Subreddit/Account | singleLineText | Subreddit with r/ prefix |
| Engagement Score | number | Upvote count at time of discovery |
| Comment Count | number | Comment count at time of discovery |
| Keyword Match | singleLineText | Which seed keyword matched this post |
| Relevance Score | number | Composite score 1-10 |
| Found Date | date | Date discovered (YYYY-MM-DD) |
| Status | singleSelect | New → Drafted → Posted → Expired |
| Notes | multilineText | Free-form notes |

**Social Mining Drafts table:**
| Field | Type | Description |
|-------|------|-------------|
| Queue Record ID | singleLineText | Links to parent Queue record |
| Original Post Title | singleLineText | Thread title from Queue (human-readable) |
| Original Post URL | url | Thread URL from Queue (click to see original post) |
| Platform | singleSelect | "Reddit" |
| Draft Response | multilineText | The actual reply text |
| Astrology Data Used | multilineText | Brief data summary (positions, aspects) |
| Data Reasoning | multilineText | **Full evidence chain: source, raw data, reasoning, verification** |
| Is Follow-Up | checkbox | false for initial responses |
| Parent Comment URL | url | Empty for initial responses |
| Thread Depth | number | 1 for initial responses |
| Contains CTA | checkbox | false (no links in initial responses) |
| Status | singleSelect | Ready → Posted / Draft (needs review) / Skipped / Expired |
| Posted Date | date | Filled when human posts it |
| Posted By | singleSelect | Who posted (Operator, VA, Agent) |
| Response Permalink | url | Filled after posting — the URL of our comment |
| Log Record ID | singleLineText | Filled by social-engager after posting |
| Notes | multilineText | Free-form notes |
