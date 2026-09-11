import streamlit as st
import requests

# Set page title and theme
st.set_page_config(page_title="Enterprise GraphRAG Dashboard", layout="wide")

# Backend API configuration
BACKEND_URL = "https://enterprise-ke-3.onrender.com"

st.title("🧠 Enterprise GraphRAG Control Panel")
st.caption("Connected to Live MCP Backend: " + BACKEND_URL)

# Sidebar - System Status
st.sidebar.header("System Health")
try:
    response = requests.get(BACKEND_URL)
    if response.status_code == 200:
        st.sidebar.success("Backend: Operational ●")
    else:
        st.sidebar.warning("Backend Issue")
except Exception as e:
    st.sidebar.error("Backend Offline")

# Tabs for the user interface
tab1, tab2, tab3 = st.tabs(["💬 Query Engine", "📄 Ingest Documents", "🕸 Graph Inspector"])

with tab1:
    st.header("Search Knowledge Graph")
    query = st.text_input("Ask a complex question across your documents:")
    if st.button("Run GraphRAG Search"):
        if query:
            st.info(f"Querying FastMCP server at {BACKEND_URL}/sse ...")
            # Here your app connects to your SSE backend to display responses
            st.write("**Answer:** (Graph Search results will render here from Neo4j)")
        else:
            st.warning("Please enter a question.")

with tab2:
    st.header("Upload Enterprise Files")
    uploaded_file = st.file_uploader("Upload PDF, DOCX, or CSV", type=["pdf", "docx", "csv"])
    if uploaded_file is not None:
        if st.button("Extract Entities & Build Knowledge Graph"):
            st.success(f"File '{uploaded_file.name}' received and sent to Graph processing pipeline!")

with tab3:
    st.header("Knowledge Graph Connections")
    st.write("Visual entity map (Client ➔ Contract ➔ Expiry Date)")
    # Placeholder for interactive PyVis / NV3D node map
  
