import uuid
from config import MAX_QUERY_RESULTS, NEO4J_DATABASE, logger
from database import get_driver
from security import validate_tenant_id, rate_limiter, write_audit_log

async def secure_graph_retrieval(tenant_id: str, topic: str) -> str:
    tenant_id = validate_tenant_id(tenant_id)

    if not topic or not topic.strip():
        raise ValueError("Search topic cannot be empty.")

    if not rate_limiter.allow(tenant_id):
        raise RuntimeError("Rate limit exceeded.")

    driver = get_driver()
    if driver is None:
        raise RuntimeError("Neo4j is not configured.")

    request_id = str(uuid.uuid4())

    query = """
    MATCH (t:Tenant {id: $tenant_id})-[:OWNS]->(d:Document)-[:MENTIONS]->(e:Entity)
    WHERE toLower(e.name) CONTAINS toLower($topic)
    RETURN e.name AS entity, d.title AS source
    LIMIT $limit
    """

    try:
        async with driver.session(database=NEO4J_DATABASE) as session:
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
            metadata={"topic": topic, "results": len(records)},
        )

        if not records:
            return f"No secure knowledge retrieved for '{topic}'."

        results = [f"- {record['entity']} (Source: {record['source']})" for record in records]
        return "Secure enterprise context:\n" + "\n".join(results)

    except Exception:
        logger.exception(f"Secure graph retrieval failed. request_id={request_id}")
        return "System error: secure retrieval aborted."
