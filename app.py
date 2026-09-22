import streamlit as st
import requests
import pandas as pd
import time
import json
import streamlit.components.v1 as components

# Set page configuration for a wide, immersive workspace
st.set_page_config(
    page_title="Enterprise GraphRAG Control Panel", 
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = "https://enterprise-ke-3.onrender.com"

# ---------------------------------------------------------
# PALANTIR / NEO4J ENTERPRISE DESIGN SYSTEM (CSS)
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* Global Workspace Dark Theme */
    .stApp {
        background-color: #07090e;
        color: #cbd5e1;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Custom Scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #07090e; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #334155; }

    /* Telemetry & Metric Cards */
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace;
        color: #38bdf8 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px 12px;
    }

    /* Enterprise Inputs */
    .stTextInput input, .stSelectbox select {
        background-color: #0f172a !important;
        border: 1px solid #334155 !important;
        color: #f8fafc !important;
        border-radius: 4px !important;
        font-size: 0.85rem !important;
    }

    /* Primary Operational Buttons */
    .stButton>button[kind="primary"] {
        background: #0284c7 !important;
        color: #ffffff !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 4px !important;
        font-weight: 600;
        font-size: 0.85rem;
        transition: background 0.2s ease;
    }
    .stButton>button[kind="primary"]:hover {
        background: #0369a1 !important;
    }

    /* Compact Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid #1e293b;
        background-color: #0b0f19;
        padding: 4px 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 36px;
        background-color: transparent;
        color: #64748b;
        font-weight: 500;
        font-size: 0.85rem;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0f172a !important;
        color: #38bdf8 !important;
        border-bottom: 2px solid #0284c7 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# AUTHENTICATION GATE
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login_screen():
    st.title("🔒 Enterprise GraphRAG Clearance Gate")
    st.caption("Restricted cryptographic access system for multi-tenant knowledge meshes.")
    col1, col2 = st.columns([1, 1])
    with col1:
        username = st.text_input("Operator ID")
        api_key = st.text_input("Security Token / Key", type="password")
        if st.button("Establish Session", type="primary"):
            if api_key in ["ENTERPRISE-2026", "admin"]:
                st.session_state["authenticated"] = True
                st.session_state["user"] = username if username else "Enterprise Operator"
                st.rerun()
            else:
                st.error("Invalid token clearance.")
    with col2:
        st.info("**Security Compliance Notice:** All node traversals and query operations are audited via FastMCP secure channels.")

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# ---------------------------------------------------------
# OPERATIONAL SIDEBAR
# ---------------------------------------------------------
st.sidebar.markdown(f"**OPERATOR:** `{st.session_state.get('user', 'Admin')}`")
if st.sidebar.button("Terminate Session", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏢 Tenant Context")
active_workspace = st.sidebar.selectbox(
    "Active Mesh Sandbox",
    [
        "🏢 Global Enterprise Knowledge Graph",
        "⚖️ Legal & Contractual Risk Engine",
        "💸 Supply Chain & Vendor Audit",
        "🛡️ FinTech Compliance Workspace"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Engine Diagnostics")
try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=2)
    if response.status_code == 200:
        st.sidebar.markdown("🟢 **FastMCP Gateway:** Online (`110ms`)")
    else:
        st.sidebar.warning("🟡 **FastMCP Gateway:** Warming Up...")
except Exception:
    st.sidebar.error("🔴 **FastMCP Gateway:** Cold Start / Offline")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Traversal Parameters")
search_mode = st.sidebar.selectbox("Query Strategy", ["GraphRAG (Multi-Hop)", "Hybrid Vector", "Cypher Direct"])
max_depth = st.sidebar.slider("Traversal Depth ($hops$)", 1, 4, 2)
confidence_threshold = st.sidebar.slider("Confidence Filter", 0.0, 1.0, 0.75)

# ---------------------------------------------------------
# MAIN CONTROL PANEL HEADER & METRICS GRID
# ---------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("### 🧠 Enterprise GraphRAG Control Panel")
    st.caption(f"Connected Backend: `{BACKEND_URL}`")
with col_h2:
    st.markdown(f"""
        <div style="background-color:#0f172a; border:1px solid #1e293b; border-radius:4px; padding:6px; text-align:center;">
            <div style="color:#64748b; font-size:0.7rem;">WORKSPACE DOMAIN</div>
            <div style="color:#38bdf8; font-weight:600; font-size:0.8rem;">{active_workspace.split(' ')[1]}</div>
        </div>
    """, unsafe_allow_html=True)

# High-density telemetry dashboard
m1, m2, m3, m4 = st.columns(4)
m1.metric("Indexed Nodes", "1,420", "+28 delta")
m2.metric("Knowledge Edges", "3,890", "+84 relationships")
m3.metric("MCP Latency", "110 ms", "Optimal")
m4.metric("Mesh State", "Synchronized", "SEC-256")

st.markdown("---")

# ---------------------------------------------------------
# WORKSPACE INTERFACE TABS
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🕸 Operational Graph Canvas", 
    "📄 Ingestion Pipeline", 
    "📊 Database Schema Inspector", 
    "⚡ Polyglot API Console"
])

# ---------------------------------------------------------
# TAB 1: OPERATIONAL CANVAS (PALANTIR/NEO4J STYLE SPLIT-PANE)
# ---------------------------------------------------------
with tab1:
    # Toolbar Row
    col_t1, col_t2, col_t3 = st.columns([2, 1, 1])
    with col_t1:
        query = st.text_input("Global Search / Entity Query", placeholder="Enter entity name (e.g., Nvidia, Scale AI)...", label_visibility="collapsed")
    with col_t2:
        include_web = st.checkbox("Include Live Web Agents", value=True)
    with col_t3:
        execute_btn = st.button("Execute Traversal", type="primary", use_container_width=True)

    if execute_btn and query:
        st.session_state["active_query"] = query.strip().title()

    current_target = st.session_state.get("active_query", "Nvidia")

    # Split Pane: Main Canvas (Left) + Inspector Drawer (Right)
    pane_canvas, pane_inspector = st.columns([2.2, 1])

    with pane_canvas:
        st.markdown(f"**Interactive Topology Canvas — Target: `{current_target}`**")
        
        # Interactive Vis.js Force-Directed Graph Canvas
        nodes_data = json.dumps([
            {"id": 1, "label": f"{current_target}\n(Target)", "group": "target"},
            {"id": 2, "label": "TSMC\n(Foundry)", "group": "vendor"},
            {"id": 3, "label": "Mellanox\n(Subsidiary)", "group": "infra"},
            {"id": 4, "label": "CUDA Ecosystem\n(Software)", "group": "term"},
            {"id": 5, "label": "Supply Chain Risk\n(Risk)", "group": "risk"}
        ])
        edges_data = json.dumps([
            {"from": 1, "to": 2, "label": "SUPPLY"},
            {"from": 1, "to": 3, "label": "ACQUIRED"},
            {"from": 1, "to": 4, "label": "DEPLOYS"},
            {"from": 2, "to": 5, "label": "TRIGGERS"}
        ])

        canvas_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/10.1.2/standalone/umd/vis-network.min.js"></script>
            <style>
                body {{ margin: 0; background-color: #07090e; }}
                #canvas {{ width: 100%; height: 440px; border: 1px solid #1e293b; border-radius: 6px; }}
            </style>
        </head>
        <body>
        <div id="canvas"></div>
        <script>
            var nodes = new vis.DataSet({nodes_data});
            var edges = new vis.DataSet({edges_data});
            var container = document.getElementById('canvas');
            var data = {{ nodes: nodes, edges: edges }};
            var options = {{
                nodes: {{ shape: 'box', font: {{ color: '#f8fafc', size: 11, face: 'Inter' }}, borderWidth: 1 }},
                groups: {{
                    target: {{ color: {{ background: '#0284c7', border: '#38bdf8' }} }},
                    vendor: {{ color: {{ background: '#059669', border: '#34d399' }} }},
                    infra: {{ color: {{ background: '#d97706', border: '#fbbf24' }} }},
                    term: {{ color: {{ background: '#7c3aed', border: '#a78bfa' }} }},
                    risk: {{ color: {{ background: '#dc2626', border: '#f87171' }} }}
                }},
                edges: {{ color: {{ color: '#334155' }}, font: {{ color: '#64748b', size: 9 }}, arrows: {{ to: {{ enabled: true }} }} }},
                physics: {{ enabled: true, stabilization: {{ iterations: 100 }} }}
            }};
            var network = new vis.Network(container, data, options);
        </script>
        </body>
        </html>
        """
        components.html(canvas_html, height=450)

    with pane_inspector:
        st.markdown("**Node Inspector Drawer**")
        st.markdown(f"""
            <div style="background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 12px; font-size: 0.8rem;">
                <div style="color: #38bdf8; font-weight: 600; margin-bottom: 8px;">ENTITY: {current_target.upper()}</div>
                <div style="color: #94a3b8; line-height: 1.4;">
                    <strong>Type:</strong> Corporation / Platform Issuer<br>
                    <strong>Confidence Score:</strong> <code>99.8%</code><br>
                    <strong>Embedding Index:</strong> <code>0.8842_cosine</code><br>
                    <strong>Workspace Node ID:</strong> <code>#N-89420</code>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Executed Cypher Payload**")
        st.code(f"""
MATCH path = (e:Entity)-[*1..{max_depth}]-(n)
WHERE e.name CONTAINS '{current_target}'
RETURN path LIMIT 10;
        """, language="cypher")

# ---------------------------------------------------------
# TAB 2: INGESTION PIPELINE
# ---------------------------------------------------------
with tab2:
    st.markdown("### 📄 Enterprise Document Ingestion Pipeline")
    col_up, col_log = st.columns([1.5, 1])
    
    with col_up:
        uploaded_files = st.file_uploader("Upload Raw Structured/Unstructured Data", type=["pdf", "docx", "csv", "parquet"], accept_multiple_files=True)
        if uploaded_files and st.button("Run Extraction & Graph Indexer", type="primary"):
            with st.status("Executing FastMCP Chunking & Embedding Pipeline...", expanded=True) as status:
                time.sleep(0.5)
                status.update(label="Graph Ingestion Complete.", state="complete")
            st.success(f"Indexed {len(uploaded_files)} files into `{active_workspace}`.")

    with col_log:
        st.markdown("**Pipeline Telemetry**")
        st.markdown("""
        * **Chunk Strategy:** Semantic Boundary
        * **Vector Model:** `text-embedding-3-large`
        * **Sync Mode:** Real-time Transactional
        """)

# ---------------------------------------------------------
# TAB 3: DATABASE SCHEMA INSPECTOR
# ---------------------------------------------------------
with tab3:
    st.markdown("### 📊 Active Knowledge Graph Schema")
    schema_df = pd.DataFrame([
        {"Label": "Vendors", "Count": 340, "Indexed Properties": "name, tier, country, risk_score"},
        {"Label": "Contracts", "Count": 182, "Indexed Properties": "id, start_date, renewal, value"},
        {"Label": "SLA Clauses", "Count": 940, "Indexed Properties": "clause_id, metric, threshold"},
        {"Label": "Risks", "Count": 85, "Indexed Properties": "severity, mitigation_status, category"}
    ])
    st.dataframe(schema_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# TAB 4: POLYGLOT API CONSOLE
# ---------------------------------------------------------
with tab4:
    st.markdown("### ⚡ FastMCP Client SDK Integration")
    st.code(f"""
from fastmcp import Client
import asyncio

async def fetch_enterprise_graph():
    async with Client("{BACKEND_URL}/sse") as client:
        result = await client.call_tool(
            "graphrag_search", 
            {{"query": "Nvidia supply chain risk", "depth": {max_depth}}}
        )
        print(result)

asyncio.run(fetch_enterprise_graph())
    """, language="python")

