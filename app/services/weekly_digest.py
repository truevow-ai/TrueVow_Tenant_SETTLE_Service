"""
Weekly Intelligence Digest Service — Phase 3.4

Automated email digest sent to active users with:
- New comparable cases in their jurisdictions
- Stale data alerts
- Coverage gaps
- Trend highlights

Extends existing email_service.py with digest template.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, UTC
from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# DIGEST MODELS
# ============================================================================

class DigestContent(BaseModel):
    """Content for a weekly intelligence digest email."""
    user_email: str
    user_name: Optional[str] = None
    week_start: str
    week_end: str
    new_cases_count: int
    new_cases_by_jurisdiction: List[Dict[str, Any]]
    stale_jurisdictions: List[str]
    coverage_gaps: List[str]
    trend_highlights: List[str]
    total_contributions: int
    total_queries: int


# ============================================================================
# DIGEST GENERATOR
# ============================================================================

class WeeklyDigestGenerator:
    """Generates weekly intelligence digest content."""

    async def generate_digest(
        self,
        user_email: str,
        user_jurisdictions: Optional[List[str]] = None,
        user_case_types: Optional[List[str]] = None,
    ) -> DigestContent:
        """
        Generate weekly digest content for a user.

        Args:
            user_email: User's email address
            user_jurisdictions: User's jurisdictions of interest
            user_case_types: User's case types of interest

        Returns:
            DigestContent with email content
        """
        db = await get_db()

        now = datetime.now(UTC)
        week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        # New cases this week
        query = db.table("settle_contributions").select("jurisdiction, case_type").eq("status", "approved").gte("created_at", week_start.isoformat())

        if user_jurisdictions:
            # Use first jurisdiction for simple filter
            query = query.ilike("jurisdiction", f"%{user_jurisdictions[0].split(',')[-1].strip()}%")

        result = await query.execute()
        rows = result.data or []

        # Count by jurisdiction
        jur_counts: Dict[str, int] = {}
        for row in rows:
            j = row.get("jurisdiction", "Unknown")
            jur_counts[j] = jur_counts.get(j, 0) + 1

        new_cases_by_jurisdiction = [
            {"jurisdiction": j, "count": c}
            for j, c in sorted(jur_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Stale jurisdictions (no new cases in 30 days)
        thirty_days_ago = (now - timedelta(days=30)).isoformat()
        stale_query = db.table("settle_contributions").select("jurisdiction").eq("status", "approved").lt("created_at", thirty_days_ago)
        stale_result = await stale_query.execute()
        stale_rows = stale_result.data or []

        stale_jurs: Dict[str, datetime] = {}
        for row in stale_rows:
            j = row.get("jurisdiction", "Unknown")
            if j not in stale_jurs:
                stale_jurs[j] = datetime.fromisoformat(row.get("created_at", ""))

        stale_jurisdictions = list(stale_jurs.keys())[:5]

        # Coverage gaps (jurisdictions with n<50)
        all_query = db.table("settle_contributions").select("jurisdiction").eq("status", "approved")
        all_result = await all_query.execute()
        all_rows = all_result.data or []

        all_counts: Dict[str, int] = {}
        for row in all_rows:
            j = row.get("jurisdiction", "Unknown")
            all_counts[j] = all_counts.get(j, 0) + 1

        coverage_gaps = [j for j, c in all_counts.items() if c < 50][:5]

        # Trend highlights
        trend_highlights = []
        if len(rows) > 0:
            trend_highlights.append(f"{len(rows)} new cases added this week")
        if len(coverage_gaps) > 0:
            trend_highlights.append(f"{len(coverage_gaps)} jurisdictions need more data (n<50)")

        # Total stats
        total_result = await db.table("settle_contributions").select("id", count="exact").eq("status", "approved").execute()
        total_contributions = total_result.count or 0

        total_queries = 0  # Would need settle_queries table

        return DigestContent(
            user_email=user_email,
            week_start=week_start.strftime("%Y-%m-%d"),
            week_end=week_end.strftime("%Y-%m-%d"),
            new_cases_count=len(rows),
            new_cases_by_jurisdiction=new_cases_by_jurisdiction,
            stale_jurisdictions=stale_jurisdictions,
            coverage_gaps=coverage_gaps,
            trend_highlights=trend_highlights,
            total_contributions=total_contributions,
            total_queries=total_queries,
        )

    def generate_html_email(self, content: DigestContent) -> str:
        """Generate HTML email body from digest content."""
        jurisdiction_rows = ""
        for item in content.new_cases_by_jurisdiction:
            jurisdiction_rows += f"<tr><td>{item['jurisdiction']}</td><td>{item['count']}</td></tr>"

        stale_list = "".join(f"<li>{j}</li>" for j in content.stale_jurisdictions)
        gap_list = "".join(f"<li>{j}</li>" for j in content.coverage_gaps)
        trend_list = "".join(f"<li>{t}</li>" for t in content.trend_highlights)

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #667eea;">SETTLE Weekly Intelligence Digest</h1>
            <p>Week of {content.week_start} — {content.week_end}</p>

            <h2>New Cases This Week: {content.new_cases_count}</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #f3f4f6;"><th style="padding: 8px; text-align: left;">Jurisdiction</th><th style="padding: 8px; text-align: center;">Cases</th></tr>
                {jurisdiction_rows}
            </table>

            <h2>Stale Data Alerts</h2>
            <ul>{stale_list or "<li>No stale data alerts</li>"}</ul>

            <h2>Coverage Gaps</h2>
            <ul>{gap_list or "<li>All jurisdictions have adequate coverage</li>"}</ul>

            <h2>Trend Highlights</h2>
            <ul>{trend_list or "<li>No notable trends this week</li>"}</ul>

            <hr>
            <p style="color: #6b7280; font-size: 12pt;">
                Database: {content.total_contributions} total approved contributions.
            </p>
            <p style="color: #6b7280; font-size: 10pt;">
                SETTLE — Descriptive statistics from anonymized settlement contributions. Not predictive.
            </p>
        </body>
        </html>
        """


# Singleton instance
weekly_digest_generator = WeeklyDigestGenerator()
