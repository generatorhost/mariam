from fastapi import APIRouter, Depends

from app.core.audit import AuditRecordRequest
from app.dependencies import get_audit_service
from app.services.audit import AuditService

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit_records(service: AuditService = Depends(get_audit_service)) -> dict:
    return {"audit_records": [record.model_dump(mode="json") for record in service.list()]}


@router.post("")
def create_audit_record(
    request: AuditRecordRequest,
    service: AuditService = Depends(get_audit_service),
) -> dict:
    record = service.record(request)
    return {"audit_record": record.model_dump(mode="json")}
