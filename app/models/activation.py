"""
Matter Activation Contract — SETTLE Service v1.0.1

Defines the canonical matter.activated payload that SETTLE receives from TRACE
when a matter enters the resolution domain.

SETTLE follows TRACE. It receives activated matters that have cleared all
engagement, conflict, authority, and jurisdiction gates.

The activation payload carries the minimum set of references SETTLE needs to
initialize resolution workflows. An immutable evidence manifest (stored by
SaaS Admin) contains the full activation evidence chain.
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class MatterActivationPayload(BaseModel):
    """Canonical matter.activated payload — single machine-readable contract.

    This is the payload SETTLE receives from TRACE via webhook when a matter
    enters the resolution domain.

    11 required fields + schema_version. Product extensions prohibited at root.
    Additional evidence references belong in the immutable evidence_manifest
    stored by SaaS Admin, retrievable by activation_id.
    """
    matter_id: UUID
    activation_id: UUID
    evidence_manifest_id: UUID
    source_matter_candidate_id: UUID
    client_party_role_id: UUID
    responsible_attorney_assignment_id: UUID
    jurisdiction_profile_version_id: UUID
    activation_policy_version_id: UUID
    engagement_workflow_id: UUID
    occurred_at: datetime
    schema_version: str = "1.0.1"


class MatterActivationEvidenceManifest(BaseModel):
    """Immutable evidence manifest — all 9 activation evidence references.

    Stored by SaaS Admin. Retrieved by TRACE / SETTLE using activation_id.
    Every reference is mandatory. No evidence becomes optional merely because
    it is stored in the manifest rather than the webhook payload.

    The 9 required evidence references (none optional):
      1. representation_decision_id
      2. conflict_clearance_authority_id
      3. engagement_workflow_id
      4. executed_package_id
      5. signature_evidence_ids
      6. completed_copy_delivery_id
      7. responsible_attorney_assignment_id
      8. jurisdiction_profile_version_id
      9. activation_policy_version_id
    """
    model_config = ConfigDict(from_attributes=True)

    manifest_id: UUID
    activation_id: UUID
    representation_decision_id: UUID
    conflict_clearance_authority_id: UUID
    engagement_workflow_id: UUID
    executed_package_id: UUID
    signature_evidence_ids: list[UUID]
    completed_copy_delivery_id: UUID
    responsible_attorney_assignment_id: UUID
    jurisdiction_profile_version_id: UUID
    activation_policy_version_id: UUID
    generated_at: datetime
    schema_version: str = "1.0.1"


class MatterActivatedWebhook(BaseModel):
    """The full webhook envelope SETTLE receives from TRACE.

    Headers (verified by webhook auth):
      X-TrueVow-Key-Id
      X-TrueVow-Timestamp
      X-TrueVow-Signature

    Body:
      event_type: "matter.activated"
      payload: MatterActivationPayload
    """
    event_type: str = "matter.activated"
    event_id: UUID
    payload: MatterActivationPayload
    tenant_id: UUID
    occurred_at: datetime
    schema_version: str = "1.0.1"


class MatterResolutionContext(BaseModel):
    """SETTLE resolution context built from activation payload.

    This is what SETTLE stores locally when it receives a matter.activated
    webhook. It links the activated matter to all its resolution workflows.

    The matter record (ENT-041) is the canonical source. This context provides
    the activation evidence references needed for audit and downstream workflows.
    """
    matter_id: UUID
    activation_id: UUID
    evidence_manifest_id: UUID
    source_matter_candidate_id: UUID
    client_party_role_id: UUID
    responsible_attorney_assignment_id: UUID
    jurisdiction_profile_version_id: UUID
    activation_policy_version_id: UUID
    engagement_workflow_id: UUID
    activated_at: datetime
    resolution_state: str = "active_prelitigation"
    tenant_id: UUID
    schema_version: str = "1.0.1"
    created_at: datetime
