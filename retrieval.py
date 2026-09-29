import asyncio
import uuid
from typing import Any, Dict, List, Tuple

from config import MAX_QUERY_RESULTS, NEO4J_DATABASE, logger
from database import get_driver, run_cypher
from security import validate_tenant_id, rate_limiter, write_audit_log


MAX_QUERY_LENGTH = 1000
MAX_DEPTH = 5


def validate_search_topic(topic: str) -> str:
    if not isinstance(topic, str):
        raise ValueError("Search topic must be a string.")

    topic = topic.strip()

    if not topic:
        raise ValueError("Search topic cannot be empty.")

    if len(topic) > MAX_QUERY_LENGTH:
        raise ValueError(
            f"Search topic cannot exceed {MAX_QUERY_LENGTH} characters."
        )

    return topic


def validate_depth(depth: int) -> int:
    if not isinstance(depth, int):
        raise ValueError("Graph depth must be an integer.")

    if depth < 1:
        return 1

    return min(depth, MAX_DEPTH)


async def secure_graph_retrieval(
    tenant_id: str,
    topic: str,
) -> str:
    tenant_id = validate_tenant_id(tenant_id)
    topic = validate_search_topic(topic)

    if not rate_limiter.allow(tenant_id):
        raise RuntimeError("Rate limit exceeded.")

    driver = get_driver()

    if driver is None:
        raise RuntimeError("Neo4j driver is not configured.")

    request_id = str(uuid.uuid4())

    query = """
    MATCH (t:Tenant {id: $tenant_id})
          -[:OWNS]->(d:Document)
          -[:MENTIONS]->(e:Entity)

    WHERE toLower(coalesce(e.name, ''))
          CONTAINS toLower($topic)

    RETURN
        e.name AS entity,
        d.title AS source,
        d.id AS document_id

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

        await write_audit_log(
            tenant_id=tenant_id,
            action="graph_retrieval",
            request_id=request_id,
            metadata={
                "topic": topic,
                "results": len(records),
            },
        )

        if not records:
            return f"No secure knowledge retrieved for '{topic}'."

        results = []

        for record in records:
            entity = record.get("entity") or "Unknown entity"
            source = record.get("source") or "Unknown document"

            results.append(
                f"- {entity} (Source: {source})"
            )

        return (
            "Secure enterprise context:\n"
            + "\n".join(results)
        )

    except RuntimeError:
        raise

    except Exception:
        logger.exception(
            "Secure graph retrieval failed. request_id=%s",
            request_id,
        )
        raise RuntimeError("Secure retrieval failed.")


def hybrid_graph_vector_search(
    query: str,
    mode: str = "GraphRAG (Multi-Hop)",
    depth: int = 2,
    tenant_id: str = "default_tenant",
) -> Tuple[
    str,
    List[str],
    List[Dict[str, Any]],
    str,
]:
    tenant_id = validate_tenant_id(tenant_id)
    query = validate_search_topic(query)
    depth = validate_depth(depth)

    request_id = str(uuid.uuid4())

    cypher_trace = """
MATCH (t:Tenant {id: $tenant_id})
      -[:OWNS]->(d:Document)
      -[:MENTIONS]->(e:Entity)
WHERE toLower(coalesce(e.name, ''))
      CONTAINS toLower($query)
RETURN
    e.name AS entity,
    d.title AS source,
    d.id AS document_id
ORDER BY d.updated_at DESC
LIMIT $limit
""".strip()

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=1
            ) as executor:
                future = executor.submit(
                    asyncio.run,
                    secure_graph_retrieval(
                        tenant_id,
                        query,
                    ),
                )
                retrieved_text = future.result()
        else:
            retrieved_text = asyncio.run(
                secure_graph_retrieval(
                    tenant_id,
                    query,
                )
            )

        if retrieved_text.startswith(
            "No secure knowledge retrieved"
        ):
            answer = retrieved_text
        else:
            answer = (
                f"Graph retrieval completed for '{query}'."
            )

        reasoning_paths = [
            (
                "Tenant Boundary → "
                f"Search restricted to tenant '{tenant_id}'."
            ),
            (
                "Graph Retrieval → "
                f"Executed secure graph search using mode '{mode}' "
                f"with requested depth {depth}."
            ),
            (
                "Audit Trail → "
                f"Request ID {request_id} generated for this operation."
            ),
        ]

        lineage_data: List[Dict[str, Any]] = []

        if retrieved_text.startswith(
            "Secure enterprise context:"
        ):
            lines = retrieved_text[
                len("Secure enterprise context:\n"):
            ].splitlines()

            for index, line in enumerate(lines):
                if not line.startswith("- "):
                    continue

                content = line[2:].strip()

                if " (Source: " in content:
                    entity_name, source_part = content.split(
                        " (Source: ",
                        1,
                    )
                    source_name = source_part.rstrip(")")
                else:
                    entity_name = content
                    source_name = "Unknown"

                lineage_data.append(
                    {
                        "Node ID": f"ENTITY-{index + 1}",
                        "Entity": entity_name,
                        "Document Name": source_name,
                        "Relationship": "MENTIONS",
                        "Status": "Retrieved",
                    }
                )

        return (
            answer,
            reasoning_paths,
            lineage_data,
            cypher_trace,
        )

    except RuntimeError as exc:
        logger.error(
            "Graph search failed request_id=%s: %s",
            request_id,
            exc,
        )

        return (
            "Graph retrieval could not be completed.",
            [
                "Retrieval stopped because the secure "
                "retrieval layer rejected the request."
            ],
            [],
            cypher_trace,
        )

    except Exception:
        logger.exception(
            "Hybrid retrieval failed request_id=%s",
            request_id,
        )

        return (
            "Graph retrieval could not be completed.",
            [
                "Retrieval stopped because an internal "
                "system error occurred."
            ],
            [],
            cypher_trace,
        )


def execute_graphrag_query(
    tenant_id: str,
    query_text: str,
    search_mode: str = "GraphRAG (Multi-Hop)",
    max_depth: int = 2,
) -> Dict[str, Any]:

    tenant_id = validate_tenant_id(tenant_id)
    query_text = validate_search_topic(query_text)
    max_depth = validate_depth(max_depth)

    if not rate_limiter.allow(tenant_id):
        return {
            "answer": "Rate limit exceeded.",
            "reasoning_path": [
                "Request rejected by the tenant rate limiter."
            ],
            "lineage": [],
            "cypher_trace": "",
        }

    request_id = str(uuid.uuid4())

    cypher_query = """
MATCH (t:Tenant {id: $tenant_id})
      -[:OWNS]->(d:Document)
      -[:MENTIONS]->(n)
WHERE
    toLower(coalesce(n.name, ''))
        CONTAINS toLower($query)
    OR
    toLower(coalesce(d.title, ''))
        CONTAINS toLower($query)

RETURN
    d.title AS document,
    n.name AS entity,
    labels(n)[0] AS category,
    d.id AS document_id

ORDER BY d.updated_at DESC

LIMIT $limit
""".strip()

    try:
        results = run_cypher(
            cypher_query,
            {
                "tenant_id": tenant_id,
                "query": query_text,
                "limit": MAX_QUERY_RESULTS,
            },
        )

        entities = list(
            dict.fromkeys(
                result.get("entity")
                for result in results
                if result.get("entity")
            )
        )

        if results:
            answer = (
                f"Graph search identified "
                f"{len(results)} relevant graph records "
                f"for '{query_text}'."
            )
        else:
            answer = (
                f"No active graph pathways found for "
                f"'{query_text}'."
            )

        reasoning_path = [
            (
                "Tenant Boundary → "
                f"Query restricted to tenant '{tenant_id}'."
            ),
            (
                "Graph Traversal → "
                f"Search mode '{search_mode}' "
                f"with maximum depth {max_depth}."
            ),
            (
                "Result Evaluation → "
                f"{len(results)} graph records returned."
            ),
        ]

        try:
            asyncio.run(
                write_audit_log(
                    tenant_id=tenant_id,
                    action="graphrag_query",
                    request_id=request_id,
                    metadata={
                        "query": query_text,
                        "results": len(results),
                        "mode": search_mode,
                        "depth": max_depth,
                    },
                )
            )
        except Exception:
            logger.exception(
                "Failed to audit GraphRAG query request_id=%s",
                request_id,
            )

        return {
            "answer": answer,
            "reasoning_path": reasoning_path,
            "lineage": results,
            "cypher_trace": cypher_query,
            "entities": entities[:10],
            "request_id": request_id,
        }

    except Exception:
        logger.exception(
            "GraphRAG query failed request_id=%s",
            request_id,
        )

        return {
            "answer": "Graph retrieval could not be completed.",
            "reasoning_path": [
                "Traversal failed during secure Cypher execution."
            ],
            "lineage": [],
            "cypher_trace": cypher_query,
            "entities": [],
            "request_id": request_id,
                }
