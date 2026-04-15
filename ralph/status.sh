#!/usr/bin/env bash
# ralph/status.sh -- Quick liveness + progress check for a running AFK loop.
#
# Useful during an afk-ralph.sh run when:
# - The output file isn't streaming live (Windows/Git Bash buffering)
# - You want to know whether Ralph is working, stuck, or done
# - You want a snapshot of which slice is in progress
#
# Usage:
#   ./ralph/status.sh [prd-issue-number] [max-iterations]
#
# Args:
#   prd-issue-number   defaults to 16 (Stage 1 PRD)
#   max-iterations     optional; if omitted, auto-detected from a running
#                      afk-ralph.sh process via `ps -ef`. Used for the
#                      "X done, Y in progress, Z remaining of N max" summary.
#
# The sandbox name is auto-detected — tries claude-<repo-basename> first,
# then falls back to any running sandbox matching claude-DailyRiff*.
#
# Safe to run from anywhere (main checkout, worktree, or clone). Read-only.

set -u

PRD_ISSUE="${1:-16}"
MAX_ITERATIONS_ARG="${2:-}"
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

# Auto-detect max-iterations from a running afk-ralph.sh process if the user
# didn't pass one as the second argument. Uses ps to find the command line and
# parses the second positional arg. Works under Git Bash on Windows because
# `ps -ef` (ProcFS emulation) shows bash scripts with their args.
MAX_ITERATIONS="${MAX_ITERATIONS_ARG}"
if [[ -z "$MAX_ITERATIONS" ]]; then
  afk_cmdline=$(ps -ef 2>/dev/null | grep -E '[a]fk-ralph\.sh' | head -1 || true)
  if [[ -n "$afk_cmdline" ]]; then
    # Extract the arguments after afk-ralph.sh. Expected: "... afk-ralph.sh <prd> <max>"
    MAX_ITERATIONS=$(echo "$afk_cmdline" | grep -oE 'afk-ralph\.sh[[:space:]]+[0-9]+[[:space:]]+[0-9]+' \
      | awk '{print $NF}' || true)
  fi
fi
# If still unknown, leave as "?" for display.
MAX_DISPLAY="${MAX_ITERATIONS:-?}"

# Detect the workspace hosting the active sandbox (used for git log and git status).
# `docker sandbox ls` prints: NAME AGENT STATE WORKSPACE (workspace may have spaces).
afk_workspace=""
if [[ -n "${SANDBOX_NAME}" ]]; then
  afk_workspace=$(docker sandbox ls 2>/dev/null \
    | awk -v sb="$SANDBOX_NAME" '$1 == sb {sub("^[^ ]+ +[^ ]+ +[^ ]+ +", ""); print}')
fi

echo "${BOLD}=== Ralph AFK status — PRD #${PRD_ISSUE} ===${RESET}"
echo "  repo:    ${REPO}"
echo "  sandbox: ${SANDBOX_NAME}"
echo "  branch:  ${BRANCH}"
echo "  max:     ${MAX_DISPLAY} iteration(s)"
echo ""

# ---- 0. Progress summary (iteration-by-iteration) --------------------------
# Walk the commits on ralph/prd-<n> ahead of origin/master, in the active
# workspace. Group review fix-up commits (message starts with "review:") with
# the preceding main commit. Each main commit = one "done" iteration.
done_count=0
done_lines=()
if [[ -n "$afk_workspace" && -d "$afk_workspace" ]]; then
  if (cd "$afk_workspace" && git rev-parse --verify "$BRANCH" >/dev/null 2>&1); then
    while IFS= read -r sha; do
      [[ -z "$sha" ]] && continue
      subj=$(cd "$afk_workspace" && git log -1 --format='%s' "$sha")
      if [[ "$subj" != review:* ]]; then
        done_count=$((done_count + 1))
        short=$(cd "$afk_workspace" && git rev-parse --short "$sha")
        # Look for "closes #N" or "#N" in the full commit message body,
        # preferring the "closes #N" form. Fall back to any #N. Fall back
        # to the commit subject if no issue reference found.
        full=$(cd "$afk_workspace" && git log -1 --format='%B' "$sha")
        closed_issue=$(echo "$full" | grep -oiE '(closes?|fix(es)?|resolves?)[[:space:]]+#[0-9]+' | grep -oE '#[0-9]+' | head -1)
        if [[ -z "$closed_issue" ]]; then
          closed_issue=$(echo "$full" | grep -oE '#[0-9]+' | head -1)
        fi
        if [[ -n "$closed_issue" ]]; then
          label="closed ${closed_issue}"
        else
          # Trim subject to ~60 chars for a compact description.
          label="\"${subj:0:60}\""
        fi
        done_lines+=("  ${GREEN}✓${RESET} Iteration ${done_count} DONE — ${label}, committed ${short}")
      fi
    done < <(cd "$afk_workspace" && git log --reverse --format='%H' "origin/master..${BRANCH}" 2>/dev/null)
  fi
fi

# Detect in-progress iteration via uncommitted work in the AFK workspace.
in_progress=0
in_progress_area=""
if [[ -n "$afk_workspace" && -d "$afk_workspace" ]]; then
  dirty=$(cd "$afk_workspace" && git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$dirty" -gt 0 ]]; then
    # If there's also a running claude process, iteration is actively in progress.
    # If claude is gone but the tree is dirty, iteration stalled/crashed.
    if docker sandbox exec "$SANDBOX_NAME" ps -eo comm 2>/dev/null | grep -q '^claude$'; then
      in_progress=1
      # Summarise the affected area (apps/web, apps/api, apps/mobile, packages/*).
      in_progress_area=$(cd "$afk_workspace" && git status --porcelain 2>/dev/null \
        | awk '{print $NF}' \
        | grep -oE '^(apps|packages|supabase|docs|ralph)/[^/]+' \
        | sort -u \
        | paste -sd ',' -)
      [[ -z "$in_progress_area" ]] && in_progress_area="files at repo root"
    fi
  fi
fi

# Compute remaining iterations of the max cap, if known.
started=$(( done_count + in_progress ))
if [[ "$MAX_ITERATIONS" =~ ^[0-9]+$ ]]; then
  remaining=$(( MAX_ITERATIONS - started ))
  (( remaining < 0 )) && remaining=0
  summary_line="${BOLD}Progress:${RESET} ${done_count} done, ${in_progress} in progress, ${remaining} not-yet-started of ${MAX_ITERATIONS} max"
else
  summary_line="${BOLD}Progress:${RESET} ${done_count} done, ${in_progress} in progress (max iterations unknown — pass as 2nd arg)"
fi

echo "${BOLD}[0/5] ${summary_line}${RESET}"
if [[ ${#done_lines[@]} -gt 0 ]]; then
  for line in "${done_lines[@]}"; do
    echo "$line"
  done
fi
if [[ "$in_progress" -eq 1 ]]; then
  next_n=$(( done_count + 1 ))
  echo "  ${YELLOW}🔄${RESET} Iteration ${next_n} IN PROGRESS — ${in_progress_area} work continuing, commit pending"
fi
if [[ "$done_count" -eq 0 && "$in_progress" -eq 0 ]]; then
  echo "  ${DIM}· no iterations started yet${RESET}"
fi
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
