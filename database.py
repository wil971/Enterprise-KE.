
"""
Professional Neo4j database manager.

Supports:
- Synchronous operations for Streamlit.
- Asynchronous operations for FastMCP.
- Connection health monitoring.
- Query timeouts.
- Safe driver lifecycle management.
- Live graph metrics.
- Centralized database error handling.

IMPORTANT:
This module does not automatically enforce tenant isolation.
Every application query that accesses tenant-owned data must
include the appropriate tenant authorization conditions.
"""

import asyncio
import threading
import time
from typing import Any, Dict, List, Optional

from neo4j import (
    AsyncGraphDatabase,
    GraphDatabase,
)

from config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASS,
    NEO4J_DATABASE,
    logger,
)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_CONNECTION_POOL_SIZE = 100
MAX_CONNECTION_LIFETIME = 3600
CONNECTION_TIMEOUT = 30
QUERY_TIMEOUT = 60


# ============================================================
# DATABASE EXCEPTIONS
# ============================================================

class DatabaseError(Exception):
    """Base exception for database-related failures."""


class DatabaseConfigurationError(DatabaseError):
    """Raised when database configuration is missing or invalid."""


class DatabaseConnectionError(DatabaseError):
    """Raised when a database connection cannot be established."""


class DatabaseQueryError(DatabaseError):
    """Raised when a Cypher query fails."""


# ============================================================
# DRIVER MANAGEMENT
# ============================================================

# Async driver is used by FastMCP and asynchronous services.
driver = None

# Sync driver is used by Streamlit and synchronous callers.
_sync_driver = None

# Prevents concurrent initialization from creating duplicate drivers.
_driver_lock = threading.RLock()


def _validate_configuration() -> None:
    """
    Validate required Neo4j configuration before creating drivers.
    """

    if not NEO4J_URI:
        raise DatabaseConfigurationError(
            "NEO4J_URI is not configured."
        )

    if not NEO4J_USER:
        raise DatabaseConfigurationError(
            "NEO4J_USER is not configured."
        )

    if not NEO4J_PASS:
        raise DatabaseConfigurationError(
            "NEO4J_PASS is not configured."
        )


def _driver_options() -> dict:
    """
    Shared Neo4j connection settings.
    """

    return {
        "max_connection_lifetime": MAX_CONNECTION_LIFETIME,
        "max_connection_pool_size": MAX_CONNECTION_POOL_SIZE,
        "connection_timeout": CONNECTION_TIMEOUT,
        "connection_acquisition_timeout": CONNECTION_TIMEOUT,
    }


def init_driver():
    """
    Initialize the asynchronous Neo4j driver.

    Used by FastMCP and other asynchronous services.
    """

    global driver

    with _driver_lock:

        if driver is not None:
            return driver

        _validate_configuration()

        try:
            driver = AsyncGraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASS),
                **_driver_options(),
            )

            logger.info(
                "Asynchronous Neo4j driver initialized."
            )

            return driver

        except Exception as exc:
            logger.exception(
                "Failed to initialize asynchronous Neo4j driver."
            )

            raise DatabaseConnectionError(
                "Unable to initialize asynchronous database driver."
            ) from exc


def get_driver():
    """
    Return the asynchronous Neo4j driver.

    Existing asynchronous services can continue using:

        drv = get_driver()
        async with drv.session(...) as session:
            ...
    """

    if driver is None:
        return init_driver()

    return driver


def init_sync_driver():
    """
    Initialize the synchronous Neo4j driver.

    Streamlit should use this driver instead of trying to
    run asynchronous database operations inside its event loop.
    """

    global _sync_driver

    with _driver_lock:

        if _sync_driver is not None:
            return _sync_driver

        _validate_configuration()

        try:
            _sync_driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASS),
                **_driver_options(),
            )

            logger.info(
                "Synchronous Neo4j driver initialized."
            )

            return _sync_driver

        except Exception as exc:
            logger.exception(
                "Failed to initialize synchronous Neo4j driver."
            )

            raise DatabaseConnectionError(
                "Unable to initialize synchronous database driver."
            ) from exc


def get_sync_driver():
    """
    Return the synchronous Neo4j driver.
    """

    if _sync_driver is None:
        return init_sync_driver()

    return _sync_driver


# ============================================================
# DATABASE SHUTDOWN
# ============================================================

async def close_driver():
    """
    Close both database drivers safely.

    Retains the original close_driver() function name
    for compatibility with existing application code.
    """

    global driver, _sync_driver

    async_driver = driver
    sync_driver = _sync_driver

    errors = []

    if async_driver is not None:
        try:
            await async_driver.close()
            logger.info(
                "Asynchronous Neo4j driver closed."
            )
            driver = None

        except Exception as exc:
            logger.exception(
                "Error closing asynchronous Neo4j driver."
            )
            errors.append(exc)

    if sync_driver is not None:
        try:
            sync_driver.close()
            logger.info(
                "Synchronous Neo4j driver closed."
            )
            _sync_driver = None

        except Exception as exc:
            logger.exception(
                "Error closing synchronous Neo4j driver."
            )
            errors.append(exc)

    if errors:
        raise DatabaseConnectionError(
            "One or more database drivers could not be closed."
        ) from errors[0]


def close_sync_driver():
    """
    Close only the synchronous driver.

    Useful when shutting down a Streamlit-specific process.
    """

    global _sync_driver

    if _sync_driver is None:
        return

    try:
        _sync_driver.close()
        _sync_driver = None

        logger.info(
            "Synchronous Neo4j driver closed."
        )

    except Exception as exc:
        logger.exception(
            "Failed to close synchronous Neo4j driver."
        )

        raise DatabaseConnectionError(
            "Unable to close synchronous database driver."
        ) from exc


# ============================================================
# QUERY VALIDATION
# ============================================================

def _validate_query(
    query: str,
    parameters: Optional[Dict[str, Any]],
) -> None:
    """
    Validate query input before sending it to Neo4j.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError(
            "Cypher query must be a non-empty string."
        )

    if parameters is not None and not isinstance(
        parameters, dict
    ):
        raise ValueError(
            "Query parameters must be provided as a dictionary."
        )


def _database_name():
    """
    Return the configured database name.

    If no database name is configured, Neo4j uses its default.
    """

    return NEO4J_DATABASE or None


# ============================================================
# ASYNCHRONOUS CYPHER EXECUTION
# ============================================================

async def run_cypher_async(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Execute a parameterized Cypher query asynchronously.

    Raises DatabaseQueryError when execution fails.
    """

    _validate_query(query, parameters)

    try:
        drv = get_driver()

        async with drv.session(
            database=_database_name()
        ) as session:

            result = await session.run(
                query,
                parameters or {},
                timeout=QUERY_TIMEOUT,
            )

            records = await result.data()

            return records

    except DatabaseError:
        raise

    except Exception as exc:
        logger.exception(
            "Asynchronous Cypher query failed."
        )

        raise DatabaseQueryError(
            "Asynchronous database query execution failed."
        ) from exc


# ============================================================
# SYNCHRONOUS CYPHER EXECUTION
# ============================================================

def run_cypher(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Execute a parameterized Cypher query synchronously.

    This function is intended for Streamlit and other
    synchronous callers.

    It deliberately does not use asyncio.run(),
    nest_asyncio, or event-loop manipulation.
    """

    _validate_query(query, parameters)

    try:
        drv = get_sync_driver()

        with drv.session(
            database=_database_name()
        ) as session:

            result = session.run(
                query,
                parameters or {},
                timeout=QUERY_TIMEOUT,
            )

            records = [record.data() for record in result]

            return records

    except DatabaseError:
        raise

    except Exception as exc:
        logger.exception(
            "Synchronous Cypher query failed."
        )

        raise DatabaseQueryError(
            "Synchronous database query execution failed."
        ) from exc


# ============================================================
# ASYNCHRONOUS DATABASE HEALTH CHECK
# ============================================================

async def check_database_health_async() -> Dict[str, Any]:
    """
    Verify actual Neo4j connectivity and measure response time.
    """

    start_time = time.perf_counter()

    try:
        drv = get_driver()

        await drv.verify_connectivity()

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        return {
            "connected": True,
            "status": "healthy",
            "latency": latency_ms,
            "database": _database_name() or "default",
            "error": None,
        }

    except Exception as exc:
        logger.exception(
            "Asynchronous database health check failed."
        )

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        return {
            "connected": False,
            "status": "unavailable",
            "latency": latency_ms,
            "database": _database_name() or "default",
            "error": "Database connection failed.",
        }


def check_database_health() -> Dict[str, Any]:
    """
    Synchronous health check for Streamlit.
    """

    start_time = time.perf_counter()

    try:
        drv = get_sync_driver()

        drv.verify_connectivity()

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        return {
            "connected": True,
            "status": "healthy",
            "latency": latency_ms,
            "database": _database_name() or "default",
            "error": None,
        }

    except Exception as exc:
        logger.exception(
            "Synchronous database health check failed."
        )

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        return {
            "connected": False,
            "status": "unavailable",
            "latency": latency_ms,
            "database": _database_name() or "default",
            "error": "Database connection failed.",
        }


# ============================================================
# LIVE GRAPH METRICS
# ============================================================

def get_graph_metrics() -> Dict[str, Any]:
    """
    Retrieve real node and relationship counts.

    No hardcoded latency or fabricated graph metrics.
    """

    health = check_database_health()

    if not health["connected"]:
        return {
            "nodes": None,
            "edges": None,
            "latency": health["latency"],
            "status": "unavailable",
            "connected": False,
            "error": health["error"],
        }

    try:
        nodes_result = run_cypher(
            "MATCH (n) RETURN count(n) AS nodes"
        )

        edges_result = run_cypher(
            "MATCH ()-[r]->() RETURN count(r) AS edges"
        )

        if not nodes_result or not edges_result:
            raise DatabaseQueryError(
                "Graph metrics query returned no results."
            )

        nodes_count = nodes_result[0]["nodes"]
        edges_count = edges_result[0]["edges"]

        return {
            "nodes": nodes_count,
            "edges": edges_count,
            "latency": health["latency"],
            "status": "healthy",
            "connected": True,
            "error": None,
        }

    except Exception as exc:
        logger.exception(
            "Unable to retrieve graph metrics."
        )

        return {
            "nodes": None,
            "edges": None,
            "latency": health["latency"],
            "status": "error",
            "connected": True,
            "error": "Unable to retrieve graph metrics.",
        }


async def get_graph_metrics_async() -> Dict[str, Any]:
    """
    Asynchronous version of live graph metrics.
    """

    health = await check_database_health_async()

    if not health["connected"]:
        return {
            "nodes": None,
            "edges": None,
            "latency": health["latency"],
            "status": "unavailable",
            "connected": False,
            "error": health["error"],
        }

    try:
        nodes_result = await run_cypher_async(
            "MATCH (n) RETURN count(n) AS nodes"
        )

        edges_result = await run_cypher_async(
            "MATCH ()-[r]->() RETURN count(r) AS edges"
        )

        if not nodes_result or not edges_result:
            raise DatabaseQueryError(
                "Graph metrics query returned no results."
            )

        return {
            "nodes": nodes_result[0]["nodes"],
            "edges": edges_result[0]["edges"],
            "latency": health["latency"],
            "status": "healthy",
            "connected": True,
            "error": None,
        }

    except Exception:
        logger.exception(
            "Unable to retrieve asynchronous graph metrics."
        )

        return {
            "nodes": None,
            "edges": None,
            "latency": health["latency"],
            "status": "error",
            "connected": True,
            "error": "Unable to retrieve graph metrics.",
        }


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

async def initialize_database() -> Dict[str, Any]:
    """
    Initialize the async driver and verify connectivity.

    Call during FastMCP application startup.
    """

    try:
        get_driver()

        health = await check_database_health_async()

        if not health["connected"]:
            raise DatabaseConnectionError(
                "Neo4j connectivity verification failed."
            )

        logger.info(
            "Neo4j database initialization completed successfully."
        )

        return health

    except DatabaseError:
        raise

    except Exception as exc:
        logger.exception(
            "Database initialization failed."
        )

        raise DatabaseConnectionError(
            "Database initialization failed."
        ) from exc
            
