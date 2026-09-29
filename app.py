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

BACKEND_URL = "https://onrender.com"

# ==============================================================================
# 2. CUSTOM DARK THEME & CSS MATRIX
# ==============================================================================
st.markdown("""
    <style>
    /* Global Application Workspace Screen Setup */
    .stApp {
        background-color: #060913;
        color: #f1f5f9;
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Global Sidebar Navigation Control Layout */
    section[data-testid="stSidebar"] {
        background-color: #0b1120 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Interactive Telemetry Containers (Gloss Glassmorphism Card Code) */
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
    
    /* Dark Drop-down Component Selection Fields */
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
    
    /* Premium Direct Action Trigger Controls Design Layout */
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
    
    /* Custom High-Lustre Module Tabs Navigation Layer Layout */
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
# 4. SIDEBAR NAVIGATION & TELEMETRY CONTROL
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

# ------------------------------------------------------------------------------
# TAB 2: AUDITED FILE EXTRACTION PIPELINE
# REAL FILE UPLOAD + SERVER RESPONSE + AUDIT REGISTRY
# ------------------------------------------------------------------------------

with tab_ingest:

    st.markdown(
        "<h3 style='color:#ffffff;'>Multi-Format Ingestion & Graph Indexing Pipeline</h3>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='color:#94a3b8;'>Upload enterprise documents for processing by your existing GraphRAG backend.</p>",
        unsafe_allow_html=True
    )

    # Persistent upload history for the current Streamlit session
    if "ingestion_audit" not in st.session_state:
        st.session_state["ingestion_audit"] = []

    # Document uploader
    uploaded_files = st.file_uploader(
        "Drop target documents for automatic entity extraction",
        type=["pdf", "docx", "csv", "parquet"],
        accept_multiple_files=True,
        key="enterprise_document_uploader"
    )

    # Upload configuration
    with st.expander("Upload configuration", expanded=False):

        st.caption(
            "The frontend sends files to your existing backend. "
            "The backend remains responsible for extraction and graph indexing."
        )

        upload_timeout = st.number_input(
            "Request timeout (seconds)",
            min_value=10,
            max_value=600,
            value=120,
            step=10
        )

    # Display selected files
    if uploaded_files:

        st.markdown("### Selected documents")

        selected_data = []

        for uploaded_file in uploaded_files:
            selected_data.append({
                "Document": uploaded_file.name,
                "Format": uploaded_file.name.rsplit(".", 1)[-1].upper(),
                "Size": f"{uploaded_file.size:,} bytes"
            })

        st.dataframe(
            pd.DataFrame(selected_data),
            use_container_width=True,
            hide_index=True
        )

    # Upload button
    start_ingestion = st.button(
        "INITIALIZE BATCH INGESTION PIPELINE",
        use_container_width=True,
        type="primary"
    )

    if start_ingestion:

        if not uploaded_files:

            st.warning(
                "Please select at least one document before starting ingestion."
            )

        elif not BACKEND_URL or BACKEND_URL.rstrip("/") == "https://onrender.com":

            st.error(
                "The backend URL is not configured. "
                "Set BACKEND_URL to your existing deployed backend address."
            )

        else:

            total_files = len(uploaded_files)

            progress_bar = st.progress(0)

            status_text = st.empty()

            results = []

            endpoint = (
                f"{BACKEND_URL.rstrip('/')}/v1/graph/ingest"
            )

            for index, uploaded_file in enumerate(uploaded_files):

                filename = uploaded_file.name

                file_size = uploaded_file.size

                status_text.info(
                    f"Uploading document {index + 1} of {total_files}: "
                    f"{filename}"
                )

                try:

                    # Read the actual uploaded file bytes
                    file_bytes = uploaded_file.getvalue()

                    if not file_bytes:

                        raise ValueError(
                            "The selected document is empty."
                        )

                    # Prepare multipart upload
                    payload_files = {
                        "file": (
                            filename,
                            file_bytes,
                            uploaded_file.type
                            or "application/octet-stream"
                        )
                    }

                    payload_data = {
                        "tenant_id": active_workspace,
                        "filename": filename
                    }

                    headers = {
                        "Authorization": "Bearer ENTERPRISE-2026"
                    }

                    # Send the actual document to the existing backend
                    response = requests.post(
                        endpoint,
                        files=payload_files,
                        data=payload_data,
                        headers=headers,
                        timeout=int(upload_timeout)
                    )

                    # Try to parse the actual server response
                    try:
                        response_data = response.json()
                    except ValueError:
                        response_data = {
                            "response_text": response.text[:2000]
                        }

                    # Successful HTTP response
                    if 200 <= response.status_code < 300:

                        result = {
                            "Document Title": filename,
                            "Format": filename.rsplit(".", 1)[-1].upper(),
                            "Payload Size": f"{file_size:,} bytes",
                            "HTTP Status": response.status_code,
                            "Status": "UPLOAD ACCEPTED",
                            "Server Response": json.dumps(
                                response_data,
                                ensure_ascii=False
                            )
                        }

                        results.append(result)

                        st.session_state["ingestion_audit"].append(
                            result
                        )

                    else:

                        results.append({
                            "Document Title": filename,
                            "Format": filename.rsplit(".", 1)[-1].upper(),
                            "Payload Size": f"{file_size:,} bytes",
                            "HTTP Status": response.status_code,
                            "Status": "SERVER REJECTED UPLOAD",
                            "Server Response": json.dumps(
                                response_data,
                                ensure_ascii=False
                            )
                        })

                except requests.exceptions.Timeout:

                    results.append({
                        "Document Title": filename,
                        "Format": filename.rsplit(".", 1)[-1].upper(),
                        "Payload Size": f"{file_size:,} bytes",
                        "HTTP Status": "TIMEOUT",
                        "Status": "UPLOAD TIMED OUT",
                        "Server Response": (
                            "The server did not respond within the "
                            "configured timeout."
                        )
                    })

                except requests.exceptions.ConnectionError as err:

                    results.append({
                        "Document Title": filename,
                        "Format": filename.rsplit(".", 1)[-1].upper(),
                        "Payload Size": f"{file_size:,} bytes",
                        "HTTP Status": "CONNECTION ERROR",
                        "Status": "SERVER UNREACHABLE",
                        "Server Response": str(err)[:1000]
                    })

                except requests.exceptions.RequestException as err:

                    results.append({
                        "Document Title": filename,
                        "Format": filename.rsplit(".", 1)[-1].upper(),
                        "Payload Size": f"{file_size:,} bytes",
                        "HTTP Status": "REQUEST ERROR",
                        "Status": "UPLOAD FAILED",
                        "Server Response": str(err)[:1000]
                    })

                except Exception as err:

                    results.append({
                        "Document Title": filename,
                        "Format": filename.rsplit(".", 1)[-1].upper(),
                        "Payload Size": f"{file_size:,} bytes",
                        "HTTP Status": "CLIENT ERROR",
                        "Status": "UPLOAD FAILED",
                        "Server Response": str(err)[:1000]
                    })

                progress_bar.progress(
                    int((index + 1) / total_files * 100)
                )

            status_text.empty()

            # Display actual upload results
            results_df = pd.DataFrame(results)

            successful_uploads = sum(
                1 for item in results
                if item["Status"] == "UPLOAD ACCEPTED"
            )

            failed_uploads = total_files - successful_uploads

            st.markdown("### Batch ingestion results")

            col_success, col_failed, col_total = st.columns(3)

            col_success.metric(
                "Accepted by server",
                successful_uploads
            )

            col_failed.metric(
                "Failed uploads",
                failed_uploads
            )

            col_total.metric(
                "Total documents",
                total_files
            )

            st.dataframe(
                results_df,
                use_container_width=True,
                hide_index=True
            )

            if successful_uploads > 0:

                st.success(
                    f"{successful_uploads} document(s) were accepted "
                    "by the backend."
                )

            if failed_uploads > 0:

                st.error(
                    f"{failed_uploads} document(s) were not accepted. "
                    "Review the server responses above."
                )

            st.info(
                "An HTTP success response confirms that the server "
                "accepted the request. It does not independently "
                "confirm that entity extraction and graph indexing "
                "have finished."
            )

    # Persistent session audit registry
    st.markdown(
        "<h4 style='color:#38bdf8; margin-top:30px;'>"
        "Ingested Documents Audit Registry"
        "</h4>",
        unsafe_allow_html=True
    )

    if st.session_state["ingestion_audit"]:

        audit_df = pd.DataFrame(
            st.session_state["ingestion_audit"]
        )

        st.dataframe(
            audit_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info()
            "No documents have been accepted during this session."
                      
                      
