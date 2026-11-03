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
# =========================
# PART 4: AUDIT LOGS & TEAM
# =========================

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import hashlib
import secrets


class InviteInput(BaseModel):
    email: EmailStr
    role: str = "member"


class AcceptInviteInput(BaseModel):
    token: str
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12)


async def write_audit(
    db: AsyncSession,
    tenant_id: str,
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    event = AuditEvent(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.commit()
    return event


@app.post("/api/v1/team/invitations")
async def create_invitation(
    payload: InviteInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    if payload.role not in {"member", "viewer"}:
        raise HTTPException(400, "Role must be member or viewer.")

    existing = await db.execute(
        select(User).where(
            User.tenant_id == user.tenant_id,
            User.email == payload.email.lower(),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "This user is already in your organization.")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    invitation = Invitation(
        id=str(uuid.uuid4()),
        tenant_id=user.tenant_id,
        email=payload.email.lower(),
        role=payload.role,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_at=datetime.now(timezone.utc),
    )
    db.add(invitation)
    await db.commit()

    await write_audit(
        db, user.tenant_id, user.id,
        "team.invitation_created", "invitation", invitation.id,
        {"email": payload.email.lower(), "role": payload.role},
        request.client.host if request.client else None,
    )

    # Deliver this token through a verified email service before production.
    return {
        "invitation_id": invitation.id,
        "email": invitation.email,
        "expires_at": invitation.expires_at,
        "invitation_token": raw_token,
        "delivery_status": "token_created_email_delivery_not_configured",
    }


@app.post("/api/v1/team/invitations/accept")
async def accept_invitation(
    payload: AcceptInviteInput,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()

    result = await db.execute(
        select(Invitation).where(Invitation.token_hash == token_hash)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(404, "Invitation is invalid.")

    now = datetime.now(timezone.utc)
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if invitation.accepted_at is not None or expires_at < now:
        raise HTTPException(400, "Invitation has expired or was already used.")

    existing = await db.execute(
        select(User).where(
            User.tenant_id == invitation.tenant_id,
            User.email == invitation.email,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "User already exists in this organization.")

    new_user = User(
        id=str(uuid.uuid4()),
        tenant_id=invitation.tenant_id,
        email=invitation.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=invitation.role,
        is_active=True,
        created_at=now,
    )
    invitation.accepted_at = now
    db.add(new_user)
    await db.commit()

    await write_audit(
        db, invitation.tenant_id, new_user.id,
        "team.invitation_accepted", "user", new_user.id,
        {"email": new_user.email},
    )

    return {"message": "Invitation accepted.", "user_id": new_user.id}


@app.get("/api/v1/team")
async def list_team(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(
        select(User)
        .where(User.tenant_id == user.tenant_id)
        .order_by(User.created_at.desc())
    )
    members = result.scalars().all()

    return [
        {
            "id": member.id,
            "email": member.email,
            "full_name": member.full_name,
            "role": member.role,
            "is_active": member.is_active,
            "created_at": member.created_at,
        }
        for member in members
    ]


@app.get("/api/v1/audit")
async def get_audit_events(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    limit = max(1, min(limit, 500))

    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.tenant_id == user.tenant_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )

    return [
        {
            "id": event.id,
            "user_id": event.user_id,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "details": event.details,
            "ip_address": event.ip_address,
            "created_at": event.created_at,
        }
        for event in result.scalars().all()
    ]# =========================
# PART 5: DOCUMENT INGESTION
# =========================

import hashlib
from pathlib import Path


def extract_document_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".txt":
        return content.decode("utf-8", errors="replace")

    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix == ".docx":
        document = DocxDocument(io.BytesIO(content))
        return "\n".join(p.text for p in document.paragraphs if p.text.strip())

    raise HTTPException(
        415,
        "Unsupported file type. Upload PDF, DOCX, or TXT.",
    )


def split_text(text_value: str, chunk_size: int = 1200, overlap: int = 150):
    text_value = re.sub(r"\s+", " ", text_value).strip()
    if not text_value:
        return []

    chunks = []
    start = 0

    while start < len(text_value):
        end = min(start + chunk_size, len(text_value))
        chunks.append(text_value[start:end])

        if end == len(text_value):
            break

        start = max(0, end - overlap)

    return chunks


async def index_document_in_graph(
    document_id: str,
    tenant_id: str,
    filename: str,
    chunks: list[str],
):
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            """
            MERGE (d:Document {id: $document_id, tenant_id: $tenant_id})
            SET d.filename = $filename,
                d.created_at = datetime()
            """,
            document_id=document_id,
            tenant_id=tenant_id,
            filename=filename,
        )

        for index, chunk in enumerate(chunks):
            chunk_id = f"{document_id}:{index}"

            await session.run(
                """
                MATCH (d:Document {id: $document_id, tenant_id: $tenant_id})
                MERGE (c:DocumentChunk {
                    id: $chunk_id,
                    tenant_id: $tenant_id
                })
                SET c.text = $chunk_text,
                    c.chunk_index = $chunk_index
                MERGE (d)-[:HAS_CHUNK]->(c)
                """,
                document_id=document_id,
                tenant_id=tenant_id,
                chunk_id=chunk_id,
                chunk_text=chunk,
                chunk_index=index,
            )


@app.post("/api/v1/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = await file.read(MAX_UPLOAD_BYTES + 1)

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File exceeds the upload size limit.")

    filename = Path(file.filename or "uploaded.txt").name
    extracted_text = extract_document_text(filename, content)

    if not extracted_text.strip():
        raise HTTPException(422, "No readable text was extracted.")

    document_id = str(uuid.uuid4())
    text_hash = hashlib.sha256(extracted_text.encode("utf-8")).hexdigest()
    chunks = split_text(extracted_text)

    document = Document(
        id=document_id,
        tenant_id=user.tenant_id,
        uploaded_by=user.id,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        source="upload",
        extracted_text=extracted_text,
        text_hash=text_hash,
        acl_groups=[],
        created_at=datetime.now(timezone.utc),
    )

    db.add(document)
    await db.commit()

    try:
        await index_document_in_graph(
            document_id,
            user.tenant_id,
            filename,
            chunks,
        )
    except Exception:
        await db.delete(document)
        await db.commit()
        logging.exception("Neo4j indexing failed for document %s", document_id)
        raise HTTPException(503, "Document indexing failed. Please retry.")

    await write_audit(
        db, user.tenant_id, user.id,
        "document.uploaded", "document", document_id,
        {"filename": filename, "chunk_count": len(chunks)},
        request.client.host if request.client else None,
    )

    return {
        "document_id": document_id,
        "filename": filename,
        "characters_extracted": len(extracted_text),
        "chunks_indexed": len(chunks),
        "status": "indexed",
    }


@app.get("/api/v1/documents")
async def list_documents(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    limit = max(1, min(limit, 500))

    result = await db.execute(
        select(Document)
        .where(Document.tenant_id == user.tenant_id)
        .order_by(Document.created_at.desc())
        .limit(limit)
    )

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "source": doc.source,
            "created_at": doc.created_at,
        }
        for doc in result.scalars().all()
    ]


@app.get("/api/v1/documents/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(404, "Document not found.")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "source": doc.source,
        "text": doc.extracted_text,
        "created_at": doc.created_at,
    }# =========================
# PART 6: SEARCH & GRAPH
# =========================

class SearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=20, ge=1, le=100)


@app.post("/api/v1/search")
async def search_documents(
    payload: SearchInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    terms = [term.strip() for term in payload.query.split() if term.strip()]
    conditions = [
        Document.extracted_text.ilike(f"%{term}%")
        for term in terms
    ]

    result = await db.execute(
        select(Document)
        .where(
            Document.tenant_id == user.tenant_id,
            *conditions,
        )
        .order_by(Document.created_at.desc())
        .limit(payload.limit)
    )

    documents = result.scalars().all()

    await write_audit(
        db, user.tenant_id, user.id,
        "search.executed", "document", None,
        {"query": payload.query, "result_count": len(documents)},
        request.client.host if request.client else None,
    )

    return {
        "query": payload.query,
        "count": len(documents),
        "results": [
            {
                "document_id": doc.id,
                "filename": doc.filename,
                "source": doc.source,
                "snippet": (
                    doc.extracted_text[:500]
                    if doc.extracted_text else ""
                ),
                "created_at": doc.created_at,
            }
            for doc in documents
        ],
        "search_method": "tenant_scoped_keyword_search",
    }


@app.get("/api/v1/graph/documents")
async def graph_documents(
    user: User = Depends(get_current_user),
):
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(
            """
            MATCH (d:Document {tenant_id: $tenant_id})
            OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:DocumentChunk {
                tenant_id: $tenant_id
            })
            RETURN d.id AS id,
                   d.filename AS filename,
                   count(c) AS chunk_count
            ORDER BY filename
            """,
            tenant_id=user.tenant_id,
        )
        records = await result.data()

    return {"nodes": records}


@app.get("/api/v1/graph/explore/{document_id}")
async def explore_document_graph(
    document_id: str,
    depth: int = 1,
    user: User = Depends(get_current_user),
):
    # Limit traversal to document/chunk nodes in this tenant.
    depth = max(1, min(depth, 2))

    cypher = f"""
    MATCH (d:Document {{
        id: $document_id,
        tenant_id: $tenant_id
    }})
    OPTIONAL MATCH path =
        (d)-[:HAS_CHUNK*1..{depth}]-(related)
    WHERE all(
        node IN nodes(path)
        WHERE node.tenant_id = $tenant_id
    )
    RETURN d.id AS document_id,
           d.filename AS filename,
           collect(DISTINCT {{
               id: related.id,
               labels: labels(related),
               filename: related.filename,
               chunk_index: related.chunk_index
           }}) AS related_nodes
    """

    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(
            cypher,
            document_id=document_id,
            tenant_id=user.tenant_id,
        )
        record = await result.single()

    if not record:
        raise HTTPException(404, "Document not found in this workspace.")

    related_nodes = [
        node for node in record["related_nodes"]
        if node.get("id") is not None
    ]

    return {
        "document_id": record["document_id"],
        "filename": record["filename"],
        "related_nodes": related_nodes,
    }# =========================
# PART 7: GLOBAL PRICING
# =========================

SUPPORTED_CURRENCIES = {
    "USD", "EUR", "GBP", "KES", "CAD", "AUD", "CHF", "AED", "SGD"
}

ENTERPRISE_PLANS = {
    "growth": {
        "name": "Enterprise GraphRAG Growth",
        "monthly_price": 2000,
        "annual_price": 21600,
        "implementation_fee": 3500,
        "included_users": 25,
        "included_documents": 25000,
        "support": "Business-hours support",
        "deployment": "Managed cloud",
    },
    "business": {
        "name": "Enterprise GraphRAG Business",
        "monthly_price": 5000,
        "annual_price": 54000,
        "implementation_fee": 10000,
        "included_users": 100,
        "included_documents": 100000,
        "support": "Priority support",
        "deployment": "Managed cloud or agreed private environment",
    },
    "enterprise": {
        "name": "Enterprise GraphRAG Enterprise",
        "monthly_price": 10000,
        "annual_price": 108000,
        "implementation_fee": 25000,
        "included_users": 250,
        "included_documents": 500000,
        "support": "Dedicated enterprise support",
        "deployment": "Custom enterprise deployment",
    },
}


class SubscriptionRequest(BaseModel):
    plan: str
    billing_period: str = "monthly"
    currency: str = "USD"


@app.get("/api/v1/pricing")
async def get_pricing():
    return {
        "reference_currency": "USD",
        "plans": ENTERPRISE_PLANS,
        "note": (
            "Prices are proposed reference prices. Final quotations, "
            "taxes and contract currency are agreed with each customer."
        ),
    }


@app.post("/api/v1/subscriptions/request")
async def request_subscription(
    payload: SubscriptionRequest,
    user: User = Depends(require_admin),
):
    plan = payload.plan.lower()
    currency = payload.currency.upper()

    if plan not in ENTERPRISE_PLANS:
        raise HTTPException(400, "Unknown subscription plan.")

    if payload.billing_period not in {"monthly", "annual"}:
        raise HTTPException(400, "Billing period must be monthly or annual.")

    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(400, "Unsupported quotation currency.")

    details = ENTERPRISE_PLANS[plan]
    amount = (
        details["monthly_price"]
        if payload.billing_period == "monthly"
        else details["annual_price"]
    )

    return {
        "tenant_id": user.tenant_id,
        "plan": plan,
        "billing_period": payload.billing_period,
        "reference_amount": amount,
        "reference_currency": "USD",
        "requested_quote_currency": currency,
        "requires_final_quote": currency != "USD",
        "implementation_fee": details["implementation_fee"],
        "message": "Subscription request prepared; payment is not yet taken.",
    }


@app.get("/api/v1/subscriptions/current")
async def current_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.tenant_id == user.tenant_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return {"subscription": None}

    return {
        "id": subscription.id,
        "plan": subscription.plan,
        "status": subscription.status,
        "starts_at": subscription.starts_at,
        "ends_at": subscription.ends_at,
    }# =========================
# PART 8: PAYMENT RECORDS
# =========================

class PaymentRequest(BaseModel):
    plan: str
    billing_period: str = "monthly"
    include_implementation: bool = False


class PaymentVerificationInput(BaseModel):
    verified_amount: int = Field(gt=0)
    verification_note: str = Field(min_length=5, max_length=1000)


@app.post("/api/v1/payments/request")
async def create_payment_request(
    payload: PaymentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    plan = payload.plan.lower()

    if plan not in ENTERPRISE_PLANS:
        raise HTTPException(400, "Unknown plan.")

    if payload.billing_period not in {"monthly", "annual"}:
        raise HTTPException(400, "Invalid billing period.")

    plan_details = ENTERPRISE_PLANS[plan]

    amount = (
        plan_details["monthly_price"]
        if payload.billing_period == "monthly"
        else plan_details["annual_price"]
    )

    if payload.include_implementation:
        amount += plan_details["implementation_fee"]

    payment = Payment(
        id=str(uuid.uuid4()),
        tenant_id=user.tenant_id,
        provider="manual_pending",
        provider_reference=str(uuid.uuid4()),
        amount=amount,
        currency="USD",
        status="pending",
        created_at=datetime.now(timezone.utc),
    )

    db.add(payment)
    await db.commit()

    await write_audit(
        db,
        user.tenant_id,
        user.id,
        "payment.requested",
        "payment",
        payment.id,
        {
            "plan": plan,
            "billing_period": payload.billing_period,
            "include_implementation": payload.include_implementation,
            "amount": amount,
            "currency": "USD",
        },
    )

    return {
        "payment_id": payment.id,
        "reference": payment.provider_reference,
        "amount": amount,
        "currency": "USD",
        "status": "pending",
        "message": "Payment request created. No payment has been processed.",
    }


@app.get("/api/v1/payments")
async def list_payments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Payment)
        .where(Payment.tenant_id == user.tenant_id)
        .order_by(Payment.created_at.desc())
    )

    return [
        {
            "id": payment.id,
            "provider": payment.provider,
            "reference": payment.provider_reference,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "created_at": payment.created_at,
        }
        for payment in result.scalars().all()
    ]


@app.post("/api/v1/admin/payments/{payment_id}/verify")
async def verify_payment_manually(
    payment_id: str,
    payload: PaymentVerificationInput,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.tenant_id == user.tenant_id,
        )
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(404, "Payment not found.")

    if payment.status != "pending":
        raise HTTPException(409, "Payment is not pending.")

    if payment.amount != payload.verified_amount:
        raise HTTPException(400, "Verified amount does not match the invoice.")

    audit_result = await db.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == user.tenant_id,
            AuditEvent.resource_type == "payment",
            AuditEvent.resource_id == payment.id,
            AuditEvent.action == "payment.requested",
        ).order_by(AuditEvent.created_at.desc()).limit(1)
    )
    audit_event = audit_result.scalar_one_or_none()

    if not audit_event:
        raise HTTPException(400, "Payment request details were not found.")

    details = audit_event.details or {}
    plan = details.get("plan")
    billing_period = details.get("billing_period")

    if plan not in ENTERPRISE_PLANS or billing_period not in {"monthly", "annual"}:
        raise HTTPException(400, "Invalid subscription details.")

    now = datetime.now(timezone.utc)
    duration_days = 365 if billing_period == "annual" else 30

    payment.status = "confirmed"

    subscription_result = await db.execute(
        select(Subscription)
        .where(Subscription.tenant_id == user.tenant_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = subscription_result.scalar_one_or_none()

    if subscription:
        subscription.plan = plan
        subscription.status = "active"
        subscription.starts_at = now
        subscription.ends_at = now + timedelta(days=duration_days)
    else:
        subscription = Subscription(
            id=str(uuid.uuid4()),
            tenant_id=user.tenant_id,
            plan=plan,
            status="active",
            starts_at=now,
            ends_at=now + timedelta(days=duration_days),
            created_at=now,
        )
        db.add(subscription)

    await db.commit()

    await write_audit(
        db,
        user.tenant_id,
        user.id,
        "payment.manually_verified",
        "payment",
        payment.id,
        {"verification_note": payload.verification_note},
    )

    return {
        "message": "Payment recorded and subscription activated.",
        "payment_id": payment.id,
        "subscription_plan": plan,
        "subscription_status": "active",
        "verification_method": "manual_admin_verification",
    }# =========================
# PART 9: CONNECTOR INGESTION
# =========================

class ConnectorDocumentInput(BaseModel):
    connector: str = Field(min_length=2, max_length=50)
    external_id: str = Field(min_length=1, max_length=500)
    filename: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


SUPPORTED_CONNECTORS = {
    "google_drive": "Google Drive",
    "sharepoint": "Microsoft SharePoint",
    "onedrive": "Microsoft OneDrive",
    "slack": "Slack",
    "notion": "Notion",
    "confluence": "Atlassian Confluence",
    "salesforce": "Salesforce",
    "hubspot": "HubSpot",
    "custom": "Custom connector",
}


@app.get("/api/v1/connectors")
async def list_connectors(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document.source)
        .where(Document.tenant_id == user.tenant_id)
        .distinct()
    )
    active_sources = set(result.scalars().all())

    return {
        "connectors": [
            {
                "id": connector_id,
                "name": connector_name,
                "status": (
                    "data_received"
                    if connector_id in active_sources
                    else "not_connected"
                ),
            }
            for connector_id, connector_name in SUPPORTED_CONNECTORS.items()
        ],
        "note": (
            "Provider OAuth, scheduled synchronization and webhook "
            "subscriptions must be configured separately."
        ),
    }


@app.post("/api/v1/connectors/ingest")
async def ingest_connector_document(
    payload: ConnectorDocumentInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    connector_id = payload.connector.lower()

    if connector_id not in SUPPORTED_CONNECTORS:
        raise HTTPException(400, "Unsupported connector.")

    content_hash = hashlib.sha256(
        payload.content.encode("utf-8")
    ).hexdigest()

    # Avoid ingesting the same content repeatedly.
    duplicate_result = await db.execute(
        select(Document).where(
            Document.tenant_id == user.tenant_id,
            Document.source == connector_id,
            Document.text_hash == content_hash,
        ).limit(1)
    )
    duplicate = duplicate_result.scalar_one_or_none()

    if duplicate:
        return {
            "status": "already_ingested",
            "document_id": duplicate.id,
            "filename": duplicate.filename,
        }

    document_id = str(uuid.uuid4())
    chunks = split_text(payload.content)

    document = Document(
        id=document_id,
        tenant_id=user.tenant_id,
        uploaded_by=user.id,
        filename=Path(payload.filename).name,
        content_type="text/plain",
        source=connector_id,
        extracted_text=payload.content,
        text_hash=content_hash,
        acl_groups=[],
        created_at=datetime.now(timezone.utc),
    )

    db.add(document)
    await db.commit()

    try:
        await index_document_in_graph(
            document_id=document_id,
            tenant_id=user.tenant_id,
            filename=document.filename,
            chunks=chunks,
        )
    except Exception:
        await db.delete(document)
        await db.commit()
        logging.exception("Connector indexing failed.")
        raise HTTPException(503, "Connector document indexing failed.")

    await write_audit(
        db,
        user.tenant_id,
        user.id,
        "connector.document_ingested",
        "document",
        document_id,
        {
            "connector": connector_id,
            "external_id": payload.external_id,
            "filename": document.filename,
            "chunk_count": len(chunks),
        },
        request.client.host if request.client else None,
    )

    return {
        "status": "ingested",
        "document_id": document_id,
        "connector": connector_id,
        "filename": document.filename,
        "chunks_indexed": len(chunks),
        }# =========================
# PART 10: DASHBOARD & STATUS
# =========================

@app.get("/api/v1/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.tenant_id == user.tenant_id
        )
    )

    user_result = await db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == user.tenant_id
        )
    )

    audit_result = await db.execute(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.tenant_id == user.tenant_id
        )
    )

    payment_result = await db.execute(
        select(func.count(Payment.id)).where(
            Payment.tenant_id == user.tenant_id,
            Payment.status == "confirmed",
        )
    )

    return {
        "tenant_id": user.tenant_id,
        "metrics": {
            "documents": document_result.scalar_one(),
            "team_members": user_result.scalar_one(),
            "audit_events": audit_result.scalar_one(),
            "confirmed_payments": payment_result.scalar_one(),
        },
        "generated_at": datetime.now(timezone.utc),
    }


@app.get("/api/v1/usage")
async def get_usage(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.tenant_id == user.tenant_id
        )
    )

    user_result = await db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == user.tenant_id
        )
    )

    subscription_result = await db.execute(
        select(Subscription)
        .where(Subscription.tenant_id == user.tenant_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = subscription_result.scalar_one_or_none()

    plan_name = subscription.plan if subscription else "unsubscribed"
    plan = ENTERPRISE_PLANS.get(plan_name)

    return {
        "plan": plan_name,
        "usage": {
            "documents": document_result.scalar_one(),
            "team_members": user_result.scalar_one(),
        },
        "allowances": (
            {
                "documents": plan["included_documents"],
                "team_members": plan["included_users"],
            }
            if plan else None
        ),
        "metering_status": {
            "ai_tokens": "not_metered",
            "embedding_storage": "not_metered",
            "graph_storage": "not_metered",
            "connector_api_calls": "not_metered",
        },
        "note": (
            "Do not charge usage overages until the corresponding "
            "metering and billing controls have been implemented."
        ),
    }


@app.get("/api/v1/platform")
async def platform_information():
    return {
        "name": "Enterprise GraphRAG",
        "description": (
            "Multi-tenant enterprise document ingestion, "
            "knowledge graph indexing and secure context retrieval."
        ),
        "api_version": "v1",
        "capabilities": {
            "authentication": "implemented",
            "tenant_scoped_documents": "implemented",
            "audit_events": "implemented",
            "document_upload": "implemented",
            "keyword_search": "implemented",
            "neo4j_document_graph": "implemented",
            "connector_content_ingestion": "implemented",
            "subscription_records": "implemented",
            "payment_records": "manual_verification_only",
            "provider_oauth_connectors": "not_implemented",
            "vector_search": "not_implemented",
            "llm_answer_generation": "not_implemented",
            "automated_payment_webhooks": "not_implemented",
            "full_fastmcp_server": "not_implemented",
        },
    }


@app.get("/api/v1/mcp/tools")
async def mcp_tool_manifest(
    user: User = Depends(get_current_user),
):
    return {
        "server_name": "EnterpriseKnowledgeHub",
        "status": "tool_manifest_only",
        "tools": [
            {
                "name": "search_enterprise_documents",
                "description": (
                    "Search documents belonging to the authenticated tenant."
                ),
                "endpoint": "POST /api/v1/search",
            },
            {
                "name": "list_enterprise_documents",
                "description": (
                    "List documents belonging to the authenticated tenant."
                ),
                "endpoint": "GET /api/v1/documents",
            },
            {
                "name": "explore_knowledge_graph",
                "description": (
                    "Explore the authenticated tenant's document graph."
                ),
                "endpoint": "GET /api/v1/graph/explore/{document_id}",
            },
        ],
        "security": (
            "The API authenticates the user and derives tenant scope "
            "from the authenticated account."
        ),
        "note": (
            "This endpoint describes available tools. It is not itself "
            "a running MCP protocol server."
        ),
    }


@app.get("/api/v1/system/status")
async def system_status(
    user: User = Depends(require_admin),
):
    status = {
        "api": "online",
        "postgresql": "unknown",
        "neo4j": "unknown",
    }

    try:
        async with engine.connect() as connection:
            await connection.execute(select(1))
        status["postgresql"] = "online"
    except Exception:
        logging.exception("PostgreSQL health check failed.")
        status["postgresql"] = "offline"

    try:
        await neo4j_driver.verify_connectivity()
        status["neo4j"] = "online"
    except Exception:
        logging.exception("Neo4j health check failed.")
        status["neo4j"] = "offline"

    overall = (
        "healthy"
        if status["postgresql"] == "online"
        and status["neo4j"] == "online"
        else "degraded"
    )

    return {
        "overall_status": overall,
        "services": status,
        "checked_at": datetime.now(timezone.utc),
    }
