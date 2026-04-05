#!/bin/bash
# JonOps — post-start setup (runs on every container start)
# This file lives in the volume-mounted project dir and survives rebuilds.

PROJECT_DIR="/home/agent/project"
CLAUDE_JSON="/home/agent/.claude.json"

echo "[post-start] JonOps container starting..."

# --- 1. Restore MCP server config ---
MCP_CONFIG="$PROJECT_DIR/.mcp-config.json"
if [ -f "$MCP_CONFIG" ] && command -v jq &>/dev/null; then
    # Read MCP servers from project config and merge into .claude.json
    MCP_SERVERS=$(cat "$MCP_CONFIG")

    # Substitute env vars in MCP config (e.g., ${ASTROLOGY_API_KEY})
    if [ -f "$PROJECT_DIR/.env" ]; then
        source "$PROJECT_DIR/.env"
    fi
    MCP_SERVERS=$(echo "$MCP_SERVERS" | envsubst 2>/dev/null || echo "$MCP_SERVERS")

    # Ensure .claude.json has the project path structure, then merge MCP servers
    UPDATED=$(jq --argjson servers "$MCP_SERVERS" '
        .projects //= {} |
        .projects["/home/agent/project"] //= {} |
        .projects["/home/agent/project"].mcpServers = $servers |
        .projects["/home/agent/project"].hasTrustDialogAccepted = true
    ' "$CLAUDE_JSON" 2>/dev/null)

    if [ $? -eq 0 ] && [ -n "$UPDATED" ]; then
        echo "$UPDATED" > "$CLAUDE_JSON"
        echo "[post-start] MCP config restored."
    else
        echo "[post-start] WARNING: Failed to merge MCP config."
    fi
else
    echo "[post-start] No MCP config found or jq not installed, skipping."
fi

# --- 2. Clean stale scheduler PID ---
PID_FILE="$PROJECT_DIR/scheduler.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ! kill -0 "$OLD_PID" 2>/dev/null; then
        rm -f "$PID_FILE"
        echo "[post-start] Cleaned stale scheduler PID ($OLD_PID)."
    fi
fi

# --- 3. Scheduler ---
# NOTE: Scheduler is managed by supervisord (auto-starts on boot).
# Do NOT start a second instance here — it causes double-dispatch.
# See: /home/agent/project/supervisor/conf.d/scheduler.conf
echo "[post-start] Scheduler managed by supervisord — skipping manual start."

# --- 4. Install Python dependencies not in base image ---
echo "[post-start] Checking Python dependencies..."
pip install --break-system-packages --quiet ephem 2>/dev/null && echo "[post-start] ephem installed." || echo "[post-start] ephem already installed or install failed."

echo "[post-start] Done."
