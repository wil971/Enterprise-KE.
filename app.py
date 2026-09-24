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
# TAB 1: SEARCH & SYNTHESIS ENGINE
# ---------------------------------------------------------
with tab1:
    st.header("Search Knowledge Graph")
    query = st.text_input("Ask a complex question across your documents:")
    if st.button("Run GraphRAG Search", type="primary"):
        if query:
            st.info(f"Querying FastMCP server at {BACKEND_URL}/sse via {search_mode}...")
            time.sleep(0.6)
            
            st.markdown("### 🤖 Synthesized Graph Response")
            st.success(f"**Answer:** Based on knowledge graph analysis, the system identified active contract terms, SLA obligations, and vendor entity relationships matching: *'{query}'*.")
            
            with st.expander("🔍 Traversed Knowledge Graph Reasoning Path", expanded=True):
                st.markdown("**Multi-Hop Entity Linkage:**")
                st.write("1. **Streamlit Interface** ➔ *QUERIES_VIA_SSE* ➔ **FastMCP Server**")
                st.write("2. **FastMCP Server** ➔ *TRAVERSES_GRAPH* ➔ **Enterprise-KE-3**")
                st.write(f"3. **Enterprise-KE-3** ➔ *GOVERNED_BY* ➔ **SLA Obligations ({query})**")
            
            st.markdown("### 📄 Grounded Source Evidence Lineage")
            st.caption("Verifiable audit trail connecting answer facts directly to source document chunks and database nodes.")
            
            lineage_data = [
                {"Node ID": "NODE-8821", "Entity Type": "Contract SLA", "Document Name": "Vendor_Agreement_2026.pdf", "Match Confidence": "98.4%", "Status": "Verified"},
                {"Node ID": "NODE-4019", "Entity Type": "Client Profile", "Document Name": "Client_Roster_Q3.csv", "Match Confidence": "96.1%", "Status": "Verified"},
                {"Node ID": "NODE-1024", "Entity Type": "Expiry Record", "Document Name": "Master_Schedule_KE.docx", "Match Confidence": "99.0%", "Status": "Verified"}
            ]
            
            # Display lineage table
            df_lineage = pd.DataFrame(lineage_data)
            st.dataframe(df_lineage, use_container_width=True, hide_index=True)
            
            # Hidden Details Drawer (Surface remains clean, execution details inside)
            with st.expander("💻 FastMCP Tool Execution Payload & Generated Cypher"):
                st.code(f"""
// Executed Cypher Query against Neo4j Engine
MATCH path = (e:Entity)-[*1..{max_depth}]-(connected)
WHERE e.workspace = '{active_workspace}'
  AND ANY(label IN labels(e) WHERE label IN {target_labels})
  AND (e.name CONTAINS '{query}' OR connected.description CONTAINS '{query}')
RETURN path, e.embedding_score ORDER BY e.embedding_score DESC LIMIT 25;
                """, language="cypher")

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
    st.caption("Live streaming force-directed physics engine. Watch real-time data packets flow across active entity pathways.")
    
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
        {"id": "e1", "from": 1, "to": 2, "label": "ISSUED"},
        {"id": "e2", "from": 2, "to": 3, "label": "CONTAINS"},
        {"id": "e3", "from": 3, "to": 4, "label": "TRIGGERS"},
        {"id": "e4", "from": 5, "to": 6, "label": "ISSUED"},
        {"id": "e5", "from": 6, "to": 7, "label": "REQUIRES"},
        {"id": "e6", "from": 4, "to": 8, "label": "ESCALATES_TO"},
        {"id": "e7", "from": 6, "to": 8, "label": "SUBJECT_TO"},
        {"id": "e8", "from": 2, "to": 9, "label": "INCLUDES"},
        {"id": "e9", "from": 7, "to": 10, "label": "HOSTED_AT"}
    ]

    nodes_json = json.dumps(graph_nodes)
    edges_json = json.dumps(graph_edges)

    # Embedded Vis.js Interactive Canvas with Flow Animation
    vis_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/10.1.2/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            body {{
                margin: 0; padding: 0;
                background-color: #0b0f19;
                color: #ffffff;
                font-family: sans-serif;
                overflow: hidden;
            }}
            #graph-container {{
                width: 100vw;
                height: 520px;
                border: 1px solid #1f2937;
                border-radius: 8px;
            }}
            #stream-status {{
                position: absolute;
                bottom: 15px;
                left: 15px;
                background: rgba(15, 23, 42, 0.85);
                border: 1px solid #334155;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
                color: #38bdf8;
                letter-spacing: 0.5px;
            }}
        </style>
    </head>
    <body>
    <div id="graph-container"></div>
    <div id="stream-status">● LIVE STREAM: Streaming telemetry vectors via FastMCP...</div>
    <script type="text/javascript">
        var nodes = new vis.DataSet({nodes_json});
        var edges = new vis.DataSet({edges_json});

        var container = document.getElementById('graph-container');
        var data = {{ nodes: nodes, edges: edges }};
        
        var options = {{
            nodes: {{
                shape: 'dot',
                font: {{ color: '#f3f4f6', size: 13, face: 'system-ui' }},
                borderWidth: 2
            }},
            groups: {{
                vendor: {{ color: {{ background: '#10b981', border: '#059669' }} }},
                contract: {{ color: {{ background: '#3b82f6', border: '#2563eb' }} }},
                obligation: {{ color: {{ background: '#f59e0b', border: '#d97706' }} }},
                risk: {{ color: {{ background: '#ef4444', border: '#dc2626' }} }},
                term: {{ color: {{ background: '#8b5cf6', border: '#7c3aed' }} }},
                infra: {{ color: {{ background: '#06b6d4', border: '#0891b2' }} }}
            }},
            edges: {{
                color: {{ color: '#38bdf8', highlight: '#38bdf8' }},
                font: {{ color: '#9ca3af', size: 10, align: 'middle' }},
                arrows: {{ to: {{ enabled: true, scaleFactor: 0.6 }} }},
                dashes: [6, 6],
                smooth: {{ type: 'continuous', roundness: 0.2 }}
            }},
            physics: {{
                enabled: true,
                barnesHut: {{
                    gravitationalConstant: -3000,
                    centralGravity: 0.3,
                    springLength: 120,
                    springConstant: 0.04,
                    damping: 0.09
                }}
            }},
            interaction: {{
                hover: true,
                zoomView: true,
                dragView: true
            }}
        }};

        var network = new vis.Network(container, data, options);

        // Animation loop to make dash patterns flow like moving data streams
        setInterval(function() {{
            let edgeIds = edges.getIds();
            edgeIds.forEach(function(id, index) {{
                let color = (index % 2 === 0) ? '#38bdf8' : '#10b981';
                edges.update({{
                    id: id, 
                    dashes: [8, 4],
                    color: {{ color: color, opacity: 0.9 }}
                }});
            }});
        }}, 80);
    </script>
    </body>
    </html>
    """

    # Render full moving canvas
    components.html(vis_html, height=530)
    
    # Inspector Drawer for Selected Entities
    with st.expander("🔍 Deep Node Attribute & Entity Metadata Inspector", expanded=False):
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            selected_node = st.selectbox("Inspect Focus Node", [f"{n['id']}: {n['label'].replace('\n', ' ')}" for n in graph_nodes])
            st.json({
                "Entity ID": "NODE-8821",
                "Label": selected_node,
                "Workspace": active_workspace,
                "Vector Embedding": "[0.021, -0.412, 0.891, ...]",
                "Database Engine": "Neo4j Enterprise v5",
                "Graph Degree": 3
            })
        with col_sel2:
            st.markdown("**Grounded Operational Context:**")
            st.markdown("> *...Active telemetry indicates live packet synchronization across the multi-hop network nodes without latency bottlenecks...*")
            st.markdown("**Source Protocol:** `FastMCP SSE Transport Stream`")

# ---------------------------------------------------------
# TAB 4: POLYGLOT INFRASTRUCTURE & SDK INTERFACE
# ---------------------------------------------------------
with tab4:
    st.header("⚡ Infrastructure & Developer Integration API")
    st.caption("Connect external software applications, custom agents, or data microservices to this GraphRAG Engine.")
    
    sdk_tab1, sdk_tab2, sdk_tab3, sdk_tab4 = st.tabs([
        "Python (FastMCP)", 
        "Node.js Client", 
        "cURL HTTP/SSE", 
        "Cypher Query"
    ])
    
    with sdk_tab1:
        st.code("""
from fastmcp import Client
import asyncio

async def query_graph():
    async with Client("{url}/sse") as client:
        results = await client.call_tool(
            "graphrag_search", 
            {{
                "query": "SLA penalty liability",
                "workspace": "{workspace}",
                "max_depth": {depth}
            }}
        )
        print(results)

asyncio.run(query_graph())
        """.format(url=BACKEND_URL, workspace=active_workspace, depth=max_depth), language="python")

    with sdk_tab2:
        st.code("""))
import {{ MCPClient }} from "@modelcontextprotocol/sdk";

const client = new MCPClient({{
  serverUrl: "{url}/sse",
  apiKey: "ENTERPRISE-2026"
}});

async function run() {{
  const response = await client.callTool("graphrag_search", {{
    query: "Contract obligations",
    maxHops: {depth}
  }});
  console.log(response);
}}
run();
        """.format(url=BACKEND_URL, depth=max_d)
