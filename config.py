import os
import logging

APP_NAME = os.getenv("APP_NAME", "AetherEnterpriseKnowledgeHub")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# Database Credentials
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASS = os.getenv("NEO4J_PASS")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Cloud AI Provider (Groq / OpenAI / Cloud API)
AI_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY")
AI_API_URL = os.getenv("AI_API_URL", "https://api.groq.com/openai/v1/chat/completions")
AI_MODEL = os.getenv("AI_MODEL", "llama-3.3-70b-versatile")

MAX_QUERY_RESULTS = int(os.getenv("MAX_QUERY_RESULTS", "25"))
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [AETHER] | %(message)s",
    force=True,
)
logger = logging.getLogger(APP_NAME)
