import json
import uuid
import asyncio
from datetime import datetime, timezone
from fastmcp import FastMCP
from config import APP_NAME, ENVIRONMENT, logger
from database import get_driver, close_driver, init_driver
from security import validate_tenant_id, rate_limiter, write_audit_log
from refiner import extract_business_entities, validate_extraction, store_business_document
from retrieval import secure_graph_retrieval

mcp = FastMCP(APP_NAME)

@mcp.tool()
async def enterprise_search(tenant_id: str, topic: str) -> str:
    """Securely retrieve enterprise knowledge belonging to a specific tenant."""
    return await secure_graph_retrieval(tenant_id, topic)

@mcp.tool()
async def ingest_business_document(tenant_id: str, title: str, text: str) -> str:
    """Extract structured business information and store it in the enterprise knowledge graph."""
    tenant_id = validate_tenant_id(tenant_id)
    if not rate_limiter.allow(tenant_id):
        raise RuntimeError("Rate limit exceeded.")

    document_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())

    try:
        extracted = extract_business_entities(text)
        extracted = validate_extraction(extracted)
        await store_business_document(tenant_id, document_id, title, text, extracted)
        await write_audit_log(
            tenant_id=tenant_id,
            action="document_ingestion",
            request_id=request_id,
            metadata={"document_id": document_id, "title": title},
        )
        return json.dumps({"success": True, "document_id": document_id, "extracted": extracted}, indent=2)
    except Exception as e:
        logger.exception(f"Ingestion failed request_id={request_id}")
        return json.dumps({"success": False, "error": str(e), "request_id": request_id}, indent=2)

@mcp.tool()
async def system_health() -> str:
    """Returns the health status of the Aether platform."""
    driver = get_driver()
    neo4j_status = "unhealthy"
    if driver is not None:
        try:
            await driver.verify_connectivity()
            neo4j_status = "healthy"
        except Exception:
            pass
    else:
        neo4j_status = "not_configured"

    return json.dumps({
        "service": APP_NAME,
        "environment": ENVIRONMENT,
        "neo4j": neo4j_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, indent=2)

@mcp.resource("config://tenant-schema")
def get_schema() -> str:
    return """
Aether Enterprise Knowledge Graph
Nodes: Tenant, Document, Client, Project, Entity, AuditLog
Relationships: Tenant -[:OWNS]-> Document, Document -[:MENTIONS]-> Client/Project, Client -[:OWNS_PROJECT]-> Project
Security: Every object must belong to a tenant_id.
"""

if __name__ == "__main__":
    init_driver()
    try:
        mcp.run()
    finally:
        asyncio.run(close_driver())
