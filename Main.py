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

