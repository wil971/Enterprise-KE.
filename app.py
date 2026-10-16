# ============================================================================
# app.py - GOOGLE-ONLY ENTERPRISE FRONTEND (FULL INFRASTRUCTURE DASHBOARD)
# ============================================================================

import os
import streamlit as st
import requests
from streamlit_oauth import OAuth2Component

st.set_page_config(
    page_title="Enterprise Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Glean-Style Modern SaaS Aesthetic
st.markdown("""
    <style>
    .stApp { 
        background: radial-gradient(circle at 50% 0%, #111827 0%, #06090f 100%);
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
        color: white;
        border: none;
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
    }
    input, select {
        background-color: #0b0f19 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #1e293b !important;
    }
    </style>
""", unsafe_allow_html=True)

# Resolve Backend URL Safely
BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", "https://enterprise-ke-3.onrender.com")).rstrip("/")

# Initialize Google OAuth Component Safely with strict secret checking
if "google_oauth" in st.secrets:
    CLIENT_ID = st.secrets["google_oauth"].get("client_id", "")
    CLIENT_SECRET = st.secrets["google_oauth"].get("client_secret", "")
elif "web" in st.secrets:
    CLIENT_ID = st.secrets["web"].get("client_id", "")
    CLIENT_SECRET = st.secrets["web"].get("client_secret", "")
else:
    web_secrets = st.secrets.get("web", st.secrets.get("google_oauth", {}))
    CLIENT_ID = web_secrets.get("client_id", "")
    CLIENT_SECRET = web_secrets.get("client_secret", "")

# Exact match redirect URI matching Google Cloud Console
REDIRECT_URI = "https://enterprise-ke-hqrlscaknjikcwz5kpndrt.streamlit.app"

oauth2 = OAuth2Component(
    CLIENT_ID,
    CLIENT_SECRET,
    "https://accounts.google.com/o/oauth2/v2/auth",
    "https://oauth2.googleapis.com/token"
)

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None

def get_auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

# ============================================================================
# AUTHENTICATION PORTAL (GOOGLE ONLY - PRESERVED UNTOUCHED)
# ============================================================================
if not st.session_state.access_token:
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="font-size: 2.4rem; font-weight: 700; color: #ffffff;">Enterprise Intelligence</h1>
                <p style="color: #94a3b8; font-size: 1.05rem;">Secure Knowledge Graph & Workspace Discovery</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1.5rem; background: rgba(15, 23, 42, 0.85); padding: 2rem; border-radius: 16px; border: 1px solid rgba(59, 130, 246, 0.4);">
                <p style="color: #94a3b8; font-size: 1rem; margin-bottom: 1.5rem;">Authenticate securely using your official Google account.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        try:
            result = oauth2.authorize_button(
                name="Sign in with Google",
                icon="https://www.google.com/favicon.ico",
                redirect_uri=REDIRECT_URI,
                scope="openid email profile",
                key="google_sso_btn",
            )
            
            if result and isinstance(result, dict):
                token_data = result.get("token", result)
                id_token_val = token_data.get("id_token") or token_data.get("access_token")
                
                if id_token_val:
                    with st.spinner("Verifying Google secure token with backend..."):
                        res = requests.post(
                            f"{BACKEND_URL}/api/v1/auth/google",
                            json={"id_token": id_token_val},
                            timeout=30
                        )
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state.access_token = data.get("access_token")
                            st.session_state.user_info = data
                            st.success("Google SSO Authenticated Successfully!")
                            st.rerun()
                        else:
                            st.error(f"Authentication failed: {res.text}")
        except Exception as oauth_err:
            pass
            
    st.stop()

# ============================================================================
# MAIN APPLICATION DASHBOARD (FULL INFRASTRUCTURE INTEGRATION)
# ============================================================================
with st.sidebar:
    st.title("🛡️ Enterprise Portal")
    user_info = st.session_state.user_info or {}
    st.write(f"**Email:** `{user_info.get('email', 'N/A')}`")
    st.write(f"**Tier:** `{user_info.get('tier', 'PRO_ENTERPRISE')}`")
    
    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.user_info = None
        st.rerun()

st.title("Enterprise Context & Intelligence Platform")

# Multi-tab layout connecting directly to all main.py infrastructure endpoints
tab_search, tab_workspaces, tab_mcp, tab_governance = st.tabs([
    "🔍 Unified Search & RAG", 
    "🏢 360° Entity Workspaces", 
    "⚡ FastMCP Server Tools", 
    "🔒 Tenant Governance & Audit"
])

with tab_search:
    st.subheader("Glean-Grade Hybrid Search & Expert Mining")
    query_input = st.text_input("Search connected knowledge sources & workspace graph:", value="OAuth2 security compliance guidelines")

    col_q1, col_q2 = st.columns([3, 1])
    with col_q1:
        search_btn = st.button("Execute Intelligence Query", type="primary", use_container_width=True)
    with col_q2:
        page_size = st.selectbox("Page Size", [10, 25, 50], index=0)

    if search_btn:
        with st.spinner("Traversing knowledge graph and analyzing vector embeddings..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/search",
                    headers=get_auth_headers(),
                    json={"query": query_input, "page": 1, "page_size": page_size},
                    timeout=20
                )
                if response.status_code == 200:
                    search_data = response.json()
                    
                    # AI Synthesis Card
                    synthesis = search_data.get("ai_synthesis", {})
                    st.markdown(f"""
                        <div style="background: rgba(15, 23, 42, 0.9); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.5); margin-bottom: 1.5rem;">
                            <h4 style="color: #60a5fa; margin-top: 0;">✨ AI Executive Synthesis</h4>
                            <p style="color: #e2e8f0; font-size: 1.05rem;">{synthesis.get('summary', 'Synthesis generated.')}</p>
                            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 0;"><b>Confidence Score:</b> {synthesis.get('confidence_score', 0.95) * 100}% | <b>Execution Time:</b> {search_data.get('execution_time_ms', 0)} ms</p>
                        </div>
                    """, unsafe_allow_html=True)

                    # Experts (Pro Enterprise Feature)
                    experts = search_data.get("experts", [])
                    if experts:
                        st.markdown("#### 👥 Suggested Subject Matter Experts")
                        cols = st.columns(len(experts))
                        for i, expert in enumerate(experts):
                            with cols[i]:
                                with st.container(border=True):
                                    st.write(f"**{expert['name']}**")
                                    st.write(f"*{expert['title']}*")
                                    st.caption(expert['match_reason'])

                    st.markdown("#### 📑 Search Results & Citations")
                    for item in search_data.get("results", []):
                        with st.container(border=True):
                            st.subheader(item['title'])
                            st.write(item['snippet'])
                            st.caption(f"App: `{item['app'].upper()}` | Author: {item['author_name']} | Relevance Score: {item['score']}")
                else:
                    st.error(f"Search request failed: {response.text}")
            except Exception as e:
                st.error(f"Search error: {str(e)}")

with tab_workspaces:
    st.subheader("360° Deep Entity Workspaces")
    st.markdown("Inspect deep operational hubs for accounts, contracts, document sandboxes, and experts.")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        entity_type = st.selectbox("Entity Type", ["account", "document", "person"])
    with col_e2:
        entity_id = st.text_input("Entity ID", value="acme_corp_01")

    if st.button("Load Entity Workspace"):
        with st.spinner("Fetching entity hub and verifying multi-tenant permissions..."):
            try:
                res = requests.get(
                    f"{BACKEND_URL}/api/v1/entities/{entity_type}/{entity_id}",
                    headers=get_auth_headers(),
                    timeout=15
                )
                if res.status_code == 200:
                    workspace = res.json()
                    st.success(f"Successfully loaded: {workspace.get('title')}")
                    st.json(workspace.get("metadata"))
                    st.markdown("#### Sub-Modules & Rooms")
                    for mod in workspace.get("sub_modules", []):
                        with st.container(border=True):
                            st.write(f"**{mod.get('room_name', 'Module')}**")
                            st.json(mod)
                else:
                    st.error(f"Failed to load workspace: {res.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

with tab_mcp:
    st.subheader("FastMCP Server Protocol Inspector")
    st.markdown("Trigger real-time FastMCP server tools defined in your backend engine.")
    
    tool_choice = st.selectbox(
        "Select FastMCP Tool:", 
        ["inspect_tenant_security_posture", "traverse_entity_graph", "summarize_workspace_documents"]
    )
    
    tool_args = {}
    if tool_choice == "inspect_tenant_security_posture":
        tenant_input = st.text_input("Tenant ID", value="tenant_enterprise_corp_com")
        tool_args = {"tenant_id": tenant_input}
    elif tool_choice == "traverse_entity_graph":
        t_id = st.text_input("Tenant ID", value="tenant_enterprise_corp_com")
        root_ent = st.text_input("Root Entity", value="doc_001")
        depth = st.slider("Traversal Depth", 1, 4, 2)
        tool_args = {"tenant_id": t_id, "root_entity": root_ent, "depth": depth}
    elif tool_choice == "summarize_workspace_documents":
        t_id = st.text_input("Tenant ID", value="tenant_enterprise_corp_com")
        ws_id = st.text_input("Workspace ID", value="workspace_eng_01")
        tool_args = {"tenant_id": t_id, "workspace_id": ws_id}

    if st.button("Execute FastMCP Tool Dispatch"):
        with st.spinner("Executing FastMCP server protocol call..."):
            try:
                res = requests.post(
                    f"{BACKEND_URL}/api/v1/fastmcp/execute",
                    headers=get_auth_headers(),
                    json={"tool_name": tool_choice, "arguments": tool_args},
                    timeout=20
                )
                if res.status_code == 200:
                    mcp_res = res.json()
                    st.success(f"Tool `{mcp_res.get('tool_name')}` executed successfully in {mcp_res.get('execution_time_ms', 0)} ms!")
                    st.json(mcp_res.get("result"))
                else:
                    st.error(f"Execution failed: {res.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

with tab_governance:
    st.subheader("Tenant Governance & Cryptographic Audit Verification")
    st.markdown("Inspect immutable audit logs and verify HMAC signature integrity across your client databases.")

    if st.button("Verify Audit Log Cryptographic Chain"):
        with st.spinner("Running HMAC signature verification across database audit logs..."):
            try:
                res = requests.get(
                    f"{BACKEND_URL}/api/v1/admin/audit-logs/verify",
                    headers=get_auth_headers(),
                    timeout=20
                )
                if res.status_code == 200:
                    gov_data = res.json()
                    status_val = gov_data.get("status")
                    if status_val == "PASSED":
                        st.success(f"Audit Verification Status: PASSED ✅ ({gov_data.get('verified_authentic')} logs verified authentically)")
                    else:
                        st.error("Audit Verification Status: CORRUPTED ⚠️ Tamper detected!")
                    st.json(gov_data)
                else:
                    st.error(f"Verification restricted or failed: {res.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
                                        
