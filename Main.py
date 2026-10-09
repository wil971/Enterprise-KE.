# ============================================================================
# app.py - PART 1/4: CONFIGURATION, DATABASE MODELS & SECURITY
# Enterprise Intelligence Platform (Glean Architecture Core)
# ============================================================================

import os
import time
import logging
import asyncio
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
import jwt

# SQLAlchemy Async Imports for Production PostgreSQL Persistence
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, Integer, Index

# ----------------------------------------------------------------------------
# 1.1 LOGGING & CONFIGURATION
# ----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("EnterpriseIntelligence.Core")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "prod-enterprise-secret-key-render-2026-v1")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24-hour persistent enterprise session

# Database URL support for Render PostgreSQL (asyncpg driver)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite+aiosqlite:///:memory:"  # In-memory fallback for immediate zero-config start
)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ----------------------------------------------------------------------------
# 1.2 DATABASE MODELS (SQLAlchemy Persistent Audit Ledger & Tenants)
# ----------------------------------------------------------------------------
class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    tenant_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(128), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    resource = Column(String(256), nullable=False)
    metadata_json = Column(JSON, nullable=True)

class EnterpriseTenantModel(Base):
    __tablename__ = "tenants"

    tenant_id = Column(String(128), primary_key=True)
    company_name = Column(String(256), nullable=False)
    subscription_tier = Column(String(64), default="STANDARD")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

# Index for multi-tenant isolation audit log queries
Index("idx_tenant_user_audit", AuditLogModel.tenant_id, AuditLogModel.user_id)

# ----------------------------------------------------------------------------
# 1.3 SECURITY & TOKEN AUTHENTICATION FUNCTIONS
# ----------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a enterprise-signed JWT token carrying Tenant & Subscription Claims."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decodes JWT token and validates signature integrity."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate enterprise credentials",
            headers={"WWW-Authenticate": "Bearer"},
)
    
