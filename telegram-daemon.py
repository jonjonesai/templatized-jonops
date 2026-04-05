#!/usr/bin/env python3
"""
telegram-daemon.py — Chat interface to the JonOps agent via Telegram.

Long-polls the Telegram Bot API, routes messages to the Claude Agent SDK,
sends responses back to the operator. Single-user whitelist via chat_id.

Runs as a long-lived process (managed by supervisord alongside scheduler.py).

Commands supported:
  /reset  — forget the current session, start fresh on next message
  /status — show session info, today's token usage, scheduler state
  /help   — show available commands

Env vars required:
  TELEGRAM_BOT_TOKEN          — from @BotFather
  TELEGRAM_CHAT_ID            — whitelisted chat ID (operator's Telegram)

Env vars optional:
  TELEGRAM_DAILY_TOKEN_BUDGET — default 500000
  TELEGRAM_DAEMON_ENABLED     — set to "false" to disable (default: true)
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections import deque
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import requests
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    SystemMessage,
    TextBlock,
)

# ─── Config ───────────────────────────────────────────────────────────────────

PROJECT_DIR = Path("/home/agent/project")
SESSIONS_DIR = PROJECT_DIR / "sessions"
LOGS_DIR = PROJECT_DIR / "logs" / "telegram"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
DAILY_TOKEN_BUDGET = int(os.environ.get("TELEGRAM_DAILY_TOKEN_BUDGET", "500000"))
DAEMON_ENABLED = os.environ.get("TELEGRAM_DAEMON_ENABLED", "true").lower() == "true"

POLL_TIMEOUT = 30  # long-poll seconds
HTTP_TIMEOUT = POLL_TIMEOUT + 10
TELEGRAM_MSG_MAX = 4000  # safety margin under 4096 hard limit
RATE_LIMIT_WINDOW = 3600  # seconds
RATE_LIMIT_MAX = 30  # messages per window

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ─── Logging ──────────────────────────────────────────────────────────────────

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _log_file() -> Path:
    return LOGS_DIR / f"{date.today().isoformat()}.log"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_log_file()),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("telegram-daemon")

# ─── Telegram API helpers ─────────────────────────────────────────────────────


def tg_send(chat_id: str, text: str, parse_mode: Optional[str] = None) -> dict:
    """Send a message. Chunks if longer than TELEGRAM_MSG_MAX."""
    if not text:
        text = "(empty response)"
    chunks = _chunk_text(text, TELEGRAM_MSG_MAX)
    last_resp = {}
    for chunk in chunks:
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            r = requests.post(
                f"{TELEGRAM_API}/sendMessage", data=payload, timeout=15
            )
            last_resp = r.json()
            if not last_resp.get("ok"):
                log.error(f"Telegram sendMessage failed: {last_resp}")
        except requests.RequestException as e:
            log.error(f"Telegram sendMessage exception: {e}")
        time.sleep(0.3)  # gentle throttle between chunks
    return last_resp


def tg_get_updates(offset: int) -> list:
    """Long-poll for new updates."""
    try:
        r = requests.get(
            f"{TELEGRAM_API}/getUpdates",
            params={"offset": offset, "timeout": POLL_TIMEOUT},
            timeout=HTTP_TIMEOUT,
        )
        data = r.json()
        if not data.get("ok"):
            log.error(f"getUpdates error: {data}")
            return []
        return data.get("result", [])
    except requests.RequestException as e:
        log.warning(f"getUpdates network error: {e}")
        return []


def _chunk_text(text: str, max_len: int) -> list[str]:
    """Split text into Telegram-safe chunks, preferring line breaks."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        # Handle single lines longer than the max (rare)
        while len(line) > max_len:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:max_len])
            line = line[max_len:]
        if len(current) + len(line) > max_len:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks


# ─── Session state ────────────────────────────────────────────────────────────


def _session_path(chat_id: str) -> Path:
    return SESSIONS_DIR / f"{chat_id}.json"


def _default_state() -> dict:
    return {
        "session_id": None,
        "started_at": None,
        "last_message_at": None,
        "token_usage_today": 0,
        "cost_today_usd": 0.0,
        "usage_date": date.today().isoformat(),
        "message_times": [],
        "total_messages": 0,
    }


def load_state(chat_id: str) -> dict:
    p = _session_path(chat_id)
    if p.exists():
        try:
            state = json.loads(p.read_text())
            # Merge defaults for any missing keys
            defaults = _default_state()
            for k, v in defaults.items():
                state.setdefault(k, v)
            return state
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"Could not load session for {chat_id}: {e}")
    return _default_state()


def save_state(chat_id: str, state: dict) -> None:
    try:
        _session_path(chat_id).write_text(json.dumps(state, indent=2))
    except OSError as e:
        log.error(f"Could not save session for {chat_id}: {e}")


def reset_daily_usage(state: dict) -> dict:
    today = date.today().isoformat()
    if state.get("usage_date") != today:
        state["token_usage_today"] = 0
        state["cost_today_usd"] = 0.0
        state["usage_date"] = today
    return state


def check_rate_limit(state: dict) -> tuple[bool, int]:
    """Returns (allowed, messages_in_window)."""
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    times = [t for t in state.get("message_times", []) if t > cutoff]
    state["message_times"] = times
    if len(times) >= RATE_LIMIT_MAX:
        return False, len(times)
    return True, len(times)


def record_message_time(state: dict) -> None:
    state.setdefault("message_times", []).append(time.time())
    state["total_messages"] = state.get("total_messages", 0) + 1


# ─── Claude Agent SDK integration ─────────────────────────────────────────────


async def run_agent(user_message: str, resume_session_id: Optional[str]) -> dict:
    """
    Send a message to the Claude agent. Returns dict with:
      text: str               — final response text
      session_id: str | None  — session ID (new or resumed)
      tokens_in: int
      tokens_out: int
      cost_usd: float
      duration_ms: int
    """
    options = ClaudeAgentOptions(
        cwd=str(PROJECT_DIR),
        permission_mode="bypassPermissions",
        setting_sources=["project"],  # loads CLAUDE.md, .claude/settings.json
        resume=resume_session_id,
    )

    t0 = time.time()
    result = {
        "text": "",
        "session_id": resume_session_id,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "duration_ms": 0,
    }
    collected_text: list[str] = []

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_message)
            async for message in client.receive_response():
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    sid = getattr(message, "session_id", None) or (
                        message.data.get("session_id") if hasattr(message, "data") else None
                    )
                    if sid:
                        result["session_id"] = sid
                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            collected_text.append(block.text)
                elif isinstance(message, ResultMessage):
                    # Final message — pull usage + cost
                    usage = getattr(message, "usage", None) or {}
                    if isinstance(usage, dict):
                        # Include cache tokens — they're the bulk of agent calls
                        result["tokens_in"] = (
                            (usage.get("input_tokens", 0) or 0)
                            + (usage.get("cache_creation_input_tokens", 0) or 0)
                            + (usage.get("cache_read_input_tokens", 0) or 0)
                        )
                        result["tokens_out"] = usage.get("output_tokens", 0) or 0
                    cost = getattr(message, "total_cost_usd", None)
                    if cost is not None:
                        result["cost_usd"] = float(cost)
                    # Prefer ResultMessage.result over streamed text (final canonical)
                    if getattr(message, "result", None):
                        result["text"] = message.result

    except Exception as e:
        log.exception("Agent SDK error")
        result["text"] = f"⚠️ Agent error: {type(e).__name__}: {e}"

    if not result["text"]:
        result["text"] = "".join(collected_text).strip() or "(no response)"

    result["duration_ms"] = int((time.time() - t0) * 1000)
    return result


# ─── Command handlers ─────────────────────────────────────────────────────────


def handle_command(chat_id: str, text: str, state: dict) -> Optional[str]:
    """Return a response string if this is a command, else None."""
    cmd = text.strip().lower().split()[0]
    if cmd == "/reset":
        state["session_id"] = None
        state["started_at"] = None
        return "🔄 Session reset. Next message starts a fresh context."
    if cmd == "/status":
        pct = (state["token_usage_today"] / DAILY_TOKEN_BUDGET * 100) if DAILY_TOKEN_BUDGET else 0
        return (
            f"📊 JonOps status\n"
            f"Session: {'active' if state.get('session_id') else 'none'}\n"
            f"Messages today: {len([t for t in state.get('message_times', []) if t > time.time() - 86400])}\n"
            f"Tokens today: {state['token_usage_today']:,} / {DAILY_TOKEN_BUDGET:,} ({pct:.1f}%)\n"
            f"Cost today: ${state['cost_today_usd']:.2f}\n"
            f"Total lifetime msgs: {state.get('total_messages', 0)}"
        )
    if cmd in ("/help", "/start"):
        return (
            "🤖 JonOps marketing agent\n\n"
            "Just message me anything — I have full access to your WordPress, "
            "Airtable, Asana, MCP tools, and project files. I remember our "
            "conversation across messages.\n\n"
            "Commands:\n"
            "/reset  — start a fresh conversation\n"
            "/status — show today's usage\n"
            "/help   — show this message"
        )
    return None


# ─── Main message handler ─────────────────────────────────────────────────────


async def handle_message(chat_id: str, text: str) -> None:
    state = load_state(chat_id)
    state = reset_daily_usage(state)

    # Rate limit check
    allowed, count = check_rate_limit(state)
    if not allowed:
        tg_send(
            chat_id,
            f"⚠️ Rate limit: {count} messages in last hour. Slow down and try again later.",
        )
        save_state(chat_id, state)
        return

    # Budget check
    if state["token_usage_today"] >= DAILY_TOKEN_BUDGET:
        tg_send(
            chat_id,
            f"⚠️ Daily token budget hit ({DAILY_TOKEN_BUDGET:,}). "
            f"Try tomorrow, or raise TELEGRAM_DAILY_TOKEN_BUDGET.",
        )
        save_state(chat_id, state)
        return

    record_message_time(state)
    state["last_message_at"] = datetime.now().isoformat()

    # Handle commands first
    cmd_response = handle_command(chat_id, text, state)
    if cmd_response is not None:
        tg_send(chat_id, cmd_response)
        save_state(chat_id, state)
        return

    # Send typing indicator
    try:
        requests.post(
            f"{TELEGRAM_API}/sendChatAction",
            data={"chat_id": chat_id, "action": "typing"},
            timeout=5,
        )
    except requests.RequestException:
        pass

    # Invoke the agent
    log.info(f"chat={chat_id} msg={text[:80]!r} session={state.get('session_id')}")
    result = await run_agent(text, state.get("session_id"))

    # Update session state
    if result["session_id"]:
        if state.get("session_id") != result["session_id"]:
            state["started_at"] = datetime.now().isoformat()
        state["session_id"] = result["session_id"]
    state["token_usage_today"] += result["tokens_in"] + result["tokens_out"]
    state["cost_today_usd"] = round(
        state.get("cost_today_usd", 0.0) + result["cost_usd"], 4
    )
    save_state(chat_id, state)

    log.info(
        f"chat={chat_id} tokens_in={result['tokens_in']} "
        f"tokens_out={result['tokens_out']} cost=${result['cost_usd']:.4f} "
        f"duration={result['duration_ms']}ms"
    )

    # Send response
    reply = result["text"]
    # Append soft warning if near budget
    pct = state["token_usage_today"] / DAILY_TOKEN_BUDGET * 100 if DAILY_TOKEN_BUDGET else 0
    if pct >= 80:
        reply += f"\n\n⚠️ {pct:.0f}% of daily budget used (${state['cost_today_usd']:.2f})"
    tg_send(chat_id, reply)


# ─── Main poll loop ───────────────────────────────────────────────────────────


async def poll_loop() -> None:
    log.info("Telegram daemon starting")
    log.info(f"Whitelisted chat_id: {TELEGRAM_CHAT_ID}")
    log.info(f"Daily token budget: {DAILY_TOKEN_BUDGET:,}")

    # Alive ping
    try:
        tg_send(
            TELEGRAM_CHAT_ID,
            "✅ JonOps is back online. Message me anytime.",
        )
    except Exception as e:
        log.warning(f"Could not send startup ping: {e}")

    offset = 0
    while True:
        updates = tg_get_updates(offset)
        for upd in updates:
            offset = max(offset, upd["update_id"] + 1)
            msg = upd.get("message") or upd.get("edited_message")
            if not msg:
                continue
            chat = msg.get("chat", {})
            chat_id_str = str(chat.get("id", ""))
            from_user = msg.get("from", {})
            username = from_user.get("username", "?")
            text = msg.get("text", "")

            # Whitelist enforcement
            if chat_id_str != TELEGRAM_CHAT_ID:
                log.warning(
                    f"REJECTED unauthorized chat_id={chat_id_str} "
                    f"user=@{username} text={text[:60]!r}"
                )
                continue

            if not text:
                continue  # ignore non-text messages (photos, stickers, etc.)

            try:
                await handle_message(chat_id_str, text)
            except Exception:
                log.exception("handle_message failed")
                try:
                    tg_send(chat_id_str, "⚠️ Internal error handling your message. Check logs.")
                except Exception:
                    pass


# ─── Entry ────────────────────────────────────────────────────────────────────


def validate_config() -> bool:
    if not TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN not set. Exiting.")
        return False
    if not TELEGRAM_CHAT_ID:
        log.error("TELEGRAM_CHAT_ID not set. Exiting.")
        return False
    if not DAEMON_ENABLED:
        log.info("TELEGRAM_DAEMON_ENABLED=false. Exiting.")
        return False
    return True


def main() -> None:
    if not validate_config():
        sys.exit(1)
    try:
        asyncio.run(poll_loop())
    except KeyboardInterrupt:
        log.info("Telegram daemon stopped by user")
    except Exception:
        log.exception("Telegram daemon crashed")
        sys.exit(1)


if __name__ == "__main__":
    main()
