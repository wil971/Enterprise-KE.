import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse

from config import ()
    APP_NAME,
    ENVIRONMENT,
    MAX_DOCUMENT_LENGTH,
    MAX_DOCUMENT_TITLE_LENGTH,
    MAX_QUERY_LENGTH,
    logger,
)

from database import get_driver, close_driver, init_driver

from security import (
    AuthenticationError,
    AuthorizationError,
    AuditLogError,
    RateLimitExceeded,
    SecurityError,
    ValidationError,
    authorize_request,
    validate_request_id,
    validate_tenant_id,
    write_audit_log,
    PERMISSION_INGEST,
    PERMISSION_SEARCH,
)

from refiner import (
    extract_business_entities,
    validate_extraction,
    store_business_document,
)

from retrieval import secure_graph_retrieval


# ==============================================================================
# APPLICATION
# ==============================================================================

mcp = FastMCP(APP_NAME)

# This is intentionally NOT a default tenant.
# In production it must be configured in Render/environment variables.
SERVICE_TENANT_ID = os.getenv("SERVICE_TENANT_ID", "").strip()

# The current API-key model represents one authenticated service identity.
# "api-client" is therefore not pretending to be a real human user.
SERVICE_USER_ID = "api-client"
SERVICE_ROLE = "service"


# ==============================================================================
# VALIDATION HELPERS
# ==============================================================================

def _require_service_tenant() -> str:
    """
    Return the tenant bound to this backend deployment.

    The server must know which tenant the current API credential belongs to.
    We do not trust a caller-supplied tenant ID as proof of tenant ownership.
    """
    if not SERVICE_TENANT_ID:
        raise RuntimeError(
            "SERVICE_TENANT_ID is not configured on the server."
        )

    return validate_tenant_id(SERVICE_TENANT_ID)


def _validate_search_topic(topic: str) -> str:
    """Validate and normalize a search topic."""
    if not isinstance(topic, str):
        raise ValidationError("Search topic must be a string.")

    topic = topic.strip()

    if not topic:
        raise ValidationError("Search topic cannot be empty.")

    if len(topic) > MAX_QUERY_LENGTH:
        raise ValidationError(
            f"Search topic exceeds the maximum length of "
            f"{MAX_QUERY_LENGTH} characters."
        )

    return topic


def _validate_document_title(title: str) -> str:
    """Validate and normalize a document title."""
    if not isinstance(title, str):
        raise ValidationError("Document title must be a string.")

    title = title.strip()

    if not title:
        raise ValidationError("Document title cannot be empty.")

    if len(title) > MAX_DOCUMENT_TITLE_LENGTH:
        raise ValidationError(
            f"Document title exceeds the maximum length of "
            f"{MAX_DOCUMENT_TITLE_LENGTH} characters."
        )

    return title


def _validate_document_text(text: str) -> str:
    """Validate and normalize document content."""
    if not isinstance(text, str):
        raise ValidationError("Document text must be a string.")

    text = text.strip()

    if not text:
        raise ValidationError("Document text cannot be empty.")

    if len(text) > MAX_DOCUMENT_LENGTH:
        raise ValidationError(
            f"Document exceeds the maximum size of "
            f"{MAX_DOCUMENT_LENGTH} characters."
        )

    return text


def _normalize_request_id(request_id: Optional[str]) -> str:
    """
    Validate a caller-provided request ID or create one.

    Request IDs are used only for tracing and auditing.
    """
    if request_id is None or not str(request_id).strip():
        return str(uuid.uuid4())

    return validate_request_id(str(request_id).strip())


# ==============================================================================
# AUTHORIZATION
# ==============================================================================

def _authorize(
    api_key: str,
    tenant_id: str,
    permission: str,
    request_id: str,
):
    """
    Authenticate the API key and authorize access to the server-bound tenant.

    The caller cannot select an arbitrary tenant because the authenticated
    tenant comes from SERVICE_TENANT_ID on the server.
    """
    server_tenant_id = _require_service_tenant()

    return authorize_request(
        api_key=api_key,
        requested_tenant_id=tenant_id,
        authenticated_tenant_id=server_tenant_id,
        permission=permission,
        user_id=SERVICE_USER_ID,
        role=SERVICE_ROLE,
        request_id=request_id,
    )


# ==============================================================================
# ERROR HANDLING
# ==============================================================================

def _public_error_message(error: Exception) -> str:
    """
    Convert internal exceptions into safe messages.

    Raw exception strings are deliberately not returned to callers because
    they can expose database, network, filesystem, or provider internals.
    """
    if isinstance(error, AuthenticationError):
        return "Authentication failed."

    if isinstance(error, RateLimitExceeded):
        return "Rate limit exceeded. Please try again later."

    if isinstance(error, AuthorizationError):
        return "You are not authorized to perform this operation."

    if isinstance(error, ValidationError):
        return str(error)

    if isinstance(error, SecurityError):
        return "Security validation failed."

    return "Internal server error."


# ==============================================================================
# AUDIT
# ==============================================================================

async def _record_audit(
    context: Any,
    action: str,
    outcome: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Persist an audit event.

    Returns True when the audit record was successfully persisted.
    Returns False when audit persistence itself fails.
    """
    try:
        await write_audit_log(
            tenant_id=context.tenant_id,
            action=action,
            request_id=context.request_id,
            user_id=context.user_id,
            role=context.role,
            outcome=outcome,
            metadata=metadata or {},
        )
        return True

    except AuditLogError:
        logger.exception(
            "Audit persistence failed "
            "request_id=%s action=%s outcome=%s",
            context.request_id,
            action,
            outcome,
        )
        return False

    except Exception:
        logger.exception(
            "Unexpected audit failure "
            "request_id=%s action=%s outcome=%s",
            context.request_id,
            action,
            outcome,
        )
        return False


# ==============================================================================
# ENTERPRISE SEARCH
# ==============================================================================

@mcp.tool()
async def enterprise_search(
    tenant_id: str,
    topic: str,
    api_key: str,
    request_id: Optional[str] = None,
) -> str:
    """
    Securely search enterprise knowledge belonging to the authenticated tenant.

    Authentication and tenant authorization happen before graph retrieval.
    """
    request_id = _normalize_request_id(request_id)

    context = None

    try:
        topic = _validate_search_topic(topic)
        tenant_id = validate_tenant_id(tenant_id)

        context = _authorize(
            api_key=api_key,
            tenant_id=tenant_id,
            permission=PERMISSION_SEARCH,
            request_id=request_id,
        )

        result = await secure_graph_retrieval(
            context.tenant_id,
            topic,
        )

        audit_recorded = await _record_audit(
            context=context,
            action="enterprise_search",
            outcome="success",
            metadata={
                "query_length": len(topic),
            },
        )

        # The retrieval layer currently returns its own JSON/text response.
        # We preserve that response instead of inventing a new response schema.
        if isinstance(result, str):
            try:
                parsed = json.loads(result)

                if isinstance(parsed, dict):
                    parsed["request_id"] = request_id
                    parsed["audit_recorded"] = audit_recorded
                    return json.dumps(parsed, indent=2)

            except json.JSONDecodeError:
                pass

        return json.dumps(
            {
                "success": True,
                "request_id": request_id,
                "audit_recorded": audit_recorded,
                "result": result,
            },
            indent=2,
            default=str,
        )

    except SecurityError as exc:
        logger.warning(
            "Search security failure request_id=%s error_type=%s",
            request_id,
            type(exc).__name__,
        )

        if context is not None:
            await _record_audit(
                context=context,
                action="enterprise_search",
                outcome="denied",
                metadata={},
            )

        return json.dumps(
            {
                "success": False,
                "error": _public_error_message(exc),
                "request_id": request_id,
            },
            indent=2,
        )

    except Exception:
        logger.exception(
            "Enterprise search failed request_id=%s",
            request_id,
        )

        if context is not None:
            await _record_audit(
                context=context,
                action="enterprise_search",
                outcome="failed",
                metadata={},
            )

        return json.dumps(
            {
                "success": False,
                "error": "Internal server error.",
                "request_id": request_id,
            },
            indent=2,
        )


# ==============================================================================
# DOCUMENT INGESTION
# ==============================================================================

@mcp.tool()
async def ingest_business_document(
    tenant_id: str,
    title: str,
    text: str,
    api_key: str,
    request_id: Optional[str] = None,
) -> str:
    """
    Extract structured business information and store a document
    in the authenticated tenant's knowledge graph.
    """
    request_id = _normalize_request_id(request_id)

    context = None
    document_id = str(uuid.uuid4())

    try:
        tenant_id = validate_tenant_id(tenant_id)
        title = _validate_document_title(title)
        text = _validate_document_text(text)

        context = _authorize(
            api_key=api_key,
            tenant_id=tenant_id,
            permission=PERMISSION_INGEST,
            request_id=request_id,
        )

        # ------------------------------------------------------------------
        # AI / structured extraction
        # ------------------------------------------------------------------

        extracted = extract_business_entities(text)
        extracted = validate_extraction(extracted)

        # ------------------------------------------------------------------
        # Persist the document and its extracted graph information
        # ------------------------------------------------------------------

        await store_business_document(
            context.tenant_id,
            document_id,
            title,
            text,
            extracted,
        )

        # ------------------------------------------------------------------
        # Audit successful ingestion
        # ------------------------------------------------------------------

        audit_recorded = await _record_audit(
            context=context,
            action="document_ingestion",
            outcome="success",
            metadata={
                "document_id": document_id,
                "title_length": len(title),
                "document_length": len(text),
            },
        )

        return json.dumps(
            {
                "success": True,
                "document_id": document_id,
                "request_id": request_id,
                "audit_recorded": audit_recorded,
                "extracted": extracted,
            },
            indent=2,
            default=str,
        )

    except SecurityError as exc:
        logger.warning(
            "Document ingestion security failure "
            "request_id=%s error_type=%s",
            request_id,
            type(exc).__name__,
        )

        if context is not None:
            await _record_audit(
                context=context,
                action="document_ingestion",
                outcome="denied",
                metadata={
                    "document_id": document_id,
                },
            )

        return json.dumps(
            {
                "success": False,
                "error": _public_error_message(exc),
                "request_id": request_id,
            },
            indent=2,
        )

    except Exception:
        logger.exception(
            "Document ingestion failed request_id=%s document_id=%s",
            request_id,
            document_id,
        )

        if context is not None:
            await _record_audit(
                context=context,
                action="document_ingestion",
                outcome="failed",
                metadata={
                    "document_id": document_id,
                },
            )

        return json.dumps(
            {
                "success": False,
                "error": "Internal server error.",
                "request_id": request_id,
            },
            indent=2,
        )


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

async def _database_health() -> str:
    """
    Perform a real Neo4j connectivity check.

    Driver existence alone is not considered proof that the database is healthy.
    """
    driver = get_driver()

    if driver is None:
        return "not_configured"

    try:
        await driver.verify_connectivity()
        return "healthy"

    except Exception:
        logger.exception("Neo4j health check failed.")
        return "unhealthy"


async def _health_payload() -> Dict[str, Any]:
    """Build the current health response."""
    database_status = await _database_health()

    if database_status == "healthy":
        overall_status = "healthy"
    elif database_status == "not_configured":
        overall_status = "not_configured"
    else:
        overall_status = "degraded"

    return {
        "service": APP_NAME,
        "status": overall_status,
        "database": database_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
async def system_health() -> str:
    """
    Return the current service health.

    This endpoint intentionally exposes only operational status.
    It does not expose credentials, database URLs, environment variables,
    or other infrastructure secrets.
    """
    try:
        payload = await _health_payload()

        return json.dumps(
            payload,
            indent=2,
        )

    except Exception:
        logger.exception("System health check failed.")

        return json.dumps(
            {
                "service": APP_NAME,
                "status": "degraded",
                "database": "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )


# ==============================================================================
# GRAPH SCHEMA RESOURCE
# ==============================================================================

@mcp.resource("config://tenant-schema")
def get_schema() -> str:
    """
    Describe the graph model currently used by the backend.
    """
    return """
Aether Enterprise Knowledge Graph

Core node labels:
- Tenant
- Document
- Client
- Project
- Entity
- AuditLog

Core relationships currently used:
- Tenant -[:OWNS]-> Document
- Document -[:MENTIONS]-> Client
- Document -[:MENTIONS]-> Project
- Document -[:MENTIONS]-> Entity
- Client -[:OWNS_PROJECT]-> Project

Security model:
- Protected operations require authentication.
- Protected operations are bound to the server-configured tenant.
- Graph queries must remain tenant-scoped.
- Audit records are associated with the authenticated tenant.
"""


# ==============================================================================
# HOMEPAGE
# ==============================================================================

@mcp.custom_route("/", methods=["GET"])
async def homepage(request: Request) -> HTMLResponse:
    """
    Lightweight operational landing page.

    The status shown here is generated from a real database connectivity check;
    it is not a hard-coded "Live & Operational" message.
    """
    payload = await _health_payload()

    status = payload["status"]
    database = payload["database"]

    if status == "healthy":
        status_label = "Operational"
    elif status == "degraded":
        status_label = "Degraded"
    elif status == "not_configured":
        status_label = "Database Not Configured"
    else:
        status_label = "Unavailable"

    if database == "healthy":
        status_symbol = "●"
    else:
        status_symbol = "○"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>{APP_NAME}</title>

            <style>
                * {{
                    box-sizing: border-box;
                }}

                body {{
                    margin: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-family: Arial, sans-serif;
                    background: #0f172a;
                    color: #f8fafc;
                }}

                .card {{
                    width: min(680px, 92%);
                    background: #1e293b;
                    padding: 40px;
                    border-radius: 16px;
                    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
                }}

                h1 {{
                    margin-top: 0;
                    margin-bottom: 12px;
                }}

                .subtitle {{
                    color: #94a3b8;
                    margin-bottom: 28px;
                }}

                .status {{
                    font-weight: 700;
                    margin-bottom: 20px;
                }}

                .database {{
                    color: #cbd5e1;
                    margin-bottom: 24px;
                }}

                code {{
                    background: #334155;
                    padding: 4px 8px;
                    border-radius: 6px;
                    color: #38bdf8;
                }}

                .timestamp {{
                    color: #64748b;
                    font-size: 13px;
                }}
            </style>
        </head>

        <body>
            <div class="card">
                <h1>Enterprise GraphRAG Backend</h1>

                <div class="subtitle">
                    {APP_NAME}
                </div>

                <div class="status">
                    {status_symbol} {status_lab}                  {status_label}
                </div>

                <div class="database">
                    Database: <strong>{database}</strong>
                </div>

                <div>
                    MCP SSE Transport Endpoint:
                    <code>/sse</code>
                </div>

                <p class="timestamp">
                    Health checked at {payload["timestamp"]}
                </p>
            </div>
        </body>
    </html>
    """

    return HTMLResponse(
        content=html_content,
        status_code=200,
    )


# ==============================================================================
# APPLICATION STARTUP
# ==============================================================================

if __name__ == "__main__":
    init_driver()

    try:
        mcp.run(
            transport="sse",
            host="0.0.0.0",
            port=8000,
        )

    finally:
        asyncio.run(close_driver())
