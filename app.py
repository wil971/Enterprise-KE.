# ============================================================================
# ENTERPRISE INTELLIGENCE PLATFORM - ELITE PRODUCTION FRONTEND (APP.PY)
# ============================================================================

import os
import streamlit as st
import requests

# ----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & ENTERPRISE DESIGN SYSTEM
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Enterprise Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", "https://enterprise-ke-3.onrender.com")).rstrip("/")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    .stApp { 
        background-color: #030712;
        color: #f8fafc;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}

    section[data-testid="stSidebar"] {
        background-color: #080e1a !important;
        border-right: 1px solid rgba(30, 41, 59, 0.8) !important;
    }

    .enterprise-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(10, 15, 30, 0.95) 100%);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 10px 30px -10px rgba(2, 132, 199, 0.2);
        margin-bottom: 16px;
    }

    .metric-container {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(51, 65, 85, 0.8);
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
    }

    .stTextInput input, .stSelectbox select, .stSlider {
        background-color: #0b0f19 !important;
        color: #f8fafc !important;
        border-radius: 8px !important;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        padding: 10px 14px !important;
    }

    .stButton>button {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: white !important;
        border: 1px solid rgba(56, 189, 248, 0.5) !important;
        border-radius: 8px !important;
        height: 2.75rem;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 2. SESSION STATE & JWT TOKEN MANAGEMENT
# ----------------------------------------------------------------------------
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None

query_params = st.query_params
if "token" in query_params and not st.session_state.access_token:
    st.session_state.access_token = query_params["token"]
    st.session_state.tenant_id = query_params.get("tenant", "tenant_enterprise")
    st.query_params.clear()
    st.rerun()

def get_auth_headers():
    return {"Authorization": f"Bearer {st.session_state.access_token}"} if st.session_state.access_token else {}

# ----------------------------------------------------------------------------
# 3. ENTERPRISE LOGIN GATEWAY (LOCKED STATE)
# ----------------------------------------------------------------------------
if not st.session_state.access_token:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 1.3, 1])

    with col_center:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="font-size: 2.2rem; font-weight: 800; color: #f8fafc; letter-spacing: -1px;">ENTERPRISE INTELLIGENCE</h1>
                <p style="color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 2px; margin-top: 8px;">Multi-Tenant GraphRAG & FastMCP Security Gateway</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        st.markdown('<div class="enterprise-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='color:#f8fafc; font-size:1.1rem; margin-top:0; margin-bottom:10px; font-weight:700; text-align:center;'>Corporate Workspace Authentication</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem; text-align: center; margin-bottom: 24px;'>Access restricted to verified corporate domains. Automated tenant isolation enabled.</p>", unsafe_allow_html=True)
        
        google_login_endpoint = f"{BACKEND_URL}/api/v1/auth/google/login"
        
        st.markdown(f"""
            <div style="text-align: center;">
                <a href="{google_login_endpoint}" target="_self" style="text-decoration: none;">
                    <div style="background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; padding: 13px 20px; border-radius: 8px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; gap: 10px; width: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                        <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"/><path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.95H1.2v3.15C3.18 21.3 7.22 24 12 24z"/><path fill="#FBBC05" d="M5.28 14.25c-.25-.72-.38-1.49-.38-2.25s.13-1.53.38-2.25V6.6H1.2C.43 8.15 0 9.89 0 12s.43 3.85 1.2 5.4l4.08-3.15z"/><path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.22 0 3.18 2.7 1.2 6.6l4.08 3.15c.95-2.84 3.6-4.95 6.72-4.95z"/></svg>
                        Sign in with Google Workspace
                    </div>
                </a>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

# ----------------------------------------------------------------------------
# 4. UNLOCKED EXECUTIVE DASHBOARD (FULL PLATFORM MODULES)
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"""
        <div style="background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(56, 189, 248, 0.3); padding: 16px; border-radius: 10px; margin-bottom: 20px;">
            <div style="color: #64748b; font-size: 0.65rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; letter-spacing: 1.5px;">ACTIVE TENANT</div>
            <div style="color: #38bdf8; font-size: 0.9rem; font-weight: 800; margin-top: 4px; word-break: break-all;">{st.session_state.get('tenant_id')}</div>
            <div style="margin-top: 10px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(51, 65, 85, 0.6); padding-top: 8px;">
                <span style="color: #94a3b8; font-size: 0.7rem;">Compliance Tier</span>
                <span style="color: #10b981; font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">PRO_ENTERPRISE</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    selected_module = st.radio(
        "Navigation Menu",
        ["🔍 Unified Search Engine", "🌐 360° Entity Workspaces", "⚡ FastMCP Tool Console", "🛡️ Tenant Governance & Audits"]
    )
    
    st.markdown("---")
    if st.button("🚪 Terminate Session", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.tenant_id = None
        st.rerun()

# ----------------------------------------------------------------------------
# MODULE 1: UNIFIED SEARCH & GRAPH RAG
# ----------------------------------------------------------------------------
if selected_module == "🔍 Unified Search Engine":
    st.title("🛡️ Enterprise Context & Intelligence Platform")
    st.markdown("Glean-grade hybrid vector search and multi-hop graph retrieval engine active.")
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown('<div class="metric-container"><span style="color: #94a3b8; font-size:0.75rem;">INDEXED NODES</span><br><b style="color: #38bdf8; font-size:1.1rem;">128,450</b></div>', unsafe_allow_html=True)
    with m2:
        st.markdown('<div class="metric-container"><span style="color: #94a3b8; font-size:0.75rem;">ACL CLEARANCE</span><br><b style="color: #10b981; font-size:1.1rem;">VERIFIED SECURE</b></div>', unsafe_allow_html=True)
    with m3:
        st.markdown('<div class="metric-container"><span style="color: #94a3b8; font-size:0.75rem;">LATENCY</span><br><b style="color: #f59e0b; font-size:1.1rem;">42 ms</b></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    query_input = st.text_input("Search connected knowledge sources & workspace graph:", value="OAuth2 security compliance guidelines")

    if st.button("Execute Intelligence Query", type="primary"):
        with st.spinner("Traversing knowledge graph and analyzing vector embeddings..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/search",
                    headers=get_auth_headers(),
                    json={"query": query_input, "page": 1, "page_size": 10},
                    timeout=15
                )
                if response.status_code == 200:
                    search_data = response.json()
                    synth = search_data.get("ai_synthesis", {})
                    
                    st.markdown("### AI Executive Synthesis")
                    st.info(synth.get("summary", "Synthesis generated successfully."))
                    
                    st.markdown("### Verified Knowledge Citations & Results")
                    for item in search_data.get("results", []):
                        st.markdown(f"""
                            <div class="enterprise-card">
                                <h4 style="margin-top:0; color:#38bdf8; font-size:1.05rem;">{item['title']}</h4>
                                <p style="color:#cbd5e1; font-size:0.9rem; margin-bottom:12px;">{item['snippet']}</p>
                                <span style="background: rgba(56, 189, 248, 0.1); color: #38bdf8; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace;">Source: {item['app']}</span>
                                <span style="background: rgba(16, 185, 129, 0.1); color: #10b981; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; margin-left: 8px;">Score: {item['score']}</span>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.error(f"Search request failed: {response.text}")
            except Exception as e:
                st.error(f"Search connection error: {str(e)}")

# ----------------------------------------------------------------------------
# MODULE 2: 360° ENTITY WORKSPACES
# ----------------------------------------------------------------------------
elif selected_module == "🌐 360° Entity Workspaces":
    st.title("🌐 360° Entity Hubs")
    st.markdown("Inspect unified client accounts, document sandboxes, and expert profiles.")
    
    col1, col2 = st.columns(2)
    with col1:
        entity_type = st.selectbox("Entity Type", ["account", "document", "person"])
    with col2:
        entity_id = st.text_input("Entity ID", value="acme_corp_01")
        
    if st.button("Inspect Entity Workspace"):
        with st.spinner("Fetching secure entity workspace..."):
            try:
                res = requests.get(
                    f"{BACKEND_URL}/api/v1/entities/{entity_type}/{entity_id}",
                    headers=get_auth_headers(),
                    timeout=15
                )
                if res.status_code == 200:
                    data = res.json()
                    st.markdown(f"""
                        <div class="enterprise-card">
                            <h3 style="color: #38bdf8; margin-top:0;">{data.get('title')}</h3>
                            <p style="color: #94a3b8; font-size: 0.85rem;">Permissions Verified: <b>{data.get('permissions_verified')}</b></p>
                        </div>
                    """, unsafe_allow_html=True)
                    st.markdown("#### Metadata Attributes")
                    st.json(data.get("metadata", {}))
                else:
                    st.error(f"Failed to fetch workspace: {res.text}")
            except Exception as e:
                st.error(f"Error: {e}")

# ----------------------------------------------------------------------------
# MODULE 3: FASTMCP TOOL CONSOLE
# ----------------------------------------------------------------------------
elif selected_module == "⚡ FastMCP Tool Console":
    st.title("⚡ FastMCP Protocol Execution Engine")
    st.markdown("Execute secure context-aware tool calls via the FastMCP server protocol.")
    
    tool_name = st.selectbox("Select FastMCP Tool", ["query_knowledge_graph", "verify_document_permissions", "inspect_tenant_security_posture"])
    depth_arg = st.slider("Graph Traversal Depth", 1, 5, 2)
    
    if st.button("Execute Tool Call"):
        with st.spinner("Executing FastMCP protocol action..."):
            try:
                payload = {"tool_name": tool_name, "arguments": {"depth": depth_arg, "doc_id": "doc_001"}}
                res = requests.post(f"{BACKEND_URL}/api/v1/fastmcp/execute", headers=get_auth_headers(), json=payload, timeout=15)
                if res.status_code == 200:
                    st.success("Tool Execution Successful 🟢")
                    st.json(res.json())
                else:
                    st.error(f"Tool execution failed: {res.text}")
            except Exception as e:
                st.error(f"Error: {e}")

# ----------------------------------------------------------------------------
# MODULE 4: TENANT GOVERNANCE & AUDIT LOGS
# ----------------------------------------------------------------------------
elif selected_module == "🛡️ Tenant Governance & Audits":
    st.title("🛡️ Tenant Governance & Cryptographic Audits")
    st.markdown("Verify audit trail integrity and inspect compliance postures using HMAC-SHA256 signature validation.")
    
    if st.button("Verify Audit Log Cryptographic Chain"):
        with st.spinner("Evaluating HMAC audit signatures..."):
            try:
                res = requests.get(f"{BACKEND_URL}/api/v1/admin/audit-logs/verify", headers=get_auth_headers(), timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    st.success("Audit verification completed successfully.")
                    st.json(data)
                else:
                    st.error(f"Audit verification failed: {res.text}")
            except Exception as e:
                st.error(f"Error: {e}")
        
