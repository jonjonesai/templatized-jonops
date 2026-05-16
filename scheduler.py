#!/usr/bin/env python3
"""
JonOps — In-Container Task Scheduler
=====================================
Runs as a persistent daemon inside the Docker container.
Reads schedule.json, dispatches tasks at scheduled times per configured timezone.

Each project container runs its own scheduler — no host cron needed.

Usage:
  python3 scheduler.py              # Run in foreground
  python3 scheduler.py --force      # Run in foreground, bypass PID check (supervisor)
  python3 scheduler.py --daemon     # Run in background (writes PID file)
  python3 scheduler.py --status     # Check if scheduler is running
  python3 scheduler.py --stop       # Stop the daemon
  python3 scheduler.py --next       # Show next scheduled task

Design:
  - Wakes up every 30 seconds to check the clock
  - At each scheduled time slot (with 2-min tolerance), dispatches the task
  - Tracks which slots have already fired today to prevent double-runs
  - Resets the "fired" tracker at midnight WITA
  - Logs to /home/agent/project/logs/scheduler.log

v2 Changes:
  - get_all_daily_slots() now includes weekly + monthly slots for today
  - get_task_for_slot() respects active:false flag (progressive disclosure)
  - Monthly task support (fires on 1st of month)
"""

import json
import os
import sys
import signal
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WITA = timezone(timedelta(hours=8))
SCHEDULE_PATH = Path("/home/agent/project/schedule.json")
DISPATCHER_PATH = Path("/home/agent/project/cron-dispatcher.sh")
LOG_DIR = Path("/home/agent/project/logs")
PID_FILE = Path("/home/agent/project/scheduler.pid")
SCHEDULER_LOG = LOG_DIR / "scheduler.log"

CHECK_INTERVAL = 30        # seconds between clock checks
TOLERANCE_MINUTES = 2      # fire if within N minutes of scheduled time
TASK_TIMEOUT = 1800        # max seconds per task (30 min)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def log(msg, level="INFO"):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(WITA)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S WITA")
    line = f"[{timestamp}] [{level}] {msg}"
    with open(SCHEDULER_LOG, "a") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# Schedule reader
# ---------------------------------------------------------------------------
def load_schedule():
    with open(SCHEDULE_PATH) as f:
        return json.load(f)


def get_all_daily_slots():
    """Return ALL time slots for today: daily + weekly overrides + monthly if 1st."""
    schedule = load_schedule()
    now = datetime.now(WITA)
    day_name = now.strftime("%A").lower()

    slots = set()

    # Daily slots always included
    daily = schedule.get("recurring", {}).get("daily", {})
    slots.update(daily.keys())

    # Weekly slots for today
    weekly = schedule.get("recurring", {}).get("weekly", {})
    for key in weekly.keys():
        if key.startswith(f"{day_name}_"):
            slot = key.replace(f"{day_name}_", "")
            slots.add(slot)

    # Monthly slots if today is the 1st
    if now.day == 1:
        monthly = schedule.get("recurring", {}).get("monthly", {})
        for key in monthly.keys():
            slot = key.replace("1st_", "")
            slots.add(slot)

    return sorted(slots)


def get_task_for_slot(slot, day_name):
    """Return the task dict for a given slot + day, considering weekly/monthly overrides.

    Logs the full resolution path so slot mismatches (e.g. friday_08:00 silently
    resolving to thursday_08:00) are diagnosable from scheduler.log.
    """
    schedule = load_schedule()
    now = datetime.now(WITA)
    weekly = schedule.get("recurring", {}).get("weekly", {})
    daily = schedule.get("recurring", {}).get("daily", {})

    # Surface any other weekday entries that share this slot — collision evidence
    colliding_weekly_keys = [k for k in weekly.keys() if k.endswith(f"_{slot}")]

    # Monthly first (only on 1st of month)
    if now.day == 1:
        monthly = schedule.get("recurring", {}).get("monthly", {})
        monthly_key = f"1st_{slot}"
        if monthly_key in monthly:
            task = monthly[monthly_key].copy()
            if task.get("active", True):
                task["slot"] = slot
                task["schedule_type"] = "monthly"
                log(f"RESOLVE slot {slot} day {day_name} → monthly[{monthly_key}] = {task.get('task')}")
                return task
            # active: false → fall through to weekly/daily

    # Weekly override
    weekly_key = f"{day_name}_{slot}"
    if weekly_key in weekly:
        task = weekly[weekly_key].copy()
        if task.get("active", True):
            task["slot"] = slot
            task["schedule_type"] = "weekly"
            task["day"] = day_name
            collisions_note = ""
            if len(colliding_weekly_keys) > 1:
                others = sorted(k for k in colliding_weekly_keys if k != weekly_key)
                collisions_note = f" (other weekdays at this slot: {', '.join(others)} — collision is fine if today's day_name resolves correctly)"
            log(f"RESOLVE slot {slot} day {day_name} → weekly[{weekly_key}] = {task.get('task')}{collisions_note}")
            return task
        # active: false → fall through to daily
        log(f"RESOLVE slot {slot} day {day_name} → weekly[{weekly_key}] inactive, falling through to daily")

    # Daily fallback
    if slot in daily:
        task = daily[slot].copy()
        if not task.get("active", True):
            log(f"RESOLVE slot {slot} day {day_name} → daily[{slot}] inactive, no task to fire")
            return None
        task["slot"] = slot
        task["schedule_type"] = "daily"
        log(f"RESOLVE slot {slot} day {day_name} → daily[{slot}] = {task.get('task')}")
        return task

    # No match at any layer — flag if there were other weekday entries for this slot
    # (most common cause: forgot to add today's weekday key while collision keys exist)
    if colliding_weekly_keys:
        log(
            f"RESOLVE slot {slot} day {day_name} → NO MATCH but other weekdays have this slot: "
            f"{', '.join(sorted(colliding_weekly_keys))}. Likely missing {day_name}_{slot} entry.",
            "WARN",
        )
    return None


def get_next_task():
    """Find the next upcoming task from now."""
    now = datetime.now(WITA)
    current_minutes = now.hour * 60 + now.minute
    day_name = now.strftime("%A").lower()
    slots = get_all_daily_slots()

    for slot in slots:
        h, m = map(int, slot.split(":"))
        slot_minutes = h * 60 + m
        if slot_minutes > current_minutes:
            task = get_task_for_slot(slot, day_name)
            if task:
                return task, slot

    # Next task is tomorrow's first slot
    tomorrow = now + timedelta(days=1)
    tomorrow_day = tomorrow.strftime("%A").lower()
    if slots:
        task = get_task_for_slot(slots[0], tomorrow_day)
        return task, f"tomorrow {slots[0]}"

    return None, None


# ---------------------------------------------------------------------------
# Process tree management
# ---------------------------------------------------------------------------
def _kill_tree(pid):
    """Kill a process and all its children via process group."""
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        time.sleep(2)
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    except (ProcessLookupError, PermissionError):
        pass


# ---------------------------------------------------------------------------
# Task dispatcher
# ---------------------------------------------------------------------------
def dispatch_task(slot):
    """Execute the cron dispatcher for a given slot using Popen + process group."""
    now = datetime.now(WITA)
    day_name = now.strftime("%A").lower()
    task_info = get_task_for_slot(slot, day_name)
    timeout = task_info.get("timeout", TASK_TIMEOUT) if task_info else TASK_TIMEOUT
    task_name = task_info.get("task", "unknown") if task_info else "unknown"

    log(f"DISPATCHING task for slot {slot} ({task_name}, timeout={timeout}s)")

    # Strip CLAUDECODE from child env to prevent nested session errors
    child_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    child_env["HOME"] = "/home/agent"
    child_env["PATH"] = "/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin"

    proc = None
    try:
        proc = subprocess.Popen(
            [str(DISPATCHER_PATH), "--slot", slot],
            cwd="/home/agent/project",
            start_new_session=True,
            env=child_env,
            stdin=subprocess.DEVNULL,
        )
        returncode = proc.wait(timeout=timeout)
        if returncode == 0:
            log(f"Task for slot {slot} completed successfully")
        else:
            log(f"Task for slot {slot} exited with code {returncode}", "WARN")
    except subprocess.TimeoutExpired:
        log(f"Task for slot {slot} TIMED OUT after {timeout}s — killing process tree", "ERROR")
        _kill_tree(proc.pid)
    except Exception as e:
        log(f"Task for slot {slot} FAILED: {e}", "ERROR")
        if proc and proc.poll() is None:
            _kill_tree(proc.pid)


# ---------------------------------------------------------------------------
# Main scheduler loop
# ---------------------------------------------------------------------------
def run_scheduler():
    """Main loop — checks clock every CHECK_INTERVAL seconds."""
    log("=" * 60)
    log("Scheduler starting — v2")
    log(f"Project: {load_schedule().get('project', 'unknown')}")
    log(f"Timezone: WITA (UTC+8)")
    log(f"Check interval: {CHECK_INTERVAL}s")
    log(f"Tolerance: {TOLERANCE_MINUTES} min")
    log(f"Schedule file: {SCHEDULE_PATH}")
    log(f"Dispatcher: {DISPATCHER_PATH}")

    slots = get_all_daily_slots()
    log(f"Today's slots: {', '.join(slots)}")

    next_task, next_slot = get_next_task()
    if next_task:
        log(f"Next task: {next_task['task']} at {next_slot}")
    log("=" * 60)

    fired_today = set()
    current_date = datetime.now(WITA).date()

    while True:
        try:
            now = datetime.now(WITA)
            today = now.date()

            # Reset fired tracker at midnight + refresh slot list for new day
            if today != current_date:
                log(f"New day: {today} — resetting fired slots")
                fired_today = set()
                current_date = today
                slots = get_all_daily_slots()
                log(f"Today's slots: {', '.join(slots)}")

            current_minutes = now.hour * 60 + now.minute
            day_name = now.strftime("%A").lower()

            for slot in slots:
                if slot in fired_today:
                    continue

                h, m = map(int, slot.split(":"))
                slot_minutes = h * 60 + m
                diff = abs(current_minutes - slot_minutes)

                if diff <= TOLERANCE_MINUTES:
                    task = get_task_for_slot(slot, day_name)
                    if task:
                        log(f"MATCH: slot {slot} (diff={diff}min) → {task['task']} [{task.get('prompt', '?')}]")
                        fired_today.add(slot)
                        dispatch_task(slot)
                    else:
                        log(f"Slot {slot} matched but no active task found — skipping", "WARN")
                        fired_today.add(slot)

        except Exception as e:
            log(f"Scheduler loop error: {e}", "ERROR")

        time.sleep(CHECK_INTERVAL)


# ---------------------------------------------------------------------------
# Daemon management
# ---------------------------------------------------------------------------
def write_pid():
    PID_FILE.write_text(str(os.getpid()))


def read_pid():
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (ValueError, OSError):
            return None
    return None


def is_running():
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def stop_daemon():
    pid = read_pid()
    if pid and is_running():
        log(f"Stopping scheduler (PID {pid})")
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        print(f"Scheduler stopped (PID {pid})")
    else:
        print("Scheduler is not running")
        PID_FILE.unlink(missing_ok=True)


def status():
    if is_running():
        pid = read_pid()
        print(f"Scheduler is RUNNING (PID {pid})")
        next_task, next_slot = get_next_task()
        if next_task:
            print(f"Next task: {next_task['task']} at {next_slot} WITA")
        now = datetime.now(WITA)
        day_name = now.strftime("%A").lower()
        print(f"\nToday's schedule ({day_name}):")
        for slot in get_all_daily_slots():
            task = get_task_for_slot(slot, day_name)
            if task:
                marker = "→" if slot > now.strftime("%H:%M") else "✓"
                print(f"  {marker} {slot} — {task['task']}: {task['description']}")
    else:
        print("Scheduler is NOT running")
        print("Start with: python3 scheduler.py --daemon")


def show_next():
    next_task, next_slot = get_next_task()
    if next_task:
        now = datetime.now(WITA)
        print(f"Current time: {now.strftime('%H:%M')} WITA ({now.strftime('%A')})")
        print(f"Next task: {next_task['task']}")
        print(f"  Time: {next_slot} WITA")
        print(f"  Prompt: {next_task.get('prompt', '?')}")
        print(f"  Description: {next_task['description']}")
    else:
        print("No upcoming tasks found")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if "--status" in sys.argv:
        status()
    elif "--stop" in sys.argv:
        stop_daemon()
    elif "--next" in sys.argv:
        show_next()
    elif "--daemon" in sys.argv:
        if is_running():
            print(f"Scheduler already running (PID {read_pid()})")
            sys.exit(1)
        pid = os.fork()
        if pid > 0:
            print(f"Scheduler started in background (PID {pid})")
            sys.exit(0)
        else:
            os.setsid()
            write_pid()
            sys.stdout = open(SCHEDULER_LOG, "a", buffering=1)
            sys.stderr = sys.stdout
            signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
            try:
                run_scheduler()
            finally:
                PID_FILE.unlink(missing_ok=True)
    else:
        # Foreground mode (used by supervisor)
        force = "--force" in sys.argv
        if not force and is_running():
            print(f"Scheduler already running (PID {read_pid()}). Use --force to override.")
            sys.exit(1)
        write_pid()
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
        try:
            run_scheduler()
        finally:
            PID_FILE.unlink(missing_ok=True)
