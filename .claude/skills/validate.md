---
skill: validate
version: 1.0.0
cadence: manual (run after /init or when debugging)
trigger: user-invocable
description: "Post-deployment validation. Catches misconfigurations before the first cron run."
---

# Validate Skill

## What This Skill Does (Plain English)
This skill runs a comprehensive health check on your JonOps deployment. It catches common misconfigurations — unfilled placeholders, missing env vars, invalid API keys, broken connections — before they cause silent failures in scheduled tasks. Run this after `/init` or whenever something seems off.

---

## When to Run
- After running `/init` wizard
- After editing `.env` or `CLAUDE.md`
- When scheduled tasks are failing silently
- Before going live with a new deployment

---

## Validation Checklist

Run each check in order. Stop and report on first critical failure.

### 1. Placeholder Check (CRITICAL)

Scan for unfilled template placeholders in generated files:

```bash
# Check CLAUDE.md for unfilled placeholders
grep -n '{{' /home/agent/project/CLAUDE.md && echo "FAIL: Unfilled placeholders in CLAUDE.md" || echo "PASS: No placeholders in CLAUDE.md"

# Check email-persona.md
grep -n '{{' /home/agent/project/email-persona.md 2>/dev/null && echo "FAIL: Unfilled placeholders in email-persona.md" || echo "PASS: No placeholders in email-persona.md"

# Check schedule.json
grep -n '{{' /home/agent/project/schedule.json && echo "FAIL: Unfilled placeholders in schedule.json" || echo "PASS: No placeholders in schedule.json"
```

**If any `{{PLACEHOLDER}}` strings remain:** The `/init` wizard didn't complete properly. Re-run `/init` or manually fill the values.

---

### 2. Required Files Check (CRITICAL)

Verify all required files exist:

```bash
FILES=(
  "/home/agent/project/CLAUDE.md"
  "/home/agent/project/MEMORY.md"
  "/home/agent/project/schedule.json"
  "/home/agent/project/.env"
  "/home/agent/project/get-current-task.py"
  "/home/agent/project/cron-dispatcher.sh"
  "/home/agent/project/telegram-alert.sh"
  "/home/agent/project/generate-image.sh"
)

for f in "${FILES[@]}"; do
  [ -f "$f" ] && echo "PASS: $f exists" || echo "FAIL: $f missing"
done
```

---

### 3. Environment Variables Check (CRITICAL)

Verify required env vars are set and non-empty:

```bash
# Source .env
set -a; source /home/agent/project/.env; set +a

# Required for all deployments
REQUIRED_VARS=(
  "ANTHROPIC_API_KEY"
  "WP_URL"
  "WP_USERNAME"
  "WP_PASSWORD"
  "AIRTABLE_API_KEY"
  "AIRTABLE_BASE_ID"
  "REPLICATE_API"
  "TINIFY_API"
)

for var in "${REQUIRED_VARS[@]}"; do
  val="${!var}"
  if [ -z "$val" ]; then
    echo "FAIL: $var is not set"
  elif [[ "$val" == *"xxxx"* ]] || [[ "$val" == *"your_"* ]] || [[ "$val" == *"XXXX"* ]]; then
    echo "FAIL: $var appears to be a placeholder value"
  else
    echo "PASS: $var is set"
  fi
done
```

---

### 4. Airtable Table IDs Check (CRITICAL)

Verify Airtable table IDs are real (not placeholders):

```bash
AIRTABLE_TABLES=(
  "AIRTABLE_KEYWORDS_TABLE"
  "AIRTABLE_CONTENT_TABLE"
  "AIRTABLE_SOCIAL_QUEUE_TABLE"
  "AIRTABLE_SOCIAL_POSTS_LOG_TABLE"
)

for var in "${AIRTABLE_TABLES[@]}"; do
  val="${!var}"
  if [ -z "$val" ]; then
    echo "FAIL: $var is not set"
  elif [[ "$val" != tbl* ]]; then
    echo "FAIL: $var doesn't look like a valid table ID (should start with 'tbl')"
  else
    echo "PASS: $var = $val"
  fi
done
```

---

### 5. API Connectivity Tests (HIGH)

Test actual API connections:

#### WordPress
```bash
WP_TEST=$(curl -s -o /dev/null -w "%{http_code}" "$WP_URL/wp-json/wp/v2/posts?per_page=1" \
  -u "$WP_USERNAME:$WP_PASSWORD")
[ "$WP_TEST" = "200" ] && echo "PASS: WordPress API connected" || echo "FAIL: WordPress API returned $WP_TEST"
```

#### Airtable
```bash
AT_TEST=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$AIRTABLE_KEYWORDS_TABLE?maxRecords=1" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY")
[ "$AT_TEST" = "200" ] && echo "PASS: Airtable API connected" || echo "FAIL: Airtable API returned $AT_TEST"
```

#### Telegram (if configured)
```bash
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
  TG_TEST=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" | grep -c '"ok":true')
  [ "$TG_TEST" = "1" ] && echo "PASS: Telegram bot connected" || echo "FAIL: Telegram bot auth failed"
else
  echo "SKIP: Telegram not configured"
fi
```

---

### 6. Schedule Validation (HIGH)

Verify schedule.json is valid and has expected structure:

```bash
# Check JSON validity
python3 -c "import json; json.load(open('/home/agent/project/schedule.json'))" 2>/dev/null \
  && echo "PASS: schedule.json is valid JSON" \
  || echo "FAIL: schedule.json is invalid JSON"

# Check timezone is set
TZ_CHECK=$(python3 -c "import json; s=json.load(open('/home/agent/project/schedule.json')); print(s.get('timezone','MISSING'))")
if [ "$TZ_CHECK" = "MISSING" ] || [[ "$TZ_CHECK" == *"{{"* ]]; then
  echo "FAIL: timezone not set in schedule.json"
else
  echo "PASS: timezone = $TZ_CHECK"
fi

# Check at least one daily task is active
ACTIVE_COUNT=$(python3 -c "
import json
s = json.load(open('/home/agent/project/schedule.json'))
daily = s.get('recurring', {}).get('daily', {})
active = sum(1 for t in daily.values() if t.get('active', True))
print(active)
")
[ "$ACTIVE_COUNT" -gt 0 ] && echo "PASS: $ACTIVE_COUNT active daily tasks" || echo "WARN: No active daily tasks"
```

---

### 7. CLAUDE.md Structure Check (MEDIUM)

Verify CLAUDE.md has required sections:

```bash
REQUIRED_SECTIONS=(
  "Brand Voice"
  "WordPress"
  "Airtable"
)

for section in "${REQUIRED_SECTIONS[@]}"; do
  grep -q "$section" /home/agent/project/CLAUDE.md \
    && echo "PASS: CLAUDE.md has '$section' section" \
    || echo "WARN: CLAUDE.md missing '$section' section"
done
```

---

### 8. Skill Files Check (MEDIUM)

Verify skill files exist and have valid frontmatter:

```bash
SKILLS_DIR="/home/agent/project/.claude/skills"
SKILL_COUNT=$(ls -1 "$SKILLS_DIR"/*.md 2>/dev/null | wc -l)
echo "INFO: Found $SKILL_COUNT skill files"

# Check a few critical skills exist
CRITICAL_SKILLS=("blog-writer.md" "daily-contribution.md" "email-checker.md" "daily-watchdog.md")
for skill in "${CRITICAL_SKILLS[@]}"; do
  [ -f "$SKILLS_DIR/$skill" ] && echo "PASS: $skill exists" || echo "FAIL: $skill missing"
done
```

---

### 9. Permissions Check (MEDIUM)

Verify scripts are executable:

```bash
SCRIPTS=(
  "/home/agent/project/cron-dispatcher.sh"
  "/home/agent/project/telegram-alert.sh"
  "/home/agent/project/generate-image.sh"
)

for script in "${SCRIPTS[@]}"; do
  [ -x "$script" ] && echo "PASS: $script is executable" || echo "WARN: $script is not executable (run: chmod +x $script)"
done
```

---

### 10. Common Misconfigurations (LOW)

Check for known gotchas:

```bash
# WP_URL shouldn't have trailing slash
if [[ "$WP_URL" == */ ]]; then
  echo "WARN: WP_URL has trailing slash — may cause double-slash in API calls"
fi

# AIRTABLE_API_KEY shouldn't have whitespace
if [[ "$AIRTABLE_API_KEY" =~ [[:space:]] ]]; then
  echo "WARN: AIRTABLE_API_KEY contains whitespace — will cause 401 errors"
fi

# Check if observations.md exists (optional but recommended)
[ -f "/home/agent/project/observations.md" ] || echo "INFO: observations.md doesn't exist yet (will be created by agent)"
```

---

## Output Format

After running all checks, summarize:

```
╔══════════════════════════════════════════════════════════════╗
║                    VALIDATION SUMMARY                        ║
╠══════════════════════════════════════════════════════════════╣
║ Critical checks:  [X passed / Y failed]                      ║
║ High checks:      [X passed / Y failed]                      ║
║ Medium checks:    [X passed / Y warnings]                    ║
║ Low checks:       [X passed / Y warnings]                    ║
╠══════════════════════════════════════════════════════════════╣
║ Status: [READY / NOT READY / NEEDS ATTENTION]                ║
╚══════════════════════════════════════════════════════════════╝
```

**Status meanings:**
- **READY** — All critical and high checks passed. Safe to run scheduled tasks.
- **NEEDS ATTENTION** — Some warnings but no critical failures. Review warnings.
- **NOT READY** — Critical or high-priority failures. Fix before running cron.

---

## SKILL_RESULT

```
SKILL_RESULT: success | Validation complete: [X] critical, [Y] high, [Z] medium, [W] low | Status: [READY/NOT READY/NEEDS ATTENTION]
```

On validation failure:
```
SKILL_RESULT: fail | Validation found critical issues: [list of failures]
```

---

## Telegram Alert

```bash
# On success (all critical passed)
bash /home/agent/project/telegram-alert.sh "✅ validate — Deployment ready: [summary]"

# On failure
bash /home/agent/project/telegram-alert.sh "❌ validate — [N] critical issues found: [list]"
```

---

*End of Validate Skill v1.0.0*
