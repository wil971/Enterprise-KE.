import os
import logging
from dotenv import load_dotenv


# ==============================================================================
# ENVIRONMENT
# ==============================================================================

load_dotenv()

APP_NAME = os.getenv(
    "APP_NAME",
    "AetherEnterpriseKnowledgeHub",
).strip()

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "production",
).strip().lower()

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://enterprise-ke-3.onrender.com",
).strip()


# ==============================================================================
# APPLICATION AUTHENTICATION
# ==============================================================================

# Do NOT use a hardcoded production API key.
# Configure ENTERPRISE_API_KEY in Render/environment variables.
ENTERPRISE_API_KEY = os.getenv(
    "ENTERPRISE_API_KEY",
    "",
).strip()


# ==============================================================================
# NEO4J DATABASE
# ==============================================================================

NEO4J_URI = os.getenv(
    "NEO4J_URI",
    "bolt://localhost:7687",
).strip()

NEO4J_USER = os.getenv(
    "NEO4J_USER",
    "neo4j",
).strip()

# Never silently fall back to "password" in production.
NEO4J_PASS = os.getenv(
    "NEO4J_PASS",
    "",
).strip()

# Standard compatibility alias.
NEO4J_PASSWORD = NEO4J_PASS

NEO4J_DATABASE = os.getenv(
    "NEO4J_DATABASE",
    "neo4j",
).strip()


# ==============================================================================
# AI PROVIDER
# ==============================================================================

# Supports Groq, OpenAI-compatible providers, or another configured provider.
AI_API_KEY = (
    os.getenv("GROQ_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("AI_API_KEY")
    or ""
).strip()

AI_API_URL = os.getenv(
    "AI_API_URL",
    "https://api.groq.com/openai/v1/chat/completions",
).strip()

AI_MODEL = os.getenv(
    "AI_MODEL",
    "llama-3.3-70b-versatile",
).strip()


# ==============================================================================
# EXECUTION LIMITS
# ==============================================================================

def _get_positive_int(
    environment_name: str,
    default: int,
    minimum: int = 1,
) -> int:
    """
    Read a positive integer environment variable safely.
    """

    raw_value = os.getenv(
        environment_name,
        str(default),
    ).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"{environment_name} must be a valid integer."
        ) from exc

    if value < minimum:
        raise RuntimeError(
            f"{environment_name} must be >= {minimum}."
        )

    return value


MAX_QUERY_RESULTS = _get_positive_int(
    "MAX_QUERY_RESULTS",
    25,
)

MAX_REQUESTS_PER_MINUTE = _get_positive_int(
    "MAX_REQUESTS_PER_MINUTE",
    60,
)


# ==============================================================================
# SECURITY / REQUEST LIMITS
# ==============================================================================

MAX_QUERY_LENGTH = _get_positive_int(
    "MAX_QUERY_LENGTH",
    1000,
)

MAX_DOCUMENT_LENGTH = _get_positive_int(
    "MAX_DOCUMENT_LENGTH",
    5_000_000,
)

MAX_DOCUMENT_TITLE_LENGTH = _get_positive_int(
    "MAX_DOCUMENT_TITLE_LENGTH",
    500,
)

MAX_GRAPH_DEPTH = _get_positive_int(
    "MAX_GRAPH_DEPTH",
    5,
)

REQUEST_TIMEOUT_SECONDS = _get_positive_int(
    "REQUEST_TIMEOUT_SECONDS",
    60,
)


# ==============================================================================
# LOGGING
# ==============================================================================

LOG_LEVEL_NAME = os.getenv(
    "LOG_LEVEL",
    "INFO",
).strip().upper()

_VALID_LOG_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}

if LOG_LEVEL_NAME not in _VALID_LOG_LEVELS:
    LOG_LEVEL_NAME = "INFO"

LOG_LEVEL = getattr(
    logging,
    LOG_LEVEL_NAME,
)


logging.basicConfig(
    level=LOG_LEVEL,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "[AETHER] | "
        "%(message)s"
    ),
    force=True,
)

logger = logging.getLogger(APP_NAME)


# ==============================================================================
# CONFIGURATION VALIDATION
# ==============================================================================

def validate_configuration() -> None:
    """
    Validate configuration required for the running environment.

    Development environments may be started without production
    credentials so that local development remains possible.

    Production environments fail closed when critical credentials
    are missing.
    """

    required_values = {
        "APP_NAME": APP_NAME,
        "BACKEND_URL": BACKEND_URL,
        "NEO4J_URI": NEO4J_URI,
        "NEO4J_USER": NEO4J_USER,
        "NEO4J_DATABASE": NEO4J_DATABASE,
    }

    missing = [
        name
        for name, value in required_values.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing required configuration: "
            + ", ".join(missing)
        )

    if ENVIRONMENT == "production":

        if not ENTERPRISE_API_KEY:
            raise RuntimeError(
                "ENTERPRISE_API_KEY must be configured "
                "in production."
            )

        if not NEO4J_PASS:
            raise RuntimeError(
                "NEO4J_PASS or NEO4J_PASSWORD must be configured "
                "in production."
            )


# ==============================================================================
# SAFE CONFIGURATION STATUS
# ==============================================================================

def get_configuration_status() -> dict:
    """
    Return non-sensitive configuration information.

    Secrets and credentials are intentionally never returned.
    """

    return {
        "app_name": APP_NAME,
        "environment": ENVIRONMENT,
        "backend_url": BACKEND_URL,
        "neo4j": {
            "configured": bool(
                NEO4J_URI
                and NEO4J_USER
                and NEO4J_PASS
            ),
            "database": NEO4J_DATABASE,
        },
        "authentication": {
            "api_key_configured": bool(
                ENTERPRISE_API_KEY
            ),
        },
        "ai": {
            "api_key_configured": bool(
                AI_API_KEY
            ),
            "api_url_configured": bool(
                AI_API_URL
            ),
            "model": AI_MODEL,
        },
        "limits": {
            "max_query_results": MAX_QUERY_RESULTS,
            "max_requests_per_minute": MAX_REQUESTS_PER_MINUTE,
            "max_query_length": MAX_QUERY_LENGTH,
            "max_document_length": MAX_DOCUMENT_LENGTH,
            "max_document_title_length": MAX_DOCUMENT_TITLE_LENGTH,
            "max_graph_depth": MAX_GRAPH_DEPTH,
            "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        },
    }
