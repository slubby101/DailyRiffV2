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

# Format a duration in seconds as "Xh Ym Zs" / "Ym Zs" / "Zs". Used for
# elapsed-time displays in the progress summary and liveness sections.
fmt_duration() {
  local s="$1"
  if [[ -z "$s" || "$s" -lt 0 ]]; then
    echo "?"
    return
  fi
  local h=$((s / 3600))
  local m=$(( (s % 3600) / 60 ))
  local sec=$((s % 60))
  if [[ "$h" -gt 0 ]]; then
    printf '%dh %dm %ds' "$h" "$m" "$sec"
  elif [[ "$m" -gt 0 ]]; then
    printf '%dm %ds' "$m" "$sec"
  else
    printf '%ds' "$sec"
  fi
}

# Parse `ps etime` format ([[DD-]HH:]MM:SS) into seconds. Used to find how
# long the afk-ralph.sh process has been running as a proxy for run start.
parse_etime_to_sec() {
  local e="$1"
  [[ -z "$e" ]] && { echo 0; return; }
  local days=0 hours=0 minutes=0 seconds=0
  if [[ "$e" == *-* ]]; then
    days="${e%%-*}"; e="${e#*-}"
  fi
  # Now e is [[HH:]MM:]SS
  local parts
  IFS=':' read -ra parts <<< "$e"
  case "${#parts[@]}" in
    3) hours="${parts[0]}"; minutes="${parts[1]}"; seconds="${parts[2]}" ;;
    2) minutes="${parts[0]}"; seconds="${parts[1]}" ;;
    1) seconds="${parts[0]}" ;;
  esac
  # Strip leading zeros to avoid octal parsing.
  hours=$((10#${hours:-0})); minutes=$((10#${minutes:-0})); seconds=$((10#${seconds:-0})); days=$((10#${days:-0}))
  echo $(( days*86400 + hours*3600 + minutes*60 + seconds ))
}

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

# Detect how long the AFK run has been going. Uses `ps etime` on the
# afk-ralph.sh process if it's still running. Falls back to the first
# commit timestamp on the branch (approximate — misses bootstrap time).
# Falls back further to unknown.
now_ts=$(date +%s)
afk_elapsed_sec=""
afk_etime_raw=$(ps -eo etime,cmd 2>/dev/null | grep -E '[a]fk-ralph\.sh' | head -1 | awk '{print $1}' || true)
if [[ -n "$afk_etime_raw" ]]; then
  afk_elapsed_sec=$(parse_etime_to_sec "$afk_etime_raw")
elif [[ -n "$afk_workspace" && -d "$afk_workspace" ]]; then
  first_commit_ts=$(cd "$afk_workspace" && git log --reverse --format='%ct' "origin/master..${BRANCH}" 2>/dev/null | head -1 || true)
  if [[ -n "$first_commit_ts" ]]; then
    afk_elapsed_sec=$(( now_ts - first_commit_ts ))
  fi
fi

echo "${BOLD}=== Ralph AFK status — PRD #${PRD_ISSUE} ===${RESET}"
echo "  repo:    ${REPO}"
echo "  sandbox: ${SANDBOX_NAME}"
echo "  branch:  ${BRANCH}"
echo "  max:     ${MAX_DISPLAY} iteration(s)"
if [[ -n "$afk_elapsed_sec" ]]; then
  if [[ -n "$afk_etime_raw" ]]; then
    echo "  elapsed: $(fmt_duration "$afk_elapsed_sec") (afk-ralph.sh still running)"
  else
    echo "  elapsed: ~$(fmt_duration "$afk_elapsed_sec") (since first commit; run may have ended)"
  fi
else
  echo "  elapsed: ${DIM}(unknown — no afk-ralph.sh process, no commits on branch yet)${RESET}"
fi
echo ""

# ---- 0. Progress summary (iteration-by-iteration) --------------------------
# Walk the commits on ralph/prd-<n> ahead of origin/master, in the active
# workspace. Group review fix-up commits (message starts with "review:") with
# the preceding main commit. Each main commit = one "done" iteration.
done_count=0
done_lines=()
done_durations_sec=()
last_main_ts=""
if [[ -n "$afk_workspace" && -d "$afk_workspace" ]]; then
  if (cd "$afk_workspace" && git rev-parse --verify "$BRANCH" >/dev/null 2>&1); then
    # Track the timestamp of the previous main commit (or the run start) so we
    # can compute per-iteration durations. Iteration 1's start is the afk-ralph
    # run start; iteration N's start is the previous main commit's timestamp.
    if [[ -n "$afk_etime_raw" ]]; then
      prev_ts=$(( now_ts - afk_elapsed_sec ))
    else
      prev_ts=""
    fi
    while IFS= read -r sha; do
      [[ -z "$sha" ]] && continue
      subj=$(cd "$afk_workspace" && git log -1 --format='%s' "$sha")
      commit_ts=$(cd "$afk_workspace" && git log -1 --format='%ct' "$sha")
      if [[ "$subj" != review:* ]]; then
        done_count=$((done_count + 1))
        short=$(cd "$afk_workspace" && git rev-parse --short "$sha")
        # Look for "closes #N" / "fixes #N" / "resolves #N" in the full commit
        # body. Fall back to any "#N" reference. Fall back to the commit subject.
        full=$(cd "$afk_workspace" && git log -1 --format='%B' "$sha")
        closed_issue=$(echo "$full" | grep -oiE '(closes?|fix(es)?|resolves?)[[:space:]]+#[0-9]+' | grep -oE '#[0-9]+' | head -1)
        if [[ -z "$closed_issue" ]]; then
          closed_issue=$(echo "$full" | grep -oE '#[0-9]+' | head -1)
        fi
        if [[ -n "$closed_issue" ]]; then
          label="closed ${closed_issue}"
        else
          label="\"${subj:0:60}\""
        fi
        # Compute iteration duration: commit_ts - previous (prev main commit or run start).
        dur_str=""
        if [[ -n "$prev_ts" ]]; then
          dur_sec=$(( commit_ts - prev_ts ))
          if [[ "$dur_sec" -ge 0 ]]; then
            done_durations_sec+=("$dur_sec")
            dur_str=" ($(fmt_duration "$dur_sec"))"
          fi
        fi
        done_lines+=("  ${GREEN}✓${RESET} Iteration ${done_count} DONE${dur_str} — ${label}, committed ${short}")
        last_main_ts="$commit_ts"
        prev_ts="$commit_ts"
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

echo "${BOLD}[0/7] ${summary_line}${RESET}"
if [[ ${#done_lines[@]} -gt 0 ]]; then
  for line in "${done_lines[@]}"; do
    echo "$line"
  done
fi
if [[ "$in_progress" -eq 1 ]]; then
  next_n=$(( done_count + 1 ))
  # How long has the in-progress iteration been running? Measured from the
  # previous main commit (or run start) to now.
  if [[ -n "$last_main_ts" ]]; then
    running_sec=$(( now_ts - last_main_ts ))
  elif [[ -n "$afk_elapsed_sec" ]]; then
    running_sec="$afk_elapsed_sec"
  else
    running_sec=""
  fi
  running_str=""
  [[ -n "$running_sec" ]] && running_str=" (running $(fmt_duration "$running_sec"))"
  echo "  ${YELLOW}🔄${RESET} Iteration ${next_n} IN PROGRESS${running_str} — ${in_progress_area} work, commit pending"
fi
if [[ "$done_count" -eq 0 && "$in_progress" -eq 0 ]]; then
  echo "  ${DIM}· no iterations started yet${RESET}"
fi

# Compute average iteration duration from done iterations, then project ETA
# for remaining iterations. Skip iteration 1 (includes bootstrap) if we have
# 2+ completed iterations, since iteration 1 is systematically slower.
if [[ "${#done_durations_sec[@]}" -gt 0 && "$MAX_ITERATIONS" =~ ^[0-9]+$ ]]; then
  if [[ "${#done_durations_sec[@]}" -ge 2 ]]; then
    # Average iterations 2..N to exclude iteration 1's bootstrap overhead.
    sum=0; count=0
    for ((i=1; i<${#done_durations_sec[@]}; i++)); do
      sum=$(( sum + done_durations_sec[i] ))
      count=$(( count + 1 ))
    done
    avg_sec=$(( sum / count ))
    avg_label="avg of iter 2+"
  else
    avg_sec="${done_durations_sec[0]}"
    avg_label="iter 1 only (includes bootstrap)"
  fi
  remaining_iters=$(( MAX_ITERATIONS - done_count - in_progress ))
  (( remaining_iters < 0 )) && remaining_iters=0
  # Add remaining time on the in-progress iteration too, if it's running.
  eta_total=$(( avg_sec * remaining_iters ))
  if [[ "$in_progress" -eq 1 && -n "${running_sec:-}" ]]; then
    in_prog_remaining=$(( avg_sec - running_sec ))
    (( in_prog_remaining < 0 )) && in_prog_remaining=0
    eta_total=$(( eta_total + in_prog_remaining ))
  fi
  echo "  ${DIM}ETA: ~$(fmt_duration "$eta_total") remaining at $(fmt_duration "$avg_sec")/iter (${avg_label})${RESET}"
fi
echo ""

# ---- 1. Sandbox liveness + last-write pulse --------------------------------
echo "${BOLD}[1/7] Sandbox liveness${RESET}"
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

  # Last-write pulse: how long since Ralph last touched a file in the workspace?
  # Distinguishes "thinking between tool calls" (<2min) from "potentially stuck"
  # (>10min) while claude is still running. Uses git status + stat (cheap,
  # deterministic) instead of a full workspace find (slow, hangs on big deps).
  # Only captures uncommitted files — misses cases where Ralph has already
  # committed and is thinking, but those are visible via commit count changes.
  if [[ -n "$afk_workspace" && -d "$afk_workspace" ]]; then
    newest=0
    while IFS= read -r file; do
      [[ -z "$file" ]] && continue
      # git status --porcelain format: "XY path" — fields 2..n are the path.
      path=$(echo "$file" | sed -E 's/^[^ ]+ +//')
      full_path="${afk_workspace}/${path}"
      if [[ -e "$full_path" ]]; then
        ts=$(stat -c '%Y' "$full_path" 2>/dev/null || echo 0)
        (( ts > newest )) && newest="$ts"
      fi
    done < <(cd "$afk_workspace" && git status --porcelain 2>/dev/null)
    if [[ "$newest" -gt 0 ]]; then
      stale_sec=$(( now_ts - newest ))
      if (( stale_sec < 120 )); then
        marker="${GREEN}✓${RESET}"
        verdict="working"
      elif (( stale_sec < 600 )); then
        marker="${DIM}·${RESET}"
        verdict="thinking (between tool calls is normal)"
      else
        marker="${YELLOW}⚠${RESET}"
        verdict="possibly stuck — no uncommitted-file writes in >10 min"
      fi
      echo "  ${marker} last uncommitted-file write: $(fmt_duration "$stale_sec") ago — ${verdict}"
    fi
  fi
else
  echo "  ${RED}✗${RESET} sandbox '${SANDBOX_NAME}' is NOT running"
  echo "      (AFK run may be finished, crashed, or not started yet)"
fi
echo ""

# ---- 2. Workspace file activity --------------------------------------------
echo "${BOLD}[2/7] Workspace file activity${RESET}"
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
echo "${BOLD}[3/7] Commits on ${BRANCH}${RESET}"
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
echo "${BOLD}[4/7] Recently closed sub-issues (last 24h, Parent PRD #${PRD_ISSUE})${RESET}"
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
echo "${BOLD}[5/7] Open non-HITL sub-issues${RESET}"
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

# ---- 6. Latest RALPH_DECISIONS.md entry ------------------------------------
echo "${BOLD}[6/7] Latest RALPH_DECISIONS.md entry${RESET}"
# Read the decisions log from the active AFK workspace (or current repo as fallback).
decisions_file=""
if [[ -n "$afk_workspace" && -f "${afk_workspace}/RALPH_DECISIONS.md" ]]; then
  decisions_file="${afk_workspace}/RALPH_DECISIONS.md"
elif [[ -f "${REPO_ROOT}/RALPH_DECISIONS.md" ]]; then
  decisions_file="${REPO_ROOT}/RALPH_DECISIONS.md"
fi
if [[ -n "$decisions_file" ]]; then
  # Extract the last entry by finding the last "### " heading and everything after.
  last_entry=$(awk '/^### / {entry=$0; next} {if (entry) entry = entry "\n" $0} END {print entry}' "$decisions_file")
  if [[ -n "$last_entry" ]]; then
    echo "$last_entry" | head -10 | sed 's/^/  /'
  else
    echo "  ${DIM}· no entries yet — Ralph hasn't logged a decision${RESET}"
  fi
else
  echo "  ${DIM}· RALPH_DECISIONS.md not found (merge PR #64 or create from template)${RESET}"
fi
echo ""

# ---- 7. Run result (visible after the run finishes) -----------------------
echo "${BOLD}[7/7] Run result${RESET}"
# If the sandbox is NOT running anymore, the run is over. Show PR link and
# exit summary. Otherwise note that the run is still in flight.
if docker sandbox ls 2>/dev/null | awk 'NR>1 {print $1, $3}' | grep -q "^${SANDBOX_NAME} running"; then
  if [[ -n "$afk_etime_raw" ]]; then
    echo "  ${DIM}· run still in flight (afk-ralph.sh running for $(fmt_duration "$afk_elapsed_sec"))${RESET}"
  else
    echo "  ${DIM}· sandbox running but no afk-ralph.sh process — manual cleanup may be needed${RESET}"
  fi
else
  # Run is over. Look for a PR opened by cleanup() against this branch.
  if [[ "$REPO" != "unknown" ]]; then
    pr_json=$(gh pr list --repo "$REPO" --head "$BRANCH" --state open --json number,url,isDraft,title --jq '.[0]' 2>/dev/null || echo "")
    if [[ -n "$pr_json" && "$pr_json" != "null" ]]; then
      pr_num=$(echo "$pr_json" | jq -r '.number')
      pr_url=$(echo "$pr_json" | jq -r '.url')
      pr_draft=$(echo "$pr_json" | jq -r '.isDraft')
      pr_title=$(echo "$pr_json" | jq -r '.title')
      if [[ "$pr_draft" == "true" ]]; then
        echo "  ${YELLOW}◐${RESET} Draft PR #${pr_num}: ${pr_title}"
        echo "      ${DIM}${pr_url}${RESET}"
        echo "      ${DIM}(draft = max iterations reached without COMPLETE — review and mark ready)${RESET}"
      else
        echo "  ${GREEN}✓${RESET} Open PR #${pr_num}: ${pr_title}"
        echo "      ${DIM}${pr_url}${RESET}"
      fi
    else
      echo "  ${DIM}· no open PR for ${BRANCH} — run may have completed with no commits, or PR already merged${RESET}"
    fi
  else
    echo "  ${YELLOW}⚠${RESET} gh CLI not available — cannot look up PR"
  fi
fi
echo ""

echo "${DIM}Run again: ./ralph/status.sh [prd-issue] [max-iterations]${RESET}"
