import os
import json
import time
from typing import Any

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# =============================================================================
# Enterprise Knowledge Graph & Secure Context Retrieval — Streamlit frontend
# =============================================================================
# Configure BACKEND_URL in Streamlit secrets or environment variables.
# Example:
# BACKEND_URL = "https://your-api-service.onrender.com"
#
# Optional authentication:
# APP_USERNAME and APP_PASSWORD may be set as environment variables/secrets.
# If neither is configured, the app uses a local demo gate (not production auth).
# Never commit real credentials or API keys to source control.

st.set_page_config(
    page_title="Enterprise Knowledge Workspace",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = (
    st.secrets.get("BACKEND_URL", "")
    if hasattr(st, "secrets")
    else ""
) or os.getenv("BACKEND_URL", "")
BACKEND_URL = BACKEND_URL.rstrip("/")

APP_USERNAME = (
    st.secrets.get("APP_USERNAME", "")
    if hasattr(st, "secrets")
    else ""
) or os.getenv("APP_USERNAME", "")
APP_PASSWORD = (
    st.secrets.get("APP_PASSWORD", "")
    if hasattr(st, "secrets")
    else ""
) or os.getenv("APP_PASSWORD", "")

REQUEST_TIMEOUT = 60
ALLOWED_EXTENSIONS = ["pdf", "docx", "csv", "parquet", "txt", "md"]

# ------------------------------- Styling ------------------------------------
st.markdown(
    """
    <style>
    .stApp { background:#060913; color:#f1f5f9; }
    #MainMenu, footer { visibility:hidden; }
    section[data-testid="stSidebar"] {
        background:#0b1120; border-right:1px solid #1e293b;
    }
    .hero {
        background:linear-gradient(135deg,#0f172a,#1e293b);
        border:1px solid #334155; border-radius:14px;
        padding:22px 24px; margin-bottom:16px;
    }
    .metric {
        background:linear-gradient(135deg,#0f172a,#1e293b);
        border:1px solid #334155; border-radius:12px;
        padding:18px; min-height:112px;
    }
    .metric-label { color:#94a3b8; font-size:.78rem; font-weight:700;
                    text-transform:uppercase; }
    .metric-value { color:#f8fafc; font-size:1.75rem; font-weight:800;
                    margin-top:5px; }
    .muted { color:#94a3b8; }
    div.stButton > button {
        background:linear-gradient(90deg,#0284c7,#0369a1);
        color:white; border:0; border-radius:8px; font-weight:600;
    }
    div.stButton > button:hover { background:#0ea5e9; color:white; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- Session state --------------------------------
defaults = {
    "authenticated": False,
    "demo_authenticated": False,
    "search_history": [],
    "upload_results": [],
    "last_query_result": None,
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


def backend_request(method: str, path: str, *, token: str = "", **kwargs):
    """Call the configured API and return (response, error_message)."""
    if not BACKEND_URL:
        return None, (
            "Backend URL is not configured. Set BACKEND_URL in Streamlit "
            "secrets or environment variables."
        )
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(
            method,
            f"{BACKEND_URL}{path}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
        return response, None
    except requests.RequestException as exc:
        return None, f"Could not reach the backend: {exc}"


def show_api_error(response, error):
    if error:
        st.error(error)
        return
    try:
        detail = response.json()
    except ValueError:
        detail = response.text[:1500]
    st.error(f"API returned HTTP {response.status_code}: {detail}")


def extract_payload(response):
    try:
        return response.json()
    except ValueError:
        return {"text": response.text}


def render_answer(payload: Any):
    """Render common answer formats without assuming a specific backend schema."""
    if isinstance(payload, dict):
        answer = (
            payload.get("answer")
            or payload.get("response")
            or payload.get("result")
            or payload.get("message")
        )
        if answer:
            st.markdown("### Answer")
            st.write(answer)

        sources = (
            payload.get("sources")
            or payload.get("citations")
            or payload.get("documents")
            or []
        )
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
def login_gate():
    st.markdown(
        """
        <div class="hero" style="text-align:center">
          <h1>ENTERPRISE KNOWLEDGE WORKSPACE</h1>
          <p class="muted">Secure search, document intelligence, and graph exploration</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, center, right = st.columns([1, 1.2, 1])
    with center:
        with st.form("login_form"):
            st.subheader("Sign in")
            username = st.text_input("Username / corporate identifier")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Continue", use_container_width=True)

        if submitted:
            # This gate is only an optional frontend convenience. Production
            # authentication and authorization must be enforced by the backend.
            if APP_USERNAME and APP_PASSWORD:
                if username == APP_USERNAME and password == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.user = username
                    st.rerun()
                st.error("Incorrect username or password.")
            elif username.strip() and password.strip():
                st.session_state.authenticated = True
                st.session_state.demo_authenticated = True
                st.session_state.user = username.strip()
                st.warning(
                    "Demo gate only: configure APP_USERNAME/APP_PASSWORD and "
                    "real backend authentication before production use."
                )
                st.rerun()
            else:
                st.warning("Enter a username and password to continue.")


if not st.session_state.authenticated:
    login_gate()
    st.stop()

# -------------------------------- Sidebar ------------------------------------
st.sidebar.markdown("## Workspace")
st.sidebar.caption(f"Signed in as: {st.session_state.get('user', 'User')}")
if st.session_state.demo_authenticated:
    st.sidebar.warning("Frontend demo session — not production authentication.")

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
    ["Vendors", "Contracts", "SLA Clauses", "Risks", "Liabilities", "Payment Terms"],
    default=["Vendors", "Contracts", "SLA Clauses", "Risks"],
)
api_token = st.sidebar.text_input(
    "Backend API token (optional)", type="password",
    help="Use a short-lived token. Do not paste a password or secret into a shared device.",
)
if st.sidebar.button("Sign out", use_container_width=True):
    for key in ("authenticated", "demo_authenticated", "user"):
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

# Live health check; never display invented metrics as real telemetry.
health_response, health_error = backend_request("GET", "/health", token=api_token)
if health_response is not None and health_response.ok:
    health_payload = extract_payload(health_response)
    service_status = "Online"
    service_detail = health_payload
else:
    service_status = "Not verified"
    service_detail = health_error or (
        f"Health endpoint returned HTTP {health_response.status_code}"
        if health_response is not None else "Backend not configured"
    )

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f'<div class="metric"><div class="metric-label">Backend status</div>'
        f'<div class="metric-value">{service_status}</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="metric"><div class="metric-label">Workspace</div>'
        f'<div class="metric-value" style="font-size:1.2rem">{workspace}</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f'<div class="metric"><div class="metric-label">Retrieval mode</div>'
        f'<div class="metric-value" style="font-size:1.2rem">{search_mode}</div></div>',
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f'<div class="metric"><div class="metric-label">Selected entity filters</div>'
        f'<div class="metric-value">{len(target_labels)}</div></div>',
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
            placeholder="e.g. What are the renewal terms and liability limits in the vendor agreements?",
            height=110,
        )
        submitted = st.form_submit_button(
            "Search enterprise knowledge", use_container_width=True
        )

    if submitted:
        if not query.strip():
            st.warning("Enter a question first.")
        else:
            body = {
                "tenant_id": workspace,
                "query": query.strip(),
                "hop_depth": max_depth,
                "target_labels": target_labels,
                "mode": search_mode,
            }
            with st.spinner("Retrieving relevant context…"):
                response, error = backend_request(
                    "POST",
                    "/v1/graph/query",
                    token=api_token,
                    json=body,
                )
            if error or response is None or not response.ok:
                show_api_error(response, error)
            else:
                payload = extract_payload(response)
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
        "Choose files, review the queue, then send them to the configured ingestion API."
    )
    files = st.file_uploader(
        "Select documents",
        type=ALLOWED_EXTENSIONS,
        accept_multiple_files=True,
        help="Supported: PDF, DOCX, CSV, Parquet, TXT, and Markdown.",
        key="document_uploader",
    )

    if files:
        upload_table = pd.DataFrame(
            [
                {
                    "File": f.name,
                    "Type": f.name.rsplit(".", 1)[-1].upper(),
                    "Size (KB)": round(f.size / 1024, 1),
                }
                for f in files
            ]
        )
        st.dataframe(upload_table, use_container_width=True, hide_index=True)

    if st.button("Upload and process selected files", use_container_width=True):
        if not files:
            st.warning("Select at least one file.")
        elif not BACKEND_URL:
            st.error("Set BACKEND_URL before attempting uploads.")
        else:
            progress = st.progress(0)
            status_area = st.empty()
            results = []
            for index, file in enumerate(files):
                status_area.info(f"Uploading {file.name} ({index + 1}/{len(files)})…")
                try:
                    file.seek(0)
                    multipart = {
                        "file": (
                            file.name,
                            file.getvalue(),
                            file.type or "application/octet-stream",
                        )
                    }
                    form_data = {
                        "tenant_id": workspace,
                        "filename": file.name,
                    }
                    response, error = backend_request(
                        "POST",
                        "/v1/graph/ingest",
                        token=api_token,
                        files=multipart,
                        data=form_data,
                    )
                    if error:
                        results.append(
                            {"File": file.name, "Status": "Connection error", "Details": error}
                        )
                    elif response.ok:
                        results.append(
                            {
                                "File": file.name,
                                "Status": "Accepted by API",
                                "Details": extract_payload(response),
                            }
                        )
                    else:
                        results.append(
                            {
                                "File": file.name,
                                "Status": f"HTTP {response.status_code}",
                                "Details": extract_payload(response),
                            }
                        )
                except Exception as exc:
                    results.append(
                        {"File": file.name, "Status": "Upload error", "Details": str(exc)}
                    )
                progress.progress((index + 1) / len(files))
            st.session_state.upload_results = results
            status_area.success("Upload batch finished. Review each API result below.")

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
        "This view requests graph data from the backend. The endpoint response "
        "must provide nodes and edges for visualization."
    )
    graph_depth = st.slider(
        "Explorer depth", 1, 5, max_depth, key="graph_depth"
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
            graph_payload = extract_payload(graph_response)
            st.session_state.graph_payload = graph_payload
            st.success("Graph data retrieved.")
    graph_payload = st.session_state.get("graph_payload")
    if graph_payload:
        st.json(graph_payload)
        st.info(
            "To render an interactive network here, return a payload containing "
            "nodes [{id, label}] and edges [{from, to, label}]."
        )
    else:
        st.info("Load graph data to inspect the backend response.")

# ------------------------------- History -------------------------------------
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

# ------------------------------- API diagnostics ----------------------------
with tab_api:
    st.subheader("API diagnostics")
    st.write("Configured base URL:", BACKEND_URL or "Not configured")
    st.write("Health check:")
    if health_response is not None:
        st.write("HTTP status:", health_response.status_code)
        st.json(service_detail if isinstance(service_detail, (dict, list)) else {"detail": service_detail})
    else:
        st.warning(service_detail)

    st.markdown("#### Expected API routes")
    routes = pd.DataFrame(
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
    st.dataframe(routes, use_container_width=True, hide_index=True)

    st.warning(
        "This Streamlit frontend does not itself provide enterprise-grade "
        "authentication, encryption-at-rest, tenant isolation, or audit guarantees. "
   
