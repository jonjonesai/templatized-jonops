# Spec: Telegram Chat Interface for JonOps Agent

**Goal:** Let the operator talk to the JonOps agent via Telegram instead of SSHing into the box and using Claude Code CLI. Same agent, same context (CLAUDE.md, MEMORY.md, MCP servers, tools, working directory) — just a different input channel.

**Why:** Most small business owners will never touch a terminal. Telegram is universal. This transforms JonOps from "a system engineers install" into "a marketing AI you text."

---

## Architecture

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Telegram   │────▶│  telegram-daemon.py  │────▶│ Claude Agent    │
│  (Operator  │◀────│  (long-lived proc)   │◀────│ SDK session     │
│   phone)    │     │                      │     │                 │
└─────────────┘     └──────────────────────┘     └─────────────────┘
                              │                           │
                              ▼                           ▼
                    ┌──────────────────┐       ┌──────────────────┐
                    │ sessions/*.json  │       │ CLAUDE.md, MCP,  │
                    │ (per-chat state) │       │ tools, filesystem│
                    └──────────────────┘       └──────────────────┘
```

The daemon runs alongside `scheduler.py` inside the existing Docker container. Uses Claude Agent SDK (Python) to spawn sessions — NOT subprocess-wrapping the CLI.

---

## Components to Build

### 1. `telegram-daemon.py` — main daemon (~200 lines)

Responsibilities:
- Long-poll Telegram API (`getUpdates` with 30s timeout)
- Whitelist check: reject any chat_id not matching `TELEGRAM_CHAT_ID`
- Load/create Claude Agent SDK session for the chat
- Stream agent response back to Telegram
- Chunk long responses (Telegram caps at 4096 chars/message)
- Handle special commands (`/reset`, `/status`, `/stop`)
- Persist session state to disk
- Track daily token usage, kill-switch if budget exceeded

### 2. `sessions/` directory

Stores per-chat session state:
```
sessions/
├── {chat_id}.json     # session_id, started_at, last_message_at, token_usage_today
└── .gitkeep
```
Gitignored.

### 3. Integration with `post-start.sh`

Daemon starts as a background process when container launches. If it crashes, gets restarted (use supervisord or a simple retry loop).

### 4. Dependency additions

`requirements.txt` (or `pyproject.toml`):
- `claude-agent-sdk` (official Anthropic package)
- `requests` (Telegram HTTP API — no heavy bot library needed)

---

## Technical Decisions

### Polling vs Webhooks → **Long-polling**
No public HTTPS endpoint needed. Simpler, no ngrok/reverse proxy. Call `getUpdates` with `timeout=30` and Telegram holds the connection open until messages arrive.

### Session model → **One Claude session per Telegram chat, persisted**
SDK supports resuming via session_id. Save session_id to `sessions/{chat_id}.json` so agent remembers context across daemon restarts and across days.

### Concurrency with scheduler → **Run in parallel, don't block**
Don't make the operator wait if a cron skill is running. Scheduled skills take 5-30 min — too long. The operator must always reach the agent. Risks of parallel access are low in practice (different files, different purposes). Document the edge case, accept it.

### Streaming vs batch responses → **Start batch, upgrade to streaming v2**
V1: wait for full response, chunk if >4000 chars, send as multiple messages.
V2: stream into a single message, edit as tokens arrive. Nicer UX but more complex.

### Permission mode → **`bypassPermissions` (same as cron)**
Interactive chat with the operator = trusted. No point prompting for tool approval over Telegram. Whitelist is the gate.

### Commands → **Minimal set**
- `/reset` — start fresh session (forget previous context)
- `/status` — show session info, today's token usage, scheduler status
- `/stop` — interrupt current agent response (harder to implement — v2)

### Cost controls → **Daily token budget with soft warning + hard kill**
- `TELEGRAM_DAILY_TOKEN_BUDGET` env var (default: 500k tokens ≈ $5 for Opus)
- At 80%: inject warning into next reply
- At 100%: daemon sends "budget hit, try tomorrow" and refuses to call SDK until midnight
- Reset counter at local midnight

---

## Security (Non-Negotiable)

1. **Whitelist enforcement.** First line of every message handler:
   ```python
   if str(update["message"]["chat"]["id"]) != os.environ["TELEGRAM_CHAT_ID"]:
       log.warning(f"Unauthorized access from chat_id={chat_id}")
       return  # silent drop
   ```

2. **No environment leakage.** Agent can read env vars as part of normal operation, but the daemon itself must never echo env vars, `.env` file contents, or credentials back to Telegram.

3. **Rate limiting.** Max 30 messages per hour from the operator (prevents runaway loops if agent goes haywire and somehow pings itself).

4. **Audit log.** Every incoming message + outgoing response logged to `logs/telegram/{date}.log`.

5. **Bot token rotation path.** Document how to rotate `TELEGRAM_BOT_TOKEN` if it leaks.

---

## Environment Variables

Add to CLAUDE.md and `.env.example`:
```
TELEGRAM_BOT_TOKEN=<from @BotFather>
TELEGRAM_CHAT_ID=<from @userinfobot>
TELEGRAM_DAILY_TOKEN_BUDGET=500000  # optional, default 500k
TELEGRAM_DAEMON_ENABLED=true        # optional kill switch
```

---

## Build Order

Ship in increments. Each step is testable before moving on.

1. **Hello-world echo bot.** Python script that polls Telegram, receives message, echoes it back. Validates: token works, polling works, whitelist works.

2. **SDK integration, single-turn.** Receive message → send to Claude Agent SDK → return response. No session persistence yet. Validates: SDK auth works, response round-trip works.

3. **Session persistence.** Save session_id per chat, resume on next message. Validates: context carries across messages.

4. **Response chunking.** Handle replies >4000 chars. Validates: long responses don't get truncated.

5. **Commands.** `/reset`, `/status`.

6. **Cost tracking + kill switch.** Per-day token counter.

7. **Daemon launcher.** Wire into `post-start.sh` with auto-restart.

8. **Rate limiting + audit logs.**

9. **End-to-end test session.** Full day of real chat usage.

10. **Document.** Update README, add a TELEGRAM-INTERFACE.md user guide.

---

## Testing Plan

**Manual tests after each build step:**

- `echo test` → bot echoes back
- `what's my name?` → Claude reads CLAUDE.md, answers with operator name
- `read MEMORY.md and summarize today's publishes` → Claude uses Read tool, summarizes
- `what's my latest blog post?` → Claude hits WordPress API or Airtable, returns URL
- `/reset` → session cleared, next message starts fresh
- `/status` → returns today's token usage
- (from another Telegram account) `hello` → silent drop, nothing happens, warning in log
- Send 10 messages in rapid succession → rate limit kicks in at message 11
- Write a message that triggers a 10k-char response → arrives as 3 chunks
- Restart the Docker container → daemon comes back, session continues

**Concurrency tests:**
- While social-miner cron is running (12:00), message "hi" → should work in parallel
- Ask Claude to edit a file while scheduler is doing same → document what happens

---

## Open Questions

1. **Budget default:** 500k tokens/day reasonable as a starter? ($5ish for Opus)
2. **`/stop` support in v1?** Mid-operation interruption is tricky — skip for now?
3. **Multiple chats?** Currently whitelist = single chat_id. Do you ever want a VA or partner to message the same bot? (Would need multi-user whitelist + per-user session isolation.)
4. **Voice messages?** Whisper API integration would let you dictate. Great feature. v2 or never?
5. **Should the daemon post a "I'm alive" message to you when the container starts?** So you know when it's ready after restarts.

---

## Templatization Notes

- All code is already generic (no brand-specific strings)
- Document in SETUP.md: user creates bot via @BotFather, gets token, gets their chat_id from @userinfobot, puts both in `.env`
- Daily budget is user-configurable
- The rest is automatic

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Bot token leaked | Token rotation documented, bot scoped to one chat_id |
| Runaway agent loop burns budget | Daily kill switch, rate limit on inbound messages |
| Parallel Claude processes corrupt files | Accept the risk, surface conflicts via git status — rare in practice |
| Daemon crashes silently | Auto-restart via supervisord, heartbeat log every 5min |
| Telegram API rate limits | Batch replies, 1s min delay between sends |
| Agent SDK auth issues | Use same `ANTHROPIC_API_KEY` flow as existing skills |

---

## What V1 Is NOT

- Not a web UI. Just Telegram.
- Not streaming responses (v2).
- Not multi-user (v2).
- Not voice (v2).
- Not tool-approval-over-Telegram (bypass mode only).

Keep scope tight, ship the core loop, iterate from there.

---

*Feature documentation for JonOps template.*
