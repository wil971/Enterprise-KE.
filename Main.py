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
        )def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must have at least 12 characters.")

    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, expected_hash = stored_hash.split("$", 1)

        actual_hash = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
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

    return jwt.encode(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    if not credentials:
        raise HTTPException(401, "Authentication required.")

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")

        if not user_id or not tenant_id:
            raise HTTPException(401, "Invalid token.")

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired.")

    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token.")

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(401, "User not found or inactive.")

    return user


async def require_admin(
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required.")

    return user


class RegisterInput(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


@app.post("/api/v1/auth/register")
async def register(
    payload: RegisterInput,
    db: AsyncSession = Depends(get_db),
):
    email = payload.email.lower().strip()

    existing = await db.execute(
        select(User).where(User.email == email)
    )

    if existing.scalar_one_or_none():
        raise HTTPException(409, "Email already registered.")

    organization = Organization(
        name=payload.organization_name.strip()
    )

    db.add(organization)
    await db.flush()

    user = User(
        tenant_id=organization.id,
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role="admin",
    )

    db.add(user)

    db.add(
        Subscription(
            tenant_id=organization.id,
            plan="free",
            status="trial",
            ends_at=utc_now() + timedelta(days=14),
        )
    )

    await db.commit()
    await db.refresh(user)

    return {
        "access_token": create_access_token(
            user.id, user.tenant_id, user.role
        ),
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
    payload: LoginInput,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.email == payload.email.lower().strip()
        )
    )

    user = result.scalar_one_or_none()

    if not user or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(401, "Invalid email or password.")

    if not user.is_active:
        raise HTTPException(403, "Account inactive.")

    return {
        "access_token": create_access_token(
            user.id, user.tenant_id, user.role
        ),
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
async def current_user_profile(
    user: User = Depends(get_current_user),
):
    return {
        "id": user.id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }async def write_audit(
    db: AsyncSession,
    tenant_id: str,
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: str = "",
    details: Optional[dict] = None,
    ip_address: str = "",
):
    event = AuditEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
    )

    db.add(event)
    await db.commit()
    return event


class InviteInput(BaseModel):
    email: EmailStr
    role: str = "member"


@app.post("/api/v1/team/invitations")
async def create_invitation(
    payload: InviteInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    email = payload.email.lower().strip()

    if payload.role not in {"member", "viewer"}:
        raise HTTPException(400, "Invalid role.")

    existing = await db.execute(
        select(User).where(
            User.tenant_id == user.tenant_id,
            User.email == email,
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(409, "User already exists.")

    raw_token = secrets.token_urlsafe(32)

    from datetime import timedelta

    invitation = Invitation(
        tenant_id=user.tenant_id,
        email=email,
        role=payload.role,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=utc_now() + timedelta(days=7),
    )

    db.add(invitation)
    await db.commit()

    await write_audit(
        db,
        user.tenant_id,
        user.id,
        "team.invitation_created",
        "invitation",
        invitation.id,
        {"email": email, "role": payload.role},
        request.client.host if request.client else "",
    )

    return {
        "invitation_id": invitation.id,
        "invitation_token": raw_token,
        "email": email,
        "expires_at": invitation.expires_at,
        "email_delivery": "not_configured",
    }


class AcceptInviteInput(BaseModel):
    token: str
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)


@app.post("/api/v1/team/invitations/accept")
async def accept_invitation(
    payload: AcceptInviteInput,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(
        payload.token.encode()
    ).hexdigest()

    result = await db.execute(
        select(Invitation).where(
            Invitation.token_hash == token_hash
        )
    )

    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(404, "Invitation not found.")

    expiry = invitation.expires_at

    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if invitation.accepted_at or expiry < utc_now():
        raise HTTPException(400, "Invitation expired or already used.")

    existing = await db.execute(
        select(User).where(
            User.tenant_id == invitation.tenant_id,
            User.email == invitation.email,
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(409, "User already exists.")

    new_user = User(
        tenant_id=invitation.tenant_id,
        email=invitation.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=invitation.role,
    )

    invitation.accepted_at = utc_now()

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "message": "Invitation accepted.",
        "user_id": new_user.id,
    }


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

    return [
        {
            "id": member.id,
            "email": member.email,
            "full_name": member.full_name,
            "role": member.role,
            "is_active": member.is_active,
            "created_at": member.created_at,
        }
        for member in result.scalars().all()
    ]


@app.get("/api/v1/audit")
async def get_audit_logs(
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
            "created_at": event.created_at,
        }
        for event in result.scalars().all()
               ]def extract_document_text(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension == ".txt":
        return content.decode("utf-8", errors="replace")

    if extension == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(
            page.extract_text() or "" for page in reader.pages
        )

    if extension == ".docx":
        document = DocxDocument(io.BytesIO(content))
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    if extension == ".csv":
        return content.decode("utf-8", errors="replace")

    raise HTTPException(
        415,
        "Supported formats: PDF, DOCX, TXT and CSV.",
    )


def split_text(
    text_value: str,
    chunk_size: int = 1200,
    overlap: int = 150,
):
    text_value = re.sub(r"\s+", " ", text_value).strip()

    if not text_value:
        return []

    chunks = []
    start = 0

    while start < len(text_value):
        end = min(start + chunk_size, len(text_value))
        chunks.append(text_value[start:end])

        if end >= len(text_value):
            break

        start = end - overlap

    return chunks


async def index_document_in_graph(
    document_id: str,
    tenant_id: str,
    filename: str,
    chunks: list[str],
):
    async with neo4j_driver.session(
        database=NEO4J_DATABASE
    ) as session:

        await session.run(
            """
            MERGE (d:Document {
                id: $document_id,
                tenant_id: $tenant_id
            })
            SET d.filename = $filename,
                d.created_at = datetime()
            """,
            document_id=document_id,
            tenant_id=tenant_id,
            filename=filename,
        )

        for index, chunk in enumerate(chunks):
            await session.run(
                """
                MATCH (d:Document {
                    id: $document_id,
                    tenant_id: $tenant_id
                })
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
                chunk_id=f"{document_id}:{index}",
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
        raise HTTPException(413, "File exceeds upload size limit.")

    filename = Path(file.filename or "document.txt").name
    extracted_text = extract_document_text(filename, content)

    if not extracted_text.strip():
        raise HTTPException(422, "No readable text extracted.")

    document_id = str(uuid.uuid4())
    text_hash = hashlib.sha256(
        extracted_text.encode()
    ).hexdigest()

    chunks = split_text(extracted_text)

    document = Document(
        id=document_id,
        tenant_id=user.tenant_id,
        uploaded_by=user.id,
        filename=filename,
        content_type=file.content_type or "",
        source="upload",
        extracted_text=extracted_text,
        text_hash=text_hash,
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
        logger.exception("Neo4j indexing failed.")

        await db.delete(document)
        await db.commit()

        raise HTTPException(
            503,
            "Graph indexing failed. Please retry.",
        )

    await write_audit(
        db,
        user.tenant_id,
        user.id,
        "document.uploaded",
        "document",
        document_id,
        {
            "filename": filename,
            "chunks": len(chunks),
        },
        request.client.host if request.client else "",
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
            "id": document.id,
            "filename": document.filename,
            "source": document.source,
            "created_at": document.created_at,
        }
        for document in result.scalars().all()
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

    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(404, "Document not found.")

    return {
        "id": document.id,
        "filename": document.filename,
        "source": document.source,
        "text": document.extracted_text,
        "created_at": document.created_at,
    }class SearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=20, ge=1, le=100)


@app.post("/api/v1/search")
async def search_documents(
    payload: SearchInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    terms = [
        term.strip()
        for term in payload.query.split()
        if term.strip()
    ]

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
        db,
        user.tenant_id,
        user.id,
        "search.executed",
        "document",
        details={
            "query": payload.query,
            "result_count": len(documents),
        },
        ip_address=request.client.host if request.client else "",
    )

    return {
        "query": payload.query,
        "count": len(documents),
        "search_type": "keyword",
        "results": [
            {
                "document_id": document.id,
                "filename": document.filename,
                "snippet": document.extracted_text[:500],
                "source": document.source,
            }
            for document in documents
        ],
    }


@app.get("/api/v1/graph/documents")
async def get_graph_documents(
    user: User = Depends(get_current_user),
):
    async with neo4j_driver.session(
        database=NEO4J_DATABASE
    ) as session:

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
    user: User = Depends(get_current_user),
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
            OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:DocumentChunk {
                tenant_id: $tenant_id
            })
            RETURN d.id AS document_id,
                   d.filename AS filename,
                   collect({
                       id: c.id,
                       text: c.text,
                       chunk_index: c.chunk_index
                   }) AS chunks
            """,
            document_id=document_id,
            tenant_id=user.tenant_id,
        )

        record = await result.single()

    if not record:
        raise HTTPException(404, "Document not found in this workspace.")

    return {
        "document_id": record["document_id"],
        "filename": record["filename"],
        "chunks": [
            chunk for chunk in record["chunks"]
            if chunk.get("id")
        ],
    }
