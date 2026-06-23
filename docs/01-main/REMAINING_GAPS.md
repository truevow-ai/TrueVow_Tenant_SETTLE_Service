# SETTLE Service — Remaining Gaps & Deferred Items

**Date:** 2026-06-23
**Status:** All pilot-critical features are DONE. These items are post-pilot or external-dependent.

---

## A. External Dependencies (Cannot Complete Without Third-Party Access)

| # | Feature | Dependency | Priority | Effort | Notes |
|---|---|---|---|---|---|
| A1 | **CRM Integrations** (Phase 2.4) | Filevine, Clio, SmartAdvocate API access + OAuth setup | High (post-pilot) | 40+ hours | Abstract adapter pattern + per-CRM adapter. Filevine first (largest PI market share). |
| A2 | **PACER/RECAP scraper** (Phase 5.2) | PACER account ($0.10/page) or free RECAP archive | Medium | 20 hours | Federal docket data. CourtListener already covers some via RECAP. |
| A3 | **State court portal scrapers** (Phase 5.3) | County clerk websites (ASP.NET, viewstate flows) | Medium | 30+ hours | Top 5 FL counties. Brittle scraping, may need headless browser. |
| A4 | **Bar ethics opinion review** (Phase 4.4) | FL + CA bar association legal review | High (pre-production) | External | Must review before production gate (n>=50) is reached. Pilot mode has transparency safeguards. |
| A5 | **Clerk JWT direct auth** (ADR S-3) | Clerk JWKS endpoint access | Low | 8 hours | Replaces X-Settle-User-Id header sidecar pattern. Cohort U-back forward-compat guard already supports. |
| A6 | **GitHub PAT workflow scope** | User grants PAT `workflow` scope | Low | 5 min | Blocked: `.github/workflows/pricing-snapshot.yml` can't be pushed. |
| A7 | **Westlaw/VerdictSearch** | $2,500+/yr subscription | Deferred | N/A | Deferred until paying customers justify cost. |

---

## B. Internal Features (Deferred — No External Dependency)

| # | Feature | Priority | Effort | Notes |
|---|---|---|---|---|
| B1 | **Firm-Wide Yield Analytics** (Phase 3.6) | Medium | 15 hours | Add `firm_id` to API keys table, build `GET /api/v1/analytics/firm-yield` with per-firm aggregation. |
| B2 | **Weekly Digest Cron Scheduler** | Medium | 5 hours | Generator exists (`weekly_digest.py`). Need APScheduler or Celery worker to send on schedule. On Fly.io: separate process in `fly.toml`. |
| B3 | **Weekly Digest Portal Toggle** | Low | 2 hours | Add toggle in settings page + backend preference endpoint. |
| B4 | **ML Model Prototype** (Phase 4.3) | Low | 40+ hours | XGBoost/RF on settlement data. Deferred until 10K+ contributions. Currently only 440. |
| B5 | **DOCKET ↔ SETTLE Cross-Reference** (Phase 5.4) | Low | 20 hours | Join queries between DOCKET-Service and SETTLE for verdict enrichment. |
| B6 | **S3 Signed URLs for PDF Storage** | Medium | 4 hours | Currently PDFs returned as direct response bytes. For persistence across sessions, store in S3 + return signed URL. |
| B7 | **LEVERAGE → SETTLE Automated Ingest** | Medium | 8 hours | Wire LEVERAGE's `settlement-details` consent flow to automatically insert into `settle_contributions`. Currently manual. |
| B8 | **Real OpenTimestamps Submission** | Low | 6 hours | Submit SHA-256 hash to OTS calendar servers for actual blockchain timestamping. Current: `sha256:{hash}` (verifiable but not blockchain-anchored). |
| B9 | **Year-2 Stash Recovery** (ADR S-4) | Low | 20+ hours | `abandoned-auth-rewrite-202605` branch has 129 files of WIP. Decide: recover selectively, recover wholesale, or abandon. |

---

## C. Data Acquisition (Documented Separately)

See `docs/01-main/DATA_ACQUISITION_STRATEGY_FL_CA.md` for the full FL/CA data plan.

| Phase | Target | Expected Yield | Timeline |
|---|---|---|---|
| A: Retry existing failures | FL | +150 rows | Week 1 |
| B: CourtListener + FJC | FL + CA | +400 FL, +700 CA | Weeks 2-3 |
| C: News enrichment | Enrichment | Narratives for new rows | Week 3 |
| D: New source scrapers | FL + CA | +145 FL, +270 CA | Weeks 4-6 |
| E: Plaintiff firm websites | FL + CA | +200-500 | Weeks 6-8 |
| F: FL court portals | FL | +250-500 | Weeks 8-12 |

---

## D. Deployment & Onboarding

| # | Task | Blocked On | Notes |
|---|---|---|---|
| D1 | Deploy to Fly.io | Yasha runs `flyctl deploy` | `fly.toml` + `.dockerignore` + `Dockerfile` ready. Need Supabase creds as secrets. |
| D2 | DNS for `settle.truevow.law` | Yasha adds CNAME record | `flyctl certs create settle.truevow.law --app truevow-settle` |
| D3 | Set SETTLE_PILOT_USER_IDS | Yasha provides Clerk user IDs | Format: `user_2xxxxx` (not email). Check Clerk Dashboard → Users. |
| D4 | Flip SETTLE_PILOT_MODE=true | After D1-D3 | `flyctl secrets set SETTLE_PILOT_MODE=true --app truevow-settle` |
| D5 | Smoke test: end-to-end query | After D4 | Customer portal → SETTLE backend → live Supabase → response |

---

## E. Misc Punch List

| # | Item | Priority | Notes |
|---|---|---|---|
| E1 | Stale docstring in `query.py:37` — claims floor=15, actual is 50 | Low | One-line fix |
| E2 | `_generate_justification()` percentile-collapse copy | Low | Better narrative when all percentiles resolve to same midpoint |
| E3 | Cold-vs-warm API latency probe | Low | Observed 11-16s cold-start, 5s warm. Consider Fly.io min_machines=1 for always-warm. |
| E4 | `SupabaseRESTClient.execute()` silent-500 absorption | Medium | HTML error responses (Cloudflare edge) get parsed as empty data |
| E5 | `SupabaseRESTQuery.range()` method missing | Low | Builder lacks range() — use limit()+offset() workaround |
| E6 | `waitlist.py` asyncpg vs SupabaseRESTClient mismatch | Low | Waitlist endpoint may use wrong DB client pattern |
| E7 | 357 rows with legacy non-enum `injury_category` values | Medium | Separate normalization pass to remap to InjuryTag taxonomy |
| E8 | `datetime.utcnow()` deprecation warning in test_phase2_5.py | Low | Replace with `datetime.now(UTC)` |

---

## Summary Priority Matrix

| Priority | Items | Blocks Pilot? |
|---|---|---|
| **P0 — Pilot Critical** | All done | No |
| **P1 — Deploy** | D1-D5 (Fly.io + DNS + pilot mode) | Yes — needs Yasha action |
| **P2 — Data** | Data acquisition Phases A-F | No — pilot mode handles sparse data |
| **P3 — Post-Pilot High** | A1 (CRM), A4 (bar review), B1 (firm yield), B7 (LEVERAGE ingest) | No |
| **P4 — Post-Pilot Medium** | B2 (digest cron), B6 (S3 PDFs), E4 (silent-500), E7 (legacy tags) | No |
| **P5 — Future** | A2 (PACER), B4 (ML model), B5 (cross-ref), B8 (real OTS), B9 (stash) | No |
