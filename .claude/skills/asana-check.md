---
skill: asana-check
version: 1.0.0
cadence: daily (22:00)
trigger: cron
airtable_reads: []
airtable_writes: []
external_apis: [asana]
active: true
notes: "Checks Agent To Do section for ad hoc tasks from the operator. Operator adds tasks from phone/anywhere."
---

# Asana Check Skill

## What This Skill Does (Plain English)
Every night at 10 PM, this skill checks an Asana "to do" list where the operator drops ad hoc tasks throughout the day (from their phone, laptop, wherever). It picks up each task, executes it if possible (e.g., "write a social post about our new product"), and marks it done. If the task needs operator input (like a financial decision), it leaves a comment explaining why and keeps it in the queue.

---

## Purpose
Check the Asana "Agent To Do" section for ad hoc tasks left by the operator. Execute any tasks that are within your capabilities autonomously. Escalate anything that requires operator input back to Asana with a comment.

This is how the operator communicates tasks to you outside of the regular cron schedule — from their phone, from a meeting, from anywhere. Always check this.

## Prerequisites
- ASANA_API_KEY in .env
- Project GID and section GIDs in CLAUDE.md

## Process

### Step 1: Fetch Agent To Do section tasks
```bash
curl -s -H "Authorization: Bearer ${ASANA_API_KEY}" \
  "https://app.asana.com/api/1.0/tasks?section=[AGENT_TODO_SECTION_GID]&opt_fields=name,notes,assignee,due_on,completed&completed_since=now"
```
If no incomplete tasks: SKILL_RESULT: skip | No ad hoc tasks in Asana. Exit cleanly.

### Step 2: For each incomplete task
Read task name and notes carefully. Categorize:

**Can execute autonomously:**
- Write/edit content (blog post, social post, email draft)
- Research a topic
- Update Airtable data
- Create WordPress draft
- Schedule social post
- Any task clearly within your skill set

**Cannot execute — needs operator:**
- Financial decisions
- Account access setup
- Tasks requiring physical action
- Ambiguous tasks where you're not sure what the operator wants

### Step 3: Execute autonomous tasks
For each executable task:
1. Execute it fully — apply relevant skill if applicable
2. Add Asana comment with what you did and any relevant URLs/results:
```bash
curl -s -X POST "https://app.asana.com/api/1.0/tasks/[TASK_GID]/stories" \
  -H "Authorization: Bearer ${ASANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"data": {"text": "✅ Done: [what you did] | [url if applicable]"}}'
```
3. Move to Done section:
```bash
curl -s -X POST "https://app.asana.com/api/1.0/sections/[DONE_SECTION_GID]/addTask" \
  -H "Authorization: Bearer ${ASANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"data": {"task": "[TASK_GID]"}}'
```

### Step 4: Comment on tasks you cannot execute
```bash
curl -s -X POST "https://app.asana.com/api/1.0/tasks/[TASK_GID]/stories" \
  -H "Authorization: Bearer ${ASANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"data": {"text": "⚠️ Needs operator: [reason why you cannot execute this]"}}'
```
Leave in Agent To Do — do not move to Done.

### Step 5: Telegram Alert & SKILL_RESULT

Before outputting SKILL_RESULT, send a Telegram alert:
```bash
bash /home/agent/project/telegram-alert.sh "✅ asana-check — [summary]"
```
On failure: `bash /home/agent/project/telegram-alert.sh "❌ asana-check — [error details]"`
On skip: `bash /home/agent/project/telegram-alert.sh "⚠️ asana-check — [skip reason]"`

```
SKILL_RESULT: success | [N] tasks executed, [M] escalated to operator | [task names]
```

## Rules
- Never mark a task Done without actually completing it
- Always add a comment explaining what you did or why you couldn't
- If a task is ambiguous, ask for clarification via comment and leave in To Do
- Never make financial decisions or commitments on the operator's behalf
