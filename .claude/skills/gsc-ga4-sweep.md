---
skill: gsc-ga4-sweep
version: 1.0.0
cadence: weekly (Monday 04:00)
trigger: cron
airtable_reads: [GSC Opportunities, GA4 Insights, Published Posts]
airtable_writes: [GSC Opportunities, GA4 Insights]
external_apis: [google_oauth, google_search_console, google_analytics_data, google_analytics_admin, wp_rankmath]
active: false
notes: "Weekly GSC + GA4 sweep. Identifies meta-title quick wins, content-refresh candidates, brand-defense gaps, traffic-source patterns. May auto-apply Rank Math meta rewrites when confidence >= 0.85. New skill class — leave active:false until first-business walkthrough per educate-before-activate."
---

# GSC + GA4 Sweep Skill

## What This Skill Does (Plain English)
Every Monday at 04:00, this skill pulls the brand's last-30-day Search Console and Google Analytics 4 data, identifies meta-title rewrite opportunities (high-impression / low-CTR queries), content-refresh candidates (pages losing rank or hostage on page 2), brand-defense gaps (brand-name queries where the site isn't top 3), and conversion-driving traffic sources. It writes findings to two Airtable tables for Jon to review and may auto-apply high-confidence meta rewrites via the Rank Math endpoint — with a snapshot saved to disk for one-shot rollback.

**Examples:**
- **TaiwanMerch:** detects "taiwan swag" at 273 impressions / 0.37% CTR / position 7.4 — homepage. (Already fixed manually 2026-05-09; skill must skip when an Auto-Applied row for the same page exists in the last 14 days.)
- **OrganicAromas:** flags "best nebulizing diffuser" at 9,545 impressions / 0.03% CTR / position 9.0 — homepage. Massive meta-rewrite opportunity surfaced by the test sweep.
- **CustomCreative:** when GSC plumbing is wired (currently NOT — see Failure Modes), would surface page-2 hostage queries with >100 impressions / <5 clicks for the content-refresh queue.

---

## Purpose
Close the SEO measurement-feedback loop. Every brand on JonOps has GSC + GA4 wired through the same `GOOGLE_REFRESH_TOKEN`. Until this skill, that data sat unread. The canonical pitch's "search traffic growth" claim needs evidence. This skill mints it weekly.

Jon's verbatim ask (2026-05-09): *"implement a gsc/ga4 sweep weekly and fix the problem!"*

## Prerequisites
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` in env (Jon's SOP wires these on every brand at setup time).
- `WP_URL`, `WP_USERNAME`, `WP_PASSWORD` in env (for Rank Math auto-apply).
- `SITE_URL` in env (canonical brand URL with trailing slash, e.g. `https://taiwanmerch.co/`). Falls back to `WP_URL` with a trailing slash appended if absent.
- `BRAND_NAME` in env (or read from CLAUDE.md front-matter `project:` and the H1 — Step 0 below).
- `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID` in env.
- `AIRTABLE_GSC_OPPORTUNITIES_TABLE`, `AIRTABLE_GA4_INSIGHTS_TABLE` in env (added to the standard 19 tables; a fresh container will have them after re-running `scripts/setup/create-airtable-tables.py`).
- Optional: `GA4_PROPERTY_ID` in env. If absent, the skill enumerates and matches by domain.

## Process

### Step 0: Resolve identity (BRAND_NAME, BRAND_SLUG, SITE_URL)

If env vars not present, parse from CLAUDE.md:
- `BRAND_NAME` → first H1 in `/home/agent/project/CLAUDE.md` (e.g. `# CLAUDE.md — Taiwan Merch Agent` → "Taiwan Merch")
- `BRAND_SLUG` → front-matter `project:` field
- `SITE_URL` → front-matter `url:` field; ensure trailing slash

### Step 1: Mint a fresh access token
```bash
ACCESS_TOKEN=$(curl -sf -X POST "https://oauth2.googleapis.com/token" \
  -d "client_id=$GOOGLE_CLIENT_ID" \
  -d "client_secret=$GOOGLE_CLIENT_SECRET" \
  -d "refresh_token=$GOOGLE_REFRESH_TOKEN" \
  -d "grant_type=refresh_token" | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
```
If this fails (HTTP 4xx, empty body) — the OAuth pairing is broken. `SKILL_RESULT: fail | OAuth refresh failed.` Do NOT retry — auth errors are not transient. Per `feedback_verify_api_failures`, before declaring expiration, verify by curl'ing a known-good endpoint with the same creds.

### Step 2: Resolve the GSC property
```bash
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "https://searchconsole.googleapis.com/webmasters/v3/sites"
```
- Pick the `siteEntry` whose `siteUrl` matches `SITE_URL` exactly (with trailing slash).
- If no exact match, prefer `https://` URL-prefix property over `http://` and over `sc-domain:`.
- If `siteEntry` is empty: skill exits cleanly. `SKILL_RESULT: skip | No GSC properties verified under this OAuth token.` Per `reference_google_oauth_scope`, the brand's GSC may be under a different Google account.

### Step 3: GSC pulls (3 queries, current 30d vs prior 30d)

```bash
END=$(date +%Y-%m-%d)
START=$(date -d "-30 days" +%Y-%m-%d)
PRIOR_END=$(date -d "-31 days" +%Y-%m-%d)
PRIOR_START=$(date -d "-60 days" +%Y-%m-%d)
ENC=$(GSC_PROPERTY="$GSC_PROPERTY" python3 -c "import urllib.parse,os;print(urllib.parse.quote(os.environ['GSC_PROPERTY'],safe=''))")
ENDPOINT="https://searchconsole.googleapis.com/webmasters/v3/sites/$ENC/searchAnalytics/query"
```

**Pull A** — current 30d page+query (rowLimit 200):
```bash
curl -s -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" "$ENDPOINT" \
  -d "{\"startDate\":\"$START\",\"endDate\":\"$END\",\"dimensions\":[\"page\",\"query\"],\"rowLimit\":200}"
```
**Pull B** — current 30d page-only (for trend baseline):
```bash
curl -s -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" "$ENDPOINT" \
  -d "{\"startDate\":\"$START\",\"endDate\":\"$END\",\"dimensions\":[\"page\"],\"rowLimit\":200}"
```
**Pull C** — prior 30d page-only (for delta):
```bash
curl -s -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" "$ENDPOINT" \
  -d "{\"startDate\":\"$PRIOR_START\",\"endDate\":\"$PRIOR_END\",\"dimensions\":[\"page\"],\"rowLimit\":200}"
```
Cache results in memory; don't re-call.

Retry rule (`feedback_wp_rest_retry`): on HTTP 000 or 5xx, retry once after 180s. 4xx is never retried.

### Step 4: Identify candidates

**4a. CTR-Rewrite (meta-title quick wins):**
From Pull A, filter rows where:
- `impressions > 50`
- `ctr < 0.015` (1.5%)
- `5 <= position <= 15`

Group by `page`. For each page, keep top 1–2 queries by impressions (cap at 2). Drop pages where the top query is a brand-name query (those go to brand-defense).

**4b. Content-Refresh:**
Two sub-flavors:
- *Rank-drop:* page in Pull B AND Pull C, current `position > prior + 3.0`, AND prior `position <= 20`. (Don't flag pages that were never ranking.)
- *Page-2 hostage:* page in Pull B with `11 <= position <= 20`, `impressions > 100`, `clicks < 5`.

Surface one row per page (if both signals fire → `Type=Content-Refresh`, `Notes` lists both).

**4c. Brand-Defense:**
Brand-name queries are tokens that contain the brand's slug or its space-tokenized variants ("taiwan merch", "organic aromas", etc. — read from CLAUDE.md `BRAND_NAME` and niche-keywords).
For each brand-name query in Pull A, if site `position > 3`: flag as `Type=Brand-Defense`. If site doesn't appear at all in Pull A for that query: stronger flag — `Notes: site not in top 200 GSC results`.

### Step 5: De-dup vs already-actioned (idempotency + `feedback_no_keyword_stuffing`)

Read existing `GSC Opportunities` rows for this brand from the last 14 days (covers same-week re-runs and the 7-day "just done" window):
```bash
FILTER="AND({Brand}=\"$BRAND_NAME\",IS_AFTER({Date},DATEADD(TODAY(),-14,'days')))"
ENC_FILTER=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$FILTER")
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_GSC_OPPORTUNITIES_TABLE}?filterByFormula=$ENC_FILTER&pageSize=100" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}"
```
Drop a candidate if there's an existing row in the last 14 days matching:
- Same `Page URL` + same `Target Query` (exact), OR
- Same `Page URL` + `Status=Auto-Applied` (don't re-propose anything we just changed), OR
- Same `Page URL` + `Status=Pending Review` AND row age < 7 days (Jon hasn't reviewed yet — don't pile on).

**Same-run dedup:** within Step 4 candidates, never propose two near-duplicate queries on the same page. Lexical near-dupes (e.g. `taiwan swag` + `taiwanese swag` + `swag taiwan`) collapse — keep the highest-impression one, drop the rest. Honors `feedback_no_keyword_stuffing`.

### Step 6: Generate suggested titles + descriptions (CTR-Rewrite only)

For each remaining CTR-Rewrite candidate:
1. Fetch the live page HTML once: `curl -sL "$PAGE_URL"` (with WP REST retry rule — 1 retry after 3 min on 5xx/000).
2. Extract current `<title>` and `<meta name="description" content="...">`.
3. Generate suggested title:
   - Start with the target query verbatim or near-verbatim.
   - Brand suffix at the end (` — {BRAND_NAME}` or ` | {BRAND_NAME}`).
   - <= 60 characters.
4. Generate suggested description:
   - Lead with the target query within the first 8 words.
   - Include 1–2 secondary supporting terms from sibling queries on the same page.
   - Mention 1 product / proof point if Brand has products (read from CLAUDE.md).
   - <= 155 characters.

For Content-Refresh and Brand-Defense, leave `Suggested Title` and `Suggested Description` blank — those need Jon's eyes and a full content rewrite, not a meta tweak.

### Step 7: Compute confidence score (CTR-Rewrite only)

```
confidence = 0.50
+ 0.15  if impressions >= 100
+ 0.10  if 5 <= position <= 12
+ 0.10  if ctr < 0.01
+ 0.10  if exact-match query token sits cleanly inside a natural English title (no awkward stuffing)
- 0.20  if page is the homepage AND another homepage rewrite was Auto-Applied within last 14 days
- 0.20  if suggested title > 60 chars or suggested description > 155 chars after generation
```
Cap at 1.0, floor at 0.0.

`Auto-Apply gate: confidence >= 0.85`. The `Confidence` field is written to the Airtable row (Number, precision 2) so Jon can audit the threshold logic post-hoc.

### Step 8: Write rows to Airtable

For each candidate, batch POST to `GSC Opportunities` (groups of 10). Schema in Step 12.

Idempotent re-runs in same day: query for an exact match on `Brand + Page URL + Target Query + Date` first; if exists, PATCH (don't POST a duplicate).

### Step 9: Auto-Apply gate (CTR-Rewrite, confidence >= 0.85, NOT first run)

This step is **disabled on the first scheduled run for any brand** — set a one-shot guard file the first time the skill writes any rows for a brand:
```bash
GUARD="/home/agent/project/.claude/data/gsc-sweep/.first-run-${BRAND_SLUG}"
if [ ! -f "$GUARD" ]; then
  mkdir -p "$(dirname "$GUARD")"
  touch "$GUARD"
  echo "First run for $BRAND_NAME — skipping auto-apply step. All rows stay Pending Review."
  # jump to Step 10
fi
```
Jon flips auto-apply on by simply running the skill once with all rows staged Pending Review, reviewing them, then running again. No code change required.

For each CTR-Rewrite row with `Status = Pending Review` AND `Confidence >= 0.85`:

**9a. Domain-lock paranoia:**
Verify the page URL's host matches `SITE_URL` host exactly. If not, mark `Status=Skipped`, Notes `domain mismatch`, continue. Defense against a misconfig where SITE_URL drifts from the actual GSC property.

**9b. Find the WP post ID:**
```bash
SITE_HOST=$(SITE_URL="$SITE_URL" python3 -c "from urllib.parse import urlparse;import os;print(urlparse(os.environ['SITE_URL']).netloc)")
SLUG=$(PAGE_URL="$PAGE_URL" python3 -c "from urllib.parse import urlparse;import os;print(urlparse(os.environ['PAGE_URL']).path.strip('/'))")
if [ -z "$SLUG" ]; then
  # Homepage — try pages?slug=home, then resolve by link
  POST_ID=$(curl -s -u "$WP_USERNAME:$WP_PASSWORD" "$WP_URL/wp-json/wp/v2/pages?slug=home" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d[0]['id'] if d else '')")
  [ -z "$POST_ID" ] && POST_ID=$(curl -s -u "$WP_USERNAME:$WP_PASSWORD" "$WP_URL/wp-json/wp/v2/pages?per_page=20" | SITE_URL="$SITE_URL" python3 -c "import json,sys,os;d=json.load(sys.stdin);t=os.environ['SITE_URL'].rstrip('/');print(next((p['id'] for p in d if p.get('link','').rstrip('/')==t),''))")
  OBJECT_TYPE=page
else
  LAST_SEG=$(echo "$SLUG" | awk -F/ '{print $NF}')
  POST_ID=$(curl -s -u "$WP_USERNAME:$WP_PASSWORD" "$WP_URL/wp-json/wp/v2/posts?slug=$LAST_SEG" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d[0]['id'] if d else '')")
  OBJECT_TYPE=post
  if [ -z "$POST_ID" ]; then
    POST_ID=$(curl -s -u "$WP_USERNAME:$WP_PASSWORD" "$WP_URL/wp-json/wp/v2/pages?slug=$LAST_SEG" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d[0]['id'] if d else '')")
    OBJECT_TYPE=page
  fi
fi
```
If `POST_ID` empty: mark `Status=Skipped`, `Notes: WP post lookup failed for slug "$SLUG"`, continue.

**9c. Snapshot current state:**
```bash
SNAPDIR="/home/agent/project/.claude/data/gsc-sweep/snapshots"
mkdir -p "$SNAPDIR"
SNAP="$SNAPDIR/$(date -u +%Y%m%dT%H%M%SZ)-${BRAND_SLUG}-${POST_ID}.md"
{
  echo "# Snapshot — $BRAND_NAME WP post $POST_ID ($PAGE_URL)"
  echo "date: $(date -Iseconds)"
  echo "object_type: $OBJECT_TYPE"
  echo "post_id: $POST_ID"
  echo
  echo "## Current title"
  echo "$CURRENT_TITLE"
  echo
  echo "## Current description"
  echo "$CURRENT_DESC"
  echo
  echo "## Suggested title"
  echo "$SUGGESTED_TITLE"
  echo
  echo "## Suggested description"
  echo "$SUGGESTED_DESC"
  echo
  echo "## Live HTML head excerpt (pre-change)"
  curl -sL "$PAGE_URL" | grep -iE '<title|<meta name="description"' | head -5
} > "$SNAP"
```

**9d. Apply via Rank Math:**
```bash
PAYLOAD=$(POST_ID=$POST_ID OBJECT_TYPE=$OBJECT_TYPE SUGGESTED_TITLE="$SUGGESTED_TITLE" SUGGESTED_DESC="$SUGGESTED_DESC" TARGET_QUERY="$TARGET_QUERY" python3 -c "
import json,os
print(json.dumps({
  'objectID': int(os.environ['POST_ID']),
  'objectType': os.environ['OBJECT_TYPE'],
  'meta': {
    'rank_math_title': os.environ['SUGGESTED_TITLE'],
    'rank_math_description': os.environ['SUGGESTED_DESC'],
    'rank_math_focus_keyword': os.environ['TARGET_QUERY']
  }
}))")

for i in 1 2; do
  RESP=$(curl -s -w "\n%{http_code}" -X POST "$WP_URL/wp-json/rankmath/v1/updateMeta" \
    -u "$WP_USERNAME:$WP_PASSWORD" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")
  CODE=$(echo "$RESP" | tail -1)
  case "$CODE" in
    200|201) break ;;
    000|5*) [ $i -lt 2 ] && sleep 180 ;;
    *) break ;;  # 4xx — don't retry
  esac
done

if [ "$CODE" != "200" ] && [ "$CODE" != "201" ]; then
  # PATCH the Airtable row: Status=Apply-Failed, Notes "Rank Math returned $CODE"
  continue
fi
```

**9e. Verify on live HTML:**
```bash
sleep 30
LIVE=$(curl -sL "$PAGE_URL" | grep -iE '<title' | head -1)
if echo "$LIVE" | grep -qF "$SUGGESTED_TITLE"; then
  STATUS=Auto-Applied
else
  STATUS=Apply-Failed
  # Roll back via the snapshot
  ROLLBACK_PAYLOAD=$(POST_ID=$POST_ID OBJECT_TYPE=$OBJECT_TYPE CURRENT_TITLE="$CURRENT_TITLE" CURRENT_DESC="$CURRENT_DESC" python3 -c "
import json,os
print(json.dumps({
  'objectID': int(os.environ['POST_ID']),
  'objectType': os.environ['OBJECT_TYPE'],
  'meta': {
    'rank_math_title': os.environ['CURRENT_TITLE'],
    'rank_math_description': os.environ['CURRENT_DESC']
  }
}))")
  RB=$(curl -s -w "\n%{http_code}" -X POST "$WP_URL/wp-json/rankmath/v1/updateMeta" \
    -u "$WP_USERNAME:$WP_PASSWORD" -H "Content-Type: application/json" -d "$ROLLBACK_PAYLOAD")
  RB_CODE=$(echo "$RB" | tail -1)
  [ "$RB_CODE" = "200" ] || [ "$RB_CODE" = "201" ] && STATUS=Rolled-Back
fi
```

**9f. Update Airtable row** with the resolved `Status` and `Snapshot Path`. Always PATCH the same record from Step 8 — do NOT create a new row.

### Step 10: GA4 sweep

**10a. Resolve property ID:**
- If `GA4_PROPERTY_ID` env var set, use it.
- Otherwise:
  ```bash
  curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
  ```
  Match by `displayName` containing `BRAND_NAME` OR by `propertySummaries[].displayName` matching the bare domain (e.g. `taiwanmerch.com`). Exclude properties whose displayName starts with "GA4 - " (those are demo accounts — see OrganicAromas's "Demo Account" entry).
  - 0 matches → continue without GA4. Write nothing to GA4 Insights. Notes in skill output: `GA4 property not found.`
  - >1 matches → write a single GA4 Insights row with `Source/Medium=AMBIGUOUS`, `Notes: multiple GA4 properties match brand. Set GA4_PROPERTY_ID in .env to disambiguate.` Skip the rest of GA4.

**10b. Pull report:**
```bash
PROP="${GA4_PROPERTY_ID#properties/}"
curl -s -X POST -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" \
  "https://analyticsdata.googleapis.com/v1beta/properties/$PROP:runReport" \
  -d '{
    "dateRanges":[
      {"startDate":"30daysAgo","endDate":"today","name":"current"},
      {"startDate":"60daysAgo","endDate":"31daysAgo","name":"prior"}
    ],
    "dimensions":[{"name":"sessionSourceMedium"}],
    "metrics":[{"name":"sessions"},{"name":"keyEvents"}],
    "limit":100
  }'
```

**10c. Identify patterns:**
- Top 5 sources by `sessions` (current 30d).
- All sources with `keyEvents > 0` (current 30d) — these prove the VSL "orders from X" claim.
- Trend per source: current vs prior. `Up` if >+10%, `Down` if <-10%, else `Flat`.
- Referral surfacing: sources matching `(reddit|tiktok|x\.com|twitter|pinterest|youtube|facebook|instagram)` with sessions > 0 → flag in Notes.

**10d. Write `GA4 Insights` rows** (batched, max 20). Idempotent: same `Brand + Source/Medium + Date` PATCH-replaces.

### Step 10.5: Queue Content-Refresh candidates for autonomous handoff to blog-writer

For every Content-Refresh candidate identified in Step 6 (page-2 hostage with > 100 impressions / < 5 clicks, OR average position drop > 3 ranks vs prior 30d):

1. Build the refresh brief — populate the `Refresh Brief` field on the Airtable row with:
   - Target query
   - Page URL + post ID + slug
   - Current position + impressions + clicks (last 30d)
   - Prior 30d position (if rank-drop)
   - Top 5 SERP competitors for the target query (pull via DataForSEO `serp` if available; otherwise leave blank)
   - Suggested angle: "rank-drop recovery" | "page-2 → page-1" | "expand for related queries"
2. Set `Status=Queued for Refresh`. Do NOT auto-rewrite content from this skill — that's blog-writer's job.
3. blog-writer's Step 0 (added in this same branch) checks this table at the start of every daily run and processes up to **1 refresh per day per brand** before pulling from the Content Calendar.

**Rationale:** Content rewrites are higher-blast-radius than meta rewrites. The blog-writer skill already owns post-creation discipline (voice, length, structure, link integrity, snapshotting). Routing refreshes through it preserves that discipline and avoids two skills competing for the same WP post. Quota of 1/day prevents content cadence from being dominated by refreshes.

**No Asana cards. No human-in-the-loop step.** The agent sees the page-2 hostage, queues it, blog-writer rewrites it on the next 00:00 cron tick. If blog-writer's rewrite fails verification, it rolls back and pings Telegram (the same critical-anomaly channel — see Step 11).

### Step 11: Telegram (critical/strategic channel only) + SKILL_RESULT

Telegram is **NOT** a routine sweep digest. It's reserved for items that require Jon's deeper thinking or operator action. Fire on these conditions and ONLY these:

| Condition | Telegram message |
|-----------|------------------|
| One or more Brand-Defense gaps surfaced (impressions ≥ 5, position > 3) | `🔍 [BRAND] brand-defense gap: "[query]" pos [P] imp [I] — strategic decision needed (schema/page/competitor)` |
| Auto-apply failed and rolled back | `❌ [BRAND] gsc-ga4-sweep auto-apply rolled back on [page]: [reason]` |
| Skill skipped due to missing creds, missing GSC property, or env mismatch | `⚠️ [BRAND] gsc-ga4-sweep skipped: [reason] — env or OAuth fix needed` |
| Critical exception (>500 lines stack trace, repeated 5xx, etc.) | `🚨 [BRAND] gsc-ga4-sweep crashed: [first-line]` |

Do NOT fire Telegram on:
- Routine successful sweeps with auto-applied CTR-rewrites and queued Content-Refresh items.
- Empty result sets (no opportunities surfaced — that's a healthy site).
- Pending-Review CTR-Rewrite candidates (those live in Airtable for the operator to scan at their own cadence).

```bash
# example invocation, only if a triggering condition above is met
bash /home/agent/project/telegram-alert.sh "<one-line message per the table above>"
```

```
SKILL_RESULT: success | [N] CTR-Rewrite, [M] Content-Refresh queued, [K] Brand-Defense, [P] GA4 rows, [A] auto-applied | top: [target_query_1], [target_query_2]
```

### Step 12: Airtable schema bootstrap

If either `AIRTABLE_GSC_OPPORTUNITIES_TABLE` or `AIRTABLE_GA4_INSIGHTS_TABLE` is unset OR Airtable returns 404 NOT_FOUND on probe, the skill emits:

```
SKILL_RESULT: skip | GSC Opportunities or GA4 Insights table missing — re-run scripts/setup/create-airtable-tables.py on this brand's base, then add AIRTABLE_GSC_OPPORTUNITIES_TABLE / AIRTABLE_GA4_INSIGHTS_TABLE to .env.
```

It does NOT auto-create tables — the canonical source of truth for table schemas is `scripts/setup/create-airtable-tables.py`.

---

## Auto-Apply Confidence Gate (one-line summary)

| Condition | Effect |
|-----------|--------|
| confidence >= 0.85 AND first-run guard passed | Auto-apply via Rank Math `/updateMeta` |
| confidence < 0.85 | Stage as `Pending Review`, surface in Telegram alert |
| Type != CTR-Rewrite | NEVER auto-apply, regardless of confidence |
| Page URL host != SITE_URL host | Skip (domain-lock) |
| Same page already auto-applied within 14d | Skip (avoid yo-yo rewrites) |
| First-ever scheduled run for the brand | Skip auto-apply on this run only (one-shot guard) |

## Rank Math endpoint payload (canonical)

```json
{
  "objectID": 1234,
  "objectType": "post",
  "meta": {
    "rank_math_title": "Target Query — Brand Tagline",
    "rank_math_description": "Target query lead. Two supporting terms. Brand proof point. CTA.",
    "rank_math_focus_keyword": "target query"
  }
}
```
Endpoint: `POST $WP_URL/wp-json/rankmath/v1/updateMeta` with WP basic auth.

## Snapshot path (canonical)

`/home/agent/project/.claude/data/gsc-sweep/snapshots/{ISO_TIMESTAMP_UTC}-{BRAND_SLUG}-{POST_ID}.md`

To roll back manually: `cat $SNAP`, then re-issue `/updateMeta` with the `Current title` / `Current description` blocks.

## Airtable Table Schemas

### GSC Opportunities
| Field | Type | Notes |
|-------|------|-------|
| Date | date (ISO) | day of run |
| Brand | singleLineText | from `BRAND_NAME` |
| Type | singleSelect | `CTR-Rewrite`, `Content-Refresh`, `Brand-Defense` |
| Page URL | url | canonical form with trailing slash |
| Target Query | singleLineText | the GSC query to target |
| Current Title | singleLineText | scraped from live HTML, CTR-Rewrite only |
| Current Description | multilineText | CTR-Rewrite only |
| Current CTR | number (4) | as decimal (0.0037) |
| Current Position | number (1) | average GSC position |
| Impressions | number (0) | last 30d |
| Suggested Action | multilineText | what to do, free-form |
| Suggested Title | singleLineText | CTR-Rewrite only |
| Suggested Description | multilineText | CTR-Rewrite only |
| Confidence | number (2) | 0.0–1.0 |
| Status | singleSelect | `Pending Review`, `Auto-Applied`, `Skipped`, `Apply-Failed`, `Rolled-Back` |
| Notes | multilineText | tagged signals (rank-drop, page-2-hostage, etc.) |
| Snapshot Path | singleLineText | absolute container path; only set after auto-apply |

### GA4 Insights
| Field | Type | Notes |
|-------|------|-------|
| Date | date (ISO) | day of run |
| Brand | singleLineText | |
| Source/Medium | singleLineText | from `sessionSourceMedium` |
| Sessions | number (0) | last 30d |
| Sessions Prior 30d | number (0) | for trend |
| Conversions | number (0) | `keyEvents` last 30d |
| Conversions Prior 30d | number (0) | |
| Trend | singleSelect | `Up`, `Flat`, `Down` |
| Notes | multilineText | referral callouts, anomalies, ambiguous-property flags |

## Failure Modes + Recovery

| Failure | Detection | Recovery |
|---------|-----------|----------|
| OAuth refresh returns 4xx | curl exit code or empty `access_token` | SKILL_RESULT: fail. Operator regenerates refresh token. Don't retry. |
| GSC `/sites` returns empty | `siteEntry` empty array | SKILL_RESULT: skip with notes. Brand's GSC may be under a different Google account. |
| GSC `searchAnalytics/query` 5xx | HTTP code 5xx | Retry once after 3 min. If still failing, SKILL_RESULT: fail. |
| WP `/posts?slug=X` returns empty | Empty array | Mark candidate `Status=Skipped`, Notes `WP post lookup failed`. Continue. |
| Rank Math `/updateMeta` 5xx/000 | HTTP code | Retry once after 3 min. If still failing, mark `Status=Apply-Failed`. |
| Auto-apply succeeds but live HTML unchanged | grep mismatch after 30s | Roll back via snapshot, mark `Status=Rolled-Back` (or `Apply-Failed` if rollback fails). |
| GA4 property ambiguous | >1 match in accountSummaries | Write a single flagged GA4 Insights row, do NOT pick blindly. Operator sets `GA4_PROPERTY_ID`. |
| Airtable POST 4xx | HTTP code | Most likely a missing table ID — see Step 12. SKILL_RESULT: skip. |
| Domain mismatch | host check | Mark `Status=Skipped`, Notes `domain mismatch`. |

## Rules

- Never auto-apply non-CTR-Rewrite candidates. Content-Refresh and Brand-Defense always go to Jon.
- Never run auto-apply on the first-ever run for a brand (one-shot guard file).
- Never propose two near-duplicate queries on the same page (`feedback_no_keyword_stuffing`).
- Always snapshot before applying; always verify after applying; always roll back on mismatch.
- Always check `feedback_verify_api_failures` before declaring an OAuth/Airtable/Rank Math failure — verify with a known-good endpoint first.
- Always update the Airtable audit trail, even on skips and failures.
- Honor the WP REST retry rule (`feedback_wp_rest_retry`): one retry after 3 min on 5xx/000, never on 4xx.

## Manual run (operator)

```bash
docker exec -it jonops-<BRAND> bash -c "cd /home/agent/project && /home/agent/.local/bin/claude --dangerously-skip-permissions -p 'Read .claude/skills/gsc-ga4-sweep.md and execute it for $BRAND_NAME.'"
```
Or via the dispatcher:
```bash
docker exec jonops-<BRAND> bash /home/agent/project/cron-dispatcher.sh --slot monday_04:00
```
