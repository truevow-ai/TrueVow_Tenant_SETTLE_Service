"""
Trend Studies / Market Reports Service — Phase 2.5

Generates quarterly "State of Settlement" reports from SETTLE's aggregated data.
Used for marketing, retention, and attorney education.

Report types:
- Quarterly trend report (by injury type, by state, by carrier category)
- Jurisdiction coverage gap analysis
- Founding Member contribution highlights

All reports are descriptive statistics only — no predictive language.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta, UTC
from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# TREND REPORT MODELS
# ============================================================================

class InjuryTypeTrend(BaseModel):
    """Trend data for a specific injury type."""
    injury_type: str
    total_cases: int
    avg_settlement: Optional[float] = None
    median_settlement: Optional[float] = None
    p25_settlement: Optional[float] = None
    p75_settlement: Optional[float] = None
    avg_medical_bills: Optional[float] = None
    avg_multiplier: Optional[float] = None  # settlement / medical_bills
    case_count_change_pct: Optional[float] = None  # vs previous quarter
    settlement_change_pct: Optional[float] = None  # vs previous quarter


class JurisdictionTrend(BaseModel):
    """Trend data for a specific jurisdiction."""
    jurisdiction: str
    state: str
    total_cases: int
    avg_settlement: Optional[float] = None
    median_settlement: Optional[float] = None
    case_count_change_pct: Optional[float] = None
    coverage_status: str = Field(..., description="adequate (n>=50), growing (n>=10), thin (n<10)")


class CarrierCategoryTrend(BaseModel):
    """Trend data for a defendant category."""
    defendant_category: str
    defendant_industry: Optional[str] = None
    total_cases: int
    avg_settlement: Optional[float] = None
    settlement_rate: Optional[float] = None
    trial_rate: Optional[float] = None
    lowball_indicator: Optional[float] = None


class QuarterlyTrendReport(BaseModel):
    """Complete quarterly trend report."""
    report_id: str
    period: str  # e.g., "Q1 2026"
    generated_at: datetime
    total_contributions: int
    total_queries: int
    total_reports_generated: int
    active_contributors: int
    injury_type_trends: List[InjuryTypeTrend]
    jurisdiction_trends: List[JurisdictionTrend]
    carrier_category_trends: List[CarrierCategoryTrend]
    top_jurisdictions_by_volume: List[Dict[str, Any]]
    fastest_growing_injury_types: List[Dict[str, Any]]
    methodology: str = Field(
        default="Descriptive statistics from anonymized settlement contributions. Not predictive.",
    )


class CoverageGapAnalysis(BaseModel):
    """Jurisdiction coverage gap analysis."""
    total_jurisdictions_tracked: int
    jurisdictions_with_adequate_data: int  # n>=50
    jurisdictions_with_growing_data: int  # n>=10
    jurisdictions_with_thin_data: int  # n<10
    coverage_pct: float
    gaps: List[Dict[str, Any]]  # jurisdictions with n<10
    recommendations: List[str]


class FoundingMemberHighlights(BaseModel):
    """Founding Member contribution highlights."""
    total_founding_members: int
    active_contributors: int
    total_contributions: int
    avg_contributions_per_member: float
    top_contributors: List[Dict[str, Any]]
    milestone_achievements: List[str]


# ============================================================================
# TREND REPORT GENERATOR
# ============================================================================

class TrendReportGenerator:
    """Generates quarterly trend reports from SETTLE data."""

    async def generate_quarterly_report(
        self,
        year: int,
        quarter: int,
    ) -> QuarterlyTrendReport:
        """
        Generate a quarterly trend report.

        Args:
            year: Report year (e.g., 2026)
            quarter: Report quarter (1-4)
        """
        db = await get_db()

        # Calculate date range for the quarter
        quarter_start = date(year, (quarter - 1) * 3 + 1, 1)
        if quarter == 4:
            quarter_end = date(year, 12, 31)
        else:
            quarter_end = date(year, quarter * 3 + 1, 1) - timedelta(days=1)

        # Previous quarter for change calculations
        if quarter == 1:
            prev_quarter_start = date(year - 1, 10, 1)
            prev_quarter_end = date(year - 1, 12, 31)
        else:
            prev_quarter_start = date(year, (quarter - 2) * 3 + 1, 1)
            prev_quarter_end = date(year, (quarter - 1) * 3 + 1, 1) - timedelta(days=1)

        # Get current quarter contributions
        current_result = await db.table("settle_contributions").select("*").eq("status", "approved").gte("created_at", quarter_start.isoformat()).lte("created_at", f"{quarter_end.isoformat()}T23:59:59").execute()
        current_rows = current_result.data or []

        # Get previous quarter contributions
        prev_result = await db.table("settle_contributions").select("*").eq("status", "approved").gte("created_at", prev_quarter_start.isoformat()).lte("created_at", f"{prev_quarter_end.isoformat()}T23:59:59").execute()
        prev_rows = prev_result.data or []

        # Overall stats
        total_contributions = len(current_rows)
        active_contributors = len(set(r.get("contributor_user_id") for r in current_rows if r.get("contributor_user_id")))

        # Query stats (approximate — would need settle_queries table)
        total_queries = 0
        total_reports_generated = 0

        # Injury type trends
        injury_trends = await self._calculate_injury_trends(current_rows, prev_rows)

        # Jurisdiction trends
        jurisdiction_trends = await self._calculate_jurisdiction_trends(current_rows, prev_rows)

        # Carrier category trends
        carrier_trends = await self._calculate_carrier_trends(current_rows)

        # Top jurisdictions by volume
        jurisdiction_counts: Dict[str, int] = {}
        for row in current_rows:
            j = row.get("jurisdiction", "Unknown")
            jurisdiction_counts[j] = jurisdiction_counts.get(j, 0) + 1
        top_jurisdictions = sorted(jurisdiction_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_jurisdictions_list = [{"jurisdiction": j, "case_count": c} for j, c in top_jurisdictions]

        # Fastest growing injury types
        current_injury_counts: Dict[str, int] = {}
        prev_injury_counts: Dict[str, int] = {}
        for row in current_rows:
            for injury in row.get("injury_category", []):
                current_injury_counts[injury] = current_injury_counts.get(injury, 0) + 1
        for row in prev_rows:
            for injury in row.get("injury_category", []):
                prev_injury_counts[injury] = prev_injury_counts.get(injury, 0) + 1

        growth_rates = []
        for injury, current_count in current_injury_counts.items():
            prev_count = prev_injury_counts.get(injury, 0)
            if prev_count > 0:
                growth_pct = ((current_count - prev_count) / prev_count) * 100
            elif current_count > 0:
                growth_pct = 100.0  # New this quarter
            else:
                growth_pct = 0.0
            growth_rates.append({"injury_type": injury, "current_count": current_count, "previous_count": prev_count, "growth_pct": round(growth_pct, 1)})

        fastest_growing = sorted(growth_rates, key=lambda x: x["growth_pct"], reverse=True)[:5]

        report_id = f"trend-{year}-q{quarter}"
        period = f"Q{quarter} {year}"

        return QuarterlyTrendReport(
            report_id=report_id,
            period=period,
            generated_at=datetime.now(UTC),
            total_contributions=total_contributions,
            total_queries=total_queries,
            total_reports_generated=total_reports_generated,
            active_contributors=active_contributors,
            injury_type_trends=injury_trends,
            jurisdiction_trends=jurisdiction_trends,
            carrier_category_trends=carrier_trends,
            top_jurisdictions_by_volume=top_jurisdictions_list,
            fastest_growing_injury_types=fastest_growing,
        )

    async def _calculate_injury_trends(
        self,
        current_rows: List[dict],
        prev_rows: List[dict],
    ) -> List[InjuryTypeTrend]:
        """Calculate injury type trend data."""
        # Group by injury type
        injury_data: Dict[str, List[dict]] = {}
        for row in current_rows:
            for injury in row.get("injury_category", []):
                if injury not in injury_data:
                    injury_data[injury] = []
                injury_data[injury].append(row)

        prev_injury_counts: Dict[str, int] = {}
        for row in prev_rows:
            for injury in row.get("injury_category", []):
                prev_injury_counts[injury] = prev_injury_counts.get(injury, 0) + 1

        trends = []
        for injury, rows in injury_data.items():
            amounts = []
            medical_bills_list = []
            for row in rows:
                exact = row.get("exact_outcome_amount")
                if exact is not None:
                    amounts.append(exact)
                mb = row.get("medical_bills")
                if mb is not None and mb > 0:
                    medical_bills_list.append(mb)

            amounts.sort()
            n = len(amounts)

            avg_settlement = sum(amounts) / n if n > 0 else None
            median_settlement = _percentile(amounts, 50) if n > 0 else None
            p25_settlement = _percentile(amounts, 25) if n > 0 else None
            p75_settlement = _percentile(amounts, 75) if n > 0 else None
            avg_medical = sum(medical_bills_list) / len(medical_bills_list) if medical_bills_list else None
            avg_multiplier = (avg_settlement / avg_medical) if avg_settlement and avg_medical and avg_medical > 0 else None

            prev_count = prev_injury_counts.get(injury, 0)
            case_count_change = ((n - prev_count) / prev_count * 100) if prev_count > 0 else (100.0 if n > 0 else 0.0)

            trends.append(InjuryTypeTrend(
                injury_type=injury,
                total_cases=n,
                avg_settlement=round(avg_settlement, 2) if avg_settlement else None,
                median_settlement=round(median_settlement, 2) if median_settlement else None,
                p25_settlement=round(p25_settlement, 2) if p25_settlement else None,
                p75_settlement=round(p75_settlement, 2) if p75_settlement else None,
                avg_medical_bills=round(avg_medical, 2) if avg_medical else None,
                avg_multiplier=round(avg_multiplier, 2) if avg_multiplier else None,
                case_count_change_pct=round(case_count_change, 1),
            ))

        trends.sort(key=lambda t: t.total_cases, reverse=True)
        return trends

    async def _calculate_jurisdiction_trends(
        self,
        current_rows: List[dict],
        prev_rows: List[dict],
    ) -> List[JurisdictionTrend]:
        """Calculate jurisdiction trend data."""
        jurisdiction_data: Dict[str, List[dict]] = {}
        for row in current_rows:
            j = row.get("jurisdiction", "Unknown")
            if j not in jurisdiction_data:
                jurisdiction_data[j] = []
            jurisdiction_data[j].append(row)

        prev_jurisdiction_counts: Dict[str, int] = {}
        for row in prev_rows:
            j = row.get("jurisdiction", "Unknown")
            prev_jurisdiction_counts[j] = prev_jurisdiction_counts.get(j, 0) + 1

        trends = []
        for jurisdiction, rows in jurisdiction_data.items():
            amounts = []
            for row in rows:
                exact = row.get("exact_outcome_amount")
                if exact is not None:
                    amounts.append(exact)

            amounts.sort()
            n = len(amounts)
            avg_settlement = sum(amounts) / n if n > 0 else None
            median_settlement = _percentile(amounts, 50) if n > 0 else None

            prev_count = prev_jurisdiction_counts.get(jurisdiction, 0)
            case_count_change = ((n - prev_count) / prev_count * 100) if prev_count > 0 else (100.0 if n > 0 else 0.0)

            # Extract state from jurisdiction
            state = jurisdiction.rsplit(",", 1)[-1].strip() if "," in jurisdiction else "Unknown"

            if n >= 50:
                coverage_status = "adequate"
            elif n >= 10:
                coverage_status = "growing"
            else:
                coverage_status = "thin"

            trends.append(JurisdictionTrend(
                jurisdiction=jurisdiction,
                state=state,
                total_cases=n,
                avg_settlement=round(avg_settlement, 2) if avg_settlement else None,
                median_settlement=round(median_settlement, 2) if median_settlement else None,
                case_count_change_pct=round(case_count_change, 1),
                coverage_status=coverage_status,
            ))

        trends.sort(key=lambda t: t.total_cases, reverse=True)
        return trends

    async def _calculate_carrier_trends(
        self,
        current_rows: List[dict],
    ) -> List[CarrierCategoryTrend]:
        """Calculate carrier category trend data."""
        carrier_data: Dict[str, List[dict]] = {}
        for row in current_rows:
            cat = row.get("defendant_category", "Unknown")
            industry = row.get("insurance_carrier") or row.get("defendant_industry")
            key = f"{cat}::{industry or 'N/A'}"
            if key not in carrier_data:
                carrier_data[key] = []
            carrier_data[key].append(row)

        trends = []
        for key, rows in carrier_data.items():
            cat, industry = key.split("::", 1)
            if industry == "N/A":
                industry = None

            amounts = []
            settlement_count = 0
            trial_count = 0
            for row in rows:
                exact = row.get("exact_outcome_amount")
                if exact is not None:
                    amounts.append(exact)
                outcome = row.get("outcome_type", "")
                if outcome == "Settlement":
                    settlement_count += 1
                elif outcome in ("Jury Verdict", "Judge's Decision"):
                    trial_count += 1

            amounts.sort()
            n = len(amounts)
            avg_settlement = sum(amounts) / n if n > 0 else None
            total_resolved = settlement_count + trial_count
            settlement_rate = settlement_count / total_resolved if total_resolved > 0 else None
            trial_rate = trial_count / total_resolved if total_resolved > 0 else None

            # Lowball indicator: proportion below median
            median = _percentile(amounts, 50) if amounts else None
            lowball_count = sum(1 for a in amounts if a < median) if median else 0
            lowball_indicator = lowball_count / n if n > 0 else None

            trends.append(CarrierCategoryTrend(
                defendant_category=cat,
                defendant_industry=industry,
                total_cases=n,
                avg_settlement=round(avg_settlement, 2) if avg_settlement else None,
                settlement_rate=round(settlement_rate, 3) if settlement_rate is not None else None,
                trial_rate=round(trial_rate, 3) if trial_rate is not None else None,
                lowball_indicator=round(lowball_indicator, 3) if lowball_indicator is not None else None,
            ))

        trends.sort(key=lambda t: t.total_cases, reverse=True)
        return trends

    async def generate_coverage_gap_analysis(self) -> CoverageGapAnalysis:
        """Generate jurisdiction coverage gap analysis."""
        db = await get_db()

        if db is None:
            rows = []
        else:
            result = await db.table("settle_contributions").select("jurisdiction").eq("status", "approved").execute()
            rows = result.data or []

        jurisdiction_counts: Dict[str, int] = {}
        for row in rows:
            j = row.get("jurisdiction", "Unknown")
            jurisdiction_counts[j] = jurisdiction_counts.get(j, 0) + 1

        total = len(jurisdiction_counts)
        adequate = sum(1 for c in jurisdiction_counts.values() if c >= 50)
        growing = sum(1 for c in jurisdiction_counts.values() if 10 <= c < 50)
        thin = sum(1 for c in jurisdiction_counts.values() if c < 10)

        gaps = []
        for j, c in jurisdiction_counts.items():
            if c < 10:
                state = j.rsplit(",", 1)[-1].strip() if "," in j else "Unknown"
                gaps.append({"jurisdiction": j, "state": state, "case_count": c})

        gaps.sort(key=lambda g: g["case_count"])

        coverage_pct = ((adequate + growing) / total * 100) if total > 0 else 0

        recommendations = []
        if thin > 0:
            recommendations.append(f"{thin} jurisdictions have thin data (n<10). Focus Founding Member recruitment in these areas.")
        if adequate < total * 0.2:
            recommendations.append("Less than 20% of jurisdictions have adequate data (n>=50). Prioritize data collection.")

        return CoverageGapAnalysis(
            total_jurisdictions_tracked=total,
            jurisdictions_with_adequate_data=adequate,
            jurisdictions_with_growing_data=growing,
            jurisdictions_with_thin_data=thin,
            coverage_pct=round(coverage_pct, 1),
            gaps=gaps[:20],  # Top 20 gaps
            recommendations=recommendations,
        )

    async def generate_founding_member_highlights(self) -> FoundingMemberHighlights:
        """Generate Founding Member contribution highlights."""
        db = await get_db()

        # Get founding members + their contributions
        if db is None:
            fm_rows = []
            contrib_rows = []
        else:
            fm_result = await db.table("settle_founding_members").select("*").execute()
            fm_rows = fm_result.data or []
            contrib_result = await db.table("settle_contributions").select("contributor_user_id").eq("status", "approved").eq("founding_member", True).execute()
            contrib_rows = contrib_result.data or []

        total_fm = len(fm_rows)
        active_fm = sum(1 for r in fm_rows if r.get("status") == "active")
        total_contributions = len(contrib_rows)

        # Count per member
        member_counts: Dict[str, int] = {}
        for row in contrib_rows:
            uid = row.get("contributor_user_id")
            if uid:
                uid_str = str(uid)
                member_counts[uid_str] = member_counts.get(uid_str, 0) + 1

        active_contributors = len(member_counts)
        avg_per_member = total_contributions / active_contributors if active_contributors > 0 else 0

        # Top contributors
        top_sorted = sorted(member_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_contributors = [{"member_id": uid, "contributions": count} for uid, count in top_sorted]

        # Milestone achievements
        milestones = []
        for uid, count in member_counts.items():
            if count >= 100:
                milestones.append(f"Member {uid[:8]}... reached 100+ contributions")
            elif count >= 50:
                milestones.append(f"Member {uid[:8]}... reached 50+ contributions")
            elif count >= 10:
                milestones.append(f"Member {uid[:8]}... reached 10+ contributions (Founding Member requirement)")

        return FoundingMemberHighlights(
            total_founding_members=total_fm,
            active_contributors=active_contributors,
            total_contributions=total_contributions,
            avg_contributions_per_member=round(avg_per_member, 1),
            top_contributors=top_contributors,
            milestone_achievements=milestones[:10],
        )


def _percentile(sorted_data: List[float], percentile: int) -> Optional[float]:
    """Calculate percentile from sorted data."""
    if not sorted_data:
        return None
    n = len(sorted_data)
    k = (percentile / 100.0) * (n - 1)
    f = int(k)
    c = min(f + 1, n - 1)
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])


# Singleton instance
trend_report_generator = TrendReportGenerator()
