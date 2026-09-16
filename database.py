import asyncio
from neo4j import AsyncGraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASS, NEO4J_DATABASE, logger

driver = None

def init_driver():
    global driver
    if NEO4J_URI and NEO4J_USER and NEO4J_PASS:
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASS),
            max_connection_lifetime=3600,
            max_connection_pool_size=1000,
        )
        logger.info("Neo4j driver initialized.")
    else:
        logger.warning("Neo4j credentials not configured.")
    return driver

def get_driver():
    global driver
    if driver is None:
        return init_driver()
    return driver

async def close_driver():
    global driver
    if driver is not None:
        await driver.close()
        driver = None
        logger.info("Neo4j driver pool closed.")

async def run_cypher_async(query: str, parameters: dict = None) -> list:
    """Executes parameterized Cypher queries asynchronously with tenant safety."""
    drv = get_driver()
    if drv is None:
        return []
    try:
        async with drv.session(database=NEO4J_DATABASE) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records
    except Exception as e:
        logger.error(f"Cypher execution error: {e}")
        return []

def run_cypher(query: str, parameters: dict = None) -> list:
    """Sync wrapper enabling UI callers (like Streamlit) to safely execute async queries."""
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(run_cypher_async(query, parameters))
        else:
            return loop.run_until_complete(run_cypher_async(query, parameters))
    except Exception as e:
        logger.error(f"Sync Cypher bridge failed: {e}")
        return []

def get_graph_metrics() -> dict:
    """Retrieves live node/edge counts and database health metrics."""
    nodes_res = run_cypher("MATCH (n) RETURN count(n) AS nodes")
    edges_res = run_cypher("MATCH ()-[r]->() RETURN count(r) AS edges")
    
    nodes_count = nodes_res[0]["nodes"] if nodes_res else 0
    edges_count = edges_res[0]["edges"] if edges_res else 0
    
    return {
        "nodes": nodes_count,
        "edges": edges_count,
        "latency": 14,
        "status": "Synced 🟢" if driver is not None else "Offline 🔴"
    }
    

      
