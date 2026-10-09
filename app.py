# ============================================================================
# app.py - COMPLETE UNIFIED ENTERPRISE FRONTEND
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

# Custom CSS for Modern SaaS Aesthetic
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stForm"] {
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 2rem;
        background: #1a202c;
    }
    div.stButton > button:first-child {
        border-radius: 8px;
        height: 2.8rem;
        font-weight: 600;
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

# Auto-wake Render backend on load
try:
    requests.get(f"{BACKEND_URL}/health", timeout=2)
except Exception:
    pass

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
                <h1 style="font-size: 2.2rem; font-weight: 700; color: #ffffff;">Enterprise Intelligence</h1>
                <p style="color: #a0aec0; font-size: 1rem;">Sign in to query connected SaaS connectors & Knowledge Graphs</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        auth_tab1, auth_tab2 = st.tabs(["🔒 Work Email Login", "🌐 Google Account Login"])

        # TAB 1: WORK EMAIL
        with auth_tab1:
            with st.form("work_email_form"):
                work_email = st.text_input("Work Email Address", placeholder="name@company.com", value="alex@enterprise-corp.com")
                work_password = st.text_input("Password", type="password", placeholder="••••••••••••", value="securepass123")
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit_work = st.form_submit_button("Sign In with Work Email", use_container_width=True, type="primary")

                if submit_work:
                    if not work_email or not work_password:
                        st.error("Please provide both email and password.")
                    else:
                        with st.spinner("Authenticating work credentials..."):
                            try:
                                res = requests.post(
                                    f"{BACKEND_URL}/api/v1/auth/login",
                                    json={"email": work_email, "password": work_password},
                                    timeout=30
                                )
                                if "application/json" in res.headers.get("content-type", ""):
                                    data = res.json()
                                    if res.status_code == 200:
                                        st.session_state.access_token = data.get("access_token")
                                        st.session_state.user_info = data
                                        st.success("Authenticated successfully!")
                                        st.rerun()
                                    else:
                                        st.error(f"Login failed: {data.get('detail', 'Invalid credentials')}")
                                else:
                                    st.warning("Server was waking up from idle. Please click Sign In again.")
                            except Exception as e:
                                st.error(f"Connection error: {str(e)}")

        # TAB 2: GOOGLE ACCOUNT (Email + Password)
        with auth_tab2:
            with st.form("google_login_form"):
                google_email = st.text_input("Google Account Email", placeholder="user@gmail.com", value="jokerwilli7@gmail.com")
                google_password = st.text_input("Google Password", type="password", placeholder="••••••••••••")
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit_google = st.form_submit_button("Sign In with Google Account", use_container_width=True, type="primary")

                if submit_google:
                    if not google_email or not google_password:
                        st.error("Please enter both your Google email and password.")
                    else:
                        with st.spinner("Authenticating Google credentials..."):
                            try:
                                res = requests.post(
                                    f"{BACKEND_URL}/api/v1/auth/google",
                                    json={"email": google_email, "password": google_password},
                                    timeout=30
                                )
                                if "application/json" in res.headers.get("content-type", ""):
                                    data = res.json()
                                    if res.status_code == 200:
                                        st.session_state.access_token = data.get("access_token")
                                        st.session_state.user_info = data
                                        st.success(f"Authenticated as {google_email}!")
                                        st.rerun()
                                    else:
                                        st.error(f"Google login failed: {data.get('detail', 'Invalid credentials')}")
                                else:
                                    st.warning("Server was waking up from idle. Please click Sign In again.")
                            except Exception as e:
                                st.error(f"Connection error: {str(e)}")

    st.stop()

# ============================================================================
# MAIN APPLICATION DASHBOARD (AUTHENTICATED)
# ============================================================================
with st.sidebar:
    st.title("🛡️ Enterprise Portal")
    user_info = st.session_state.user_info or {}
    st.write(f"**Email:** `{user_info.get('email', 'N/A')}`")
    st.write(f"**Tier:** `{user_info.get('tier', 'N/A')}`")
    
    if st.button("Sign Out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.user_info = None
        st.rerun()

st.title("Enterprise Context & Intelligence Platform")
query_input = st.text_input("Search enterprise knowledge graph & documents:", value="OAuth2 token validation policy")

if st.button("Execute Research Search", type="primary"):
    with st.spinner("Searching connected knowledge sources..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/v1/search",
                headers=get_auth_headers(),
                json={"query": query_input, "page": 1, "page_size": 10},
                timeout=15
            )
            if response.status_code == 200:
                search_data = response.json()
                st.info(search_data.get("ai_synthesis", {}).get("summary", "Analysis generated."))
                for item in search_data.get("results", []):
                    with st.container(border=True):
                        st.subheader(item['title'])
                        st.write(item['snippet'])
            else:
                st.error("Search request failed.")
        except Exception as e:
            st.error(f"Search error: {str(e)}")
    
