from neo4j import AsyncGraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASS, logger

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
        logger.info("Neo4j driver pool closed.")
      
