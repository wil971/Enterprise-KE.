
# ============================================================================
# ENTERPRISE KNOWLEDGE PLATFORM
# PART 1/10 — CONFIGURATION, DATABASES AND APPLICATION STARTUP
# ============================================================================

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from neo4j import AsyncGraphDatabase

from fastmcp import FastMCP


# ----------------------------------------------------------------------------
# 1.1 LOGGING
# ----------------------------------------------------------------------------

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger("EnterpriseIntelligence")


# ----------------------------------------------------------------------------
# 1.2 ENVIRONMENT CONFIGURATION
# ----------------------------------------------------------------------------

PROJECT_NAME = "Enterprise Context & Intelligence Platform"
PROJECT_VERSION = "3.0.0"

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
AUDIT_SIGNING_KEY = os.getenv("AUDIT_SIGNING_KEY", "")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

NEO4J_URI = os.getenv("NEO4J_URI", "").strip()
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j").strip()
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j").strip()

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "https://enterprise-ke-hqrlscaknjikcwz5kpndrt.streamlit.app",
    ).split(",")
    if origin.strip()
]

# Validate critical configuration before starting the application.
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from environment variables.")

if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters.")

if not AUDIT_SIGNING_KEY or len(AUDIT_SIGNING_KEY) < 32:
    raise RuntimeError("AUDIT_SIGNING_KEY must contain at least 32 characters.")

if not NEO4J_URI or not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_URI or NEO4J_PASSWORD is missing.")


# ----------------------------------------------------------------------------
# 1.3 NORMALIZE POSTGRESQL URL
# ----------------------------------------------------------------------------

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+asyncpg://",
        1,
    )
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )

if not DATABASE_URL.startswith("postgresql+asyncpg://"):
    raise RuntimeError(
        "DATABASE_URL must be a PostgreSQL connection string "
        "compatible with asyncpg."
    )


# ----------------------------------------------------------------------------
# 1.4 POSTGRESQL CONNECTION
# ----------------------------------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    connect_args={
        "ssl": "require",
        "timeout": 30,
    },
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# All SQLAlchemy models in Part 2 must inherit from this same Base.
Base = declarative_base()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional database session to API routes."""

    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ----------------------------------------------------------------------------
# 1.5 NEO4J AURA CONNECTION
# ----------------------------------------------------------------------------

neo4j_driver = None
neo4j_connected = False


async def connect_neo4j() -> None:
    """Connects to Neo4j Aura and verifies database connectivity."""

    global neo4j_driver, neo4j_connected

    neo4j_driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        max_connection_pool_size=50,
        connection_timeout=30,
    )

    await neo4j_driver.verify_connectivity()

    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run("RETURN 1 AS connection_test")
        record = await result.single()

        if not record or record["connection_test"] != 1:
            raise RuntimeError("Neo4j connection verification failed.")

    neo4j_connected = True

    logger.info("Neo4j Aura connection verified.")


async def close_neo4j() -> None:
    """Closes Neo4j connections during application shutdown."""

    global neo4j_driver, neo4j_connected

    if neo4j_driver is not None:
        await neo4j_driver.close()

    neo4j_driver = None
    neo4j_connected = False

    logger.info("Neo4j connection closed.")


# ----------------------------------------------------------------------------
# 1.6 FASTMCP INSTANCE
# ----------------------------------------------------------------------------

mcp = FastMCP("EnterpriseIntelligence")


# ----------------------------------------------------------------------------
# 1.7 APPLICATION LIFESPAN
# ----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting Enterprise Intelligence Platform.")

    try:
        # Verify PostgreSQL.
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        logger.info("Supabase PostgreSQL connection verified.")

        # Verify Neo4j.
        await connect_neo4j()

        # Models declared in Part 2 are loaded before application startup.
        # Tables are created only after all model declarations have loaded.
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        logger.info("Database schema initialization completed.")

        yield

    except Exception:
        logger.exception("Application startup failed.")
        raise

    finally:
        await close_neo4j()
        await engine.dispose()

        logger.info("Enterprise Intelligence Platform stopped.")


# ----------------------------------------------------------------------------
# 1.8 SINGLE FASTAPI APPLICATION
# ----------------------------------------------------------------------------

app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
    description=(
        "Multi-tenant enterprise search, knowledge graph "
        "and secure context retrieval platform."
    ),
    lifespan=lifespan,
)


# ----------------------------------------------------------------------------
# 1.9 CORS
# ----------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-ID"],
)


# ----------------------------------------------------------------------------
# 1.10 HEALTH ENDPOINTS
# ----------------------------------------------------------------------------

@app.get("/", tags=["System"])
async def root_entry():
    return {
        "service": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "status": "online",
        "documentation": "/docs",
        "health": "/api/v1/health",
    }


@app.get("/api/v1/health", tags=["System"])
async def system_health():

    return {
        "service": PROJECT_NAME,
        "status": "running",
        "version": PROJECT_VERSION,
        "neo4j_connected": neo4j_connected,
    }


@app.get("/api/v1/health/database", tags=["System"])
async def database_health():

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        return {
            "status": "connected",
            "database": "postgresql",
            "provider": "supabase",
        }

    except Exception:
        logger.exception("PostgreSQL health check failed")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL database unavailable.",
        )


@app.get("/api/v1/health/neo4j", tags=["System"])
async def neo4j_health():

    if neo4j_driver is None or not neo4j_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j is not connected.",
        )

    try:
        async with neo4j_driver.session(
            database=NEO4J_DATABASE
        ) as session:

            result = await session.run("RETURN 1 AS check")
            await result.single()

        return {
            "status": "connected",
            "database": NEO4J_DATABASE,
            "provider": "neo4j_aura",
        }

    except Exception:
        logger.exception("Neo4j health check failed")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database unavailable.",
)
        
# ============================================================================
# PART 2/10 — SQLALCHEMY MODELS
# ============================================================================

import uuid

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,
    JSON,
    Integer,
    Float,
    ForeignKey,
    UniqueConstraint,
    Index,
)


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


# ----------------------------------------------------------------------------
# 2.1 TENANTS
# ----------------------------------------------------------------------------

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=new_id)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    plan = Column(String(50), nullable=False, default="STANDARD")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# ----------------------------------------------------------------------------
# 2.2 USERS
# ----------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=new_id)
    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email = Column(String(320), nullable=False, index=True)
    password_hash = Column(String(500), nullable=True)
    full_name = Column(String(200), nullable=True)

    role = Column(String(50), nullable=False, default="employee")
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)

    google_subject = Column(String(255), nullable=True, unique=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )


# ----------------------------------------------------------------------------
# 2.3 DOCUMENTS
# ----------------------------------------------------------------------------

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=new_id)

    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    workspace_id = Column(String(36), nullable=True, index=True)

    title = Column(String(500), nullable=False)
    filename = Column(String(500), nullable=True)
    content = Column(Text, nullable=False, default="")
    content_hash = Column(String(128), nullable=True, index=True)

    source_app = Column(
        String(100),
        nullable=False,
        default="knowledge_graph",
    )

    external_id = Column(String(500), nullable=True)
    source_url = Column(Text, nullable=True)

    author_name = Column(String(200), nullable=True)
    author_avatar = Column(Text, nullable=True)

    acl_read_groups = Column(
        JSON,
        nullable=False,
        default=lambda: ["public"],
    )

    status = Column(String(50), nullable=False, default="indexed")
    metadata_json = Column(JSON, nullable=False, default=dict)

    uploaded_by = Column(String(36), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_documents_tenant_workspace", "tenant_id", "workspace_id"),
        UniqueConstraint(
            "tenant_id",
            "source_app",
            "external_id",
            name="uq_document_external_source",
        ),
    )


# ----------------------------------------------------------------------------
# 2.4 KNOWLEDGE GRAPH EDGES
# ----------------------------------------------------------------------------

class KnowledgeGraphEdge(Base):
    __tablename__ = "knowledge_graph_edges"

    id = Column(String(36), primary_key=True, default=new_id)

    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_entity = Column(String(500), nullable=False, index=True)
    target_entity = Column(String(500), nullable=False, index=True)

    relation_type = Column(String(150), nullable=False)
    properties_json = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index(
            "ix_graph_edge_tenant_source",
            "tenant_id",
            "source_entity",
        ),
        Index(
            "ix_graph_edge_tenant_target",
            "tenant_id",
            "target_entity",
        ),
    )


# ----------------------------------------------------------------------------
# 2.5 AUDIT LOGS
# ----------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=new_id)

    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)

    action = Column(String(150), nullable=False)
    resource = Column(String(500), nullable=False)

    metadata_json = Column(JSON, nullable=False, default=dict)

    ip_address = Column(String(100), nullable=True)
    signature = Column(String(128), nullable=False)

    timestamp = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )


# ----------------------------------------------------------------------------
# 2.6 SUBSCRIPTIONS
# ----------------------------------------------------------------------------

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=new_id)

    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    plan_name = Column(String(100), nullable=False, default="STANDARD")
    status = Column(String(50), nullable=False, default="trial")

    currency = Column(String(10), nullable=False, default="KES")
    monthly_price = Column(Float, nullable=False, default=0.0)

    payment_provider = Column(String(100), nullable=True)
    provider_subscription_id = Column(String(255), nullable=True)

    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# ----------------------------------------------------------------------------
# 2.7 PAYMENT RECORDS
# ----------------------------------------------------------------------------

class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(String(36), primary_key=True, default=new_id)

    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    subscription_id = Column(
        String(36),
        ForeignKey("subscriptions.id"),
        nullable=True,
    )

    provider = Column(String(100), nullable=False)
    provider_reference = Column(String(255), nullable=True, unique=True)

    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="KES")
    status = Column(String(50), nullable=False, default="pending")

    payment_metadata = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# ----------------------------------------------------------------------------
# 2.8 CONNECTOR ACCOUNTS
# ----------------------------------------------------------------------------

class ConnectorAccount(Base):
    __tablename__ = "connector_accounts"

    id = Column(String(36), primary_key=True, default=new_id)

    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider = Column(String(100), nullable=False)
    external_account_id = Column(String(255), nullable=True)

    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default="pending")
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# ----------------------------------------------------------------------------
# 2.9 WEBHOOK EVENTS
# ----------------------------------------------------------------------------

class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String(36), primary_key=True, default=new_id)

    provider = Column(String(100), nullable=False)
    event_id = Column(String(255), nullable=False)
    event_type = Column(String(150), nullable=False)

    payload = Column(JSON, nullable=False, default=dict)
    processed = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "event_id",
            name="uq_webhook_provider_event",
        ),
    )
    
