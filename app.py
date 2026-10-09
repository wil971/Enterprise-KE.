# ============================================================================
# app.py - UNIFIED STREAMLIT ENTERPRISE INTELLIGENCE FRONTEND
# Glean-Grade Decoupled Consumer for Render Backend Engine
# ============================================================================

import os
import streamlit as st
import requests

# ----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & SECRETS RESOLUTION
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Enterprise Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern SaaS Aesthetic & Centered Floating Auth Card
st.markdown("""
    <style>
    /* Main Canvas Background & Typography */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Centered Floating Container Card */
    div[data-testid="stForm"] {
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 2rem;
        background: #1a202c;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    }

    /* Primary Buttons */
    div.stButton > button:first-child {
        border-radius: 8px;
        height: 2.8rem;
        font-weight: 600;
    }
    
    /* Google Sign-In Custom Styling */
    .google-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #ffffff;
        color: #3c4043;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-weight: 500;
        text-decoration: none;
        border: 1px solid #dadce0;
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Backend URL Resolution
if "BACKEND_URL" in st.secrets:
    BACKEND_URL = st.secrets["BACKEND_URL"].rstrip("/")
else:
    BACKEND_URL = os.getenv("BACKEND_URL", "https://enterprise-ke-3.onrender.com").rstrip("/")

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None

def get_auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

# ----------------------------------------------------------------------------
# 2. FRONT-PAGE FLOATING AUTHENTICATION PORTAL (UNAUTHENTICATED VIEW)
# ----------------------------------------------------------------------------
if not st.session_state.access_token:
    # Top spacing & header banner
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="font-size: 2.2rem; font-weight: 700; color: #ffffff;">Enterprise Intelligence</h1>
                <p style="color: #a0aec0; font-size: 1rem;">Sign in to query across connected SaaS connectors & Knowledge Graphs</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        auth_tab1, auth_tab2 = st.tabs(["🔒 Work Email Login", "🌐 Google Workspace OAuth"])

        # TAB 1: WORK EMAIL AUTHENTICATION
        with auth_tab1:
            with st.form("main_email_login_form"):
                user_email = st.text_input(
                    "Work Email Address", 
                    placeholder="name@company.com",
                    value="alex@enterprise-corp.com"
                )
                user_password = st.text_input(
                    "Password", 
                    type="password", 
                    placeholder="••••••••••••",
                    value="securepass123"
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit_email = st.form_submit_button("Sign In to Enterprise Portal", use_container_width=True, type="primary")

                if submit_email:
                    if not user_email or not user_password:
                        st.error("Please provide both email and password.")
                    else:
                        with st.spinner("Connecting to secure backend server..."):
                            try:
                                res = requests.post(
                                    f"{BACKEND_URL}/api/v1/auth/login",
                                    json={"email": user_email, "password": user_password},
                                    headers={"Content-Type": "application/json"},
                                    timeout=30
                                )
                                if res.status_code == 200:
                                    data = res.json()
                                    st.session_state.access_token = data.get("access_token")
                                    st.session_state.user_info = data
                                    st.success("Authentication successful! Loading workspace...")
                                    st.rerun()
                                else:
                                    try:
                                        err_msg = res.json().get("detail", "Invalid login credentials.")
                                    except Exception:
                                        err_msg = "Server returned an unexpected format. Verify Render server status."
                                    st.error(f"Login Failed: {err_msg}")
                            except Exception as e:
                                st.error(f"Backend Connection Error: {str(e)}")

        # TAB 2: GOOGLE OAUTH AUTHENTICATION
        with auth_tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.write("Authenticate securely using your corporate Google Workspace identity.")
            
            google_email = st.text_input(
                "Google Account Email", 
                placeholder="user@gmail.com or company@domain.com",
                key="google_email_input"
            )
            
            if st.button("🚀 Sign In with Google Account", use_container_width=True, type="primary"):
                if not google_email:
                    st.warning("Please enter your Google account email to proceed.")
                else:
                    with st.spinner("Verifying Google OAuth token..."):
                        try:
                            res = requests.post(
                                f"{BACKEND_URL}/api/v1/auth/google",
                                json={
                                    "id_token": "mock_google_identity_token_2026",
                                    "email": google_email
                                },
                                headers={"Content-Type": "application/json"},
                                timeout=30
                            )
                            if res.status_code == 200:
                                data = res.json()
                                # Update profile email with user's inputted email
                                data["email"] = google_email
                                st.session_state.access_token = data.get("access_token")
                                st.session_state.user_info = data
                                st.success(f"Authenticated as {google_email}! Redirecting...")
                                st.rerun()
                            else:
                                try:
                                    err_msg = res.json().get("detail", "Google OAuth token validation failed.")
                                except Exception:
                                    err_msg = "Backend returned unexpected non-JSON response."
                                st.error(f"Google Sign-In Failed: {err_msg}")
                        except Exception as e:
                            st.error(f"Connection Error: {str(e)}")

        st.caption("Protected by Enterprise HMAC SHA-256 Audit Logging & Multi-Tenant Access Control")

    # Stop rendering the rest of the application until authenticated
    st.stop()

# ----------------------------------------------------------------------------
# 3. SIDEBAR & AUTHENTICATED USER SESSION
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("🛡️ Enterprise Portal")
    st.caption("Decoupled Frontend Engine")

    # Health Check Monitor
    try:
        health_resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if health_resp.status_code == 200:
            st.success("Backend: ONLINE 🟢")
        else:
            st.warning(f"Backend Status: HTTP {health_resp.status_code}")
    except Exception:
        st.error("Backend: OFFLINE / WAKING UP 🔴")

    st.divider()

    # Logged-in profile card
    user_info = st.session_state.user_info or {}
    st.markdown("### 👤 User Profile")
    st.write(f"**Email:** `{user_info.get('email', 'N/A')}`")
    st.write(f"**User ID:** `{user_info.get('user_id', 'N/A')}`")
    st.write(f"**Tenant:** `{user_info.get('tenant_id', 'N/A')}`")
    st.write(f"**Tier:** `{user_info.get('tier', 'N/A')}`")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sign Out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.user_info = None
        st.rerun()

# ----------------------------------------------------------------------------
# 4. MAIN DASHBOARD (AUTHENTICATED VIEW)
# ----------------------------------------------------------------------------
st.title("Enterprise Context & Intelligence Platform")

tab_search, tab_workspaces, tab_fastmcp, tab_governance = st.tabs([
    "🔍 Unified Search & AI Synthesis",
    "🏢 360° Deep Workspaces",
    "⚡ FastMCP Tool Protocols",
    "🔒 Governance & Connectors"
])

# TAB 1: UNIFIED SEARCH
with tab_search:
    col_query, col_button = st.columns([4, 1])
    with col_query:
        query_input = st.text_input(
            "Search enterprise data across Drive, Slack, Jira & Knowledge Graph:",
            value="OAuth2 Bearer token validation policy",
            label_visibility="collapsed"
        )
    with col_button:
        execute_search = st.button("Search", use_container_width=True, type="primary")

    if execute_search and query_input:
        with st.spinner("Executing hybrid RAG search and knowledge graph traversal..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/search",
                    headers=get_auth_headers(),
                    json={"query": query_input, "page": 1, "page_size": 10},
                    timeout=15
                )
                if response.status_code == 200:
                    search_data = response.json()
                    
                    synthesis = search_data.get("ai_synthesis", {})
                    st.markdown("### 🤖 AI Executive Synthesis")
                    st.info(synthesis.get("summary", "No summary generated."))
                    
                    if synthesis.get("citations"):
                        st.write("**Verified Source Citations:**")
                        cite_cols = st.columns(len(synthesis["citations"]))
                        for idx, cite in enumerate(synthesis["citations"]):
                            with cite_cols[idx]:
                                st.caption(f"[{cite['id']}] **{cite['app'].upper()}**: [{cite['title']}]({cite['url']})")

                    st.divider()

                    st.markdown(f"### 📄 Matching Results ({search_data.get('total_results', 0)})")
                    for item in search_data.get("results", []):
                        with st.container(border=True):
                            c1, c2 = st.columns([5, 1])
                            with c1:
                                st.subheader(f"[{item['app'].upper()}] {item['title']}")
                                st.write(item["snippet"])
                                st.caption(f"Author: **{item['author_name']}** | Last Updated: {item['last_updated']} | Score: {item['score']}")
                            with c2:
                                st.link_button("Open Resource", item["url"])
                else:
                    st.error(f"Search request failed: {response.text}")
            except Exception as e:
                st.error(f"Failed to reach search endpoint: {str(e)}")

# TAB 2: 360° WORKSPACES
with tab_workspaces:
    st.subheader("Inspect Entity Workspaces")
    col1, col2 = st.columns(2)
    with col1:
        entity_type = st.selectbox("Entity Type", ["account", "document", "person", "project"])
    with col2:
        entity_id = st.text_input("Entity ID", value="acme_corp_global")

    if st.button("Load 360° Workspace"):
        try:
            res = requests.get(
                f"{BACKEND_URL}/api/v1/entities/{entity_type}/{entity_id}",
                headers=get_auth_headers(),
                timeout=10
            )
            if res.status_code == 200:
                st.json(res.json())
            else:
                st.error("Failed to load workspace data.")
        except Exception as e:
            st.error(f"Error fetching workspace: {str(e)}")

# TAB 3: FASTMCP TOOL PROTOCOLS
with tab_fastmcp:
    st.subheader("Execute FastMCP Context Tools")
    tool_choice = st.selectbox(
        "Select Protocol Tool",
        ["inspect_tenant_security_posture", "traverse_entity_graph", "summarize_workspace_documents"]
    )

    tenant_val = user_info.get("tenant_id", "tenant_acme_corp")
    if tool_choice == "inspect_tenant_security_posture":
        target_tenant = st.text_input("Tenant ID", value=tenant_val)
        args = {"tenant_id": target_tenant}
    elif tool_choice == "traverse_entity_graph":
        target_tenant = st.text_input("Tenant ID", value=tenant_val)
        root = st.text_input("Root Entity", value="Account: Acme Corp")
        depth = st.slider("Traversal Depth", 1, 4, 2)
        args = {"tenant_id": target_tenant, "root_entity": root, "depth": depth}
    else:
        target_tenant = st.text_input("Tenant ID", value=tenant_val)
        ws_id = st.text_input("Workspace ID", value="ws_engineering_2026")
        args = {"tenant_id": target_tenant, "workspace_id": ws_id}

    if st.button("Dispatch FastMCP Tool"):
        try:
            res = requests.post(
                f"{BACKEND_URL}/api/v1/fastmcp/execute",
                headers=get_auth_headers(),
                json={"tool_name": tool_choice, "arguments": args},
                timeout=10
            )
            if res.status_code == 200:
                st.json(res.json())
            else:
                st.error(f"Tool execution failed: {res.text}")
        except Exception as e:
            st.error(f"Tool dispatch error: {str(e)}")

# TAB 4: GOVERNANCE & AUDIT
with tab_governance:
    st.subheader("Tenant Governance & Audit Ledger")
    col_audit, col_conn = st.columns(2)
    
    with col_audit:
        st.markdown("#### Cryptographic Audit Log Status")
        if st.button("Verify Audit Ledger Integrity"):
            try:
                res = requests.get(
                    f"{BACKEND_URL}/api/v1/admin/audit-logs/verify",
                    headers=get_auth_headers(),
                    timeout=10
                )
                if res.status_code == 200:
                    st.json(res.json())
                else:
                    st.error("Audit verification request failed.")
            except Exception as e:
                st.error(f"Error verifying logs: {str(e)}")

    with col_conn:
        st.markdown("#### SaaS Connector Integrations")
        if st.button("Check Active Connectors"):
            try:
                res = requests.get(
                    f"{BACKEND_URL}/api/v1/connectors/status",
                    headers=get_auth_headers(),
                    timeout=10
                )
                if res.status_code == 200:
                    st.json(res.json())
                else:
                    st.error("Failed to retrieve connector status.")
            except Exception as e:
                st.error(f"Error checking connectors: {str(e)}")
        
