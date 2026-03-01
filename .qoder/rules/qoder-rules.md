---
trigger: always_on
---

QODER PROJECT RULES (GLOBAL) — CHECKPOINTS + TRUTH-LOCK + VERIFICATION GATES
Version: 3.0
Date: 2026-02-36
Applies to: ALL agents, ALL modules, ALL repos unless overridden by a repo-local addendum.

================================================================================
0) PURPOSE (READ THIS ONCE)
================================================================================
These rules exist to prevent:
- false "DONE" claims
- undocumented assumptions
- silent/uncaptured terminal output
- "fix 10 things then rerun once" chaos
- refactor damage without backups
- repo-structure drift caused by agents inventing folders

If an agent cannot comply, they MUST stop and report status as UNVERIFIED or BLOCKED.

================================================================================
1) STATUS WORDS (ONLY THESE THREE)
================================================================================
Agents may use ONLY these statuses:

1) DONE
   - Truth commands executed AND finished (success/fail)
   - Raw outputs captured (pasted OR written to logs files)
   - Any runtime behavior claims backed by real curl or integration test output
   - If a remote exists AND user expects push: commits exist AND push outputs captured

2) UNVERIFIED
   - Code written but truth commands not executed OR output not captured
   - OR tests/build still failing
   - OR work is "implemented" but not "verified"

3) BLOCKED
   - A specific prerequisite prevents execution (must list exact missing item)
   - Must include reproduction steps and where it fails
   - "environmental" is not accepted without pinpointed proof (see Section 9)

FORBIDDEN WORDING unless status == DONE:
- "complete", "finished", "ready", "production-ready", "shippable", "fully verified"
If status != DONE, say: "Implemented" or "Code written", and keep status UNVERIFIED/BLOCKED.

================================================================================
2) REPO CLASSIFICATION (MANDATORY BEFORE WORK)
================================================================================
Before making structural decisions, the agent MUST classify the repo type using the actual files:

A) Python backend repo indicators:
- requirements.txt OR pyproject.toml
- pytest.ini OR tests/ folder
- alembic.ini OR database/migrations
- app/ folder (FastAPI, etc.)

B) Node/Next frontend repo indicators:
- package-lock.json / pnpm-lock.yaml / yarn.lock
- next.config.js, middleware.ts, tailwind.config.*, postcss.config.*
- src/ or app/ (Next routing)

C) Monorepo indicators:
- multiple lockfiles
- multiple package.json
- backend + frontend folders

RULE:
- Agents MUST NOT invent a new directory structure "because it's standard".
- Agents MUST follow the structure already present in tree output and README(s).
- If the repo has a repo-local addendum, it OVERRIDES structure decisions here.

================================================================================
3) CHECKPOINT METHODOLOGY (MANDATORY)
================================================================================
3.1 Before starting any milestone:
- Read docs/01-main/IMPLEMENTATION_PROGRESS.md (if exists)
- Read latest docs/01-main/MILESTONE_*_CHECKPOINT.md (if exists)
- Read repo-local addendum (if exists):
  - docs/01-main/REPO_RULES_ADDENDUM.md
  - OR .qoder/rules/repo-addendum.md
  - OR .cursor/rules/* (if repo uses Cursor rules)

3.2 After each milestone:
- Create: docs/01-main/MILESTONE_{N}_CHECKPOINT.md
- Update: docs/01-main/IMPLEMENTATION_PROGRESS.md
- If a non-trivial architectural decision was made:
  - Create ADR: docs/01-main/adr/ADR_{YYYYMMDD}_{short_title}.md

3.3 During work:
- Use search first (grep/rg/codebase_search) before opening files
- Only open files you will modify or that directly affect current task
- Update progress tracker incrementally, not only at the end

3.4 Checkpoint template (use this exact structure):
# Milestone/Feature Checkpoint
Date: YYYY-MM-DD
Status: DONE | UNVERIFIED | BLOCKED 

Summary:
- (2–3 sentences)

What was built/changed:
- path:description
- path:description

Key decisions:
- decision + link to ADR if created

Verification evidence:
- Commands run:
  - <command>
  - <command>
- Outputs captured:
  - pasted in chat OR logs/<file>.log
- Result:
  - PASS / FAIL / BLOCKED

Next steps:
- single next command to run OR single next task

Token efficiency note:
- what to read next time (only key files)

================================================================================
3.5 MINIMAL CONTEXT CACHE (MANDATORY — CREDIT / TOKEN CONTROL)
================================================================================
Goal: minimize file reads and context bloat while keeping continuity across agents.

A) THE ONLY "ALLOWED MEMORY" SOURCES
Agents MUST rely on, in this order:
1) docs/01-main/IMPLEMENTATION_PROGRESS.md
2) latest docs/01-main/MILESTONE_*_CHECKPOINT.md
3) relevant ADR(s) if referenced by checkpoint
4) only the specific files being edited in the current task

Agents MUST NOT re-open or re-read large files if the checkpoint already summarizes them.

B) MAXIMUM FILE READ BUDGET (HARD LIMITS)
Per task/milestone, unless user explicitly approves more:
- Max 10 file opens total
- Max 3 "large file" reads (large = >300 lines OR config dumps)
- Unlimited grep/rg/search (search is cheap compared to reading)

If budget is exceeded: agent must justify in WORKING_CACHE.md + checkpoint; status remains UNVERIFIED unless truth commands prove DONE.

C) SEARCH-FIRST RULE (MANDATORY)
Before opening any file, agent MUST:
- run grep/rg/codebase_search for the symbol/path first
- open only the exact file(s) that contain the match needed

D) MICRO-CACHE WRITES (REQUIRED)
During work, agent MUST maintain 2 lightweight cache files:

1) docs/01-main/IMPLEMENTATION_PROGRESS.md (append-only updates)
Must include:
- current milestone number
- what changed today (1–3 bullets)
- next command to run

2) docs/01-main/WORKING_CACHE.md (small, always <150 lines)
This file is the "session handoff cache" and MUST include:
- Repo type: Python/Node/Monorepo
- Truth commands for this repo (exact commands)
- Current status: DONE/UNVERIFIED/BLOCKED + why
- Active modules touched (paths)
- Known failing commands (if any) + last error snippet
- Next single action

RULE: WORKING_CACHE.md must be updated at least once every 60 minutes of work OR at task end.

E) "NO RE-EXPLAIN" RULE
If architecture/process was already documented:
- agent MUST reference checkpoint/ADR instead of rewriting explanation
- repeating long explanations is forbidden unless user asks

F) BLOAT CONTROL
Agents MUST NOT paste huge logs in chat.
Instead:
- write full output to logs/<name>.log
- paste only the failing section (or 30 lines around failure)
- cite the log path

If an agent violates F (spam pastes massive output), status must remain UNVERIFIED.
================================================================================

================================================================================
4) SAFETY RULES (NO DAMAGE)
================================================================================
4.1 File delete policy:
- MUST ask before deleting any file/folder:
  "DELETE REQUEST: <path> — type 'yes' to proceed"
- If user says no: find non-destructive alternative
- No forced deletes quietly (rm -f / Remove-Item -Force / shutil.rmtree)

4.2 Restructure safety protocol:
Before folder restructure:
1) git add -A
2) git stash push -m "pre-refactor auto-stash"
3) COPY (do not move) files to new location
4) Verify content (line count or checksum)
5) Ask before deleting originals (see 4.1)
6) git add -A && commit with clear message
7) Update checkpoint

4.3 Content preservation:
- Never "clean up" or "organize" without explicit approval
- Never delete logs/docs just because they're noisy
- If the repo contains many draft docs, do NOT remove them unless requested

================================================================================
5) TERMINAL OUTPUT RULES (NO INVISIBLE WORK)
================================================================================
5.1 Command executed definition:
A command is NOT considered executed unless:
- the process exits (success OR failure), AND
- output is captured (pasted OR written to logs/*.log)

5.2 Mandatory log fallback:
If terminal output is unreliable (Cursor/Qoder terminal bug), agent MUST:
- create a logs/ folder at repo root
- redirect outputs to logs files
- paste the failing section verbatim plus the log path

Required logs for verification runs:
- logs/alembic.log
- logs/pytest.log
- logs/pnpm_install.log OR logs/npm_install.log OR logs/yarn_install.log
- logs/pnpm_lint.log   OR logs/npm_lint.log   OR logs/yarn_lint.log
- logs/pnpm_typecheck.log (if exists)
- logs/pnpm_build.log  OR logs/npm_build.log  OR logs/yarn_build.log

5.3 Hang protocol (MANDATORY):
If no new output for >60 seconds:
1) Re-run with time measurement AND log capture
2) Isolate the hang source (binary search imports for Python; single-test for Jest)
3) Do NOT label "environmental" until the exact stall point is identified

Pytest hang isolation order:
- python -X importtime -m pytest tests/ --collect-only -q
- python -m pytest -vv -s --maxfail=1 --setup-show
- If still stuck:
  - isolate conftest imports (comment-free binary search by import path)
  - report the exact module import that triggers the stall

================================================================================
6) TRUTH COMMANDS (VERIFICATION GATES)
================================================================================
DONE requires truth commands AND outputs.

6.1 Python backend truth commands (if repo is Python backend):
A) Migrations:
- alembic upgrade head
B) Tests:
- python -m pytest tests/ -v
C) Optional lint/typecheck (ONLY if configured):
- ruff check .
- mypy .

If lint/typecheck are not configured:
- agent may propose adding them
- status cannot become DONE because "not configured"
- status remains UNVERIFIED unless user explicitly says lint/typecheck not required

6.2 Node/Next truth commands (if repo is Node/Next):
Package manager rule (MANDATORY):
- If pnpm-lock.yaml exists: use pnpm ONLY
- Else if package-lock.json exists: use npm ONLY
- Else if yarn.lock exists: use yarn ONLY
- No mixing in one verification run

Truth commands:
A) Install:
- pnpm install  OR npm ci OR yarn install
B) Lint:
- pnpm lint OR npm run lint OR yarn lint
C) Typecheck (if script exists):
- pnpm typecheck OR npm run typecheck OR yarn typecheck
D) Build:
- pnpm build OR npm run build OR yarn build

6.3 Runtime behavior claims (API correctness claims):
If the agent claims a runtime behavior (example: "409 on stale row_version", idempotency replay),
DONE requires ONE of:
- 2 real curl requests showing request + response code/body, OR
- 1 passing integration test covering the behavior with raw output

No runtime evidence => status stays UNVERIFIED even if unit tests pass.

================================================================================
7) FIRST-FAILURE FIX LOOP (NO RANDOM FIXES)
================================================================================
When a truth command fails:
1) Paste FULL output (or log path + failing section)
2) Fix ONLY the first failure
3) Re-run the same command
4) Repeat until green
5) Commit each fix with message:
   - fix: <first failure summary>

Forbidden:
- fixing multiple unrelated failures before rerunning the failing command.