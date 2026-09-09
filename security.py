import time
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from config import MAX_REQUESTS_PER_MINUTE, NEO4J_DATABASE, logger
from database import get_driver

class SimpleRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    def allow(self, tenant_id: str) -> bool:
        now = time.time()
        history = self.requests.setdefault(tenant_id, [])
        history[:] = [ts for ts in history if now - ts < self.window_seconds]
        if len(history) >= self.max_requests:
            return False
        history.append(now)
        return True

rate_limiter = SimpleRateLimiter(MAX_REQUESTS_PER_MINUTE)

def validate_tenant_id(tenant_id: str) -> str:
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id is required.")
    if len(tenant_id) > 128:
        raise ValueError("Invalid tenant_id.")
    return tenant_id.strip()

async def write_audit_log(
    tenant_id: str,
    action: str,
    request_id: str,
    metadata: Optional[Dict[str, Any]] = None,
):
    driver = get_driver()
    if driver is None:
        return

    query = """
    MATCH (t:Tenant {id: $tenant_id})
    CREATE (a:AuditLog {
        id: $request_id,
        action: $action,
        timestamp: $timestamp,
        metadata: $metadata
    })
    CREATE (t)-[:GENERATED_AUDIT]->(a)
    """
    try:
        async with driver.session(database=NEO4J_DATABASE) as session:
            await session.run(
                query,
                tenant_id=tenant_id,
                request_id=request_id,
                action=action,
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata=json.dumps(metadata or {}),
            )
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
