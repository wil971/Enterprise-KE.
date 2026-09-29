import os
import json
import time
from typing import Any

import pandas as pd
import requests
import streamlit as st

# =============================================================================
# Enterprise Knowledge Workspace
# Streamlit frontend for a separately deployed FastAPI backend.
# =============================================================================

st.set_page_config(
    page_title="Enterprise Knowledge Workspace",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

def get_setting(name: str, default: str = "") -> str:
    """Read a setting from Streamlit secrets, then environment variables."""
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return str(value or os.getenv(name, default)).strip()


BACKEND_URL = get_setting("BACKEND_URL").rstrip("/")
APP_USERNAME = get_setting("APP_USERNAME")
APP_PASSWORD = get_setting("APP_PASSWORD")
REQUEST_TIMEOUT = 60
UPLOAD_TIMEOUT = 180
ALLOWED_EXTENSIONS = ["pdf", "docx", "csv", "parquet", "txt", "md"]

# ------------------------------- Styling -------------------------------------

st.markdown(
    """
    <style>
    .stApp { background: #070b16; color: #f1f5f9; }
    #MainMenu, footer { visibility: hidden; }
    section[data-testid="stSidebar"] {
        background: #0b1120;
        border-right: 1px solid #1e293b;
    }
    .hero {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 22px 24px;
        margin-bottom: 16px;
    }
    .metric {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
        min-height: 112px;
    }
    .metric-label {
        color: #94a3b8;
        font-size: .78rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 1.55rem;
        font-weight: 800;
        margin-top: 5px;
        overflow-wrap: anywhere;
    }
    div.stButton > button {
        background: linear-gradient(90deg, #0284c7, #0369a1);
        color: white;
        border: 0;
        border-radius: 8px;
        font-weight: 600;
    }
    div.stButton > button:hover {
        background: #0ea5e9;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- Session state --------------------------------

DEFAULTS = {
    "authenticated": False,
    "demo_authenticated": False,
    "user": "",
    "search_history": [],
    "upload_results": [],
    "last_query_result": None,
    "graph_payload": None,
for state_key, default_value in DEFAULTS.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value


# ------------------------------- API helpers ---------------------------------

def backend_request(
    method: str,
    path: str,
    *,
    token: str = "",
    timeout: int = REQUEST_TIMEOUT,
    **kwargs: Any,
):
    """Call the backend and return (response, error_message)."""
    if not BACKEND_URL:
        return None, (
            "Backend URL is not configured. Add BACKEND_URL to "
            "Streamlit secrets or environment variables."
        )

    headers = dict(kwargs.pop("headers", {}) or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(
            method=method,
            url=f"{BACKEND_URL}{path}",
            headers=headers,
            timeout=timeout,
            **kwargs,
        )
        return response, None
    except requests.RequestException as exc:
        return None, f"Could not reach the backend: {exc}"


def response_payload(response: requests.Response) -> Any:
    """Decode JSON responses, falling back to plain text."""
    try:
        return response.json()
    except ValueError:
        return {"text": response.text[:3000]}


def show_api_error(response, error: str | None) -> None:
    if error:
        st.error(error)
        return

    if response is None:
        st.error("The backend did not return a response.")
        return

    payload = response_payload(response)
    st.error(f"API returned HTTP {response.status_code}.")
    with st.expander("Error details", expanded=True):
        st.json(payload)


def render_answer(payload: Any) -> None:
    """Render common answer formats without assuming a backend schema."""
    if isinstance(payload, dict):
        answer = (
            payload.get("answer")
            or payload.get("response")
            or payload.get("result")
            or payload.get("message")
        )
        sources = (
            payload.get("sources")
            or payload.get("citations")
            or payload.get("documents")
            or []
        )

        if answer:
            st.markdown("### Answer")
            st.write(answer)

        if sources:
            st.markdown("### Sources and evidence")
            if isinstance(sources, list):
                for index, source in enumerate(sources, start=1):
                    with st.expander(f"Source {index}", expanded=index == 1):
                        if isinstance(source, dict):
                            st.json(source)
                        else:
                            st.write(source)
            else:
                st.write(sources)

        if not answer and not sources:
            st.json(payload)
    else:
        st.write(payload)


# ----------------------------- Authentication -------------------------------

def login_gate() -> None:
    st.markdown(
        """
        <div class="hero" style="text-align:center">
          <h1>ENTERPRISE KNOWLEDGE WORKSPACE</h1>
          <p>Secure search, document intelligence, and graph exploration</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        with st.form("login_form"):
            st.subheader("Sign in")
            username = st.text_input("Username / corporate identifier")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Continue",
                use_container_width=True,
)if submitted:
            if APP_USERNAME and APP_PASSWORD:
                if username == APP_USERNAME and password == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.demo_authenticated = False
                    st.session_state.user = username
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")
            elif username.strip() and password.strip():
                st.session_state.authenticated = True
                st.session_state.demo_authenticated = True
                st.session_state.user = username.strip()
                st.warning(
                    "Demo sign-in only. Configure APP_USERNAME and "
                    "APP_PASSWORD and enforce authentication in the backend "
                    "before production use."
                )
                st.rerun()
            else:
                st.warning("Enter a username and password to continue.")


if not st.session_state.authenticated:
    login_gate()
    st.stop()

# -------------------------------- Sidebar ------------------------------------

st.sidebar.markdown("## Workspace")
st.sidebar.caption(f"Signed in as: {st.session_state.user or 'User'}")

if st.session_state.demo_authenticated:
    st.sidebar.warning("Demo session — this is not production authentication.")

workspace = st.sidebar.selectbox(
    "Workspace",
    [
        "Global Enterprise",
        "Legal & Contracts",
        "Supply Chain & Vendors",
        "FinTech Compliance",
    ],
)

search_mode = st.sidebar.selectbox(
    "Retrieval mode",
    [
        "Hybrid search",
        "Graph multi-hop",
        "Semantic search",
        "Keyword search",
    ],
)

max_depth = st.sidebar.slider("Graph traversal depth", 1, 5, 2)
target_labels = st.sidebar.multiselect(
    "Entity filters",
    [
        "Vendors",
        "Contracts",
        "SLA Clauses",
        "Risks",
        "Liabilities",
        "Payment Terms",
    ],
    default=["Vendors", "Contracts", "SLA Clauses", "Risks"],
)

api_token = st.sidebar.text_input(
    "Backend API token (optional)",
    type="password",
    help="Use a short-lived token. Do not paste a password or secret into a shared device.",
)

if st.sidebar.button("Sign out", use_container_width=True):
    for key in (
        "authenticated",
        "demo_authenticated",
        "user",
        "api_token",
    ):
        st.session_state.pop(key, None)
    st.rerun()

# --------------------------------- Header ------------------------------------

st.markdown(
    f"""
    <div class="hero">
      <h2 style="margin:0">Enterprise Knowledge Graph</h2>
      <p style="color:#38bdf8;margin:.4rem 0 0">
        Workspace: {workspace} · Evidence-backed context retrieval
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Health check: report only data actually returned by the backend.
health_response, health_error = backend_request(
    "GET",
    "/health",
    token=api_token,
)
if health_response is not None and health_response.ok:
    service_status = "Online"
    service_detail = response_payload(health_response)
else:
    service_status = "Not verified"
    if health_error:
        service_detail = health_error
    elif health_response is not None:
        service_detail = (
            f"Health endpoint returned HTTP {health_response.status_code}"
        )
    else:
        service_detail = "Backend is not configured."


metric_columns = st.columns(4)
metric_values = [
    ("Backend status", service_status),
    ("Workspace", workspace),
    ("Retrieval mode", search_mode),
    ("Entity filters", str(len(target_labels))),
]
for column, (label, value) in zip(metric_columns, metric_values):
    with column:
        st.markdown(
            f"""
            <div class="metric">
              <div class="metric-label">{label}</div>
              <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with st.expander("Backend health details"):
    st.write(service_detail)

tab_search, tab_upload, tab_graph, tab_activity, tab_api = st.tabs(
    [
        "🔎 Enterprise Search",
        "📤 Document Ingestion",
        "🕸️ Knowledge Graph",
        "🕘 Search & Upload History",
        "⚙️ API Diagnostics",
    ]
)

# ------------------------------ Enterprise search ---------------------------

with tab_search:
    st.subheader("Ask your organization's knowledge")
    st.caption(
        "Search internal material and inspect the evidence returned by your backend."
    )

    with st.form("enterprise_search_form"):
        query = st.text_area(
            "Question",
            placeholder=(
                "e.g. What are the renewal terms and liability limits "
                "in the vendor agreements?"
            ),
            height=110,
        )
        search_submitted = st.form_submit_button(
            "Search enterprise knowledge",
            use_container_width=True,
        )

    if search_submitted:
        if not query.strip():
            st.warning("Enter a question first.")
        else:
            request_body = {
                "tenant_id": workspace,
                "query": query.strip(),
                "hop_depth": max_depth,
                "target_labels": target_labels,
                "mode": search_mode,
            }
            with st.spinner("Retrieving relevant context..."):
                response, error = backend_request(
                    "POST",
                    "/v1/graph/query",
                    token=api_token,
                    json=request_body,
                )

            if error or response is None or not response.ok:
                show_api_error(response, error)
            else:
                payload = response_payload(response)
                st.session_state.last_query_result = payload
                st.session_state.search_history.insert(
                    0,
                    {
                        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": query.strip(),
                        "workspace": workspace,
                        "status": response.status_code,
                    },
                )
                st.success("Search completed.")
                render_answer(payload)

    if st.session_state.last_query_result is not None:
        with st.expander("View raw response JSON"):
            st.json(st.session_state.last_query_result)

# ------------------------------ Document ingestion --------------------------

with tab_upload:
    st.subheader("Upload and index documents")
    st.write(
        "Select files, review the queue, and send them to the configured ingestion API."
    )
    st.info(
        "The frontend can send files, but successful indexing depends on the "
        "backend implementing POST /v1/graph/ingest and returning a success response."
    )

    uploaded_files = st.file_uploader(
        "Select documents",
        type=ALLOWED_EXTENSIONS,
        accept_multiple_files=True,
        help="Supported: PDF, DOCX, CSV, Parquet, TXT, and Markdown.",
        key="document_uploader",
    )

    if uploaded_files:
        upload_table = pd.DataFrame(
            [
                {
                    "File": uploaded_file.name,
                    "Type": uploaded_file.name.rsplit(".", 1)[-1].upper(),
                    "Size (KB)": round(uploaded_file.size / 1024, 1),
                }
                for uploaded_fileuploaded_files
            ]
        )
        st.dataframe(
            upload_table,
            use_container_width=True,
            hide_index=True,
        )

    if st.button(
        "Upload and process selected files",
        use_container_width=True,
        disabled=not bool(uploaded_files),
    ):
        if not BACKEND_URL:
            st.error("Set BACKEND_URL before attempting uploads.")
        else:
            progress = st.progress(0)
            status_area = st.empty()
            batch_results = []

            for file_index, uploaded_file in enumerate(uploaded_files):
                status_area.info(
                    f"Uploading {uploaded_file.name} "
                    f"({file_index + 1}/{len(uploaded_files)})..."
                )

                try:
                    uploaded_file.seek(0)
                    multipart_files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type or "application/octet-stream",
                        )
                    }
                    form_data = {
                        "tenant_id": workspace,
                        "filename": uploaded_file.name,
                    }

                    response, error = backend_request(
                        "POST",
                        "/v1/graph/ingest",
                        token=api_token,
                        timeout=UPLOAD_TIMEOUT,
                        files=multipart_files,
                        data=form_data,
                    )

                    if error:
                        batch_results.append(
                            {
                                "File": uploaded_file.name,
                                "Status": "Connection error",
                                "Details": error,
                            }
                        )
                    elif response is not None and response.ok:
                        batch_results.append(
                            {
                                "File": uploaded_file.name,
                                "Status": "Accepted by API",
                                "Details": response_payload(response),
                            }
                        )
                    elif response is not None:
                        batch_results.append(
                            {
                                "File": uploaded_file.name,
                                "Status": f"HTTP {response.status_code}",
                                "Details": response_payload(response),
                            }
                        )
                    else:
                        batch_results.append(
                            {
                                "File": uploaded_file.name,
                                "Status": "No response",
                                "Details": "The backend returned no response.",
                            }
                        )

                except Exception as exc:
                    batch_results.append(
                        {
                            "File": uploaded_file.name,
                            "Status": "Upload error",
                            "Details": str(exc),
                        }
                    )

                progress.progress((file_index + 1) / len(uploaded_files))

            st.session_state.upload_results = batch_results
            status_area.success("Upload batch finished. Review the API result below.")

    if st.session_state.upload_results:
        st.subheader("Batch upload results")
        st.dataframe(
            pd.DataFrame(st.session_state.upload_results),
            use_container_width=True,
            hide_index=True,
        )

# ------------------------------- Graph explorer -----------------------------

with tab_graph:
    st.subheader("Explore graph relationships")
    st.caption(
        "This view requests graph data from the backend. The API should return "
        "nodes and edges to enable network visualization."
    )

    graph_depth = st.slider(
        "Explorer depth",
        1,
        5,
        max_depth,
        key="graph_depth",
    )

    if st.button("Load graph data", use_container_width=True):
        graph_response, graph_error = backend_request(
            "GET",
            "/v1/graph/traverse",
            token=api_token,
            params={
                "tenant_id": workspace,
                "hop_depth": graph_depth,
                "labels": ",".join(target_labels),
            },
        )

        if graph_error or graph_response is None or not graph_response.ok:
            show_api_error(graph_response, graph_error)
        else:
            st.session_state.graph_payload = response_payload(graph_response)
            st.success("Graph data retrieved.")

    graph_payload = st.session_state.graph_payload
    if graph_payload:
        st.json(graph_payload)
        st.info(
            "Interactive graph rendering requires the backend to return nodes "
            "such as [{id, label}] and edges such as [{from, to, label}]."
        )
    else:
        st.info("Load graph data to inspect the backend response.")

# -------------------------------- History ------------------------------------

with tab_activity:
    st.subheader("Recent activity")

    if st.session_state.search_history:
        st.dataframe(
            pd.DataFrame(st.session_state.search_history),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No searches in this session yet.")

    if st.session_state.upload_results:
        st.subheader("Latest upload activity")
        st.dataframe(
            pd.DataFrame(st.session_state.upload_results),
            use_container_width=True,
            hide_index=True,
        )

# ------------------------------ API diagnostics -----------------------------

with tab_api:
    st.subheader("API diagnostics")
    st.write("Configured base URL:", BACKEND_URL or "Not configured")
    st.write("Health check:")

    if health_response is not None:
        st.write("HTTP status:", health_response.status_code)
        if isinstance(service_detail, (dict, list)):
            st.json(service_detail)
        else:
            st.write(service_detail)
    else:
        st.warning(service_detail)

    st.markdown("#### Expected API routes")
    expected_routes = pd.DataFrame(
        [
            {
                "Method": "GET",
                "Route": "/health",
                "Purpose": "Service health check",
            },
            {
                "Method": "POST",
                "Route": "/v1/graph/query",
                "Purpose": "Retrieve answers and supporting context",
            },
            {
                "Method": "POST",
                "Route": "/v1/graph/ingest",
                "Purpose": "Upload and index a document",
            },
            {
                "Method": "GET",
                "Route": "/v1/graph/traverse",
                "Purpose": "Return graph nodes and relationships",
            },
        ]
    )
    st.dataframe(
        expected_routes,
        use_container_width=True,
        hide_index=True,
    )

    st.warning(
        "This Streamlit frontend does not itself provide enterprise-grade "
        "authentication, encryption at rest, tenant isolation, or audit guarantees. "
        "Those controls must be implemented and tested in the backend and deployment."
  )

