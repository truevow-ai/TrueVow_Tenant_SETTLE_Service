---
trigger: always_on
---

# TrueVow SETTLE Service — Agent Rules

## Last Updated: 2026-06-19

---

## 1. Core Objective

SETTLE is the first attorney-owned settlement database — an ethical alternative to insurance industry tools like Colossus. Its mission is to empower plaintiff attorneys with real, anonymized settlement data so they can negotiate better outcomes for their clients.

Part of TrueVow's 3-product ecosystem: INTAKE (Benjamin AI receptionist) -> LEVERAGE (50-state case intelligence) -> SETTLE (settlement intelligence network).

**Tech Stack:** Python/FastAPI, Supabase PostgreSQL, Redis, OpenTimestamps, Sentry
**Service Port:** 8002 dev / 8004 prod
**Database:** Shared SETTLE DB (not tenant-isolated)
**Auth:** API key-based (Bearer token / X-API-Key header)

---

## 2. Hard Constraints (NEVER Violate)

1. **No PHI/PII collection** — No names, SSNs, DOBs, phone numbers, emails, case numbers, MRNs, addresses, CPT/ICD codes. Enforced by `app/services/anonymizer.py` regex-based detection.
2. **No free-text narratives** — All fields are dropdown/bucketed/enum. Prevents liability language and accidental PHI leakage. Any `TextField` or free-text input is a violation.
3. **No predictive modeling** — Use "historical benchmarks," "descriptive statistics," "aggregated data" — NEVER "predict," "forecast," "will settle for." Bar compliance requirement.
4. **No liability assessment** — Defendant is only a generic category (Individual/Business/Government/Unknown). No "at fault," "negligent," "liable," or fault-percentage fields.
5. **No legal advice** — All outputs include disclaimer language. SETTLE is purely informational.
6. **No empty dashboards** — `IntelligenceGate` enforces n>=50 credibility floor before showing aggregate data. Pilot mode allows n>=10 at state-tier with transparency safeguards per ADR S-2.
7. **No tenant isolation** — SETTLE uses a single shared database for ALL users. Network-effect product — data value increases with sharing.

---

## 3. Status Words (ONLY These Three)

### DONE
- Truth commands executed AND finished (success/fail)
- Raw outputs captured (pasted OR written to log files)
- Any runtime behavior claims backed by real curl or integration test output
- If a remote exists AND user expects push: commits exist AND push outputs captured

### UNVERIFIED
- Code written but truth commands not executed OR output not captured
- OR tests/build still failing
- OR work is "implemented" but not "verified"

### BLOCKED
- A specific prerequisite prevents execution (must list exact missing item)
- Must include reproduction steps and where it fails
- "environmental" is not accepted without pinpointed proof

**FORBIDDEN WORDING** unless status == DONE:
"complete", "finished", "ready", "production-ready", "shippable", "fully verified"
If status != DONE, say: "Implemented" or "Code written", and keep status UNVERIFIED/BLOCKED.

---

## 4. Code Conventions

### Python Style
- 4-space indentation, 88-char line length
- Type hints on all function signatures
- Docstrings on all public functions and classes
- `logging.getLogger(__name__)` for logging (never `print()`)
- `async/await` for all I/O operations
- All table names use `settle_` prefix

### Database Patterns
- Use `get_db()` from `app.core.database` for all database operations — never `supabase` directly
- Never mix sync and async database calls
- Never hardcode credentials — use `app.core.config.settings`

### API Endpoint Patterns
- Register new routers in `app/api/v1/router.py`
- All new endpoints use proper auth
- All new models use Pydantic v2

### Testing Patterns
- Test files in `tests/` directory
- Use `pytest.mark.asyncio` for async tests
- Mock `get_db()` for unit tests
- Follow patterns in `tests/test_estimator.py`
- Test happy path, edge cases, and error cases
- Never skip tests for new features

---

## 5. Truth Commands (MANDATORY Before DONE)

### Full Test Suite
```bash
python -m pytest tests/ -v --tb=short
```

### Targeted Test Commands
```bash
python -m pytest tests/test_<module>.py -v --tb=short
```

### E2E Test Command
```bash
python -m pytest tests/e2e/ -v --tb=short
```

### Current Test Counts
- **Unit tests:** 186/186 passing
- **DOCKET tests:** 23/24 passing
- **E2E tests:** 14 passing

### Runtime Behavior Claims (API Correctness)
If the agent claims a runtime behavior (example: "409 on stale row_version", idempotency replay), DONE requires ONE of:
- 2 real curl requests showing request + response code/body, OR
- 1 passing integration test covering the behavior with raw output

No runtime evidence => status stays UNVERIFIED even if unit tests pass.

### Optional Lint/Typecheck (ONLY if configured)
```bash
ruff check .
mypy .
```
If not configured: status cannot become DONE "because not configured" — status remains UNVERIFIED unless user explicitly says lint/typecheck not required.

---

## 6. Checkpoint Methodology

### 6.1 Before Starting Any Milestone
- Read `docs/01-main/IMPLEMENTATION_PROGRESS.md` (if exists)
- Read latest `docs/01-main/MILESTONE_*_CHECKPOINT.md` (if exists)
- Read repo-local addendum (if exists): `docs/01-main/REPO_RULES_ADDENDUM.md` or `.cursor/rules/*`

### 6.2 After Each Milestone
- Create: `docs/01-main/MILESTONE_{N}_CHECKPOINT.md`
- Update: `docs/01-main/IMPLEMENTATION_PROGRESS.md`
- If a non-trivial architectural decision was made: create ADR in `docs/01-main/adr/ADR_{YYYYMMDD}_{short_title}.md`

### 6.3 Checkpoint Template (use this exact structure)
```
# Milestone/Feature Checkpoint
Date: YYYY-MM-DD
Status: DONE | UNVERIFIED | BLOCKED

Summary:
- (2-3 sentences)

What was built/changed:
- path:description

Key decisions:
- decision + link to ADR if created

Verification evidence:
- Commands run:
  - <command>
- Outputs captured:
  - pasted in chat OR logs/<file>.log
- Result:
  - PASS / FAIL / BLOCKED

Next steps:
- single next command to run OR single next task

Token efficiency note:
- what to read next time (only key files)
```

### 6.4 Minimal Context Cache
**Goal:** Minimize file reads and context bloat while keeping continuity across agents.

**Allowed memory sources (in order):**
1. `docs/01-main/IMPLEMENTATION_PROGRESS.md`
2. Latest `docs/01-main/MILESTONE_*_CHECKPOINT.md`
3. Relevant ADR(s) if referenced by checkpoint
4. Only the specific files being edited in the current task

**File read budget (hard limits per task):**
- Max 10 file opens total
- Max 3 large file reads (>300 lines or config dumps)
- Unlimited grep/rg/search (search is cheap)
- If exceeded: justify in WORKING_CACHE.md + checkpoint; status remains UNVERIFIED unless truth commands prove DONE

**Search-first rule:** Before opening any file, run grep/rg/search for the symbol/path first. Open only exact file(s) containing the match needed.

**Micro-cache writes (required):**

1. `docs/01-main/IMPLEMENTATION_PROGRESS.md` (append-only updates): current milestone number, what changed today (1-3 bullets), next command to run
2. `docs/01-main/WORKING_CACHE.md` (small, always <150 lines): repo type, truth commands, current status + why, active modules touched, known failing commands + last error snippet, next single action. Update at least once every 60 minutes of work OR at task end.

**No-re-explain rule:** If architecture/process was already documented, reference checkpoint/ADR instead of rewriting explanation.

**Bloat control:** Never paste huge logs in chat. Write full output to `logs/<name>.log`, paste only the failing section (or 30 lines around failure), cite the log path. Violation => status remains UNVERIFIED.

---

## 7. First-Failure Fix Loop

1. Paste FULL output (or log path + failing section)
2. Fix ONLY the first failure
3. Re-run the same command
4. Repeat until green
5. Commit each fix with message: `fix: <first failure summary>`

**Forbidden:** Fixing multiple unrelated failures before rerunning the failing command.

---

## 8. Safety Rules

### File Delete Policy
- MUST ask before deleting any file/folder: `DELETE REQUEST: <path> — type 'yes' to proceed`
- If user says no: find non-destructive alternative
- No forced deletes quietly (`rm -f` / `Remove-Item -Force` / `shutil.rmtree`)

### Restructure Safety Protocol
Before folder restructure:
1. `git add -A`
2. `git stash push -m "pre-refactor auto-stash"`
3. COPY (do not move) files to new location
4. Verify content (line count or checksum)
5. Ask before deleting originals (see file delete policy)
6. `git add -A` and commit with clear message
7. Update checkpoint

### Content Preservation
- Never "clean up" or "organize" without explicit approval
- Never delete logs/docs just because they're noisy
- If the repo contains many draft docs, do NOT remove them unless requested

---

## 9. Terminal Output Rules

### Command Executed Definition
A command is NOT considered executed unless:
- The process exits (success OR failure), AND
- Output is captured (pasted OR written to `logs/*.log`)

### Mandatory Log Fallback
If terminal output is unreliable, agent MUST:
- Create a `logs/` folder at repo root
- Redirect outputs to log files
- Paste the failing section verbatim plus the log path

Required logs for verification runs:
- `logs/pytest.log`
- `logs/alembic.log`
- Build/install/lint logs as applicable

### Hang Protocol (MANDATORY)
If no new output for >60 seconds:
1. Re-run with time measurement AND log capture
2. Isolate the hang source (binary search imports for Python; single-test for Jest)
3. Do NOT label "environmental" until the exact stall point is identified

Pytest hang isolation order:
- `python -X importtime -m pytest tests/ --collect-only -q`
- `python -m pytest -vv -s --maxfail=1 --setup-show`
- If still stuck: isolate conftest imports (comment-free binary search by import path), report the exact module import that triggers the stall

---

## 10. Architecture Validation Checklist

Before marking DONE:
- [ ] No PHI/PII collection in new code
- [ ] No free-text narrative fields added
- [ ] No predictive AI language
- [ ] No liability assessment language
- [ ] No legal advice language
- [ ] IntelligenceGate n>=50 floor not lowered (or n>=10 pilot mode per ADR S-2)
- [ ] No tenant isolation added to SETTLE
- [ ] All new endpoints use proper auth
- [ ] All new models use Pydantic v2
- [ ] All new DB operations use `get_db()` (async)
- [ ] All new code has tests
- [ ] All tests pass
- [ ] Documentation updated

---

## 11. Architecture Validation Matrix

| Phase | Feature | C1 (PHI) | C2 (Text) | C3 (Predict) | C4 (Liability) | C5 (Advice) | C6 (n>=50) | C7 (Tenant) | Status |
|---|---|---|---|---|---|---|---|---|---|
| Phase 1 | Internal Verdict DB | PASS | N/A | N/A | PASS | N/A | N/A | PASS | VALIDATED |
| Phase 1 | 17-Filter Search | PASS | N/A | N/A | PASS | N/A | N/A | PASS | VALIDATED |
| Phase 1 | Scraping Pipeline | PASS | N/A | N/A | PASS | N/A | N/A | PASS | VALIDATED |
| Phase 2.1 | Confidence Score | PASS | PASS | PASS | PASS | PASS | PASS | PASS | VALIDATED |
| Phase 2.2 | Advanced Filters | PASS | PASS | PASS | PASS | PASS | PASS | PASS | VALIDATED |
| Phase 2.3 | Carrier Patterns | PASS | PASS | PASS | PASS | PASS | PASS | PASS | VALIDATED |
| Phase 3 | Multiplier Models | PASS | PASS | PASS | PASS | PASS | PASS | PASS | VALIDATED |
| Phase 3 | Overdemand Cliff | PASS | PASS | PASS | PASS | PASS | PASS | PASS | VALIDATED |
| Phase 3 | Override Tracking | PASS | PASS | PASS | PASS | PASS | PASS | PASS | VALIDATED |
| Phase 4 | Outcome Prediction | PASS | PASS | PASS | PASS | PASS | PASS | PASS | VALIDATED |
| Phase 5 | Docket Tracker | PASS | PASS | PASS | PASS | PASS | PASS | PASS | VALIDATED |

### Validation Procedure
1. Read the change description (checkpoint or commit message)
2. Identify which files were modified/created
3. Check each hard constraint against the changes
4. Document pass/fail for each constraint
5. If any constraint fails: BLOCK the change, report specific violation
6. If all constraints pass: update validation matrix, mark VALIDATED

### Update Frequency
- Validate after every phase completion
- Validate after every new feature addition
- Validate after every schema change

---

## 12. Git & Commit Rules

- Only commit when explicitly requested
- Only commit when all tests pass
- Stage only intended files — never commit secrets or API keys
- Never force push
- Never update docs without verifying code first

### Conventional Commit Types
```
feat: new feature
fix: bug fix
refactor: code restructuring
test: adding/updating tests
docs: documentation only
chore: maintenance tasks
```

---

## 13. Mode Switching

- `/mode architect` — Plan first, compare with architecture, hand off to coder
- `/mode coder` — Implement planned tasks, write tests, run truth commands
- `/mode qa` — Test, validate architecture, commit, document

### Architect Forbidden Actions
- NEVER write code
- NEVER assume a library is available without checking
- NEVER propose features that violate hard constraints
- NEVER lower the n>=50 credibility floor without an ADR
- NEVER invent directory structures that don't match existing patterns

### Architect Planning Requirements
Every plan MUST include:
- Objective statement (2-3 sentences)
- Architecture impact analysis (modified/new/deleted files)
- Compliance check (bar-compliance, PHI/PII, predictive language)
- Ordered implementation steps
- Test strategy
- Risk assessment
- Clear handoff prompt for Coder

### Repo Classification (Before Structural Decisions)
Agents MUST classify the repo type using actual files:
- **Python backend:** requirements.txt/pyproject.toml, pytest.ini/tests/, alembic.ini, app/ folder
- **Node/Next frontend:** package-lock.json/pnpm-lock.yaml, next.config.js, src/ or app/
- **Monorepo:** multiple lockfiles, multiple package.json

Agents MUST NOT invent a new directory structure. Follow the structure already present.
