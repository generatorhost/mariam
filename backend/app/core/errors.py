from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


ERROR_CONTRACT_VERSION = "v1"
DATA_PLATFORM = "DB MARIAM"


def api_error_contract() -> dict[str, Any]:
    return {
        "title": "Mariam Structured API Error Response Contract",
        "version": ERROR_CONTRACT_VERSION,
        "status": "ready",
        "data_platform": DATA_PLATFORM,
        "applies_to": [
            "governed_endpoints",
            "permission_enforced_mutations",
            "runtime_routes",
            "plugin_routes",
            "artifact_routes",
        ],
        "required_fields": [
            "detail",
            "error.error_id",
            "error.code",
            "error.message",
            "error.status_code",
            "error.path",
            "error.method",
            "error.request_id",
            "error.data_platform",
            "error.traceability",
        ],
        "compatibility_rule": "Existing clients may continue reading detail while new clients use error.",
        "governance_rule": "Every governed API error must expose request traceability without secrets.",
        "acceptance_criteria": [
            "403 permission errors include a structured error object.",
            "404 not found errors include a structured error object.",
            "422 validation errors include a structured error object.",
            "No response includes secrets or credentials.",
        ],
    }


def build_error_payload(
    request: Request,
    *,
    status_code: int,
    detail: Any,
    code: str,
) -> dict[str, Any]:
    message = detail if isinstance(detail, str) else "Request failed."
    request_id = request.headers.get("x-mariam-request-id", "local-command-center-request")
    return {
        "detail": detail,
        "error": {
            "error_id": f"api-error-{uuid4()}",
            "code": code,
            "message": message,
            "status_code": status_code,
            "path": request.url.path,
            "method": request.method,
            "request_id": request_id,
            "data_platform": DATA_PLATFORM,
            "traceability": {
                "contract_version": ERROR_CONTRACT_VERSION,
                "source": "mariam-api-error-handler",
                "governed": request.url.path.startswith("/api/"),
            },
        },
    }


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    payload = build_error_payload(
        request,
        status_code=exc.status_code,
        detail=exc.detail,
        code=f"http_{exc.status_code}",
    )
    return JSONResponse(status_code=exc.status_code, content=payload, headers=getattr(exc, "headers", None))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    payload = build_error_payload(
        request,
        status_code=422,
        detail=exc.errors(),
        code="validation_failed",
    )
    return JSONResponse(status_code=422, content=payload)
