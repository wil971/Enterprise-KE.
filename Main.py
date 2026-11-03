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
# ============================================================
# PART 2 - DATABASE MODELS
# ============================================================

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    role: Mapped[str] = mapped_column(
        String(30), default="employee"
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(30), default="employee")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(100))
    external_id: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    content: Mapped[str] = mapped_column(Text)
    acl_groups: Mapped[list] = mapped_column(
        JSON, default=lambda: ["tenant"]
    )
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(100))
    resource: Mapped[str] = mapped_column(String(500))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), unique=True
    )
    plan: Mapped[str] = mapped_column(String(40), default="trial")
    status: Mapped[str] = mapped_column(String(30), default="trial")
    provider: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    provider_reference: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    plan: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
# ============================================================
# PART 3 - SCHEMAS AND AUTHENTICATION
# ============================================================

class RegisterInput(BaseModel):
    organization: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class InviteInput(BaseModel):
    email: EmailStr
    role: str = "employee"


class AcceptInviteInput(BaseModel):
    token: str
    password: str = Field(min_length=12, max_length=200)


class SearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50)


def create_access_token(user: User) -> str:
    now = utc_now()
    return jwt.encode(
        {
            "sub": user.id,
            "tenant_id": user.tenant_id,
            "role": user.role,
            "iat": now,
            "exp": now + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            ),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


async def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security_scheme
    ),
) -> User:
    if credentials is None:
        raise HTTPException(401, "Authentication required")

    try:
        claims = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid or expired token")

    async with AsyncSessionLocal() as session:
        user = await session.get(User, claims.get("sub"))

        if (
            user is None
            or not user.active
            or user.tenant_id != claims.get("tenant_id")
        ):
            raise HTTPException(401, "Account is unavailable")

        return user


def admin_only(user: User):
    if user.role not in {"admin", "superadmin"}:
        raise HTTPException(403, "Administrator access required")


@app.post("/api/v1/auth/register")
async def register(data: RegisterInput):
    email = data.email.lower()
    slug = data.organization.lower().strip().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(User).where(User.email == email)
        )
        if existing:
            raise HTTPException(409, "Email already registered")

        organization = Organization(
            id=new_id("org"),
            name=data.organization,
            slug=f"{slug}-{uuid.uuid4().hex[:6]}",
        )
        session.add(organization)
        await session.flush()

        user = User(
            id=new_id("usr"),
            email=email,
            password_hash=hash_password(data.password),
            tenant_id=organization.id,
            role="admin",
        )
        session.add(user)

        session.add(Subscription(
            id=new_id("sub"),
            tenant_id=organization.id,
            plan="trial",
            status="trial",
            current_period_end=utc_now() + timedelta(days=14),
        ))

        await session.commit()

        return {
            "access_token": create_access_token(user),
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "tenant_id": user.tenant_id,
                "role": user.role,
            },
        }


@app.post("/api/v1/auth/login")
async def login(data: LoginInput):
    async with AsyncSessionLocal() as session:
        user = await session.scalar(
            select(User).where(
                User.email == data.email.lower()
            )
        )

        if (
            user is None
            or not user.active
            or not verify_password(
                data.password,
                user.password_hash,
            )
        ):
            raise HTTPException(401, "Incorrect email or password")

        return {
            "access_token": create_access_token(user),
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "tenant_id": user.tenant_id,
                "role": user.role,
            },
        }


@app.get("/api/v1/auth/me")
async def who_am_i(user: User = Depends(current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "role": user.role,
            }
    # ============================================================
# PART 4 - AUDIT LOGGING AND INVITATIONS
# ============================================================

async def write_audit(
    tenant_id: str,
    user_id: str,
    action: str,
    resource: str,
    details: dict | None = None,
):
    async with AsyncSessionLocal() as session:
        session.add(AuditEvent(
            id=new_id("audit"),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource=resource,
            details=details or {},
        ))
        await session.commit()


@app.post("/api/v1/team/invitations")
async def create_invitation(
    data: InviteInput,
    user: User = Depends(current_user),
):
    admin_only(user)

    if data.role not in {"employee", "admin"}:
        raise HTTPException(400, "Invalid invitation role")

    raw_token = secrets.token_urlsafe(40)
    token_hash = hashlib.sha256(
        raw_token.encode()
    ).hexdigest()

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(User).where(
                User.email == data.email.lower()
            )
        )
        if existing:
            raise HTTPException(409, "This email already has an account")

        invitation = Invitation(
            id=new_id("invite"),
            email=data.email.lower(),
            tenant_id=user.tenant_id,
            role=data.role,
            token_hash=token_hash,
            expires_at=utc_now() + timedelta(days=3),
        )

        session.add(invitation)
        await session.commit()

    await write_audit(
        user.tenant_id,
        user.id,
        "team.invitation.created",
        data.email.lower(),
        {"role": data.role},
    )

    return {
        "invitation_token": raw_token,
        "expires_at": invitation.expires_at.isoformat(),
        "message": "Send this invitation token securely to the invited employee.",
    }


@app.post("/api/v1/team/invitations/accept")
async def accept_invitation(data: AcceptInviteInput):
    token_hash = hashlib.sha256(
        data.token.encode()
    ).hexdigest()

    async with AsyncSessionLocal() as session:
        invitation = await session.scalar(
            select(Invitation).where(
                Invitation.token_hash == token_hash
            )
        )

        if (
            invitation is None
            or invitation.accepted_at is not None
            or invitation.expires_at <= utc_now()
        ):
            raise HTTPException(400, "Invitation is invalid or expired")

        existing = await session.scalar(
            select(User).where(
                User.email == invitation.email
            )
        )
        if existing:
            raise HTTPException(409, "Account already exists")

        employee = User(
            id=new_id("usr"),
            email=invitation.email,
            password_hash=hash_password(data.password),
            tenant_id=invitation.tenant_id,
            role=invitation.role,
        )

        invitation.accepted_at = utc_now()
        session.add(employee)
        await session.commit()

        await write_audit(
            employee.tenant_id,
            employee.id,
            "team.invitation.accepted",
            employee.email,
        )

        return {
            "message": "Invitation accepted",
            "access_token": create_access_token(employee),
            "token_type": "bearer",
        }


@app.get("/api/v1/team")
async def list_team(user: User = Depends(current_user)):
    admin_only(user)

    async with AsyncSessionLocal() as session:
        result = await session.scalars(
            select(User).where(
                User.tenant_id == user.tenant_id
            )
        )
        return [
            {
                "id": item.id,
                "email": item.email,
                "role": item.role,
                "active": item.active,
            }
            for item in result.all()
        ]


@app.get("/api/v1/audit")
async def list_audit(
    limit: int = 50,
    user: User = Depends(current_user),
):
    admin_only(user)
    limit = max(1, min(limit, 200))

    async with AsyncSessionLocal() as session:
        result = await session.scalars(
            select(AuditEvent)
            .where(AuditEvent.tenant_id == user.tenant_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )

        return [
            {
                "id": item.id,
                "user_id": item.user_id,
                "action": item.action,
                "resource": item.resource,
                "details": item.details,
                "created_at": item.created_at.isoformat(),
            }
            for item in result.all()
        ]
# ============================================================
# PART 5 - DOCUMENT INGESTION
# ============================================================

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def extract_document_text(
    filename: str,
    content: bytes,
) -> str:
    suffix = filename.lower().rsplit(".", 1)[-1]

    if suffix == "txt":
        return content.decode("utf-8", errors="replace")

    if suffix == "pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    if suffix == "docx":
        document = DocxDocument(io.BytesIO(content))
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    raise HTTPException(
        415,
        "Supported document formats: PDF, DOCX and TXT",
    )


def split_text(text: str, size: int = 1200):
    words = text.split()
    chunks = []

    current = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 > size and current:
            chunks.append(" ".join(current))
            current = []
            current_length = 0

        current.append(word)
        current_length += len(word) + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


async def index_document_in_graph(
    document: Document,
):
    async with neo4j_driver.session(
        database=NEO4J_DATABASE
    ) as session:
        await session.run(
            """
            MERGE (d:Document {
                id: $id,
                tenant_id: $tenant_id
            })
            SET d.title = $title,
                d.source = $source,
                d.url = $url,
                d.content = $content,
                d.acl_groups = $acl_groups,
                d.updated_at = $updated_at
            """,
            id=document.id,
            tenant_id=document.tenant_id,
            title=document.title,
            source=document.source,
            url=document.url or "",
            content=document.content,
            acl_groups=["tenant"],
            updated_at=utc_now().isoformat(),
        )


@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
):
    if user.role not in {"employee", "admin", "superadmin"}:
        raise HTTPException(403, "Document upload not permitted")

    filename = file.filename or "document"
    content = await file.read(MAX_UPLOAD_BYTES + 1)

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File exceeds the 25 MB upload limit")

    extracted = extract_document_text(filename, content)

    if not extracted.strip():
        raise HTTPException(422, "No readable text was found")

    document = Document(
        id=new_id("doc"),
        tenant_id=user.tenant_id,
        title=filename,
        source="upload",
        content=extracted,
        acl_groups=["tenant"],
        created_by=user.id,
    )

    async with AsyncSessionLocal() as session:
        session.add(document)
        await session.commit()

    try:
        await index_document_in_graph(document)
    except Exception:
        logger.exception("Neo4j document indexing failed")
        async with AsyncSessionLocal() as session:
            await session.delete(
                await session.get(Document, document.id)
            )
            await session.commit()
        raise HTTPException(
            503,
            "Document was not indexed. Please retry later."
        )

    await write_audit(
        user.tenant_id,
        user.id,
        "document.uploaded",
        document.id,
        {"filename": filename},
    )

    return {
        "id": document.id,
        "title": document.title,
        "status": "indexed",
        "chunks": len(split_text(extracted)),
    }


@app.get("/api/v1/documents")
async def list_documents(
    user: User = Depends(current_user),
):
    async with AsyncSessionLocal() as session:
        result = await session.scalars(
            select(Document)
            .where(Document.tenant_id == user.tenant_id)
            .order_by(Document.created_at.desc())
            .limit(100)
        )

        return [
            {
                "id": item.id,
                "title": item.title,
                "source": item.source,
                "created_at": item.created_at.isoformat(),
            }
            for item in result.all()
        ]
        # ============================================================
# PART 6 - ENTERPRISE SEARCH
# ============================================================

@app.post("/api/v1/search")
async def enterprise_search(
    data: SearchInput,
    user: User = Depends(current_user),
):
    offset = (data.page - 1) * data.page_size

    async with AsyncSessionLocal() as session:
        result = await session.scalars(
            select(Document)
            .where(
                Document.tenant_id == user.tenant_id,
                Document.content.ilike(f"%{data.query}%")
                | Document.title.ilike(f"%{data.query}%"),
            )
            .order_by(Document.updated_at.desc())
            .offset(offset)
            .limit(data.page_size)
        )

        documents = result.all()

    results = [
        {
            "id": item.id,
            "title": item.title,
            "source": item.source,
            "snippet": item.content[:500],
            "url": item.url,
            "created_at": item.created_at.isoformat(),
            "evidence": "PostgreSQL document record",
        }
        for item in documents
    ]

    await write_audit(
        user.tenant_id,
        user.id,
        "search.executed",
        "enterprise_search",
        {"query": data.query},
    )

    return {
        "query": data.query,
        "page": data.page,
        "page_size": data.page_size,
        "count": len(results),
        "results": results,
    }


@app.get("/api/v1/graph/document/{document_id}")
async def document_relationships(
    document_id: str,
    user: User = Depends(current_user),
):
    async with neo4j_driver.session(
        database=NEO4J_DATABASE
    ) as session:
        result = await session.run(
            """
            MATCH (d:Document {
                id: $document_id,
                tenant_id: $tenant_id
            })
            OPTIONAL MATCH (d)-[r]-(related)
            WHERE related.tenant_id = $tenant_id
            RETURN d {
                .id, .title, .source
            } AS document,
            collect({
                relationship: type(r),
                entity: properties(related),
                labels: labels(related)
            }) AS relationships
            """,
            document_id=document_id,
            tenant_id=user.tenant_id,
        )

        record = await result.single()

    if not record or not record["document"]:
        raise HTTPException(404, "Document not found")

    return {
        "document": record["document"],
        "relationships": [
            item
            for item in record["relationships"]
            if item["entity"] is not None
        ],
    }


@app.post("/api/v1/graph/entities")
async def create_graph_entity(
    name: str,
    entity_type: str,
    document_id: str,
    user: User = Depends(current_user),
):
    if len(name) > 300 or len(entity_type) > 80:
        raise HTTPException(400, "Entity information is too long")

    async with AsyncSessionLocal() as session:
        document = await session.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == user.tenant_id,
            )
        )

    if document is None:
        raise HTTPException(404, "Document not found")

    async with neo4j_driver.session(
        database=NEO4J_DATABASE
    ) as session:
        await session.run(
            """
            MATCH (d:Document {
                id: $document_id,
                tenant_id: $tenant_id
            })
            MERGE (e:Entity {
                tenant_id: $tenant_id,
                name: $name,
                entity_type: $entity_type
            })
            MERGE (d)-[:MENTIONS]->(e)
            """,
            document_id=document_id,
            tenant_id=user.tenant_id,
            name=name,
            entity_type=entity_type,
        )

    await write_audit(
        user.tenant_id,
        user.id,
        "graph.entity.created",
        name,
        {"type": entity_type, "document_id": document_id},
    )

    return {
        "status": "created",
        "entity": name,
        "type": entity_type,
    }


@app.get("/api/v1/graph/explore")
async def explore_graph(
    query: str,
    depth: int = 2,
    user: User = Depends(current_user),
):
    depth = max(1, min(depth, 4))

    cypher = f"""
    MATCH (start)
    WHERE start.tenant_id = $tenant_id
      AND (
        toLower(coalesce(start.name, '')) CONTAINS toLower($query)
        OR toLower(coalesce(start.title, '')) CONTAINS toLower($query)
      )
    MATCH path = (start)-[*1..{depth}]-(related)
    WHERE all(n IN nodes(path)
              WHERE n.tenant_id = $tenant_id)
    RETURN path
    LIMIT 100
    """

    async with neo4j_driver.session(
        database=NEO4J_DATABASE
    ) as session:
        result = await session.run(
            cypher,
            tenant_id=user.tenant_id,
            query=query,
        )

        records = await result.data()

    nodes = {}
    edges = []

    for record in records:
        path = record["path"]

        for node in path.nodes:
            node_id = node.element_id
            nodes[node_id] = {
                "id": node_id,
                "labels": list(node.labels),
                "properties": dict(node),
            }

        for relationship in path.relationships:
            edges.append({
                "source": relationship.start_node.element_id,
                "target": relationship.end_node.element_id,
                "type": relationship.type,
            })

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
    }
    # ============================================================
# PART 7 - SUBSCRIPTIONS AND PLANS
# ============================================================

PLANS = {
    "starter": {
        "name": "Starter",
        "monthly_price_kes": 14900,
        "max_documents": 2500,
    },
    "growth": {
        "name": "Growth",
        "monthly_price_kes": 44900,
        "max_documents": 15000,
    },
    "scale": {
        "name": "Scale",
        "monthly_price_kes": 119900,
        "max_documents": 75000,
    },
    "enterprise": {
        "name": "Enterprise",
        "monthly_price_kes": None,
        "max_documents": None,
    },
}


@app.get("/api/v1/billing/plans")
async def available_plans():
    return {"plans": PLANS}


@app.get("/api/v1/billing/subscription")
async def current_subscription(
    user: User = Depends(current_user),
):
    async with AsyncSessionLocal() as session:
        subscription = await session.scalar(
            select(Subscription).where(
                Subscription.tenant_id == user.tenant_id
            )
        )

    if subscription is None:
        return {
            "plan": "trial",
            "status": "trial",
            "current_period_end": None,
        }

    return {
        "plan": subscription.plan,
        "status": subscription.status,
        "provider": subscription.provider,
        "current_period_end": (
            subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None
        ),
    }


@app.get("/api/v1/billing/payments")
async def payment_history(
    user: User = Depends(current_user),
):
    async with AsyncSessionLocal() as session:
        records = await session.scalars(
            select(Payment)
            .where(Payment.tenant_id == user.tenant_id)
            .order_by(Payment.created_at.desc())
            .limit(50)
        )

    return [
        {
            "id": payment.id,
            "provider": payment.provider,
            "amount": payment.amount,
            "currency": payment.currency,
            "plan": payment.plan,
            "status": payment.status,
            "created_at": payment.created_at.isoformat(),
        }
        for payment in records.all()
    ]


async def activate_subscription(
    tenant_id: str,
    plan: str,
    provider: str,
):
    async with AsyncSessionLocal() as session:
        subscription = await session.scalar(
            select(Subscription).where(
                Subscription.tenant_id == tenant_id
            )
        )

        if subscription is None:
            subscription = Subscription(
                id=new_id("sub"),
                tenant_id=tenant_id,
            )
            session.add(subscription)

        subscription.plan = plan
        subscription.status = "active"
        subscription.provider = provider
        subscription.current_period_end = (
            utc_now() + timedelta(days=30)
        )
        subscription.updated_at = utc_now()

        await session.commit()

# ============================================================
# PART 8 - PAYPAL AND M-PESA
# ============================================================

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox").lower()

PAYPAL_API = (
    "https://api-m.paypal.com"
    if PAYPAL_MODE == "live"
    else "https://api-m.sandbox.paypal.com"
)

MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "")
MPESA_ENV = os.getenv("MPESA_ENV", "sandbox").lower()

MPESA_API = (
    "https://api.safaricom.co.ke"
    if MPESA_ENV == "production"
    else "https://sandbox.safaricom.co.ke"
)


async def paypal_token():
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise HTTPException(503, "PayPal is not configured")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{PAYPAL_API}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
        )

    if response.status_code != 200:
        raise HTTPException(502, "PayPal authentication failed")

    return response.json()["access_token"]


@app.post("/api/v1/payments/paypal/create")
async def paypal_create(
    plan: str,
    user: User = Depends(current_user),
):
    if plan not in {"starter", "growth", "scale"}:
        raise HTTPException(400, "Invalid paid plan")

    amount = PLANS[plan]["monthly_price_kes"]
    # PayPal checkout uses USD. Configure a real USD price per plan.
    usd_prices = {
        "starter": os.getenv("STARTER_PRICE_USD", ""),
        "growth": os.getenv("GROWTH_PRICE_USD", ""),
        "scale": os.getenv("SCALE_PRICE_USD", ""),
    }

    try:
        usd_amount = float(usd_prices[plan])
        if usd_amount <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(503, "USD plan price is not configured")

    token = await paypal_token()

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{PAYPAL_API}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "reference_id": user.tenant_id,
                    "custom_id": f"{user.tenant_id}:{plan}",
                    "amount": {
                        "currency_code": "USD",
                        "value": f"{usd_amount:.2f}",
                    },
                }],
                "application_context": {
                    "return_url": f"{FRONTEND_URL}/billing/success",
                    "cancel_url": f"{FRONTEND_URL}/billing/cancel",
                },
            },
        )

    if response.status_code >= 300:
        raise HTTPException(502, "PayPal order creation failed")

    order = response.json()

    async with AsyncSessionLocal() as session:
        session.add(Payment(
            id=new_id("pay"),
            tenant_id=user.tenant_id,
            provider="paypal",
            provider_reference=order["id"],
            amount=int(usd_amount * 100),
            currency="USD",
            plan=plan,
            status="pending",
        ))
        await session.commit()

    approval = next(
        (
            link["href"]
            for link in order.get("links", [])
            if link.get("rel") == "approve"
        ),
        None,
    )

    return {
        "order_id": order["id"],
        "approval_url": approval,
    }


@app.post("/api/v1/payments/paypal/capture")
async def paypal_capture(
    order_id: str,
    user: User = Depends(current_user),
):
    token = await paypal_token()

    async with AsyncSessionLocal() as session:
        payment = await session.scalar(
            select(Payment).where(
                Payment.provider == "paypal",
                Payment.provider_reference == order_id,
                Payment.tenant_id == user.tenant_id,
            )
        )

        if payment is None:
            raise HTTPException(404, "Payment not found")

        if payment.status == "completed":
            return {"status": "completed"}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{PAYPAL_API}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    if response.status_code >= 300:
        raise HTTPException(502, "PayPal capture failed")

    capture_data = response.json()
    if capture_data.get("status") != "COMPLETED":
        raise HTTPException(402, "PayPal payment is not completed")

    async with AsyncSessionLocal() as session:
        payment = await session.scalar(
            select(Payment).where(
                Payment.provider_reference == order_id,
                Payment.tenant_id == user.tenant_id,
            )
        )
        payment.status = "completed"
        await session.commit()

    await activate_subscription(
        user.tenant_id,
        payment.plan,
        "paypal",
    )

    await write_audit(
        user.tenant_id,
        user.id,
        "payment.completed",
        order_id,
        {"provider": "paypal", "plan": payment.plan},
    )

    return {"status": "completed", "plan": payment.plan}


async def mpesa_token():
    if not MPESA_CONSUMER_KEY or not MPESA_CONSUMER_SECRET:
        raise HTTPException(503, "M-Pesa is not configured")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{MPESA_API}/oauth/v1/generate"
            "?grant_type=client_credentials",
            auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET),
        )

    if response.status_code != 200:
        raise HTTPException(502, "M-Pesa authentication failed")

    return response.json()["access_token"]


@app.post("/api/v1/payments/mpesa/stk")
async def mpesa_stk(
    phone: str,
    plan: str,
    user: User = Depends(current_user),
):
    if plan not in {"starter", "growth", "scale"}:
        raise HTTPException(400, "Invalid paid plan")

    if not MPESA_SHORTCODE or not MPESA_PASSKEY or not MPESA_CALLBACK_URL:
        raise HTTPException(503, "M-Pesa STK configuration is incomplete")

    normalized = phone.replace("+", "").replace(" ", "")
    if normalized.startswith("0"):
        normalized = "254" + normalized[1:]
    if not normalized.startswith("254") or len(normalized) != 12:
        raise HTTPException(400, "Use a valid Kenyan phone number")

    amount = PLANS[plan]["monthly_price_kes"]
    token = await mpesa_token()
    timestamp = utc_now().strftime("%Y%m%d%H%M%S")

    import base64
    password = base64.b64encode(
        f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()
    ).decode()

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{MPESA_API}/mpesa/stkpush/v1/processrequest",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "BusinessShortCode": MPESA_SHORTCODE,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": amount,
                "PartyA": normalized,
                "PartyB": MPESA_SHORTCODE,
                "PhoneNumber": normalized,
                "CallBackURL": MPESA_CALLBACK_URL,
                "AccountReference": user.tenant_id[:12],
                "TransactionDesc": f"{plan} subscription",
            },
        )

    if response.status_code >= 300:
        raise HTTPException(502, "M-Pesa request failed")

    result = response.json()

    if result.get("ResponseCode") != "0":
        raise HTTPException(502, "M-Pesa did not accept the request")

    async with AsyncSessionLocal() as session:
        session.add(Payment(
            id=new_id("pay"),
            tenant_id=user.tenant_id,
            provider="mpesa",
            provider_reference=result["CheckoutRequestID"],
            amount=amount,
            currency="KES",
            plan=plan,
            status="pending",
        ))
        await session.commit()

    return {
        "status": "pending",
        "checkout_request_id": result["CheckoutRequestID"],
        "message": "Check your phone to complete the M-Pesa payment.",
    }


@app.post("/api/v1/payments/mpesa/callback")
async def mpesa_callback(request: Request):
    payload = await request.json()
    callback = payload.get("Body", {}).get("stkCallback", {})

    checkout_id = callback.get("CheckoutRequestID")
    result_code = callback.get("ResultCode")

    if not checkout_id:
        raise HTTPException(400, "Missing checkout reference")

    async with AsyncSessionLocal() as session:
        payment = await session.scalar(
            select(Payment).where(
                Payment.provider == "mpesa",
                Payment.provider_reference == checkout_id,
            )
        )

        if payment is None:
            raise HTTPException(404, "Payment not found")

        if payment.status == "completed":
            return {"ResultCode": 0, "ResultDesc": "Already processed"}

        if result_code == 0:
            payment.status = "completed"
            await session.commit()
            tenant_id = payment.tenant_id
            plan = payment.plan
        else:
            payment.status = "failed"
            await session.commit()
            return {"ResultCode": 0, "ResultDesc": "Payment recorded"}

    await activate_subscription(tenant_id, plan, "mpesa")

    return {"ResultCode": 0, "ResultDesc": "Accepted"}


