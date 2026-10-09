# ============================================================================
# app.py - UNIFIED STREAMLIT ENTERPRISE INTELLIGENCE FRONTEND
# Glean-Grade Decoupled Consumer for Render Backend Engine
# ============================================================================

import os
import streamlit as st
import requests

# ----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & SESSION STATE INITIALIZATION
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Enterprise Intelligence Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Render Backend URL
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
# 2. SIDEBAR & AUTHENTICATION MANAGEMENT
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("🛡️ Enterprise Portal")
    st.caption("Decoupled Frontend Engine")

    # Backend Connectivity Health Monitor
    try:
        health_resp = requests.get(f"{BACKEND_URL}/health", timeout=3)
        if health_resp.status_code == 200:
            st.success("Backend: ONLINE 🟢")
        else:
            st.warning(f"Backend Status: {health_resp.status_code}")
    except Exception:
        st.error("Backend: OFFLINE 🔴")

    st.divider()

    if not st.session_state.access_token:
        st.subheader("Sign In")
        auth_mode = st.radio("Authentication Method", ["Work Email", "Google OAuth"], index=0)

        if auth_mode == "Work Email":
            with st.form("login_form"):
                email = st.text_input("Work Email", value="alex@enterprise-corp.com")
                password = st.text_input("Password", type="password", value="securepass123")
                submit = st.form_submit_button("Sign In")

                if submit:
                    try:
                        res = requests.post(
                            f"{BACKEND_URL}/api/v1/auth/login",
                            json={"email": email, "password": password},
                            timeout=10
                        )
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state.access_token = data["access_token"]
                            st.session_state.user_info = data
                            st.success("Authenticated successfully!")
                            st.rerun()
                        else:
                            st.error(f"Authentication failed: {res.json().get('detail', 'Error')}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")

        elif auth_mode == "Google OAuth":
            if st.button("Sign In with Google Account"):
                try:
                    res = requests.post(
                        f"{BACKEND_URL}/api/v1/auth/google",
                        json={"id_token": "mock_google_identity_token_2026"},
                        timeout=10
                    )
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.access_token = data["access_token"]
                        st.session_state.user_info = data
                        st.success("Authenticated via Google!")
                        st.rerun()
                    else:
                        st.error("Google authentication failed.")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
    else:
        st.write(f"**User ID:** `{st.session_state.user_info.get('user_id')}`")
        st.write(f"**Tenant ID:** `{st.session_state.user_info.get('tenant_id')}`")
        st.write(f"**Subscription Tier:** `{st.session_state.user_info.get('tier')}`")

        if st.button("Sign Out"):
            st.session_state.access_token = None
            st.session_state.user_info = None
            st.rerun()

# ----------------------------------------------------------------------------
# 3. MAIN INTERFACE & TAB NAVIGATION
# ----------------------------------------------------------------------------
st.title("Enterprise Context & Intelligence Platform")

if not st.session_state.access_token:
    st.info("👈 Please sign in using the sidebar to access unified search, knowledge graphs, and workspace tools.")
    st.stop()

tab_search, tab_workspaces, tab_fastmcp, tab_governance = st.tabs([
    "🔍 Unified Search & AI Synthesis",
    "🏢 360° Deep Workspaces",
    "⚡ FastMCP Tool Protocols",
    "🔒 Governance & Connectors"
])

# ----------------------------------------------------------------------------
# TAB 1: UNIFIED SEARCH & AI SYNTHESIS
# ----------------------------------------------------------------------------
with tab_search:
    col_query, col_button = st.columns([4, 1])
    with col_query:
        query_input = st.text_input(
            "Search enterprise data across Drive, Slack, Jira & Knowledge Graph:",
            value="OAuth2 Bearer token validation policy",
            label_visibility="collapsed"
        )
    with col_button:
        execute_search = st.button("Search", use_container_width=True)

    if execute_search and query_input:
        with st.spinner("Executing hybrid RAG search and knowledge graph traversal..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/search",
                    headers=get_auth_headers(),
                    json={"query": query_input, "page": 1, "page_size": 10},
                    timeout=12
                )
                if response.status_code == 200:
                    search_data = response.json()
                    
                    # AI Synthesis Card
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

                    # Search Results List
                    st.markdown(f"### 📄 Matching Results ({search_data.get('total_results', 0)})")
                    for item in search_data.get("results", []):
                        with st.container(border=True):
                            c1, c2 = st.columns([5, 1])
                            with c1:
                                st.subheader(f"[{item['app'].upper()}] {item['title']}")
                                st.write(item["snippet"])
                                st.caption(f"Author: **{item['author_name']}** | Last Updated: {item['last_updated']} | Relevance Score: {item['score']}")
                            with c2:
                                st.link_button("Open Resource", item["url"])
                else:
                    st.error(f"Search request failed: {response.text}")
            except Exception as e:
                st.error(f"Failed to reach search endpoint: {str(e)}")

# ----------------------------------------------------------------------------
# TAB 2: 360° DEEP WORKSPACES
# ----------------------------------------------------------------------------
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
                ws = res.json()
                st.success(f"Workspace Loaded: {ws['title']}")
                st.json(ws)
            else:
                st.error("Failed to load workspace data.")
        except Exception as e:
            st.error(f"Error fetching workspace: {str(e)}")

# ----------------------------------------------------------------------------
# TAB 3: FASTMCP TOOL PROTOCOLS
# ----------------------------------------------------------------------------
with tab_fastmcp:
    st.subheader("Execute FastMCP Context Tools")
    tool_choice = st.selectbox(
        "Select Protocol Tool",
        ["inspect_tenant_security_posture", "traverse_entity_graph", "summarize_workspace_documents"]
    )

    if tool_choice == "inspect_tenant_security_posture":
        target_tenant = st.text_input("Tenant ID", value=st.session_state.user_info.get("tenant_id"))
        args = {"tenant_id": target_tenant}
    elif tool_choice == "traverse_entity_graph":
        target_tenant = st.text_input("Tenant ID", value=st.session_state.user_info.get("tenant_id"))
        root = st.text_input("Root Entity", value="Account: Acme Corp")
        depth = st.slider("Traversal Depth", 1, 4, 2)
        args = {"tenant_id": target_tenant, "root_entity": root, "depth": depth}
    else:
        target_tenant = st.text_input("Tenant ID", value=st.session_state.user_info.get("tenant_id"))
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

# ----------------------------------------------------------------------------
# TAB 4: GOVERNANCE & CONNECTORS
# ----------------------------------------------------------------------------
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
        
