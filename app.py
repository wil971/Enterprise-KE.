import streamlit as st
import pandas as pd
import json
import time
import requests
import streamlit.components.v1 as components

# 1. PAGE SETUP
st.set_page_config(page_title="GraphRAG Context Engine", layout="wide", initial_sidebar_state="expanded")

# 2. SIDEBAR CONFIGURATION (Added LLM Selector & API Key)
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    active_workspace = st.selectbox("Active Security Boundary", ["Global Enterprise Knowledge Graph", "HR Confidential Sandbox", "Finance Ledger Audit"])
    
    st.markdown("### 🧠 AI Model Engine")
    llm_provider = st.selectbox("Select Reasoning Engine", ["OpenAI GPT-4o", "Google Gemini 1.5 Pro", "Anthropic Claude 3.5 Sonnet"])
    api_key_input = st.text_input("Enterprise API Key", type="password", placeholder="Enter key (sk-...)")
    
    max_depth = st.slider("Traversal Hop Depth", 1, 5, 2)
    target_labels = st.multiselect("Entity Filters", ["Vendors", "Contracts", "SLA Clauses", "Risks", "Liabilities"], default=["Vendors", "Contracts", "SLA Clauses", "Risks"])
    
    st.markdown("---")
    st.caption("Backend Gateway: `https://graphrag-fastmcp.onrender.com`")

BACKEND_URL = "https://graphrag-fastmcp.onrender.com"

# 3. MAIN HEADER & METRICS
st.markdown("<h1 style='color:#ffffff; margin-bottom:5px;'>ENTERPRISE KNOWLEDGE GRAPH CONTEXT ENGINE</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#94a3b8;'>Asynchronous FastMCP Processing Instance Gateway: 🟢 <code>{active_workspace}</code></p>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("INDEXED METADATA NODES", "1,420", "+ 28 linked today")
m2.metric("ACTIVE STRUCTURAL EDGES", "3,890", "+ 342 obs sync avg")
m3.metric("FASTMCP ROUTER LATENCY", "110 ms", "- 12ms optimization")
m4.metric("SYNC COMPLIANCE", "100%", "SECURE 🟢 Real-time")

st.markdown("<hr style='border-color: #1e293b;'>", unsafe_allow_html=True)

# 4. TABS DEFINITION
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
    
    # User input for dynamic querying
    user_query = st.text_input(
        "Enter Enterprise Subgraph Query Target", 
        value="What are the contractual liability thresholds and uptime SLA penalties for core vendor software agreements?",
        key="query_input"
    )
    
    col_act, _ = st.columns([1, 2])
    with col_act:
        run_query = st.button("EXECUTE FAST_MCP MULTI-HOP GRAPH SEARCH", use_container_width=True)
    
    if run_query:
        if not user_query.strip():
            st.warning("Please enter a query before searching.")
        else:
            # DYNAMIC PROGRESS TRACER
            with st.status(f"Tracing Subgraph Dependencies via {llm_provider}...", expanded=True) as status:
                st.write(f"🔹 Ingesting query: *'{user_query}'*...")
                time.sleep(0.4)
                st.write(f"🔹 Traversing target labels: {', '.join(target_labels)} up to {max_depth} hop depth...")
                time.sleep(0.4)
                st.write("🔹 Resolving Vector Hybrid Nearest Neighbors...")
                time.sleep(0.4)
                st.write("🔹 Synthesizing Cypher Graph Path Traversal...")
                time.sleep(0.4)
                
                # Simulating dynamic response generation based on the specific query
                generated_answer = f"""
                Based on multi-hop index traversal across active enterprise agreements in **{active_workspace}** using **{llm_provider}**:
                
                * **Liability Threshold Cap:** Contractual liability for this query context is strictly capped at 12 months of recurring fees.
                * **Uptime SLA Obligations:** Core vendor agreements enforce a 99.9% monthly uptime SLA standard across all production tenants.
                * **Financial Penalties:** Outages exceeding 2 consecutive hours trigger a 5% service credit fee deduction.
                """
                
                status.update(label="Subgraph Traversal & Synthesis Complete 🟢", state="complete", expanded=False)

            # DYNAMIC SYNTHESIZED CONTEXT EXECUTIVE SUMMARY
            st.markdown(f"""
            <div style="background-color:#0b1120; border:1px solid #1e293b; border-radius:12px; padding:20px; margin-top:10px; margin-bottom:20px;">
                <div style="display:flex; align-items:center; margin-bottom:12px;">
                    <span style="font-size:1.3rem; margin-right:8px;">✨</span>
                    <h4 style="color:#ffffff; margin:0; font-weight:800; font-size:1.1rem;">
                        Synthesized Context Executive Summary ({llm_provider})
                    </h4>
                </div>
                <p style="color:#38bdf8; font-size:0.95rem; font-weight:600; margin-bottom:10px;">
                    🎯 Query Addressed: "{user_query}"
                </p>
                <div style="color:#f1f5f9; font-size:0.92rem; line-height:1.7;">
                    {generated_answer}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # INTERACTIVE CLICKABLE SOURCE CARDS (POPOVERS)
            st.markdown("<h4 style='color:#ffffff; font-size:1rem; font-weight:700;'>📄 Grounded Source Artifacts</h4>", unsafe_allow_html=True)
            art1, art2, art3, art4 = st.columns(4)
            
            with art1:
                with st.popover("📄 vendor_agreement_2026.pdf\n\nEntity: SLA Clause\nProximity: 0.984"):
                    st.markdown("#### Source Document Chunk")
                    st.info(f"Retrieved excerpt related to: '{user_query[:30]}...'\n\n\"The vendor agrees to maintain 99.9% uptime...\"")
            with art2:
                with st.popover("📄 client_roster_q3.csv\n\nEntity: Liability Rule\nProximity: 0.961"):
                    st.markdown("#### Source Document Chunk")
                    st.info("Row 42: Liability capped at 12-month trailing revenue.")
            with art3:
                with st.popover("📄 enterprise_sla_master.pdf\n\nEntity: Vendor Org\nProximity: 0.923"):
                    st.markdown("#### Source Document Chunk")
                    st.info("Section 4.1: Standard SLA terms for enterprise software deployments.")
            with art4:
                with st.popover("📄 fintech_compliance_v2.docx\n\nEntity: Risk Contact\nProximity: 0.895"):
                    st.markdown("#### Source Document Chunk")
                    st.info("Risk matrix identifying downtime as a tier-1 critical incident.")

            st.markdown("<hr style='border-color:#1e293b; margin:25px 0;'>", unsafe_allow_html=True)
            
            # EXTRACTED SUBGRAPH ENTITY TRIPLES TABLE
            st.markdown("<h4 style='color:#38bdf8; font-size:1rem;'>🕸️ Extracted Subgraph Entity Triples</h4>", unsafe_allow_html=True)
            triples_df = pd.DataFrame([
                {"Subject Entity": "Vendor: AcroCorp", "Relationship (Edge)": "ISSUED_CONTRACT", "Target Entity": "Master SLA 2026", "Source": "vendor_agreement_2026.pdf"},
                {"Subject Entity": "Master SLA 2026", "Relationship (Edge)": "ENFORCES_CLAUSE", "Target Entity": "99.9% Uptime SLA", "Source": "vendor_agreement_2026.pdf"},
                {"Subject Entity": "Master SLA 2026", "Relationship (Edge)": "GOVERNED_BY", "Target Entity": "12-Month Liability Cap", "Source": "client_roster_q3.csv"}
            ])
            st.dataframe(triples_df, use_container_width=True, hide_index=True)
                # ------------------------------------------------------------------------------
# TAB 2: AUDITED FILE EXTRACTION PIPELINE
# ------------------------------------------------------------------------------
with tab_ingest:
    st.markdown("<h3 style='color:#ffffff;'>Document Ingestion & Entity Extraction</h3>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Upload legal contracts, CSV rosters, or technical compliance PDFs", accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("RUN DISTRIBUTED GRAPH EXTRACTION"):
            with st.status("Executing Extraction Pipeline...") as status:
                st.write("Chunking documents...")
                time.sleep(0.5)
                st.write("Running NER (Named Entity Recognition)...")
                time.sleep(0.5)
                st.write("Generating Vector Embeddings...")
                time.sleep(0.5)
                status.update(label="Extraction Complete", state="complete")
            
            st.success(f"Successfully indexed {len(uploaded_files)} document(s) into {active_workspace}.")
            st.dataframe(pd.DataFrame([
                {"Timestamp": "Just now", "Action": "create_audit_log", "File": f.name, "Nodes Extracted": 14, "Status": "SUCCESS"}
                for f in uploaded_files
            ]), use_container_width=True)

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
        edges: { font: { color: '#94a3b8', size: 10, align: 'middle' }, smooth: { type: 'continuous' } },
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
        {"Endpoint Route": "/v1/graph/query", "Method": "POST", "Rate Limit": "1000 req/min"},
        {"Endpoint Route": "/v1/graph/ingest", "Method": "POST", "Rate Limit": "200 req/min"}
    ])
    st.dataframe(routes_df, use_container_width=True, hide_index=True)
    
    st.markdown("<h4 style='color:#38bdf8; margin-top:20px;'>Live Interactive Request Tester</h4>", unsafe_allow_html=True)
    col_req, col_res = st.columns(2)
    
    default_payload = json.dumps({"tenant_id": "Global", "query": "Find high liability contracts", "hop_depth": 2}, indent=2)

    with col_req:
        st.markdown("**Request Payload (JSON)**")
        request_body = st.text_area("JSON Body", value=default_payload, height=150)
        send_req_test = st.button("SEND TEST DISPATCH CALL")
        
    with col_res:
        st.markdown("**Server Response Stream**")
        if send_req_test:
            st.json({"status": 200, "dispatch_id": "DSP-998231-X", "execution_time_ms": 112, "nodes_evaluated": 42})
        else:
            st.info("Trigger 'SEND TEST DISPATCH CALL' to evaluate API endpoint performance.")

    st.markdown("<h4 style='color:#38bdf8; margin-top:20px;'>SDK Integration Snippets</h4>", unsafe_allow_html=True)
    sdk_tab_python, sdk_tab_bash = st.tabs(["🐍 Python SDK", "💻 cURL"])

    with sdk_tab_python:
        st.code(f"""import requests
url = "{BACKEND_URL}/v1/graph/query"
payload = {request_body}
response = requests.post(url, headers={{"Authorization": "Bearer YOUR_KEY"}}, json=payload)
print(response.json())""", language="python")

    with sdk_tab_bash:
        st.code(f"""curl -X POST "{BACKEND_URL}/v1/graph/query" \\
  -H "Authorization: Bearer YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{request_body}'""", language="bash")
            
