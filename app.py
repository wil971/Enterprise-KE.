
# ============================================================
# ENTERPRISE GRAPHRAG
# PART 1/20 — CORE APPLICATION + DESIGN SYSTEM + API ENGINE
# ============================================================

import os
import json
import requests
import streamlit as st
from datetime import datetime, timezone

st.set_page_config(
    page_title="Enterprise GraphRAG",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# APPLICATION CONFIGURATION
# ------------------------------------------------------------

API_BASE = os.getenv(
    "GRAPHRAG_API_URL",
    "https://enterprise-ke-3.onrender.com"
).rstrip("/")

PRODUCT_NAME = "Enterprise GraphRAG"

if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "Home"

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "search_query" not in st.session_state:
    st.session_state.search_query = ""

if "api_status" not in st.session_state:
    st.session_state.api_status = None


# ------------------------------------------------------------
# DESIGN SYSTEM
# ------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --background: #f7f8fa;
    --surface: #ffffff;
    --border: #e8ebf0;
    --text: #202124;
    --muted: #707784;
    --success: #15803d;
}

html, body, [class*="css"] {
    font-family: Inter, sans-serif;
}

.stApp {
    background: var(--background);
    color: var(--text);
}

.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e8ebf0;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
}

h1 {
    font-weight: 800 !important;
    letter-spacing: -1.3px !important;
}

h2, h3 {
    font-weight: 700 !important;
    letter-spacing: -0.5px !important;
}

.eg-brand {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 7px 3px 23px;
}

.eg-logo {
    width: 42px;
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 23px;
    font-weight: 800;
    border-radius: 13px;
    background: linear-gradient(135deg, #2563eb, #6366f1);
}

.eg-name {
    font-size: 17px;
    font-weight: 800;
    color: #1e293b;
}

.eg-tagline {
    font-size: 10px;
    color: #7b8492;
    margin-top: 3px;
}

.eg-section {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.1px;
    text-transform: uppercase;
    color: #9aa2ae;
    padding: 17px 0 7px 4px;
}

.eg-card {
    background: #ffffff;
    border: 1px solid #e8ebf0;
    border-radius: 15px;
    padding: 20px;
}

.eg-card-title {
    font-size: 15px;
    font-weight: 700;
    color: #202938;
}

.eg-card-subtitle {
    font-size: 12px;
    color: #77808d;
    margin-top: 5px;
}

.eg-muted {
    color: #77808d;
}

.eg-pill {
    display: inline-block;
    background: #eff6ff;
    color: #2563eb;
    border-radius: 20px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 600;
}

.eg-search-box {
    background: white;
    border: 1px solid #dfe5ed;
    border-radius: 16px;
    padding: 10px;
    box-shadow: 0 5px 20px rgba(15, 23, 42, 0.035);
}

.eg-auth {
    background: white;
    border: 1px solid #e8ebf0;
    border-radius: 20px;
    padding: 30px;
    box-shadow: 0 12px 40px rgba(15, 23, 42, .045);
}

.eg-divider {
    border-bottom: 1px solid #e8ebf0;
    margin: 15px 0;
}

.eg-footer {
    color: #9aa2ae;
    font-size: 11px;
    padding-top: 15px;
}

button[kind="primary"] {
    background: #2563eb !important;
    border-color: #2563eb !important;
    border-radius: 9px !important;
}

button[kind="secondary"] {
    border-radius: 9px !important;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e8ebf0;
    border-radius: 13px;
    padding: 15px;
}

[data-testid="stMetricValue"] {
    font-weight: 750;
}

</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
# API CLIENT ENGINE
# ------------------------------------------------------------

def api_request(
    method,
    endpoint,
    payload=None,
    authenticated=True,
    timeout=45,
):
    headers = {
        "Accept": "application/json",
    }

    if authenticated and st.session_state.token:
        headers["Authorization"] = (
            f"Bearer {st.session_state.token}"
        )

    try:
        response = requests.request(
            method=method,
            url=f"{API_BASE}{endpoint}",
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        try:
            result = response.json()
        except ValueError:
            result = {"detail": response.text}

        return response.status_code, result

    except requests.exceptions.Timeout:
        return 0, {"detail": "Backend request timed out."}

    except requests.exceptions.ConnectionError:
        return 0, {"detail": "Backend connection failed."}

    except requests.exceptions.RequestException as exc:
        return 0, {"detail": str(exc)}


def api_get(endpoint, authenticated=True):
    return api_request(
        "GET",
        endpoint,
        authenticated=authenticated,
    )


def api_post(endpoint, payload=None, authenticated=True):
    return api_request(
        "POST",
        endpoint,
        payload=payload,
        authenticated=authenticated,
    )


def api_delete(endpoint, authenticated=True):
    return api_request(
        "DELETE",
        endpoint,
        authenticated=authenticated,
    )


def api_health():
    status, result = api_get(
        "/health",
        authenticated=False,
    )

    st.session_state.api_status = (
        status == 200,
        result,
    )

    return status == 200, result


# ------------------------------------------------------------
# AUTHENTICATION HELPERS
# ------------------------------------------------------------

def set_authenticated(data):
    st.session_state.token = data.get("access_token")
    st.session_state.user = data.get("user")
    st.session_state.page = "Home"


def clear_authenticated():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.chat_messages = []
    st.session_state.page = "Home"
    st.session_state.auth_mode = "login"


def authenticated():
    return bool(
        st.session_state.token
        and st.session_state.user
    )


def current_user():
    return st.session_state.user or {}


def user_display_name():
    user = current_user()
    return user.get("full_name", "User")


def user_email():
    user = current_user()
    return user.get("email", "")


def organization_id():
    user = current_user()
    return user.get("tenant_id", "")


# ------------------------------------------------------------
# SHARED UI COMPONENTS
# ------------------------------------------------------------

def brand():
    st.markdown("""
    <div class="eg-brand">
        <div class="eg-logo">◈</div>
        <div>
            <div class="eg-name">Enterprise GraphRAG</div>
            <div class="eg-tagline">Knowledge Intelligence Platform</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def page_header(title, subtitle=None):
    st.markdown(f"# {title}")

    if subtitle:
        st.markdown(
            f'<p class="eg-muted">{subtitle}</p>',
            unsafe_allow_html=True,
        )


def card_start():
    st.markdown(
        '<div class="eg-card">',
        unsafe_allow_html=True,
    )


def card_end():
    st.markdown(
        '</div>',
        unsafe_allow_html=True,
    )


def section_label(text):
    st.markdown(
        f'<div class="eg-section">{text}</div>',
        unsafe_allow_html=True,
    )


def timestamp_now():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )


# ------------------------------------------------------------
# PART 1 PLACEHOLDER ROUTER
# Later parts expand this router with real product modules.
# ------------------------------------------------------------

def run_application():

    if not authenticated():
        return

    st.title("Enterprise GraphRAG")
    st.caption(
        "Your organization's knowledge intelligence environment."
    )

    st.info(
        "The core application engine is initialized. "
        "The product workspace will be built through "
        "Parts 2–20."
    )

    st.write("Signed in:", user_display_name())

    st.write("Organization:", organization_id())


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------

if authenticated():
    run_application()
    
# ============================================================
# PART 2/20 — AUTHENTICATION UI
# ============================================================

def login_screen():

    left, center, right = st.columns([1, 1.15, 1])

    with center:

        st.markdown("""
        <div style="text-align:center;padding:30px 0 20px">
            <div style="font-size:44px;color:#2563eb">◈</div>
            <h1 style="font-size:30px">Welcome back</h1>
            <p style="color:#718096">
                Search and discover your organization's knowledge.
            </p>
        </div>
        """, unsafe_allow_html=True)

        card_start()

        with st.form("eg_login"):

            email = st.text_input(
                "Work email",
                placeholder="name@company.com",
            )

            password = st.text_input(
                "Password",
                type="password",
            )

            submitted = st.form_submit_button(
                "Sign in",
                type="primary",
                use_container_width=True,
            )

            if submitted:

                if not email.strip() or not password:
                    st.error("Enter your email and password.")

                else:

                    with st.spinner("Authenticating..."):

                        status, data = api_post(
                            "/api/v1/auth/login",
                            {
                                "email": email.strip(),
                                "password": password,
                            },
                            authenticated=False,
                        )

                    if status == 200 and data.get("access_token"):

                        set_authenticated(data)
                        st.rerun()

                    else:

                        st.error(
                            data.get(
                                "detail",
                                "Authentication failed."
                            )
                        )

        card_end()

        st.write("")

        if st.button(
            "Create a new organization",
            use_container_width=True,
        ):
            st.session_state.auth_mode = "register"
            st.rerun()


def registration_screen():

    left, center, right = st.columns([1, 1.15, 1])

    with center:

        st.markdown("""
        <div style="text-align:center;padding:25px 0 20px">
            <div style="font-size:44px;color:#2563eb">◈</div>
            <h1 style="font-size:29px">Create your workspace</h1>
            <p style="color:#718096">
                Bring your organization's knowledge together.
            </p>
        </div>
        """, unsafe_allow_html=True)

        card_start()

        with st.form("eg_register"):

            org = st.text_input(
                "Organization name",
                placeholder="Organization",
            )

            name = st.text_input(
                "Full name",
                placeholder="Your name",
            )

            email = st.text_input(
                "Work email",
                placeholder="name@company.com",
            )

            password = st.text_input(
                "Password",
                type="password",
                help="Use at least 12 characters.",
            )

            confirmation = st.text_input(
                "Confirm password",
                type="password",
            )

            submitted = st.form_submit_button(
                "Create workspace",
                type="primary",
                use_container_width=True,
            )

            if submitted:

                if not all([
                    org.strip(),
                    name.strip(),
                    email.strip(),
                    password,
                    confirmation,
                ]):
                    st.warning("Complete all fields.")

                elif len(password) < 12:
                    st.warning(
                        "Use a password of at least 12 characters."
                    )

                elif password != confirmation:
                    st.warning("Passwords do not match.")

                else:

                    payload = {
                        "organization_name": org.strip(),
                        "full_name": name.strip(),
                        "email": email.strip(),
                        "password": password,
                    }

                    with st.spinner(
                        "Creating organization..."
                    ):

                        status, data = api_post(
                            "/api/v1/auth/register",
                            payload,
                            authenticated=False,
                        )

                    if status == 200 and data.get("access_token"):

                        set_authenticated(data)
                        st.rerun()

                    else:

                        st.error(
                            data.get(
                                "detail",
                                "Workspace creation failed."
                            )
                        )

        card_end()

        st.write("")

        if st.button(
            "Return to sign in",
            use_container_width=True,
        ):
            st.session_state.auth_mode = "login"
            st.rerun()


def authentication_router():

    if authenticated():
        return True

    if st.session_state.auth_mode == "register":
        registration_screen()

    else:
        login_screen()

    return False


# ------------------------------------------------------------
# REPLACE PART 1 ENTRY POINT WITH THIS AT THE VERY END
# ------------------------------------------------------------

if authentication_router():
    run_application()
    
# ============================================================
# PART 3/20 — ENTERPRISE PRODUCT SHELL
# ============================================================

PRODUCT_NAVIGATION = {
    "KNOWLEDGE": [
        ("Home", "⌂"),
        ("Search", "⌕"),
        ("Assistant", "✧"),
        ("Discover", "◉"),
    ],
    "CONTENT": [
        ("Documents", "▤"),
        ("Knowledge Graph", "◈"),
        ("Spaces", "▧"),
    ],
    "ORGANIZATION": [
        ("People", "♙"),
        ("Teams", "♧"),
    ],
    "MANAGEMENT": [
        ("Sources", "⇄"),
        ("Activity", "◷"),
        ("Settings", "⚙"),
    ],
}


def navigation_item(label, symbol):

    selected = st.session_state.page == label

    if selected:
        button_label = f"{symbol}  {label}"
    else:
        button_label = f"{symbol}  {label}"

    if st.button(
        button_label,
        key=f"nav_{label}",
        use_container_width=True,
        type="primary" if selected else "secondary",
    ):
        st.session_state.page = label
        st.rerun()


def render_sidebar():

    with st.sidebar:

        brand()

        st.markdown(
            '<div class="eg-section">Workspace</div>',
            unsafe_allow_html=True,
        )

        user = current_user()

        st.markdown(
            f"""
            <div style="
                border:1px solid #e8ebf0;
                border-radius:12px;
                padding:11px;
                margin-bottom:15px;
            ">
                <div style="font-weight:650;font-size:13px">
                    {user.get('organization_name', 'Workspace')}
                </div>
                <div style="font-size:11px;color:#7b8492">
                    Enterprise knowledge
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for section, items in PRODUCT_NAVIGATION.items():

            section_label(section)

            for label, symbol in items:
                navigation_item(label, symbol)

        st.markdown(
            '<div class="eg-divider"></div>',
            unsafe_allow_html=True,
        )

        user = current_user()

        st.markdown(
            f"""
            <div style="padding:8px 3px">
                <div style="font-weight:600;font-size:13px">
                    {user.get('full_name', 'User')}
                </div>
                <div style="font-size:11px;color:#718096">
                    {user.get('email', '')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Sign out",
            use_container_width=True,
            key="eg_signout",
        ):
            clear_authenticated()
            st.rerun()


def render_topbar():

    c1, c2 = st.columns([5, 1])

    with c1:
        st.markdown(
            f"""
            <div style="
                font-size:12px;
                color:#8a94a3;
                padding-top:5px;
            ">
                Enterprise GraphRAG
                <span style="padding:0 8px">/</span>
                <strong style="color:#283447">
                    {st.session_state.page}
                </strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div style="
                text-align:right;
                font-size:12px;
                color:#718096;
                padding-top:5px;
            ">
                Knowledge workspace
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_workspace_shell():

    render_sidebar()

    render_topbar()


# ------------------------------------------------------------
# REPLACE run_application() FROM PART 1 WITH THIS VERSION
# ------------------------------------------------------------

def run_application():

    render_workspace_shell()

    page = st.session_state.page

    if page == "Home":
        st.title("Home")

    elif page == "Search":
        st.title("Search")

    elif page == "Assistant":
        st.title("Assistant")

    elif page == "Discover":
        st.title("Discover")

    elif page == "Documents":
        st.title("Documents")

    elif page == "Knowledge Graph":
        st.title("Knowledge Graph")

    elif page == "Spaces":
        st.title("Spaces")

    elif page == "People":
        st.title("People")

    elif page == "Teams":
        st.title("Teams")

    elif page == "Sources":
        st.title("Sources")

    elif page == "Activity":
        st.title("Activity")

    elif page == "Settings":
        st.title("Settings")

    else:
        st.session_state.page = "Home"
        st.rerun()
        
# ============================================================
# PART 4/20 — KNOWLEDGE INTELLIGENCE HOME
# ============================================================

def render_home():

    page_header(
        "Good to see you, " + user_display_name(),
        "Discover, search and connect knowledge across your organization.",
    )

    st.markdown("")

    # Main enterprise search entry point
    st.markdown("""
    <div style="
        background:white;
        border:1px solid #e4e9f0;
        border-radius:18px;
        padding:22px;
        box-shadow:0 5px 25px rgba(15,23,42,.035);
    ">
        <div style="
            font-size:17px;
            font-weight:700;
            margin-bottom:5px;
        ">
            What are you looking for?
        </div>

        <div style="
            font-size:12px;
            color:#7b8492;
            margin-bottom:15px;
        ">
            Search your organization's knowledge or ask a question.
        </div>
    </div>
    """, unsafe_allow_html=True)

    query = st.text_input(
        "Search organizational knowledge",
        placeholder="Search documents, projects, policies, people...",
        label_visibility="collapsed",
        key="home_search",
    )

    c1, c2, c3 = st.columns([1, 1, 3])

    with c1:
        if st.button(
            "Search knowledge",
            type="primary",
            use_container_width=True,
        ):
            if query.strip():
                st.session_state.search_query = query.strip()
                st.session_state.page = "Search"
                st.rerun()

    with c2:
        if st.button(
            "Ask AI",
            use_container_width=True,
        ):
            if query.strip():
                st.session_state.chat_messages.append({
                    "role": "user",
                    "content": query.strip(),
                })
            st.session_state.page = "Assistant"
            st.rerun()

    st.markdown("")

    # Knowledge overview
    st.subheader("Your knowledge workspace")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Documents", "—", help="Connected document collection")
    m2.metric("Knowledge sources", "—", help="Connected source systems")
    m3.metric("Knowledge connections", "—", help="Graph relationships")
    m4.metric("People", "—", help="Workspace members")

    st.caption(
        "Metrics will be populated from backend endpoints "
        "as those integrations are implemented."
    )

    st.markdown("")

    # AI Assistant entry card
    left, right = st.columns([1.5, 1])

    with left:

        card_start()

        st.markdown(
            '<div class="eg-card-title">✧ Knowledge Assistant</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="eg-card-subtitle">
                Ask questions about your organization's knowledge
                and find answers across information sources.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("")

        if st.button(
            "Start a conversation",
            type="primary",
            key="home_start_assistant",
        ):
            st.session_state.page = "Assistant"
            st.rerun()

        card_end()

    with right:

        card_start()

        st.markdown(
            '<div class="eg-card-title">◈ Knowledge Graph</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="eg-card-subtitle">
                Explore the connections between documents,
                concepts and organizational information.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("")

        if st.button(
            "Explore graph",
            key="home_graph",
        ):
            st.session_state.page = "Knowledge Graph"
            st.rerun()

        card_end()

    st.markdown("")

    # Discovery entry points
    st.subheader("Explore your knowledge")

    d1, d2, d3 = st.columns(3)

    with d1:
        card_start()
        st.markdown("### ▤ Documents")
        st.caption(
            "Find and review the documents in your workspace."
        )
        if st.button("Browse documents", key="home_docs"):
            st.session_state.page = "Documents"
            st.rerun()
        card_end()

    with d2:
        card_start()
        st.markdown("### ⇄ Sources")
        st.caption(
            "Explore the systems supplying organizational knowledge."
        )
        if st.button("View sources", key="home_sources"):
            st.session_state.page = "Sources"
            st.rerun()
        card_end()

    with d3:
        card_start()
        st.markdown("### ◉ Discover")
        st.caption(
            "Explore knowledge and find information related to your work."
        )
        if st.button("Discover knowledge", key="home_discover"):
            st.session_state.page = "Discover"
            st.rerun()
        card_end()


# ------------------------------------------------------------
# UPDATE THE run_application ROUTER
# Add Home to the router's page conditions.
# ------------------------------------------------------------

# Inside run_application(), replace:
# if page == "Home":
#     st.title("Home")
#
# With:
# if page == "Home":
#     render_home()

# ============================================================
# PART 5/20 — ENTERPRISE SEARCH
# ============================================================

def render_search():

    page_header(
        "Search",
        "Find information across your organization's knowledge.",
    )

    query = st.text_input(
        "Search",
        value=st.session_state.search_query,
        placeholder="Search policies, projects, documents...",
        key="enterprise_search_input",
    )

    c1, c2 = st.columns([1, 5])

    with c1:
        search_clicked = st.button(
            "Search",
            type="primary",
            use_container_width=True,
        )

    with c2:
        st.caption(
            "Search results are restricted to your organization's "
            "documents by the backend."
        )

    if search_clicked and query.strip():

        st.session_state.search_query = query.strip()

        with st.spinner("Searching your knowledge..."):

            status, data = api_post(
                "/api/v1/search",
                {
                    "query": query.strip(),
                    "limit": 20,
                },
            )

        if status == 200:

            st.session_state.search_results = data

        else:

            st.session_state.search_results = None

            st.error(
                data.get(
                    "detail",
                    "Search request failed."
                )
            )

    results = st.session_state.get(
        "search_results"
    )

    if not results:
        st.markdown("")
        st.info(
            "Enter a query to search your organizational documents."
        )
        return

    st.markdown("")

    st.markdown(
        f"**{results.get('count', 0)} results** "
        f"for `{results.get('query', '')}`"
    )

    st.caption(
        f"Search mode: {results.get('search_type', 'unknown')}"
    )

    documents = results.get("results", [])

    if not documents:

        st.warning("No matching documents were found.")

        return

    for index, document in enumerate(documents):

        card_start()

        st.markdown(
            f"### ▤ {document.get('filename', 'Untitled document')}"
        )

        st.caption(
            f"Source: {document.get('source', 'Unknown')}"
        )

        snippet = document.get("snippet", "")

        if snippet:

            st.markdown(
                snippet[:500]
            )

        st.markdown("")

        if st.button(
            "Open document",
            key=f"search_open_{index}",
        ):

            st.session_state.selected_document = (
                document.get("document_id")
            )

            st.session_state.page = "Documents"

            st.rerun()

        card_end()

        st.markdown("")


# In run_application(), replace the Search branch with:
#
# elif page == "Search":
#     render_search()

# ============================================================
# PART 6/20 — DOCUMENT LIBRARY
# ============================================================

def upload_file_to_backend(uploaded_file):

    headers = {}

    if st.session_state.token:
        headers["Authorization"] = (
            f"Bearer {st.session_state.token}"
        )

    try:

        response = requests.post(
            f"{API_BASE}/api/v1/documents/upload",
            headers=headers,
            files={
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type or "application/octet-stream",
                )
            },
            timeout=120,
        )

        try:
            data = response.json()
        except ValueError:
            data = {"detail": response.text}

        return response.status_code, data

    except requests.RequestException as exc:

        return 0, {"detail": str(exc)}


def load_documents():

    status, data = api_get(
        "/api/v1/documents?limit=100"
    )

    if status == 200 and isinstance(data, list):
        return data

    return None


def render_documents():

    page_header(
        "Documents",
        "Manage and explore your organization's knowledge documents.",
    )

    tab_library, tab_upload = st.tabs([
        "Library",
        "Upload documents",
    ])

    with tab_upload:

        st.subheader("Add knowledge to your workspace")

        st.caption(
            "Upload documents to extract their text and index "
            "them in the knowledge graph."
        )

        files = st.file_uploader(
            "Select files",
            accept_multiple_files=True,
            key="eg_doc_upload",
        )

        if files:

            if st.button(
                "Upload and index",
                type="primary",
            ):

                for file in files:

                    with st.spinner(
                        f"Processing {file.name}..."
                    ):

                        status, data = upload_file_to_backend(
                            file
                        )

                    if status == 200:

                        st.success(
                            f"{file.name} indexed successfully."
                        )

                        st.json(data)

                    else:

                        st.error(
                            f"{file.name}: "
                            f"{data.get('detail', 'Upload failed')}"
                        )

    with tab_library:

        if st.button(
            "Refresh library",
            key="eg_refresh_documents",
        ):
            st.rerun()

        documents = load_documents()

        if documents is None:

            st.error(
                "Could not load documents from your backend."
            )

            return

        st.markdown(
            f"**{len(documents)} documents**"
        )

        if not documents:

            st.info(
                "Your document library is empty. "
                "Upload documents to begin."
            )

            return

        for document in documents:

            card_start()

            st.markdown(
                f"### ▤ {document.get('filename', 'Document')}"
            )

            st.caption(
                f"Source: {document.get('source', 'Unknown')}"
            )

            created_at = document.get("created_at")

            if created_at:
                st.caption(f"Created: {created_at}")

            document_id = document.get("id")

            if st.button(
                "View document",
                key=f"doc_view_{document_id}",
            ):

                st.session_state.selected_document = document_id

                st.session_state.page = "Document Viewer"

                st.rerun()

            card_end()


# Add "Document Viewer" to navigation in Part 3
# under CONTENT:
# ("Document Viewer", "▣")
#
# In run_application(), add:
#
# elif page == "Documents":
#     render_documents()

# ============================================================
# PART 7/20 — DOCUMENT VIEWER
# ============================================================

def render_document_viewer():

    document_id = st.session_state.get(
        "selected_document"
    )

    if not document_id:

        st.warning("Select a document from the library first.")

        if st.button("Return to documents"):
            st.session_state.page = "Documents"
            st.rerun()

        return

    status, data = api_get(
        f"/api/v1/documents/{document_id}"
    )

    if status != 200:

        st.error(
            data.get(
                "detail",
                "Unable to retrieve document."
            )
        )

        return

    if st.button("← Back to documents"):
        st.session_state.page = "Documents"
        st.rerun()

    st.markdown("")

    st.title(data.get("filename", "Document"))

    st.caption(
        f"Source: {data.get('source', 'Unknown')}"
    )

    st.caption(
        f"Document ID: {data.get('id', '')}"
    )

    st.divider()

    text_content = data.get("text", "")

    if not text_content:

        st.info("This document has no extracted text.")

        return

    st.markdown("### Document content")

    st.text_area(
        "Extracted text",
        value=text_content,
        height=600,
        label_visibility="collapsed",
        disabled=True,
    )


# Add this branch to the application router:
#
# elif page == "Document Viewer":
#     render_document_viewer()

# ============================================================
# PART 8/20 — AI KNOWLEDGE ASSISTANT INTERFACE
# ============================================================

def render_assistant():

    page_header(
        "Knowledge Assistant",
        "Ask questions about your organization's information.",
    )

    st.markdown("""
    <div class="eg-card">
        <div class="eg-card-title">
            ✧ Ask your organization’s knowledge
        </div>
        <div class="eg-card-subtitle">
            The assistant interface is being connected to
            the retrieval and answer-generation service.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    st.warning(
        "The current backend has document search but does not "
        "yet expose a dedicated AI chat endpoint. This interface "
        "will not fabricate answers."
    )

    if not st.session_state.chat_messages:

        st.markdown("### Try asking")

        suggestions = [
            "What policies are available?",
            "Find documents about our projects.",
            "What information is in our document library?",
        ]

        for i, suggestion in enumerate(suggestions):

            if st.button(
                suggestion,
                key=f"assistant_suggestion_{i}",
                use_container_width=True,
            ):

                st.session_state.chat_messages.append({
                    "role": "user",
                    "content": suggestion,
                })

                st.session_state.page = "Search"

                st.session_state.search_query = suggestion

                st.rerun()

    for message in st.session_state.chat_messages:

        with st.chat_message(message["role"]):

            st.write(message["content"])

    prompt = st.chat_input(
        "Ask a question about your organization..."
    )

    if prompt:

        st.session_state.chat_messages.append({
            "role": "user",
            "content": prompt,
        })

        st.session_state.search_query = prompt

        st.session_state.page = "Search"

        st.rerun()


# Router addition:
#
# elif page == "Assistant":
#     render_assistant()

# ============================================================
# PART 9/20 — KNOWLEDGE GRAPH LIBRARY
# ============================================================

def render_knowledge_graph():

    page_header(
        "Knowledge Graph",
        "Explore documents indexed in your knowledge graph.",
    )

    status, data = api_get(
        "/api/v1/graph/documents"
    )

    if status != 200:

        st.error(
            data.get(
                "detail",
                "Graph service could not be reached."
            )
        )

        return

    nodes = data.get("nodes", [])

    st.markdown("")

    a, b = st.columns(2)

    a.metric("Graph documents", len(nodes))

    b.metric(
        "Indexed chunks",
        sum(
            int(node.get("chunk_count", 0) or 0)
            for node in nodes
        ),
    )

    st.markdown("")

    if not nodes:

        st.info(
            "No documents are currently available in the graph."
        )

        return

    st.subheader("Indexed knowledge")

    for node in nodes:

        card_start()

        st.markdown(
            f"### ◈ {node.get('filename', 'Document')}"
        )

        st.caption(
            f"Document ID: {node.get('id', '')}"
        )

        st.caption(
            f"Knowledge chunks: {node.get('chunk_count', 0)}"
        )

        if st.button(
            "Explore document",
            key=f"graph_explore_{node.get('id')}",
        ):

            st.session_state.selected_document = node.get("id")

            st.session_state.page = "Graph Explorer"

            st.rerun()

        card_end()

        st.markdown("")


# Router addition:
#
# elif page == "Knowledge Graph":
#     render_knowledge_graph()

# ============================================================
# PART 10/20 — GRAPH DOCUMENT EXPLORER
# ============================================================

def render_graph_explorer():

    document_id = st.session_state.get(
        "selected_document"
    )

    if not document_id:

        st.info("Choose a graph document to explore.")

        if st.button("Return to graph"):
            st.session_state.page = "Knowledge Graph"
            st.rerun()

        return

    if st.button("← Back to knowledge graph"):
        st.session_state.page = "Knowledge Graph"
        st.rerun()

    status, data = api_get(
        f"/api/v1/graph/explore/{document_id}"
    )

    if status != 200:

        st.error(
            data.get(
                "detail",
                "Graph exploration is currently unavailable."
            )
        )

        st.caption(
            "The backend graph-exploration route needs "
            "to be corrected and tested."
        )

        return

    page_header(
        data.get("filename", "Graph Explorer"),
        "Explore the document's indexed knowledge chunks.",
    )

    chunks = data.get("chunks", [])

    st.metric("Chunks", len(chunks))

    if not chunks:

        st.info("No chunks are available.")

        return

    for chunk in chunks:

        card_start()

        st.markdown(
            f"**Chunk {chunk.get('chunk_index', 0)}**"
        )

        st.write(chunk.get("text", ""))

        card_end()

        st.markdown("")


# Router addition:
#
# elif page == "Graph Explorer":
#     render_graph_explorer()

# ============================================================
# PART 11/20 — KNOWLEDGE DISCOVERY
# ============================================================

def render_discover():

    page_header(
        "Discover",
        "Explore information connected to your organization's knowledge.",
    )

    st.markdown("### Explore by knowledge")

    query = st.text_input(
        "Discovery search",
        placeholder="Explore a topic, project, concept or document...",
        key="discover_query",
    )

    if st.button("Explore knowledge", type="primary"):

        if query.strip():

            st.session_state.search_query = query.strip()
            st.session_state.page = "Search"
            st.rerun()

    st.divider()

    st.subheader("Knowledge exploration")

    col1, col2 = st.columns(2)

    with col1:
        card_start()
        st.markdown("### ◈ Connected knowledge")
        st.caption(
            "Explore indexed documents and relationships "
            "within the organization's knowledge graph."
        )
        if st.button("Open graph", key="discover_graph"):
            st.session_state.page = "Knowledge Graph"
            st.rerun()
        card_end()

    with col2:
        card_start()
        st.markdown("### ▤ Document collections")
        st.caption(
            "Browse the documents available to your workspace."
        )
        if st.button("Browse documents", key="discover_docs"):
            st.session_state.page = "Documents"
            st.rerun()
        card_end()

    st.subheader("Recently indexed knowledge")

    status, data = api_get("/api/v1/graph/documents")

    if status != 200:
        st.warning("Knowledge discovery data is unavailable.")
        return

    nodes = data.get("nodes", [])

    if not nodes:
        st.info("No indexed knowledge is available yet.")
        return

    for node in nodes[:10]:

        card_start()

        st.markdown(
            f"**{node.get('filename', 'Document')}**"
        )

        st.caption(
            f"{node.get('chunk_count', 0)} knowledge chunks"
        )

        if st.button(
            "Explore",
            key=f"discover_node_{node.get('id')}",
        ):
            st.session_state.selected_document = node.get("id")
            st.session_state.page = "Graph Explorer"
            st.rerun()

        card_end()
    
# ============================================================
# PART 12/20 — KNOWLEDGE SOURCES
# ============================================================

SUPPORTED_SOURCE_TYPES = [
    "Manual Upload",
    "Google Drive",
    "Microsoft SharePoint",
    "OneDrive",
    "Notion",
    "Slack",
    "Confluence",
    "Website",
    "Other",
]


def render_sources():

    page_header(
        "Knowledge Sources",
        "Manage the systems and content supplying your knowledge.",
    )

    st.subheader("Source overview")

    st.caption(
        "The current backend supports content ingestion. "
        "External OAuth integrations and automated synchronization "
        "must be implemented separately."
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Available source types", len(SUPPORTED_SOURCE_TYPES))
    c2.metric("OAuth integrations", "Not implemented")
    c3.metric("Automated synchronization", "Not implemented")

    st.divider()

    st.subheader("Available source types")

    for source in SUPPORTED_SOURCE_TYPES:

        card_start()

        st.markdown(f"**{source}**")

        if source == "Manual Upload":
            st.caption("Available through the document upload endpoint.")
            if st.button(
                "Upload documents",
                key="source_upload",
            ):
                st.session_state.page = "Documents"
                st.rerun()

        else:
            st.caption(
                "Connector integration is not yet configured."
            )

        card_end()
        
# ============================================================
# PART 13/20 — CONTENT INGESTION
# ============================================================

def render_connector_ingestion():

    page_header(
        "Content Ingestion",
        "Bring external knowledge into your GraphRAG workspace.",
    )

    st.info(
        "This interface uses the backend's generic connector "
        "ingestion endpoint. It submits content supplied here; "
        "it does not automatically connect to external accounts."
    )

    with st.form("connector_ingest_form"):

        source_name = st.selectbox(
            "Source",
            SUPPORTED_SOURCE_TYPES,
        )

        content_title = st.text_input(
            "Content title",
            placeholder="Document or content title",
        )

        source_reference = st.text_input(
            "Source reference",
            placeholder="Optional URL or external reference",
        )

        content = st.text_area(
            "Content",
            height=300,
            placeholder="Paste the knowledge content to ingest...",
        )

        submitted = st.form_submit_button(
            "Submit knowledge",
            type="primary",
        )

        if submitted:

            if not content_title.strip() or not content.strip():

                st.warning(
                    "A title and content are required."
                )

            else:

                payload = {
                    "source": source_name,
                    "title": content_title.strip(),
                    "content": content.strip(),
                    "reference": source_reference.strip(),
                }

                with st.spinner("Submitting content..."):

                    status, result = api_post(
                        "/api/v1/connectors/ingest",
                        payload,
                    )

                if status in (200, 201, 202):

                    st.success("Content submitted.")

                    st.json(result)

                else:

                    st.error(
                        result.get(
                            "detail",
                            "Content ingestion failed."
                        )
                    )
                    
# ============================================================
# PART 14/20 — SPACES
# ============================================================

def render_spaces():

    page_header(
        "Spaces",
        "Organize knowledge around projects, teams and topics.",
    )

    st.info(
        "Spaces interface established. Persistent spaces, "
        "membership, and document assignment require a Spaces "
        "backend model and API."
    )

    st.subheader("Create a knowledge space")

    with st.form("create_space_form"):

        space_name = st.text_input(
            "Space name",
            placeholder="Research, Product, Operations...",
        )

        description = st.text_area(
            "Description",
            placeholder="What knowledge belongs in this space?",
        )

        visibility = st.selectbox(
            "Visibility",
            ["Organization", "Private"],
        )

        submit = st.form_submit_button(
            "Prepare space",
            type="primary",
        )

        if submit:

            if not space_name.strip():

                st.warning("Enter a space name.")

            else:

                st.warning(
                    "Space information was entered, but it is "
                    "not saved yet because the backend Spaces "
                    "API is not implemented."
                )

                st.write({
                    "name": space_name.strip(),
                    "description": description.strip(),
                    "visibility": visibility,
                })

    st.divider()

    st.subheader("Organize knowledge")

    c1, c2 = st.columns(2)

    with c1:

        card_start()

        st.markdown("### Projects")

        st.caption(
            "Group documents and knowledge by project."
        )

        if st.button("Open documents", key="spaces_project_docs"):
            st.session_state.page = "Documents"
            st.rerun()

        card_end()

    with c2:

        card_start()

        st.markdown("### Departments")

        st.caption(
            "Organize knowledge around organizational departments."
        )

        if st.button("Explore teams", key="spaces_teams"):
            st.session_state.page = "Teams"
            st.rerun()

        card_end()
        
# ============================================================
# PART 15/20 — PEOPLE
# ============================================================

def render_people():

    page_header(
        "People",
        "Explore the people in your knowledge workspace.",
    )

    status, data = api_get("/api/v1/team")

    if status != 200:

        st.error(
            data.get(
                "detail",
                "Unable to retrieve organization members."
            )
        )

        return

    members = data if isinstance(data, list) else data.get(
        "members",
        data.get("users", []),
    )

    st.markdown(
        f"**{len(members)} members**"
    )

    search = st.text_input(
        "Find people",
        placeholder="Search by name or email...",
        key="people_search",
    )

    filtered = []

    for member in members:

        name = member.get("full_name", "")
        email = member.get("email", "")

        searchable = f"{name} {email}".lower()

        if search.lower() in searchable:
            filtered.append(member)

    if not filtered:

        st.info("No matching members found.")

        return

    for member in filtered:

        card_start()

        name = member.get("full_name", "Member")
        email = member.get("email", "")
        role = member.get("role", "Member")

        st.markdown(f"### {name}")

        st.caption(email)

        st.markdown(
            f'<span class="eg-pill">{role}</span>',
            unsafe_allow_html=True,
        )

        card_end()

        st.markdown("")
        
# ============================================================
# PART 16/20 — TEAMS
# ============================================================

def render_teams():

    page_header(
        "Teams",
        "Understand the people working across your organization.",
    )

    status, data = api_get("/api/v1/team")

    if status != 200:

        st.error(
            data.get(
                "detail",
                "Team information is unavailable."
            )
        )

        return

    members = data if isinstance(data, list) else data.get(
        "members",
        data.get("users", []),
    )

    if not members:

        st.info("No team members have been returned.")

        return

    roles = {}

    for member in members:

        role = member.get("role", "Member")

        roles[role] = roles.get(role, 0) + 1

    st.subheader("Organization overview")

    c1, c2 = st.columns(2)

    c1.metric("Members", len(members))

    c2.metric("Roles", len(roles))

    st.divider()

    st.subheader("Organization roles")

    for role, count in roles.items():

        card_start()

        st.markdown(f"**{role}**")

        st.caption(f"{count} member(s)")

        card_end()

    st.divider()

    st.subheader("Team members")

    for member in members:

        card_start()

        st.markdown(
            f"**{member.get('full_name', 'Member')}**"
        )

        st.caption(
            member.get("email", "")
        )

        card_end()
        
                    



        
    
    
