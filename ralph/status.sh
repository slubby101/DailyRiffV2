#!/usr/bin/env bash
# ralph/status.sh -- Quick liveness + progress check for a running AFK loop.
#
# Useful during an afk-ralph.sh run when:
# - The output file isn't streaming live (Windows/Git Bash buffering)
# - You want to know whether Ralph is working, stuck, or done
# - You want a snapshot of which slice is in progress
#
# Usage:
#   ./ralph/status.sh [prd-issue-number]
#
# If no argument given, defaults to 16 (Stage 1 PRD). Pass a different number
# for a different PRD. The script auto-detects the sandbox name from the
# current repo root, the same way afk-ralph.sh does.
#
# Safe to run from anywhere (main checkout, worktree, or clone). Read-only.

set -u

PRD_ISSUE="${1:-16}"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
REPO_BASENAME="$(basename "$REPO_ROOT")"
BRANCH="ralph/prd-${PRD_ISSUE}"
REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || echo "unknown")"

# Sandbox detection: prefer the one matching this checkout (claude-<repo-basename>),
# but fall back to any running sandbox whose name starts with claude-DailyRiff*.
# This matters when running status from a different worktree/clone than the one
# hosting the active AFK run (e.g., running ./ralph/status.sh from main while
# afk-ralph.sh runs from ../DailyRiffV2-afk-run).
SANDBOX_NAME="claude-${REPO_BASENAME}"
if ! docker sandbox ls 2>/dev/null | awk 'NR>1 {print $1, $3}' | grep -q "^${SANDBOX_NAME} running"; then
  # Local sandbox not running — look for any running claude sandbox matching this project.
  candidate=$(docker sandbox ls 2>/dev/null \
    | awk 'NR>1 && $3 == "running" {print $1}' \
    | grep -i "claude-dailyriff" | head -1)
  if [[ -n "$candidate" ]]; then
    echo "# note: sandbox '${SANDBOX_NAME}' not running; using '${candidate}' instead" >&2
    SANDBOX_NAME="$candidate"
  fi
fi

# Colors — use tput when available, fall back to raw ANSI.
if command -v tput >/dev/null 2>&1 && [[ -t 1 ]]; then
  BOLD=$(tput bold); DIM=$(tput dim); GREEN=$(tput setaf 2); YELLOW=$(tput setaf 3); RED=$(tput setaf 1); CYAN=$(tput setaf 6); RESET=$(tput sgr0)
else
  BOLD=""; DIM=""; GREEN=""; YELLOW=""; RED=""; CYAN=""; RESET=""
fi

echo "${BOLD}=== Ralph AFK status — PRD #${PRD_ISSUE} ===${RESET}"
echo "  repo:    ${REPO}"
echo "  sandbox: ${SANDBOX_NAME}"
echo "  branch:  ${BRANCH}"
echo ""

# ---- 1. Sandbox liveness ---------------------------------------------------
echo "${BOLD}[1/5] Sandbox liveness${RESET}"
if docker sandbox ls 2>/dev/null | awk 'NR>1 {print $1, $3}' | grep -q "^${SANDBOX_NAME} running"; then
  echo "  ${GREEN}✓${RESET} sandbox '${SANDBOX_NAME}' is running"

  # Top-5 processes inside the sandbox by CPU.
  top_procs=$(docker sandbox exec "$SANDBOX_NAME" ps -eo pid,pcpu,pmem,comm --sort=-pcpu 2>/dev/null | head -6)
  if echo "$top_procs" | grep -qE "^\s*[0-9]+\s+[0-9.]+\s+[0-9.]+\s+claude"; then
    echo "  ${GREEN}✓${RESET} claude process is running (top processes by CPU):"
    echo "$top_procs" | sed 's/^/      /'
  else
    echo "  ${YELLOW}⚠${RESET} no 'claude' process in top-5. Either iteration finished or Ralph stopped."
    echo "$top_procs" | sed 's/^/      /'
  fi
else
  echo "  ${RED}✗${RESET} sandbox '${SANDBOX_NAME}' is NOT running"
  echo "      (AFK run may be finished, crashed, or not started yet)"
fi
echo ""

# Detect the workspace hosting the active sandbox (used by sections 2 and 3).
# `docker sandbox ls` prints: NAME AGENT STATE WORKSPACE (workspace may have spaces).
afk_workspace=""
if [[ -n "${SANDBOX_NAME}" ]]; then
  afk_workspace=$(docker sandbox ls 2>/dev/null \
    | awk -v sb="$SANDBOX_NAME" '$1 == sb {sub("^[^ ]+ +[^ ]+ +[^ ]+ +", ""); print}')
fi

# ---- 2. Workspace file activity --------------------------------------------
echo "${BOLD}[2/5] Workspace file activity${RESET}"
# Prefer the AFK workspace if detected; fall back to current REPO_ROOT.
status_dir="${afk_workspace:-$REPO_ROOT}"
if [[ -d "${status_dir}/.git" ]] || [[ -f "${status_dir}/.git" ]]; then
  dirty_count=$(cd "$status_dir" && git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$dirty_count" -gt 0 ]]; then
    echo "  ${GREEN}✓${RESET} ${dirty_count} modified/new files in workspace — Ralph is mid-implementation"
    echo "      ${DIM}(workspace: ${status_dir})${RESET}"
    (cd "$status_dir" && git status --short 2>/dev/null | head -10) | sed 's/^/      /'
    if [[ "$dirty_count" -gt 10 ]]; then
      echo "      ${DIM}... and $((dirty_count - 10)) more${RESET}"
    fi
  else
    echo "  ${DIM}·${RESET} working tree clean — Ralph is between tool calls, or iteration just committed"
  fi
else
  echo "  ${YELLOW}⚠${RESET} no git repo detected at ${status_dir}"
fi
echo ""

# ---- 3. Branch commits (in the active AFK workspace) -----------------------
echo "${BOLD}[3/5] Commits on ${BRANCH}${RESET}"
base="origin/master"
if [[ -n "$afk_workspace" && -d "$afk_workspace" ]]; then
  if (cd "$afk_workspace" && git rev-parse --verify "$BRANCH" >/dev/null 2>&1); then
    n=$(cd "$afk_workspace" && git rev-list --count "${base}..${BRANCH}" 2>/dev/null || echo 0)
    if [[ "$n" -gt 0 ]]; then
      echo "  ${GREEN}✓${RESET} ${BRANCH} in ${afk_workspace}: ${n} commit(s) ahead of ${base}"
      (cd "$afk_workspace" && git log --oneline "${base}..${BRANCH}" 2>/dev/null | head -10) | sed 's/^/      /'
    else
      echo "  ${DIM}·${RESET} ${BRANCH} in active workspace: 0 commits ahead of ${base}"
      echo "      ${DIM}(iteration 1 hasn't committed yet, or a just-merged PR reset the branch)${RESET}"
    fi
  else
    echo "  ${YELLOW}⚠${RESET} ${BRANCH} not found in active workspace (${afk_workspace})"
  fi
else
  # Fallback: check current repo and remote.
  if git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
    n=$(git rev-list --count "${base}..origin/${BRANCH}" 2>/dev/null || echo 0)
    if [[ "$n" -gt 0 ]]; then
      echo "  ${GREEN}✓${RESET} origin/${BRANCH}: ${n} commit(s) (pushed by a prior or completed run)"
      git log --oneline "${base}..origin/${BRANCH}" 2>/dev/null | head -10 | sed 's/^/      /'
    fi
  else
    echo "  ${DIM}·${RESET} no active workspace detected and origin/${BRANCH} doesn't exist yet"
  fi
fi
echo ""

# ---- 4. Recently closed sub-issues -----------------------------------------
echo "${BOLD}[4/5] Recently closed sub-issues (last 24h, Parent PRD #${PRD_ISSUE})${RESET}"
if [[ "$REPO" != "unknown" ]]; then
  closed=$(gh search issues --repo "$REPO" "Parent PRD #${PRD_ISSUE} state:closed" \
    --json number,title,closedAt \
    --jq '[.[] | select(.closedAt > (now - 86400 | todate))] | sort_by(.closedAt) | reverse | .[] | "  \(.closedAt[11:19]) #\(.number) \(.title)"' 2>/dev/null)
  if [[ -n "$closed" ]]; then
    echo "$closed"
  else
    echo "  ${DIM}·${RESET} none closed in the last 24h"
  fi
else
  echo "  ${YELLOW}⚠${RESET} gh CLI not available or not authenticated"
fi
echo ""

# ---- 5. Open sub-issue pool (what Ralph has to work with) ------------------
echo "${BOLD}[5/5] Open non-HITL sub-issues${RESET}"
if [[ "$REPO" != "unknown" ]]; then
  open_count=$(gh search issues --repo "$REPO" "Parent PRD #${PRD_ISSUE} -label:hitl" \
    --json number,state --jq '[.[] | select(.state == "open")] | length' 2>/dev/null)
  hitl_count=$(gh search issues --repo "$REPO" "Parent PRD #${PRD_ISSUE} label:hitl" \
    --json number,state --jq '[.[] | select(.state == "open")] | length' 2>/dev/null)
  echo "  ${CYAN}${open_count}${RESET} open non-HITL sub-issue(s) remaining in Ralph's pool"
  echo "  ${DIM}${hitl_count} open HITL sub-issue(s) excluded from AFK runs${RESET}"
else
  echo "  ${YELLOW}⚠${RESET} gh CLI not available or not authenticated"
fi
echo ""

echo "${DIM}Run again: ./ralph/status.sh [prd-issue]${RESET}"
