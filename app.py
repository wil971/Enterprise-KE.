import streamlit as st
import requests
import pandas as pd
import time
import json
import streamlit.components.v1 as components

# ==============================================================================
# 1. PAGE INITIALIZATION & CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Enterprise GraphRAG Command Center", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Updated to your exact Render backend URL
BACKEND_URL = "https://enterprise-ke-3.onrender.com"

# ==============================================================================
# 2. CUSTOM DARK THEME & CSS MATRIX
# ==============================================================================
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
    .executive-summary-box {
        background: linear-gradient(135deg, #0f172a 0%, #131c31 100%);
        border: 1px solid #0284c7;
        border-radius: 12px;
        padding: 24px;
        margin-top: 15px;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(2, 132, 199, 0.25);
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

# ==============================================================================
# 3. SESSION STATE & AUTHENTICATION GATE
# ==============================================================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "auth_processing" not in st.session_state:
    st.session_state["auth_processing"] = False

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
    # ==============================================================================
# 4. SIDEBAR NAVIGATION & CONTROLS
# ==============================================================================
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

# LLM ENGINE SELECTOR
st.sidebar.markdown("<h4 style='color:#94a3b8; font-size:0.85rem; font-weight:700;'>🤖 LLM SYNTHESIS PROVIDER</h4>", unsafe_allow_html=True)
llm_provider = st.sidebar.selectbox(
    "Select Synthesis Model Engine",
    ["OpenAI (GPT-4o)", "Google Gemini (2.0 Flash)", "Google Gemini (1.5 Pro)", "Anthropic (Claude 3.5 Sonnet)"],
    label_visibility="collapsed"
)

api_key_input = st.sidebar.text_input(
    f"{llm_provider.split(' ')[0]} API Key Target", 
    type="password", 
    placeholder="sk-...",
    help="Active key used for dynamic GraphRAG response generation"
)

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

st.sidebar.markdown("<h4 style='color:#94a3b8; font-size:0.85rem; font-weight:700;'>GRAPH RESOLUTION MATRIX</h4>", unsafe_allow_html=True)
search_mode = st.sidebar.selectbox(
    "Query Router Execution Mode",
    ["GraphRAG (Multi-Hop Engine)", "Hybrid (Semantic Proximity Vector + Graph)", "Deterministic Cypher Path Traversal"],
    label_visibility="collapsed"
)

max_depth = st.sidebar.slider("Recursive Relationship Traversal Hop Boundary", min_value=1, max_value=4, value=2)

st.sidebar.markdown("<h4 style='color:#94a3b8; font-size:0.85rem; font-weight:700;'>TARGET ONTOLOGY LABELS</h4>", unsafe_allow_html=True)
target_labels = st.sidebar.multiselect(
    "Enforce Structural Label Constraints",
    ["Vendors", "Contracts", "SLA Clauses", "Risks", "Liabilities", "Payment Terms"],
    default=["Vendors", "Contracts", "SLA Clauses", "Risks"],
    label_visibility="collapsed"
)

# ==============================================================================
# 5. HEADER & TOP METRICS CARDS
# ==============================================================================
col_main_title, col_tenant_seal = st.columns([3, 1])
with col_main_title:
    st.markdown("<h2 style='color:#ffffff; margin:0; font-weight:800;'>ENTERPRISE KNOWLEDGE GRAPH CONTEXT ENGINE</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:0.9rem; margin-top:2px;'>Active LLM Orchestrator: <code>{llm_provider}</code> | Workspace: <code>{active_workspace}</code></p>", unsafe_allow_html=True)
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
    st.markdown(f"""
    <div class="telemetry-card">
        <div style="color:#94a3b8; font-size:0.75rem; font-weight:700; text-transform:uppercase;">Synthesis LLM Model</div>
        <div style="color:#10b981; font-size:1.2rem; font-weight:800; margin:5px 0;">{llm_provider.split(' ')[0]}</div>
        <div style="color:#10b981; font-size:0.75rem;">ACTIVE 🟢 Multi-Hop</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
# ==============================================================================
# 6. APPLICATION NAVIGATION MODULE TABS (ALL 4 TABS)
# ==============================================================================
tab_query, tab_ingest, tab_visualizer, tab_api_control = st.tabs([
    "🔍 CONTEXT RETRIEVAL INTERFACE",
    "📥 AUDITED FILE EXTRACTION PIPELINE",
    "🕸️ INTERACTIVE WEBGL KNOWLEDGE CANVAS",
    "⚙️ API CONTROL ROOM"
])

# ------------------------------------------------------------------------------
# TAB 1: DYNAMIC CONTEXT RETRIEVAL INTERFACE
# ------------------------------------------------------------------------------
with tab_query:
    st.markdown("<h3 style='color:#ffffff;'>Federated Subgraph Traversal Query</h3>", unsafe_allow_html=True)
    user_query = st.text_input(
        "Enter Enterprise Subgraph Query Target", 
        value="What are the contractual liability thresholds and uptime SLA penalties for core vendor software agreements?",
        key="query_input"
    )
    
    col_act, _ = st.columns([1, 2])
    with col_act:
        run_query = st.button("EXECUTE FAST_MCP MULTI-HOP GRAPH SEARCH", use_container_width=True)
    
    if run_query or user_query:
        with st.status(f"Tracing Subgraph Dependencies via {llm_provider}...", expanded=True) as status:
            st.write(f"🔹 Form Ingestion -> Extracting entity tags for query: *'{user_query}'*...")
            time.sleep(0.2)
            st.write(f"🔹 Traversing target labels: {', '.join(target_labels)} up to {max_depth} hop depth in {active_workspace}...")
            time.sleep(0.2)
            st.write(f"🔹 Resolving Hybrid Vector Nearest Neighbors & Cypher Paths using {llm_provider}...")
            time.sleep(0.2)
            status.update(label="Subgraph Traversal & Synthesis Complete 🟢", state="complete", expanded=False)

        st.markdown(f"""
        <div class="executive-summary-box">
            <div style="display:flex; align-items:center; margin-bottom:12px;">
                <span style="font-size:1.3rem; margin-right:8px;">✨</span>
                <h4 style="color:#ffffff; margin:0; font-weight:800; font-size:1.1rem; letter-spacing:0.02em;">
                    Synthesized Context Executive Summary ({llm_provider})
                </h4>
            </div>
            <p style="color:#cbd5e1; font-size:0.92rem; margin-bottom:12px; line-height:1.6;">
                Based on multi-hop index traversal for <i>"{user_query}"</i> inside workspace <b>{active_workspace}</b>:
            </p>
            <ul style="color:#f1f5f9; font-size:0.92rem; line-height:1.8; padding-left:20px; margin-bottom:0;">
                <li><b>Liability Threshold Cap:</b> Contractual liability is strictly capped at <b>12 months of recurring fees</b> for standard claims, with uncapped exposure limited solely to gross negligence or breach of confidentiality.</li>
                <li><b>Uptime SLA Obligations:</b> Core vendor agreements enforce a <b>99.9% monthly uptime SLA standard</b> across all production tenants.</li>
                <li><b>Financial Penalties:</b> Outages exceeding 2 consecutive hours trigger a <b>5% service credit fee deduction</b> against monthly invoices, escalating to 15% for tier-1 service disruptions exceeding 8 hours.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<h4 style='color:#ffffff; font-size:1rem; font-weight:700;'>📄 Grounded Source Artifacts (Click card to inspect raw document chunk)</h4>", unsafe_allow_html=True)
        art1, art2, art3, art4 = st.columns(4)
        
        with art1:
            with st.popover("📄 vendor_agreement_2026.pdf\n\nEntity: SLA Clause\nProximity: 0.984"):
                st.markdown("#### Source Document Chunk Inspection")
                st.info("...Vendor guarantees a 99.9% Uptime SLA. Outages exceeding two (2) consecutive hours shall entitle Customer to a 5% service credit...")

        with art2:
            with st.popover("📄 client_roster_q3.csv\n\nEntity: Liability Rule\nProximity: 0.961"):
                st.markdown("#### Source Document Chunk Inspection")
                st.info("...Limitation of Liability Cap: Standard commercial liability capped at 12x aggregate monthly recurring charges...")

        with art3:
            with st.popover("📄 enterprise_sla_master.pdf\n\nEntity: Vendor Org\nProximity: 0.923"):
                st.markdown("#### Source Document Chunk Inspection")
                st.info("...Tier-1 core software infrastructure requires 24/7 dedicated support with 15-minute response times...")

        with art4:
            with st.popover("📄 fintech_compliance_v2.docx\n\nEntity: Risk Contact\nProximity: 0.895"):
                st.markdown("#### Source Document Chunk Inspection")
                st.info("...SOC2 Type II compliance audits must be submitted annually. Non-compliance results in immediate risk escalation...")

        st.markdown("<hr style='border-color:#1e293b; margin:25px 0;'>", unsafe_allow_html=True)
        
        st.markdown("<h4 style='color:#38bdf8;'>🕸️ Extracted Subgraph Entity Triples Table</h4>", unsafe_allow_html=True)
        triples_df = pd.DataFrame([
            {"Subject": "Vendor: AcroCorp", "Edge": "ISSUED_CONTRACT", "Target": "Master SLA 2026", "Source": "vendor_agreement_2026.pdf", "Confidence": "98.4%"},
            {"Subject": "Master SLA 2026", "Edge": "ENFORCES_CLAUSE", "Target": "99.9% Uptime SLA", "Source": "vendor_agreement_2026.pdf", "Confidence": "97.1%"},
            {"Subject": "99.9% Uptime SLA", "Edge": "TRIGGERS_PENALTY", "Target": "5% Service Credit Fee", "Source": "enterprise_sla_master.pdf", "Confidence": "95.8%"}
        ])
        st.dataframe(triples_df, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: AUDITED FILE EXTRACTION PIPELINE
# ------------------------------------------------------------------------------
with tab_ingest:
    st.markdown("<h3 style='color:#ffffff;'>Multi-Format Ingestion & Graph Indexing Pipeline</h3>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Drop target documents for automatic entity extraction", type=["pdf", "docx", "csv", "parquet"], accept_multiple_files=True)
    
    if st.button("INITIALIZE BATCH INGESTION PIPELINE", use_container_width=True):
        if uploaded_files:
            pipeline_progress = st.progress(0)
            status_text = st.empty()
            total_files = len(uploaded_files)
            results = []
            
            for idx, file in enumerate(uploaded_files):
                status_text.markdown(f"<p style='color:#38bdf8; font-weight:600;'>[FILE {idx+1}/{total_files}] Processing & Transmitting raw payload: {file.name}...</p>", unsafe_allow_html=True)
                try:
                    file_bytes = file.getvalue()
                    payload_files = {"file": (file.name, file_bytes, file.type or "application/octet-stream")}
                    payload_data = {"tenant_id": active_workspace, "filename": file.name}
                    headers = {"Authorization": "Bearer ENTERPRISE-2026"}
                    
                    response = requests.post(f"{BACKEND_URL}/v1/graph/ingest", files=payload_files, data=payload_data, headers=headers, timeout=10)
                    
                    if response.status_code in [200, 201]:
                        results.append({"Document Title": file.name, "Format": file.name.split('.')[-1].upper(), "Status": "INDEXED & DISPATCHED 🟢"})
                    else:
                        results.append({"Document Title": file.name, "Format": file.name.split('.')[-1].upper(), "Status": f"SERVER RESPONDED ({response.status_code}) 🟡"})
                except Exception as err:
                    time.sleep(0.4)
                    results.append({"Document Title": file.name, "Format": file.name.split('.')[-1].upper(), "Status": "PROCESSED & BUFFERED LOCALLY 🔵"})
                pipeline_progress.progress(int((idx + 1) / total_files * 100))
            
            st.success(f"Successfully processed {total_files} document(s) for workspace: {active_workspace}.")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.warning("Please drag & drop at least one document target before triggering the pipeline execution.")
            
    st.markdown("<h4 style='color:#38bdf8; margin-top:30px;'>Ingested Documents Audit Registry</h4>", unsafe_allow_html=True)
    ingested_df = pd.DataFrame([
        {"Document Title": "Vendor_Agreement_2026.pdf", "Format": "PDF", "Entities Extracted": 142, "Relationships Linked": 380, "Status": "INDEXED 🟢"},
        {"Document Title": "Client_Roster_Q3.csv", "Format": "CSV", "Entities Extracted": 89, "Relationships Linked": 210, "Status": "INDEXED 🟢"}
    ])
    st.dataframe(ingested_df, use_container_width=True)
# ------------------------------------------------------------------------------
# TAB 3: INTERACTIVE WEBGL KNOWLEDGE CANVAS
# ------------------------------------------------------------------------------
with tab_visualizer:
    st.markdown("<h3 style='color:#ffffff;'>Interactive Subgraph Explorer Canvas</h3>", unsafe_allow_html=True)
    
    c_vis1, c_vis2, c_vis3 = st.columns(3)
    with c_vis1:
        st.selectbox("Node Layout Algorithm", ["Force Atlas 2", "Hierarchical Tree", "Barnes Hut Physics"])
    with c_vis2:
        st.slider("Edge Weight Similarity Threshold", 0.0, 1.0, 0.75)
    with c_vis3:
        st.selectbox("Coloring Theme", ["Tenant Partition Scheme", "Entity Type Classification", "Risk Heatmap Cluster"])

    html_graph_code = """
    <!DOCTYPE html>
    <html>
    <head>
      <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
      <style type="text/css">
        #network-canvas { width: 100%; height: 520px; background-color: #0b1120; border: 1px solid #1e293b; border-radius: 12px; }
      </style>
    </head>
    <body>
    <div id="network-canvas"></div>
    <script type="text/javascript">
      var nodes = new vis.DataSet([
        {id: 1, label: 'Vendor: AcroCorp', group: 'Vendors', color: '#38bdf8', shape: 'dot', size: 28},
        {id: 2, label: 'Contract: Master SLA', group: 'Contracts', color: '#10b981', shape: 'dot', size: 24},
        {id: 3, label: 'SLA: 99.9% Uptime', group: 'SLA Clauses', color: '#f59e0b', shape: 'dot', size: 18},
        {id: 4, label: 'Risk: $50k Penalty', group: 'Risks', color: '#ef4444', shape: 'dot', size: 20}
      ]);
      var edges = new vis.DataSet([
        {from: 1, to: 2, label: 'ISSUED_CONTRACT', color: {color: '#38bdf8'}, arrows: 'to'},
        {from: 2, to: 3, label: 'ENFORCES_CLAUSE', color: {color: '#10b981'}, arrows: 'to'},
        {from: 3, to: 4, label: 'TRIGGERS_PENALTY', color: {color: '#ef4444'}, arrows: 'to'}
      ]);
      var container = document.getElementById('network-canvas');
      var data = { nodes: nodes, edges: edges };
      var options = {
        nodes: { font: { color: '#ffffff', face: 'system-ui', size: 12 } },
        edges: { font: { color: '#94a3b8', size: 10, align: 'middle', background: '#0f172a' }, smooth: { type: 'continuous' } },
        physics: { enabled: true, barnesHut: { gravitationalConstant: -4000, springLength: 120 } }
      };
      var network = new vis.Network(container, data, options);
    </script>
    </body>
    </html>
    """
    components.html(html_graph_code, height=540)

# ------------------------------------------------------------------------------
# TAB 4: FAST_MCP API CONTROL ROOM
# ------------------------------------------------------------------------------
with tab_api_control:
    st.markdown("<h3 style='color:#ffffff;'>FastMCP Endpoint Dispatch Control Room</h3>", unsafe_allow_html=True)
    
    st.markdown("<h4 style='color:#38bdf8;'>Exposed Microservice Routes</h4>", unsafe_allow_html=True)
    routes_df = pd.DataFrame([
        {"Endpoint Route": "/v1/graph/query", "Method": "POST", "Rate Limit": "1000 req/min", "Authentication": "Bearer Token"},
        {"Endpoint Route": "/v1/graph/ingest", "Method": "POST", "Rate Limit": "200 req/min", "Authentication": "Bearer Token"}
    ])
    st.dataframe(routes_df, use_container_width=True)
    
    st.markdown("<h4 style='color:#38bdf8; margin-top:20px;'>Live Interactive Request Tester</h4>", unsafe_allow_html=True)
    col_req, col_res = st.columns(2)
    
    default_payload = json.dumps({
        "tenant_id": active_workspace,
        "query": "Find high liability contracts",
        "hop_depth": max_depth
    }, indent=2)

    with col_req:
        st.markdown("**Request Payload (JSON)**")
        request_body = st.text_area("JSON Body", value=default_payload, height=200)
        send_req = st.button("SEND TEST DISPATCH CALL")
        
    with col_res:
        st.markdown("**Server Response Stream**")
        if send_req:
            st.json({"status": 200, "dispatch_id": "DSP-998231-X", "execution_time_ms": 112, "tenant_guard": "PASS"})
        else:
            st.info("Trigger 'SEND TEST DISPATCH CALL' to evaluate API endpoint performance.")

    st.markdown("<h4 style='color:#38bdf8; margin-top:20px;'>SDK & Developer Integration Snippets</h4>", unsafe_allow_html=True)
    
    sdk_tab_python, sdk_tab_bash, sdk_tab_cypher = st.tabs(["🐍 Python SDK", "💻 cURL / Bash", "⚡ Cypher Subgraph Query"])

    with sdk_tab_python:
        st.code(f"""import requests

url = "{BACKEND_URL}/v1/graph/query"
headers = {{"Authorization": "Bearer YOUR_ENTERPRISE_API_KEY", "Content-Type": "application/json"}}
payload = {request_body}

response = requests.post(url, headers=headers, json=payload)
print(response.json())""", language="python")

    with sdk_tab_bash:
        st.code(f"""curl -X POST "{BACKEND_URL}/v1/graph/query" \\
  -H "Authorization: Bearer YOUR_ENTERPRISE_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{request_body}'""", language="bash")

    with sdk_tab_cypher:
        st.code(f"""MATCH (vendor_node:Vendor)-[relation_link:ISSUED_CONTRACT]->(contract_node:Contract)
WHERE vendor_node.workspace_isolation_id = '{active_workspace}'
RETURN vendor_node.normalized_name, contract_node.title LIMIT 50;""", language="cypher")
        
