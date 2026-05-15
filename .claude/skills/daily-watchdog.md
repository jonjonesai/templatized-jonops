---
skill: daily-watchdog
version: 1.1.0
cadence: daily (23:30)
trigger: cron
airtable_reads: []
airtable_writes: []
external_apis: [asana, metricool]
active: true
notes: "Runs last thing every night. Reviews today's cron results AND Metricool scheduled posts, retries transient failures. The safety net."
---

# Daily Watchdog Skill

## What This Skill Does (Plain English)
This is the safety net that runs last thing every night (11:30 PM). It reviews the logs from every cron job that ran today, identifies any that failed or timed out, and retries them once. For example, if the social poster failed at 9 AM due to an API timeout, the watchdog catches it and runs it again. It then posts a summary report to Asana so the operator can see at a glance what succeeded and what needs attention.

---

## Purpose
Review today's cron job results, identify any failures, and retry them once. This is the safety net that ensures nothing important gets silently missed. Runs at 23:30 WITA — after all daily tasks have had a chance to complete.

## Process

### Step 1: Read today's scheduler log
```bash
TODAY=$(TZ='Asia/Makassar' date '+%Y-%m-%d')
grep "$TODAY" /home/agent/project/logs/scheduler.log
```

Extract all DISPATCHING entries for today. Build a list of:
- Task name
- Slot time
- Result (completed successfully / exited with code X / TIMED OUT)

### Step 2: For each task — find its log file and check result
```bash
ls /home/agent/project/logs/ | grep "$TODAY"
```

For each task log file found, check the last few lines:
- Contains `SKILL_RESULT: success` → ✅ passed
- Contains `EXIT CODE: 0` → ✅ passed  
- Contains `EXIT CODE: 1` or `TIMED OUT` or `FAILED` → ❌ failed
- No log file exists (dispatcher died before creating it) → ❌ failed

### Step 3: Build the daily report
Produce a structured summary:

```
DAILY WATCHDOG REPORT — [DATE]
==============================
✅ PASSED:
  - 00:00 blog-writer — "Post Title" published
  - 07:00 daily-contribution — published
  - 09:00 social-poster-1 — 6 posts scheduled
  - 11:00 email-checker — 3 emails processed

❌ FAILED:
  - 08:00 outreach-conductor — Instantly API 524 timeout
  - 20:00 social-poster-2 — Social Queue empty

⚠️ SKIPPED (no log):
  - 22:00 asana-check — no log file found
```

### Step 4: Retry failed tasks
For each failed task — retry it ONCE by calling the dispatcher directly:

```bash
bash /home/agent/project/cron-dispatcher.sh --slot [SLOT_TIME]
```

Wait for it to complete before moving to the next retry.

After retry, check the new log file for success or failure.

**Rules for retrying:**
- Only retry tasks where failure was likely transient (API timeout, network error, empty queue)
- Do NOT retry blog-writer or daily-contribution if they already published successfully (check WordPress)
- Do NOT retry if failure was due to missing credentials or config — escalate to Asana instead
- Maximum ONE retry per failed task

### Step 4b: Sweep Metricool for failed scheduled posts

Facebook and Pinterest intermittently return generic 500s ("Please reduce the amount of data…" or "Something went wrong on our end") on otherwise valid posts. These are provider-side flakes, not stack bugs. Reclone the failed post into a +10-minute slot so it gets a second shot, capped at 2 retries per original post.

**Step 4b.1 — Resolve env (handles both naming conventions across brands):**
```bash
METRICOOL_BLOG="${METRICOOL_BLOG_ID:-${METRICOOL_BLOGID:-}}"
METRICOOL_USER="${METRICOOL_USER_ID:-${METRICOOL_USERID:-}}"
WATCHDOG_TZ=$(jq -r '.timezone // "Asia/Makassar"' /home/agent/project/schedule.json)

if [[ -z "$METRICOOL_API_TOKEN" || -z "$METRICOOL_BLOG" || -z "$METRICOOL_USER" ]]; then
  echo "[watchdog] Metricool env unset — skipping Step 4b"
  # Note "metricool env unset" in the daily report and proceed to Step 5
fi
```

**Step 4b.2 — Query today's Metricool posts:**
```bash
TODAY=$(TZ="$WATCHDOG_TZ" date '+%Y-%m-%d')
TOMORROW=$(TZ="$WATCHDOG_TZ" date -d '+1 day' '+%Y-%m-%d')
curl -s -H "X-Mc-Auth: ${METRICOOL_API_TOKEN}" \
  "https://app.metricool.com/api/v2/scheduler/posts?blogId=${METRICOOL_BLOG}&userId=${METRICOOL_USER}&start=${TODAY}T00:00:00&end=${TOMORROW}T00:00:00&timezone=${WATCHDOG_TZ}" \
  > /tmp/metricool-today.json
```

**Step 4b.3 — Find ERROR posts and classify:**

Parse `/tmp/metricool-today.json`. For each post where any `providers[].status == "ERROR"`:

- Identify the network (`providers[].network`) and `detailedStatus`.
- Retry ONLY if `detailedStatus` matches a known transient pattern:
  - Contains `"Code: 500"` AND (`"reduce the amount of data"` OR `"Something went wrong on our end"` OR `"Internal Server Error"`)
  - OR contains `"timeout"` / `"timed out"` / `"503"` / `"502"`
- Do NOT retry if `detailedStatus` indicates auth/format/policy issues (`"invalid_token"`, `"expired"`, `"unsupported"`, `"policy"`, `"permission"`, `"Code: 4"` series, `"Code: 1"` with no transient phrase). Note these in the daily report as "NEEDS OPERATOR" — do not silently skip.

**Step 4b.4 — Check retry counter:**

Retry counters live in `/home/agent/project/cache/metricool-retries.json`:
```json
{
  "<original_uuid>": {"count": 1, "last_retry": "2026-05-15T23:40:00", "network": "facebook"}
}
```

- Load (or initialize empty) the JSON.
- Garbage-collect entries older than 3 days.
- If the failed post's `uuid` already has `count >= 2`, do NOT retry — note in report as "exhausted retries."

**Step 4b.5 — Reclone the post:**

For each retry-eligible post, build a new payload that mirrors the failed one and POST it back to Metricool with a publication time 10 minutes from now:

```bash
NOW_PLUS_10=$(TZ="$WATCHDOG_TZ" date -d '+10 minutes' '+%Y-%m-%dT%H:%M:00')

# Build payload from the failed post:
#   - Preserve: text, media, mediaAltText, firstCommentText, autoPublish, shortener,
#     videoCoverMilliseconds, and the network-specific data block (facebookData / instagramData /
#     pinterestData / twitterData / etc.) for the FAILING network only.
#   - Set publicationDate to NOW_PLUS_10 with timezone=$WATCHDOG_TZ.
#   - providers[] must contain ONLY the failing network — do not double-post to networks
#     that already published.

curl -s -X POST -H "X-Mc-Auth: ${METRICOOL_API_TOKEN}" \
  -H "Content-Type: application/json" \
  "https://app.metricool.com/api/v2/scheduler/posts?blogId=${METRICOOL_BLOG}&userId=${METRICOOL_USER}&timezone=${WATCHDOG_TZ}" \
  -d @/tmp/retry-payload.json
```

After POST, increment the counter in `metricool-retries.json` and write it back.

**Step 4b.6 — Note results in the daily report:**

Add a section to the report:
```
🔁 METRICOOL RETRIES:
  - 09:00 facebook (post 325817152) — transient 500, re-cloned to 23:42 [retry 1/2]
  - 09:00 pinterest (post 325673415) — transient 500, re-cloned to 23:42 [retry 1/2]

⚠️ METRICOOL — NEEDS OPERATOR:
  - 11:00 instagram (post 325XXXXXX) — invalid_token, requires re-auth
```

**Rules:**
- Only retry the failing network — never duplicate posts that already published.
- Cap at 2 retries per original `uuid` per 3-day window.
- Hard-fail patterns (auth, policy, format) go to the report's "NEEDS OPERATOR" section, not the retry queue.
- If `METRICOOL_API_TOKEN` / blog id / user id are unset, skip Step 4b and note "metricool env unset" in the report.

### Step 5: Create Asana summary task
Create one Asana task in the Inbox section summarizing today's results:

```bash
curl -s -X POST "https://app.asana.com/api/1.0/tasks" \
  -H "Authorization: Bearer ${ASANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "📊 Daily Watchdog Report — [DATE]",
      "notes": "[full report text]",
      "projects": ["'${ASANA_PROJECT_GID}'"],
      "memberships": [{"project": "'${ASANA_PROJECT_GID}'", "section": "'${ASANA_INBOX_GID}'"}]
    }
  }'
```

### Step 6: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ daily-watchdog — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ daily-watchdog — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ daily-watchdog — [skip reason]"`

```
SKILL_RESULT: success | [N] passed, [N] failed, [N] retried ([N] retry success) | [date]
```

## Retry Decision Logic

| Failure Type | Retry? | Action |
|-------------|--------|--------|
| API timeout (Instantly, Metricool, etc.) | ✅ Yes | Retry once |
| Empty queue (Social Queue, Newsletter Queue) | ❌ No | Note in report — researcher needs to run |
| Auth error | ❌ No | Escalate to Asana — needs operator |
| Already published (blog/horoscope) | ❌ No | Mark as success |
| Network error | ✅ Yes | Retry once |
| Prompt file not found | ❌ No | Escalate to Asana |
| Timed out (task took too long) | ✅ Yes | Retry once with same timeout |
| Metricool post — transient 500 (FB "reduce data" / Pinterest "something went wrong" / 502/503/timeout) | ✅ Yes | Reclone to +10 min, capped at 2 retries / uuid / 3 days |
| Metricool post — auth/format/policy (invalid_token, expired, unsupported, policy, permission, Code 4xx) | ❌ No | Report under "NEEDS OPERATOR" |

## Rules
- Never retry blog-writer or daily-contribution if WordPress already has today's post
- Never retry more than once — if retry fails, escalate to Asana
- Always create the Asana summary task regardless of outcome
- This skill reads logs — it does NOT modify them
- Metricool retries are tracked in `cache/metricool-retries.json` and capped at 2 per original post; the file is the source of truth for the cap and must be persisted across runs
