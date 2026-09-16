import uuid
import time
import asyncio
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

# Module Imports
from config import BACKEND_URL, APP_NAME, logger
from database import get_graph_metrics, run_cypher
from security import authenticate_api_key, validate_tenant_id, rate_limiter, write_audit_log
from refiner import process_and_store_document
from retrieval import execute_graphrag_query

st.set_page_config(page_title="Enterprise GraphRAG Dashboard", layout="wide")

# ---------------------------------------------------------
# SECURITY & AUTHENTICATION GATE
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "tenant_id" not in st.session_state:
    st.session_state["tenant_id"] = "tenant_default"

def login_screen():
    st.title("🔒 Enterprise GraphRAG Access Gate")
    st.caption("Restricted access system for enterprise knowledge database.")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        username = st.text_input("Username / Tenant Name", value="enterprise_user")
        api_key = st.text_input("Enterprise API Key / Password", type="password")
        if st.button("Authenticate Session", type="primary"):
            if authenticate_api_key(api_key):
                try:
                    tenant_clean = validate_tenant_id(username)
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = tenant_clean
                    st.session_state["tenant_id"] = tenant_clean
                    st.success("Authentication successful!")
                    st.rerun()
                except ValueError as ve:
                    st.error(f"Invalid Tenant ID: {ve}")
            else:
                st.error("Invalid API Key or Password. Access denied.")
    
    with col2:
        st.info("""
        **Security Policy Enforcement:**
        * Unauthorized access attempts are monitored and logged.
        * Sliding-window rate limiting is active per tenant.
        * Multi-tenant graph isolation enabled for all queries.
        """)

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

tenant_id = st.session_state["tenant_id"]

# ---------------------------------------------------------
# SIDEBAR - SYSTEM STATUS & CONTROLS
# ---------------------------------------------------------
st.sidebar.title(f"👤 Tenant: `{tenant_id}`")
if st.sidebar.button("🔒 Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("System Health")
try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=3)
    if response.status_code == 200:
        st.sidebar.success("FastMCP Engine: Operational ●")
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

# ---------------------------------------------------------
# MAIN DASHBOARD HEADER & LIVE TELEMETRY
# ---------------------------------------------------------
st.title("🧠 Enterprise GraphRAG Control Panel")
st.caption("Connected to Live Backend Infrastructure")

# Live Database Metrics Harvester (from database.py)
live_metrics = get_graph_metrics()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Indexed Knowledge Nodes", f"{live_metrics.get('nodes', 0):,}")
m2.metric("Active Knowledge Edges", f"{live_metrics.get('edges', 0):,}")
m3.metric("FastMCP Latency", f"{live_metrics.get('latency', 0)} ms")
m4.metric("Graph Sync Status", live_metrics.get("status", "Offline 🔴"))

st.markdown("---")

# ---------------------------------------------------------
# WORKSPACE TABS INTERFACE
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["💬 Query Engine", "📄 Ingest Documents", "🕸 Graph Inspector"])

# TAB 1: GRAPH QUERY & RETRIEVAL ENGINE
with tab1:
    st.header("Search Knowledge Graph")
    query = st.text_input("Ask a complex question across your documents:")
    if st.button("Run GraphRAG Search", type="primary"):
        if not query.strip():
            st.warning("Please enter a question.")
        elif not rate_limiter.allow(tenant_id):
            st.error("Rate limit exceeded. Please wait a minute before making more requests.")
        else:
            request_id = f"req_{uuid.uuid4().hex[:8]}"
            with st.spinner("Traversing knowledge graph and evaluating pathways..."):
                # Call live retrieval pipeline
                retrieval_response = execute_graphrag_query(
                    tenant_id=tenant_id,
                    query_text=query,
                    search_mode=search_mode,
                    max_depth=max_depth
                )
                
                st.markdown("### 🤖 Synthesized Graph Response")
                st.success(retrieval_response.get("answer", "No context retrieved."))
                
                with st.expander("🔍 Traversed Knowledge Graph Reasoning Path", expanded=True):
                    st.markdown("**Multi-Hop Entity Linkage:**")
                    reasoning_paths = retrieval_response.get("reasoning_path", [
                        f"Tenant '{tenant_id}' ➔ Initiated Search ➔ Executed Cypher Traversal"
                    ])
                    for path_step in reasoning_paths:
                        st.write(f"• {path_step}")
                
                st.markdown("### 📄 Grounded Source Evidence Lineage")
                st.caption("Verifiable audit trail connecting answer facts directly to database nodes.")
                
                lineage = retrieval_response.get("lineage", [])
                if lineage:
                    st.dataframe(pd.DataFrame(lineage), use_container_width=True)
                else:
                    st.info("No explicit source node lineages attached to this response.")
                
                with st.expander("🛠️ View FastMCP & Neo4j Cypher Execution Trace"):
                    st.code(
                        retrieval_response.get("cypher_trace", "// Query executed successfully"),
                        language="cypher"
                    )

            # Record Audit Trail via security.py
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                loop.create_task(write_audit_log(tenant_id, "GRAPH_QUERY", request_id, {"query": query}))
            else:
                loop.run_until_complete(write_audit_log(tenant_id, "GRAPH_QUERY", request_id, {"query": query}))

# TAB 2: REFINER & DOCUMENT INGESTION PIPELINE
with tab2:
    st.header("Upload Enterprise Files")
    uploaded_file = st.file_uploader("Upload PDF, DOCX, TXT, or CSV", type=["pdf", "docx", "txt", "csv"])
    doc_title = st.text_input("Document Identifier / Title", value="Enterprise_Doc_2026")
    
    col1, col2 = st.columns(2)
    with col1:
        extract_ner = st.checkbox("Extract Named Entities (NER)", value=True)
    with col2:
        link_nodes = st.checkbox("Link to Existing Nodes", value=True)
        
    if uploaded_file is not None:
        if st.button("Extract Entities & Build Knowledge Graph", type="primary"):
            if not rate_limiter.allow(tenant_id):
                st.error("Rate limit exceeded. Please wait before uploading more files.")
            else:
                with st.spinner("Parsing document structure and refining entity triples..."):
                    file_text = uploaded_file.read().decode("utf-8", errors="ignore")
                    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
                    
                    # Live Document Ingestion Call (refiner.py)
                    success, msg, stats = process_and_store_document(
                        tenant_id=tenant_id,
                        document_id=doc_id,
                        title=doc_title,
                        text=file_text
                    )
                    
                    if success:
                        st.success(msg)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Client Identified", stats.get("client", "General"))
                        c2.metric("Project Mapped", stats.get("project", "Default"))
                        c3.metric("Entities Extracted", stats.get("entities_extracted", 0))
                    else:
                        st.error(msg)

    st.markdown("---")
    st.subheader("📁 Ingested Knowledge Base Repository")
    st.caption("Active enterprise documents mapped inside the Neo4j graph for this tenant.")
    
    # Query Live Ingested Documents from Neo4j
    doc_query = """
    MATCH (t:Tenant {id: $tenant_id})-[:OWNS]->(d:Document)
    RETURN d.id AS Document_ID, d.title AS Title, d.updated_at AS Last_Processed
    LIMIT 25
    """
    raw_docs = run_cypher(doc_query, {"tenant_id": tenant_id})
    if raw_docs:
        st.dataframe(pd.DataFrame(raw_docs), use_container_width=True)
    else:
        st.info("No documents uploaded for this tenant yet.")

# TAB 3: LIVE GRAPH INSPECTOR & VISUALIZATION
with tab3:
    st.header("Knowledge Graph Connections")
    st.caption("Visual entity topology for active graph nodes.")
    
    # Fetch Live Nodes and Edges from Neo4j
    nodes_cypher = """
    MATCH (t:Tenant {id: $tenant_id})-[:OWNS]->(d:Document)-[:MENTIONS]->(n)
    RETURN DISTINCT n.name AS Entity_Name, labels(n)[0] AS Category
    LIMIT 30
    """
    edges_cypher = """
    MATCH (t:Tenant {id: $tenant_id})-[:OWNS]->(d:Document)-[:MENTIONS]->(a)
    MATCH (a)-[r]->(b)
    RETURN a.name AS Source, type(r) AS Relationship, b.name AS Target
    LIMIT 30
    """
    
    live_nodes = run_cypher(nodes_cypher, {"tenant_id": tenant_id})
    live_edges = run_cypher(edges_cypher, {"tenant_id": tenant_id})

    st.subheader("🕸️ Interactive Knowledge Graph Canvas")
    if live_nodes:
        try:
            net = Network(height="380px", width="100%", bgcolor="#0e1117", font_color="white")
            for node in live_nodes:
                name = node.get("Entity_Name", "Unknown")
                cat = node.get("Category", "Entity")
                net.add_node(name, label=name, title=f"Category: {cat}")
                
            for edge in live_edges:
                net.add_edge(
                    edge.get("Source"), 
                    edge.get("Target"), 
                    title=edge.get("Relationship"), 
                    label=edge.get("Relationship")
                )
                
            net.save_graph("graph.html")
            components.html(open("graph.html", "r").read(), height=395)
        except Exception as e:
            st.warning(f"Interactive canvas rendering skipped: {e}")
    else:
        st.info("Graph canvas empty. Upload documents in Tab 2 to populate live nodes.")

    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Indexed Entity Records")
        if live_nodes:
            st.dataframe(pd.DataFrame(live_nodes), use_container_width=True)
        else:
            st.caption("No entity records indexed.")
            
    with col_b:
        st.subheader("Mapped Relationships")
        if live_edges:
            st.dataframe(pd.DataFrame(live_edges), use_container_width=True)
        else:
            st.caption("No relationship edges mapped.")
            

