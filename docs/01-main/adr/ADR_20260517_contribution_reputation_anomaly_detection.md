# ADR S-3: Contribution Reputation & Anomaly Detection

**Date:** 2026-05-17
**Status:** DRAFT — for Yasha review
**Author:** Interim architect+executor
**Cohort:** W (Rich Fields) + X (Reputation)

---

## Context

SETTLE's value depends on data integrity. The platform faces adversarial threats:
- Insurance companies submitting artificially low "settlements" to depress ranges
- Competitor attorneys inflating ranges to justify higher fees
- Experienced attorneys submitting garbage data to maintain informational edge
- Trolling/random noise submissions

Existing defenses (admin approval, blockchain hashing, outlier detection) are insufficient:
- Admin approval doesn't scale past ~500 submissions/month
- Blockchain proves immutability, not truthfulness
- Outlier detection catches extremes, not systematic 15% bias
- Bucketed amounts make precise gaming harder but coarse manipulation still works

## Decision

Implement a layered defense system with three components:

### 1. Reputation Scoring (`contribution_reputation` table)

Each attorney gets a trust score (0.0–1.0) that affects:
- How their submissions are weighted in estimates
- Whether submissions bypass review or require admin approval
- Access level to aggregate data

**Score calculation:**
```
reputation_score = base_weight(0.3) + verification_weight(0.4) + consistency_weight(0.3)

base_weight:
  - 0.0: New account, no submissions
  - 0.1: 1-2 submissions (pending review)
  - 0.2: 3-9 submissions (all approved)
  - 0.3: 10+ submissions

verification_weight (max 0.4):
  - +0.1: First submission approved
  - +0.1: 5 submissions approved
  - +0.1: 10 submissions approved
  - +0.1: 25+ submissions approved
  - +0.05: Case citation provided and verified (per submission, capped at 0.2)

consistency_weight (max 0.3):
  - Based on statistical alignment with peer submissions
  - Measured by z-score of submission amounts vs. jurisdiction/case_type/injury cell median
  - 0.3: |z| < 0.5 (highly consistent)
  - 0.2: 0.5 <= |z| < 1.0
  - 0.1: 1.0 <= |z| < 1.5
  - 0.0: |z| >= 1.5 (outlier pattern)
```

**Reputation tiers:**
| Tier | Score | Effects |
|---|---|---|
| `unverified` | 0.0–0.15 | Submissions held for review, no aggregate access |
| `probationary` | 0.15–0.35 | Submissions auto-approved after 24h delay, basic aggregate access |
| `trusted` | 0.35–0.65 | Immediate approval, full aggregate access, higher weight |
| `founding` | 0.65–1.0 | Immediate approval, full access, highest weight, peer flag immunity |

### 2. Anomaly Detection Service (`app/services/anomaly_detector.py`)

Runs on every submission and periodically (nightly batch).

**Per-submission checks:**
```python
def detect_anomalies(submission: ContributionRequest) -> AnomalyReport:
    """
    Returns:
      - severity: 'none' | 'warning' | 'critical'
      - flags: list of detected anomalies
      - z_score: statistical deviation from cell median
      - recommendation: 'approve' | 'review' | 'reject'
    """
```

**Detection algorithms:**

| Check | Method | Threshold |
|---|---|---|
| **Cell outlier** | Z-score of `exact_outcome_amount` vs. jurisdiction/case_type/injury cell | |z| > 2.0 → warning, |z| > 3.0 → critical |
| **Medical bills ratio** | `outcome_amount / medical_bills` vs. cell median ratio | Ratio > 50× or < 0.5× median → warning |
| **Comparative negligence** | Submitted negligence % vs. cell distribution | > 2σ from cell mean → warning |
| **Carrier pattern** | Same carrier + same jurisdiction + same outcome pattern across multiple submissions | > 3 identical patterns → review |
| **Velocity** | Submissions per day from same user | > 5/day → warning, > 10/day → critical |
| **Cross-validation** | Submitted amount vs. scraped verdict median in same cell | > 3× or < 0.3× scraped median → warning |

**Nightly batch checks:**
- Per-attorney z-score trend (is an attorney's average submission drifting?)
- Jurisdiction-level anomaly clusters (are multiple attorneys submitting similar outliers in one cell?)
- Temporal anomalies (sudden spike in submissions for a rare injury type)

### 3. Reputation-Weighted Estimator

The `SettlementEstimator` is modified to weight cases by contributor reputation:

```python
def _calculate_weighted_percentile_ranges(
    self,
    cases: List[SettleContribution],
    medical_bills: float
) -> Tuple[Dict[str, float], str]:
    """
    Instead of equal-weight percentiles, weight each case by:
    weight = contributor_reputation_score * source_quality_factor
    
    source_quality_factor:
      - firm_submission: 1.0
      - scraped_verdict: 0.8 (verdicts ≠ settlements)
      - news_report: 0.6 (less structured)
      - court_docket: 0.7
    
    Cases with reputation < 0.2 are excluded from percentile calculation
    but still shown in comparable_cases list with a "low confidence" flag.
    """
```

**Confidence band widening:**
When the dataset contains a high proportion of low-reputation submissions, confidence bands widen:
```python
low_rep_ratio = count(reputation < 0.35) / total_cases
if low_rep_ratio > 0.3:
    # Widen bands by 15%
    p25 *= 0.85
    p95 *= 1.15
    confidence = "medium"  # downgrade from "high"
```

## Database Schema

### New table: `settle_contribution_reputation`

```sql
CREATE TABLE settle_contribution_reputation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contributor_user_id UUID NOT NULL,  -- references central users table
    reputation_score NUMERIC NOT NULL DEFAULT 0.0 CHECK (reputation_score >= 0 AND reputation_score <= 1),
    tier TEXT NOT NULL DEFAULT 'unverified' CHECK (tier IN ('unverified', 'probationary', 'trusted', 'founding')),
    total_submissions INT NOT NULL DEFAULT 0,
    approved_submissions INT NOT NULL DEFAULT 0,
    rejected_submissions INT NOT NULL DEFAULT 0,
    flagged_submissions INT NOT NULL DEFAULT 0,
    average_z_score NUMERIC,  -- rolling average z-score of submissions
    last_submission_at TIMESTAMPTZ,
    last_reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (contributor_user_id)
);
```

### New table: `settle_anomaly_flags`

```sql
CREATE TABLE settle_anomaly_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contribution_id UUID REFERENCES settle_contributions(id) ON DELETE CASCADE,
    flag_type TEXT NOT NULL,  -- 'cell_outlier', 'medical_bills_ratio', 'velocity', etc.
    severity TEXT NOT NULL CHECK (severity IN ('warning', 'critical')),
    z_score NUMERIC,
    details JSONB,  -- algorithm-specific details
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by UUID,  -- admin who resolved
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_anomaly_flags_contribution ON settle_anomaly_flags(contribution_id);
CREATE INDEX idx_anomaly_flags_severity ON settle_anomaly_flags(severity);
CREATE INDEX idx_anomaly_flags_unresolved ON settle_anomaly_flags(resolved) WHERE resolved = FALSE;
```

### Alter `settle_contributions`:

```sql
ALTER TABLE settle_contributions
ADD COLUMN contributor_reputation_score NUMERIC DEFAULT 0.0,
ADD COLUMN anomaly_flags JSONB DEFAULT '[]'::jsonb,
ADD COLUMN submission_quality_weight NUMERIC DEFAULT 1.0;
```

## API Endpoints

### Admin endpoints (new):

```
GET    /api/v1/admin/reputation                    # List all users with reputation scores
GET    /api/v1/admin/reputation/{user_id}           # Detailed reputation history
POST   /api/v1/admin/reputation/{user_id}/adjust    # Manual score adjustment (admin override)
GET    /api/v1/admin/anomaly-flags                  # List unresolved anomaly flags
POST   /api/v1/admin/anomaly-flags/{id}/resolve     # Resolve a flag
GET    /api/v1/admin/anomaly-detection/stats        # Nightly batch job statistics
```

### Client endpoints (new):

```
GET    /api/v1/settle/reputation/me                 # Current user's reputation status
GET    /api/v1/settle/reputation/tiers              # Tier definitions and requirements
```

## Implementation Sequence

### Phase 1: Foundation (Week 1)
1. Database migration (reputation table, anomaly flags table, contribution columns)
2. `AnomalyDetector` service with per-submission checks
3. Reputation score calculation service
4. Admin API endpoints for reputation/anomaly management

### Phase 2: Estimator Integration (Week 2)
1. Modify `SettlementEstimator` to use reputation-weighted percentiles
2. Add confidence band widening logic
3. Update `ComparableCase` to include contributor reputation indicator
4. Update frontend to show "low confidence" flags on cases

### Phase 3: Batch Processing (Week 3)
1. Nightly batch anomaly detection job
2. Per-attorney z-score trend tracking
3. Jurisdiction-level anomaly cluster detection
4. Automated reputation score recalculation

### Phase 4: Frontend Integration (Week 4)
1. Customer portal: show user's reputation status
2. Customer portal: show case confidence flags
3. Admin UI: reputation dashboard
4. Admin UI: anomaly flag review queue

## Rollout Strategy

**Gradual activation via feature flags:**

| Flag | Default | Effect |
|---|---|---|
| `REPUTATION_SCORING_ENABLED` | `false` | When true, calculate scores but don't affect estimates |
| `REPUTATION_WEIGHTING_ENABLED` | `false` | When true, use reputation-weighted percentiles |
| `ANOMALY_AUTO_REJECT_ENABLED` | `false` | When true, auto-reject critical anomalies |
| `CONFIDENCE_WIDENING_ENABLED` | `false` | When true, widen bands for low-rep datasets |

**Activation sequence:**
1. Enable `REPUTATION_SCORING_ENABLED` — collect data, verify scores look correct
2. Enable `REPUTATION_WEIGHTING_ENABLED` — estimates change slightly, monitor for regressions
3. Enable `CONFIDENCE_WIDENING_ENABLED` — confidence labels may change, verify with founding members
4. Enable `ANOMALY_AUTO_REJECT_ENABLED` — last to enable, requires high confidence in detection accuracy

## Consequences

### Positive
- Systematic data manipulation becomes statistically detectable
- Bad data degrades gracefully (wider bands) rather than corrupting estimates
- Good contributors are rewarded with higher influence
- Admin review burden decreases as reputation system matures
- Cross-validation against scraped data provides baseline truth

### Negative
- Adds complexity to the estimator algorithm
- Reputation scoring requires historical data — cold start problem for new users
- May discourage new attorneys if they feel penalized for low initial scores
- Requires ongoing tuning of detection thresholds

### Risks
- Over-aggressive anomaly detection could flag legitimate outlier cases
- Reputation system could create a "rich get richer" dynamic
- Adversaries may adapt their strategies to evade detection

## Mitigations
- All anomaly flags are reviewable by admins — false positives can be corrected
- Reputation scores decay over time (30-day half-life) — recent behavior matters more
- New users get a "probationary" tier with reasonable access, not locked out
- Detection thresholds are configurable via environment variables

## Alternatives Considered

### 1. Manual review only
- Pro: Simple, human judgment
- Con: Doesn't scale, subjective, slow

### 2. Blockchain verification of truth
- Pro: Immutable record
- Con: Can't verify truthfulness at submission time, expensive

### 3. Peer review (attorneys rate each other)
- Pro: Community-driven
- Con: Collusion risk, gaming, social dynamics

### 4. Machine learning model
- Pro: Can detect complex patterns
- Con: Requires large training set, black-box, hard to explain to attorneys

### Decision: Rule-based + statistical approach
- Transparent, explainable, tunable
- No training data required
- Can be combined with ML later as dataset grows

## References
- `docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md` — pilot mode gate design
- `docs/01-main/adr/ADR_20260513_deterministic_injury_classifier.md` — deterministic classification pattern
- `app/services/intelligence_gate.py` — existing gate pattern (similar design philosophy)
- `app/services/estimator.py` — estimator to be modified
