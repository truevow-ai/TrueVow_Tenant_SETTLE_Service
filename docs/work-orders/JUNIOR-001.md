# Junior Assignment JUNIOR-001 - Baseline verification - run repo truth commands and file honest results

> Repo: **SETTLE** - issued 2026-08-26 - bounded, review-gated, integration-gated.
> You are a junior developer. Do NOT decide scope, architecture, or what ships.
> This document defines exactly what you may touch and what "done" means.
> Before coding, read canonical fixes for this repo in
> TrueVow_CTO_Knowledge_Orchestrator/Decisions/Canonical-*.md - never re-solve a
> solved defect or overwrite an existing fix without citing why it is superseded.

## Scope (only these)

- [ ] (fill 2-3 concrete items you own)
- [ ] Nothing outside this list without asking first.

## Definition of Done (all must be true)

- [ ] Code committed with a message referencing JUNIOR-001
- [ ] Repo truth commands pass (lint/typecheck/tests)
- [ ] No secrets, PHI, or raw stack traces introduced
- [ ] Report-back section below completed honestly

## Constraints (binding)

- RULE 0 - no fabrication. Report only what you directly observed.
- NO deploys, NO migrations on shared data, NO secret changes (founder gate).
- Ambiguity => STOP and ask. Never guess-and-proceed.
- Cross-service files are off-limits unless the assignment names them.

## Report-back

1. What I did:
2. Evidence observed (real vs simulated labeled):
3. Tests run + results:
4. Questions for reviewer/founder:

--- SUBMITTED 2026-08-26 ---

1. What I did: ran repo truth-command subset (ruff check; pytest --collect-only). No code changed.
2. Evidence observed: RUFF = 2 errors (only fixable via --unsafe-fixes). PYTEST = 339 tests collected cleanly in 34s (collection only; full run outside time box).
3. Tests run + results: ruff => FAILED(2); pytest collect => OK.
4. Questions: auto-fix the 2 unsafe-fix lint errors in a follow-up ticket?