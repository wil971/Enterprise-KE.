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
