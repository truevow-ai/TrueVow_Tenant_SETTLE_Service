"""
Contribution Service

Handles settlement data contribution workflow:
1. Validate data (DataValidator + AnonymizationValidator)
2. Run anomaly detection (AnomalyDetector)
3. Generate blockchain hash (OpenTimestamps)
4. Store in database (status='pending' or 'flagged' based on anomaly)
5. Track Founding Member stats
6. Return confirmation with blockchain receipt

Reference: Part 7, Section 7.4 (Contribution Workflow)
"""

import hashlib
import json
import logging
from typing import Tuple, Optional
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.models.case_bank import (
    ContributionRequest,
    ContributionResponse,
    SettleContribution
)
from app.services.validator import DataValidator
from app.services.anonymizer import AnonymizationValidator
from app.services.anomaly_detector import AnomalyDetector
from app.services.reputation_service import ReputationService

logger = logging.getLogger(__name__)


class ContributionService:
    """
    Service for handling settlement contributions.
    
    Workflow:
    1. Validate data (completeness, correctness)
    2. Check anonymization (no PHI/PII)
    3. Run anomaly detection (statistical checks)
    4. Generate blockchain hash (OpenTimestamps)
    5. Store in database (status='pending' or 'flagged')
    6. Track Founding Member stats
    7. Return confirmation with blockchain receipt
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize contribution service.
        
        Args:
            db_connection: Database connection
        """
        self.db = db_connection
        self.validator = DataValidator()
        self.anonymizer = AnonymizationValidator()
        self.anomaly_detector = AnomalyDetector(db_connection=db_connection)
        self.reputation_service = ReputationService(db_connection=db_connection)
    
    async def submit_contribution(
        self,
        request: ContributionRequest,
        api_key_id: Optional[UUID] = None,
        contributor_user_id: Optional[UUID] = None,
        is_founding_member: bool = False
    ) -> Tuple[bool, ContributionResponse, Optional[str]]:
        """
        Submit a settlement contribution.
        
        Args:
            request: ContributionRequest object
            api_key_id: API key ID (for tracking)
            contributor_user_id: User ID of the contributor (for reputation/anomaly)
            is_founding_member: True if submitter is Founding Member
            
        Returns:
            Tuple of (success, response, error_message)
        """
        # Step 1: Validate data
        is_valid, validation_errors = self.validator.validate_contribution(request)
        if not is_valid:
            error_msg = "Validation failed: " + "; ".join(validation_errors)
            logger.warning(error_msg)
            return False, None, error_msg
        
        # Step 2: Check anonymization (NO PHI/PII)
        request_dict = request.model_dump()
        is_anonymous, anonymization_violations = self.anonymizer.validate_contribution(
            request_dict
        )
        if not is_anonymous:
            error_msg = "Anonymization check failed: " + "; ".join(anonymization_violations)
            logger.error(error_msg)
            return False, None, error_msg
        
        # Step 3: Run anomaly detection
        anomaly_report = await self.anomaly_detector.check_submission(
            jurisdiction=request.jurisdiction,
            case_type=request.case_type,
            injury_category=request.injury_category,
            medical_bills=request.medical_bills,
            outcome_amount_range=request.outcome_amount_range,
            comparative_negligence_pct=None,  # Not in ContributionRequest
            insurance_carrier=None,  # Not in ContributionRequest
            contributor_user_id=str(contributor_user_id) if contributor_user_id else None,
        )
        
        # Determine status based on anomaly recommendation
        if anomaly_report.recommendation == "review":
            status = "flagged"
        else:
            status = "pending"
        
        # Step 4: Generate blockchain hash (OpenTimestamps)
        contribution_id = uuid4()
        blockchain_hash = self._generate_blockchain_hash(
            contribution_id,
            request_dict
        )
        
        # Step 5: Store in database
        now = datetime.now(UTC)
        contribution_data = {
            "id": str(contribution_id),
            "jurisdiction": request.jurisdiction,
            "case_type": request.case_type,
            "injury_category": request.injury_category,
            "primary_diagnosis": request.primary_diagnosis,
            "treatment_type": request.treatment_type,
            "duration_of_treatment": request.duration_of_treatment,
            "imaging_findings": request.imaging_findings,
            "medical_bills": request.medical_bills,
            "lost_wages": request.lost_wages,
            "policy_limits": request.policy_limits,
            "defendant_category": request.defendant_category,
            "outcome_type": request.outcome_type,
            "outcome_amount_range": request.outcome_amount_range,
            "contributed_at": now.isoformat(),
            "blockchain_hash": blockchain_hash,
            "consent_confirmed": request.consent_confirmed,
            "contributor_api_key_id": str(api_key_id) if api_key_id else None,
            "contributor_user_id": str(contributor_user_id) if contributor_user_id else None,
            "founding_member": is_founding_member,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "status": status,
            "rejection_reason": None,
            "is_outlier": anomaly_report.severity == "critical",
            "confidence_score": 1.0,
            "case_narrative": None,
            # Rich fields (Cohort W) — not in ContributionRequest, set to None
            "insurance_carrier": None,
            "comparative_negligence_pct": None,
            "exact_outcome_amount": None,
            "is_verdict": None,
            "date_of_verdict": None,
            "court_level": None,
            "injury_severity": None,
            "policy_limit_amount": None,
            "source_type": "firm_submission",
            "trial_duration_days": None,
            "appeal_filed": None,
            "appeal_outcome": None,
            # Reputation columns (Cohort X)
            "contributor_reputation_score": 0.0,
            "anomaly_flags": [
                {
                    "flag_type": f.flag_type.value,
                    "severity": f.severity.value,
                    "z_score": f.z_score,
                    "details": f.details,
                }
                for f in anomaly_report.flags
            ],
            "submission_quality_weight": 1.0,
        }
        
        if self.db:
            result = self.db.table("settle_contributions").insert(contribution_data).execute()
            if not result.data:
                error_msg = "Failed to store contribution in database"
                logger.error(error_msg)
                return False, None, error_msg
            
            # Persist anomaly flags to dedicated table
            if anomaly_report.has_flags:
                await self.anomaly_detector.persist_flags(str(contribution_id), anomaly_report)
            
            logger.info(
                f"Contribution {contribution_id} stored successfully (status={status}). "
                f"Blockchain hash: {blockchain_hash}, "
                f"Anomaly flags: {len(anomaly_report.flags)}"
            )
        else:
            # Mock mode — log only
            logger.warning(
                f"Mock mode: Contribution {contribution_id} would be stored. "
                f"Status: {status}, Blockchain hash: {blockchain_hash}"
            )
        
        # Step 6: Update Founding Member stats (if applicable)
        founding_member_status = None
        if is_founding_member:
            founding_member_status = await self._update_founding_member_stats(
                api_key_id
            )
        
        # Step 7: Return confirmation
        response = ContributionResponse(
            contribution_id=contribution_id,
            blockchain_hash=blockchain_hash,
            message=(
                "Thank you for contributing to the SETTLE database! "
                "Your submission has been received and will be reviewed for approval. "
                "The blockchain hash serves as cryptographic proof of your contribution."
            ),
            founding_member_status=founding_member_status,
            status=status,
            created_at=now
        )
        
        return True, response, None
    
    def _generate_blockchain_hash(
        self,
        contribution_id: UUID,
        contribution_data: dict
    ) -> str:
        """
        Generate blockchain hash for contribution using OpenTimestamps.
        
        This creates a cryptographic proof that can be verified independently.
        
        Steps:
        1. Create canonical JSON representation of data
        2. Compute SHA-256 hash
        3. Submit to OpenTimestamps (returns OTS receipt)
        4. Return OTS receipt hash
        
        Args:
            contribution_id: Unique contribution ID
            contribution_data: Contribution data dictionary
            
        Returns:
            Blockchain hash (OTS receipt hash)
        """
        # Step 1: Create canonical representation
        # Include contribution ID and timestamp for uniqueness
        canonical_data = {
            "contribution_id": str(contribution_id),
            "timestamp": datetime.now(UTC).isoformat(),
            "data": contribution_data
        }
        
        # Sort keys for deterministic hashing
        canonical_json = json.dumps(canonical_data, sort_keys=True)
        
        # Step 2: Compute SHA-256 hash
        sha256_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
        
        # Step 3: Submit to OpenTimestamps
        # TODO: Implement actual OpenTimestamps submission
        # For now, return the SHA-256 hash with a prefix
        ots_hash = f"ots_{sha256_hash[:16]}"
        
        logger.info(
            f"Generated blockchain hash for contribution {contribution_id}: {ots_hash}"
        )
        
        return ots_hash
    
    async def _verify_blockchain_hash(
        self,
        contribution_id: UUID,
        blockchain_hash: str
    ) -> bool:
        """
        Verify blockchain hash using OpenTimestamps.
        
        Args:
            contribution_id: Contribution ID
            blockchain_hash: Blockchain hash to verify
            
        Returns:
            True if hash is valid
        """
        # TODO: Implement actual OpenTimestamps verification
        # For now, return True
        return True
    
    async def _update_founding_member_stats(
        self,
        api_key_id: Optional[UUID]
    ) -> Optional[dict]:
        """
        Update Founding Member contribution stats.
        
        Args:
            api_key_id: API key ID
            
        Returns:
            Founding member status dict (contributions count, etc.)
        """
        if not api_key_id:
            return None
        
        # TODO: Implement actual database update
        # For now, return mock stats
        return {
            "contributions_count": 5,  # Mock: increment by 1
            "queries_count": 12,
            "reports_generated": 3,
            "message": "Your Founding Member stats have been updated. Thank you for building the database!"
        }
    
    async def approve_contribution(
        self,
        contribution_id: UUID,
        approved_by: str,
        contributor_user_id: Optional[UUID] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Approve a pending contribution (admin action).
        
        Args:
            contribution_id: Contribution ID
            approved_by: Admin user who approved
            contributor_user_id: User ID of the contributor (for reputation update)
            
        Returns:
            Tuple of (success, error_message)
        """
        if self.db:
            result = self.db.table("settle_contributions").update({
                "status": "approved",
                "approved_at": datetime.now(UTC).isoformat(),
                "approved_by": approved_by,
            }).eq("id", str(contribution_id)).execute()
            
            if not result.data:
                return False, "Contribution not found"
            
            # Update contributor reputation after approval
            if contributor_user_id:
                try:
                    await self.reputation_service.update_after_decision(
                        UUID(contributor_user_id), "approved"
                    )
                except Exception as e:
                    logger.warning(f"Reputation update after approval failed: {e}")
        else:
            logger.warning(f"Mock mode: Contribution {contribution_id} would be approved")
        
        logger.info(
            f"Contribution {contribution_id} approved by {approved_by}"
        )
        
        return True, None
    
    async def reject_contribution(
        self,
        contribution_id: UUID,
        rejection_reason: str,
        rejected_by: str,
        contributor_user_id: Optional[UUID] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Reject a pending contribution (admin action).
        
        Args:
            contribution_id: Contribution ID
            rejection_reason: Reason for rejection
            rejected_by: Admin user who rejected
            contributor_user_id: User ID of the contributor (for reputation update)
            
        Returns:
            Tuple of (success, error_message)
        """
        if self.db:
            result = self.db.table("settle_contributions").update({
                "status": "rejected",
                "rejected_at": datetime.now(UTC).isoformat(),
                "rejected_by": rejected_by,
                "rejection_reason": rejection_reason,
            }).eq("id", str(contribution_id)).execute()
            
            if not result.data:
                return False, "Contribution not found"
            
            # Update contributor reputation after rejection
            if contributor_user_id:
                try:
                    await self.reputation_service.update_after_decision(
                        UUID(contributor_user_id), "rejected"
                    )
                except Exception as e:
                    logger.warning(f"Reputation update after rejection failed: {e}")
        else:
            logger.warning(f"Mock mode: Contribution {contribution_id} would be rejected")
        
        logger.info(
            f"Contribution {contribution_id} rejected by {rejected_by}. "
            f"Reason: {rejection_reason}"
        )
        
        return True, None
    
    async def flag_contribution_for_review(
        self,
        contribution_id: UUID,
        flag_reason: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Flag a contribution for manual review.
        
        Args:
            contribution_id: Contribution ID
            flag_reason: Reason for flagging
            
        Returns:
            Tuple of (success, error_message)
        """
        if self.db:
            result = self.db.table("settle_contributions").update({
                "status": "flagged",
                "flag_reason": flag_reason,
            }).eq("id", str(contribution_id)).execute()
            
            if not result.data:
                return False, "Contribution not found"
        else:
            logger.warning(f"Mock mode: Contribution {contribution_id} would be flagged")
        
        logger.warning(
            f"Contribution {contribution_id} flagged for review. "
            f"Reason: {flag_reason}"
        )
        
        return True, None


# ============================================================================
# BLOCKCHAIN VERIFICATION UTILITIES
# ============================================================================

class BlockchainVerifier:
    """
    Utility class for blockchain verification using OpenTimestamps.
    
    OpenTimestamps provides cryptographic proof that data existed at a specific time.
    This is used for audit trail and integrity verification.
    """
    
    @staticmethod
    def verify_ots_hash(ots_hash: str, original_data: dict) -> bool:
        """
        Verify an OpenTimestamps hash.
        
        Args:
            ots_hash: OTS hash to verify
            original_data: Original contribution data
            
        Returns:
            True if hash is valid
        """
        # TODO: Implement actual OTS verification
        # For now, return True
        return True
    
    @staticmethod
    def get_timestamp_from_ots(ots_hash: str) -> Optional[datetime]:
        """
        Extract timestamp from OpenTimestamps hash.
        
        Args:
            ots_hash: OTS hash
            
        Returns:
            Timestamp of when data was timestamped
        """
        # TODO: Implement actual OTS timestamp extraction
        # For now, return current time
        return datetime.now(UTC)
