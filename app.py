(import streamlit as st
st.set_page_config(
    page_title="Enterprise KE",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# SESSION STATE
defaults = {
    "active_page": "Overview",
    "access_token": None,
    "current_user": None,
    "backend_status": "Not checked",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# DESIGN SYSTEM
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #080b12;
    --panel: #111722;
    --border: rgba(148,163,184,.14);
    --text: #e8edf5;
    --muted: #8c9aaf;
    --cyan: #67e8f9;
    --purple: #818cf8;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background:
        radial-gradient(ellipse at 10% 0%,
        rgba(70,90,180,.14), transparent 40%),
        radial-gradient(ellipse at 95% 35%,
        rgba(0,200,220,.07), transparent 35%),
        var(--bg);
    color: var(--text);
}

.block-container {
    max-width: 1450px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    font-family: 'Manrope', sans-serif !important;
    letter-spacing: -.035em;
}

section[data-testid="stSidebar"] {
    background: #0b1019;
    border-right: 1px solid var(--border);
}

.stButton > button {
    border: 1px solid var(--border);
    border-radius: 12px;
    background: linear-gradient(135deg,
        rgba(99,102,241,.17),
        rgba(34,211,238,.09));
    color: var(--text);
    font-weight: 600;
    transition: all .25s ease;
}

.stButton > button:hover {
    border-color: rgba(103,232,249,.5);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(34,211,238,.1);
}

[data-testid="stMetric"] {
    background: rgba(17,23,34,.82);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px;
}

[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
}

.module-card {
    background: rgba(17,23,34,.8);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 22px;
    min-height: 145px;
    transition: all .3s ease;
}

.module-card:hover {
    background: #151e2b;
    border-color: rgba(103,232,249,.3);
    transform: translateY(-4px);
}

.module-title {
    font-size: 17px;
    font-weight: 700;
    margin-bottom: 8px;
}

.module-desc {
    color: #91a0b6;
    font-size: 13px;
    line-height: 1.6;
}

.hero {
    background: linear-gradient(120deg,
        rgba(99,102,241,.16),
        rgba(34,211,238,.08));
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 30px;
    transition: .3s ease;
}

.hero:hover {
    border-color: rgba(103,232,249,.3);
    transform: translateY(-2px);
}

.pill {
    display: inline-block;
    border-radius: 999px;
    padding: 5px 11px;
    font-size: 11px;
    font-weight: 700;
    background: rgba(99,102,241,.15);
    border: 1px solid rgba(99,102,241,.25);
    color: #a5b4fc;
}

.ambient {
    position: fixed;
    width: 330px;
    height: 330px;
    border-radius: 50%;
    filter: blur(100px);
    opacity: .12;
    pointer-events: none;
    z-index: 0;
}

.ambient-a {
    background: #6366f1;
    top: -100px;
    left: 18%;
    animation: drift-a 18s ease-in-out infinite alternate;
}

.ambient-b {
    background: #22d3ee;
    bottom: -130px;
    right: 12%;
    animation: drift-b 23s ease-in-out infinite alternate;
}

@keyframes drift-a {
    from { transform: translate(0,0); }
    to { transform: translate(130px,90px); }
}

@keyframes drift-b {
    from { transform: translate(0,0); }
    to { transform: translate(-100px,-80px); }
}

div[data-testid="stExpander"] {
    border: 1px solid var(--border);
    border-radius: 14px;
}

hr {
    border-color: var(--border);
}
</style>

<div class="ambient ambient-a"></div>
<div class="ambient ambient-b"></div>
""", unsafe_allow_html=True)


# NAVIGATION
PAGES = [
    "Overview",
    "Knowledge Graph",
    "Documents",
    "AI Intelligence",
    "Connectors",
    "Team",
    "Payments",
    "Settings",
]

ICONS = {
    "Overview": "◈",
    "Knowledge Graph": "◎",
    "Documents": "▤",
    "AI Intelligence": "✧",
    "Connectors": "⌘",
    "Team": "♙",
    "Payments": "◇",
    "Settings": "⚙",
}


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:12px 4px 22px;">
            <div style="font-size:25px;font-weight:800;">
                <span style="color:#67e8f9;">ENTERPRISE</span>
                <span style="color:#818cf8;"> KE</span>
            </div>
            <div style="color:#8391a7;font-size:11px;
                letter-spacing:2px;margin-top:5px;">
                KNOWLEDGE INTELLIGENCE
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.caption("WORKSPACE")

        for page in PAGES:
            if st.button(
                f"{ICONS[page]}   {page}",
                key=f"nav_{page}",
                use_container_width=True,
            ):
                st.session_state.active_page = page
                st.rerun()

        st.divider()

        st.caption("PLATFORM")

        st.markdown("""
        <div style="color:#8c9aaf;font-size:12px;padding:8px;">
            Enterprise Knowledge Platform
        </div>
        """, unsafe_allow_html=True)


# HEADER
def render_header():
    page = st.session_state.active_page

    st.markdown(
        f"""
        <div style="margin-bottom:24px;">
            <div style="color:#8c9aaf;font-size:12px;
                letter-spacing:1.5px;">
                ENTERPRISE WORKSPACE
            </div>
            <div style="font-size:25px;font-weight:800;
                margin-top:5px;">
                {page}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# OVERVIEW
def render_overview():
    st.markdown("""
    <div class="hero">
        <div class="pill">KNOWLEDGE INTELLIGENCE PLATFORM</div>

        <h1 style="margin-top:18px;font-size:36px;">
            Your knowledge.<br>
            <span style="color:#67e8f9;">
                Connected intelligently.
            </span>
        </h1>

        <p style="color:#9aa8bc;max-width:700px;
            font-size:15px;line-height:1.8;">
            Organize enterprise documents, discover connections,
            explore knowledge relationships and manage your
            workspace from one unified platform.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    st.subheader("Platform Modules")

    modules = [
        ("Knowledge Graph",
         "Explore relationships between documents and knowledge entities."),
        ("Documents",
         "Upload and manage your organization's knowledge files."),
        ("AI Intelligence",
         "Search your knowledge base using natural-language queries."),
        ("Connectors",
         "Bring external content into your knowledge workspace."),
        ("Team",
         "Manage workspace members and invitations."),
        ("Payments",
         "View plans and payment requests for your subscription."),
    ]

    columns = st.columns(3)

    for i, (name, description) in enumerate(modules):
        with columns[i % 3]:
            st.markdown(
                f"""
                <div class="module-card">
                    <div class="module-title">{name}</div>
                    <div class="module-desc">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write("")

            if st.button(
                f"Open {name}",
                key=f"open_{name}",
                use_container_width=True,
            ):
                st.session_state.active_page = name
                st.rerun()


# PLACEHOLDER PAGES
def render_placeholder(page):
    st.markdown("""
    <div class="hero">
        <div class="pill">MODULE FRAMEWORK</div>
        <h2 style="margin-top:15px;">Module framework ready</h2>
        <p style="color:#9aa8bc;">
            This module will be connected to its real backend
            functionality during the next development parts.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ROUTING
def render_page():
    page = st.session_state.active_page

    if page == "Overview":
        render_overview()
    else:
        render_placeholder(page)


# APP START
render_sidebar()
render_header()
render_page()

import requests

BASE_URL = "https://enterprise-ke-3.onrender.com"


class APIClient:
    def __init__(self):
        self.token = None

    def set_token(self, token):
        self.token = token

    def headers(self):
        result = {}

        if self.token:
            result["Authorization"] = f"Bearer {self.token}"

        return result

    def request(self, method, path, **kwargs):
        try:
            response = requests.request(
                method,
                f"{BASE_URL}{path}",
                headers=self.headers(),
                timeout=60,
                **kwargs,
            )

            if response.status_code == 204:
                return None

            try:
                data = response.json()
            except ValueError:
                data = {"detail": response.text}

            if not response.ok:
                raise RuntimeError(
                    str(data.get("detail", "Request failed"))
                )

            return data

        except requests.exceptions.Timeout:
            raise RuntimeError("Backend request timed out.")

        except requests.exceptions.ConnectionError:
            raise RuntimeError("Backend connection failed.")

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def upload(self, path, file):
        return self.post(
            path,
            files={
                "file": (
                    file.name,
                    file.getvalue(),
                    getattr(file, "type", "application/octet-stream"),
                )
            },
        )


api = APIClient()
import streamlit as st
from api_client import api


def login_form():
    st.subheader("Sign in")

    email = st.text_input("Email", key="login_email")
    password = st.text_input(
        "Password",
        type="password",
        key="login_password",
    )

    if st.button("Sign in", key="login_submit"):
        if not email or not password:
            st.warning("Enter your email and password.")
            return

        try:
            result = api.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )

            token = result["access_token"]

            api.set_token(token)
            st.session_state["access_token"] = token
            st.session_state["current_user"] = result["user"]

            st.success("Signed in successfully.")
            st.rerun()

        except Exception as error:
            st.error(str(error))


def register_form():
    st.subheader("Create enterprise account")

    organization = st.text_input(
        "Organization name",
        key="reg_organization",
    )

    full_name = st.text_input(
        "Full name",
        key="reg_full_name",
    )

    email = st.text_input(
        "Email address",
        key="reg_email",
    )

    password = st.text_input(
        "Password (minimum 12 characters)",
        type="password",
        key="reg_password",
    )

    confirm = st.text_input(
        "Confirm password",
        type="password",
        key="reg_confirm",
    )

    if st.button("Create account", key="reg_submit"):
        if not all([organization, full_name, email, password]):
            st.warning("Please complete all fields.")
            return

        if len(password) < 12:
            st.warning("Password must be at least 12 characters.")
            return

        if password != confirm:
            st.warning("Passwords do not match.")
            return

        try:
            result = api.post(
                "/api/v1/auth/register",
                json={
                    "organization_name": organization,
                    "full_name": full_name,
                    "email": email,
                    "password": password,
                },
            )

            token = result["access_token"]

            api.set_token(token)
            st.session_state["access_token"] = token
            st.session_state["current_user"] = result["user"]

            st.success("Account created.")
            st.rerun()

        except Exception as error:
            st.error(str(error))


def auth_page():
    login_tab, register_tab = st.tabs(
        ["Sign In", "Create Account"]
    )

    with login_tab:
        login_form()

    with register_tab:
        register_form()
        import streamlit as st
from api_client import api


def dashboard_page():
    st.title("Enterprise Overview")

    try:
        data = api.get("/api/v1/dashboard")
        usage = api.get("/api/v1/usage")

    except Exception as error:
        st.error(f"Dashboard unavailable: {error}")
        return

    col1, col2, col3 = st.columns(3)

    col1.metric("Documents", data.get("documents", 0))
    col2.metric("Team Members", data.get("users", 0))
    col3.metric("Audit Events", data.get("audit_events", 0))

    st.divider()

    st.subheader("Workspace Information")

    st.write("Tenant ID:", data.get("tenant_id", "Unavailable"))
    st.write("Backend:", data.get("backend_url", "Unavailable"))
    st.write("Generated:", data.get("generated_at", "Unavailable"))

    st.divider()

    st.subheader("Subscription & Usage")

    st.write("Plan:", usage.get("plan", "Unavailable"))

    usage_values = usage.get("usage", {})
    limits = usage.get("limits", {})

    for key, value in usage_values.items():
        limit = limits.get(key)

        st.write(key.replace("_", " ").title(), value, "/", limit)

        if isinstance(value, (int, float)):
            if isinstance(limit, (int, float)) and limit > 0:
                st.progress(min(value / limit, 1.0))
