# ============================================================
# ENTERPRISE INTELLIGENCE PLATFORM
# BACKEND - PART 1 OF 10
# Foundation, configuration, database and application setup
# ============================================================

import os
import uuid
import json
import hashlib
import secrets
import logging
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from typing import Optional, Any

import jwt
import httpx

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Request,
    Header,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pydantic import BaseModel, EmailStr, Field

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Text,
    Integer,
    JSON,
    ForeignKey,
    select,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from neo4j import AsyncGraphDatabase


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("enterprise_intelligence")


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

PROJECT_NAME = "Enterprise Intelligence Platform"

DATABASE_URL = os.getenv("DATABASE_URL", "")

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv(
    "NEO4J_USERNAME",
    os.getenv("NEO4J_USER", "neo4j"),
)
NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD",
    os.getenv("NEO4J_PASS", ""),
)
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:3000",
).rstrip("/")

CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", FRONTEND_URL).split(",")
    if origin.strip()
]


# ============================================================
# CONFIGURATION VALIDATION
# ============================================================

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing.")

if not NEO4J_URI:
    raise RuntimeError("NEO4J_URI is missing.")

if not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD is missing.")

if len(JWT_SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY must contain at least 32 characters."
    )


# ============================================================
# POSTGRESQL / SUPABASE CONNECTION
# ============================================================

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

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ============================================================
# DATABASE BASE
# ============================================================

class Base(DeclarativeBase):
    pass


# ============================================================
# NEO4J AURA CONNECTION
# ============================================================

neo4j_driver = AsyncGraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
)


# ============================================================
# SECURITY
# ============================================================

security_scheme = HTTPBearer(auto_error=False)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError(
            "Password must contain at least 12 characters."
        )

    salt = secrets.token_bytes(16)

    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )

    return (
        salt.hex()
        + "$"
        + digest.hex()
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, expected_hex = stored_hash.split("$", 1)

        salt = bytes.fromhex(salt_hex)

        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )

        return secrets.compare_digest(
            actual.hex(),
            expected_hex,
        )

    except (ValueError, TypeError):
        return False


# ============================================================
# APPLICATION LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting Enterprise Intelligence Backend")

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        await neo4j_driver.verify_connectivity()

        logger.info("Supabase PostgreSQL connection established")
        logger.info("Neo4j Aura connection established")

        yield

    except Exception:
        logger.exception("Backend startup failed")
        raise

    finally:
        await neo4j_driver.close()
        await engine.dispose()

        logger.info("Backend connections closed")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title=PROJECT_NAME,
    description=(
        "Secure enterprise knowledge retrieval, "
        "document intelligence and graph search API."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# ============================================================
# BASIC HEALTH ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {
        "name": PROJECT_NAME,
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": utc_now().isoformat(),
    }


@app.get("/api/v1/health")
async def detailed_health():

    postgres_status = "connected"
    neo4j_status = "connected"

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                select(1)
            )
    except Exception:
        postgres_status = "unavailable"

    try:
        await neo4j_driver.verify_connectivity()
    except Exception:
        neo4j_status = "unavailable"

    overall = (
        "healthy"
        if postgres_status == "connected"
        and neo4j_status == "connected"
        else "degraded"
    )

    return {
        "status": overall,
        "services": {
            "postgresql": postgres_status,
            "neo4j": neo4j_status,
        },
        "timestamp": utc_now().isoformat(),
    }


# ============================================================
# END OF PART 1
# PART 2 CONTINUES IN THIS SAME FILE
# ============================================================
