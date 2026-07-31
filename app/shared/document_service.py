"""
Document Service — Generates, versions, signs, delivers, and preserves documents.

INV-006: Every sent, filed, or executed document references an immutable
Document Version and hash. Later changes produce a new version.
"""

import logging
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.shared.models import (
    DocumentVersion, SignatureEvidence, ActorRole,
)

logger = logging.getLogger(__name__)


class DocumentService:
    """Manages document lifecycle: creation, versioning, approval, signing, delivery."""

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    async def create_document(
        self,
        tenant_id: UUID,
        document_type: str,
        title: str,
        content: str,
        matter_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        mime_type: str = "text/plain",
        generated_from_template_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[DocumentVersion]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        content_hash = self.compute_hash(content)
        doc_id = uuid4()

        record = {
            "id": str(doc_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(matter_id) if matter_id else None,
            "document_type": document_type,
            "title": title,
            "version": 1,
            "content_hash": content_hash,
            "mime_type": mime_type,
            "byte_size": len(content.encode()),
            "state": "draft",
            "generated_from_template_id": str(generated_from_template_id) if generated_from_template_id else None,
            "created_by": str(created_by) if created_by else None,
            "metadata": metadata or {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("document_versions").insert(record).execute()
        if not result.data:
            return None
        return DocumentVersion(**result.data[0])

    async def get_document(self, doc_id: UUID) -> Optional[DocumentVersion]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("document_versions").select("*").eq("id", str(doc_id)).execute()
        if not result.data:
            return None
        return DocumentVersion(**result.data[0])

    async def approve_document(
        self, doc_id: UUID, approved_by: UUID,
    ) -> Optional[DocumentVersion]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        result = db.table("document_versions").update({
            "state": "approved",
            "approved_by": str(approved_by),
            "approved_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("id", str(doc_id)).execute()
        if not result.data:
            return None
        return DocumentVersion(**result.data[0])

    async def create_new_version(
        self,
        doc_id: UUID,
        new_content: str,
        created_by: Optional[UUID] = None,
    ) -> Optional[DocumentVersion]:
        existing = await self.get_document(doc_id)
        if existing is None:
            return None

        now = datetime.now(UTC)
        content_hash = self.compute_hash(new_content)
        new_id = uuid4()

        db = await get_db()
        record = {
            "id": str(new_id),
            "tenant_id": str(existing.tenant_id),
            "matter_id": str(existing.matter_id) if existing.matter_id else None,
            "document_type": existing.document_type,
            "title": existing.title,
            "version": existing.version + 1,
            "content_hash": content_hash,
            "mime_type": existing.mime_type,
            "byte_size": len(new_content.encode()),
            "state": "draft",
            "lineage_id": str(existing.id),
            "created_by": str(created_by) if created_by else None,
            "metadata": existing.metadata,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("document_versions").insert(record).execute()
        if not result.data:
            return None

        await db.table("document_versions").update({
            "state": "superseded",
            "superseded_by_id": str(new_id),
            "updated_at": now.isoformat(),
        }).eq("id", str(doc_id)).execute()

        return DocumentVersion(**result.data[0])

    async def record_signature(
        self,
        tenant_id: UUID,
        document_version_id: UUID,
        signer_id: UUID,
        signer_role: ActorRole,
        document_hash: str,
        signature_type: str = "electronic",
        esign_consent_id: Optional[UUID] = None,
        authentication_method: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
        intent_confirmed: bool = True,
    ) -> Optional[SignatureEvidence]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        sig_id = uuid4()
        record = {
            "id": str(sig_id),
            "tenant_id": str(tenant_id),
            "document_version_id": str(document_version_id),
            "signer_id": str(signer_id),
            "signer_role": signer_role.value,
            "signature_type": signature_type,
            "esign_consent_id": str(esign_consent_id) if esign_consent_id else None,
            "authentication_method": authentication_method,
            "authentication_timestamp": now.isoformat(),
            "signature_timestamp": now.isoformat(),
            "ip_address": ip_address,
            "device_info": device_info or {},
            "document_hash_at_signing": document_hash,
            "intent_confirmed": intent_confirmed,
            "evidence_package": {
                "timestamp": now.isoformat(),
                "signature_type": signature_type,
                "ip_address": ip_address,
            },
            "created_at": now.isoformat(),
        }
        result = db.table("signature_evidences").insert(record).execute()
        if not result.data:
            return None

        await db.table("document_versions").update({
            "state": "executed",
            "executed_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("id", str(document_version_id)).execute()

        return SignatureEvidence(**result.data[0])

    async def get_documents_by_matter(self, matter_id: UUID) -> list:
        db = await get_db()
        if db is None:
            return []
        result = db.table("document_versions").select("*").eq("matter_id", str(matter_id)).order("created_at", desc=True).execute()
        if not result.data:
            return []
        return result.data

    async def get_latest_version(self, matter_id: UUID, document_type: str) -> Optional[DocumentVersion]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("document_versions").select("*").eq("matter_id", str(matter_id)).eq("document_type", document_type).order("version", desc=True).limit(1).execute()
        if not result.data:
            return None
        return DocumentVersion(**result.data[0])

    async def get_signature_evidence(self, document_version_id: UUID) -> list:
        db = await get_db()
        if db is None:
            return []
        result = db.table("signature_evidences").select("*").eq("document_version_id", str(document_version_id)).execute()
        if not result.data:
            return []
        return result.data


document_service = DocumentService()
