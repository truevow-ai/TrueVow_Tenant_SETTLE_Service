"""Anomaly Detection Service — SETTLE Contribution Integrity

Detects suspicious or anomalous contributions using statistical methods.
Runs per-submission (real-time) and as a nightly batch job.

Design principle: transparent, explainable, tunable. Every flag includes
the algorithm that triggered it and the data that led to the decision.
"""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# Z-score thresholds for cell outlier detection
Z_SCORE_WARNING: float = 2.0
Z_SCORE_CRITICAL: float = 3.0

# Medical bills ratio thresholds
MEDICAL_BILLS_RATIO_MAX: float = 50.0   # outcome > 50x medical bills
MEDICAL_BILLS_RATIO_MIN: float = 0.5    # outcome < 0.5x medical bills

# Velocity thresholds (submissions per day)
VELOCITY_WARNING: int = 5
VELOCITY_CRITICAL: int = 10

# Cross-validation thresholds (vs scraped data)
CROSS_VALIDATION_RATIO_MAX: float = 3.0
CROSS_VALIDATION_RATIO_MIN: float = 0.3


class AnomalySeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


class AnomalyFlagType(str, Enum):
    CELL_OUTLIER = "cell_outlier"
    MEDICAL_BILLS_RATIO = "medical_bills_ratio"
    COMPARATIVE_NEGLIGENCE = "comparative_negligence"
    CARRIER_PATTERN = "carrier_pattern"
    VELOCITY = "velocity"
    CROSS_VALIDATION = "cross_validation"


class AnomalyFlag(BaseModel):
    """Single anomaly flag for a contribution."""
    flag_type: AnomalyFlagType
    severity: AnomalySeverity
    z_score: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AnomalyReport(BaseModel):
    """Complete anomaly report for a submission."""
    contribution_id: Optional[str] = None
    severity: str = "none"  # "none", "warning", "critical"
    flags: List[AnomalyFlag] = Field(default_factory=list)
    recommendation: str = "approve"  # "approve", "review", "reject"

    @property
    def has_flags(self) -> bool:
        return len(self.flags) > 0

    @property
    def max_severity(self) -> str:
        if not self.flags:
            return "none"
        if any(f.severity == AnomalySeverity.CRITICAL for f in self.flags):
            return "critical"
        return "warning"


class AnomalyDetector:
    """
    Detects anomalous contributions using statistical methods.

    Usage:
        detector = AnomalyDetector(db_connection=db)
        report = await detector.check_submission(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            injury_category=["spinal_injury"],
            medical_bills=45000,
            exact_outcome_amount=180000,
            comparative_negligence_pct=15,
            insurance_carrier="State Farm",
            contributor_user_id=uuid,
        )
    """

    def __init__(self, db_connection=None):
        self.db = db_connection

    async def check_submission(
        self,
        *,
        jurisdiction: str,
        case_type: str,
        injury_category: List[str],
        medical_bills: float,
        exact_outcome_amount: Optional[float] = None,
        outcome_amount_range: Optional[str] = None,
        comparative_negligence_pct: Optional[float] = None,
        insurance_carrier: Optional[str] = None,
        contributor_user_id: Optional[str] = None,
    ) -> AnomalyReport:
        """
        Run all anomaly checks on a single submission.

        Returns AnomalyReport with flags, severity, and recommendation.
        """
        report = AnomalyReport()
        flags: List[AnomalyFlag] = []

        # Check 1: Cell outlier (z-score vs jurisdiction/case_type/injury cell)
        cell_outlier = await self._check_cell_outlier(
            jurisdiction, case_type, injury_category, exact_outcome_amount, outcome_amount_range
        )
        if cell_outlier:
            flags.append(cell_outlier)

        # Check 2: Medical bills ratio
        if exact_outcome_amount and medical_bills > 0:
            ratio_flag = self._check_medical_bills_ratio(
                exact_outcome_amount, medical_bills, jurisdiction, case_type, injury_category
            )
            if ratio_flag:
                flags.append(ratio_flag)

        # Check 3: Comparative negligence
        if comparative_negligence_pct is not None:
            neg_flag = await self._check_comparative_negligence(
                comparative_negligence_pct, jurisdiction, case_type, injury_category
            )
            if neg_flag:
                flags.append(neg_flag)

        # Check 4: Carrier pattern
        if insurance_carrier and contributor_user_id:
            carrier_flag = await self._check_carrier_pattern(
                insurance_carrier, jurisdiction, case_type, exact_outcome_amount, contributor_user_id
            )
            if carrier_flag:
                flags.append(carrier_flag)

        # Check 5: Velocity
        if contributor_user_id:
            velocity_flag = await self._check_velocity(contributor_user_id)
            if velocity_flag:
                flags.append(velocity_flag)

        # Check 6: Cross-validation against scraped data
        if exact_outcome_amount:
            cross_val_flag = await self._check_cross_validation(
                exact_outcome_amount, jurisdiction, case_type, injury_category
            )
            if cross_val_flag:
                flags.append(cross_val_flag)

        report.flags = flags

        # Determine overall severity and recommendation
        if any(f.severity == AnomalySeverity.CRITICAL for f in flags):
            report.severity = "critical"
            report.recommendation = "review"
        elif len(flags) >= 2:
            report.severity = "warning"
            report.recommendation = "review"
        elif len(flags) == 1:
            report.severity = "warning"
            report.recommendation = "approve"  # single warning doesn't block
        else:
            report.severity = "none"
            report.recommendation = "approve"

        logger.info(
            "AnomalyDetector: submission check complete — "
            "severity=%s, flags=%d, recommendation=%s",
            report.severity, len(flags), report.recommendation,
        )

        return report

    async def _check_cell_outlier(
        self,
        jurisdiction: str,
        case_type: str,
        injury_category: List[str],
        exact_outcome_amount: Optional[float],
        outcome_amount_range: Optional[str],
    ) -> Optional[AnomalyFlag]:
        """
        Check if the outcome amount is a statistical outlier within
        the jurisdiction/case_type/injury_category cell.
        """
        if not self.db:
            return None

        amount = exact_outcome_amount
        if amount is None and outcome_amount_range:
            amount = self._bucket_to_midpoint(outcome_amount_range)
        if amount is None:
            return None

        try:
            # Get all approved cases in the same cell
            query = self.db.table("settle_contributions").select(
                "exact_outcome_amount, outcome_amount_range"
            ).eq("status", "approved").eq("jurisdiction", jurisdiction).eq("case_type", case_type)

            if injury_category:
                query = query.cs("injury_category", injury_category)

            rows = query.execute().data or []

            if len(rows) < 5:
                return None  # too few data points for meaningful z-score

            # Extract amounts
            amounts = []
            for row in rows:
                if row.get("exact_outcome_amount"):
                    amounts.append(row["exact_outcome_amount"])
                elif row.get("outcome_amount_range"):
                    amounts.append(self._bucket_to_midpoint(row["outcome_amount_range"]))

            if len(amounts) < 5:
                return None

            import numpy as np
            mean = np.mean(amounts)
            std = np.std(amounts)

            if std == 0:
                return None

            z_score = (amount - mean) / std

            if abs(z_score) > Z_SCORE_CRITICAL:
                return AnomalyFlag(
                    flag_type=AnomalyFlagType.CELL_OUTLIER,
                    severity=AnomalySeverity.CRITICAL,
                    z_score=round(z_score, 2),
                    details={
                        "cell": f"{jurisdiction} / {case_type} / {injury_category}",
                        "submitted_amount": amount,
                        "cell_mean": round(float(mean), 2),
                        "cell_std": round(float(std), 2),
                        "cell_n": len(amounts),
                    },
                )
            elif abs(z_score) > Z_SCORE_WARNING:
                return AnomalyFlag(
                    flag_type=AnomalyFlagType.CELL_OUTLIER,
                    severity=AnomalySeverity.WARNING,
                    z_score=round(z_score, 2),
                    details={
                        "cell": f"{jurisdiction} / {case_type} / {injury_category}",
                        "submitted_amount": amount,
                        "cell_mean": round(float(mean), 2),
                        "cell_std": round(float(std), 2),
                        "cell_n": len(amounts),
                    },
                )
        except Exception as exc:
            logger.warning("AnomalyDetector: cell_outlier check failed: %s", exc)

        return None

    def _check_medical_bills_ratio(
        self,
        exact_outcome_amount: float,
        medical_bills: float,
        jurisdiction: str,
        case_type: str,
        injury_category: List[str],
    ) -> Optional[AnomalyFlag]:
        """
        Check if the outcome/medical_bills ratio is extreme compared
        to the cell median ratio.
        """
        if medical_bills <= 0:
            return None

        ratio = exact_outcome_amount / medical_bills

        # Absolute thresholds
        if ratio > MEDICAL_BILLS_RATIO_MAX:
            return AnomalyFlag(
                flag_type=AnomalyFlagType.MEDICAL_BILLS_RATIO,
                severity=AnomalySeverity.WARNING,
                details={
                    "ratio": round(ratio, 2),
                    "threshold_max": MEDICAL_BILLS_RATIO_MAX,
                    "outcome_amount": exact_outcome_amount,
                    "medical_bills": medical_bills,
                },
            )
        elif ratio < MEDICAL_BILLS_RATIO_MIN:
            return AnomalyFlag(
                flag_type=AnomalyFlagType.MEDICAL_BILLS_RATIO,
                severity=AnomalySeverity.WARNING,
                details={
                    "ratio": round(ratio, 2),
                    "threshold_min": MEDICAL_BILLS_RATIO_MIN,
                    "outcome_amount": exact_outcome_amount,
                    "medical_bills": medical_bills,
                },
            )

        return None

    async def _check_comparative_negligence(
        self,
        comparative_negligence_pct: float,
        jurisdiction: str,
        case_type: str,
        injury_category: List[str],
    ) -> Optional[AnomalyFlag]:
        """
        Check if the submitted comparative negligence % is an outlier
        vs. the cell distribution.
        """
        if not self.db or comparative_negligence_pct < 0 or comparative_negligence_pct > 100:
            return None

        try:
            query = self.db.table("settle_contributions").select(
                "comparative_negligence_pct"
            ).eq("status", "approved").eq("jurisdiction", jurisdiction).eq("case_type", case_type)

            if injury_category:
                query = query.cs("injury_category", injury_category)

            query = query.not_.is_("comparative_negligence_pct", "null")
            rows = query.execute().data or []

            if len(rows) < 5:
                return None

            import numpy as np
            values = [r["comparative_negligence_pct"] for r in rows if r.get("comparative_negligence_pct") is not None]

            if len(values) < 5:
                return None

            mean = np.mean(values)
            std = np.std(values)

            if std == 0:
                return None

            z_score = (comparative_negligence_pct - mean) / std

            if abs(z_score) > 2.0:
                return AnomalyFlag(
                    flag_type=AnomalyFlagType.COMPARATIVE_NEGLIGENCE,
                    severity=AnomalySeverity.WARNING,
                    z_score=round(z_score, 2),
                    details={
                        "submitted_pct": comparative_negligence_pct,
                        "cell_mean": round(float(mean), 2),
                        "cell_std": round(float(std), 2),
                        "cell_n": len(values),
                    },
                )
        except Exception as exc:
            logger.warning("AnomalyDetector: comparative_negligence check failed: %s", exc)

        return None

    async def _check_carrier_pattern(
        self,
        insurance_carrier: str,
        jurisdiction: str,
        case_type: str,
        exact_outcome_amount: Optional[float],
        contributor_user_id: str,
    ) -> Optional[AnomalyFlag]:
        """
        Check if the same contributor has submitted multiple cases with
        the same carrier + jurisdiction + similar outcome pattern.
        """
        if not self.db or exact_outcome_amount is None:
            return None

        try:
            query = self.db.table("settle_contributions").select(
                "exact_outcome_amount, insurance_carrier"
            ).eq("status", "approved").eq("insurance_carrier", insurance_carrier).eq(
                "jurisdiction", jurisdiction
            ).eq("case_type", case_type)

            rows = query.execute().data or []

            if len(rows) < 3:
                return None

            # Check if this contributor has submitted 3+ similar patterns
            import numpy as np
            amounts = [r["exact_outcome_amount"] for r in rows if r.get("exact_outcome_amount")]

            if len(amounts) >= 3:
                # Check if the new submission is within 10% of the mean
                mean = np.mean(amounts)
                deviation = abs(exact_outcome_amount - mean) / mean if mean > 0 else 1.0

                if deviation < 0.10 and len(amounts) >= 5:
                    return AnomalyFlag(
                        flag_type=AnomalyFlagType.CARRIER_PATTERN,
                        severity=AnomalySeverity.WARNING,
                        details={
                            "carrier": insurance_carrier,
                            "jurisdiction": jurisdiction,
                            "pattern_count": len(amounts),
                            "pattern_mean": round(float(mean), 2),
                            "submitted_amount": exact_outcome_amount,
                            "deviation_pct": round(deviation * 100, 1),
                        },
                    )
        except Exception as exc:
            logger.warning("AnomalyDetector: carrier_pattern check failed: %s", exc)

        return None

    async def _check_velocity(self, contributor_user_id: str) -> Optional[AnomalyFlag]:
        """
        Check if the contributor has submitted too many cases in the
        last 24 hours.
        """
        if not self.db:
            return None

        try:
            from datetime import timedelta

            cutoff = (datetime.now(UTC) - timedelta(hours=24)).isoformat()

            result = self.db.table("settle_contributions").select(
                "id", count="exact"
            ).eq("contributor_user_id", contributor_user_id).gte("created_at", cutoff).execute()

            count = result.count if hasattr(result, "count") and isinstance(result.count, int) else 0

            if count > VELOCITY_CRITICAL:
                return AnomalyFlag(
                    flag_type=AnomalyFlagType.VELOCITY,
                    severity=AnomalySeverity.CRITICAL,
                    details={
                        "submissions_24h": count,
                        "threshold_critical": VELOCITY_CRITICAL,
                    },
                )
            elif count > VELOCITY_WARNING:
                return AnomalyFlag(
                    flag_type=AnomalyFlagType.VELOCITY,
                    severity=AnomalySeverity.WARNING,
                    details={
                        "submissions_24h": count,
                        "threshold_warning": VELOCITY_WARNING,
                    },
                )
        except Exception as exc:
            logger.warning("AnomalyDetector: velocity check failed: %s", exc)

        return None

    async def _check_cross_validation(
        self,
        exact_outcome_amount: float,
        jurisdiction: str,
        case_type: str,
        injury_category: List[str],
    ) -> Optional[AnomalyFlag]:
        """
        Cross-validate submitted amount against scraped verdict data
        in the same cell. Scraped data is the baseline truth.
        """
        if not self.db:
            return None

        try:
            # Get scraped verdicts in the same cell
            query = self.db.table("settle_contributions").select(
                "exact_outcome_amount, source_type"
            ).eq("status", "approved").eq("jurisdiction", jurisdiction).eq("case_type", case_type).eq("source_type", "scraped_verdict")

            if injury_category:
                query = query.cs("injury_category", injury_category)

            rows = query.execute().data or []

            if len(rows) < 3:
                return None  # not enough scraped data for comparison

            import numpy as np
            scraped_amounts = [r["exact_outcome_amount"] for r in rows if r.get("exact_outcome_amount")]

            if len(scraped_amounts) < 3:
                return None

            median_scraped = float(np.median(scraped_amounts))

            if median_scraped == 0:
                return None

            ratio = exact_outcome_amount / median_scraped

            if ratio > CROSS_VALIDATION_RATIO_MAX:
                return AnomalyFlag(
                    flag_type=AnomalyFlagType.CROSS_VALIDATION,
                    severity=AnomalySeverity.WARNING,
                    details={
                        "submitted_amount": exact_outcome_amount,
                        "scraped_median": round(median_scraped, 2),
                        "ratio": round(ratio, 2),
                        "scraped_n": len(scraped_amounts),
                    },
                )
            elif ratio < CROSS_VALIDATION_RATIO_MIN:
                return AnomalyFlag(
                    flag_type=AnomalyFlagType.CROSS_VALIDATION,
                    severity=AnomalySeverity.WARNING,
                    details={
                        "submitted_amount": exact_outcome_amount,
                        "scraped_median": round(median_scraped, 2),
                        "ratio": round(ratio, 2),
                        "scraped_n": len(scraped_amounts),
                    },
                )
        except Exception as exc:
            logger.warning("AnomalyDetector: cross_validation check failed: %s", exc)

        return None

    async def persist_flags(
        self,
        contribution_id: str,
        report: AnomalyReport,
    ) -> List[str]:
        """Persist anomaly flags to the database."""
        if not self.db or not report.has_flags:
            return []

        flag_ids = []
        for flag in report.flags:
            result = self.db.table("settle_anomaly_flags").insert({
                "contribution_id": contribution_id,
                "flag_type": flag.flag_type.value,
                "severity": flag.severity.value,
                "z_score": flag.z_score,
                "details": flag.details,
            }).execute()

            if result.data:
                flag_ids.append(result.data[0]["id"])

        # Also update the contribution's anomaly_flags JSONB column
        flags_json = [
            {
                "flag_type": f.flag_type.value,
                "severity": f.severity.value,
                "z_score": f.z_score,
                "details": f.details,
            }
            for f in report.flags
        ]

        self.db.table("settle_contributions").update({
            "anomaly_flags": flags_json,
        }).eq("id", contribution_id).execute()

        return flag_ids

    @staticmethod
    def _bucket_to_midpoint(bucket: str) -> float:
        """Convert outcome amount bucket to midpoint value."""
        bucket_midpoints = {
            "$0-$50k": 25000,
            "$50k-$100k": 75000,
            "$100k-$150k": 125000,
            "$150k-$225k": 187500,
            "$225k-$300k": 262500,
            "$300k-$600k": 450000,
            "$600k-$1M": 800000,
            "$1M+": 1500000,
        }
        return bucket_midpoints.get(bucket, 100000)
