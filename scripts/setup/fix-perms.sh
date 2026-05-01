#!/bin/bash
# Set project-tree perms so the container's UID 1001 ("agent") can read+write
# the bind-mounted volume, while the host user can still manage the files
# through the jonops-shared group.
#
# Why this is needed: a virgin `git clone` produces files owned by the host
# user (UID 1000), with mode 755/644. The container runs as UID 1001 — that's
# "other" relative to UID 1000, and 755/644 denies write. Result: supervisord
# can't open its log file, scheduler can't write its PID, container crash-loops.
#
# The fix follows the templatized convention:
#   - chown -R 1001:jonops-shared  (UID 1001 = container's agent; group is shared
#                                   between host user and container)
#   - dirs 2775                     (rwxrwxr-x + setgid: new files inherit group)
#   - files g+rwX                   (group read/write; preserve exec bit if set)
#   - default ACL group:jonops-shared:rwx (new files created inside container
#                                          stay accessible to host user)
#
# Usage (from project root):
#   sudo bash scripts/setup/fix-perms.sh
# Or, to target a specific project dir:
#   sudo bash scripts/setup/fix-perms.sh /opt/jonops/projects/<biz>/project
#
# Idempotent. Safe to re-run.

set -euo pipefail

PROJECT_DIR="${1:-./project}"
SHARED_GROUP="jonops-shared"
AGENT_UID=1001

if [ ! -d "$PROJECT_DIR" ]; then
  echo "[fix-perms] ERROR: $PROJECT_DIR not found" >&2
  exit 1
fi

if [ "$EUID" -ne 0 ]; then
  echo "[fix-perms] ERROR: must run as root (use 'sudo bash $0 $*')" >&2
  exit 1
fi

# Sanity guards. If the user accidentally passes a path like /opt/jonops or /,
# this script would recurse over multiple businesses' trees and clobber every
# .env file in sight. Refuse unless the target looks like a single business's
# project root.
PROJECT_DIR_RESOLVED=$(realpath "$PROJECT_DIR")

if [ "$(basename "$PROJECT_DIR_RESOLVED")" != "project" ]; then
  echo "[fix-perms] ERROR: target must be a directory named 'project'." >&2
  echo "[fix-perms]        Got: $PROJECT_DIR_RESOLVED" >&2
  echo "[fix-perms]        Expected: /opt/.../<business>/project" >&2
  exit 1
fi

PARENT_DIR=$(dirname "$PROJECT_DIR_RESOLVED")
if [ ! -f "$PARENT_DIR/docker-compose.yml" ] && [ ! -f "$PARENT_DIR/.env" ]; then
  echo "[fix-perms] ERROR: $PARENT_DIR has no docker-compose.yml or .env file." >&2
  echo "[fix-perms]        This doesn't look like a JonOps business directory." >&2
  echo "[fix-perms]        Refusing to recurse — pass an explicit per-business project path." >&2
  exit 1
fi

# Prevent operating on a path so shallow that multiple businesses are below it.
SUBDIRS=$(find "$PROJECT_DIR_RESOLVED" -maxdepth 2 -name "docker-compose.yml" 2>/dev/null | wc -l)
if [ "$SUBDIRS" -gt 0 ]; then
  echo "[fix-perms] ERROR: target contains its own docker-compose.yml descendants." >&2
  echo "[fix-perms]        Refusing — this looks like a shared root, not a single business." >&2
  exit 1
fi

# 1. Ensure the shared group exists.
if ! getent group "$SHARED_GROUP" >/dev/null; then
  echo "[fix-perms] Creating group '$SHARED_GROUP'..."
  groupadd "$SHARED_GROUP"
fi
SHARED_GID=$(getent group "$SHARED_GROUP" | cut -d: -f3)

# 2. Ensure the invoking host user (the one who ran sudo) is in the group,
#    so they can still read/edit the project tree from the host shell.
INVOKING_USER="${SUDO_USER:-}"
if [ -n "$INVOKING_USER" ] && [ "$INVOKING_USER" != "root" ]; then
  if ! id -nG "$INVOKING_USER" | tr ' ' '\n' | grep -qx "$SHARED_GROUP"; then
    echo "[fix-perms] Adding $INVOKING_USER to $SHARED_GROUP group..."
    usermod -aG "$SHARED_GROUP" "$INVOKING_USER"
    echo "[fix-perms] NOTE: $INVOKING_USER must log out + back in for group to take effect."
  fi
fi

echo "[fix-perms] Target: $PROJECT_DIR"
echo "[fix-perms] Pre-state: $(stat -c '%a %u:%g' "$PROJECT_DIR")"

# 3. chown to UID 1001 : jonops-shared.
echo "[fix-perms] chown -R $AGENT_UID:$SHARED_GROUP ..."
chown -R "$AGENT_UID:$SHARED_GROUP" "$PROJECT_DIR"

# 4. Directories: 2775 (setgid bit so new files inherit the group).
echo "[fix-perms] chmod dirs 2775 ..."
find "$PROJECT_DIR" -type d -exec chmod 2775 {} +

# 5. Files: g+rwX preserves exec bit on scripts; ensures group read/write.
echo "[fix-perms] chmod files u+rw,g+rwX,o+rX ..."
find "$PROJECT_DIR" -type f -exec chmod u+rw,g+rwX,o+rX {} +

# 6. Default ACL: new files created inside the container by UID 1001 inherit
#    rwx for the shared group, so host user can still edit them later.
if command -v setfacl >/dev/null; then
  echo "[fix-perms] setfacl default ACL: group:$SHARED_GROUP:rwx ..."
  setfacl -R -d -m "group:$SHARED_GROUP:rwx" "$PROJECT_DIR"
  setfacl -R -m "group:$SHARED_GROUP:rwx" "$PROJECT_DIR"
else
  echo "[fix-perms] WARNING: setfacl not installed; new files may need manual fix later"
  echo "[fix-perms]          Install with: apt-get install -y acl"
fi

# 7. Tighten .env (always 600, even after the chmod above).
if [ -f "$PROJECT_DIR/../.env" ]; then
  chmod 600 "$PROJECT_DIR/../.env"
  echo "[fix-perms] Re-tightened ../.env to 600"
fi

echo "[fix-perms] Done."
echo "[fix-perms] Post-state: $(stat -c '%a %u:%g' "$PROJECT_DIR")"
