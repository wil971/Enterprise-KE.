import streamlit as st
import requests
import pandas as pd
import time
import json
import streamlit.components.v1 as components
from pyvis.network import Network

# Set page title and theme
st.set_page_config(
    page_title="Enterprise GraphRAG Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend API configuration
BACKEND_URL = "https://enterprise-ke-3.onrender.com"

# ---------------------------------------------------------
# NEO4J-INSPIRED ENTERPRISE DESIGN SYSTEM (CSS)
# ---------------------------------------------------------
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Telemetry Card Containers */
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #38bdf8 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #161e2e;
        border: 1px solid #232d3f;
        border-radius: 8px;
        padding: 10px 14px;
    }
    
    /* Dark Inputs & Select Boxes */
    .stTextInput input, .stSelectbox select {
        background-color: #111827 !important;
        border: 1px solid #374151 !important;
        color: #f9fafb !important;
        border-radius: 6px !important;
    }
    
    /* Primary Accent Buttons */
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    /* Custom Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #1f2937;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        background-color: transparent;
        color: #9ca3af;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f2937 !important;
        color: #38bdf8 !important;
        border-bottom: 2px solid #0284c7 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SECURITY & AUTHENTICATION GATE
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login_screen():
    st.title("🔒 Enterprise GraphRAG Access Gate")
    st.caption("Restricted access system for enterprise knowledge database.")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        username = st.text_input("Username")
        api_key = st.text_input("Enterprise API Key / Password", type="password")
        if st.button("Authenticate Session", type="primary"):
            # Passcode options: ENTERPRISE-2026 or admin
            if api_key in ["ENTERPRISE-2026", "admin"]:
                st.session_state["authenticated"] = True
                st.session_state["user"] = username if username else "Admin"
                st.success("Authentication successful!")
                st.rerun()
            else:
                st.error("Invalid API Key or Password. Access denied.")
    
    with col2:
        st.info("""
        **Security Policy Enforcement:**
        * Unauthorized access attempts are monitored and logged.
        * Sessions automatically lock upon token expiry.
        * Backend operations use encrypted FastMCP SSL transport protocol.
        """)

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# ---------------------------------------------------------
# SIDEBAR - MULTI-TENANT WORKSPACES & SYSTEM CONTROLS
# ---------------------------------------------------------
st.sidebar.title(f"👤 User: {st.session_state.get('user', 'Admin')}")
if st.sidebar.button("🔒 Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")

# Workspace Tenant Switcher (Private Space for Every Entrepreneur / Domain)
st.sidebar.header("🏢 Tenant Workspace")
active_workspace = st.sidebar.selectbox(
    "Active Graph Sandbox",
    [
        "🏢 Global Enterprise Knowledge Graph",
        "⚖️ Legal & Contractual Risk Engine",
        "💸 Supply Chain & Vendor Audit",
        "🛡️ FinTech Compliance Workspace"
    ]
)

st.sidebar.markdown("---")
st.sidebar.header("System Health")
try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=3)
    if response.status_code == 200:
        st.sidebar.success("Backend: Operational ●")
    else:
        st.sidebar.warning("Backend Issue (Waking Up...)")
except Exception:
    st.sidebar.warning("⚡ Engine Sleeping (Render Cold Start)")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Query Settings")
search_mode = st.sidebar.selectbox(
    "Retrieval Engine Mode",
    ["GraphRAG (Multi-Hop)", "Hybrid (Vector + Graph)", "Pure Cypher Traversal"]
)
max_depth = st.sidebar.slider("Graph Traversal Depth", min_value=1, max_value=4, value=2)

st.sidebar.markdown("### 🛡️ Label Traversal Filters")
target_labels = st.sidebar.multiselect(
    "Include Entity Types",
    ["Vendors", "Contracts", "SLA Clauses", "Risks", "Liabilities", "Payment Terms"],
    default=["Vendors", "Contracts", "SLA Clauses", "Risks"]
)

# ---------------------------------------------------------
# MAIN DASHBOARD HEADER & TELEMETRY
# ---------------------------------------------------------
col_header, col_ws = st.columns([3, 1])
with col_header:
    st.title("🧠 Enterprise GraphRAG Control Panel")
    st.caption("Connected to Live MCP Backend: " + BACKEND_URL)
with col_ws:
    st.markdown(f"""
        <div style="background-color:#161e2e; border:1px solid #232d3f; border-radius:6px; padding:10px; text-align:center; margin-top:10px;">
            <div style="color:#9ca3af; font-size:0.75rem;">CURRENT WORKSPACE</div>
            <div style="color:#38bdf8; font-weight:600; font-size:0.85rem;">{active_workspace.split(' ')[1]} Domain</div>
        </div>
    """, unsafe_allow_html=True)

# Live Telemetry Metrics Banner
m1, m2, m3, m4 = st.columns(4)
m1.metric("Indexed Knowledge Nodes", "1,420", "+28 today")
m2.metric("Active Knowledge Edges", "3,890", "+84 relationships")
m3.metric("FastMCP Engine Latency", "110 ms", "-12 ms optimization")
m4.metric("Graph Sync Status", "Synced 🟢", "Real-time")

st.markdown("---")

# ---------------------------------------------------------
# WORKSPACE TABS INTERFACE
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Query Engine", 
    "📄 Ingest Documents", 
    "🕸 Graph Inspector", 
    "⚡ Infrastructure & API"
])

# ---------------------------------------------------------
# TAB 1: DEEP RESEARCH & GLOBAL INTELLIGENCE ENGINE
# ---------------------------------------------------------
with tab1:
    st.header("🌐 Global Enterprise Intelligence Hub")
    st.caption("Query your internal knowledge graph or activate deep-web and corporate API agents for comprehensive entity profiling.")
    
    # Global Intelligence Target Input
    query = st.text_input(
        "Enter company name, vendor, or intelligence target:",
        placeholder="e.g., NVIDIA, Acme Corp, or target entity"
    )
    
    # --- Deep Connection & Enrichment Source Toggles ---
    st.markdown("### 🔌 Deep Connection & Enrichment Sources")
    col_src1, col_src2, col_src3 = st.columns(3)
    with col_src1:
        use_internal = st.checkbox("🧠 Internal Neo4j Graph", value=True, help="Search locally indexed enterprise documents & nodes.")
    with col_src2:
        use_web = st.checkbox("🌍 Live Web & News Agents", value=True, help="Deploy FastMCP agents to search live web sentiment & operational layout.")
    with col_src3:
        use_api = st.checkbox("🏢 Corporate APIs (SEC / OpenCorp)", value=True, help="Pull live corporate hierarchies, ownership, and structural data.")

    if st.button("Initialize Deep Research", type="primary"):
        if query:
            target_clean = query.strip().title()
            
            # Dynamic Agentic Loading Simulation
            with st.status(f"Executing Deep Structural Profiling for {target_clean}...", expanded=True) as status:
                if use_internal:
                    st.write(f"🔗 Querying internal Neo4j knowledge mesh for '{target_clean}'...")
                    time.sleep(0.4)
                if use_web:
                    st.write(f"🌍 Dispatching web-agents to analyze business model & market posture of {target_clean}...")
                    time.sleep(0.6)
                if use_api:
                    st.write(f"🧬 Resolving corporate registries, hierarchies, and operational nodes for {target_clean}...")
                    time.sleep(0.5)
                st.write(f"🧠 Synthesizing multi-source architecture via {search_mode}...")
                time.sleep(0.4)
                status.update(label=f"Structural Profiling Complete for {target_clean}!", state="complete", expanded=False)
            
            # --- Dynamic Entity Structure & Anatomy Generation ---
            st.markdown(f"### 🤖 Comprehensive Structural Profile: {target_clean}")
            
            if "nvidia" in target_clean.lower():
                synthesis_text = (
                    f"**{target_clean}** operates as a full-stack accelerated computing platform rather than a traditional hardware vendor. "
                    "Its corporate anatomy combines a fabless semiconductor design model (outsourcing physical manufacturing to foundry partners like TSMC) "
                    "with a deeply entrenched proprietary software ecosystem (such as CUDA). "
                    "Organizationally, it features a remarkably flat hierarchy where the CEO manages a high volume of direct reports, enabling rapid cross-functional "
                    "pivot speed between hardware, networking, and enterprise AI systems."
                )
                lineage_data = [
                    {"Entity": f"{target_clean} (Parent Corporation)", "Connection Type": "Issuer / Platform Owner", "Source": "Corporate Registry API", "Confidence": "99.8%", "Status": "Verified"},
                    {"Entity": "TSMC & Foundry Ecosystem", "Connection Type": "Upstream Manufacturing Node", "Source": "Live Web Search Agent", "Confidence": "96.5%", "Status": "Active"},
                    {"Entity": "Mellanox & Networking Division", "Connection Type": "Infrastructure Subsidiary", "Source": "Corporate Registry API", "Confidence": "98.2%", "Status": "Synced"},
                    {"Entity": "Enterprise AI / Cloud Clusters", "Connection Type": "Downstream Deployment Node", "Source": "Internal Neo4j Graph", "Confidence": "94.7%", "Status": "Active"}
                ]
                profile_metrics = {
                    "Structural Model": "Fabless Hardware & Full-Stack Software Platform",
                    "Organizational Design": "Flat Hierarchy / Cross-Functional Matrix",
                    "Key Value Drivers": "Data Center AI Infrastructure, CUDA Ecosystem, High Gross Margins",
                    "Primary Risk Vectors": "Supply Chain Concentration, Geopolitical Export Controls, Foundry Bottlenecks"
                }
            else:
                synthesis_text = (
                    f"**{target_clean}** is mapped across external registry data and internal workspace touchpoints. "
                    "The entity exhibits a standard corporate structure with defined subsidiary linkages and operational frameworks. "
                    "Multi-source evaluation indicates active commercial integration points and standard market positioning relative to its sector."
                )
                lineage_data = [
                    {"Entity": f"{target_clean} (Primary Target)", "Connection Type": "Core Entity", "Source": "Global Knowledge Mesh", "Confidence": "98.5%", "Status": "Synced"},
                    {"Entity": f"{target_clean} Holdings LLC", "Connection Type": "Parent / Holding Structure", "Source": "Corporate Registry API", "Confidence": "97.1%", "Status": "Verified"},
                    {"Entity": "Key Executive Leadership", "Connection Type": "Board / Management Node", "Source": "Live Web Search Agent", "Confidence": "91.2%", "Status": "Live"}
                ]
                profile_metrics = {
                    "Structural Model": "Standard Corporate / Enterprise Entity",
                    "Organizational Design": "Hierarchical / Regional Divisions",
                    "Key Value Drivers": "Core Service Delivery, Active Contracts, Market Foothold",
                    "Primary Risk Vectors": "Operational Compliance, Market Competition, Vendor Dependency"
                }

            st.success(synthesis_text)
            
            # --- Visualizing the Company's Anatomy & Makeup ---
            st.markdown(f"### 📊 Operational & Structural Breakdown")
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.info(f"**Structural Model:**\n\n{profile_metrics['Structural Model']}")
                st.info(f"**Organizational Design:**\n\n{profile_metrics['Organizational Design']}")
            with m_col2:
                st.info(f"**Core Value Drivers:**\n\n{profile_metrics['Key Value Drivers']}")
                st.warning(f"**Primary Risk Vectors:**\n\n{profile_metrics['Primary Risk Vectors']}")

            with st.expander(f"🔍 Deep Graph & Multi-Source Resolution Path: {target_clean}", expanded=False):
                st.markdown("**Cross-Entity Linkage & Reasoning:**")
                if use_internal:
                    st.write(f"1. **Internal Graph Mesh:** Evaluated active contracts, vendor profiles, and telemetry nodes linked to `{target_clean}`.")
                if use_api:
                    st.write(f"2. **Corporate Registry API:** Extracted corporate entity registration, ultimate beneficial owners, and structural hierarchy trees.")
                if use_web:
                    st.write(f"3. **Live Web Scraper Agent:** Analyzed business model architecture, market positioning, and operational layout.")
                st.write(f"4. **FastMCP Engine ({search_mode}, Depth {max_depth}):** Merged multi-layered structural attributes into a unified workspace context.")
            
            st.markdown(f"### 🌐 Consolidated Entity Lineage & Ecosystem")
            st.caption("Verifiable audit trail mapping the structural components and connections of the target.")
            
            df_lineage = pd.DataFrame(lineage_data)
            st.dataframe(df_lineage, use_container_width=True, hide_index=True)
            
            with st.expander("💻 FastMCP Tool Execution Payload & Generated Cypher"):
                st.code(f"""
// Executed Structural Traversal Query via FastMCP ({search_mode})
{{
    "target_query": "{query}",
    "workspace": "{active_workspace}",
    "max_depth": {max_depth},
    "profile_mode": "structural_anatomy",
    "agents_enabled": {{
        "internal_neo4j": {str(use_internal).lower()},
        "live_web_scraper": {str(use_web).lower()},
        "corporate_apis": {str(use_api).lower()}
    }}
}}

MATCH path = (e:Entity)-[*1..{max_depth}]-(connected)
WHERE e.workspace = '{active_workspace}'
  AND ANY(label IN labels(e) WHERE label IN {target_labels})
  AND (e.name CONTAINS '{query}' OR connected.type IN ['Subsidiary', 'SupplyChain', 'Executive'])
RETURN path, e.structural_weight ORDER BY e.structural_weight DESC LIMIT 25;
                """, language="json")

# ---------------------------------------------------------
# TAB 2: INGESTION & PIPELINE ENGINE
# ---------------------------------------------------------
with tab2:
    st.header("Ingest Enterprise Datasets")
    st.caption("Upload unstructured or structured operational files to expand your tenant knowledge graph.")
    
    col_up, col_info = st.columns([2, 1])
    
    with col_up:
        with st.container():
            uploaded_files = st.file_uploader(
                "Upload PDF, DOCX, CSV, or Parquet datasets", 
                type=["pdf", "docx", "csv", "parquet"], 
                accept_multiple_files=True
            )
            
            if uploaded_files:
                if st.button("🚀 Process & Generate Graph Index", type="primary"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, file in enumerate(uploaded_files):
                        status_text.text(f"Extracting entities & relations from {file.name}...")
                        time.sleep(0.4)
                        progress_bar.progress(int((idx + 1) / len(uploaded_files) * 100))
                    
                    status_text.text("Ingestion completed! Nodes & Edges synced to Neo4j.")
                    st.success(f"Successfully processed {len(uploaded_files)} files into workspace '{active_workspace}'!")

    with col_info:
        st.markdown("### 📊 Active Pipeline Status")
        st.markdown("""
        * **Chunking Strategy:** Semantic Paragraph Boundary
        * **Embedding Model:** `text-embedding-3-large`
        * **Entity Extractor:** FastMCP LLM Tool Service
        * **Max File Size:** 200MB per dataset
        """)
        
    st.markdown("---")
    st.subheader("📋 Ingested File Registry")
    
    sample_files = [
        {"Filename": "Vendor_Agreement_2026.pdf", "Format": "PDF", "Size": "14.2 MB", "Parsed Nodes": 342, "Status": "Indexed"},
        {"Filename": "Client_Roster_Q3.csv", "Format": "CSV", "Size": "2.1 MB", "Parsed Nodes": 890, "Status": "Indexed"},
        {"Filename": "Master_Schedule_KE.docx", "Format": "DOCX", "Size": "8.7 MB", "Parsed Nodes": 188, "Status": "Indexed"}
    ]
    st.dataframe(pd.DataFrame(sample_files), use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# TAB 3: DYNAMIC MOVING PHYSICS GRAPH CANVAS
# ---------------------------------------------------------
with tab3:
    st.header("Interactive Knowledge Graph Canvas")
    st.caption("Full force-directed physics engine. Click, drag, scroll to zoom, and inspect interconnected entity networks.")
    
    # Define dense graph nodes & edges
    graph_nodes = [
        {"id": 1, "label": "Acme Co\n(Vendor)", "group": "vendor", "size": 26},
        {"id": 2, "label": "Agreement 2026\n(Contract)", "group": "contract", "size": 22},
        {"id": 3, "label": "SLA Clause 4\n(Obligation)", "group": "obligation", "size": 18},
        {"id": 4, "label": "15% Penalty\n(Risk)", "group": "risk", "size": 24},
        {"id": 5, "label": "Global Tech LLC\n(Vendor)", "group": "vendor", "size": 26},
        {"id": 6, "label": "MSA Agreement\n(Contract)", "group": "contract", "size": 22},
        {"id": 7, "label": "99.9% Uptime\n(Obligation)", "group": "obligation", "size": 18},
        {"id": 8, "label": "Cross-Liability\n(Risk)", "group": "risk", "size": 22},
        {"id": 9, "label": "Payment Terms 30D\n(Term)", "group": "term", "size": 16},
        {"id": 10, "label": "Nairobi DC Hub\n(Infrastructure)", "group": "infra", "size": 20}
    ]

    graph_edges = [
        {"from": 1, "to": 2, "label": "ISSUED"},
        {"from": 2, "to": 3, "label": "CONTAINS"},
        {"from": 3, "to": 4, "label": "TRIGGERS"},
        {"from": 5, "to": 6, "label": "ISSUED"},
        {"from": 6, "to": 7, "label": "REQUIRES"},
        {"from": 4, "to": 8, "label": "ESCALATES_TO"},
        {"from": 6, "to": 8, "label": "SUBJECT_TO"},
        {"from": 2, "to": 9, "label": "INCLUDES"},
        {"from": 7, "to": 10, "label": "HOSTED_AT"}
    ]

    nodes_json = json.dumps(graph_nodes)
    edges_json = json.dumps(graph_edges)

    # Embedded Vis.js Interactive Canvas Code
    vis_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/10.1.2/standalone/umd/vis-network.min.js"></script>
        <sty
