#!/usr/bin/env python3
"""
Reads schedule.json and returns the current task based on WITA time.
Supports daily, weekly, and monthly schedules.
Respects active:false flag (progressive disclosure).

Usage:
  python3 get-current-task.py              # Returns current task (if any)
  python3 get-current-task.py --slot 00:00 # Force a specific time slot
  python3 get-current-task.py --list       # List all scheduled tasks

Output (JSON):
  {"task": "blog-writer", "prompt": "blog-writer.md", "description": "...", "slot": "00:00"}
  or exits with code 1 if no task matches
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCHEDULE_PATH = Path("/home/agent/project/schedule.json")
WITA = timezone(timedelta(hours=8))


def load_schedule():
    with open(SCHEDULE_PATH) as f:
        return json.load(f)


def get_current_task(force_slot=None):
    schedule = load_schedule()
    now = datetime.now(WITA)
    day_name = now.strftime("%A").lower()
    current_time = force_slot or now.strftime("%H:%M")

    # Monthly tasks (only on 1st of month)
    # NOTE: If monthly task is inactive, fall through to check weekly/daily
    if now.day == 1:
        monthly = schedule.get("recurring", {}).get("monthly", {})
        monthly_key = f"1st_{current_time}"
        if monthly_key in monthly:
            task = monthly[monthly_key].copy()
            if task.get("active", True):
                task["slot"] = current_time
                task["schedule_type"] = "monthly"
                return task
            # Inactive monthly → fall through to weekly/daily

    # Weekly tasks (override daily on matching day+time)
    # NOTE: If weekly task is inactive, fall through to check daily
    weekly = schedule.get("recurring", {}).get("weekly", {})
    weekly_key = f"{day_name}_{current_time}"
    if weekly_key in weekly:
        task = weekly[weekly_key].copy()
        if task.get("active", True):
            task["slot"] = current_time
            task["schedule_type"] = "weekly"
            task["day"] = day_name
            return task
        # Inactive weekly → fall through to daily

    # Daily tasks
    daily = schedule.get("recurring", {}).get("daily", {})
    if current_time in daily:
        task = daily[current_time].copy()
        if not task.get("active", True):
            return {}
        task["slot"] = current_time
        task["schedule_type"] = "daily"
        return task

    return {}


def list_all_tasks():
    schedule = load_schedule()
    now = datetime.now(WITA)
    day_name = now.strftime("%A").lower()

    print(f"Schedule for: {schedule.get('project', 'unknown')}")
    print(f"Timezone: {schedule.get('timezone', 'unknown')}")
    print(f"Auth expiry: {schedule.get('auth_expiry', 'not set')}")
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M')} WITA ({day_name})")
    print()

    print("Daily tasks:")
    daily = schedule.get("recurring", {}).get("daily", {})
    for slot in sorted(daily.keys()):
        t = daily[slot]
        status = "✓" if t.get("active", True) else "✗ (inactive)"
        print(f"  {slot} {status} — {t['task']}: {t['description']}")

    print()
    print("Weekly tasks:")
    weekly = schedule.get("recurring", {}).get("weekly", {})
    for key in sorted(weekly.keys()):
        t = weekly[key]
        status = "✓" if t.get("active", True) else "✗ (inactive)"
        print(f"  {key} {status} — {t['task']}: {t['description']}")

    print()
    print("Monthly tasks:")
    monthly = schedule.get("recurring", {}).get("monthly", {})
    for key in sorted(monthly.keys()):
        t = monthly[key]
        status = "✓" if t.get("active", True) else "✗ (inactive)"
        print(f"  {key} {status} — {t['task']}: {t['description']}")


if __name__ == "__main__":
    if "--list" in sys.argv:
        list_all_tasks()
    else:
        force_slot = None
        if "--slot" in sys.argv:
            idx = sys.argv.index("--slot")
            if idx + 1 < len(sys.argv):
                force_slot = sys.argv[idx + 1]

        task = get_current_task(force_slot)
        if task:
            print(json.dumps(task))
        else:
            sys.exit(1)
