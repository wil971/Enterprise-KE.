
# ============================================================
# ENTERPRISE-KE | PART 1 — CORE FOUNDATION
# ============================================================

import streamlit as st
import requests
import pandas as pd
import json
import uuid
import re
import time
import math
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List

st.set_page_config(
    page_title="Enterprise-KE",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_NAME = "Enterprise-KE"
APP_VERSION = "3.0.0"
API_BASE_URL = "https://enterprise-ke-3.onrender.com"
API_TIMEOUT = 25

COLORS = {
    "bg": "#080B12",
    "surface": "#101622",
    "surface2": "#151D2B",
    "border": "#263144",
    "text": "#F2F5FA",
    "muted": "#8995A8",
    "accent": "#7C8CFF",
    "accent2": "#48D6C6",
    "danger": "#FF657A",
    "warning": "#FFC66E",
    "success": "#55D6A5"
}

STATE_DEFAULTS = {
    "authenticated": False,
    "access_token": None,
    "user": None,
    "current_page": "Overview",
    "search_query": "",
    "search_results": [],
    "documents": [],
    "collections": [],
    "team": [],
    "notifications": [],
    "chat_messages": [],
    "connectors": [],
    "selected_document": None,
    "selected_collection": None,
    "api_status": "unknown",
    "api_error": None,
    "loading": False,
    "notice": None,
    "filters": {},
    "last_refresh": None
}

def initialize_session_state():
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = (
                json.loads(json.dumps(value))
                if isinstance(value, (dict, list))
                else value
            )

initialize_session_state()

def set_notice(message, kind="info"):
    st.session_state.notice = {
        "message": str(message),
        "kind": kind,
        "time": time.time()
    }

def clear_notice():
    st.session_state.notice = None

def api_call(method, endpoint, params=None, payload=None,
              files=None, timeout=API_TIMEOUT):
    """Central API request handler."""
    headers = {}

    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=params,
            json=payload,
            files=files,
            timeout=timeout
        )

        try:
            data = response.json()
        except Exception:
            data = {"detail": response.text[:2000]}

        return {
            "ok": response.ok,
            "status": response.status_code,
            "data": data,
            "error": None if response.ok else data
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "status": 0,
            "data": None,
            "error": str(exc)
        }

def api_get(endpoint, params=None):
    return api_call("GET", endpoint, params=params)

def api_post(endpoint, payload=None):
    return api_call("POST", endpoint, payload=payload)

def api_delete(endpoint):
    return api_call("DELETE", endpoint)

def safe_list(value):
    return value if isinstance(value, list) else []

def safe_dict(value):
    return value if isinstance(value, dict) else {}

def format_datetime(value):
    if not value:
        return "—"
    try:
        return str(value).replace("T", " ")[:19]
    except Exception:
        return "—"

def inject_base_style():
    st.markdown("""
    <style>
    :root {
        --ek-bg: #080B12;
        --ek-surface: #101622;
        --ek-surface2: #151D2B;
        --ek-border: #263144;
        --ek-text: #F2F5FA;
        --ek-muted: #8995A8;
        --ek-accent: #7C8CFF;
        --ek-teal: #48D6C6;
    }

    .stApp {
        background:
          radial-gradient(ellipse at 10% 0%,
          rgba(124,140,255,.10), transparent 35%),
          var(--ek-bg);
        color: var(--ek-text);
    }

    html, body, [class*="css"] {
        font-family: Inter, system-ui, sans-serif;
    }

    h1, h2, h3, h4 {
        letter-spacing: -0.035em;
    }

    div[data-testid="stMetric"] {
        background: rgba(16,22,34,.75);
        border: 1px solid var(--ek-border);
        padding: 16px;
        border-radius: 16px;
    }

    div[data-testid="stMetricValue"] {
        color: var(--ek-text);
    }

    .ek-card {
        background: linear-gradient(
            145deg,
            rgba(21,29,43,.95),
            rgba(12,17,26,.92)
        );
        border: 1px solid var(--ek-border);
        border-radius: 18px;
        padding: 20px;
        transition: .25s ease;
    }

    .ek-card:hover {
        transform: translateY(-2px);
        border-color: rgba(124,140,255,.45);
        box-shadow: 0 12px 35px rgba(0,0,0,.20);
    }

    .ek-muted {
        color: var(--ek-muted);
    }

    .ek-pill {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 12px;
        background: rgba(124,140,255,.12);
        border: 1px solid rgba(124,140,255,.25);
    }

    button, [role="button"] {
        transition: .2s ease !important;
    }

    @media (max-width: 768px) {
        .ek-card {
            padding: 14px;
            border-radius: 14px;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        * {
            transition: none !important;
            animation: none !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

inject_base_style()

# Part 1 complete — foundational configuration
# PART 2 — APPLICATION STATE MODEL

APP_STATE = {
    "workspace": None,
    "user": None,
    "permissions": [],
    "route": "overview",
    "search": {
        "query": "",
        "filters": {},
        "results": [],
        "cursor": None,
    },
    "documents": {},
    "entities": {},
    "relationships": {},
    "collections": {},
    "conversations": {},
    "connectors": {},
    "notifications": [],
    "activity": [],
    "ui": {
        "sidebar_open": True,
        "active_panel": None,
        "selected_document": None,
        "selected_entity": None,
    },
}


def get_state(path, default=None):
    current = APP_STATE

    for key in path.split("."):
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def set_state(path, value):
    keys = path.split(".")
    current = APP_STATE

    for key in keys[:-1]:
        current = current.setdefault(key, {})

    current[keys[-1]] = value


def reset_state():
    APP_STATE.clear()
    APP_STATE.update(
        json.loads(json.dumps(APP_STATE))
    )# PART 3 — SCHEMA REGISTRY

SCHEMAS = {
    "document": {
        "required": ["id", "title"],
        "fields": [
            "id", "title", "content", "source",
            "mime_type", "owner", "permissions",
            "created_at", "updated_at", "metadata",
        ],
    },
    "person": {
        "required": ["id", "name"],
        "fields": [
            "id", "name", "email", "department",
            "role", "manager_id", "metadata",
        ],
    },
    "entity": {
        "required": ["id", "label", "type"],
        "fields": [
            "id", "label", "type", "description",
            "properties", "source_ids",
        ],
    },
    "relationship": {
        "required": ["id", "source", "target", "type"],
        "fields": [
            "id", "source", "target", "type",
            "weight", "properties",
        ],
    },
}


def validate_object(object_type, data):
    schema = SCHEMAS.get(object_type)

    if not schema:
        return False, "Unknown object type"

    if not isinstance(data, dict):
        return False, "Object must be a dictionary"

    missing = [
        field
        for field in schema["required"]
        if field not in data
    ]

    if missing:
        return False, f"Missing fields: {missing}"

    unknown = [
        field
        for field in data
        if field not in schema["fields"]
    ]

    if unknown:
        return False, f"Unknown fields: {unknown}"

    return True, None# PART 4 — DATA ADAPTERS

class DataAdapter:

    def list_items(self, **filters):
        raise NotImplementedError

    def get_item(self, item_id):
        raise NotImplementedError

    def create_item(self, payload):
        raise NotImplementedError

    def update_item(self, item_id, payload):
        raise NotImplementedError

    def delete_item(self, item_id):
        raise NotImplementedError


class BackendAdapter(DataAdapter):
    def __init__(self):
        pass

    def list_items(self, endpoint, **filters):
        return api_get(
            endpoint,
            params=filters,
        )

    def get_item(self, endpoint, item_id):
        return api_get(
            f"{endpoint}/{item_id}"
        )

    def create_item(self, endpoint, payload):
        return api_post(
            endpoint,
            payload=payload,
        )

    def update_item(self, endpoint, item_id, payload):
        return api_call(
            "PATCH",
            f"{endpoint}/{item_id}",
            payload=payload,
        )

    def delete_item(self, endpoint, item_id):
        return api_delete(
            f"{endpoint}/{item_id}"
        )


DATA_ADAPTER = BackendAdapter()
# PART 5 — ACCESS CONTROL

def has_permission(permission):
    permissions = APP_STATE.get("permissions", [])

    return (
        permission in permissions
        or "*" in permissions
    )


def can_view_document(document):
    if not isinstance(document, dict):
        return False

    permissions = document.get("permissions")

    if permissions is None:
        return has_permission("documents.read")

    return has_permission("documents.read")


def can_edit_document(document):
    return (
        has_permission("documents.edit")
        and can_view_document(document)
    )


def can_manage_workspace():
    return has_permission("workspace.manage")


def require_permission(permission):
    if not has_permission(permission):
        st.error("You don't have permission for this action.")
        return False

    return True 
    # PART 6 — KNOWLEDGE GRAPH

class KnowledgeGraph:

    def __init__(self):
        self.nodes = {}
        self.edges = {}

    def add_node(self, node):
        valid, error = validate_object(
            "entity", node
        )

        if not valid:
            raise ValueError(error)

        self.nodes[node["id"]] = node

    def add_edge(self, edge):
        valid, error = validate_object(
            "relationship", edge
        )

        if not valid:
            raise ValueError(error)

        self.edges[edge["id"]] = edge

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def neighbors(self, node_id):
        results = []

        for edge in self.edges.values():

            if edge["source"] == node_id:
                results.append(edge["target"])

            elif edge["target"] == node_id:
                results.append(edge["source"])

        return results

    def clear(self):
        self.nodes.clear()
        self.edges.clear()


knowledge_graph = KnowledgeGraph() 
# PART 7 — SEARCH MODEL

SEARCH_FIELDS = [
    "query",
    "source",
    "document_type",
    "owner",
    "date_range",
    "department",
]


def build_search_request():
    search_state = APP_STATE["search"]

    return {
        "query": search_state["query"],
        "filters": search_state["filters"],
        "cursor": search_state["cursor"],
    }


def update_search_query(query):
    APP_STATE["search"]["query"] = query


def update_search_filter(name, value):
    APP_STATE["search"]["filters"][name] = value


def clear_search_filters():
    APP_STATE["search"]["filters"] = {}


def execute_search():

    request_data = build_search_request()

    if not request_data["query"].strip():
        return None

    response = api.get(
        "/api/v1/search",
        params=request_data,
    )

    return response
    # PART 8 — SOURCE LINEAGE

class SourceRegistry:

    def __init__(self):
        self.sources = {}

    def register(self, source):
        source_id = source.get("id")

        if not source_id:
            raise ValueError(
                "Source requires an ID"
            )

        self.sources[source_id] = source

    def get(self, source_id):
        return self.sources.get(source_id)

    def resolve_many(self, source_ids):
        return [
            self.sources[source_id]
            for source_id in source_ids
            if source_id in self.sources
        ]

    def clear(self):
        self.sources.clear()


source_registry = SourceRegistry()


def extract_response_sources(response):
    if not isinstance(response, dict):
        return []

    source_ids = response.get("source_ids", [])

    return source_registry.resolve_many(
        source_ids
    )# PART 9 — APPLICATION EVENTS

EVENT_HANDLERS = {}


def subscribe(event_name, handler):

    EVENT_HANDLERS.setdefault(
        event_name, []
    ).append(handler)


def dispatch(event_name, payload=None):

    payload = payload or {}

    handlers = EVENT_HANDLERS.get(
        event_name, []
    )

    results = []

    for handler in handlers:
        results.append(
            handler(payload)
        )

    return results


def on_search_requested(payload):

    query = payload.get("query", "")

    update_search_query(query)

    return query


def on_document_selected(payload):

    document_id = payload.get(
        "document_id"
    )

    APP_STATE["ui"][
        "selected_document"
    ] = document_id

    return document_id


subscribe(
    "search.requested",
    on_search_requested,
)

subscribe(
    "document.selected",
    on_document_selected,
)# PART 10 — PAGE REGISTRY

PAGE_REGISTRY = {}


def register_page(
    page_id,
    title,
    description,
    icon,
    permission=None,
):
    PAGE_REGISTRY[page_id] = {
        "id": page_id,
        "title": title,
        "description": description,
        "icon": icon,
        "permission": permission,
    }


register_page(
    "overview",
    "Overview",
    "Your knowledge workspace",
    "◈",
)

register_page(
    "search",
    "Search",
    "Discover enterprise knowledge",
    "⌕",
    "search.read",
)

register_page(
    "documents",
    "Documents",
    "Explore organizational content",
    "▤",
    "documents.read",
)

register_page(
    "graph",
    "Knowledge Graph",
    "Explore connected knowledge",
    "◎",
    "graph.read",
)

register_page(
    "assistant",
    "AI Workspace",
    "Work with enterprise knowledge",
    "✦",
    "assistant.use",
)

register_page(
    "collections",
    "Collections",
    "Organize important resources",
    "▦",
)

register_page(
    "team",
    "Team",
    "People and team management",
    "♙",
    "team.read",
)

register_page(
    "connectors",
    "Connectors",
    "Manage connected data sources",
    "⇄",
    "connectors.read",
)

register_page(
    "activity",
    "Activity",
    "Workspace activity and audit history",
    "◷",
    "activity.read",
)

register_page(
    "analytics",
    "Analytics",
    "Usage and knowledge insights",
    "▥",
    "analytics.read",
)

register_page(
    "billing",
    "Billing",
    "Plans, payments and subscriptions",
    "◇",
    "billing.read",
)

register_page(
    "settings",
    "Settings",
    "Workspace preferences",
    "⚙",
)

register_page(
    "admin",
    "Administration",
    "Administrative controls",
    "⌘",
    "admin.read",
)


def get_page(page_id):
    return PAGE_REGISTRY.get(page_id)


def navigate_to(page_id):

    if page_id not in PAGE_REGISTRY:
        return False

    page = PAGE_REGISTRY[page_id]

    permission = page.get("permission")

    if permission and not has_permission(permission):
        return False

    APP_STATE["route"] = page_id

    return True


def available_pages():

    return [
        page
        for page in PAGE_REGISTRY.values()
        if (
            not page["permission"]
            or has_permission(page["permission"])
        )
    ]
# ============================================================
# PART 11 — PREMIUM MOTION DESIGN SYSTEM
# ============================================================

def inject_premium_motion():

    st.markdown("""
    <style>

    :root {
        --ek-bg: #F6F7FB;
        --ek-surface: #FFFFFF;
        --ek-primary: #6657E8;
        --ek-primary-light: #8B80FF;
        --ek-text: #202238;
        --ek-muted: #8589A0;
        --ek-border: #E9EAF2;
        --ek-radius: 18px;
    }

    .stApp {
        background:
            radial-gradient(
                ellipse at 15% 0%,
                rgba(111,92,255,.055),
                transparent 40%
            ),
            #F6F7FB;
    }

    @keyframes ekFadeIn {
        from {
            opacity: 0;
            transform: translateY(12px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes ekFloat {
        0%, 100% {
            transform: translateY(0px);
        }
        50% {
            transform: translateY(-5px);
        }
    }

    @keyframes ekPulse {
        0%, 100% {
            opacity: .65;
        }
        50% {
            opacity: 1;
        }
    }

    @keyframes ekGlow {
        0%, 100% {
            box-shadow: 0 0 0 rgba(102,87,232,0);
        }
        50% {
            box-shadow: 0 0 24px rgba(102,87,232,.12);
        }
    }

    @keyframes ekShimmer {
        0% {
            background-position: -500px 0;
        }
        100% {
            background-position: 500px 0;
        }
    }

    .ek-animate-in {
        animation: ekFadeIn .45s ease both;
    }

    .ek-float {
        animation: ekFloat 5s ease-in-out infinite;
    }

    .ek-glow {
        animation: ekGlow 4s ease-in-out infinite;
    }

    .ek-premium-card {
        background: rgba(255,255,255,.88);
        backdrop-filter: blur(18px);
        border: 1px solid rgba(226,228,240,.9);
        border-radius: 18px;
        box-shadow:
            0 4px 18px rgba(32,35,68,.035),
            0 1px 3px rgba(32,35,68,.025);
        transition:
            transform .24s ease,
            box-shadow .24s ease,
            border-color .24s ease;
    }

    .ek-premium-card:hover {
        transform: translateY(-3px);
        box-shadow:
            0 15px 36px rgba(32,35,68,.075);
        border-color: #D8D5FF;
    }

    .ek-premium-button {
        transition:
            transform .18s ease,
            box-shadow .18s ease,
            background .18s ease;
    }

    .ek-premium-button:hover {
        transform: translateY(-1px);
    }

    @media (prefers-reduced-motion: reduce) {
        *,
        *::before,
        *::after {
            animation-duration: .01ms !important;
            transition-duration: .01ms !important;
        }
    }

    </style>
    """, unsafe_allow_html=True)
    # ============================================================
# PART 12 — AMBIENT BACKGROUND
# ============================================================

def render_ambient_background():

    st.markdown("""
    <div style="
        position:fixed;
        top:-140px;
        right:-130px;
        width:380px;
        height:380px;
        background:radial-gradient(
            circle,
            rgba(118,102,255,.10),
            transparent 70%
        );
        border-radius:50%;
        pointer-events:none;
        z-index:0;
    "></div>

    <div style="
        position:fixed;
        bottom:-180px;
        left:160px;
        width:420px;
        height:420px;
        background:radial-gradient(
            circle,
            rgba(76,175,255,.065),
            transparent 70%
        );
        border-radius:50%;
        pointer-events:none;
        z-index:0;
    "></div>
    """, unsafe_allow_html=True)


def render_animated_accent():

    st.markdown("""
    <div class="ek-float" style="
        display:inline-flex;
        width:42px;
        height:42px;
        align-items:center;
        justify-content:center;
        border-radius:14px;
        color:white;
        font-size:20px;
        background:linear-gradient(
            135deg,#8174FF,#5140D6
        );
        box-shadow:
            0 8px 22px rgba(95,78,220,.22);
    ">
        ✦
    </div>
    """, unsafe_allow_html=True) 
# ============================================================
# PART 13 — PREMIUM WORKSPACE BAR
# ============================================================

def render_premium_workspace_bar():

    st.markdown("""
    <div class="ek-premium-card" style="
        padding:12px 18px;
        margin-bottom:16px;
        display:flex;
        align-items:center;
        justify-content:space-between;
    ">

        <div style="
            display:flex;
            align-items:center;
            gap:10px;
        ">

            <div style="
                height:32px;
                width:32px;
                border-radius:10px;
                background:linear-gradient(
                    135deg,#8275FF,#5948DB
                );
                display:flex;
                align-items:center;
                justify-content:center;
                color:white;
                font-size:15px;
            ">
                ✳
            </div>

            <div>
                <div style="
                    font-size:12px;
                    font-weight:750;
                    color:#292B43;
                ">
                    Enterprise KE
                </div>

                <div style="
                    font-size:9px;
                    color:#85899C;
                ">
                    Knowledge Intelligence Workspace
                </div>
            </div>

        </div>

        <div style="
            padding:6px 10px;
            background:#F1F0FF;
            color:#6555DC;
            border-radius:20px;
            font-size:10px;
            font-weight:700;
        ">
            WORKSPACE
        </div>

    </div>
    """, unsafe_allow_html=True)
    # ============================================================
# PART 14 — ANIMATED PAGE TITLES
# ============================================================

def render_premium_page_title(
    title,
    subtitle="",
    eyebrow="WORKSPACE",
    icon="✦",
):

    st.markdown(
        f"""
        <div class="ek-animate-in"
             style="margin:25px 0 22px">

            <div style="
                display:flex;
                align-items:center;
                gap:9px;
                font-size:9px;
                font-weight:800;
                letter-spacing:1.6px;
                color:#8A8DA2;
                margin-bottom:11px;
            ">
                <span style="color:#7163E8">
                    {icon}
                </span>

                {eyebrow}
            </div>

            <div style="
                font-size:32px;
                font-weight:820;
                letter-spacing:-1.5px;
                color:#22243B;
                line-height:1.15;
            ">
                {title}
            </div>

            <div style="
                font-size:13px;
                color:#85899C;
                margin-top:9px;
            ">
                {subtitle}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


def render_breadcrumb(items):

    breadcrumb_html = " &nbsp;›&nbsp; ".join(
        f'<span style="color:#777D92">{item}</span>'
        for item in items
    )

    st.markdown(
        f"""
        <div style="
            font-size:10px;
            margin:8px 0 15px;
            color:#A1A4B4;
        ">
            {breadcrumb_html}
        </div>
        """,
        unsafe_allow_html=True,
)
    # ============================================================
# PART 15 — PREMIUM SEARCH COMMAND BAR
# ============================================================

def render_premium_search_bar():

    st.markdown("""
    <div style="
        font-size:11px;
        color:#73778D;
        margin-bottom:8px;
        font-weight:600;
    ">
        SEARCH YOUR ORGANIZATION
    </div>
    """, unsafe_allow_html=True)

    with st.form("premium_search_command"):

        query = st.text_input(
            "Knowledge search",
            placeholder=(
                "Ask a question or search documents, "
                "people and knowledge..."
            ),
            label_visibility="collapsed",
        )

        submitted = st.form_submit_button(
            "⌕  Search knowledge",
            type="primary",
            use_container_width=True,
        )

    if submitted and query.strip():

        st.session_state.search_query = query

        with st.spinner("Searching your knowledge..."):

            result = search_backend(query)

        if result.success:

            st.session_state.search_results = result.data

            st.session_state.current_page = "search"

            st.rerun()

        else:

            show_api_error(result)

    st.markdown("""
    <div style="
        display:flex;
        gap:6px;
        flex-wrap:wrap;
        margin-top:9px;
        font-size:9px;
        color:#9195A7;
    ">
        <span>Search across your workspace</span>
        <span>·</span>
        <span>Find documents</span>
        <span>·</span>
        <span>Discover knowledge</span>
    </div>
    """, unsafe_allow_html=True)
    # ============================================================
# PART 16 — PREMIUM GLASS CARDS
# ============================================================

def render_glass_panel(
    title,
    description="",
    content=None,
    accent="#7163E8",
):

    description_html = ""

    if description:

        description_html = f"""
        <div style="
            font-size:11px;
            color:#85899C;
            margin-top:6px;
        ">
            {description}
        </div>
        """

    content_html = ""

    if content:

        content_html = f"""
        <div style="
            margin-top:16px;
            color:#484B61;
            font-size:12px;
        ">
            {content}
        </div>
        """

    st.markdown(
        f"""
        <div class="ek-premium-card ek-animate-in"
             style="padding:20px 21px">

            <div style="
                width:3px;
                height:25px;
                border-radius:10px;
                background:{accent};
                margin-bottom:13px;
            "></div>

            <div style="
                font-size:15px;
                font-weight:750;
                color:#292B43;
            ">
                {title}
            </div>

            {description_html}

            {content_html}

        </div>
        """,
        unsafe_allow_html=True,
    )


def render_premium_metric(
    label,
    value,
    detail="",
    icon="✦",
):

    st.markdown(
        f"""
        <div class="ek-premium-card"
             style="padding:18px">

            <div style="
                display:flex;
                justify-content:space-between;
                align-items:center;
            ">

                <div style="
                    font-size:10px;
                    font-weight:650;
                    color:#85899C;
                ">
                    {label}
                </div>

                <div style="
                    height:30px;
                    width:30px;
                    background:#F0EEFF;
                    border-radius:10px;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    color:#6D5EE5;
                ">
                    {icon}
                </div>

            </div>

            <div style="
                font-size:27px;
                font-weight:800;
                color:#252740;
                margin-top:13px;
                letter-spacing:-1px;
            ">
                {value}
            </div>

            <div style="
                font-size:10px;
                color:#9295A7;
                margin-top:6px;
            ">
                {detail}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )
# ============================================================
# PART 17 — LOADING SKELETONS
# ============================================================

def render_skeleton(
    rows=3,
    height=15,
):

    for _ in range(rows):

        st.markdown(
            f"""
            <div style="
                height:{height}px;
                border-radius:8px;
                margin-bottom:11px;
                background:linear-gradient(
                    90deg,
                    #F0F1F6 25%,
                    #E7E9F2 50%,
                    #F0F1F6 75%
                );
                background-size:1000px 100%;
                animation:ekShimmer 1.8s infinite linear;
            "></div>
            """,
            unsafe_allow_html=True,
        )


def render_loading_panel(
    message="Loading workspace...",
):

    st.markdown(
        f"""
        <div class="ek-premium-card"
             style="
                padding:25px;
                text-align:center;
             ">

            <div class="ek-float"
                 style="
                    font-size:26px;
                    color:#7264E8;
                    margin-bottom:10px;
                 ">
                ✦
            </div>

            <div style="
                font-size:12px;
                color:#73778D;
            ">
                {message}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


def render_loading_documents():

    for _ in range(3):

        with st.container(border=True):

            render_skeleton(
                rows=2,
                height=12,
)
            # ============================================================
# PART 18 — INTERACTIVE FILTER CHIPS
# ============================================================

def render_filter_chips(
    label,
    options,
    state_key,
):

    st.markdown(
        f"""
        <div style="
            font-size:11px;
            color:#777D91;
            font-weight:650;
            margin-bottom:7px;
        ">
            {label}
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected = st.session_state.get(
        state_key,
        "All",
    )

    if selected not in options:
        selected = options[0]

    selection = st.radio(
        label,
        options,
        index=options.index(selected),
        horizontal=True,
        label_visibility="collapsed",
        key=f"chip_selector_{state_key}",
    )

    st.session_state[state_key] = selection

    return selection


def render_filter_row():

    left, right = st.columns(
        [4, 1]
    )

    with left:

        selected = render_filter_chips(
            "Content type",
            [
                "All",
                "Documents",
                "People",
                "Collections",
            ],
            "active_content_filter",
        )

    with right:

        st.markdown(
            "<div style='height:20px'></div>",
            unsafe_allow_html=True,
        )

        if st.button(
            "Reset",
            key="reset_filter_chips",
        ):

            st.session_state.active_content_filter = "All"

            st.rerun()

    return selected
    # ============================================================
# PART 19 — DOCUMENT PREVIEW COMPONENT
# ============================================================

def document_type_icon(document):

    mime_type = (
        document.get("mime_type")
        or document.get("file_type")
        or ""
    ).lower()

    if "pdf' in mime_type:
        return "▧"

    if "spreadsheet" in mime_type or "excel" in mime_type:
        return "▦"

    if "presentation" in mime_type:
        return "▣"

    if "image" in mime_type:
        return "▧"

    return "▤"


def render_document_preview_card(document):

    document_id = document.get("id")

    title = (
        document.get("title")
        or document.get("filename")
        or "Untitled document"
    )

    description = (
        document.get("description")
        or document.get("snippet")
        or ""
    )

    source = (
        document.get("source")
        or document.get("source_name")
        or "Source unavailable"
    )

    updated = (
        document.get("updated_at")
        or document.get("created_at")
        or ""
    )

    icon = document_type_icon(document)

    st.markdown(
        f"""
        <div class="ek-premium-card"
             style="padding:16px;margin-bottom:10px">

            <div style="
                display:flex;
                gap:13px;
                align-items:flex-start;
            ">

                <div style="
                    width:43px;
                    height:43px;
                    background:#F1F0FF;
                    color:#6759DE;
                    border-radius:12px;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:19px;
                    flex-shrink:0;
                ">
                    {icon}
                </div>

                <div style="flex:1">

                    <div style="
                        font-size:13px;
                        font-weight:730;
                        color:#303248;
                    ">
                        {title}
                    </div>

                    <div style="
                        font-size:10px;
                        color:#85899C;
                        margin-top:5px;
                    ">
                        {source}
                    </div>

                    <div style="
                        font-size:11px;
                        color:#777D91;
                        margin-top:9px;
                    ">
                        {description[:250]}
                    </div>

                    <div style="
                        font-size:9px;
                        color:#A0A3B2;
                        margin-top:10px;
                    ">
                        {updated}
                    </div>

                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    if document_id:

        if st.button(
            "Open document",
            key=f"open_doc_{document_id}",
        ):

            APP_STATE["ui"]["selected_document"] = document_id

            st.session_state.selected_document_id = document_id

            st.session_state.current_page = "documents"

            st.rerun()
            # ============================================================
# PART 20 — PREMIUM APPLICATION SHELL
# ============================================================

def render_premium_shell_start():

    inject_premium_motion()

    render_ambient_background()

    render_sidebar_navigation()

    render_premium_workspace_bar()

    header_left, header_right = st.columns(
        [8, 1]
    )

    with header_right:

        render_notification_center()


def render_premium_shell_end():

    st.markdown("""
    <div style="
        margin-top:50px;
        padding:20px 0 10px;
        border-top:1px solid #E8EAF1;
        text-align:center;
        color:#9A9DAE;
        font-size:9px;
        letter-spacing:.5px;
    ">
        ENTERPRISE KE · KNOWLEDGE INTELLIGENCE
    </div>
    """, unsafe_allow_html=True)


def render_premium_page(
    title,
    subtitle="",
    icon="✦",
    eyebrow="WORKSPACE",
):

    render_premium_shell_start()

    render_premium_page_title(
        title=title,
        subtitle=subtitle,
        icon=icon,
        eyebrow=eyebrow,
    )

    render_premium_shell_end()
    
# ============================================================
# PART 21 — COMPATIBILITY / API BRIDGE
# ============================================================

BASE_APP_STATE = {
    "user": None,
    "documents": [],
    "entities": [],
    "relationships": [],
    "search": {"query": "", "results": []},
    "notifications": [],
    "active_page": "Overview"
}

APP_STATE = globals().get("APP_STATE", {})
APP_STATE.update({
    k: v for k, v in BASE_APP_STATE.items()
    if k not in APP_STATE
})

def get_state(key, default=None):
    return APP_STATE.get(key, default)

def set_state(key, value):
    APP_STATE[key] = value
    return value

def reset_state():
    APP_STATE.clear()
    APP_STATE.update(json.loads(json.dumps(BASE_APP_STATE)))

class APIClient:
    def get(self, endpoint, params=None):
        return api_get(endpoint, params)

    def post(self, endpoint, payload=None):
        return api_post(endpoint, payload)

    def delete(self, endpoint):
        return api_delete(endpoint)

api = APIClient()

def normalize_search_results(data):
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    for key in ("results", "items", "documents", "data"):
        value = data.get(key)
        if isinstance(value, list):
            return value

    return []

def normalize_documents(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("documents", "items", "results", "data"):
            if isinstance(data.get(key), list):
                return data[key]

    return []

def get_api_error(result):
    error = result.get("error")
    if isinstance(error, dict):
        return error.get("detail") or str(error)
    return error or "Request failed"

# Bridge Streamlit session state to architecture state
def sync_app_state():
    APP_STATE["user"] = st.session_state.get("user")
    APP_STATE["active_page"] = st.session_state.get("current_page")
    APP_STATE["documents"] = st.session_state.get("documents", [])
    APP_STATE["search"] = {
        "query": st.session_state.get("search_query", ""),
        "results": st.session_state.get("search_results", [])
    }

sync_app_state()

# ============================================================
# PART 22 — NAVIGATION
# ============================================================

NAVIGATION = {
    "Workspace": [
        ("Overview", "◈"),
        ("Search", "⌕"),
        ("Documents", "▤"),
        ("Knowledge Graph", "◎"),
        ("AI Workspace", "✧"),
        ("Collections", "▣")
    ],
    "Organization": [
        ("Team", "♧"),
        ("Connectors", "⌘"),
        ("Activity", "◷"),
        ("Analytics", "▥")
    ],
    "Management": [
        ("Billing", "◇"),
        ("Settings", "⚙"),
        ("Admin", "⌘")
    ]
}

def navigate_to(page):
    st.session_state.current_page = page
    APP_STATE["active_page"] = page

def render_sidebar_navigation():
    with st.sidebar:
        st.markdown("## ✦ Enterprise-KE")
        st.caption("Knowledge workspace")

        if st.session_state.get("user"):
            user = st.session_state.user
            st.caption(user.get("email", "Signed in"))
        else:
            st.caption("Workspace")

        st.divider()

        for group, items in NAVIGATION.items():
            st.caption(group.upper())

            for page, icon in items:
                active = st.session_state.current_page == page

                if st.button(
                    f"{icon}  {page}",
                    key=f"nav_{page}",
                    use_container_width=True,
                    type="primary" if active else "secondary"
                ):
                    navigate_to(page)
                    st.rerun()

        st.divider()

        if st.button("↻ Refresh workspace", use_container_width=True):
            st.session_state.last_refresh = time.time()
            st.rerun()

        st.caption(f"Enterprise-KE · v{APP_VERSION}")

# ============================================================
# PART 23 — NOTIFICATIONS / PAGE HELPERS
# ============================================================

def render_notification_center():
    notifications = safe_list(
        st.session_state.get("notifications")
    )

    with st.popover("♧ Notifications"):
        if not notifications:
            st.caption("No new notifications.")
        else:
            for item in notifications[:10]:
                if isinstance(item, dict):
                    st.write(item.get("message", "Notification"))
                else:
                    st.write(str(item))

            if st.button("Clear notifications"):
                st.session_state.notifications = []
                st.rerun()

def render_page_header(title, subtitle="", icon="✦"):
    st.markdown(f"### {icon} {title}")
    if subtitle:
        st.caption(subtitle)
    st.divider()

def render_page_notice():
    notice = st.session_state.get("notice")
    if not notice:
        return

    kind = notice.get("kind", "info")
    message = notice.get("message", "")

    if kind == "success":
        st.success(message)
    elif kind == "error":
        st.error(message)
    elif kind == "warning":
        st.warning(message)
    else:
        st.info(message)

def render_empty_state(title, description, icon="◇"):
    st.markdown(
        f"""
        <div class="ek-card" style="text-align:center;padding:35px">
            <div style="font-size:38px;margin-bottom:12px">{icon}</div>
            <h3>{title}</h3>
            <p class="ek-muted">{description}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_api_status():
    result = api_get("/api/v1/health")

    if result["ok"]:
        st.caption("● API reachable")
    else:
        st.caption("○ API unavailable")
    
# ============================================================
# PART 24 — OVERVIEW DASHBOARD
# ============================================================

def render_overview():
    render_page_header(
        "Overview",
        "Your organization's knowledge at a glance.",
        "◈"
    )

    result = api_get("/api/v1/dashboard")

    if not result["ok"]:
        st.warning("Dashboard data is currently unavailable.")
        with st.expander("Technical details"):
            st.code(str(result.get("error")))
        return

    data = safe_dict(result["data"])

    st.markdown("#### Workspace snapshot")

    metric_candidates = [
        ("Documents", ["documents", "document_count", "total_documents"]),
        ("Team members", ["team", "team_members", "member_count"]),
        ("Collections", ["collections", "collection_count"]),
        ("Connectors", ["connectors", "connector_count"])
    ]

    cols = st.columns(4)

    for col, (label, keys) in zip(cols, metric_candidates):
        value = None

        for key in keys:
            if key in data:
                candidate = data[key]
                if isinstance(candidate, (int, float)):
                    value = candidate
                    break
                if isinstance(candidate, list):
                    value = len(candidate)
                    break

        with col:
            if value is not None:
                st.metric(label, value)
            else:
                st.metric(label, "—")

    st.markdown("#### Workspace activity")

    activity = data.get("activity") or data.get("recent_activity")

    if isinstance(activity, list) and activity:
        for item in activity[:8]:
            if isinstance(item, dict):
                st.markdown(
                    f"**{item.get('title', item.get('action', 'Activity'))}**"
                )
                st.caption(
                    item.get("created_at", item.get("timestamp", ""))
                )
    else:
        render_empty_state(
            "No recent activity",
            "Activity will appear here when workspace events are available.",
            "◷"
        )

    st.markdown("#### Quick actions")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("⌕ Search knowledge", use_container_width=True):
            navigate_to("Search")
            st.rerun()

    with c2:
        if st.button("▤ Browse documents", use_container_width=True):
            navigate_to("Documents")
            st.rerun()

    with c3:
        if st.button("◎ Explore graph", use_container_width=True):
            navigate_to("Knowledge Graph")
            st.rerun()
            

