#!/usr/bin/env bash
set -euo pipefail

# afk-ralph.sh -- Run RALPH in autonomous loop until all sub-issues are closed or max iterations.
# Usage: ./ralph/afk-ralph.sh <prd-issue-number> [max-iterations]
#
# Runs inside a Docker sandbox for isolation.
#
# IMPORTANT: afk-ralph must NOT be run from a git worktree. Git worktrees use a
# `.git` file that points to `<main-repo>/.git/worktrees/<name>`, a path that
# does not exist inside the Docker sandbox (only the workspace directory is
# mounted). Claude-in-the-sandbox then hits a broken git repo and has been
# observed to `git init` a fresh orphan history to unblock itself — every
# commit lands unreachable from master and is lost when the sandbox goes away.
#
# Always run afk-ralph from a standalone clone:
#
#   git clone https://github.com/<org>/<repo>.git ../<repo>-afk-run
#   cd ../<repo>-afk-run
#   ./ralph/afk-ralph.sh <prd-issue> [max-iterations]
#
# The script enforces this with a preflight check below.

PRD_ISSUE="${1:?Usage: afk-ralph.sh <prd-issue-number> [max-iterations]}"
MAX_ITERATIONS="${2:-20}"
REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner')"
REPO_ROOT="$(git rev-parse --show-toplevel)"
PRD_TITLE="$(gh issue view "$PRD_ISSUE" --repo "$REPO" --json title --jq '.title')"

# Preflight: refuse to run from a git worktree. In a worktree, `.git` is a FILE
# containing `gitdir: <main-repo>/.git/worktrees/<name>`. In a normal clone (or
# the main repo itself), `.git` is a DIRECTORY. The Docker sandbox only mounts
# the workspace, so a worktree's gitdir is unreachable from inside the sandbox.
if [[ -f "${REPO_ROOT}/.git" ]]; then
  cat >&2 <<ERRMSG
ERROR: afk-ralph cannot run from a git worktree.

  Detected: ${REPO_ROOT}/.git is a file (worktree marker), not a directory.

The Docker sandbox mounts only the workspace directory, so the worktree's
gitdir (outside the workspace) is unreachable from inside the sandbox.
Claude-in-the-sandbox will hit a broken git repo and has been observed to
\`git init\` a fresh orphan history — every commit lands unreachable from
master and is lost when the sandbox is torn down.

Run from a standalone clone instead:

  git clone https://github.com/${REPO}.git ../$(basename "${REPO_ROOT}")-afk-run
  cd ../$(basename "${REPO_ROOT}")-afk-run
  ./ralph/afk-ralph.sh ${PRD_ISSUE} ${MAX_ITERATIONS}

(ralph-once.sh is unaffected — it runs claude directly on the host and works
fine from a worktree.)
ERRMSG
  exit 2
fi

# Detect default branch dynamically. Falls back to the current branch if the
# remote default is empty (fresh repo with nothing pushed yet). This makes the
# script work on both `main` and `master` defaults without hard-coding.
DEFAULT_BRANCH="$(gh repo view "$REPO" --json defaultBranchRef --jq '.defaultBranchRef.name // ""')"
if [[ -z "$DEFAULT_BRANCH" ]]; then
  DEFAULT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo master)"
  echo "Warning: remote has no default branch set; using '${DEFAULT_BRANCH}' as PR base."
fi

cd "$REPO_ROOT"

# Inject credentials into the Docker sandbox.
# - Claude OAuth: reads ~/.claude/.credentials.json directly (cross-platform;
#   works on Windows + Linux, and on macOS if the file has been exported from Keychain).
#   The previous macOS-only `security find-generic-password` call has been removed.
# - GitHub CLI: gh auth token -> GH_TOKEN env var
inject_sandbox_credentials() {
  local creds_file="${HOME}/.claude/.credentials.json"
  local gh_token

  # Claude OAuth
  if [[ -f "$creds_file" ]]; then
    # shellcheck disable=SC2002
    cat "$creds_file" | docker sandbox exec -i "$SANDBOX_NAME" bash -c \
      'mkdir -p /home/agent/.claude && cat > /home/agent/.claude/.credentials.json' 2>/dev/null \
      && echo "Injected Claude OAuth credentials into sandbox (${creds_file})"
  else
    echo "Warning: ${creds_file} not found; sandbox will not have Claude credentials."
  fi

  # GitHub CLI
  gh_token=$(gh auth token 2>/dev/null) || true
  if [[ -n "$gh_token" ]]; then
    docker sandbox exec "$SANDBOX_NAME" bash -c \
      "grep -q GH_TOKEN /etc/sandbox-persistent.sh 2>/dev/null || echo 'export GH_TOKEN=${gh_token}' >> /etc/sandbox-persistent.sh" 2>/dev/null
    echo "Injected GitHub token into sandbox"
  fi
}

SANDBOX_NAME="claude-$(basename "$REPO_ROOT")"

# Note on custom templates: `docker sandbox save` + `-t <image>` is broken on this
# Docker Desktop version — `docker sandbox create` ignores `--pull-template never` and
# always contacts the registry, so locally-saved templates can't be reused. Instead, we
# bootstrap dev tools into the standard `claude` sandbox on first setup (see
# bootstrap_sandbox_tools below). The sandbox is persistent across `run` invocations,
# so the install only happens once per sandbox lifetime.

# Bootstrap dev tools into a newly-created sandbox. Idempotent — checks for each tool
# and only installs what's missing. Safe to call every run.
bootstrap_sandbox_tools() {
  echo "Bootstrapping sandbox dev tools (idempotent)..."
  docker sandbox exec "$SANDBOX_NAME" bash -c '
    set -e
    needs_install=0
    if ! command -v pnpm >/dev/null 2>&1; then needs_install=1; fi
    if ! command -v supabase >/dev/null 2>&1; then needs_install=1; fi
    node_major=$(node --version 2>/dev/null | sed "s/^v//;s/\..*//")
    if [[ "$node_major" != "22" ]]; then needs_install=1; fi

    if [[ "$needs_install" -eq 0 ]]; then
      echo "  All tools already present (node $(node --version), pnpm $(pnpm --version), supabase $(supabase --version))"
      exit 0
    fi

    echo "  Installing missing tools..."

    if [[ "$node_major" != "22" ]]; then
      echo "  -> Node 22 via NodeSource"
      sudo apt-get remove -y nodejs >/dev/null 2>&1 || true
      curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - >/dev/null 2>&1
      sudo apt-get install -y nodejs >/dev/null 2>&1
    fi

    if ! command -v pnpm >/dev/null 2>&1; then
      echo "  -> pnpm 9"
      sudo npm install -g pnpm@9 >/dev/null 2>&1
    fi

    if ! command -v supabase >/dev/null 2>&1; then
      echo "  -> supabase CLI"
      curl -sL -o /tmp/supabase.tar.gz \
        https://github.com/supabase/cli/releases/latest/download/supabase_linux_amd64.tar.gz
      cd /tmp && tar -xzf supabase.tar.gz && sudo mv supabase /usr/local/bin/
    fi

    echo "  Bootstrap complete: node $(node --version), pnpm $(pnpm --version), supabase $(supabase --version)"
  '
}

echo "Starting AFK RALPH: PRD #${PRD_ISSUE}, $MAX_ITERATIONS max iterations"
echo ""

# --- Host-side Supabase orchestration ---
# Running `supabase start` inside a docker-in-docker sandbox fails with "path not shared"
# because supabase CLI uses bind mounts that the host daemon can't resolve from sandbox paths.
# Workaround: start supabase on the HOST before the loop, and inject host-routable connection
# URLs into the sandbox via env vars. The sandbox reaches the host via `host.docker.internal`.
if command -v supabase >/dev/null 2>&1 && [[ -f supabase/config.toml ]]; then
  if ! supabase status >/dev/null 2>&1; then
    echo "Starting host-side supabase..."
    supabase start 2>&1 | tail -5
  else
    echo "Host-side supabase already running."
  fi
  # Capture the JWT secret and pass sandbox-routable URLs into the sandbox env.
  SUPABASE_JWT_SECRET_HOST="$(supabase status -o env 2>/dev/null | awk -F= '/^JWT_SECRET=/ {print $2}' | tr -d '"')"
  SUPABASE_ANON_KEY_HOST="$(supabase status -o env 2>/dev/null | awk -F= '/^ANON_KEY=/ {print $2}' | tr -d '"')"
  SUPABASE_SERVICE_ROLE_HOST="$(supabase status -o env 2>/dev/null | awk -F= '/^SERVICE_ROLE_KEY=/ {print $2}' | tr -d '"')"
  export SANDBOX_DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:54322/postgres"
  export SANDBOX_SUPABASE_URL="http://host.docker.internal:54321"
  export SANDBOX_SUPABASE_JWT_SECRET="${SUPABASE_JWT_SECRET_HOST}"
  export SANDBOX_SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY_HOST}"
  export SANDBOX_SUPABASE_SERVICE_ROLE="${SUPABASE_SERVICE_ROLE_HOST}"
fi

# Ensure sandbox exists, bootstrap dev tools, and inject OAuth credentials.
if ! docker sandbox ls 2>/dev/null | awk 'NR>1 {print $1}' | grep -q "^${SANDBOX_NAME}$"; then
  echo "Creating sandbox '${SANDBOX_NAME}'..."
  docker sandbox create --name "$SANDBOX_NAME" claude "$REPO_ROOT"
fi
bootstrap_sandbox_tools
inject_sandbox_credentials

# Inject Supabase env vars into sandbox so tests can reach the host supabase.
if [[ -n "${SANDBOX_DATABASE_URL:-}" ]]; then
  docker sandbox exec "$SANDBOX_NAME" bash -c "cat >> /etc/sandbox-persistent.sh <<ENVEOF
export DATABASE_URL='${SANDBOX_DATABASE_URL}'
export SUPABASE_URL='${SANDBOX_SUPABASE_URL}'
export SUPABASE_JWT_SECRET='${SANDBOX_SUPABASE_JWT_SECRET}'
export SUPABASE_ANON_KEY='${SANDBOX_SUPABASE_ANON_KEY}'
export SUPABASE_SERVICE_ROLE='${SANDBOX_SUPABASE_SERVICE_ROLE}'
ENVEOF" 2>/dev/null && echo "Injected host supabase env into sandbox."
fi

# Create feature branch for this PRD
BRANCH="ralph/prd-${PRD_ISSUE}"
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git branch -D "$BRANCH"
fi
git checkout -b "$BRANCH"
echo "Created branch: ${BRANCH}"
echo ""

# On exit: push branch and create PR (or draft PR on failure)
cleanup() {
  local exit_code=$?
  local current_branch
  current_branch=$(git branch --show-current)

  if [[ "$current_branch" != "$BRANCH" ]]; then
    exit "$exit_code"
  fi

  local commits_ahead
  commits_ahead=$(git rev-list --count "${DEFAULT_BRANCH}..${BRANCH}" 2>/dev/null || echo "0")

  if [[ "$commits_ahead" -gt 0 ]]; then
    echo ""
    echo "Pushing branch ${BRANCH} (${commits_ahead} commit(s))..."
    git push --force-with-lease --set-upstream origin "$BRANCH"

    # Check if a PR already exists for this branch
    existing_pr=$(gh pr view "$BRANCH" --repo "$REPO" --json number --jq '.number' 2>/dev/null || echo "")

    if [[ -n "$existing_pr" ]]; then
      echo "PR #${existing_pr} already exists for branch ${BRANCH}."
    elif [[ "$exit_code" -eq 0 ]]; then
      echo "Creating pull request..."
      gh pr create \
        --repo "$REPO" \
        --base "$DEFAULT_BRANCH" \
        --head "$BRANCH" \
        --title "$PRD_TITLE" \
        --body "$(cat <<EOF
Implements PRD #${PRD_ISSUE}.

## PRD
Closes #${PRD_ISSUE}
EOF
)"
    else
      echo "Creating draft pull request (incomplete — max iterations reached)..."
      gh pr create \
        --repo "$REPO" \
        --base "$DEFAULT_BRANCH" \
        --head "$BRANCH" \
        --title "[WIP] $PRD_TITLE" \
        --draft \
        --body "$(cat <<EOF
Partial implementation of PRD #${PRD_ISSUE} (max iterations reached).

## PRD
References #${PRD_ISSUE}
EOF
)"
    fi
  else
    echo "No new commits on ${BRANCH}. Skipping push and PR."
  fi

  echo "Switching back to ${DEFAULT_BRANCH}..."
  git checkout "$DEFAULT_BRANCH"
  exit "$exit_code"
}
trap cleanup EXIT

for ((i=1; i<=MAX_ITERATIONS; i++)); do
  echo "=== RALPH iteration $i / $MAX_ITERATIONS ==="

  # Re-fetch issue state each iteration to get current open/closed status
  echo "Fetching PRD issue #${PRD_ISSUE}..."
  prd_body=$(gh issue view "$PRD_ISSUE" --repo "$REPO" --json number,title,state,body \
    --jq '"# PRD: \(.title) (#\(.number))\nState: \(.state)\n\n\(.body)"')

  echo "Finding sub-issues (excluding hitl-labeled)..."
  # HARD GUARDRAIL: `-label:hitl` excludes human-in-the-loop issues from AFK runs.
  # HITL issues (legal review, prod creds, manual testing, third-party account setup)
  # must never run unattended. To work on a HITL issue, use ralph-once.sh with human
  # supervision, or remove the label after completing the human-required setup.
  sub_issue_numbers=$(gh search issues --repo "$REPO" "Parent PRD #${PRD_ISSUE} -label:hitl" \
    --json number --jq '.[].number' | grep -v "^${PRD_ISSUE}$" | sort -n)

  if [[ -z "$sub_issue_numbers" ]]; then
    echo "No sub-issues found. Nothing to do."
    exit 1
  fi

  # Check if all sub-issues are closed before fetching details
  open_count=0
  for num in $sub_issue_numbers; do
    state=$(gh issue view "$num" --repo "$REPO" --json state --jq '.state')
    if [[ "$state" == "OPEN" ]]; then
      open_count=$((open_count + 1))
    fi
  done

  if [[ "$open_count" -eq 0 ]]; then
    echo "=== RALPH: All sub-issues closed after $((i - 1)) iterations ==="
    exit 0
  fi

  echo "$open_count open sub-issue(s) remaining."

  # Ensure OAuth credentials are available in the sandbox
  inject_sandbox_credentials

  # Fetch each sub-issue's full details, including labels so the prompt-level
  # HITL check has something to match on (belt-and-suspenders with the shell filter above).
  sub_issues=""
  for num in $sub_issue_numbers; do
    detail=$(gh issue view "$num" --repo "$REPO" --json number,title,state,body,labels \
      --jq '"---\n## Sub-issue #\(.number): \(.title)\nState: \(.state)\nLabels: \([.labels[].name] | join(", "))\n\n\(.body)"')
    sub_issues="${sub_issues}\n${detail}"
  done

  # Write the assembled context to a file inside the repo (avoids Windows CLI arg length
  # limits and keeps the file within claude's allowed working dir). Gitignored via ralph/.gitignore.
  ctx_file="ralph/.ctx.md"
  {
    echo "${prd_body}"
    echo ""
    echo "# Sub-issues"
    echo -e "${sub_issues}"
  } > "$ctx_file"

  result=$(docker sandbox run "$SANDBOX_NAME" -- \
    -p \
    --permission-mode bypassPermissions \
    "@ralph/prompt.md
@${ctx_file}

Read the PRD and sub-issues above. Then:
1. Identify which sub-issues are OPEN and not blocked by other OPEN issues.
2. Pick ONE open, unblocked sub-issue to work on (prioritize: architecture > integration > spikes > features > polish).
3. Implement that sub-issue. Keep the change small and focused.
4. Detect and run the project's test suite (check package.json, pyproject.toml, Makefile, Cargo.toml, CLAUDE.md, etc.). Fix any failures.
5. Make a git commit with a descriptive message.
6. Close the sub-issue: gh issue close <number> --repo ${REPO} --comment \"Completed in \$(git rev-parse --short HEAD). <brief summary of what was done>\"
7. If ALL sub-issues are now closed, output <promise>COMPLETE</promise>.
ONLY WORK ON A SINGLE SUB-ISSUE PER ITERATION.")

  echo "$result"
  echo ""

  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    echo "=== RALPH: All work complete after $i iterations ==="
    exit 0
  fi

  # --- Code review gate ---
  echo "--- Code review for iteration $i ---"

  review_result=$(docker sandbox run "$SANDBOX_NAME" -- \
    -p \
    --permission-mode bypassPermissions \
    "@ralph/review-prompt.md

Review the changes from the most recent commit. Follow the review procedure exactly.")

  echo "$review_result"
  echo ""

  if [[ "$review_result" == *"<review>FIXES_APPLIED</review>"* ]]; then
    echo "--- Review: fixes applied, continuing ---"
  else
    echo "--- Review: clean, continuing ---"
  fi
done

echo "=== RALPH: Reached max iterations ($MAX_ITERATIONS) without completion ==="
exit 1
