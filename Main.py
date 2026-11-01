# PART 1/10 — IMPORTS, SETTINGS, DATABASES AND APPLICATION CONFIGURATION
# ============================================================================

import os
import re
import io
import json
import uuid
import time
import hmac
import base64
import hashlib
import html as html_lib
import logging
import secrets
from enum import Enum
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from contextlib import asynccontextmanager
from typing import Any, Optional, Literal
from urllib.parse import urlencode, quote

import httpx
import jwt
from fastapi import (
    FastAPI, Depends, HTTPException, status, Request, UploadFile, File,
    Form, BackgroundTasks, Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, JSON, Integer, Numeric,
    ForeignKey, UniqueConstraint, Index, select, or_, and_, func, text,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import make_url
from pgvector.sqlalchemy import VECTOR
from neo4j import AsyncGraphDatabase
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token
from pwdlib import PasswordHash
from pypdf import PdfReader
from docx import Document as WordDocument
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("enterprise.platform")


def env_value(*names: str, default: Optional[str] = None) -> Optional[str]:
    """Read an environment variable while preserving the user's existing names."""
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip() != "":
            return value.strip()
    return default


PROJECT_NAME = env_value("PROJECT_NAME", default="Enterprise Knowledge Platform")
PROJECT_VERSION = "3.0.0"
ENVIRONMENT = env_value("ENVIRONMENT", "environment", default="production").lower()

# Existing Render variable names from the supplied screenshot are supported.
DATABASE_URL_RAW = env_value("DATABASE_URL", "database_url")
NEO4J_URI = env_value("NEO4J_URI", "neo4j_uri")
NEO4J_USERNAME = env_value("NEO4J_USERNAME", "NEO4J_USER", "neo4j_user", default="neo4j")
NEO4J_PASSWORD = env_value("NEO4J_PASSWORD", "NEO4J_PASS", "neo4j_pass")
NEO4J_DATABASE = env_value("NEO4J_DATABASE", "neo4j_database", default="neo4j")
JWT_SECRET_KEY = env_value("JWT_SECRET_KEY", "jwt_secret_key")
GOOGLE_CLIENT_ID = env_value("GOOGLE_CLIENT_ID", "Client_Id", "CLIENT_ID", "client_id")
GOOGLE_CLIENT_SECRET = env_value("GOOGLE_CLIENT_SECRET", "Client_Secret", "CLIENT_SECRET", "client_secret")
NVIDIA_API_KEY = env_value("NVIDIA_API_KEY", "nvidia_api_key")
ALLOW_EXTERNAL_AI_PROCESSING = env_value("ALLOW_EXTERNAL_AI_PROCESSING", default="false").lower() in {"1", "true", "yes"}
NVIDIA_MODEL = env_value("NVIDIA_MODEL", default="meta/llama-3.3-70b-instruct")
NVIDIA_EMBEDDING_MODEL = env_value("NVIDIA_EMBEDDING_MODEL", default="nvidia/nemotron-3-embed-1b")
EMBEDDING_DIMENSIONS = 2048
NVIDIA_BASE_URL = env_value("NVIDIA_BASE_URL", default="https://integrate.api.nvidia.com/v1")

JWT_ALGORITHM = "HS256"
JWT_ISSUER = env_value("JWT_ISSUER", default="enterprise-knowledge-platform")
JWT_AUDIENCE = env_value("JWT_AUDIENCE", default="enterprise-platform-api")
ACCESS_TOKEN_EXPIRE_MINUTES = int(env_value("ACCESS_TOKEN_EXPIRE_MINUTES", default="60"))

if not DATABASE_URL_RAW:
    raise RuntimeError("Missing Render environment variable: database_url (or DATABASE_URL).")
if not NEO4J_URI or not NEO4J_PASSWORD:
    raise RuntimeError("Missing Render environment variables: NEO4J_URI and NEO4J_PASS (or NEO4J_PASSWORD).")
if not JWT_SECRET_KEY or len(JWT_SECRET_KEY.encode("utf-8")) < 32:
    raise RuntimeError("Set JWT_SECRET_KEY in Render to a random secret of at least 32 bytes.")

# Derive a distinct HMAC key if AUDIT_SIGNING_KEY is not configured. This keeps
# audit signatures cryptographically separate from JWT signatures.
AUDIT_SIGNING_KEY = env_value("AUDIT_SIGNING_KEY", "audit_signing_key")
if not AUDIT_SIGNING_KEY:
    AUDIT_SIGNING_KEY = hmac.new(
        JWT_SECRET_KEY.encode("utf-8"), b"enterprise-audit-chain-v1", hashlib.sha256
    ).hexdigest()

# Supabase direct/session-pooler URLs are accepted. Transaction pooler mode
# (port 6543) disables asyncpg/SQLAlchemy prepared-statement caches.
db_url = make_url(DATABASE_URL_RAW)
if db_url.drivername in ("postgres", "postgresql"):
    db_url = db_url.set(drivername="postgresql+asyncpg")
if db_url.drivername != "postgresql+asyncpg":
    raise RuntimeError("database_url must be a PostgreSQL URL for Supabase.")
query_params = dict(db_url.query)
ssl_mode = query_params.pop("sslmode", None)
connect_args: dict[str, Any] = {
    "ssl": "require",
    "timeout": 30,
    "server_settings": {"search_path": "public,extensions"},
}
if db_url.port == 6543:
    connect_args["statement_cache_size"] = 0
    query_params["prepared_statement_cache_size"] = "0"
db_url = db_url.set(query=query_params)

engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    connect_args=connect_args,
)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()

neo4j_driver = AsyncGraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
    connection_timeout=30,
    max_connection_pool_size=50,
)
neo4j_connected = False
password_hasher = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Restrict CORS to known website origins; never combine wildcard origins and
# credentialed requests in a production multi-tenant application.
DEFAULT_ORIGINS = "https://enterprise-ke-hqrlscaknjikcwz5kpndrt.streamlit.app"
CORS_ORIGINS = [
    item.strip().rstrip("/")
    for item in env_value("CORS_ORIGINS", default=DEFAULT_ORIGINS).split(",")
    if item.strip() and item.strip() != "*"
]

# The same JWT issuer signs REST and MCP tokens; MCP requires its own audience.
mcp_auth = JWTVerifier(
    public_key=JWT_SECRET_KEY,
    algorithm=JWT_ALGORITHM,
    issuer=JWT_ISSUER,
    audience="enterprise-platform-mcp",
    required_scopes=["mcp:use"],
)
mcp = FastMCP(PROJECT_NAME, auth=mcp_auth)

app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
    description="Multi-tenant enterprise knowledge, search and graph API",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# ============================================================================
# PART 2/10 — RELATIONAL DATA MODEL (ONE SHARED SQLALCHEMY BASE)
# ============================================================================


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String(36), primary_key=True, default=new_id)
    name = Column(String(255), nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=new_id)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(320), nullable=False)
    full_name = Column(String(255), nullable=False, default="")
    password_hash = Column(String(255), nullable=True)
    google_subject = Column(String(255), unique=True, nullable=True)
    role = Column(String(30), nullable=False, default="employee")
    groups = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),)


class Invitation(Base):
    __tablename__ = "invitations"
    id = Column(String(36), primary_key=True, default=new_id)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(320), nullable=False)
    role = Column(String(30), nullable=False, default="employee")
    token_hash = Column(String(64), unique=True, nullable=False)
    invited_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class DocumentRecord(Base):
    __tablename__ = "documents"
    id = Column(String(36), primary_key=True, default=new_id)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    filename = Column(String(500), nullable=True)
    content = Column(Text, nullable=False, default="")
    content_hash = Column(String(64), nullable=False)
    source_app = Column(String(80), nullable=False, default="upload")
    external_id = Column(String(500), nullable=True)
    source_url = Column(Text, nullable=True)
    author_name = Column(String(255), nullable=True)
    acl_user_ids = Column(JSON, nullable=False, default=list)
    acl_emails = Column(JSON, nullable=False, default=list)
    acl_groups = Column(JSON, nullable=False, default=list)
    status = Column(String(30), nullable=False, default="indexed")
    metadata_json = Column(JSON, nullable=False, default=dict)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_app", "external_id", name="uq_documents_external_source"),
        Index("ix_documents_tenant_updated", "tenant_id", "updated_at"),
    )


class DocumentChunk(Base):
    """Searchable document passages with NVIDIA dense embeddings in Supabase pgvector."""
    __tablename__ = "document_chunks"
    id = Column(String(36), primary_key=True, default=new_id)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(VECTOR(2048), nullable=True)
    embedding_model = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
        Index("ix_document_chunks_tenant_document", "tenant_id", "document_id"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, default=new_id)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(500), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    ip_address = Column(String(64), nullable=True)
    previous_signature = Column(String(64), nullable=True)
    signature = Column(String(64), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(String(36), primary_key=True, default=new_id)
    code = Column(String(80), unique=True, nullable=False)
    name = Column(String(160), nullable=False)
    price_kes = Column(Numeric(12, 2), nullable=False)
    billing_days = Column(Integer, nullable=False, default=30)
    seats = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String(36), primary_key=True, default=new_id)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan_id = Column(String(36), ForeignKey("subscription_plans.id"), nullable=True)
    status = Column(String(30), nullable=False, default="inactive")
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class PaymentRecord(Base):
    __tablename__ = "payment_records"
    id = Column(String(36), primary_key=True, default=new_id)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(String(36), ForeignKey("subscription_plans.id"), nullable=False)
    provider = Column(String(40), nullable=False, default="mpesa")
    phone_number = Column(String(20), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(8), nullable=False, default="KES")
    status = Column(String(30), nullable=False, default="pending")
    merchant_request_id = Column(String(120), nullable=True)
    checkout_request_id = Column(String(120), unique=True, nullable=True)
    provider_receipt = Column(String(120), unique=True, nullable=True)
    result_code = Column(String(30), nullable=True)
    result_description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class ConnectorAccount(Base):
    __tablename__ = "connector_accounts"
    id = Column(String(36), primary_key=True, default=new_id)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(80), nullable=False)
    external_account_id = Column(String(255), nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    sync_cursor = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="connected")
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (UniqueConstraint("tenant_id", "provider", name="uq_connector_tenant_provider"),)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id = Column(String(36), primary_key=True, default=new_id)
    provider = Column(String(80), nullable=False)
    event_id = Column(String(255), nullable=False)
    event_type = Column(String(120), nullable=False)
    payload_json = Column(JSON, nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event"),)


# ============================================================================
# PART 3/10 — REQUEST SCHEMAS, JWT SECURITY AND ACCESS CONTROL
# ============================================================================


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    tenant_slug: Optional[str] = Field(default=None, max_length=120)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=20)


class InviteRequest(BaseModel):
    email: EmailStr
    role: Literal["employee", "admin"] = "employee"


class AcceptInvitationRequest(BaseModel):
    invitation_token: str = Field(min_length=20)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=256)


class UpdateUserGroupsRequest(BaseModel):
    groups: list[str] = Field(default_factory=list, max_length=50)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=10, ge=1, le=50)
    workspace_id: Optional[str] = None
    source_app: Optional[str] = None


class ReindexRequest(BaseModel):
    after_id: Optional[str] = None
    batch_size: int = Field(default=10, ge=1, le=25)


class CreatePlanRequest(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    price_kes: float = Field(gt=0, le=10_000_000)
    billing_days: int = Field(default=30, ge=1, le=3650)
    seats: int = Field(default=5, ge=1, le=100000)


class MpesaCheckoutRequest(BaseModel):
    plan_code: str = Field(min_length=2, max_length=80)
    phone_number: str = Field(min_length=9, max_length=16)


class UserContext(BaseModel):
    user_id: str
    tenant_id: str
    email: str
    role: str
    groups: list[str] = Field(default_factory=list)


def create_access_token(user: User) -> str:
    now = utc_now()
    claims = {
        "sub": user.id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "role": user.role,
        "groups": user.groups or [],
        "iss": JWT_ISSUER,
        "aud": [JWT_AUDIENCE, "enterprise-platform-mcp"],
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "scope": "api:read api:write mcp:use",
    }
    return jwt.encode(claims, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "sub", "tenant_id", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Access token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserContext:
    claims = decode_access_token(token)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                User.id == claims["sub"],
                User.tenant_id == claims["tenant_id"],
                User.is_active.is_(True),
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User is inactive or no longer exists")
        tenant_result = await session.execute(
            select(Tenant).where(Tenant.id == user.tenant_id, Tenant.is_active.is_(True))
        )
        if not tenant_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Organization is inactive")
        return UserContext(
            user_id=user.id, tenant_id=user.tenant_id, email=user.email,
            role=user.role, groups=user.groups or [],
        )


def require_roles(*roles: str):
    async def role_dependency(user: UserContext = Depends(get_current_user)) -> UserContext:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission for this operation")
        return user
    return role_dependency


# ============================================================================
# PART 4/10 — TAMPER-EVIDENT AUDIT LOG, BOOTSTRAP, LOGIN AND INVITATIONS
# ============================================================================


async def create_audit_log(
    tenant_id: str,
    user_id: Optional[str],
    action: str,
    resource: Optional[str],
    metadata: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Write a tenant-scoped HMAC-linked audit record; audit failures are logged."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Serialize each tenant's chain updates on PostgreSQL.
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtext(:tenant_id))"),
                    {"tenant_id": tenant_id},
                )
                previous_result = await session.execute(
                    select(AuditLog.signature)
                    .where(AuditLog.tenant_id == tenant_id)
                    .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
                    .limit(1)
                )
                previous_signature = previous_result.scalar_one_or_none()
                timestamp = utc_now()
                log_id = new_id()
                safe_metadata = metadata or {}
                canonical = json.dumps(
                    {
                        "id": log_id,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "action": action,
                        "resource": resource,
                        "metadata": safe_metadata,
                        "ip_address": ip_address,
                        "timestamp": timestamp.isoformat(),
                        "previous_signature": previous_signature,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                ).encode("utf-8")
                signature = hmac.new(
                    AUDIT_SIGNING_KEY.encode("utf-8"), canonical, hashlib.sha256
                ).hexdigest()
                session.add(AuditLog(
                    id=log_id, tenant_id=tenant_id, user_id=user_id,
                    action=action[:100], resource=resource, metadata_json=safe_metadata,
                    ip_address=ip_address, previous_signature=previous_signature,
                    signature=signature, timestamp=timestamp,
                ))
    except Exception as exc:
        logger.exception("Could not persist audit event action=%s", action)
        raise RuntimeError("Audit logging failed; the operation could not be fully recorded") from exc


async def verify_audit_signature(log: AuditLog) -> bool:
    canonical = json.dumps(
        {
            "id": log.id,
            "tenant_id": log.tenant_id,
            "user_id": log.user_id,
            "action": log.action,
            "resource": log.resource,
            "metadata": log.metadata_json or {},
            "ip_address": log.ip_address,
            "timestamp": log.timestamp.isoformat(),
            "previous_signature": log.previous_signature,
        }, sort_keys=True, separators=(",", ":"), default=str,
    ).encode("utf-8")
    expected = hmac.new(AUDIT_SIGNING_KEY.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, log.signature)


async def bootstrap_first_tenant(session: AsyncSession) -> None:
    """Create the first tenant/admin only when explicit Render bootstrap vars exist."""
    email = env_value("BOOTSTRAP_ADMIN_EMAIL")
    password = env_value("BOOTSTRAP_ADMIN_PASSWORD")
    tenant_name = env_value("BOOTSTRAP_TENANT_NAME")
    if not (email and password and tenant_name):
        return
    if len(password) < 12:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters")
    existing = await session.execute(select(User.id).limit(1))
    if existing.scalar_one_or_none():
        return
    slug = re.sub(r"[^a-z0-9]+", "-", tenant_name.lower()).strip("-")[:100]
    tenant_result = await session.execute(select(Tenant).where(Tenant.slug == slug))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(name=tenant_name, slug=slug)
        session.add(tenant)
        await session.flush()
    admin = User(
        tenant_id=tenant.id, email=email.lower(), full_name="Platform Owner",
        password_hash=password_hasher.hash(password), role="superadmin",
        groups=["tenant:all"], is_active=True, email_verified=True,
    )
    session.add(admin)
    await session.flush()


# ----------------------------------------------------------------------------
# Token encryption for Google refresh tokens (Fernet key derived from JWT key).
# ----------------------------------------------------------------------------
from cryptography.fernet import Fernet, InvalidToken
FERNET_KEY = base64.urlsafe_b64encode(
    hashlib.sha256(JWT_SECRET_KEY.encode("utf-8") + b"enterprise-connector-token-v1").digest()
)
token_cipher = Fernet(FERNET_KEY)


# ============================================================================
 # PART 5/10 — AUTH API, INVITATION-ONLY ONBOARDING AND DOCUMENT INGESTION
# ============================================================================


@app.post("/api/v1/auth/login", tags=["Authentication"])
async def login_with_work_email(payload: LoginRequest, request: Request):
    email = str(payload.email).lower()
    async with AsyncSessionLocal() as session:
        query = (
            select(User)
            .join(Tenant, Tenant.id == User.tenant_id)
            .where(User.email == email, User.is_active.is_(True), Tenant.is_active.is_(True))
        )
        if payload.tenant_slug:
            query = query.where(Tenant.slug == payload.tenant_slug.lower())
        result = await session.execute(query.limit(3))
        candidates = result.scalars().all()
        if len(candidates) == 0:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if len(candidates) > 1:
            raise HTTPException(status_code=400, detail="This email belongs to multiple organizations; provide tenant_slug")
        user = candidates[0]
        if not user.password_hash or not password_hasher.verify(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = create_access_token(user)
        user_id, tenant_id, role = user.id, user.tenant_id, user.role
    await create_audit_log(
        tenant_id, user_id, "USER_LOGIN", "AUTH_SERVICE",
        {"method": "password"}, request.client.host if request.client else None,
    )
    return {
        "access_token": token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {"id": user_id, "email": email, "tenant_id": tenant_id, "role": role},
    }


@app.post("/api/v1/auth/google", tags=["Authentication"])
async def login_with_google(payload: GoogleLoginRequest, request: Request):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured: set Client_Id in Render")
    try:
        identity = google_id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception as exc:
        logger.warning("Google ID token verification failed: %s", type(exc).__name__)
        raise HTTPException(status_code=401, detail="Google identity token is invalid") from exc
    email = str(identity.get("email", "")).lower()
    subject = identity.get("sub")
    if not email or not subject or not identity.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account email is not verified")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                or_(User.google_subject == subject, User.email == email),
                User.is_active.is_(True),
            ).limit(3)
        )
        candidates = result.scalars().all()
        if not candidates:
            raise HTTPException(status_code=403, detail="Your organization must invite you before you can sign in")
        if len(candidates) > 1:
            raise HTTPException(status_code=409, detail="This Google email is registered in more than one organization; ask the platform owner to link the correct account")
        user = candidates[0]
        tenant_result = await session.execute(
            select(Tenant).where(Tenant.id == user.tenant_id, Tenant.is_active.is_(True))
        )
        if not tenant_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Organization is inactive")
        if user.google_subject and user.google_subject != subject:
            raise HTTPException(status_code=403, detail="Google identity does not match the linked account")
        if not user.google_subject:
            user.google_subject = subject
            user.email_verified = True
            user.full_name = user.full_name or str(identity.get("name", ""))
            await session.commit()
        token = create_access_token(user)
        user_id, tenant_id, role = user.id, user.tenant_id, user.role

    await create_audit_log(
        tenant_id, user_id, "USER_LOGIN_GOOGLE", "AUTH_SERVICE",
        {"method": "google_id_token"}, request.client.host if request.client else None,
    )
    return {
        "access_token": token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {"id": user_id, "email": email, "tenant_id": tenant_id, "role": role},
    }


@app.post("/api/v1/organizations/invitations", tags=["Organization Management"])
async def create_invitation(
    payload: InviteRequest,
    request: Request,
    user: UserContext = Depends(require_roles("admin", "superadmin")),
):
    if payload.role == "admin" and user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Only a superadmin can invite another admin")
    raw_token = secrets.token_urlsafe(36)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    async with AsyncSessionLocal() as session:
        tenant_user = await session.execute(
            select(User).where(User.tenant_id == user.tenant_id, User.email == str(payload.email).lower())
        )
        if tenant_user.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="A user with this email already exists in the organization")
        invite = Invitation(
            tenant_id=user.tenant_id, email=str(payload.email).lower(), role=payload.role,
            token_hash=token_hash, invited_by=user.user_id,
            expires_at=utc_now() + timedelta(days=7),
        )
        session.add(invite)
        await session.commit()
        invitation_id = invite.id
    await create_audit_log(
        user.tenant_id, user.user_id, "INVITATION_CREATED", invitation_id,
        {"email": str(payload.email).lower(), "role": payload.role},
        request.client.host if request.client else None,
    )
    # The token is returned once so the admin can deliver it through their
    # trusted channel. The backend never sends invitations to an invented email.
    return {"invitation_id": invitation_id, "invitation_token": raw_token, "expires_in_hours": 168}


@app.post("/api/v1/auth/accept-invitation", tags=["Authentication"])
async def accept_invitation(payload: AcceptInvitationRequest, request: Request):
    if len(payload.password) < 12:
        raise HTTPException(status_code=422, detail="Password must contain at least 12 characters")
    token_hash = hashlib.sha256(payload.invitation_token.encode()).hexdigest()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Invitation).where(
                    Invitation.token_hash == token_hash,
                    Invitation.accepted_at.is_(None),
                    Invitation.expires_at > utc_now(),
                ).with_for_update()
            )
            invite = result.scalar_one_or_none()
            if not invite:
                raise HTTPException(status_code=400, detail="Invitation is invalid, expired or already used")
            existing = await session.execute(
                select(User.id).where(User.tenant_id == invite.tenant_id, User.email == invite.email)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="This account already exists")
            user = User(
                tenant_id=invite.tenant_id, email=invite.email,
                full_name=payload.full_name.strip(),
                password_hash=password_hasher.hash(payload.password),
                role=invite.role, groups=[], is_active=True, email_verified=True,
            )
            session.add(user)
            invite.accepted_at = utc_now()
            await session.flush()
            user_id, tenant_id = user.id, user.tenant_id
            token = create_access_token(user)
    await create_audit_log(tenant_id, user_id, "INVITATION_ACCEPTED", "USER", {"email": invite.email})
    return {"access_token": token, "token_type": "bearer", "user_id": user_id, "tenant_id": tenant_id}


@app.get("/api/v1/auth/me", tags=["Authentication"])
async def current_user_profile(user: UserContext = Depends(get_current_user)):
    return user.model_dump()


@app.patch("/api/v1/organizations/users/{target_user_id}/groups", tags=["Organization Management"])
async def update_user_groups(
    target_user_id: str, payload: UpdateUserGroupsRequest, request: Request,
    admin: UserContext = Depends(require_roles("admin", "superadmin")),
):
    normalized = sorted({group.strip().lower() for group in payload.groups if group.strip()})
    if any(len(group) > 255 for group in normalized):
        raise HTTPException(status_code=422, detail="Group names must be 255 characters or fewer")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == target_user_id, User.tenant_id == admin.tenant_id)
        )
        target = result.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail="User not found in this organization")
        if target.role == "superadmin" and admin.role != "superadmin":
            raise HTTPException(status_code=403, detail="Only a superadmin can change a superadmin account")
        target.groups = normalized
        await session.commit()
    await create_audit_log(
        admin.tenant_id, admin.user_id, "USER_GROUPS_UPDATED", target_user_id,
        {"groups": normalized}, request.client.host if request.client else None,
    )
    return {"user_id": target_user_id, "groups": normalized}


def extract_file_text(filename: str, raw: bytes) -> str:
    extension = os.path.splitext(filename.lower())[1]
    if extension == ".pdf":
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if extension == ".docx":
        document = WordDocument(io.BytesIO(raw))
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        table_text = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
        return "\n".join(paragraphs + table_text).strip()
    if extension in {".txt", ".md", ".csv", ".json", ".html", ".xml"}:
        return raw.decode("utf-8-sig", errors="replace").strip()
    raise HTTPException(status_code=415, detail="Supported formats: PDF, DOCX, TXT, MD, CSV, JSON, HTML and XML")


def can_read_document(document: DocumentRecord, user: UserContext) -> bool:
    if user.user_id in (document.acl_user_ids or []):
        return True
    if user.email.lower() in [item.lower() for item in (document.acl_emails or [])]:
        return True
    allowed_groups = set(document.acl_groups or [])
    user_groups = {str(group).lower() for group in (user.groups or [])}
    allowed_emails = {str(email).lower() for email in (document.acl_emails or [])}
    return (
        "tenant:all" in allowed_groups
        or bool(allowed_groups.intersection(user_groups))
        or bool(allowed_emails.intersection(user_groups))
    )


@app.post("/api/v1/documents/upload", tags=["Knowledge Ingestion"])
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    workspace_id: Optional[str] = Form(default=None),
    visibility: Literal["private", "tenant"] = Form(default="private"),
    user: UserContext = Depends(get_current_user),
):
    max_bytes = int(env_value("MAX_UPLOAD_BYTES", default=str(25 * 1024 * 1024)))
    raw = await file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {max_bytes // (1024 * 1024)} MB limit")
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    safe_filename = os.path.basename(file.filename or "uploaded-file")
    content = extract_file_text(safe_filename, raw)
    if not content:
        raise HTTPException(status_code=422, detail="No searchable text could be extracted from this file")
    content_hash = hashlib.sha256(raw).hexdigest()
    document_id = new_id()
    acl_groups = ["tenant:all"] if visibility == "tenant" and user.role in {"admin", "superadmin"} else []
    if visibility == "tenant" and not acl_groups:
        raise HTTPException(status_code=403, detail="Only organization admins can share a document with the whole tenant")
    async with AsyncSessionLocal() as session:
        duplicate_result = await session.execute(
            select(DocumentRecord).where(
                DocumentRecord.tenant_id == user.tenant_id,
                DocumentRecord.source_app == "upload",
                DocumentRecord.content_hash == content_hash,
            ).limit(1)
        )
        duplicate = duplicate_result.scalar_one_or_none()
        if duplicate:
            return {"status": "already_indexed", "document_id": duplicate.id, "content_hash": content_hash}
        record = DocumentRecord(
            id=document_id, tenant_id=user.tenant_id, workspace_id=workspace_id,
            title=(title or safe_filename)[:500], filename=safe_filename,
            content=content, content_hash=content_hash, source_app="upload",
            acl_user_ids=[user.user_id], acl_emails=[], acl_groups=acl_groups,
            uploaded_by=user.user_id, status="indexed",
            metadata_json={"content_type": file.content_type, "size_bytes": len(raw)},
        )
        session.add(record)
        await session.commit()
    embedding_status = (
        "indexed" if NVIDIA_API_KEY and ALLOW_EXTERNAL_AI_PROCESSING
        else "disabled_by_policy" if NVIDIA_API_KEY and not ALLOW_EXTERNAL_AI_PROCESSING
        else "not_configured"
    )
    if NVIDIA_API_KEY and ALLOW_EXTERNAL_AI_PROCESSING:
        try:
            await index_document_embeddings(user.tenant_id, document_id, content)
        except Exception:
            logger.exception("Embedding indexing failed for document %s", document_id)
            embedding_status = "failed"
    graph_status = "queued"
    try:
        await index_document_graph(user.tenant_id, document_id, record.title, content)
        graph_status = "indexed"
    except Exception:
        logger.exception("Graph indexing failed for document %s", document_id)
        graph_status = "failed"
    await create_audit_log(
        user.tenant_id, user.user_id, "DOCUMENT_UPLOADED", document_id,
        {"filename": safe_filename, "size_bytes": len(raw), "graph_status": graph_status},
        request.client.host if request.client else None,
    )
    return {"status": "indexed", "document_id": document_id, "embedding_status": embedding_status, "graph_status": graph_status}


@app.get("/api/v1/documents/{document_id}", tags=["Knowledge Ingestion"])
async def get_document(document_id: str, user: UserContext = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DocumentRecord).where(
                DocumentRecord.id == document_id,
                DocumentRecord.tenant_id == user.tenant_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document or not can_read_document(document, user):
            raise HTTPException(status_code=404, detail="Document not found")
        data = {
            "id": document.id, "title": document.title, "filename": document.filename,
            "source_app": document.source_app, "source_url": document.source_url,
            "content": document.content, "created_at": document.created_at.isoformat(),
        }
    await create_audit_log(user.tenant_id, user.user_id, "DOCUMENT_READ", document_id)
    return data


# ============================================================================
                            
