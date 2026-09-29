
import hmac
import json
import re
import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from config import (
    MAX_REQUESTS_PER_MINUTE,
    NEO4J_DATABASE,
    ENTERPRISE_API_KEY,
    logger,
)
from database import get_driver


# ============================================================
# 1. CONFIGURATION
# ============================================================

MAX_TENANT_ID_LENGTH = 128
MAX_ACTION_LENGTH = 100
MAX_REQUEST_ID_LENGTH = 128
MAX_METADATA_LENGTH = 10000

TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")


# ============================================================
# 2. THREAD-SAFE RATE LIMITER
# ============================================================

class SimpleRateLimiter:
    """
    Thread-safe, process-local rate limiter.

    Limits requests per tenant within a rolling time window.

    Note:
    This implementation is suitable for a single server instance.
    A distributed deployment should use Redis or another shared store.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int = 60,
    ):
        if max_requests < 1:
            raise ValueError("max_requests must be greater than zero.")

        if window_seconds < 1:
            raise ValueError("window_seconds must be greater than zero.")

        self.max_requests = max_requests
        self.window_seconds = window_seconds

        self.requests = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, tenant_id: str) -> bool:
        now = time.monotonic()

        with self.lock:
            history = self.requests[tenant_id]

            # Remove expired requests.
            while (
                history
                and now - history[0] >= self.window_seconds
            ):
                history.popleft()

            if len(history) >= self.max_requests:
                return False

            history.append(now)
            return True

    def remaining(self, tenant_id: str) -> int:
        now = time.monotonic()

        with self.lock:
            history = self.requests[tenant_id]

            while (
                history
                and now - history[0] >= self.window_seconds
            ):
                history.popleft()

            return max(
                0,
                self.max_requests - len(history),
            )


rate_limiter = SimpleRateLimiter(
    MAX_REQUESTS_PER_MINUTE
)


# ============================================================
# 3. TENANT ID VALIDATION
# ============================================================

def validate_tenant_id(tenant_id: str) -> str:
    """
    Validates tenant ID format.

    Important:
    This validates the format only. It does NOT establish that
    the caller is authorized to access the tenant.
    """

    if not isinstance(tenant_id, str):
        raise ValueError("tenant_id must be a string.")

    tenant_id = tenant_id.strip()

    if not tenant_id:
        raise ValueError("tenant_id is required.")

    if len(tenant_id) > MAX_TENANT_ID_LENGTH:
        raise ValueError("tenant_id exceeds the maximum length.")

    if not TENANT_ID_PATTERN.fullmatch(tenant_id):
        raise ValueError("tenant_id contains invalid characters.")

    return tenant_id


# ============================================================
# 4. API KEY AUTHENTICATION
# ============================================================

def authenticate_api_key(api_key: str) -> bool:
    """
    Validates an API key using constant-time comparison.

    Only the configured environment variable is accepted.
    No hardcoded fallback credentials are permitted.
    """

    if not isinstance(api_key, str):
        return False

    if not isinstance(ENTERPRISE_API_KEY, str):
        logger.error("API key configuration is invalid.")
        return False

    configured_key = ENTERPRISE_API_KEY.strip()
    supplied_key = api_key.strip()

    if not configured_key or not supplied_key:
        return False

    return hmac.compare_digest(
        supplied_key.encode("utf-8"),
        configured_key.encode("utf-8"),
    )


# ============================================================
# 5. AUDIT LOGGING
# ============================================================

async def write_audit_log(
    tenant_id: str,
    action: str,
    request_id: str,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Writes an audit event to Neo4j.

    Audit records are associated with their tenant.
    Sensitive credentials should never be included in metadata.
    """

    tenant_id = validate_tenant_id(tenant_id)

    if not isinstance(action, str) or not action.strip():
        raise ValueError("Audit action is required.")

    action = action.strip()

    if len(action) > MAX_ACTION_LENGTH:
        raise ValueError("Audit action is too long.")

    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request_id is required.")

    request_id = request_id.strip()

    if len(request_id) > MAX_REQUEST_ID_LENGTH:
        raise ValueError("request_id is too long.")

    if metadata is None:
        metadata = {}

    if not isinstance(metadata, dict):
        raise ValueError("Audit metadata must be a dictionary.")

    try:
        serialized_metadata = json.dumps(
            metadata,
            default=str,
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Audit metadata is not serializable.") from exc

    if len(serialized_metadata) > MAX_METADATA_LENGTH:
        raise ValueError("Audit metadata exceeds the allowed size.")

    driver = get_driver()

    if driver is None:
        logger.error(
            "Audit logging unavailable: Neo4j driver is not configured."
        )
        raise RuntimeError("Audit logging is unavailable.")

    query = """
    MATCH (t:Tenant {id: $tenant_id})
    CREATE (a:AuditLog {
        id: $request_id,
        action: $action,
        timestamp: $timestamp,
        metadata: $metadata
    })
    CREATE (t)-[:GENERATED_AUDIT]->(a)
    RETURN a.id AS audit_id
    """

    try:
        async with driver.session(
            database=NEO4J_DATABASE
        ) as session:

            result = await session.run(
                query,
                tenant_id=tenant_id,
                request_id=request_id,
                action=action,
                timestamp=datetime.now(
                    timezone.utc
                ).isoformat(),
                metadata=serialized_metadata,
            )

            record = await result.single()

            if record is None:
                raise RuntimeError(
                    "Audit log was not written. "
                    "The tenant may not exist."
                )

    except Exception:
        logger.exception(
            "Audit logging failed for request_id=%s",
            request_id,
        )
        raise RuntimeError(
            "Unable to persist audit log."
        )


# ============================================================
# 6. SECURITY STATUS
# ============================================================

def get_security_status() -> Dict[str, Any]:
    """
    Returns non-sensitive security configuration information.
    Never returns API keys or credentials.
    """

    return {
        "authentication_configured": bool(
            isinstance(ENTERPRISE_API_KEY, str)
            and ENTERPRISE_API_KEY.strip()
        ),
        "rate_limit_per_minute": MAX_REQUESTS_PER_MINUTE,
        "rate_limiter": "process-local",
        "tenant_validation": "enabled",
        "audit_logging": "neo4j",
  }
      
