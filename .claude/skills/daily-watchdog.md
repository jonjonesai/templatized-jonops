---
skill: daily-watchdog
version: 1.0.0
cadence: daily (23:30)
trigger: cron
airtable_reads: []
airtable_writes: []
external_apis: [asana]
active: true
notes: "Runs last thing every night. Reviews today's cron results, retries failures. The safety net."
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

## Rules
- Never retry blog-writer or daily-contribution if WordPress already has today's post
- Never retry more than once — if retry fails, escalate to Asana
- Always create the Asana summary task regardless of outcome
- This skill reads logs — it does NOT modify them
