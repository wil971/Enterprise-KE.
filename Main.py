# ============================================================
# ENTERPRISE INTELLIGENCE PLATFORM
# Main.py — Part 1 of 10
# ============================================================

import os
import io
import re
import json
import uuid
import hmac
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
    func,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from neo4j import AsyncGraphDatabase

from pypdf import PdfReader
from docx import Document as DocxDocument


# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("enterprise-intelligence")


# ------------------------------------------------------------
# ENVIRONMENT CONFIGURATION
# ------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

NEO4J_URI = os.getenv("NEO4J_URI", "").strip()
NEO4J_USERNAME = os.getenv(
    "NEO4J_USERNAME",
    os.getenv("NEO4J_USER", "neo4j"),
).strip()
NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD",
    os.getenv("NEO4J_PASS", ""),
)
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j").strip()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:3000",
).strip()

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", FRONTEND_URL).split(",")
    if origin.strip()
]

MAX_UPLOAD_BYTES = int(
    os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024))
)


# ------------------------------------------------------------
# REQUIRED CONFIGURATION CHECKS
# ------------------------------------------------------------

missing_settings = []

if not DATABASE_URL:
    missing_settings.append("DATABASE_URL")

if not NEO4J_URI:
    missing_settings.append("NEO4J_URI")

if not NEO4J_PASSWORD:
    missing_settings.append("NEO4J_PASSWORD")

if len(JWT_SECRET_KEY) < 32:
    missing_settings.append("JWT_SECRET_KEY (minimum 32 characters)")

if missing_settings:
    raise RuntimeError(
        "Missing or invalid Render environment variables: "
        + ", ".join(missing_settings)
    )


# ------------------------------------------------------------
# DATABASE URL NORMALIZATION
# ------------------------------------------------------------

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

elif DATABASE_URL.startswith("postgresql+psycopg://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql+psycopg://",
        "postgresql+asyncpg://",
        1,
    )


# ------------------------------------------------------------
# SQLALCHEMY ASYNC ENGINE
# ------------------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# ------------------------------------------------------------
# NEO4J ASYNC DRIVER
# ------------------------------------------------------------

neo4j_driver = AsyncGraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
    max_connection_pool_size=50,
    connection_timeout=20,
)


# ------------------------------------------------------------
# SECURITY HELPERS
# ------------------------------------------------------------

security = HTTPBearer(auto_error=False)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")

    salt = secrets.token_bytes(16)

    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )

    return (
        salt.hex()
        + "$"
        + derived.hex()
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, expected_hash = stored_hash.split("$", 1)

        salt = bytes.fromhex(salt_hex)

        actual_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
        ).hex()

        return hmac.compare_digest(actual_hash, expected_hash)

    except (ValueError, TypeError):
        return False


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
) -> str:
    now = utc_now()

    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


# ------------------------------------------------------------
# APPLICATION LIFESPAN
# ------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Enterprise Intelligence Platform")

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        await neo4j_driver.verify_connectivity()

        logger.info("PostgreSQL connection successful")
        logger.info("Neo4j connection successful")

        yield

    except Exception:
        logger.exception("Application startup failed")
        raise

    finally:
        await neo4j_driver.close()
        await engine.dispose()

        logger.info("Application resources closed")


# ------------------------------------------------------------
# FASTAPI APPLICATION
# ------------------------------------------------------------

app = FastAPI(
    title="Enterprise Intelligence Platform",
    description=(
        "Secure enterprise knowledge retrieval, "
        "document intelligence and graph exploration API."
    ),
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


# ------------------------------------------------------------
# BASIC HEALTH ENDPOINTS
# ------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "service": "Enterprise Intelligence Platform",
        "status": "online",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": utc_now().isoformat(),
    }


@app.get("/api/v1/health")
async def api_health():
    database_status = "connected"
    graph_status = "connected"

    try:
        async with engine.connect() as connection:
            await connection.execute(select(1))
    except Exception:
        database_status = "unavailable"

    try:
        await neo4j_driver.verify_connectivity()
    except Exception:
        graph_status = "unavailable"

    overall = (
        "healthy"
        if database_status == "connected"
        and graph_status == "connected"
        else "degraded"
    )

    return {
        "status": overall,
        "postgresql": database_status,
        "neo4j": graph_status,
        "timestamp": utc_now().isoformat(),
    }


# ============================================================
# END OF PART 1
# PART 2 GOES DIRECTLY BELOW THIS LINE
# ============================================================# ============================================================
# PART 2 — DATABASE MODELS
# ============================================================

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
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
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(320), nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(512), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(30), default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    organization = relationship("Organization", back_populates="users")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="member")
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    uploaded_by: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), default="")
    source: Mapped[str] = mapped_column(String(100), default="upload")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    text_hash: Mapped[str] = mapped_column(String(64), default="")
    acl_groups: Mapped[list] = mapped_column(
        JSON, default=lambda: ["tenant"]
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    organization = relationship("Organization", back_populates="documents")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
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
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
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
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_reference: Mapped[str] = mapped_column(
        String(200), default=""
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="KES")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


# ============================================================
# END OF PART 2
# PART 3 GOES DIRECTLY BELOW THIS LINE
# ============================================================# ============================================================
# PART 3 — AUTHENTICATION
# ============================================================

class RegisterInput(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserOutput(BaseModel):
    id: str
    tenant_id: str
    email: str
    full_name: str
    role: str


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")

        if not user_id or not tenant_id:
            raise HTTPException(status_code=401, detail="Invalid token")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def require_admin(
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


@app.post("/api/v1/auth/register")
async def register(
    data: RegisterInput,
    db: AsyncSession = Depends(get_db),
):
    email = data.email.lower().strip()

    existing = await db.execute(
        select(User).where(User.email == email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    try:
        password_hash = hash_password(data.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    organization = Organization(name=data.organization_name.strip())
    db.add(organization)
    await db.flush()

    user = User(
        tenant_id=organization.id,
        email=email,
        password_hash=password_hash,
        full_name=data.full_name.strip(),
        role="admin",
    )
    db.add(user)

    subscription = Subscription(
        tenant_id=organization.id,
        plan="free",
        status="trial",
        ends_at=utc_now() + timedelta(days=14),
    )
    db.add(subscription)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        user.id,
        user.tenant_id,
        user.role,
    )

    return {
        "message": "Account created",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "tenant_id": user.tenant_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@app.post("/api/v1/auth/login")
async def login(
    data: LoginInput,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == data.email.lower().strip())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    token = create_access_token(
        user.id,
        user.tenant_id,
        user.role,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "tenant_id": user.tenant_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@app.get("/api/v1/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


# ============================================================
# END OF PART 3
# PART 4 GOES DIRECTLY BELOW THIS LINE
# ============================================================
