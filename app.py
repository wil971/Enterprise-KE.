# ============================================================================
# app.py - ENTERPRISE CLIENT-READY FRONTEND
# ============================================================================

import os
import streamlit as st
import requests

st.set_page_config(
    page_title="Enterprise Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Glean-Style Modern SaaS Aesthetic with Live Animations & Glowing Borders
st.markdown("""
    <style>
    /* Deep Immersive Enterprise Background */
    .stApp { 
        background: radial-gradient(circle at 50% 0%, #111827 0%, #06090f 100%);
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Moving Gradient Border / Ambient Glow Animation */
    @keyframes borderGlow {
        0% { border-color: rgba(59, 130, 246, 0.4); box-shadow: 0 0 25px rgba(59, 130, 246, 0.1); }
        50% { border-color: rgba(129, 140, 248, 0.8); box-shadow: 0 0 40px rgba(99, 102, 241, 0.25); }
        100% { border-color: rgba(59, 130, 246, 0.4); box-shadow: 0 0 25px rgba(59, 130, 246, 0.1); }
    }

    /* Main Authentication Form Container */
    div[data-testid="stForm"] {
        background: rgba(15, 23, 42, 0.85);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(59, 130, 246, 0.4);
        border-radius: 16px;
        padding: 2.5rem;
        animation: borderGlow 6s infinite ease-in-out;
    }

    /* High-End Primary Buttons with Smooth Hover Lift */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
        color: white;
        border: none;
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
        letter-spacing: 0.025em;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
    }

    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6);
        filter: brightness(1.1);
    }

    /* Sleek Dark Mode Input Fields */
    input {
        background-color: #0b0f19 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #1e293b !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    
    input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25) !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 23, 42, 0.5);
        padding: 6px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        color: #94a3b8;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# Resolve Backend URL
if "BACKEND_URL" in st.secrets:
    BACKEND_URL = st.secrets["BACKEND_URL"].rstrip("/")
else:
    BACKEND_URL = os.getenv("BACKEND_URL", "https://enterprise-ke-3.onrender.com").rstrip("/")

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None

def get_auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

# ============================================================================
# AUTHENTICATION PORTAL (UNAUTHENTICATED)
# ============================================================================
if not st.session_state.access_token:
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="font-size: 2.4rem; font-weight: 700; color: #ffffff; letter-spacing: -0.025em;">Enterprise Intelligence</h1>
                <p style="color: #94a3b8; font-size: 1.05rem;">Secure Knowledge Graph & Workspace Discovery</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        auth_tab1, auth_tab2 = st.tabs(["🔒 Work Email Login", "🌐 Google Account Login"])

        # TAB 1: WORK EMAIL
        with auth_tab1:
            with st.form("work_email_form"):
                work_email = st.text_input("Work Email Address", placeholder="name@company.com", value="")
                work_password = st.text_input("Password", type="password", placeholder="••••••••••••", value="")
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit_work = st.form_submit_button("Sign In with Work Email", use_container_width=True, type="primary")

                if submit_work:
                    if not work_email or not work_password:
                        st.error("Please enter both your work email and password.")
                    else:
                        with st.spinner("Authenticating secure enterprise session..."):
                            try:
                                res = requests.post(
                                    f"{BACKEND_URL}/api/v1/auth/login",
                                    json={"email": work_email, "password": work_password},
                                    timeout=30
                                )
                                if res.status_code == 200:
                                    data = res.json()
                                    st.session_state.access_token = data.get("access_token")
                                    st.session_state.user_info = data
                                    st.success("Authenticated successfully! Loading workspace...")
                                    st.rerun()
                                else:
                                    st.error("Invalid work email or password.")
                            except Exception as e:
                                st.error("Connection error. Please verify network.")

        # TAB 2: GOOGLE ACCOUNT (Email + Password)
        with auth_tab2:
            with st.form("google_login_form"):
                google_email = st.text_input("Google Account Email", placeholder="user@gmail.com", value="")
                google_password = st.text_input("Google Password", type="password", placeholder="••••••••••••", value="")
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit_google = st.form_submit_button("Sign In with Google Account", use_container_width=True, type="primary")

                if submit_google:
                    if not google_email or not google_password:
                        st.error("Please enter both your Google email and password.")
                    else:
                        with st.spinner("Authenticating Google Workspace..."):
                            try:
                                res = requests.post(
                                    f"{BACKEND_URL}/api/v1/auth/google",
                                    json={"email": google_email, "password": google_password, "id_token": "mock_token"},
                                    timeout=30
                                )
                                if res.status_code == 200:
                                    data = res.json()
                                    st.session_state.access_token = data.get("access_token")
                                    st.session_state.user_info = data
                                    st.success(f"Welcome back, {google_email}!")
                                    st.rerun()
                                else:
                                    st.error("Invalid Google credentials.")
                            except Exception as e:
                                st.error("Connection error. Please verify network.")

    st.stop()

# ============================================================================
# MAIN APPLICATION DASHBOARD (AUTHENTICATED CLIENT VIEW)
# ============================================================================
with st.sidebar:
    st.title("🛡️ Enterprise Portal")
    user_info = st.session_state.user_info or {}
    st.write(f"**Email:** `{user_info.get('email', 'N/A')}`")
    st.write(f"**Tier:** `{user_info.get('tier', 'PRO_ENTERPRISE')}`")
    
    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.user_info = None
        st.rerun()

st.title("Enterprise Context & Intelligence Platform")
query_input = st.text_input("Search connected knowledge sources & workspace graph:", value="OAuth2 security compliance guidelines")

if st.button("Execute Intelligence Query", type="primary"):
    with st.spinner("Traversing knowledge graph and analyzing vector embeddings..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/v1/search",
                headers=get_auth_headers(),
                json={"query": query_input, "page": 1, "page_size": 10},
                timeout=15
            )
            if response.status_code == 200:
                search_data = response.json()
                st.info(search_data.get("ai_synthesis", {}).get("summary", "Synthesis generated successfully."))
                for item in search_data.get("results", []):
                    with st.container(border=True):
                        st.subheader(item['title'])
                        st.write(item['snippet'])
            else:
                st.error("Search request failed.")
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            
