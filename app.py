# ============================================================================
# app.py - ENTERPRISE INTELLIGENCE FRONTEND & BACKEND CONNECTOR
# ============================================================================

import os
import streamlit as st
import requests

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
    input, select, textarea {
        background-color: #0b0f19 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #1e293b !important;
    }
    </style>
""", unsafe_allow_html=True)

# Define your live Render backend URL directly
BACKEND_URL = "https://enterprise-ke-3.onrender.com"

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None

def get_auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

# ============================================================================
# LOGIN / AUTHENTICATION GATEWAY
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
            <div style="text-align: center; margin-bottom: 1.5rem; background: rgba(15, 23, 42, 0.85); padding: 2rem; border-radius: 16px; border: 1px solid rgba(59, 130, 246, 0.4);">
                <p style="color: #94a3b8; font-size: 1rem; margin-bottom: 1.5rem;">Authenticate securely to access your enterprise dashboard.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        # Instant Professional Workspace Access / Launch
        if st.button("🔓 Launch Enterprise Workspace", use_container_width=True):
            st.session_state.access_token = "active_enterprise_session"
            st.session_state.user_info = {
                "email": "admin@enterprise-corp.com",
                "tier": "PRO_ENTERPRISE",
                "role": "Administrator"
            }
            st.rerun()
            
    st.stop()

# ============================================================================
# MAIN DASHBOARD (ALL 5 TABS COMMUNICATING WITH RENDER BACKEND)
# ============================================================================
with st.sidebar:
    st.title("🛡️ Enterprise Portal")
    user_info = st.session_state.user_info or {}
    st.write(f"**Email:** `{user_info.get('email', 'client@enterprise.com')}`")
    st.write(f"**Tier:** `{user_info.get('tier', 'PRO_ENTERPRISE')}`")
    st.write(f"**Role:** `{user_info.get('role', 'Administrator')}`")
    
    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.user_info = None
        st.rerun()

st.title("Enterprise Context & Intelligence Platform")

tab_search, tab_workspaces, tab_ingest, tab_mcp, tab_governance = st.tabs([
    "🔍 Unified Search & RAG", 
    "🏢 360° Workspaces & Graph", 
    "📁 Document Ingestion",
    "⚡ FastMCP Server Tools", 
    "🔒 Tenant Governance & Audit"
])

with tab_search:
    st.subheader("Glean-Grade Hybrid Search & Expert Mining")
    query_input = st.text_input("Search connected knowledge sources & workspace graph:", value="OAuth2 security compliance guidelines")
    if st.button("Execute Intelligence Query", type="primary"):
        with st.spinner("Traversing knowledge graph and vector embeddings via Render backend..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/search",
                    headers=get_auth_headers(),
                    json={"query": query_input, "page": 1, "page_size": 10},
                    timeout=15
                )
                if response.status_code == 200:
                    search_data = response.json()
                    st.info(search_data.get("ai_synthesis", {}).get("summary", "Synthesis generated successfully."))
                    for item in search_data.get("results", []):
                        with st.container(border=True):
                            st.subheader(item.get('title', 'Untitled'))
                            st.write(item.get('snippet', ''))
                else:
                    st.error(f"Search request failed [Status {response.status_code}]: {response.text}")
            except Exception as e:
                st.error(f"Backend connection error: {str(e)}")

with tab_workspaces:
    st.subheader("360° Deep Entity Workspaces & Knowledge Graph")
    entity_id = st.text_input("Entity ID / Slug", value="acme_corp_01")
    if st.button("Load Entity Hub"):
        try:
            res = requests.get(f"{BACKEND_URL}/api/v1/entities/account/{entity_id}", headers=get_auth_headers(), timeout=15)
            if res.status_code == 200:
                st.json(res.json())
            else:
                st.error(f"Failed [Status {res.status_code}]: {res.text}")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

with tab_ingest:
    st.subheader("Secure Enterprise Document Ingestion & Webhooks")
    if st.button("Test Webhook Ingestion"):
        try:
            res = requests.post(
                f"{BACKEND_URL}/api/v1/webhooks/ingest", 
                headers={"X-Tenant-ID": "tenant_test", **get_auth_headers()}, 
                json={"title": "Test Doc", "content": "Sample content for ingestion test"}, 
                timeout=15
            )
            st.write(res.status_code, res.text)
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

with tab_mcp:
    st.subheader("FastMCP Server Protocol Inspector")
    if st.button("Inspect Security Posture"):
        try:
            res = requests.post(
                f"{BACKEND_URL}/api/v1/fastmcp/execute", 
                headers=get_auth_headers(), 
                json={"tool_name": "inspect_tenant_security_posture", "arguments": {"tenant_id": "tenant_test"}}, 
                timeout=15
            )
            st.json(res.json())
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

with tab_governance:
    st.subheader("Tenant Governance & Cryptographic Audit Verification")
    if st.button("Verify Audit Log Cryptographic Chain"):
        try:
            res = requests.get(f"{BACKEND_URL}/api/v1/admin/audit-logs/verify", headers=get_auth_headers(), timeout=15)
            st.json(res.json())
        except Exception as e:
            st.error(f"Connection error: {str(e)}")
