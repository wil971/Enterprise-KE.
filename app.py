"""Enterprise Knowledge Workspace — production-oriented Streamlit frontend.

This frontend expects a separately deployed API implementing the routes listed
in the API Diagnostics tab. Security, tenant authorization, durable storage,
and document processing must be enforced by that backend.
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

import pandas as pd
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# Page configuration and configuration loading
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Enterprise Intelligence Workspace",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def setting(name: str, default: str = "") -> str:
    """Read a setting from Streamlit secrets first, then environment."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, default) or default)


BACKEND_URL = setting("BACKEND_URL").rstrip("/")
APP_USERNAME = setting("APP_USERNAME")
APP_PASSWORD = setting("APP_PASSWORD")
REQUEST_TIMEOUT = int(setting("REQUEST_TIMEOUT", "60"))
MAX_UPLOAD_MB = int(setting("MAX_UPLOAD_MB", "25"))
ALLOWED_EXTENSIONS = ["pdf", "docx", "csv", "parquet", "txt", "md"]

# -----------------------------------------------------------------------------
# Visual system
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root { --ink:#e8eef8; --muted:#91a0b8; --panel:#101a2b; --line:#26364e; }
    .stApp { background: radial-gradient(ellipse at 15% 0%, #14233b 0%, #080e19 48%); }
    #MainMenu, footer { visibility:hidden; }
    section[data-testid="stSidebar"] { background:#0b1423; border-right:1px solid #26364e; }
    .hero { padding:24px 28px; border:1px solid #2c405d; border-radius:18px;
            background:linear-gradient(120deg,rgba(17,36,62,.98),rgba(13,24,42,.96));
            margin-bottom:18px; }
    .eyebrow { color:#66d9ef; text-transform:uppercase; letter-spacing:.14em;
               font-size:.72rem; font-weight:800; }
    .hero h1 { color:#f4f7fc; margin:.35rem 0; font-size:2rem; }
    .hero p { color:#a6b5ca; margin:0; }
    .metric-card { background:linear-gradient(145deg,#13213a,#101a2b);
                   border:1px solid #293d59; border-radius:14px; padding:17px 19px;
                   min-height:115px; }
    .metric-label { color:#9aabc2; font-size:.75rem; font-weight:700;
                    letter-spacing:.06em; text-transform:uppercase; }
    .metric-value { color:#f4f7fc; font-size:1.35rem; font-weight:800;
                    margin-top:9px; overflow-wrap:anywhere; }
    div.stButton > button[kind="primary"] { background:linear-gradient(90deg,#087cae,#075985);
        border:0; color:white; font-weight:700; border-radius:9px; }
    div.stButton > button { border-radius:9px; }
    div[data-testid="stTabs"] button { font-weight:650; }
    .subtle { color:#9aabc2; font-size:.88rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
DEFAULTS = {
    "authenticated": False,
    "demo_authenticated": False,
    "user": "",
    "search_history": [],
    "upload_results": [],
    "last_query_result": None,
    "graph_payload": None,
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


# -----------------------------------------------------------------------------
# API helpers
# -----------------------------------------------------------------------------
def api_request(method: str, path: str, *, token: str = "", **kwargs):
    if not BACKEND_URL:
        return None, "Backend URL is not configured. Add BACKEND_URL to Streamlit secrets or environment variables."
    headers = dict(kwargs.pop("headers", {}) or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(
            method=method,
            url=f"{BACKEND_URL}{path}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
        return response, None
    except requests.RequestException as exc:
        return None, f"Backend connection failed: {exc}"


def response_payload(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"text": response.text[:4000]}


def show_api_error(response, error: str | None) -> None:
    if error:
        st.error(error)
    elif response is not None:
        payload = response_payload(response)
        st.error(f"API request failed (HTTP {response.status_code}).")
        with st.expander("Technical details"):
            st.json(payload)


def render_answer(payload: Any) -> None:
    if not isinstance(payload, dict):
        st.write(payload)
        return
    answer = next((payload.get(k) for k in ("answer", "response", "result", "message") if payload.get(k)), None)
    sources = next((payload.get(k) for k in ("sources", "citations", "documents") if payload.get(k)), [])
    if answer:
        st.markdown("#### Retrieved answer")
        st.write(answer)
    if sources:
        st.markdown("#### Supporting evidence")
        if isinstance(sources, list):
            for index, source in enumerate(sources, start=1):
                title = source.get("title") or source.get("filename") or f"Evidence {index}" if isinstance(source, dict) else f"Evidence {index}"
                with st.expander(f"{index}. {title}", expanded=index == 1):
                    if isinstance(source, dict):
                        st.json(source)
                    else:
                        st.write(source)
        else:
            st.write(sources)
    if not answer and not sources:
        st.info("The API returned data, but no recognized answer or evidence fields were found.")
        st.json(payload)


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="subtle">{note}</div></div>',
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Authentication gate
# -----------------------------------------------------------------------------
def login_gate() -> None:
    st.markdown(
        '<div class="hero"><div class="eyebrow">Secure knowledge operations</div>'
        '<h1>Enterprise Intelligence Workspace</h1>'
        '<p>Search organizational knowledge, inspect evidence, and explore connected information.</p></div>',
        unsafe_allow_html=True,
    )
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        with st.form("login_form"):
            st.subheader("Sign in")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)
        if submitted:
            # This optional gate is a convenience only. Production authentication
            # and authorization must be enforced by the backend.
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
                st.warning("Demo sign-in only. Configure credentials and enforce authentication in the backend before production use.")
                st.rerun()
            else:
                st.warning("Enter both username and password.")


if not st.session_state.authenticated:
    login_gate()
    st.stop()

# -----------------------------------------------------------------------------
# Sidebar controls
# -----------------------------------------------------------------------------
st.sidebar.markdown("## ◈ Workspace")
st.sidebar.caption(f"Signed in as **{st.session_state.user or 'User'}**")
if st.session_state.demo_authenticated:
    st.sidebar.warning("Demo session — not production authentication.")

workspace = st.sidebar.selectbox(
    "Workspace",
    ["Global Enterprise", "Legal & Contracts", "Supply Chain & Vendors", "FinTech Compliance"],
)
search_mode = st.sidebar.selectbox(
    "Retrieval mode", ["Hybrid search", "Graph multi-hop", "Semantic search", "Keyword search"]
)
max_depth = st.sidebar.slider("Graph traversal depth", 1, 5, 2)
target_labels = st.sidebar.multiselect(
    "Entity filters",
    ["Vendors", "Contracts", "SLA Clauses", "Risks", "Liabilities", "Payment Terms"],
    default=["Vendors", "Contracts", "SLA Clauses", "Risks"],
)
api_token = st.sidebar.text_input(
    "Backend API token (optional)", type="password",
    help="Use a short-lived token. Do not paste credentials on a shared device.",
)
if st.sidebar.button("Sign out", use_container_width=True):
    for key in ("authenticated", "demo_authenticated", "user", "last_query_result", "graph_payload"):
        st.session_state.pop(key, None)
    st.rerun()

# -----------------------------------------------------------------------------
# Header and live service status
# -----------------------------------------------------------------------------
st.markdown(
    f'<div class="hero"><div class="eyebrow">Enterprise intelligence</div>'
    f'<h1>Knowledge Workspace</h1><p>{workspace} · Evidence-led context retrieval</p></div>',
    unsafe_allow_html=True,
)

health_response, health_error = api_request("GET", "/health", token=api_token)
if health_response is not None and health_response.ok:
    health_payload = response_payload(health_response)
    service_status = "Online"
    service_detail = health_payload
else:
    service_status = "Not verified"
    service_detail = health_error or (
        f"Health endpoint returned HTTP {health_response.status_code}" if health_response is not None else "Backend not configured"
    )

c1, c2, c3 = st.columns(3)
with c1:
    metric_card("Backend status", service_status, "Live /health response")
with c2:
    metric_card("Workspace", workspace, "Selected workspace")
with c3:
    metric_card("Retrieval mode", search_mode, f"{len(target_labels)} entity filters selected")
with st.expander("Service health details"):
    st.write(service_detail)

# -----------------------------------------------------------------------------
# Main workspace tabs
# -----------------------------------------------------------------------------
tab_search, tab_documents, tab_graph, tab_activity, tab_admin = st.tabs(
    ["⌕  Knowledge Search", "⇧  Document Ingestion", "⌘  Graph Explorer", "◷  Activity", "⚙  Diagnostics"]
)

with tab_search:
    st.subheader("Ask your organization's knowledge")
    st.caption("Search approved internal material and inspect the evidence returned by the backend.")
    with st.form("enterprise_search_form"):
        query = st.text_area(
            "Question",
            placeholder="Example: What are the renewal terms and liability limits in the vendor agreements?",
            height=115,
        )
        submitted = st.form_submit_button("Search enterprise knowledge", type="primary", use_container_width=True)
    if submitted:
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
            with st.spinner("Retrieving relevant context…"):
                response, error = api_request("POST", "/v1/graph/query", token=api_token, json=request_body)
            if error or response is None or not response.ok:
                show_api_error(response, error)
            else:
                payload = response_payload(response)
                st.session_state.last_query_result = payload
                st.session_state.search_history.insert(
                    0,
                    {"time": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
                     "query": query.strip(), "workspace": workspace, "status": response.status_code},
                )
                st.success("Search request completed. Review the answer and supporting evidence below.")
                render_answer(payload)
    if st.session_state.last_query_result is not None:
        with st.expander("View raw API response"):
            st.json(st.session_state.last_query_result)

with tab_documents:
    st.subheader("Upload and index documents")
    st.caption("Select files, review the queue, and submit them to the configured ingestion API.")
    uploaded_files = st.file_uploader(
        "Select documents", type=ALLOWED_EXTENSIONS, accept_multiple_files=True, key="document_uploader",
        help=f"Supported: {', '.join(ALLOWED_EXTENSIONS).upper()}. Maximum {MAX_UPLOAD_MB} MB per file.",
    )
    if uploaded_files:
        table = pd.DataFrame([
            {"File": f.name, "Type": f.name.rsplit(".", 1)[-1].upper(),
             "Size (MB)": round(f.size / (1024 * 1024), 2),
             "Validation": "Within limit" if f.size <= MAX_UPLOAD_MB * 1024 * 1024 else "Exceeds limit"}
            for f in uploaded_files
        ])
        st.dataframe(table, use_container_width=True, hide_index=True)
    if st.button("Upload and process selected files", type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("Select at least one file.")
        elif not BACKEND_URL:
            st.error("Configure BACKEND_URL before uploading.")
        elif any(f.size > MAX_UPLOAD_MB * 1024 * 1024 for f in uploaded_files):
            st.error(f"One or more files exceed the {MAX_UPLOAD_MB} MB limit. Remove them and try again.")
        else:
            progress = st.progress(0)
            status_area = st.empty()
            results = []
            for index, file in enumerate(uploaded_files):
                status_area.info(f"Submitting {file.name} ({index + 1}/{len(uploaded_files)})…")
                try:
                    file.seek(0)
                    multipart = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
                    form_data = {"tenant_id": workspace, "filename": file.name}
                    response, error = api_request(
                        "POST", "/v1/graph/ingest", token=api_token, files=multipart, data=form_data
                    )
                    if error:
                        results.append({"File": file.name, "Status": "Connection error", "Details": error})
                    elif response is not None and response.ok:
                        results.append({"File": file.name, "Status": "Accepted by API", "Details": response_payload(response)})
                    else:
                        results.append({"File": file.name, "Status": f"HTTP {response.status_code}", "Details": response_payload(response) if response else "No response"})
                except Exception as exc:  # Keep one bad file from aborting the batch.
                    results.append({"File": file.name, "Status": "Upload error", "Details": str(exc)})
                progress.progress((index + 1) / len(uploaded_files))
            st.session_state.upload_results = results
            status_area.success("Upload batch finished. Check each API response; acceptance does not necessarily mean indexing is complete.")
    if st.session_state.upload_results:
        st.markdown("#### Batch results")
        st.dataframe(pd.DataFrame(st.session_state.upload_results), use_container_width=True, hide_index=True)

with tab_graph:
    st.subheader("Explore graph relationships")
    st.caption("The backend should return graph nodes and edges. The explorer renders a basic relationship view when that structure is available.")
    graph_depth = st.slider("Explorer depth", 1, 5, max_depth, key="graph_depth")
    if st.button("Load graph data", type="primary", use_container_width=True):
        graph_response, graph_error = api_request(
            "GET", "/v1/graph/traverse", token=api_token,
            params={"tenant_id": workspace, "hop_depth": graph_depth, "labels": ",".join(target_labels)},
        )
        if graph_error or graph_response is None or not graph_response.ok:
            show_api_error(graph_response, graph_error)
        else:
            st.session_state.graph_payload = response_payload(graph_response)
            st.success("Graph data retrieved.")
    graph_payload = st.session_state.graph_payload
    if graph_payload:
        nodes = graph_payload.get("nodes", []) if isinstance(graph_payload, dict) else []
        edges = graph_payload.get("edges", []) if isinstance(graph_payload, dict) else []
        if nodes and isinstance(nodes, list):
            node_ids = {str(n.get("id")): str(n.get("label", n.get("id"))) for n in nodes if isinstance(n, dict) and n.get("id") is not None}
            dot = ["graph KnowledgeGraph {", '  graph [bgcolor="transparent", overlap=false];',
                   '  node [shape=box, style="rounded,filled", fillcolor="#163451", fontcolor="white", color="#4c8eb5"];',
                   '  edge [color="#6b829b", fontcolor="#aabbd0"];']
            for node_id, label in node_ids.items():
                safe_id = "n" + "".join(ch if ch.isalnum() else "_" for ch in node_id)
                dot.append(f'  "{safe_id}" [label="{label[:80].replace(chr(34), chr(39))}"];')
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                source = str(edge.get("from", edge.get("source", "")))
                target = str(edge.get("to", edge.get("target", "")))
                if source in node_ids and target in node_ids:
                    sid = "n" + "".join(ch if ch.isalnum() else "_" for ch in source)
                    tid = "n" + "".join(ch if ch.isalnum() else "_" for ch in target)
                    label = str(edge.get("label", "" )).replace('"', "'")[:50]
                    dot.append(f'  "{sid}" -- "{tid}" [label="{label}"];')
            dot.append("}")
            st.graphviz_chart("\n".join(dot), use_container_width=True)
            st.caption(f"Rendered {len(node_ids)} nodes. Graph visualization is limited to the nodes and edges returned by the API.")
        else:
            st.info("No nodes array was found. Showing the raw response for backend schema inspection.")
        with st.expander("Raw graph response"):
            st.json(graph_payload)
    else:
        st.info("Load graph data to inspect relationships.")

with tab_activity:
    st.subheader("Recent session activity")
    st.caption("This view is session-scoped. For production audit history, persist events in the backend.")
    if st.session_state.search_history:
        st.dataframe(pd.DataFrame(st.session_state.search_history), use_container_width=True, hide_index=True)
    else:
        st.info("No searches in this session yet.")
    if st.session_state.upload_results:
        st.markdown("#### Latest upload batch")
        st.dataframe(pd.DataFrame(st.session_state.upload_results), use_container_width=True, hide_index=True)

with tab_admin:
    st.subheader("API diagnostics")
    st.write("Configured base 
