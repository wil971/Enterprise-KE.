import os
import logging
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

APP_NAME = os.getenv("APP_NAME", "AetherEnterpriseKnowledgeHub")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# System Backend & Auth Credentials
BACKEND_URL = os.getenv("BACKEND_URL", "https://enterprise-ke-3.onrender.com")
ENTERPRISE_API_KEY = os.getenv("ENTERPRISE_API_KEY", "ENTERPRISE-2026")

# Database Credentials
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS") or os.getenv("NEO4J_PASSWORD", "password")
NEO4J_PASSWORD = NEO4J_PASS  # Alias for standard Neo4j driver compatibility
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Cloud AI Provider (Groq / OpenAI / Cloud API)
AI_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY")
AI_API_URL = os.getenv("AI_API_URL", "https://api.groq.com/openai/v1/chat/completions")
AI_MODEL = os.getenv("AI_MODEL", "llama-3.3-70b-versatile")

# Execution Thresholds
MAX_QUERY_RESULTS = int(os.getenv("MAX_QUERY_RESULTS", "25"))
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))

# Central Logger Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [AETHER] | %(message)s",
    force=True,
)
logger = logging.getLogger(APP_NAME)
