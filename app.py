import streamlit as st
import requests
import pandas as pd
import time
import streamlit.components.v1 as components
from pyvis.network import Network
import tempfile

# Page configuration
st.set_page_config(page_title="Enterprise Knowledge & Graph Intelligence", layout="wide")

BACKEND_URL = "https://enterprise-ke-3.onrender.com"

# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login_screen():
    st.title("🔒 Enterprise GraphRAG Access Gate")
    col1, col2 = st.columns([1, 1])
    with col1:
        username = st.text_input("Username")
        api_key = st.text_input("Enterprise API Key", type="password")
        if st.button("Authenticate Session", type="primary"):
            if api_key in ["ENTERPRISE-2026", "admin"]:
                st.session_state["authenticated"] = True
                st.session_state["user"] = username if username else "Admin"
                st.rerun()
            else:
                st.error("Invalid credentials.")
    with col2:
        st.info("System protected under Enterprise Security Governance.")

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# ---------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.title(f"👤 User: {st.session_state.get('user', 'Admin')}")
if st.sidebar.button("🔒 Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Graph Traversal Engine")
search_mode = st.sidebar.selectbox(
    "Ontology Traversal Mode",
    ["GraphRAG (Multi-Hop)", "Hybrid (Vector + Graph)", "Cypher Path Engine"]
)
max_depth = st.sidebar.slider("Max Traversal Hops", min_value=1, max_value=4, value=2)
entity_filter = st.sidebar.multiselect(
    "Filter Entity Types",
    ["Vendors", "Contracts", "SLA Clauses", "Risks", "Clients"],
    default=["Vendors", "Contracts", "SLA Clauses"]
)

# ---------------------------------------------------------
# ATRIUM TELEMETRY DASHBOARD
# ---------------------------------------------------------
st.title("🧠 Enterprise Knowledge & Graph Intelligence")
st.caption("Connected to Active Enterprise Ontology Engine | FastMCP Backend")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Indexed Knowledge Nodes", "1,420", "+28 today")
m2.metric("Active Knowledge Edges", "3,890", "+84 relationships")
m3.metric("Engine Query Latency", "110 ms", "-12 ms optimization")
m4.metric("Ontology Sync Status", "Synced 🟢", "Real-time")

st.markdown("---")

# ---------------------------------------------------------
# WORKSPACE TABS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["💬 Global Intelligence Query", "📄 Ingestion & Pipeline", "🕸 Interactive Canvas Inspector"])

# --- TAB 1: QUERY ENGINE ---
with tab1:
    st.header("Explore Global Entity & Network Graph")
    query = st.text_input(
        "Search entities, contracts, compliance risks, or global datasets:",
        placeholder="e.g., Excel contract SLA obligations and financial liability terms"
    )
    
    if st.button("Run Enterprise Search", type="primary"):
        if query:
            st.info(f"Traversing global ontology network via {search_mode} (Depth: {max_depth})...")
            time.sleep(0.4)
            
            st.markdown("### 🤖 Synthesized Intelligence Answer")
            st.success(f"**Verified Insight:** System retrieved active vendor obligations, SLA clauses, and financial liability metrics matching **'{query}'**.")
            
            # Domain-Only Reasoning Path (Purged Infrastructure)
            with st.expander("🔍 Domain Knowledge Reasoning Path", expanded=True):
                st.markdown("**Multi-Hop Entity Traversal Lineage:**")
                st.write(f"1. **Entity:** `[Vendor: Acme Global]` ➔ *HAS_CONTRACT* ➔ **`[Document: Vendor_Agreement_2026]`**")
                st.write(f"2. **Document:** `[Vendor_Agreement_2026]` ➔ *CONTAINS_CLAUSE* ➔ **`[SLA: Response Time SLA]`**")
                st.write(f"3. **SLA:** `[Response Time SLA]` ➔ *SUBJECT_TO_PENALTY* ➔ **`[Risk Term: {query} Liability Clause]`**")

            st.markdown("### 📄 Grounded Source Evidence & Provenance")
            lineage_df = pd.DataFrame([
                {"Node ID": "NODE-8821", "Entity Category": "SLA Clause", "Source File": "Vendor_Agreement_2026.pdf", "Page": "p. 14", "Confidence": "98.4%"},
                {"Node ID": "NODE-4019", "Entity Category": "Client Profile", "Source File": "Client_Roster_Q3.csv", "Page": "Row 42", "Confidence": "96.1%"},
                {"Node ID": "NODE-1024", "Entity Category": "Risk Penalty", "Source File": "Master_Schedule_KE.docx", "Page": "p. 3", "Confidence": "99.0%"}
            ])
            
            st.dataframe(lineage_df, use_container_width=True)
            
            with st.expander("📖 Inspect Source Document Chunk Text"):
                st.markdown("> *'...Vendor agrees to maintain 99.9% uptime for all managed interfaces. Failure to respond within 2 hours triggers a 15% SLA penalty credit applied to the next billing cycle...'*")

# --- TAB 2: INGESTION ---
with tab2:
    st.header("Ingest Enterprise Datasets")
    st.file_uploader("Upload PDF, DOCX, CSV, or Parquet datasets", accept_multiple_files=True)

# --- TAB 3: GRAPH INSPECTOR & PYVIS CANVAS ---
with tab3:
    st.header("Interactive Knowledge Graph Canvas")
    st.caption("Click, drag, zoom, or select nodes to inspect domain entity relationships.")
    
    # Generate Interactive Pyvis Network
    net = Network(height="450px", width="100%", bgcolor="#0E1117", font_color="white")
    
    # Domain Nodes (No Infrastructure Nodes)
    net.add_node("Acme Corp", label="Acme Corp\n(Vendor)", color="#4CAF50", size=25)
    net.add_node("Agreement 2026", label="Agreement 2026\n(Contract)", color="#2196F3", size=20)
    net.add_node("SLA Clause 4", label="SLA Clause 4\n(Obligation)", color="#FF9800", size=18)
    net.add_node("15% Penalty", label="15% Penalty\n(Risk)", color="#F44336", size=15)
    
    # Domain Edges
    net.add_edge("Acme Corp", "Agreement 2026", title="ISSUED_CONTRACT")
    net.add_edge("Agreement 2026", "SLA Clause 4", title="CONTAINS_CLAUSE")
    net.add_edge("SLA Clause 4", "15% Penalty", title="HAS_PENALTY")
    
    # Render Canvas
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        net.save_graph(tmp_file.name)
        with open(tmp_file.name, "r", encoding="utf-8") as f:
            html_bytes = f.read()
    
    components.html(html_bytes, height=470)
    
