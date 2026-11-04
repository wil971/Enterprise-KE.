import os
import io
import re
import uuid
import json
import hmac
import hashlib
import secrets
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from typing import Optional

import jwt
from fastapi import (
    FastAPI, HTTPException, Depends, UploadFile, File,
    Request, Header
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import (
    String, Boolean, DateTime, Text, Integer, JSON,
    ForeignKey, UniqueConstraint, select, func
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.orm import sessionmaker
from neo4j import AsyncGraphDatabase
from pypdf import PdfReader
from docx import Document as DocxDocument

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enterprise-knowledge-graph")

# YOUR ACTUAL RENDER BACKEND URL
BACKEND_PUBLIC_URL = "https://enterprise-ke-3.onrender.com"

# SUPABASE POSTGRESQL
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing.")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://", "postgresql+asyncpg://", 1
    )
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )

# NEO4J
NEO4J_URI = os.getenv("NEO4J_URI", "").strip()
NEO4J_USERNAME = os.getenv(
    "NEO4J_USERNAME",
    os.getenv("NEO4J_USER", "neo4j")
)
NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD",
    os.getenv("NEO4J_PASS", "")
)
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

if not NEO4J_URI or not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_URI or NEO4J_PASSWORD is missing.")

# SECURITY
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()
if len(JWT_SECRET_KEY) < 32:
    raise RuntimeError(
        "Set JWT_SECRET_KEY to a secure value of at least 32 characters."
    )

JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

MAX_UPLOAD_BYTES = int(
    os.getenv("MAX_UPLOAD_BYTES", "26214400")
)

# FRONTEND CORS: configure your actual frontend domain in Render.
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS", FRONTEND_URL
    ).split(",")
    if origin.strip()
]

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

neo4j_driver = AsyncGraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
    max_connection_pool_size=50,
    connection_timeout=20,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


def utc_now():
    return datetime.now(timezone.utc)


security = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        await neo4j_driver.verify_connectivity()
        logger.info("Supabase PostgreSQL connected.")
        logger.info("Neo4j connected.")
        logger.info("Backend URL: %s", BACKEND_PUBLIC_URL)

        yield

    finally:
        await neo4j_driver.close()
        await engine.dispose()


app = FastAPI(
    title="Enterprise Knowledge Graph API",
    description="Enterprise document retrieval and knowledge graph backend.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-ID"],
)


@app.get("/")
async def root():
    return {
        "application": "Enterprise Knowledge Graph",
        "backend_url": BACKEND_PUBLIC_URL,
        "status": "online",
        "documentation": f"{BACKEND_PUBLIC_URL}/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "online",
        "backend_url": BACKEND_PUBLIC_URL,
        "timestamp": utc_now().isoformat(),
}class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    users = relationship("User", back_populates="organization")
    documents = relationship("Document", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(30), default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    organization = relationship("Organization", back_populates="users")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "email",
            name="uq_user_tenant_email"
        ),
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    uploaded_by: Mapped[str] = mapped_column(
        ForeignKey("users.id")
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), default="")
    source: Mapped[str] = mapped_column(String(100), default="upload")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    text_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    organization = relationship("Organization", back_populates="documents")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(150), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), default="")
    resource_id: Mapped[str] = mapped_column(String(100), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    plan: Mapped[str] = mapped_column(String(50), default="free")
    status: Mapped[str] = mapped_column(String(30), default="trial")
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_reference: Mapped[str] = mapped_column(
        String(200), default=""
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
        )
