---
skill: social-researcher
version: 1.0.0
cadence: twice-weekly (Thursday + Sunday)
trigger: cron
source: multi-source sweep (Reddit, TikTok, Pinterest, Competitor IG, Wikipedia, Google News, People Also Ask)
airtable_reads: [Social Queue, Social Posts Log]
airtable_writes: [Social Queue]
external_apis: [scrapecreators, wikipedia, web-search]
active: true
notes: "Feeds Social Queue for SP2. Runs multi-source sweep, scores topics, pushes top 5 briefs."
---

# Social Researcher — Multi-Source Topic Discovery Skill

## What This Skill Does (Plain English)
This skill sweeps 7 different sources — Reddit, TikTok, Pinterest, competitor Instagram, Wikipedia "On This Day," Google News, and People Also Ask — to discover trending topics relevant to the niche. It scores and ranks all findings, then queues the top 5 topics as ready-to-use briefs in Airtable. Social Poster 2 later picks up these briefs and turns them into scheduled social media posts.

---

## Purpose
Discover 5 high-potential social media content topics by sweeping 7 different sources. Score, rank, and push the best topics as briefs to the Social Queue in Airtable. Social Poster 2 consumes these briefs to create and schedule posts.

This skill is designed to be **niche-agnostic** — it reads the project's niche keywords, competitors, and audience from CLAUDE.md and adapts accordingly.

## Prerequisites
- SCRAPECREATORS_API_KEY in env
- AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_SOCIAL_QUEUE_TABLE in env
- AIRTABLE_SOCIAL_POSTS_LOG_TABLE in env (for dedup check)
- Active platforms + niche keywords + competitor list defined in CLAUDE.md

## Process

### Step 0: Load context
Read CLAUDE.md to extract:
- **Niche seed keywords** (listed under "Niche Keywords" section)
- **Competitor list** (listed under "Competitor List" section)
- **Target audience** (demographics, interests)
- **Brand voice** (tone, style constraints)
- **Active social platforms** (which platforms we post to)

Pick 2-3 seed keywords to use as search terms across sources. Rotate which keywords you use each run — don't always pick the same ones.

Read **observations.md** (tail ~50 lines) for recent astronomical or niche events that might inform topic selection.

Read the latest **Market Intelligence** record for trending topics and competitor activity:
```bash
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_MARKET_INTEL_TABLE}?sort%5B0%5D%5Bfield%5D=Month&sort%5B0%5D%5Bdirection%5D=desc&maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Use **Key Trends** and **Competitor Moves** to identify timely social topics. Topics aligned with current trends score higher.

### Step 1: Dedup check
Query Airtable Social Posts Log for posts from the last 14 days:
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_POSTS_LOG_TABLE}?filterByFormula=IS_AFTER({Date},'$(date -d '14 days ago' +%Y-%m-%d)')&fields[]=Topic&fields[]=Caption Preview" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Also check Social Queue for currently Queued topics:
```bash
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_QUEUE_TABLE}?filterByFormula=Status='Queued'" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Build a mental "already covered" list. Do NOT queue topics that overlap with recent posts or existing queue items.

### Step 2: Sweep all 7 sources

Run all sources. For each, extract the **top 2-3 most interesting results**. Not everything will be relevant — that's fine. Cast a wide net, filter later.

---

#### Source 1: Reddit (ScrapeCreators)
Search relevant subreddits for hot/trending posts.
```bash
# Search across Reddit for niche topics
curl -s --retry 3 --retry-delay 2 "https://api.scrapecreators.com/v1/reddit/search?query=KEYWORD&sort=relevance&time=week" \
  -H "x-api-key: ${SCRAPECREATORS_API_KEY}"

# Or pull hot posts from a specific subreddit (NOTE: param is "subreddit", NOT "name")
curl -s --retry 3 --retry-delay 2 "https://api.scrapecreators.com/v1/reddit/subreddit?subreddit=SUBREDDIT_NAME&sort=hot&limit=10" \
  -H "x-api-key: ${SCRAPECREATORS_API_KEY}"
```
**What to look for:** Questions with lots of upvotes/comments = proven audience interest. Debates, "what do you think about X" posts, personal stories that resonate.

**Subreddit selection:** Use your niche knowledge to pick 2-3 relevant subreddits. For astrology that might be r/astrology, r/zodiac. For a bakery it might be r/baking, r/foodporn. For accounting: r/accounting, r/smallbusiness.

---

#### Source 2: TikTok Trending + Keyword Search (ScrapeCreators)
```bash
# Get trending feed
curl -s --retry 3 --retry-delay 2 "https://api.scrapecreators.com/v1/tiktok/get-trending-feed" \
  -H "x-api-key: ${SCRAPECREATORS_API_KEY}"

# Search by niche keyword (NOTE: param is "query", NOT "keyword")
curl -s --retry 3 --retry-delay 2 "https://api.scrapecreators.com/v1/tiktok/search/keyword?query=KEYWORD&limit=10" \
  -H "x-api-key: ${SCRAPECREATORS_API_KEY}"

# Check popular hashtags
curl -s --retry 3 --retry-delay 2 "https://api.scrapecreators.com/v1/tiktok/hashtags/popular" \
  -H "x-api-key: ${SCRAPECREATORS_API_KEY}"
```
**What to look for:** Videos with high view counts in the niche. Trending sounds/formats that could be adapted. Hashtags gaining momentum.

---

#### Source 3: Pinterest Search (ScrapeCreators)
```bash
curl -s --retry 3 --retry-delay 2 "https://api.scrapecreators.com/v1/pinterest/search?query=KEYWORD&limit=10" \
  -H "x-api-key: ${SCRAPECREATORS_API_KEY}"
```
**What to look for:** Pins with high save counts = proven evergreen interest. Visual trends. "How to" and "Guide" formats that perform well on Pinterest.

---

#### Source 4: Competitor Instagram (ScrapeCreators)
```bash
# Pull recent posts from a competitor's IG (NOTE: param is "handle", NOT "username")
curl -s --retry 3 --retry-delay 2 "https://api.scrapecreators.com/v2/instagram/user/posts?handle=COMPETITOR_HANDLE&limit=10" \
  -H "x-api-key: ${SCRAPECREATORS_API_KEY}"
```
**What to look for:** Their most-liked/commented recent posts. Topics they're covering that we haven't. Engagement patterns — what's working for them?

Pick 1-2 competitor IG handles from the competitor list in CLAUDE.md. If IG handles aren't listed, skip this source gracefully.

---

#### Source 5: Wikipedia "On This Day" (Free — no API key)
```bash
MONTH=$(date +%-m)
DAY=$(date +%-d)
curl -s "https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/${MONTH}/${DAY}" \
  -H "User-Agent: JonOpsAgent/1.0"
```
**What to look for:** Historical events, births, or milestones that connect to the niche. Be creative with the connection — for astrology: "On this day in 1930, Pluto was discovered." For a bakery: "On this day in 1853, the first commercial bread-slicing machine was patented." For accounting: "On this day, the IRS was founded."

Only use entries where the niche connection is genuine and interesting — don't force it.

---

#### Source 6: Google News (Free — web search)
Use web search to find recent news in the niche:
```
Search: "[niche keyword] news this week"
Search: "[niche keyword] trending 2026"
```
**What to look for:** Breaking news, new studies, celebrity mentions, seasonal events, industry changes. Timely content that people are searching for RIGHT NOW.

---

#### Source 7: People Also Ask (Free — web search)
Use web search with niche keywords and look for "People Also Ask" questions:
```
Search: "[niche keyword]"
Search: "what is [niche topic]"
Search: "how to [niche activity]"
```
**What to look for:** Questions that Google surfaces in PAA boxes = proven search demand. These make excellent educational/explainer social posts. Look for questions you can answer in a compelling, visual way.

---

### Step 3: Score and rank all findings

From all 7 sources, you should have ~15-20 raw topic candidates. Now score each one on these criteria:

| Criteria | Weight | How to assess |
|----------|--------|---------------|
| **Engagement signal** | High | Upvotes, views, likes, saves, comments from the source |
| **Timeliness** | High | Is this trending NOW? Time-sensitive? Seasonal? |
| **Relevance** | High | How closely does it match our niche + audience? |
| **Novelty** | Medium | Have we covered this recently? (check dedup list from Step 1) |
| **Platform fit** | Medium | Does this work well as a social post? Is it visual? Shareable? |
| **Uniqueness** | Medium | Can we add our own angle, or would we just be copying? |

Assign each topic a score from 1-10. Be ruthless — only the best 5 make the cut.

**Aim for diversity in the final 5:**
- At least 1 timely/trending topic
- At least 1 evergreen/educational topic
- At least 1 engagement/question-based topic
- Mix of sources (don't pull all 5 from Reddit)

### Step 4: Write briefs for top 5

For each of the top 5 topics, write a brief that Social Poster 2 can turn into a post:

**Brief format:**
```
TOPIC: [Clear, specific topic headline — not vague]
ANGLE: [The unique spin or hook — what makes OUR take different]
KEY POINTS:
- [Point 1 — the most important thing to communicate]
- [Point 2 — supporting detail or stat]
- [Point 3 — practical takeaway or call to action]
SOURCE CONTEXT: [Where this came from and why it's hot right now — 1 sentence]
PLATFORM FIT: [Which platforms this works best on and why]
SUGGESTED FORMAT: [Carousel? Single image? Quote graphic? Video idea? Poll/question?]
```

Keep briefs **concise but specific** — 100-150 words max per brief. SP2 needs enough to write from but doesn't need an essay.

### Step 5: Push to Airtable Social Queue

For each of the 5 briefs, create a record:
```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_SOCIAL_QUEUE_TABLE}" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" \
  -H "Content-Type: application/json" \
  --data-raw '{
    "typecast": true,
    "records": [{
      "fields": {
        "Topic": "TOPIC HEADLINE",
        "Research Brief": "FULL BRIEF TEXT (angle + key points + format suggestion)",
        "Platform Fit": ["FB-IG", "Pinterest"],
        "Status": "Queued",
        "Priority": 8,
        "Source": "Reddit",
        "Source URL": "https://reddit.com/r/...",
        "Date Added": "'"$(date +%Y-%m-%d)"'"
      }
    }]
  }'
```

**Important:**
- Always include `"typecast": true` (allows creating new select options if needed)
- Platform Fit values must match exactly: `FB-IG`, `Twitter`, `Pinterest`
- Source values must match exactly: `Reddit`, `TikTok`, `Pinterest`, `Wikipedia`, `Google News`, `Competitor IG`, `People Also Ask`
- Priority: 1-10 scale (10 = most urgent/timely, 5 = solid evergreen, 1 = filler)
- Source URL: the original Reddit post, TikTok, article, etc. Use null if no direct URL (e.g. PAA)

### Step 6: Update observations.md
Append a summary:
```
## YYYY-MM-DD HH:MM — Social Researcher

**Sources swept:** Reddit (r/X, r/Y), TikTok (keyword: Z), Pinterest (keyword: Z), Competitor IG (@handle), Wikipedia On This Day, Google News, PAA
**Raw candidates found:** N
**Topics queued:** 5
1. [Topic] — Source: [source], Priority: [N], Platforms: [list]
2. ...
**ScrapeCreators credits used:** ~N calls
**Notable trend:** [Any interesting pattern or spike worth noting]
```

### Step 7: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ social-researcher — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ social-researcher — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ social-researcher — [skip reason]"`

```
SKILL_RESULT: success | Social researcher queued 5 topics from 7 sources (Reddit, TikTok, Pinterest, Competitor IG, Wikipedia, Google News, PAA) | N/A
```

## Error Handling
- ScrapeCreators API down or out of credits → skip that source, continue with others. Log warning.
- Wikipedia API down → skip, continue. It's supplementary.
- All ScrapeCreators sources fail → fall back to free sources only (Wikipedia + Google News + PAA). Still queue at least 3 topics.
- Zero relevant topics found across all sources → SKILL_RESULT: skip | No relevant topics found across 7 sources
- Airtable write fails → SKILL_RESULT: fail | Airtable write error — check API key

## Rules
- NEVER invent topics from thin air — every topic must trace back to a real source signal
- NEVER queue duplicate topics (always check dedup in Step 1)
- Always include Source URL so briefs have provenance
- Aim for 5 topics but 3 is acceptable if quality is low
- Respect ScrapeCreators credits — don't make unnecessary calls. ~10-12 API calls per run is the target.
- Keep briefs actionable — SP2 should be able to write a post from the brief alone
- Prioritize timely topics over evergreen when both score equally
- Source diversity matters — spread across sources, don't over-index on one

## Niche Adaptation Notes
This skill reads niche context from CLAUDE.md. When deployed on a different project:
- Seed keywords come from "Niche Keywords" section
- Competitors come from "Competitor List" section
- Subreddits and IG handles must be inferred from the niche or listed in CLAUDE.md
- Wikipedia "On This Day" connections require creative niche-linking — skip if nothing fits
- The scoring criteria stay the same regardless of niche
