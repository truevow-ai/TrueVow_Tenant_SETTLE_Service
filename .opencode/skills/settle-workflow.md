# SETTLE Service — Three-Mode Workflow & Architecture Knowledge Base

**Last Updated:** 2026-06-19
**When to use:** Every coding session on the SETTLE codebase.

---

## 1. Three-Mode Workflow

### Core Objective (All Modes)

SETTLE is the first attorney-owned settlement database — an ethical alternative to insurance industry tools like Colossus. Its mission is to empower plaintiff attorneys with real, anonymized settlement data so they can negotiate better outcomes for their clients.

### Design Philosophy (HARD CONSTRAINTS — All Modes)

These are non-negotiable. Every plan, implementation, and review MUST respect these:

| Constraint | Rationale / Enforcement |
|---|---|
| No PHI/PII collection | Bar compliance — no names, SSNs, DOB, case numbers, MRN, addresses. Anonymizer service rejects all PII patterns. |
| No free-text narratives | Prevents liability language and accidental PHI leakage. All fields are dropdown/bucketed. |
| No predictive modeling / "AI" | Only descriptive statistics. Never "predict settlements." Use "descriptive statistics" language only. |
| No liability assessment | No "at fault," "negligent," "liable" language. Generic defendant categories only. |
| No legal advice | Purely informational; ranges are historical benchmarks. Disclaimer in all outputs. |
| No empty dashboards | Hard gate: n<50 means all aggregate widgets suppressed. IntelligenceGate enforces n>=50 floor. |
| No tenant isolation | SETTLE is a single shared database — network-effect product. API key auth. |

### Truth Commands (All Modes — MANDATORY)

After every implementation, before marking DONE:

```bash
# Core tests (always run)
python -m pytest tests/test_estimator.py tests/test_intelligence_gate.py tests/test_anonymizer.py tests/test_validator.py -v --tb=short

# Feature tests
python -m pytest tests/test_phase1_phase2.py tests/test_phase2_5.py tests/test_phase3_1.py tests/test_phase3_2.py tests/test_phase3_3.py tests/test_phase3_4_5_6.py tests/test_phase4.py -v --tb=short

# Full suite (final verification)
python -m pytest tests/ -v --tb=short --ignore=tests/test_customer_scenarios.py --ignore=tests/test_automated_integration.py --ignore=tests/test_functional.py --ignore=tests/comprehensive_test_suite.py
```

Status is **UNVERIFIED** until truth commands pass with captured output.

### Mode Switching

- To switch to Architect mode: `/mode architect`
- To switch to Coder mode: `/mode coder`
- To switch to QA mode: `/mode qa`

---

### 1a. Architect Mode

**Role:** Plan, analyze, validate. **NEVER write code.** Output is always a structured plan, gap analysis, or architecture validation report.

#### Planning Workflow

**Step 1: Survey**
- Read `docs/01-main/IMPLEMENTATION_PROGRESS.md` for current status
- Read latest `docs/01-main/MILESTONE_*_CHECKPOINT.md` for context
- Use grep/search to find relevant code before opening files
- Max 10 file opens, max 3 large file reads per task

**Step 2: Analyze**
- Compare proposed feature against core objective and design philosophy
- Identify which existing services/models need modification
- Identify new files needed
- Check for bar-compliance implications
- Check for PHI/PII risks
- Check for conflicts with existing architecture

**Step 3: Plan**

Produce a structured plan with:
1. **Objective** — What are we building and why
2. **Architecture Impact** — Which files change, which new files needed
3. **Compliance Check** — Bar-compliance, PHI/PII, predictive language review
4. **Implementation Steps** — Ordered tasks for the Coder agent
5. **Test Strategy** — What tests need to be written/updated
6. **Risk Assessment** — What could go wrong, how to mitigate
7. **Handoff** — Clear prompt for the Coder agent

**Step 4: Validate (Post-Implementation)**

When the Coder and QA agents complete work:
1. Read the checkpoint file
2. Verify the implementation matches the plan
3. Check that all truth commands pass
4. Verify documentation is updated
5. Approve or request fixes

#### Plan Output Format

```markdown
# Architecture Plan: [Feature Name]

## Objective
[2-3 sentences]

## Architecture Impact
- Modified files: [list]
- New files: [list]
- Deleted files: [none or list with justification]

## Compliance Check
- Bar-compliance: [PASS/FAIL + notes]
- PHI/PII risk: [NONE/LOW/MEDIUM/HIGH + notes]
- Predictive language: [CLEAN/NEEDS REFRAMING + notes]

## Implementation Steps
1. [Step 1]
2. [Step 2]
...

## Test Strategy
- New tests: [list]
- Modified tests: [list]
- Truth commands: [list]

## Risk Assessment
- [Risk 1] -> [Mitigation]
- [Risk 2] -> [Mitigation]

## Handoff to Coder
[Clear, specific prompt for the Coder agent]
```

#### Architect Anti-Patterns

- **Never write code** — that's the Coder agent's job
- **Never assume a library is available** — check existing imports first
- **Never propose predictive AI features** without descriptive reframing
- **Never suggest PHI collection** — even if "useful"
- **Never propose tenant isolation for SETTLE** — it's a shared database
- **Never lower the n>=50 credibility floor** without written ADR
- **Never invent directory structures** — follow existing patterns
- **Never re-explain architecture** if checkpoint already covers it

---

### 1b. Coder Mode

**Role:** Implement tasks specified by the Architect agent. Write code, tests, and documentation. Run truth commands after every change.

#### Code Conventions

**Python Style:**
- Follow existing patterns in `app/` directory
- Use Pydantic v2 for all models
- Use `async/await` for all database operations
- Use `logging.getLogger(__name__)` for logging
- Type hints on all function signatures
- Docstrings on all public functions and classes
- No comments unless explicitly requested

**Database:**
- Use `get_db()` from `app.core.database` for async database access
- All table names use `settle_` prefix
- Soft-delete pattern: `deleted_at`, `deleted_by` columns
- Optimistic locking: `row_version` column
- UUIDs for all primary keys

**API Endpoints:**
- Use FastAPI router pattern in `app/api/v1/endpoints/`
- Register routers in `app/api/v1/router.py`
- Use dependency injection for auth (`require_admin`, `require_any_auth`)
- Return Pydantic models as response types
- Use `HTTPException` for error responses

**Testing:**
- Use pytest with pytest-asyncio
- Test files in `tests/` directory
- Mock `get_db()` for unit tests
- Follow existing test patterns in `tests/test_estimator.py`

#### Implementation Workflow

**Step 1: Receive Plan**
- Read the Architect's plan
- Understand the objective, architecture impact, and compliance requirements
- Identify which files to modify and which to create

**Step 2: Context Gathering**
- Read ONLY the files you will modify (max 10 file opens)
- Use grep/search to find relevant symbols before opening files
- Read existing test files for similar functionality

**Step 3: Implement**
- Write code following existing conventions
- Write tests alongside code
- Update models if schema changes
- Update router if new endpoints added
- Update documentation if API changes

**Step 4: Verify**
- Run truth commands (see top-level section)
- Fix first failure only, re-run, repeat
- All tests must pass before marking DONE

**Step 5: Document**
- Update `docs/01-main/IMPLEMENTATION_PROGRESS.md`
- Create/update `docs/01-main/MILESTONE_*_CHECKPOINT.md`
- Update `docs/01-main/WORKING_CACHE.md`
- Create ADR if non-trivial architectural decision made

#### Common Code Patterns

**New Service:**
```python
"""
Service Name -- Brief description.
"""
import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)

class ServiceResponse(BaseModel):
    """Response model."""
    field: str = Field(..., description="Description")

async def service_function(param: str) -> ServiceResponse:
    """Function description."""
    db = await get_db()
    # Implementation
    return ServiceResponse(field="value")
```

**New API Endpoint:**
```python
"""
Endpoint Name -- Brief description.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import require_any_auth
from app.services import service_module

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prefix", tags=["tag"])

@router.get("/endpoint", response_model=ResponseModel)
async def get_endpoint(
    param: str = Query(None),
    auth=Depends(require_any_auth),
):
    """Endpoint description."""
    try:
        result = await service_module.function(param)
        return result
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**New Test:**
```python
"""
Tests for Feature Name.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import service_module

class TestFeatureName:
    """Tests for feature."""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        """Test successful case."""
        with patch("app.services.service_module.get_db") as mock_get_db:
            mock_get_db.return_value = MagicMock()
            result = await service_module.function("param")
            assert result is not None
```

#### Coder Anti-Patterns

- **Never use `supabase` directly** — use `get_db()` from `app.core.database`
- **Never mix sync and async** database calls
- **Never use `print()`** — use `logging.getLogger(__name__)`
- **Never hardcode credentials** — use `app.core.config.settings`
- **Never skip tests** — every new feature needs tests
- **Never claim DONE without truth commands** — status stays UNVERIFIED
- **Never fix multiple failures at once** — fix first failure, re-run, repeat
- **Never delete files without asking** — follow restructure safety protocol

---

### 1c. QA Mode

**Role:** Verify implementations, run truth commands, fix test failures, commit to git, and update documentation.

#### QA Workflow

**Step 1: Verify Implementation**
- Read the Architect's plan
- Read the Coder's checkpoint file
- Verify the implementation matches the plan
- Check that all files were created/modified correctly

**Step 2: Run Truth Commands**
- Run full test suite (see top-level truth commands section)
- If any failures, fix FIRST failure only, re-run, repeat

**Step 3: Fix Test Failures**

When a truth command fails:
1. Paste FULL output (or log path + failing section)
2. Fix ONLY the first failure
3. Re-run the same command
4. Repeat until green
5. Commit each fix with message: `fix: <first failure summary>`

**Step 4: Git Commit**

When all tests pass:
```bash
git add -A
git commit -m "feat: <feature description>

- Summary of changes
- Files modified
- Tests added/updated"
```

**Step 5: Update Documentation**
- Update `docs/01-main/IMPLEMENTATION_PROGRESS.md`
- Create/update `docs/01-main/MILESTONE_*_CHECKPOINT.md`
- Update `docs/01-main/WORKING_CACHE.md`
- Create ADR if non-trivial architectural decision was made

**Step 6: Architecture Validation**
- Verify the change respects all hard constraints
- Check for PHI/PII risks
- Check for predictive language violations
- Check for bar-compliance issues
- Document validation result in checkpoint

#### Architecture Validation Checklist

Before marking DONE, verify:

- [ ] No PHI/PII collection in new code
- [ ] No free-text narrative fields added
- [ ] No predictive AI language ("predict", "forecast", "will settle for")
- [ ] No liability assessment language ("at fault", "negligent", "liable")
- [ ] No legal advice language
- [ ] IntelligenceGate n>=50 floor not lowered
- [ ] No tenant isolation added to SETTLE
- [ ] All new endpoints use proper auth dependencies
- [ ] All new models use Pydantic v2
- [ ] All new database operations use `get_db()` (async)
- [ ] All new code has tests
- [ ] All tests pass
- [ ] Documentation updated

#### Test Coverage (Current: 186/186 passing)

| Test File | Module(s) Covered | Status |
|---|---|---|
| `test_estimator.py` | Estimator engine | PASSING |
| `test_intelligence_gate.py` | Intelligence gate, hierarchical fallback | PASSING |
| `test_anonymizer.py` | PHI/PII anonymizer | PASSING |
| `test_validator.py` | Input validation | PASSING |
| `test_phase1_phase2.py` | Confidence score, carrier patterns, verdict search models | PASSING |
| `test_phase2_5.py` | Advanced search filters | PASSING |
| `test_phase3_1.py` | Multiplier model layer | PASSING |
| `test_phase3_2.py` | Overdemand cliff detection | PASSING |
| `test_phase3_3.py` | Override tracking | PASSING |
| `test_phase3_4_5_6.py` | Weekly digest, recency weighting, firm-wide yield | PASSING |
| `test_phase4.py` | Outcome distribution, trend reports | PASSING |
| `test_e2e_integration.py` | End-to-end integration (14 tests) | PASSING |

#### Git Commit Convention

Types: `feat` (new feature), `fix` (bug fix), `test` (test additions/changes), `docs` (documentation), `refactor` (no behavior change), `chore` (maintenance)

---

## 2. Architecture Knowledge Base (Current State: 2026-06-19)

### TrueVow 3-Product Ecosystem

| Product | Description | Pricing |
|---|---|---|
| **INTAKE (Benjamin)** | AI receptionist for law firms | $499 / $1,299 / $1,999/mo |
| **LEVERAGE** | 50-state PI Case Intelligence. 34 endpoints. Damages, SOL, compliance. | $99/mo ecosystem |
| **SETTLE** | Settlement Intelligence Network. Comparable case matching. Attorney-owned settlement database. | Port 8002 dev / 8004 prod |

### 5-Stage Attorney Journey

```
Stage 1: INTAKE (lead capture)
  -> Stage 2: LEVERAGE (compliance -- SOL, jurisdiction, filing rules)
    -> Stage 3: LEVERAGE (damages -- economic calculations, medical costs)
      -> Stage 4: LEVERAGE + SETTLE (negotiation -- demand letters, carrier intelligence, comparable settlements)
        -> Stage 5: SETTLE (network effect -- industry-wide settlement intelligence)
```

### Tech Stack

Python/FastAPI, Supabase PostgreSQL, Redis, OpenTimestamps, Sentry

### Three-Database Architecture

1. **Tenant databases** (per-firm isolated) -- intake data
2. **SaaS Admin DB** -- central `users` table, billing, tenants
3. **SETTLE DB** -- shared settlement data, references `users.user_id` without FK constraints

### Current Implementation Status

**ALL Phases 1-5: DONE. 186/186 unit tests passing. 23/24 DOCKET tests. 14 E2E tests ready.**

| Phase | Scope | Status |
|---|---|---|
| Phase 1 | Core estimation engine, intelligence gate, contribution workflow, anonymizer, anomaly detection, reputation, injury classifier, PDF reports, API key auth, Stripe billing, S3 storage, email notifications, Sentry | DONE |
| Phase 2 | Internal verdict research (17-filter), demand confidence score (7 factors), advanced search (9 filters), carrier pattern analytics | DONE |
| Phase 2.5 | Advanced search filters expansion | DONE |
| Phase 3.1 | Multiplier model layer (SettleCase Models 01-03) | DONE |
| Phase 3.2 | Overdemand cliff detection | DONE |
| Phase 3.3 | Override tracking | DONE |
| Phase 3.4-3.6 | Weekly intelligence digest, recency weighting, firm-wide yield analytics | DONE |
| Phase 4 | Outcome distribution, trend reports (descriptive framing) | DONE |
| Phase 5 | DOCKET-Service scaffolded (23/24 tests) | DONE |

### Service Layer (22+ modules at `app/services/`)

| Module | File(s) | Description |
|---|---|---|
| Estimator | `estimator.py` | Percentile + 3-tier multiplier + recency weighting settlement range engine |
| Intelligence Gate | `intelligence_gate.py` | Hierarchical gate: county (n>=50) -> state (n>=10 pilot) -> suppressed |
| Confidence Score | `confidence_score.py` | 7-factor weighted scoring (10-95), customer-facing 0-100 |
| Injury Classifier | `injury_classifier/` (6 modules) | Deterministic 17-tag classifier |
| Carrier Patterns | `carrier_patterns.py` | Descriptive carrier behavior analytics |
| Outcome Distribution | `outcome_distribution.py` | Settlement outcome distribution analysis |
| Overdemand Cliff | `overdemand_cliff.py` | Overdemand cliff detection |
| Override Tracking | `override_tracking.py` | Attorney override tracking and analysis |
| Reputation Service | `reputation_service.py` | Trust score calculation (4 tiers) |
| Anomaly Detector | `anomaly_detector.py` | 6 anomaly checks on contributions |
| Trend Reports | `trend_reports.py` | Trend analysis and reporting |
| Weekly Digest | `weekly_digest.py` | Weekly intelligence digest generation |
| Verdict Search | `verdict_search.py` | Internal verdict search (17 filters, admin-only) |
| Contributor | `contributor.py` | Contribution workflow |
| Anonymizer | `anonymizer.py` | PHI/PII detection and sanitization |
| Validator | `validator.py` | Input validation service |
| PDF Generator | `reports/pdf_generator.py` | 4-page PDF generation (WeasyPrint) |
| Stripe Billing | `billing/stripe_service.py` | Stripe billing integration |
| Email Notifications | `notifications/email_service.py` | Resend email notifications |
| S3 Storage | `storage/s3_service.py` | AWS S3 file storage |
| Platform Integration | `integrations/platform/client.py` | Platform integration client |
| Internal Ops | `integrations/internal_ops/client.py` | Internal operations integration |

### API Endpoints (10 files, 40+ endpoints)

| Group | File | Prefix | Key Endpoints |
|---|---|---|---|
| Query | `query.py` | `/api/v1/query` | `POST /estimate`, `GET /health` |
| Contribute | `contribute.py` | `/api/v1/contribute` | `POST /submit`, `GET /stats` |
| Reports | `reports.py` | `/api/v1/reports` | `POST /generate`, `GET /template` |
| Waitlist | `waitlist.py` | `/api/v1/waitlist` | `POST /join`, admin CRUD |
| Stats | `stats.py` | `/api/v1/stats` | `/founding-members`, `/database` |
| Admin | `admin.py` | `/api/v1/admin` | Contributions, founding members, API keys, analytics |
| Carrier Analytics | `carrier_analytics.py` | `/api/v1/analytics` | `/carrier-patterns` |
| Verdicts | `verdicts.py` | `/api/v1/internal/verdicts` | Search, stats, CRUD, scrape jobs (admin-only) |
| Trend Reports | `trend_reports.py` | `/api/v1/trends` | Trend analysis endpoints |
| Override Tracking | `override_tracking.py` | `/api/v1/overrides` | Override tracking endpoints |

### Key Files Reference

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app setup, lifespan, CORS |
| `app/core/config.py` | Environment configuration (SETTLE_ prefix) |
| `app/core/auth.py` | API key authentication, access levels |
| `app/core/database.py` | Supabase REST client (httpx-based) |
| `app/core/security.py` | API key generation, hashing, rate limiting |
| `app/api/v1/router.py` | Router registration |
| `app/models/case_bank.py` | Pydantic models for contributions, estimates |
| `app/models/verdicts.py` | Pydantic models for internal verdicts |
| `database/schemas/settle_supabase.sql` | Production DB schema |
| `database/schemas/settle_verdicts_internal.sql` | Internal verdict DB schema |
| `docs/01-main/IMPLEMENTATION_PROGRESS.md` | Implementation status tracker |
| `docs/01-main/WORKING_CACHE.md` | Working memory across sessions |
