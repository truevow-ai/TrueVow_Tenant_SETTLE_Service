"""Contribution Reputation Service — SETTLE

Manages per-attorney trust scores that affect:
- How submissions are weighted in estimates
- Whether submissions bypass review or require approval
- Access level to aggregate data

Scoring formula:
  reputation = base_weight(0.3) + verification_weight(0.4) + consistency_weight(0.3)

Tiers:
  unverified   (0.0–0.15): held for review, no aggregate access
  probationary (0.15–0.35): auto-approved after 24h delay, basic access
  trusted      (0.35–0.65): immediate approval, full access, higher weight
  founding     (0.65–1.0):  immediate approval, highest weight, peer flag immunity
"""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

REPUTATION_TIERS = {
    "unverified":   (0.0,  0.15),
    "probationary": (0.15, 0.35),
    "trusted":      (0.35, 0.65),
    "founding":     (0.65, 1.0),
}

# Score component weights
BASE_WEIGHT_MAX: float = 0.3
VERIFICATION_WEIGHT_MAX: float = 0.4
CONSISTENCY_WEIGHT_MAX: float = 0.3

# Reputation decay half-life (days) — recent behavior matters more
REPUTATION_DECAY_HALF_LIFE: int = 30

# Submission thresholds for verification weight
VERIFICATION_THRESHOLDS = [
    (1,  0.1),   # 1+ submissions approved
    (5,  0.1),   # 5+ submissions approved
    (10, 0.1),   # 10+ submissions approved
    (25, 0.1),   # 25+ submissions approved
]

# Citation verification bonus (capped)
CITATION_BONUS_PER_VERIFIED: float = 0.05
CITATION_BONUS_MAX: float = 0.2


# ============================================================================
# MODELS
# ============================================================================

class ReputationRecord(BaseModel):
    """Full reputation record for a contributor."""
    contributor_user_id: UUID
    reputation_score: float = 0.0
    tier: str = "unverified"
    total_submissions: int = 0
    approved_submissions: int = 0
    rejected_submissions: int = 0
    flagged_submissions: int = 0
    average_z_score: Optional[float] = None
    last_submission_at: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ReputationTierInfo(BaseModel):
    """Information about a reputation tier."""
    name: str
    min_score: float
    max_score: float
    effects: List[str]


# ============================================================================
# SERVICE
# ============================================================================

class ReputationService:
    """
    Manages contributor reputation scores.

    Usage:
        svc = ReputationService(db_connection=db)

        # Get or create reputation for a user
        record = await svc.get_or_create(user_id)

        # Update after a submission is approved/rejected
        await svc.update_after_decision(user_id, decision="approved")

        # Recalculate score from scratch
        await svc.recalculate(user_id)
    """

    def __init__(self, db_connection=None):
        self.db = db_connection

    async def get_or_create(self, user_id: UUID) -> ReputationRecord:
        """Get existing reputation record or create a new one."""
        db = self.db or await get_db()
        if not db:
            return ReputationRecord(contributor_user_id=user_id)

        result = db.table("settle_contribution_reputation").select("*").eq(
            "contributor_user_id", str(user_id)
        ).execute()

        if result.data:
            return ReputationRecord(**result.data[0])

        # Create new record
        insert_result = db.table("settle_contribution_reputation").insert({
            "contributor_user_id": str(user_id),
            "reputation_score": 0.0,
            "tier": "unverified",
        }).execute()

        if insert_result.data:
            return ReputationRecord(**insert_result.data[0])

        return ReputationRecord(contributor_user_id=user_id)

    async def recalculate(self, user_id: UUID) -> ReputationRecord:
        """
        Recalculate reputation score from scratch based on all
        historical contributions.
        """
        db = self.db or await get_db()
        if not db:
            return ReputationRecord(contributor_user_id=user_id)

        # Get all contributions by this user
        contributions = db.table("settle_contributions").select(
            "id, status, exact_outcome_amount, outcome_amount_range, "
            "jurisdiction, case_type, injury_category, created_at"
        ).eq("contributor_user_id", str(user_id)).execute()

        rows = contributions.data or []

        # Count by status
        approved = [r for r in rows if r.get("status") == "approved"]
        rejected = [r for r in rows if r.get("status") == "rejected"]
        flagged = [r for r in rows if r.get("status") == "flagged"]

        # Calculate base weight (0.0–0.3)
        base_weight = self._calc_base_weight(len(approved))

        # Calculate verification weight (0.0–0.4)
        verification_weight = self._calc_verification_weight(len(approved))

        # Calculate consistency weight (0.0–0.3)
        consistency_weight = await self._calc_consistency_weight(user_id, approved)

        # Total score
        score = min(1.0, base_weight + verification_weight + consistency_weight)
        score = round(score, 3)

        # Determine tier
        tier = self._score_to_tier(score)

        # Calculate average z-score
        avg_z = await self._calc_average_z_score(user_id, approved)

        # Last submission date
        last_submission = None
        if rows:
            dates = [r.get("created_at") for r in rows if r.get("created_at")]
            if dates:
                last_submission = max(dates)

        # Update database
        update_data = {
            "reputation_score": score,
            "tier": tier,
            "total_submissions": len(rows),
            "approved_submissions": len(approved),
            "rejected_submissions": len(rejected),
            "flagged_submissions": len(flagged),
            "average_z_score": avg_z,
            "last_submission_at": last_submission,
            "updated_at": datetime.now(UTC).isoformat(),
        }

        db.table("settle_contribution_reputation").update(update_data).eq(
            "contributor_user_id", str(user_id)
        ).execute()

        # Also update the reputation score on each approved contribution
        # (for estimator weighting)
        if approved:
            db.table("settle_contributions").update({
                "contributor_reputation_score": score,
                "submission_quality_weight": self._calc_submission_weight(score, rows[0].get("source_type")),
            }).eq("contributor_user_id", str(user_id)).eq("status", "approved").execute()

        record = ReputationRecord(
            contributor_user_id=user_id,
            reputation_score=score,
            tier=tier,
            total_submissions=len(rows),
            approved_submissions=len(approved),
            rejected_submissions=len(rejected),
            flagged_submissions=len(flagged),
            average_z_score=avg_z,
            last_submission_at=last_submission,
        )

        logger.info(
            "ReputationService: recalculated for %s — score=%.3f, tier=%s, "
            "approved=%d, rejected=%d",
            user_id, score, tier, len(approved), len(rejected),
        )

        return record

    async def update_after_decision(
        self,
        user_id: UUID,
        decision: str,  # "approved", "rejected", "flagged"
    ) -> ReputationRecord:
        """Incremental update after a single submission decision."""
        db = self.db or await get_db()
        if not db:
            return ReputationRecord(contributor_user_id=user_id)

        # Get current record
        record = await self.get_or_create(user_id)

        # Increment counters
        updates = {"updated_at": datetime.now(UTC).isoformat()}

        if decision == "approved":
            updates["approved_submissions"] = record.approved_submissions + 1
            updates["total_submissions"] = record.total_submissions + 1
        elif decision == "rejected":
            updates["rejected_submissions"] = record.rejected_submissions + 1
            updates["total_submissions"] = record.total_submissions + 1
        elif decision == "flagged":
            updates["flagged_submissions"] = record.flagged_submissions + 1

        db.table("settle_contribution_reputation").update(updates).eq(
            "contributor_user_id", str(user_id)
        ).execute()

        # Full recalculation is safer than incremental for score accuracy
        return await self.recalculate(user_id)

    def get_submission_weight(self, reputation_score: float, source_type: Optional[str]) -> float:
        """
        Calculate the weight for a single submission in the estimator.

        weight = reputation_score * source_quality_factor

        Low-reputation submissions (< 0.2) are excluded from percentile
        calculation but still shown in comparable_cases with a flag.
        """
        if reputation_score < 0.2:
            return 0.0  # excluded from calculation

        source_factors = {
            "firm_submission": 1.0,
            "scraped_verdict": 0.8,
            "news_report": 0.6,
            "court_docket": 0.7,
            "settlement_survey": 0.9,
        }

        source_factor = source_factors.get(source_type, 0.8)  # default to scraped
        return round(reputation_score * source_factor, 4)

    def should_auto_approve(self, reputation_score: float) -> bool:
        """Determine if a submission from this user should be auto-approved."""
        return reputation_score >= 0.35  # trusted or founding tier

    def should_delay_approval(self, reputation_score: float) -> bool:
        """Determine if a submission should be held for 24h delay."""
        return 0.15 <= reputation_score < 0.35  # probationary tier

    def get_tier_effects(self, tier: str) -> List[str]:
        """Return human-readable effects for a reputation tier."""
        effects = {
            "unverified": [
                "Submissions held for admin review",
                "No aggregate data access",
                "Estimates show wider confidence bands",
            ],
            "probationary": [
                "Submissions auto-approved after 24h delay",
                "Basic aggregate data access",
                "Standard estimate weighting",
            ],
            "trusted": [
                "Immediate submission approval",
                "Full aggregate data access",
                "Higher weight in estimate calculations",
            ],
            "founding": [
                "Immediate submission approval",
                "Full aggregate data access",
                "Highest weight in estimate calculations",
                "Peer flag immunity (requires 5 flags for review)",
            ],
        }
        return effects.get(tier, [])

    def get_all_tiers(self) -> List[ReputationTierInfo]:
        """Return information about all reputation tiers."""
        return [
            ReputationTierInfo(
                name="unverified",
                min_score=0.0,
                max_score=0.15,
                effects=self.get_tier_effects("unverified"),
            ),
            ReputationTierInfo(
                name="probationary",
                min_score=0.15,
                max_score=0.35,
                effects=self.get_tier_effects("probationary"),
            ),
            ReputationTierInfo(
                name="trusted",
                min_score=0.35,
                max_score=0.65,
                effects=self.get_tier_effects("trusted"),
            ),
            ReputationTierInfo(
                name="founding",
                min_score=0.65,
                max_score=1.0,
                effects=self.get_tier_effects("founding"),
            ),
        ]

    # ========================================================================
    # Internal calculation methods
    # ========================================================================

    @staticmethod
    def _calc_base_weight(approved_count: int) -> float:
        """Calculate base weight from submission count (0.0–0.3)."""
        if approved_count == 0:
            return 0.0
        elif approved_count < 3:
            return 0.1
        elif approved_count < 10:
            return 0.2
        else:
            return 0.3

    @staticmethod
    def _calc_verification_weight(approved_count: int) -> float:
        """Calculate verification weight from approval milestones (0.0–0.4)."""
        weight = 0.0
        for threshold, bonus in VERIFICATION_THRESHOLDS:
            if approved_count >= threshold:
                weight += bonus
        return min(VERIFICATION_WEIGHT_MAX, weight)

    async def _calc_consistency_weight(
        self,
        user_id: UUID,
        approved_contributions: List[Dict],
    ) -> float:
        """
        Calculate consistency weight based on z-score alignment with
        peer submissions (0.0–0.3).
        """
        if not approved_contributions or len(approved_contributions) < 3:
            return 0.0

        db = self.db or await get_db()
        if not db:
            return 0.0

        z_scores = []

        for contrib in approved_contributions:
            jurisdiction = contrib.get("jurisdiction")
            case_type = contrib.get("case_type")
            injury_category = contrib.get("injury_category")
            amount = contrib.get("exact_outcome_amount")

            if not all([jurisdiction, case_type, amount]):
                continue

            # Get cell median
            query = db.table("settle_contributions").select(
                "exact_outcome_amount"
            ).eq("status", "approved").eq("jurisdiction", jurisdiction).eq("case_type", case_type)

            if injury_category:
                query = query.cs("injury_category", injury_category)

            rows = query.execute().data or []

            if len(rows) < 5:
                continue

            amounts = [r["exact_outcome_amount"] for r in rows if r.get("exact_outcome_amount")]
            if len(amounts) < 5:
                continue

            import numpy as np
            mean = np.mean(amounts)
            std = np.std(amounts)

            if std == 0:
                continue

            z = abs((amount - mean) / std)
            z_scores.append(z)

        if not z_scores:
            return 0.0

        avg_z = np.mean(z_scores)

        if avg_z < 0.5:
            return 0.3
        elif avg_z < 1.0:
            return 0.2
        elif avg_z < 1.5:
            return 0.1
        else:
            return 0.0

    async def _calc_average_z_score(
        self,
        user_id: UUID,
        approved_contributions: List[Dict],
    ) -> Optional[float]:
        """Calculate the average absolute z-score for a user's submissions."""
        if not approved_contributions:
            return None

        db = self.db or await get_db()
        if not db:
            return None

        z_scores = []

        for contrib in approved_contributions:
            jurisdiction = contrib.get("jurisdiction")
            case_type = contrib.get("case_type")
            injury_category = contrib.get("injury_category")
            amount = contrib.get("exact_outcome_amount")

            if not all([jurisdiction, case_type, amount]):
                continue

            query = db.table("settle_contributions").select(
                "exact_outcome_amount"
            ).eq("status", "approved").eq("jurisdiction", jurisdiction).eq("case_type", case_type)

            if injury_category:
                query = query.cs("injury_category", injury_category)

            rows = query.execute().data or []

            if len(rows) < 5:
                continue

            amounts = [r["exact_outcome_amount"] for r in rows if r.get("exact_outcome_amount")]
            if len(amounts) < 5:
                continue

            import numpy as np
            mean = np.mean(amounts)
            std = np.std(amounts)

            if std == 0:
                continue

            z = abs((amount - mean) / std)
            z_scores.append(z)

        if not z_scores:
            return None

        return round(float(np.mean(z_scores)), 3)

    @staticmethod
    def _score_to_tier(score: float) -> str:
        """Convert a reputation score to a tier name."""
        if score < 0.15:
            return "unverified"
        elif score < 0.35:
            return "probationary"
        elif score < 0.65:
            return "trusted"
        else:
            return "founding"

    @staticmethod
    def _calc_submission_weight(reputation_score: float, source_type: Optional[str]) -> float:
        """Calculate the submission quality weight for storage."""
        if reputation_score < 0.2:
            return 0.0

        source_factors = {
            "firm_submission": 1.0,
            "scraped_verdict": 0.8,
            "news_report": 0.6,
            "court_docket": 0.7,
            "settlement_survey": 0.9,
        }

        source_factor = source_factors.get(source_type, 0.8)
        return round(reputation_score * source_factor, 4)
