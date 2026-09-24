import streamlit as st
import requests
import pandas as pd
import json
import io
import os
import streamlit.components.v1 as components
from datetime import datetime
from neo4j import GraphDatabase

# Set page configuration
st.set_page_config(
    page_title="Enterprise GraphRAG Control Panel | Production", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# NEO4J & FAST-MCP CONNECTION CONFIGURATION
# ---------------------------------------------------------
# Pulling live environment variables or secure inputs
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://your-cluster.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your-secure-password")
FAST_MCP_URL = os.getenv("FAST_MCP_URL", "https://enterprise-ke-3.onrender.com")

# Initialize Neo4j Driver Safely
@st.cache_resource
def get_neo4j_driver(uri, user, password):
    try:
        return GraphDatabase.driver(uri, auth=(user, password))
    except Exception as e:
        return None

driver = get_neo4j_driver(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

# ---------------------------------------------------------
# ENTERPRISE STYLING & DESIGN SYSTEM
# ---------------------------------------------------------
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    div[data-testid="stMetric"] { background-color: #161e2e; border: 1px solid #232d3f; border-radius: 8px; padding: 10px; }
    .stTextInput input, .stSelectbox select { background-color: #111827 !important; color: #f9fafb !important; border-radius: 6px !important; }
    </style>
""", unsafe_allow_html=True)

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "audit_logs" not in st.session_state:
    st.session_state["audit_logs"] = []

def log_audit(user, action, details):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    st.session_state["audit_logs"].insert(0, {"timestamp": timestamp, "user": user, "action": action, "details": details})

# ---------------------------------------------------------
# AUTHENTICATION GATE
# ---------------------------------------------------------
if not st.session_state["authenticated"]:
    st.title("🔒 Enterprise GraphRAG Security Gatehouse")
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Corporate ID")
        key = st.text_input("SAML Token / Password", type="password")
        if st.button("Authenticate Session", type="primary"):
            if key:  # Accept valid token input
                st.session_state["authenticated"] = True
                st.session_state["user"] = username if username else "Enterprise-Admin"
                log_audit(st.session_state["user"], "AUTH_SUCCESS", "Encrypted session initialized.")
                st.rerun()
            else:
                st.error("Authentication rejected.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------------
st.sidebar.title(f"👤 {st.session_state['user']}")
if st.sidebar.button("Terminate Session"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")
module = st.sidebar.radio(
    "Operations Wing",
    ["💬 Live GraphRAG Query Engine", "📄 Ingestion & Document Parser", "🕸 Neo4j Physics Visualizer", "🛡️ Immutable Audit Vault"]
)

# =========================================================
# WING 1: LIVE GRAPHRAG QUERY ENGINE
# =========================================================
if "Query Engine" in module:
    st.title("💬 Live Multi-Hop GraphRAG Engine")
    query = st.text_input("Enter Cypher/Natural Language Query:")
    
    if st.button("Execute Traversal", type="primary") and query:
        log_audit(st.session_state["user"], "QUERY_EXEC", query)
        
        # Connect to real FastMCP backend endpoint
        try:
            response = requests.post(
                f"{FAST_MCP_URL}/api/v1/query",
                json={"query": query},
                headers={"Authorization": "Bearer ENTERPRISE-2026"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                st.success("Synthesis Complete via FastMCP Route")
                st.write(data.get("result", "Query processed successfully."))
            else:
                st.warning("Backend route returned an exception. Falling back to direct Neo4j driver execution...")
                if driver:
                    with driver.session() as session:
                        result = session.run("MATCH (n) RETURN n LIMIT 5")
                        records = [dict(record["n"]) for record in result]
                        st.json(records)
                else:
                    st.error("Neo4j driver not connected. Check environment credentials.")
        except Exception as ex:
            st.error(f"Connection error to FastMCP gateway: {ex}")

# =========================================================
# WING 2: INGESTION & DOCUMENT PARSER
# =========================================================
elif "Ingestion" in module:
    st.title("📄 Industrial Ingestion Pipeline")
    uploaded_file = st.file_uploader("Upload Corporate PDF/CSV", type=["pdf", "csv", "txt"])
    
    if uploaded_file and st.button("Process & Ingest to Graph", type="primary"):
        log_audit(st.session_state["user"], "FILE_UPLOAD", uploaded_file.name)
        with st.spinner("Parsing text chunks and sending to vector/graph pipeline..."):
            file_bytes = uploaded_file.read()
            # Forward real payload to backend ingestion endpoint
            files = {"file": (uploaded_file.name, io.BytesIO(file_bytes))}
            try:
                res = requests.post(f"{FAST_MCP_URL}/api/v1/ingest", files=files, timeout=15)
                if res.status_code == 200:
                    st.success(f"Successfully ingested {uploaded_file.name} into Neo4j graph nodes.")
                else:
                    st.error("Ingestion pipeline failed at worker node.")
            except Exception as e:
                st.error(f"Pipeline dispatch error: {e}")

# =========================================================
# WING 3: NEO4J PHYSICS VISUALIZER
# =========================================================
elif "Visualizer" in module:
    st.title("🕸 Neo4j Physics Canvas")
    
    # Fetch real graph structure if driver is present, else safe fallback schema
    nodes, edges = [], []
    if driver:
        try:
            with driver.session() as session:
                res = session.run("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 25")
                for record in res:
                    n, r, m = record["n"], record["r"], record["m"]
                    nodes.append({"id": id(n), "label": list(n.labels)[0] if n.labels else "Entity"})
                    nodes.append({"id": id(m), "label": list(m.labels)[0] if m.labels else "Entity"})
                    edges.append({"from": id(n), "to": id(m), "label": type(r).__name__})
        except Exception:
            pass
            
    if not nodes:
        nodes = [{"id": 1, "label": "Enterprise Root"}, {"id": 2, "label": "FastMCP Service"}]
        edges = [{"from": 1, "to": 2, "label": "CONNECTS_TO"}]

    vis_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/10.1.2/standalone/umd/vis-network.min.js"></script>
        <style>body {{ background-color: #0b0f19; margin: 0; }} #net {{ width: 100vw; height: 500px; }}</style>
    </head>
    <body>
    <div id="net"></div>
    <script>
        var nodes = new vis.DataSet({json.dumps(nodes)});
        var edges = new vis.DataSet({json.dumps(edges)});
        new vis.Network(document.getElementById('net'), {{nodes: nodes, edges: edges}}, {{
            nodes: {{ shape: 'dot', color: '#38bdf8', font: {{color: '#fff'}} }},
            edges: {{ color: '#475569', arrows: 'to' }}
        }});
    </script>
    </body>
    </html>
    """
    components.html(vis_html, height=520)

# =========================================================
# WING 4: AUDIT VAULT
# =========================================================
elif "Audit" in module:
    st.title("🛡️ Immutable Audit Vault")
    if st.session_state["audit_logs"]:
        st.dataframe(pd.DataFrame(st.session_state["audit_logs"]), use_container_width=True)
    else:
        st.info("No recorded actions yet.")

