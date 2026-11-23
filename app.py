
# ============================================================
# ENTERPRISE-KE | PART 1 — CORE FOUNDATION
# ============================================================

import streamlit as st
import requests
import pandas as pd
import json
import uuid
import re
import time
import math
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List

st.set_page_config(
    page_title="Enterprise-KE",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_NAME = "Enterprise-KE"
APP_VERSION = "3.0.0"
API_BASE_URL = "https://enterprise-ke-3.onrender.com"
API_TIMEOUT = 25

COLORS = {
    "bg": "#080B12",
    "surface": "#101622",
    "surface2": "#151D2B",
    "border": "#263144",
    "text": "#F2F5FA",
    "muted": "#8995A8",
    "accent": "#7C8CFF",
    "accent2": "#48D6C6",
    "danger": "#FF657A",
    "warning": "#FFC66E",
    "success": "#55D6A5"
}

STATE_DEFAULTS = {
    "authenticated": False,
    "access_token": None,
    "user": None,
    "current_page": "Overview",
    "search_query": "",
    "search_results": [],
    "documents": [],
    "collections": [],
    "team": [],
    "notifications": [],
    "chat_messages": [],
    "connectors": [],
    "selected_document": None,
    "selected_collection": None,
    "api_status": "unknown",
    "api_error": None,
    "loading": False,
    "notice": None,
    "filters": {},
    "last_refresh": None
}

def initialize_session_state():
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = (
                json.loads(json.dumps(value))
                if isinstance(value, (dict, list))
                else value
            )

initialize_session_state()

def set_notice(message, kind="info"):
    st.session_state.notice = {
        "message": str(message),
        "kind": kind,
        "time": time.time()
    }

def clear_notice():
    st.session_state.notice = None

def api_call(method, endpoint, params=None, payload=None,
              files=None, timeout=API_TIMEOUT):
    """Central API request handler."""
    headers = {}

    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=params,
            json=payload,
            files=files,
            timeout=timeout
        )

        try:
            data = response.json()
        except Exception:
            data = {"detail": response.text[:2000]}

        return {
            "ok": response.ok,
            "status": response.status_code,
            "data": data,
            "error": None if response.ok else data
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "status": 0,
            "data": None,
            "error": str(exc)
        }

def api_get(endpoint, params=None):
    return api_call("GET", endpoint, params=params)

def api_post(endpoint, payload=None):
    return api_call("POST", endpoint, payload=payload)

def api_delete(endpoint):
    return api_call("DELETE", endpoint)

def safe_list(value):
    return value if isinstance(value, list) else []

def safe_dict(value):
    return value if isinstance(value, dict) else {}

def format_datetime(value):
    if not value:
        return "—"
    try:
        return str(value).replace("T", " ")[:19]
    except Exception:
        return "—"

def inject_base_style():
    st.markdown("""
    <style>
    :root {
        --ek-bg: #080B12;
        --ek-surface: #101622;
        --ek-surface2: #151D2B;
        --ek-border: #263144;
        --ek-text: #F2F5FA;
        --ek-muted: #8995A8;
        --ek-accent: #7C8CFF;
        --ek-teal: #48D6C6;
    }

    .stApp {
        background:
          radial-gradient(ellipse at 10% 0%,
          rgba(124,140,255,.10), transparent 35%),
          var(--ek-bg);
        color: var(--ek-text);
    }

    html, body, [class*="css"] {
        font-family: Inter, system-ui, sans-serif;
    }

    h1, h2, h3, h4 {
        letter-spacing: -0.035em;
    }

    div[data-testid="stMetric"] {
        background: rgba(16,22,34,.75);
        border: 1px solid var(--ek-border);
        padding: 16px;
        border-radius: 16px;
    }

    div[data-testid="stMetricValue"] {
        color: var(--ek-text);
    }

    .ek-card {
        background: linear-gradient(
            145deg,
            rgba(21,29,43,.95),
            rgba(12,17,26,.92)
        );
        border: 1px solid var(--ek-border);
        border-radius: 18px;
        padding: 20px;
        transition: .25s ease;
    }

    .ek-card:hover {
        transform: translateY(-2px);
        border-color: rgba(124,140,255,.45);
        box-shadow: 0 12px 35px rgba(0,0,0,.20);
    }

    .ek-muted {
        color: var(--ek-muted);
    }

    .ek-pill {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 12px;
        background: rgba(124,140,255,.12);
        border: 1px solid rgba(124,140,255,.25);
    }

    button, [role="button"] {
        transition: .2s ease !important;
    }

    @media (max-width: 768px) {
        .ek-card {
            padding: 14px;
            border-radius: 14px;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        * {
            transition: none !important;
            animation: none !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

inject_base_style()

# Part 1 complete — foundational configuration
