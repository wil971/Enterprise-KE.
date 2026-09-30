import hmac
import json
import re
import secrets
import time
import threading

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, FrozenSet

from config import (
    ENTERPRISE_API_KEY,
    MAX_REQUESTS_PER_MINUTE,
    NEO4J_DATABASE,
    logger,
)
from database import get_driver


# ==============================================================================
# SECURITY LIMITS
# ==============================================================================

MAX_TENANT_ID_LENGTH = 128
MAX_USER_ID_LENGTH = 128
MAX_ROLE_LENGTH = 64
MAX_ACTION_LENGTH = 100
MAX_REQUEST_ID_LENGTH = 128
MAX_METADATA_LENGTH = 10000
MAX_API_KEY_LENGTH = 4096

TENANT_ID_PATTERN = re.compile(
    r"^[a-zA-Z0-9_.-]+$"
)

USER_ID_PATTERN = re.compile(
    r"^[a-zA-Z0-9_.:@+-]+$"
)

ROLE_PATTERN = re.compile(
    r"^[a-zA-Z0-9_.-]+$"
)


# ==============================================================================
# SECURITY EXCEPTIONS
# ==============================================================================

class SecurityError(Exception):
    """Base class for security-related errors."""


class AuthenticationError(SecurityError):
    """Raised when authentication fails."""


class AuthorizationError(SecurityError):
    """Raised when an authenticated caller lacks permission."""


class TenantAccessError(AuthorizationError):
    """Raised when a caller attempts unauthorized tenant access."""


class RateLimitExceeded(SecurityError):
    """Raised when the request rate exceeds the configured limit."""


class ValidationError(SecurityError):
    """Raised when security-related input validation fails."""


class AuditLogError(SecurityError):
    """Raised when an audit event cannot be persisted."""


# ==============================================================================
# ROLES AND PERMISSIONS
# ==============================================================================

PERMISSION_SEARCH = "search"
PERMISSION_INGEST = "ingest"
PERMISSION_READ_GRAPH = "read_graph"
PERMISSION_READ_AUDIT = "read_audit"
PERMISSION_MANAGE = "manage"


ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "viewer": frozenset({
        PERMISSION_SEARCH,
        PERMISSION_READ_GRAPH,
    }),

    "member": frozenset({
        PERMISSION_SEARCH,
        PERMISSION_INGEST,
        PERMISSION_READ_GRAPH,
    }),

    "admin": frozenset({
        PERMISSION_SEARCH,
        PERMISSION_INGEST,
        PERMISSION_READ_GRAPH,
        PERMISSION_READ_AUDIT,
        PERMISSION_MANAGE,
    }),

    "service": frozenset({
        PERMISSION_SEARCH,
        PERMISSION_INGEST,
        PERMISSION_READ_GRAPH,
    }),
}


# ==============================================================================
# SECURITY CONTEXT
# ==============================================================================

@dataclass(frozen=True)
class SecurityContext:
    """
    Represents the authenticated identity for one request.

    IMPORTANT:
    tenant_id in this object is trusted only after authentication
    and tenant authorization have succeeded.
    """

    user_id: str
    tenant_id: str
    role: str
    request_id: str

    @property
    def permissions(self) -> FrozenSet[str]:
        return ROLE_PERMISSIONS.get(
            self.role,
            frozenset(),
        )

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


# ==============================================================================
# PROCESS-LOCAL RATE LIMITER
# ==============================================================================

class SimpleRateLimiter:
    """
    Thread-safe rolling-window rate limiter.

    This is intentionally process-local.

    For multiple Render instances, replace this with a shared
    Redis/database-backed limiter so all instances enforce the
    same limit.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int = 60,
    ):
        if max_requests < 1:
            raise ValueError(
                "max_requests must be greater than zero."
            )

        if window_seconds < 1:
            raise ValueError(
                "window_seconds must be greater than zero."
            )

        self.max_requests = max_requests
        self.window_seconds = window_seconds

        self.requests = defaultdict(deque)
        self.lock = threading.Lock()

    def _cleanup(self, key: str, now: float) -> deque:
        history = self.requests[key]

        while (
            history
            and now - history[0] >= self.window_seconds
        ):
            history.popleft()

        return history

    def allow(self, key: str) -> bool:
        if not isinstance(key, str) or not key:
            raise ValidationError(
                "Rate-limit key is required."
            )

        now = time.monotonic()

        with self.lock:
            history = self._cleanup(key, now)

            if len(history) >= self.max_requests:
                return False

            history.append(now)
            return True

    def remaining(self, key: str) -> int:
        if not isinstance(key, str) or not key:
            return 0

        now = time.monotonic()

        with self.lock:
            history = self._cleanup(key, now)

            return max(
                0,
                self.max_requests - len(history),
            )


rate_limiter = SimpleRateLimiter(
    MAX_REQUESTS_PER_MINUTE
)


# ==============================================================================
# INPUT VALIDATION
# ==============================================================================

def validate_tenant_id(tenant_id: str) -> str:
    """
    Validate tenant identifier syntax.

    This does NOT authorize the caller.
    """

    if not isinstance(tenant_id, str):
        raise ValidationError(
            "tenant_id must be a string."
        )

    tenant_id = tenant_id.strip()

    if not tenant_id:
        raise ValidationError(
            "tenant_id is required."
        )

    if len(tenant_id) > MAX_TENANT_ID_LENGTH:
        raise ValidationError(
            "tenant_id exceeds the maximum length."
        )

    if not TENANT_ID_PATTERN.fullmatch(tenant_id):
        raise ValidationError(
            "tenant_id contains invalid characters."
        )

    return tenant_id


def validate_user_id(user_id: str) -> str:
    if not isinstance(user_id, str):
        raise ValidationError(
            "user_id must be a string."
        )

    user_id = user_id.strip()

    if not user_id:
        raise ValidationError(
            "user_id is required."
        )

    if len(user_id) > MAX_USER_ID_LENGTH:
        raise ValidationError(
            "user_id exceeds the maximum length."
        )

    if not USER_ID_PATTERN.fullmatch(user_id):
        raise ValidationError(
            "user_id contains invalid characters."
        )

    return user_id


def validate_role(role: str) -> str:
    if not isinstance(role, str):
        raise ValidationError(
            "role must be a string."
        )

    role = role.strip().lower()

    if not role:
        raise ValidationError(
            "role is required."
        )

    if len(role) > MAX_ROLE_LENGTH:
        raise ValidationError(
            "role exceeds the maximum length."
        )

    if not ROLE_PATTERN.fullmatch(role):
        raise ValidationError(
            "role contains invalid characters."
        )

    if role not in ROLE_PERMISSIONS:
        raise ValidationError(
            "Unsupported security role."
        )

    return role


def validate_request_id(
    request_id: Optional[str] = None,
) -> str:
    """
    Accept a supplied request ID when valid, otherwise generate
    a cryptographically random request ID.
    """

    if request_id is None:
        return secrets.token_urlsafe(32)

    if not isinstance(request_id, str):
        raise ValidationError(
            "request_id must be a string."
        )

    request_id = request_id.strip()

    if not request_id:
        raise ValidationError(
            "request_id cannot be empty."
        )

    if len(request_id) > MAX_REQUEST_ID_LENGTH:
        raise ValidationError(
            "request_id exceeds the maximum length."
        )

    return request_id


# ==============================================================================
# API KEY AUTHENTICATION
# ==============================================================================

def authenticate_api_key(api_key: str) -> bool:
    """
    Authenticate against the configured enterprise API key.

    Constant-time comparison is used to avoid leaking key information
    through comparison timing.

    No hardcoded fallback credential is accepted.
    """

    if not isinstance(api_key, str):
        return False

    if len(api_key) > MAX_API_KEY_LENGTH:
        return False

    configured_key = (
        ENTERPRISE_API_KEY.strip()
        if isinstance(ENTERPRISE_API_KEY, str)
        else ""
    )

    supplied_key = api_key.strip()

    if not configured_key or not supplied_key:
        return False

    return hmac.compare_digest(
        supplied_key.encode("utf-8"),
        configured_key.encode("utf-8"),
    )


def require_api_key(api_key: str) -> None:
    """
    Raise AuthenticationError when the API key is invalid.
    """

    if not authenticate_api_key(api_key):
        raise AuthenticationError(
            "Authentication failed."
        )


# ==============================================================================
# TENANT AUTHORIZATION
# ==============================================================================

def authorize_tenant(
    authenticated_tenant_id: str,
    requested_tenant_id: str,
) -> str:
    """
    Verify that the authenticated identity is accessing its
    authorized tenant.

    The tenant ID supplied to an operation is NOT considered
    authorization by itself.
    """

    authenticated_tenant_id = validate_tenant_id(
        authenticated_tenant_id
    )

    requested_tenant_id = validate_tenant_id(
        requested_tenant_id
    )

    if not hmac.compare_digest(
        authenticated_tenant_id,
        requested_tenant_id,
    ):
        raise TenantAccessError(
            "Tenant access denied."
        )

    return requested_tenant_id


# ==============================================================================
# PERMISSION AUTHORIZATION
# ==============================================================================

def require_permission(
    role: str,
    permission: str,
) -> None:
    """
    Verify that the caller's role contains the requested permission.
    """

    role = validate_role(role)

    if not isinstance(permission, str):
        raise ValidationError(
            "permission must be a string."
        )

    permission = permission.strip()

    if not permission:
        raise ValidationError(
            "permission is required."
        )

    permissions = ROLE_PERMISSIONS.get(
        role,
        frozenset(),
    )

    if permission not in permissions:
        raise AuthorizationError(
            "Permission denied."
        )


# ==============================================================================
# REQUEST RATE LIMITING
# ==============================================================================

def enforce_rate_limit(
    context: SecurityContext,
) -> None:
    """
    Apply rate limiting to the authenticated security identity.

    The limiter key contains authenticated identity information,
    not an arbitrary tenant ID supplied by an unauthenticated caller.
    """

    key = (
        f"{context.tenant_id}:"
        f"{context.user_id}"
    )

    if not rate_limiter.allow(key):
        raise RateLimitExceeded(
            "Rate limit exceeded."
        )


# ==============================================================================
# SECURITY CONTEXT CREATION
# ==============================================================================

def create_security_context(
    api_key: str,
    tenant_id: str,
    user_id: str = "api-client",
    role: str = "service",
    request_id: Optional[str] = None,
) -> SecurityContext:
    """
    Authenticate the caller and construct the trusted security context.

    With the current configuration, the single configured enterprise
    API key represents the service identity.

    Per-user/per-tenant API credentials can be introduced later
    without changing the rest of the authorization flow.
    """

    require_api_key(api_key)

    tenant_id = validate_tenant_id(
        tenant_id
    )

    user_id = validate_user_id(
        user_id
    )

    role = validate_role(
        role
    )

    request_id = validate_request_id(
        request_id
    )

    return SecurityContext(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        request_id=request_id,
    )


# ==============================================================================
# COMPLETE REQUEST AUTHORIZATION
# ==============================================================================

def authorize_request(
    api_key: str,
    requested_tenant_id: str,
    permission: str,
    authenticated_tenant_id: Optional[str] = None,
    user_id: str = "api-client",
    role: str = "service",
    request_id: Optional[str] = None,
) -> SecurityContext:
    """
    Complete authorization pipeline:

        1. Authenticate API key
        2. Validate identity information
        3. Establish trusted tenant identity
        4. Verify requested tenant
        5. Check role permission
        6. Apply rate limit

    The returned SecurityContext is the object that protected
    application operations should use.
    """

    context_tenant_id = (
        authenticated_tenant_id
        if authenticated_tenant_id is not None
        else requested_tenant_id
    )

    context = create_security_context(
        api_key=api_key,
        tenant_id=context_tenant_id,
        user_id=user_id,
        role=role,
        request_id=request_id,
    )

    authorize_tenant(
        authenticated_tenant_id=context.tenant_id,
        requested_tenant_id=requested_tenant_id,
    )

    require_permission(
        role=context.role,
        permission=permission,
    )

    enforce_rate_limit(context)

    return context


# ==============================================================================
# AUDIT METADATA REDACTION
# ==============================================================================

SENSITIVE_METADATA_KEYS = {
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "neo4j_pass",
    "neo4j_password",
    "groq_api_key",
    "openai_api_key",
}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().strip()

    if normalized in SENSITIVE_METADATA_KEYS:
        return True

    sensitive_fragments = (
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "authorization",
    )

    return any(
        fragment in normalized
        for fragment in sensitive_fragments
    )


def redact_metadata(
    metadata: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Remove sensitive values from audit metadata recursively.
    """

    if metadata is None:
        return {}

    if not isinstance(metadata, dict):
        raise ValidationError(
            "Audit metadata must be a dictionary."
        )

    def redact_value(value: Any) -> Any:

        if isinstance(value, dict):
            result = {}

            for key, nested_value in value.items():
                key_string = str(key)

                if _is_sensitive_key(key_string):
                    result[key_string] = "[REDACTED]"
                else:
                    result[key_string] = redact_value(
                        nested_value
                    )

            return result

        if isinstance(value, list):
            return [
                redact_value(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                redact_value(item)
                for item in value
            ]

        return value

    return redact_value(metadata)


# ==============================================================================
# AUDIT LOGGING
# ==============================================================================

async def write_audit_log(
    tenant_id: str,
    action: str,
    request_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    role: Optional[str] = None,
    outcome: str = "success",
) -> None:
    """
    Persist a tenant-scoped audit event in Neo4j.

    Audit failures are surfaced instead of silently pretending that
    the event was recorded.
    """

    tenant_id = validate_tenant_id(
        tenant_id
    )

    request_id = validate_request_id(
        request_id
    )

    if not isinstance(action, str):
        raise ValidationError(
            "Audit action must be a string."
        )

    action = action.strip()

    if not action:
        raise ValidationError(
            "Audit action is required."
        )

    if len(action) > MAX_ACTION_LENGTH:
        raise ValidationError(
            "Audit action is too long."
        )

    if user_id is not None:
        user_id = validate_user_id(
            user_id
        )

    if role is not None:
        role = validate_role(
            role
        )

    if not isinstance(outcome, str):
        raise ValidationError(
            "Audit outcome must be a string."
        )

    outcome = outcome.strip().lower()

    if not outcome:
        raise ValidationError(
            "Audit outcome is required."
        )

    safe_metadata = redact_metadata(
        metadata
    )

    try:
        serialized_metadata = json.dumps(
            safe_metadata,
            default=str,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Audit metadata is not serializable."
        ) from exc

    if len(serialized_metadata) > MAX_METADATA_LENGTH:
        raise ValidationError(
            "Audit metadata exceeds the allowed size."
        )

    driver = get_driver()

    if driver is None:
        logger.error(
            "Audit logging unavailable: "
            "Neo4j driver is not configured. "
            "request_id=%s",
            request_id,
        )
        raise AuditLogError(
            "Audit logging is unavailable."
        )

    audit_id = secrets.token_urlsafe(24)

    query = """
    MATCH (t:Tenant {id: $tenant_id})

    CREATE (a:AuditLog {
        id: $audit_id,
        request_id: $request_id,
        action: $action,
        outcome: $outcome,
        user_id: $user_id,
        role: $role,
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
                audit_id=audit_id,
                request_id=request_id,
                action=action,
                outcome=outcome,
                user_id=user_id,
                role=role,
                timestamp=datetime.now(
                    timezone.utc
                ).isoformat(),
                metadata=serialized_metadata,
            )

            record = await result.single()

            if record is None:
                raise AuditLogError(
                    "Audit log could not be associated "
                    "with therecord = await result.single()

            if record is None:
                raise AuditLogError(
                    "Audit log could not be associated "
                    "with the requested tenant."
                )

    except AuditLogError:
        raise

    except Exception as exc:
        logger.exception(
            "Audit logging failed. request_id=%s",
            request_id,
        )
        raise AuditLogError(
            "Unable to persist audit log."
        ) from exc


# ==============================================================================
# SECURITY STATUS
# ==============================================================================

def get_security_status() -> Dict[str, Any]:
    """
    Return non-sensitive security state.

    Secrets are never returned.
    """

    return {
        "authentication": {
            "api_key_configured": bool(
                isinstance(
                    ENTERPRISE_API_KEY,
                    str,
                )
                and ENTERPRISE_API_KEY.strip()
            ),
        },
        "authorization": {
            "tenant_isolation": "enabled",
            "role_based_permissions": "enabled",
            "roles": sorted(
                ROLE_PERMISSIONS.keys()
            ),
        },
        "rate_limiting": {
            "enabled": True,
            "limit_per_minute": MAX_REQUESTS_PER_MINUTE,
            "scope": "authenticated_identity",
            "implementation": "process-local",
        },
        "audit_logging": {
            "enabled": True,
            "storage": "neo4j",
            "metadata_redaction": "enabled",
        },
        }
