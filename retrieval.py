import asyncio
import json
import uuid
from typing import Any, Dict, List, Tuple

from config import MAX_QUERY_RESULTS, NEO4J_DATABASE, logger
from database import get_driver, run_cypher
from security import (
    validate_tenant_id,
    rate_limiter,
    write_audit_log,
)


# ==============================================================================
# RETRIEVAL LIMITS
# ==============================================================================

MAX_QUERY_LENGTH = 1000
MAX_DEPTH = 5


# ==============================================================================
# VALIDATION
# ==============================================================================

def validate_search_topic(topic: str) -> str:
    """Validate and normalize a search query."""

    if not isinstance(topic, str):
        raise ValueError("Search topic must be a string.")

    topic = topic.strip()

    if not topic:
        raise ValueError("Search topic cannot be empty.")

    if len(topic) > MAX_QUERY_LENGTH:
        raise ValueError(
            f"Search topic cannot exceed "
            f"{MAX_QUERY_LENGTH} characters."
        )

    return topic


def validate_depth(depth: int) -> int:
    """Keep graph traversal depth within safe limits."""

    if not isinstance(depth, int):
        raise ValueError("Graph depth must be an integer.")

    return max(1, min(depth, MAX_DEPTH))


# ==============================================================================
# ASYNC AUDIT HELPER
# ==============================================================================

async def _write_retrieval_audit(
    tenant_id: str,
    action: str,
    request_id: str,
    metadata: Dict[str, Any],
) -> bool:
    """
    Persist a retrieval audit event.

    Audit failures are logged rather than replacing a successful
    retrieval result with an unrelated audit error.
    """

    try:
        await write_audit_log(
            tenant_id=tenant_id,
            action=action,
            request_id=request_id,
            metadata=metadata,
        )

        return True

    except Exception:
        logger.exception(
            "Retrieval audit failed "
            "request_id=%s action=%s",
            request_id,
            action,
        )

        return False


# ==============================================================================
# SYNC AUDIT HELPER
# ==============================================================================

def _audit_sync(
    tenant_id: str,
    action: str,
    request_id: str,
    metadata: Dict[str, Any],
) -> bool:
    """
    Run the async audit function from synchronous retrieval functions.
    """

    async def _write() -> bool:
        return await _write_retrieval_audit(
            tenant_id=tenant_id,
            action=action,
            request_id=request_id,
            metadata=metadata,
        )

    try:
        asyncio.get_running_loop()

    except RuntimeError:
        return asyncio.run(_write())

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=1
    ) as executor:

        future = executor.submit(
            asyncio.run,
            _write(),
        )

        return future.result()


# ==============================================================================
# RESULT NORMALIZATION
# ==============================================================================

def _result_payload(
    query: str,
    mode: str,
    depth: int,
    records: List[Dict[str, Any]],
    request_id: str,
) -> Dict[str, Any]:
    """
    Convert raw Neo4j records into a consistent GraphRAG response.
    """

    entities: List[str] = []
    documents: List[str] = []
    relationships: List[Dict[str, Any]] = []
    lineage: List[Dict[str, Any]] = []

    seen_entities = set()
    seen_documents = set()

    for record in records:

        entity = record.get("entity")
        document = record.get("document")

        if entity and entity not in seen_entities:
            seen_entities.add(entity)
            entities.append(entity)

        if document and document not in seen_documents:
            seen_documents.add(document)
            documents.append(document)

        relationship = {
            "from": record.get("from_name"),
            "from_type": record.get("from_type"),
            "relationship": record.get("relationship"),
            "to": record.get("to_name"),
            "to_type": record.get("to_type"),
            "document": document,
            "document_id": record.get("document_id"),
        }

        if relationship["from"] or relationship["to"]:
            relationships.append(relationship)

        lineage.append(
            {
                "document_id": record.get("document_id"),
                "document": document,
                "entity": entity,
                "category": record.get("category"),
                "from": record.get("from_name"),
                "relationship": record.get("relationship"),
                "to": record.get("to_name"),
                "source_type": "neo4j",
            }
        )

    if records:
        answer = (
            f"Found {len(records)} relevant knowledge records "
            f"for '{query}'."
        )
    else:
        answer = (
            f"No relevant enterprise knowledge found "
            f"for '{query}'."
        )

    reasoning_path = [
        (
            "Tenant Boundary → "
            "Search started from documents owned by the "
            "requested tenant."
        ),
        f"Retrieval Mode → {mode}.",
        (
            f"Graph Depth → Maximum requested traversal "
            f"depth: {depth}."
        ),
        (
            f"Evidence → {len(records)} records returned "
            f"from Neo4j."
        ),
    ]

    return {
        "success": True,
        "answer": answer,
        "reasoning_path": reasoning_path,
        "lineage": lineage,
        "relationships": relationships,
        "entities": entities[:MAX_QUERY_RESULTS],
        "documents": documents[:MAX_QUERY_RESULTS],
        "result_count": len(records),
        "request_id": request_id,
            }# ==============================================================================
# SECURE GRAPH RETRIEVAL
# ==============================================================================

async def secure_graph_retrieval(
    tenant_id: str,
    topic: str,
) -> str:
    """
    Perform tenant-scoped graph retrieval.

    Retrieval begins at a Tenant-owned Document and searches actual
    document/entity data stored in Neo4j.
    """

    tenant_id = validate_tenant_id(tenant_id)
    topic = validate_search_topic(topic)

    if not rate_limiter.allow(tenant_id):
        raise RuntimeError("Rate limit exceeded.")

    driver = get_driver()

    if driver is None:
        raise RuntimeError(
            "Neo4j driver is not configured."
        )

    request_id = str(uuid.uuid4())

    query = """
    MATCH (t:Tenant {id: $tenant_id})
          -[:OWNS]->(d:Document)

    OPTIONAL MATCH (d)-[:MENTIONS]->(n)

    WHERE
        toLower(coalesce(d.title, ''))
            CONTAINS toLower($topic)
        OR
        toLower(coalesce(d.content, ''))
            CONTAINS toLower($topic)
        OR
        toLower(coalesce(n.name, ''))
            CONTAINS toLower($topic)
        OR
        toLower(coalesce(n.title, ''))
            CONTAINS toLower($topic)

    RETURN
        d.id AS document_id,
        d.title AS document,
        n.name AS entity,
        labels(n)[0] AS category,

        n.name AS from_name,
        labels(n)[0] AS from_type,

        CASE
            WHEN n IS NULL THEN NULL
            ELSE 'MENTIONS'
        END AS relationship,

        d.title AS to_name,
        'Document' AS to_type,

        d.updated_at AS updated_at

    ORDER BY d.updated_at DESC

    LIMIT $limit
    """

    try:
        async with driver.session(
            database=NEO4J_DATABASE
        ) as session:

            result = await session.run(
                query,
                tenant_id=tenant_id,
                topic=topic,
                limit=MAX_QUERY_RESULTS,
            )

            records = await result.data()

        payload = _result_payload(
            query=topic,
            mode="Tenant-Scoped Graph Retrieval",
            depth=1,
            records=records,
            request_id=request_id,
        )

        await _write_retrieval_audit(
            tenant_id=tenant_id,
            action="graph_retrieval",
            request_id=request_id,
            metadata={
                "query_length": len(topic),
                "results": len(records),
            },
        )

        return json.dumps(
            payload,
            indent=2,
            default=str,
        )

    except RuntimeError:
        raise

    except Exception:
        logger.exception(
            "Secure graph retrieval failed "
            "request_id=%s",
            request_id,
        )

        raise RuntimeError(
            "Secure retrieval failed."
        )


# ==============================================================================
# MULTI-HOP GRAPH EXECUTION
# ==============================================================================

def _execute_graph_records(
    tenant_id: str,
    query: str,
    depth: int,
) -> Tuple[
    List[Dict[str, Any]],
    str,
]:
    """
    Execute a real tenant-scoped Neo4j graph traversal.

    The traversal begins with documents owned by the tenant.
    It then follows real relationships from those documents up to
    the requested depth.

    No graph nodes or relationships are fabricated here.
    """

    depth = validate_depth(depth)

    # The depth value is validated and inserted only after validation.
    cypher = f"""
    MATCH (t:Tenant {{id: $tenant_id}})
          -[:OWNS]->(d:Document)

    OPTIONAL MATCH path=(d)-[rels*1..{depth}]-(n)

    WITH
        t,
        d,
        n,
        rels

    WHERE
        toLower(coalesce(d.title, ''))
            CONTAINS toLower($query)
        OR
        toLower(coalesce(d.content, ''))
            CONTAINS toLower($query)
        OR
        toLower(coalesce(n.name, ''))
            CONTAINS toLower($query)
        OR
        toLower(coalesce(n.title, ''))
            CONTAINS toLower($query)

    RETURN
        d.id AS document_id,
        d.title AS document,

        n.name AS entity,

        CASE
            WHEN n IS NULL THEN NULL
            ELSE labels(n)[0]
        END AS category,

        CASE
            WHEN n IS NULL THEN NULL
            ELSE coalesce(
                n.name,
                n.title,
                n.id
            )
        END AS from_name,

        CASE
            WHEN n IS NULL THEN NULL
            ELSE labels(n)[0]
        END AS from_type,

        CASE
            WHEN size(rels) = 0 THEN NULL
            ELSE type(rels[0])
        END AS relationship,

        CASE
            WHEN n IS NULL THEN NULL
            ELSE coalesce(
                n.name,
                n.title,
                n.id
            )
        END AS to_name,

        CASE
            WHEN n IS NULL THEN NULL
            ELSE labels(n)[0]
        END AS to_type,

        d.updated_at AS updated_at

    ORDER BY d.updated_at DESC

    LIMIT $limit
    """.strip()

    records = run_cypher(
        cypher,
        {
            "tenant_id": tenant_id,
            "query": query,
            "limit": MAX_QUERY_RESULTS,
        },
    )

    return records, cypher
