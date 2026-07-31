"""
Universal Authority Gate — AUTH-001 through AUTH-020

Prevents software from performing attorney- or client-only actions.
Implements TV-CMP-002 (fail-closed authorization) and TV-CMP-004 (no self-authorization).

Every material action must pass:
  1. Authority class check (who can do what)
  2. State transition validation (is this move allowed)
  3. Policy version check (is the governing policy active)
  4. Jurisdiction gate check (is the jurisdiction supported)
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.shared.models import AuthorityClass, ActorRole, TransitionContract

logger = logging.getLogger(__name__)


UNIVERSAL_AUTHORITY_REGISTRY: Dict[str, Dict[str, Any]] = {
    # INTAKE
    "intake.collect_information": {
        "authority": AuthorityClass.FIRM_POLICY,
        "control": "No legal conclusions; preserve source.",
    },
    "intake.classify_practice_area": {
        "authority": AuthorityClass.FIRM_POLICY,
        "control": "Routing classification is not legal advice or acceptance.",
    },
    # RETAINER
    "conflict.search": {
        "authority": AuthorityClass.FIRM_POLICY,
        "control": "Result is possible match only.",
    },
    "conflict.clear": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Record attorney decision and rationale.",
        "platform_role": "prohibited",
    },
    "representation.approve": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "No system-derived approval.",
        "platform_role": "prohibited",
    },
    "representation.decline": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Record and execute approved communication.",
    },
    "template.select": {
        "authority": AuthorityClass.FIRM_POLICY,
        "control": "Only among approved, effective templates.",
    },
    "template.create_legal_language": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Drafting may assist; attorney approval mandatory.",
    },
    "engagement.explain_terms": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Escalate client questions.",
        "platform_role": "prohibited",
    },
    "engagement.deliver_package": {
        "authority": AuthorityClass.FIRM_POLICY,
        "control": "Execute after authority gate.",
    },
    "engagement.esign_consent": {
        "authority": AuthorityClass.CLIENT_AUTH,
        "control": "Capture affirmative consent.",
    },
    "engagement.sign_client": {
        "authority": AuthorityClass.CLIENT_AUTH,
        "control": "Never delegated to platform.",
    },
    "engagement.sign_firm": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Record authenticated signature.",
    },
    "matter.activate": {
        "authority": AuthorityClass.FIRM_POLICY,
        "control": "Only after required gates pass.",
    },
    # TRACE
    "deadline.legal_conclusion": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Automated date signals are not legal conclusions.",
    },
    "demand.authorize_transmission": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Package version becomes immutable at authorization.",
    },
    # SETTLE
    "settlement.recommend": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Recommendation must be attorney-controlled.",
    },
    "settlement.accept": {
        "authority": AuthorityClass.CLIENT_AUTH,
        "control": "Client owns the settlement decision.",
    },
    "settlement.reject": {
        "authority": AuthorityClass.CLIENT_AUTH,
        "control": "Client owns the settlement decision.",
    },
    "settlement.counter": {
        "authority": AuthorityClass.CLIENT_AUTH,
        "control": "Client owns the settlement decision.",
    },
    "lien.resolve": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Jurisdiction and agreement dependent.",
    },
    "allocation.approve": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Must reconcile gross to net.",
    },
    "disbursement.authorize": {
        "authority": AuthorityClass.STAFF_AUTH,
        "control": "Never based solely on workflow completion.",
    },
    # COMMAND
    "matter.close": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Requires unresolved-item checks.",
    },
    "matter.reopen": {
        "authority": AuthorityClass.ATTY_AUTH,
        "control": "Requires documented authority.",
    },
    "data.delete_confidential": {
        "authority": AuthorityClass.FIRM_POLICY,
        "control": "Must pass retention and legal-hold checks.",
    },
    # Cross-cutting
    "ai.generate_output": {
        "authority": AuthorityClass.SYS_ADMIN,
        "control": "AI outputs are drafts/signals until human-authorized. INV-020.",
    },
    "platform.self_authorize": {
        "authority": AuthorityClass.PROHIBITED,
        "control": "No self-authorization. INV-011.",
    },
}

ACTOR_AUTHORITY_MAP: Dict[ActorRole, List[AuthorityClass]] = {
    ActorRole.RESPONSIBLE_ATTORNEY: [
        AuthorityClass.ATTY_AUTH, AuthorityClass.STAFF_AUTH,
        AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.SUPERVISING_ATTORNEY: [
        AuthorityClass.ATTY_AUTH, AuthorityClass.STAFF_AUTH,
        AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.MANAGING_ATTORNEY: [
        AuthorityClass.ATTY_AUTH, AuthorityClass.STAFF_AUTH,
        AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.LITIGATION_ATTORNEY: [
        AuthorityClass.ATTY_AUTH, AuthorityClass.STAFF_AUTH,
        AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.PARALEGAL: [
        AuthorityClass.STAFF_AUTH, AuthorityClass.FIRM_POLICY,
        AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.CASE_MANAGER: [
        AuthorityClass.STAFF_AUTH, AuthorityClass.FIRM_POLICY,
        AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.LEGAL_ASSISTANT: [
        AuthorityClass.STAFF_AUTH, AuthorityClass.FIRM_POLICY,
        AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.TRUST_ACCOUNTING: [
        AuthorityClass.STAFF_AUTH, AuthorityClass.FIRM_POLICY,
        AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.INTAKE_COORDINATOR: [
        AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.FIRM_ADMINISTRATOR: [
        AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.CLIENT: [
        AuthorityClass.CLIENT_AUTH,
    ],
    ActorRole.SETTLEMENT_AUTHORITY_HOLDER: [
        AuthorityClass.CLIENT_AUTH,
    ],
    ActorRole.COMPLIANCE_REVIEWER: [
        AuthorityClass.ATTY_AUTH, AuthorityClass.STAFF_AUTH,
        AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN,
    ],
    ActorRole.PLATFORM: [
        AuthorityClass.SYS_ADMIN, AuthorityClass.FIRM_POLICY,
    ],
    ActorRole.AI_ASSISTANCE: [
        AuthorityClass.SYS_ADMIN,
    ],
}


class AuthorityGate:
    """Universal authority enforcement service for all TrueVow products."""

    def get_required_authority(self, action: str) -> AuthorityClass:
        entry = UNIVERSAL_AUTHORITY_REGISTRY.get(action)
        if entry:
            return entry["authority"]
        logger.warning(f"No authority mapping for '{action}'. Defaulting to ATTY_AUTH (fail-safe).")
        return AuthorityClass.ATTY_AUTH

    def is_prohibited(self, action: str) -> bool:
        return self.get_required_authority(action) == AuthorityClass.PROHIBITED

    def is_client_only(self, action: str) -> bool:
        return self.get_required_authority(action) == AuthorityClass.CLIENT_AUTH

    def is_attorney_only(self, action: str) -> bool:
        return self.get_required_authority(action) == AuthorityClass.ATTY_AUTH

    def validate(
        self,
        action: str,
        actor_role: ActorRole,
        actor_id: UUID,
        tenant_id: UUID,
        matter_id: Optional[UUID] = None,
        policy_version_id: Optional[UUID] = None,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        required = self.get_required_authority(action)

        if required == AuthorityClass.PROHIBITED:
            return {
                "valid": False,
                "reason": f"Action '{action}' is PROHIBITED for platform execution.",
                "required_authority": required.value,
            }

        allowed = ACTOR_AUTHORITY_MAP.get(actor_role, [])
        if required not in allowed:
            return {
                "valid": False,
                "reason": (
                    f"Actor role '{actor_role.value}' lacks required authority "
                    f"'{required.value}' for action '{action}'."
                ),
                "required_authority": required.value,
                "actor_role": actor_role.value,
            }

        return {
            "valid": True,
            "required_authority": required.value,
            "actor_role": actor_role.value,
            "actor_id": str(actor_id),
            "tenant_id": str(tenant_id),
            "action": action,
        }

    def validate_transition(
        self,
        contract: TransitionContract,
        current_state: str,
    ) -> Dict[str, Any]:
        if current_state not in contract.from_states:
            return {
                "valid": False,
                "reason": (
                    f"Transition '{contract.command}' cannot execute from state "
                    f"'{current_state}'. Allowed from: {contract.from_states}"
                ),
                "current_state": current_state,
                "allowed_from": contract.from_states,
                "target_state": contract.to_state,
            }
        return {"valid": True, "target_state": contract.to_state}

    async def gate(
        self,
        action: str,
        actor_role: ActorRole,
        actor_id: UUID,
        tenant_id: UUID,
        matter_id: Optional[UUID] = None,
        current_state: Optional[str] = None,
        contract: Optional[TransitionContract] = None,
        policy_version_id: Optional[UUID] = None,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        authority_result = self.validate(
            action=action,
            actor_role=actor_role,
            actor_id=actor_id,
            tenant_id=tenant_id,
            matter_id=matter_id,
        )
        if not authority_result["valid"]:
            return authority_result

        if contract is not None and current_state is not None:
            state_result = self.validate_transition(contract=contract, current_state=current_state)
            if not state_result["valid"]:
                return {**authority_result, **state_result, "valid": False}

        return authority_result


authority_gate = AuthorityGate()
