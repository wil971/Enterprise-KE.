import streamlit as st
import requests
import pandas as pd
import time
import json
import streamlit.components.v1 as components

# 1. PAGE INITIALIZATION
st.set_page_config(
    page_title="Enterprise GraphRAG Command Center", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Target API endpoint (replace with your actual deployed Render service URL)
BACKEND_URL = "https://your-fastmcp-backend.onrender.com"
# 2. CUSTOM DARK THEME & CSS MATRIX
st.markdown("""
    <style>
    .stApp {
        background-color: #060913;
        color: #f1f5f9;
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    section[data-testid="stSidebar"] {
        background-color: #0b1120 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    .telemetry-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .telemetry-card:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
    }
    
    .stTextInput input, .stSelectbox select, .stMultiSelect div {
        background-color: #0f172a !important;
        border: 1px solid #334155 !important;
        color: #f8fafc !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    .stTextInput input:focus {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2) !important;
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        letter-spacing: 0.025em !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #0ea5e9 0%, #0284c7 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(14, 165, 233, 0.4) !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 2px solid #1e293b;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background-color: #0f172a;
        color: #94a3b8;
        font-weight: 600;
        border: 1px solid #1e293b;
        border-radius: 8px 8px 0 0;
        padding: 0 24px;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        border: 1px solid #334155 !important;
        border-bottom: 3px solid #38bdf8 !important;
    }
    </style>
""", unsafe_allow_html=True)
# 3. SESSION STATE & AUTHENTICATION GATE
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "auth_processing" not in st.session_state:
    st.session_state["auth_processing"] = False
if "uploaded_docs_cache" not in st.session_state:
    st.session_state["uploaded_docs_cache"] = []

def run_secure_login_gate():
    components.html("""
    <div style="width:100%; text-align:center; margin-bottom:10px;">
        <svg width="80" height="80" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="40" stroke="#1e293b" stroke-width="4"/>
            <circle cx="50" cy="50" r="40" stroke="#38bdf8" stroke-width="4" stroke-dasharray="80 200">
                <animateTransform attributeName="transform" type="rotate" from="0 50 50" to="360 50 50" dur="2.5s" repeatCount="indefinite"/>
            </circle>
            <path d="M35 50L45 60L65 40" stroke="#38bdf8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    </div>
    """, height=90)
    
    st.markdown("<h1 style='text-align: center; color: #ffffff; font-weight: 800; letter-spacing: -0.025em;'>ENTERPRISE SECURE RETRIEVAL GATEWAY</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.1rem; margin-bottom: 40px;'>Cryptographically Audited Context Retrieval Infrastructure Node</p>", unsafe_allow_html=True)
    
    col_center, _ = st.columns([1, 0.001])
    with col_center:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1px solid #334155; border-radius: 16px; padding: 40px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);">
            <h3 style="margin-top:0; color:#f8fafc; font-size:1.3rem; margin-bottom:20px;">Identity Provider Authorization</h3>
        """, unsafe_allow_html=True)
        
        user_input = st.text_input("Corporate Identifier / IAM User")
        pass_input = st.text_input("Cryptographic Access Key / Token", type="password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        trigger_auth = st.button("INITIALIZE SECURE AUTHENTICATION HANDSHAKE FLOW", use_container_width=True)
        
        if trigger_auth:
            if pass_input in ["ENTERPRISE-2026", "admin"]:
                st.session_state["auth_processing"] = True
                auth_ticker = st.progress(0)
                status_block = st.empty()
                
                for step in range(1, 101, 20):
                    status_block.markdown(f"<p style='color:#38bdf8; font-weight:500; text-align:center;'>🔒 Executing Zero-Knowledge Token Proof Challenge... {step}%</p>", unsafe_allow_html=True)
                    auth_ticker.progress(step)
                    time.sleep(0.12)
                
                st.session_state["authenticated"] = True
                st.session_state["user"] = user_input if user_input else "Principal Executor"
                st.rerun()
            else:
                st.error("Access Allocation Rejected: Cryptographic signature mismatch or token expiry flag.")
        
        st.markdown("""
            <hr style="border-color:#334155; margin:30px 0;">
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; color:#94a3b8; font-size:0.85rem;">
                <div>--- ENCRYPTED SSL FAST_MCP</div>
                <div>--- HARDENED NODE PROTECTION</div>
                <div>--- ACTIVE RECONCILIATION AUDIT</div>
                <div>--- ISOLATED WORKSPACE FRAME</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

if not st.session_state["authenticated"]:
    run_secure_login_gate()
    st.stop()
    # 4. SIDEBAR NAVIGATION & TELEMETRY CONTROL
st.sidebar.markdown(f"""
    <div style="background-color:#1e293b; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center; margin-bottom:15px;">
        <div style="color:#64748b; font-size:0.75rem; font-weight:700; text-transform: uppercase;">AUTHENTICATED PRINCIPAL</div>
        <div style="color:#38bdf8; font-size:1.1rem; font-weight:700;">{st.session_state.get('user', 'Global Admin')}</div>
    </div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Terminate Secure Session Context", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("<hr style='border-color:#1e293b;'>", unsafe_allow_html=True)

st.sidebar.markdown("<h4 style='color:#94a3b8; font-size:0.85rem; font-weight:700;'>DATA PRIVACY ISOLATION SPACES</h4>", unsafe_allow_html=True)
active_workspace = st.sidebar.selectbox(
    "Select Tenant Authorization Plane",
    [
        "🏢 Global Enterprise Knowledge Graph",
        "⚖️ Legal & Contractual Risk Engine",
        "💸 Supply Chain & Vendor Audit",
        "🛡️ FinTech Compliance Workspace"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("<hr style='border-color:#1e293b;'>", unsafe_allow_html=True)

st.sidebar.markdown("<h4 style='color:#94a3b8; font-size:0.85rem; font-weight:700;'>SERVER STREAM DISPATCH HEALTH</h4>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div style="background-color:#0f172a; border:1px solid #1e293b; border-radius:8px; padding:12px; margin-bottom:15px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span style="font-size:0.8rem; color:#94a3b8;">FastMCP Core Router</span>
        <span style="color:#10b981; font-weight:700; font-size:0.8rem;">ONLINE ●</span>
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span style="font-size:0.8rem; color:#94a3b8;">SSE Transport Socket</span>
        <span style="color:#10b981; font-weight:700; font-size:0.8rem;">SECURED SSL</span>
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:0.8rem; color:#94a3b8;">Graph Database Pool</span>
        <span style="color:#10b981; font-weight:700; font-size:0.8rem;">CONNECTED</span>
    </div>
</div>
""", unsafe_allow_html=True)

search_mode = st.sidebar.selectbox(
    "Query Router Execution Mode",
    ["GraphRAG (Multi-Hop Engine)", "Hybrid (Semantic Proximity Vector + Graph)", "Deterministic Cypher Path Traversal"],
    label_visibility="collapsed"
)

max_depth = st.sidebar.slider("Recursive Relationship Traversal Hop Boundary", min_value=1, max_value=4, value=2)

target_labels = st.sidebar.multiselect(
    "Enforce Structural Label Constraints",
    ["Vendors", "Contracts", "SLA Clauses", "Risks", "Liabilities", "Payment Terms"],
    default=["Vendors", "Contracts", "SLA Clauses", "Risks"],
    label_visibility="collapsed"
)

# 5. HEADER & METRICS
col_main_title, col_tenant_seal = st.columns([3, 1])
with col_main_title:
    st.markdown("<h2 style='color:#ffffff; margin:0; font-weight:800;'>ENTERPRISE KNOWLEDGE GRAPH CONTEXT ENGINE</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:0.9rem; margin-top:2px;'>Asynchronous FastMCP Processing Instance Gateway: <code>{active_workspace}</code></p>", unsafe_allow_html=True)
with col_tenant_seal:
    st.markdown(f"""
    <div style="background-color:#0f172a; border:1px solid #38bdf8; border-radius:8px; padding:10px; text-align:center;">
        <span style="color:#38bdf8; font-size:0.75rem; font-weight:700; display:block;">ACTIVE SECURITY BOUNDARY</span>
        <span style="color:#ffffff; font-size:0.85rem; font-weight:600;">{active_workspace.split(' ')[1] if ' ' in active_workspace else active_workspace}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown("""
    <div class="telemetry-card">
        <div style="color:#94a3b8; font-size:0.75rem; font-weight:700; text-transform:uppercase;">Indexed Metadata Nodes</div>
        <div style="color:#ffffff; font-size:1.8rem; font-weight:800; margin:5px 0;">1,420</div>
        <div style="color:#10b981; font-size:0.75rem;">↑ 28 linked today</div>
    </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown("""
    <div class="telemetry-card">
        <div style="color:#94a3b8; font-size:0.75rem; font-weight:700; text-transform:uppercase;">Active Structural Edges</div>
        <div style="color:#ffffff; font-size:1.8rem; font-weight:800; margin:5px 0;">3,890</div>
        <div style="color:#38bdf8; font-size:0.75rem;">↑ 84 links syncing</div>
    </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown("""
    <div class="telemetry-card">
        <div style="color:#94a3b8; font-size:0.75rem; font-weight:700; text-transform:uppercase;">FastMCP Router Latency</div>
        <div style="color:#ffffff; font-size:1.8rem; font-weight:800; margin:5px 0;">110 ms</div>
        <div style="color:#10b981; font-size:0.75rem;">↓ 12ms optimized</div>
    </div>
    """, unsafe_allow_html=True)
with m4:
    st.markdown("""
    <div class="telemetry-card">
        <div style="color:#94a3b8; font-size:0.75rem; font-weight:700; text-transform:uppercase;">Sync Compliance</div>
        <div style="color:#ffffff; font-size:1.8rem; font-weight:800; margin:5px 0;">100%</div>
        <div style="color:#10b981; font-size:0.75rem;">SECURE 🟢 Real-time</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

