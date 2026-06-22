# DOCKET-Service — Litigation Tracker

**Phase 5: Separate service for docket/litigation tracking.**

This service runs parallel to SETTLE and tracks court dockets, filings, and litigation outcomes. It does NOT share the settlement database. Data may be cross-referenced in the future for expanded product offerings.

## Scope

- Docket search by attorney, firm, judge, jurisdiction
- Case timeline tracking
- Outcome aggregation by judge/court
- Filing pattern analysis
- Settlement vs. trial rate by firm
- Expert witness appearance tracking
- Damages trend analysis

## Data Sources

| Source | Type | Data |
|---|---|---|
| PACER/RECAP | Federal | Dockets, filings, orders, judgments |
| State court portals | State | Varies by jurisdiction |
| CourtListener API | Aggregator | Federal + some state dockets |
| Legal news sites | Scraped | Verdict announcements, settlement reports |
| Law360/VerdictSearch | Scraped | Published verdicts and settlements |

## Compliance

- Court data is public record — different compliance regime than SETTLE
- Names and PII are permissible (public records)
- Still need to consider terms of service for scraping sources
- PACER has usage limits and fees
- State court portals vary widely in access policies

## Future Integration with SETTLE

| Integration | Description | Phase |
|---|---|---|
| Verdict enrichment | Cross-reference SETTLE settlements with docket verdicts | Phase 4 |
| Judge analytics | Judge tendency data for SETTLE reports | Phase 4 |
| Firm benchmarking | Compare firm settlements to docket outcomes | Phase 5+ |
| Expert witness data | Expert history for SETTLE carrier patterns | Phase 5+ |
| Case lifecycle tracking | Track SETTLE-contributed cases through docket | Phase 5+ |

## Status

**Scaffolding complete.** Database schema defined. Service implementation pending.
