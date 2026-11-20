
import streamlit as st
import time

# =========================================================
# ENTERPRISE-KE.-3
# PREMIUM KNOWLEDGE INTELLIGENCE FRONTEND
# PART 1 — APPLICATION FOUNDATION
# =========================================================

st.set_page_config(
    page_title="Enterprise-KE.-3",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

defaults = {
    "active_page": "Overview",
    "token": None,
    "user": None,
    "sidebar_expanded": True,
    "backend_connected": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------------------------------
# DESIGN SYSTEM — PREMIUM DARK INTERFACE
# ---------------------------------------------------------

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #070B12;
    --surface: #0D1420;
    --surface2: #111B2A;
    --border: rgba(148,163,184,0.12);
    --text: #F1F5F9;
    --muted: #94A3B8;
    --cyan: #38BDF8;
    --blue: #6366F1;
    --violet: #8B5CF6;
    --green: #34D399;
}

/* GLOBAL */

html, body, [data-testid="stApp"] {
    background: var(--bg);
    color: var(--text);
    font-family: Inter, sans-serif;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(
            ellipse at 75% -10%,
            rgba(14,165,233,0.12),
            transparent 40%
        ),
        radial-gradient(
            ellipse at 0% 50%,
            rgba(99,102,241,0.06),
            transparent 35%
        ),
        var(--bg);
}

.block-container {
    max-width: 1550px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

/* SIDEBAR */

[data-testid="stSidebar"] {
    background: #090F19;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.3rem;
}

[data-testid="stSidebar"] p {
    color: var(--muted);
}

/* SIDEBAR BRAND */

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 7px 4px 22px;
}

.brand-logo {
    width: 43px;
    height: 43px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 23px;
    font-weight: 800;
    color: white;
    background: linear-gradient(135deg, #0EA5E9, #6366F1, #8B5CF6);
    box-shadow: 0 0 28px rgba(56,189,248,0.22);
}

.brand-title {
    font-size: 14px;
    font-weight: 750;
    color: #F8FAFC;
}

.brand-subtitle {
    font-size: 10px;
    letter-spacing: 0.12em;
    color: #64748B;
    text-transform: uppercase;
    margin-top: 4px;
}

/* NAVIGATION */

.stButton > button {
    width: 100%;
    border-radius: 10px;
    background: rgba(255,255,255,0.015);
    border: 1px solid rgba(148,163,184,0.08);
    color: #B8C5D6;
    padding: 0.68rem 0.9rem;
    text-align: left;
    transition: all 0.22s ease;
}

.stButton > button:hover {
    background: rgba(56,189,248,0.08);
    border-color: rgba(56,189,248,0.25);
    color: #F8FAFC;
    transform: translateX(2px);
}

/* HEADER */

.top-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px 0 22px;
    margin-bottom: 28px;
    border-bottom: 1px solid var(--border);
}

.header-eyebrow {
    color: #64748B;
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.header-title {
    color: #F8FAFC;
    font-size: 24px;
    font-weight: 750;
    margin-top: 5px;
    letter-spacing: -0.04em;
}

.status-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border: 1px solid rgba(56,189,248,0.18);
    border-radius: 30px;
    background: rgba(56,189,248,0.05);
    color: #7DD3FC;
    font-size: 11px;
}

.status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #38BDF8;
    box-shadow: 0 0 10px rgba(56,189,248,0.5);
}

/* HERO */

.hero {
    position: relative;
    overflow: hidden;
    padding: 30px 0 22px;
}

.hero-label {
    color: #38BDF8;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.17em;
    text-transform: uppercase;
}

.hero-title {
    font-size: clamp(34px, 4.5vw, 58px);
    font-weight: 800;
    line-height: 1.08;
    letter-spacing: -0.055em;
    margin-top: 15px;
    color: #F8FAFC;
}

.hero-gradient {
    background: linear-gradient(
        90deg,
        #F8FAFC 0%,
        #67E8F9 35%,
        #818CF8 75%,
        #C4B5FD 100%
    );
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-description {
    color: #94A3B8;
    font-size: 14px;
    line-height: 1.8;
    max-width: 720px;
    margin-top: 18px;
}

/* PANELS */

.surface {
    background: linear-gradient(
        145deg,
        rgba(17,27,42,0.95),
        rgba(10,16,26,0.97)
    );
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 23px;
    transition: all 0.25s ease;
}

.surface:hover {
    border-color: rgba(56,189,248,0.22);
    box-shadow: 0 8px 35px rgba(0,0,0,0.12);
}

.surface-label {
    color: #38BDF8;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.surface-title {
    font-size: 17px;
    font-weight: 700;
    color: #F1F5F9;
    margin-top: 12px;
}

.surface-description {
    color: #94A3B8;
    font-size: 13px;
    line-height: 1.7;
    margin-top: 9px;
}

/* FLOATING DECORATION */

.float {
    animation: floating 6s ease-in-out infinite;
}

.float-delay {
    animation: floating 7s ease-in-out infinite;
    animation-delay: 1.4s;
}

@keyframes floating {
    0%, 100% {
        transform: translateY(0px);
    }
    50% {
        transform: translateY(-7px);
    }
}

/* FOOTER */

.footer {
    border-top: 1px solid var(--border);
    padding-top: 20px;
    margin-top: 48px;
    color: #526176;
    font-size: 11px;
}

/* RESPONSIVE */

@media(max-width: 768px) {
    .block-container {
        padding: 1rem;
    }

    .hero-title {
        font-size: 34px;
    }

    .surface {
        padding: 17px;
    }

    .header-title {
        font-size: 20px;
    }
}

</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# APPLICATION NAVIGATION
# ---------------------------------------------------------

workspace_pages = {
    "Overview": "⌂",
    "Knowledge Graph": "◈",
    "Documents": "▤",
    "AI Intelligence": "✦",
    "Connectors": "⌘",
}

management_pages = {
    "Team": "♧",
    "Payments": "◇",
    "Settings": "⚙",
}


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:

    st.markdown("""
    <div class="brand">
        <div class="brand-logo">◈</div>
        <div>
            <div class="brand-title">Enterprise-KE.-3</div>
            <div class="brand-subtitle">Knowledge Intelligence</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.caption("WORKSPACE")

    for page, icon in workspace_pages.items():

        if st.button(
            f"{icon}   {page}",
            key=f"workspace_{page}",
        ):
            st.session_state.active_page = page
            st.rerun()

    st.divider()

    st.caption("MANAGEMENT")

    for page, icon in management_pages.items():

        if st.button(
            f"{icon}   {page}",
            key=f"management_{page}",
        ):
            st.session_state.active_page = page
            st.rerun()

    st.divider()

    st.markdown("""
    <div style="
        border:1px solid rgba(148,163,184,0.12);
        border-radius:13px;
        padding:14px;
        background:rgba(255,255,255,0.02);
    ">
        <div style="
            font-size:10px;
            color:#64748B;
            letter-spacing:0.12em;
        ">
            PLATFORM
        </div>

        <div style="
            font-size:13px;
            font-weight:700;
            color:#E2E8F0;
            margin-top:7px;
        ">
            Enterprise Intelligence
        </div>

        <div style="
            font-size:11px;
            color:#64748B;
            margin-top:5px;
        ">
            Workspace environment
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------
# MAIN HEADER
# ---------------------------------------------------------

active_page = st.session_state.active_page

st.markdown(f"""
<div class="top-header">
    <div>
        <div class="header-eyebrow">Enterprise Workspace</div>
        <div class="header-title">{active_page}</div>
    </div>

    <div class="status-pill">
        <span class="status-dot"></span>
        Frontend Online
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# OVERVIEW
# ---------------------------------------------------------

if active_page == "Overview":

    st.markdown("""
    <div class="hero">
        <div class="hero-label">
            Knowledge Intelligence Platform
        </div>

        <div class="hero-title">
            Understand your data.<br>
            <span class="hero-gradient">
                Connect your knowledge.
            </span>
        </div>

        <div class="hero-description">
            A unified intelligence workspace designed to connect
            enterprise information, explore relationships, discover
            insights and transform disconnected data into knowledge.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    st.markdown("""
    <div class="surface float">
        <div class="surface-label">
            PLATFORM FOUNDATION
        </div>

        <div class="surface-title">
            Welcome to your intelligence workspace
        </div>

        <div class="surface-description">
            Enterprise-KE.-3 brings documents, connected knowledge,
            AI intelligence and enterprise data into a unified workspace.
            Each module will connect directly to your deployed backend.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # FEATURE CARDS

    col1, col2 = st.columns(2, gap="large")

    with col1:

        st.markdown("""
        <div class="surface">
            <div class="surface-label">01 / KNOWLEDGE</div>
            <div class="surface-title">Knowledge Graph</div>
            <div class="surface-description">
                Navigate connected entities, relationships and
                organizational knowledge through graph exploration.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:

        st.markdown("""
        <div class="surface float-delay">
            <div class="surface-label">02 / INTELLIGENCE</div>
            <div class="surface-title">AI Intelligence</div>
            <div class="surface-description">
                Analyze information, ask questions and discover
                intelligence across your knowledge environment.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    col3, col4 = st.columns(2, gap="large")

    with col3:

        st.markdown("""
        <div class="surface float-delay">
            <div class="surface-label">03 / KNOWLEDGE BASE</div>
            <div class="surface-title">Documents</div>
            <div class="surface-description">
                Upload, organize, retrieve and analyze
                your enterprise information.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:

        st.markdown("""
        <div class="surface">
            <div class="surface-label">04 / INTEGRATIONS</div>
            <div class="surface-title">Connectors</div>
            <div class="surface-description">
                Connect external information sources and
                bring your data into a unified workspace.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------
# MODULE ROUTING — TEMPORARY FOUNDATION
# MODULES WILL BE REPLACED WITH FUNCTIONAL PAGES
# ---------------------------------------------------------

elif active_page != "Overview":

    descriptions = {
        "Knowledge Graph":
            "Explore entities, relationships and connected knowledge.",
        "Documents":
            "Upload, organize and retrieve enterprise documents.",
        "AI Intelligence":
            "AI-powered analysis and intelligent knowledge workflows.",
        "Connectors":
            "Connect and manage external enterprise data sources.",
        "Team":
            "Workspace members, collaboration and invitations.",
        "Payments":
            "Subscriptions, payment requests and billing.",
        "Settings":
            "Account, workspace and platform configuration.",
    }

    st.markdown(f"""
    <div class="surface">
        <div class="surface-label">WORKSPACE MODULE</div>

        <div class="surface-title" style="font-size:24px;">
            {active_page}
        </div>

        <div class="surface-description">
            {descriptions.get(active_page, "Workspace module")}
        </div>

        <div style="
            margin-top:22px;
            padding:14px;
            border-radius:12px;
            background:rgba(56,189,248,0.04);
            border:1px solid rgba(56,189,248,0.10);
            color:#94A3B8;
            font-size:12px;
        ">
            Module foundation initialized.
            Functional integration will be added in the
            upcoming development components.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.markdown("""
<div class="footer">
    ENTERPRISE-KE.-3 &nbsp;·&nbsp;
    KNOWLEDGE INTELLIGENCE PLATFORM
</div>
""", unsafe_allow_html=True)


# =========================================================
# ENTERPRISE-KE.-3
# PART 2 — BACKEND API SERVICE
# File: frontend/services/api.py
# =========================================================

import os
import requests
import streamlit as st
from typing import Any, Optional


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

DEFAULT_BACKEND_URL = "https://enterprise-ke-3.onrender.com"


def get_backend_url() -> str:
    """
    Reads backend URL from Streamlit secrets or environment.
    Falls back to the deployed Enterprise-KE.-3 backend.
    """

    try:
        configured_url = st.secrets.get("BACKEND_URL", "")
    except Exception:
        configured_url = ""

    configured_url = (
        configured_url
        or os.getenv("BACKEND_URL")
        or DEFAULT_BACKEND_URL
    )

    return configured_url.rstrip("/")


BASE_URL = get_backend_url()


# ---------------------------------------------------------
# TOKEN MANAGEMENT
# ---------------------------------------------------------

def get_token() -> Optional[str]:
    """Return the current session authentication token."""

    return st.session_state.get("token")


def set_token(token: Optional[str]) -> None:
    """Set or clear the authentication token."""

    st.session_state["token"] = token


def clear_authentication() -> None:
    """Clear current authentication state."""

    st.session_state["token"] = None
    st.session_state["user"] = None


# ---------------------------------------------------------
# REQUEST HEADERS
# ---------------------------------------------------------

def get_headers(
    extra_headers: Optional[dict] = None
) -> dict:

    headers = {
        "Accept": "application/json",
    }

    token = get_token()

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if extra_headers:
        headers.update(extra_headers)

    return headers


# ---------------------------------------------------------
# RESPONSE HANDLING
# ---------------------------------------------------------

def parse_response(response: requests.Response) -> Any:
    """
    Parses backend responses.
    Raises a readable exception for failed requests.
    """

    try:
        data = response.json()
    except ValueError:
        data = response.text

    if not response.ok:

        if isinstance(data, dict):
            detail = (
                data.get("detail")
                or data.get("message")
                or data.get("error")
                or str(data)
            )
        else:
            detail = str(data)

        raise APIError(
            message=str(detail),
            status_code=response.status_code,
            response_data=data,
        )

    return data


# ---------------------------------------------------------
# CUSTOM API ERROR
# ---------------------------------------------------------

class APIError(Exception):

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Any = None,
    ):

        self.message = message
        self.status_code = status_code
        self.response_data = response_data

        super().__init__(message)


# ---------------------------------------------------------
# REQUEST ENGINE
# ---------------------------------------------------------

def request(
    method: str,
    endpoint: str,
    *,
    params: Optional[dict] = None,
    json_data: Optional[dict] = None,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 45,
    authenticated: bool = True,
) -> Any:
    """
    Central request engine used by all frontend modules.

    Supports:
    - GET
    - POST
    - PUT
    - PATCH
    - DELETE
    - JSON
    - Form data
    - File uploads
    - Bearer authentication
    """

    endpoint = endpoint.lstrip("/")
    url = f"{BASE_URL}/{endpoint}"

    request_headers = {}

    if authenticated:
        request_headers.update(get_headers())

    if headers:
        request_headers.update(headers)

    # Let requests generate multipart headers for file uploads.
    if files:
        request_headers.pop("Content-Type", None)

    try:

        response = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json_data,
            data=data,
            files=files,
            headers=request_headers,
            timeout=timeout,
        )

        return parse_response(response)

    except requests.Timeout as exc:

        raise APIError(
            "The backend request timed out. "
            "The service may be waking up or processing a request."
        ) from exc

    except requests.ConnectionError as exc:

        raise APIError(
            "Unable to connect to the Enterprise-KE.-3 backend. "
            "Check the backend deployment and internet connection."
        ) from exc

    except requests.RequestException as exc:

        raise APIError(
            f"Network request failed: {exc}"
        ) from exc


# ---------------------------------------------------------
# HTTP METHODS
# ---------------------------------------------------------

def get(
    endpoint: str,
    *,
    params: Optional[dict] = None,
    authenticated: bool = True,
    timeout: int = 45,
):
    return request(
        "GET",
        endpoint,
        params=params,
        authenticated=authenticated,
        timeout=timeout,
    )


def post(
    endpoint: str,
    *,
    json_data: Optional[dict] = None,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
    authenticated: bool = True,
    timeout: int = 60,
):
    return request(
        "POST",
        endpoint,
        json_data=json_data,
        data=data,
        files=files,
        authenticated=authenticated,
        timeout=timeout,
    )


def put(
    endpoint: str,
    *,
    json_data: Optional[dict] = None,
    authenticated: bool = True,
    timeout: int = 45,
):
    return request(
        "PUT",
        endpoint,
        json_data=json_data,
        authenticated=authenticated,
        timeout=timeout,
    )


def patch(
    endpoint: str,
    *,
    json_data: Optional[dict] = None,
    authenticated: bool = True,
    timeout: int = 45,
):
    return request(
        "PATCH",
        endpoint,
        json_data=json_data,
        authenticated=authenticated,
        timeout=timeout,
    )


def delete(
    endpoint: str,
    *,
    authenticated: bool = True,
    timeout: int = 45,
):
    return request(
        "DELETE",
        endpoint,
        authenticated=authenticated,
        timeout=timeout,
    )


# ---------------------------------------------------------
# FILE UPLOAD
# ---------------------------------------------------------

def upload_file(
    endpoint: str,
    uploaded_file,
    *,
    extra_data: Optional[dict] = None,
    authenticated: bool = True,
    timeout: int = 120,
):
    """
    Uploads a Streamlit UploadedFile object.

    The file is sent as multipart/form-data.
    """

    file_payload = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream",
        )
    }

    return request(
        "POST",
        endpoint,
        data=extra_data,
        files=file_payload,
        authenticated=authenticated,
        timeout=timeout,
    )


# ---------------------------------------------------------
# BACKEND HEALTH
# ---------------------------------------------------------

def health_check() -> dict:
    """
    Checks the backend health endpoints.
    """

    endpoints = [
        "/api/v1/health",
        "/health",
    ]

    last_error = None

    for endpoint in endpoints:

        try:

            response = requests.get(
                f"{BASE_URL}{endpoint}",
                timeout=15,
            )

            if response.ok:

                try:
                    payload = response.json()
                except ValueError:
                    payload = {"response": response.text}

                return {
                    "connected": True,
                    "endpoint": endpoint,
                    "data": payload,
                    "url": BASE_URL,
                }

            last_error = (
                f"Health endpoint returned HTTP "
                f"{response.status_code}"
            )

        except requests.RequestException as exc:
            last_error = str(exc)

    return {
        "connected": False,
        "endpoint": None,
        "data": None,
        "url": BASE_URL,
        "error": last_error or "Health check failed",
    }


# ---------------------------------------------------------
# AUTHENTICATION HELPERS
# ---------------------------------------------------------

def login(email: str, password: str):
    """
    Sends login request to the backend.

    Actual response fields will be mapped in the
    authentication module after verifying the API schema.
    """

    return post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
        authenticated=False,
    )


def register(
    email: str,
    password: str,
    name: str,
):
    """
    Account registration helper.
    """

    return post(
        "/api/v1/auth/register",
        json_data={
            "email": email,
            "password": password,
            "name": name,
        },
        authenticated=False,
    )


def get_current_user():
    """
    Retrieve the authenticated user.
    """

    return get(
        "/api/v1/auth/me",
        authenticated=True,
)

