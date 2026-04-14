# Universal Dev Toolchain

> The complete pipeline from idea to production. Every tool has one job.
> Nothing is bolted on at the end.
>
> This toolchain is product-agnostic. It works with any product built on
> the Universal Platform Decisions stack (monorepo, FastAPI + Supabase +
> Expo + Next.js).

---

## The Mental Model

Three layers. No overlaps.

```
SPRINT MANAGEMENT     gstack                  Think → Plan → Review → Ship
CODING ENGINE         Ralph (+ Matt Pocock)   Spec → Issues → TDD → Commit
TESTING DISCIPLINE    TDD + CI gates          Red → Green → Refactor → Gate
```

Tests are not a phase. They are the compile check. Code that does not have a
passing test cannot be committed. Code that breaks a coverage gate cannot ship.

---

## The Full Pipeline

### Stage 1 — Idea (gstack)

```
/office-hours        Stress-test the idea before writing code.
                     Six forcing questions. Challenges your framing.
                     Writes a design doc that feeds every downstream step.

/autoplan            One command runs CEO → design → eng review.
                     Only surfaces taste decisions for your approval.
                     Locks architecture, data flow, edge cases, test matrix.
```

**Output:** Locked design doc. No ambiguity before code is written.

---

### Stage 2 — Specification (Matt Pocock skills)

```
/grill-me            Relentless questioning of the idea's assumptions.
                     Run before write-a-prd to catch gaps early.

/write-a-prd         Turns the validated idea into a GitHub issue (the PRD).
                     Engineering spec with acceptance criteria.

/prd-to-issues       Breaks the PRD into vertical-slice sub-issues.
                     Each sub-issue: one logical change, acceptance criteria,
                     and Blocked by dependencies for correct ordering.
```

**Install Matt Pocock skills:**
```bash
npx skills@latest add mattpocock/skills -s grill-me
npx skills@latest add mattpocock/skills -s write-a-prd
npx skills@latest add mattpocock/skills -s prd-to-issues
```

**Sub-issue format:**
```markdown
## Parent PRD
#42

## What to build
[One logical change — vertical slice through the monorepo]

## Acceptance criteria
- [ ] [Specific, testable behavior]
- [ ] [Specific, testable behavior]
- [ ] [Specific, testable behavior]

## Blocked by
- #41    ← Ralph will not touch this until #41 is closed
```

**Output:** GitHub issues with dependencies. Ralph has a clear work queue.

---

### Stage 3 — Implementation (Ralph)

Ralph = **R**epeated **A**utonomous **L**oop for **P**RD **H**andling.
The execution engine. Implements each sub-issue autonomously using TDD.

#### Start here: human-in-the-loop mode

```bash
./ralph/ralph-once.sh 42
```

Implements ONE sub-issue, then stops. Review the output. Run again for the next.
Run this mode for your first 3–5 iterations before going AFK. Trust it first.

#### AFK mode: autonomous

```bash
./ralph/afk-ralph.sh 42 20
```

Runs inside a Docker sandbox, up to 20 iterations, no human in the loop.
Credentials are injected into the sandbox automatically.
When all sub-issues are closed → pushes branch → opens PR.
If max iterations reached without finishing → opens a draft PR.

**Install Ralph:**
```bash
# Install the skill
npx skills@latest add TheCraigHewitt/skills -s ralph

# Copy scripts to your project root
mkdir -p ralph
cp .agents/skills/ralph/afk-ralph.sh ralph/
cp .agents/skills/ralph/ralph-once.sh ralph/
cp .agents/skills/ralph/prompt.md ralph/
cp .agents/skills/ralph/review-prompt.md ralph/
chmod +x ralph/*.sh
```

#### What happens inside one Ralph iteration

```
1.  Fetch PRD issue + all sub-issues from GitHub via gh CLI
2.  Find open sub-issues not blocked by other open issues
3.  Pick ONE (priority: architecture → integration → spikes → features → polish)
4.  TDD — implement using strict red-green-refactor:
      a. Plan behaviors (list what the public interface must do)
      b. RED   — write ONE failing test through the public interface
      c. GREEN — write minimal code to pass that test
      d. Repeat b-c for each behavior
      e. REFACTOR — only after all tests are green
5.  Run the full test suite — fix failures before proceeding
6.  Git commit with descriptive message (imperative mood)
7.  Close the GitHub sub-issue:
      gh issue close <n> --comment "Completed in <sha>. <summary>"
8.  Code review gate runs (review-prompt.md) — fixes applied inline if found
9.  Check: are all sub-issues closed?
      → YES: output COMPLETE, push branch, open PR
      → NO:  start next iteration
```

#### TDD rules Ralph enforces

- ONE test at a time, ONE implementation at a time. Never write all tests first.
- Tests verify behavior through public interfaces. Not implementation details.
- Mock ONLY at system boundaries: external APIs, databases, time, randomness.
  Never mock your own modules.
- Test names describe WHAT the system does, not HOW.
  ✅  "user can checkout with a valid cart"
  ❌  "checkout calls payment service"
- Never commit with a failing test. Ever.
- Never refactor while a test is failing.

#### Sub-issue priority ordering (critical for a monorepo)

Ralph picks in this order, which maps correctly to a monorepo dependency graph:

```
1. Architecture / scaffolding   Types, interfaces, DB models, directory structure
2. Integration points           FastAPI routes, API client regeneration
3. Spikes                       Proving out unknowns (native modules, Supabase Realtime)
4. Feature implementation       Screens, components, business logic
5. Polish                       Docs, edge cases, cleanup
```

This order matters: the SQLAlchemy model must exist before the FastAPI route,
the FastAPI route before the generated TypeScript client,
the client before the mobile hook, the hook before the screen.

---

### Stage 4 — Quality Gates (gstack)

Ralph's built-in review gate runs per-commit (per sub-issue).
gstack's gates run at PR level. Different scopes. Both are required.

```
/review              Staff engineer review on the full branch.
                     Finds production bugs that pass CI.
                     Race conditions, missing error handling, edge cases.
                     Auto-fixes obvious issues. Flags the rest for your decision.

/qa <staging-url>    Opens a real Chromium browser against staging.
                     Explores flows, finds regressions.
                     Auto-generates a Playwright regression test for every bug found.
                     Fixes the bug with an atomic commit, re-verifies.

/ship                Coverage audit against your gates:
                       Python: 85% minimum
                       Mobile: 90% minimum
                       Web:    90% minimum
                     Bootstraps test framework from scratch if missing.
                     Opens PR when gates pass. Blocks if they fail.

/land-and-deploy     Merges the PR. Waits for CI + Railway deploy.
                     Verifies production health before closing.

/canary              Post-deploy monitoring loop.
                     Watches for console errors, performance regressions, failures.
```

**Install gstack:**
```bash
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git \
  ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
```

---

### Stage 5 — CI Enforcement (GitHub Actions)

Tests are not just run locally. Every PR is blocked until CI passes.

```yaml
# .github/workflows/ci.yaml

jobs:
  api:
    - pytest --cov=app --cov-fail-under=85       # Python coverage gate
    - schemathesis run /openapi.json              # Contract tests (spec vs. reality)

  codegen:
    - python tools/codegen/export_openapi.py     # Export spec from running FastAPI
    - npx @hey-api/openapi-ts -i openapi.json \
        -o packages/api-client/src               # Regenerate TypeScript client
    - cd apps/mobile && tsc --noEmit             # Type-check mobile against new client
    - cd apps/web    && tsc --noEmit             # Type-check web against new client

  mobile:
    - cd apps/mobile && jest --coverage \
        --coverageThreshold='{"global":{"lines":90}}'
    - eas build --profile preview --platform all  # EAS preview build

  web:
    - cd apps/web && jest --coverage \
        --coverageThreshold='{"global":{"lines":90}}'
    - cd apps/web && playwright test              # E2E on web
```

The TypeScript type-check step after codegen is a contract test.
If the backend changed something the mobile or web app consumed,
the build fails before any code reaches production.

---

## Testing Layer Map

Every layer has a specific job. No layer duplicates another.

| Layer | Tool | Scope | When it runs |
|---|---|---|---|
| Unit — backend | pytest + pytest-asyncio | Domain services, pure logic | Every commit (Ralph) |
| Unit — mobile | jest-expo + RTL Native | Hooks, stores, components | Every commit (Ralph) |
| Unit — web | jest + RTL | Hooks, stores, components | Every commit (Ralph) |
| Integration — backend | httpx async test client | FastAPI routes + real Supabase test project | Every commit (Ralph) |
| Contract — backend | Schemathesis | OpenAPI spec vs. actual route behavior | CI on every PR |
| E2E — mobile | Maestro | Native iOS/Android flows | CI on every PR |
| E2E — web | Playwright | Next.js user flows | CI on every PR |
| AI-driven QA | agent-browser + gstack /qa | Live staging environment | PR review, pre-deploy |

### What NOT to test

Do not test Supabase's auth logic. Do not test library internals.
Do not test TanStack Query's cache behavior. Those are the library authors' responsibility.

Test your domain logic:
- Can a resource be created when a conflict exists?
- Does the endpoint return 403 when the user does not own the resource?
- Does the UI update when the backend fires a state-change event?

### agent-browser and Playwright — the relationship

These are complementary. They are not competing.

**Playwright** is your scripted regression suite. Tests you write, commit to the repo,
and run in CI on every PR. This is the testing layer.

**agent-browser** is browser automation for AI agents. It gives Claude Code vision
during the `/qa` phase — the ability to navigate staging, click through flows,
and find bugs without a pre-written script. When `/qa` finds a bug, it generates
a **Playwright test** for it. agent-browser is the discovery mechanism.
Playwright is the specification artifact that lives in the repo.

Install agent-browser as a Claude Code skill:
```bash
npx skills add vercel-labs/agent-browser
```

---

## Complete Feature Sprint — End to End

Example: implementing a feature (PRD issue #42)

```
YOU                          TOOL              WHAT HAPPENS
──────────────────────────────────────────────────────────────────────
Describe the feature         /office-hours     Six forcing questions, design doc written
Approve design               /autoplan         CEO + design + eng review runs, plan locked
──────────────────────────────────────────────────────────────────────
Create engineering spec      /grill-me         Assumptions stress-tested
                             /write-a-prd      GitHub issue #42 created
                             /prd-to-issues    Sub-issues created with dependencies:
                                               #43 Domain model + Alembic migration
                                               #44 POST endpoint (FastAPI route)
                                               #45 OpenAPI client regenerated
                                               #46 Mobile service layer
                                               #47 Mobile hook
                                               #48 Mobile screen
                                               #49 Web component
──────────────────────────────────────────────────────────────────────
First iteration (review it)  ralph-once #42    Picks #43 (architecture first)
                                               TDD: domain model + migration
                                               Tests pass, commit, issue closed
You review the output        (you)             Looks good, continue

Go AFK                       afk-ralph #42 20  Iterations 2–7:
                                               #44 route → #45 codegen → #46 service
                                               → #47 hook → #48 screen → #49 web
                                               Per-iteration code review gate runs
                                               All sub-issues closed → PR opened
──────────────────────────────────────────────────────────────────────
PR review                    /review           Staff engineer review on full branch
                                               Race condition found → auto-fixed
AI-driven QA                 /qa staging-url   Real browser, explores flows
                                               Bug found in web component → fixed
                                               Playwright regression test generated
Ship                         /ship             Coverage gates checked (85/90/90)
                                               PR updated, CI triggered
Deploy                       /land-and-deploy  PR merged, Railway deploy verified
Monitor                      /canary           Post-deploy health check passes
──────────────────────────────────────────────────────────────────────
DONE. Feature is in production.
```

---

## Toolchain Install Checklist

```bash
# 1. Claude Code
npm install -g @anthropic-ai/claude-code

# 2. gstack (virtual engineering team)
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git \
  ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup

# 3. Matt Pocock skills (idea → PRD → issues)
npx skills@latest add mattpocock/skills -s grill-me
npx skills@latest add mattpocock/skills -s write-a-prd
npx skills@latest add mattpocock/skills -s prd-to-issues

# 4. Ralph (autonomous TDD coding loop)
npx skills@latest add TheCraigHewitt/skills -s ralph
# Then copy scripts to project root (see Stage 3 above)

# 5. agent-browser (browser vision for Claude Code / gstack /qa)
npx skills add vercel-labs/agent-browser

# 6. GitHub CLI (required by Ralph)
brew install gh && gh auth login

# 7. Docker Desktop (required for AFK Ralph sandbox)
# Download from https://docker.com/products/docker-desktop
# Enable Sandbox support in settings

# 8. EAS CLI (mobile builds)
npm install -g eas-cli && eas login
```

---

## CLAUDE.md — DailyRiff Example

Every Claude Code session starts by reading CLAUDE.md.
This is how the decisions in this document become permanent context.

```markdown
# DailyRiff — Claude Code context

## Architecture
- Monorepo: apps/mobile (Expo), apps/web (Next.js 15), apps/api (FastAPI)
- Shared packages: packages/api-client, packages/shared-types, packages/ui-tokens
- Database: Supabase Postgres via connection pooler (port 6543)
- Auth: Supabase Auth JWT validated in FastAPI middleware
- Audio: react-native-track-player (primary), expo-audio (recording/UI sounds)
- Realtime: Supabase Realtime for presence and DB change events

## Development pipeline
- Ideas → /office-hours → /autoplan → /grill-me → /write-a-prd → /prd-to-issues
- Implementation → ralph-once first, then afk-ralph
- Quality → /review → /qa → /ship → /land-and-deploy → /canary

## TDD rules (enforced by Ralph, enforced by CI)
- Write the failing test before writing any implementation
- One test at a time, one implementation at a time
- Mock only at system boundaries (Supabase, external APIs, time)
- Never mock your own modules
- Never commit with a failing test

## Coverage gates (CI will block if not met)
- Python (FastAPI): 85% minimum
- Mobile (Expo): 90% minimum
- Web (Next.js): 90% minimum

## API contracts
- FastAPI auto-generates /openapi.json
- CI runs codegen: openapi.json → packages/api-client/src
- Both apps/mobile and apps/web import from packages/api-client
- If the backend breaks a type the frontend uses, tsc --noEmit fails in CI

## gstack skills available
/office-hours, /autoplan, /plan-ceo-review, /plan-eng-review,
/plan-design-review, /review, /qa, /qa-only, /ship, /land-and-deploy,
/canary, /cso, /retro, /investigate, /document-release
Use /browse from gstack for all web browsing.

## Key files
- apps/api/alembic/versions/   DB migrations (never skip, never hand-edit prod)
- packages/api-client/src/     Auto-generated — never edit manually
- ralph/prompt.md              Ralph's TDD instructions per iteration
- ralph/review-prompt.md       Ralph's per-iteration code review gate
```

---

*Universal Dev Toolchain v1 — works with gstack, Matt Pocock skills, and Ralph.*
