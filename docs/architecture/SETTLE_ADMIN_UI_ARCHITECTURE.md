# SETTLE Admin UI Architecture

**Version:** 1.0
**Date:** 2026-05-17
**Status:** DRAFT — for SaaS Admin team implementation

---

## Overview

This document defines the SETTLE Admin UI architecture for the SaaS Admin platform. It specifies the pages, routes, components, and API contracts needed to manage the SETTLE service.

## Admin Pages

### 1. Dashboard (`/admin/settle/dashboard`)

**Purpose:** Overview of SETTLE service health and metrics.

**Components:**
- Total contributions (approved, pending, rejected, flagged)
- Founding member count and capacity (2,100 max)
- Query volume (today, this week, this month)
- Report generation stats
- Data coverage by state/jurisdiction
- Rich field breakdowns:
  - Insurance carrier distribution
  - Injury severity distribution
  - Source type mix (firm_submission vs scraped_verdict)
  - Verdict vs settlement ratio
  - Court level distribution

**API calls:**
- `GET /api/v1/admin/analytics/dashboard`
- `GET /api/v1/admin/analytics/rich-fields`

---

### 2. Contributions Management (`/admin/settle/contributions`)

**Purpose:** Browse, filter, approve, reject, and edit contributions.

**Components:**
- Data table with pagination
- Filter panel:
  - Status (pending, approved, rejected, flagged)
  - Jurisdiction (text search)
  - Case type (dropdown)
  - Insurance carrier (dropdown, populated from data)
  - Injury severity (dropdown)
  - Source type (dropdown)
  - Is verdict (toggle)
- Row actions: View details, Approve, Reject, Edit fields
- Bulk actions: Approve selected, Reject selected

**API calls:**
- `GET /api/v1/admin/contributions` (with query params for filters)
- `GET /api/v1/admin/contributions/{id}` (details)
- `POST /api/v1/admin/contributions/{id}/approve`
- `POST /api/v1/admin/contributions/{id}/reject?reason=...`
- `PATCH /api/v1/admin/contributions/{id}` (update rich fields)

**Editable fields (PATCH):**
- `insurance_carrier`, `comparative_negligence_pct`, `exact_outcome_amount`
- `is_verdict`, `date_of_verdict`, `court_level`, `injury_severity`
- `policy_limit_amount`, `source_type`, `trial_duration_days`
- `appeal_filed`, `appeal_outcome`, `status`, `rejection_reason`
- `is_outlier`, `confidence_score`

---

### 3. Injury Tag Management (`/admin/settle/injury-tags`)

**Purpose:** View and manage the injury classifier taxonomy.

**Components:**
- Tag list table showing:
  - Tag value (e.g., `soft_tissue`, `fracture`)
  - Pattern count (number of regex rules)
  - Default confidence
  - Co-occurrence requirements/forbidden rules
  - Usage count (how many approved cases have this tag)
- Tag detail view (click to expand):
  - All regex patterns for the tag
  - Confidence schedule
  - Co-occurrence rules
  - Sample cases with this tag
- Add tag form (requires code deployment — tags are enum values)
- Note: Adding/removing tags requires a semver-major bump and code change

**API calls:**
- `GET /api/v1/admin/injury-tags`
- `GET /api/v1/admin/injury-tags/usage-stats`

---

### 4. Injury Review Queue (`/admin/settle/review-queue`)

**Purpose:** Review and resolve flagged injury classifications.

**Components:**
- Queue table with columns:
  - Contribution ID (link to details)
  - Classification snapshot (tags, confidence)
  - Review triggers (excessive_tag_count, low_confidence, etc.)
  - Status (pending, accepted, modified, rejected)
  - Created date
- Review modal:
  - Show original narrative (if available)
  - Show classifier's tags and confidence
  - Show matched spans (audit trail)
  - Actions: Accept, Modify (provide corrected tags), Reject
  - Notes field

**API calls:**
- `GET /api/v1/admin/review-queue` (with status filter)
- `POST /api/v1/admin/review-queue/{id}/review` (submit decision)

---

### 5. Provenance Viewer (`/admin/settle/provenance/{contribution_id}`)

**Purpose:** Audit-only access to identifying case fields.

**Components:**
- Case name, citation, docket number
- Judge name, plaintiff firm, defense firm
- Source URLs (TopVerdict, Verdix, etc.)
- News provenance URL
- Enrichment status, match confidence
- Last audit access log

**API calls:**
- `GET /api/v1/admin/provenance/{contribution_id}`

**Security note:** This accesses the `settle_case_provenance` table which is RLS-protected (service_role only). Never expose this data in user-facing reports.

---

### 6. Founding Members (`/admin/settle/founding-members`)

**Purpose:** Manage the 2,100 Founding Member program.

**Components:**
- Member list with contribution stats
- Monthly compliance tracking (1-3 submissions/month)
- Status management (active, inactive, suspended)
- API key management per member

**API calls:**
- `GET /api/v1/admin/founding-members`
- `GET /api/v1/admin/founding-members/{id}`
- `POST /api/v1/admin/founding-members/{id}/status`
- `GET /api/v1/admin/founding-members/contributions`

---

### 7. API Key Management (`/admin/settle/api-keys`)

**Purpose:** Create, rotate, and revoke SETTLE API keys.

**Components:**
- Key list table (prefix, access level, usage, status)
- Create key form (tenant ID, access level)
- Rotate key action
- Revoke key action

**API calls:**
- `POST /api/v1/admin/api-keys/create`
- `GET /api/v1/admin/api-keys/{tenant_id}`
- `POST /api/v1/admin/api-keys/{key_id}/rotate`
- `DELETE /api/v1/admin/api-keys/{key_id}`

---

## Route Structure

```
/admin/settle/
├── dashboard           # Overview metrics
├── contributions       # Browse, filter, approve, reject, edit
├── injury-tags         # Tag taxonomy management
├── review-queue        # Flagged classification review
├── provenance/{id}     # Audit-only case identifiers
├── founding-members    # Founding Member program
└── api-keys            # API key lifecycle
```

## Component Reuse

The following components from the existing frontend library can be reused:
- `ToastProvider` — for success/error notifications
- `Breadcrumb` — for page navigation context
- `Sidebar` — for navigation menu (extend with new routes)
- `Layout` — for consistent page structure

## Data Types

All API responses follow the existing SETTLE Pydantic models. Key types:

```typescript
interface Contribution {
  id: string;
  jurisdiction: string;
  case_type: string;
  injury_category: string[];
  medical_bills: number;
  outcome_amount_range: string;
  status: 'pending' | 'approved' | 'rejected' | 'flagged';
  // Rich fields (Cohort W)
  insurance_carrier?: string;
  comparative_negligence_pct?: number;
  exact_outcome_amount?: number;
  is_verdict?: boolean;
  date_of_verdict?: string;
  court_level?: string;
  injury_severity?: string;
  policy_limit_amount?: number;
  source_type?: string;
  trial_duration_days?: number;
  appeal_filed?: boolean;
  appeal_outcome?: string;
}

interface InjuryTag {
  value: string;
  name: string;
  pattern_count: number;
  confidence?: number;
  co_occurrence_required: string[];
  co_occurrence_forbidden: string[];
}

interface ReviewQueueItem {
  id: string;
  contribution_id: string;
  classification_snapshot: object;
  triggers: string[];
  status: 'pending' | 'accepted' | 'modified' | 'rejected';
  created_at: string;
}
```

## Implementation Priority

1. **Dashboard** — highest visibility, shows service health
2. **Contributions Management** — core admin workflow
3. **Review Queue** — quality control for injury classifications
4. **Injury Tags** — reference view for taxonomy
5. **Provenance Viewer** — audit compliance
6. **Founding Members** — program management
7. **API Keys** — operational tooling
