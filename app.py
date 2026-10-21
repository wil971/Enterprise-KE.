# ============================================================================
# app.py - GOOGLE-ONLY ENTERPRISE FRONTEND (Loop-Free Production)
# ============================================================================

import os
import streamlit as st
import requests
from streamlit_oauth import OAuth2Component

st.set_page_config(
    page_title="Enterprise Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Glean-Style Modern SaaS Aesthetic
st.markdown("""
    <style>
    .stApp { 
        background: radial-gradient(circle at 50% 0%, #111827 0%, #06090f 100%);
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
        color: white;
        border: none;
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
    }
    input {
        background-color: #0b0f19 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #1e293b !important;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 1. ENVIRONMENT & SECRET CONFIGURATION
# ----------------------------------------------------------------------------
BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", "https://enterprise-ke-3.onrender.com")).rstrip("/")

# Safely extract Client ID and Client Secret from Streamlit Secrets
CLIENT_ID = ""
CLIENT_SECRET = ""

if "web" in st.secrets:
    CLIENT_ID = st.secrets["web"].get("client_id", "")
    CLIENT_SECRET = st.secrets["web"].get("client_secret", "")
elif "google_oauth" in st.secrets:
    CLIENT_ID = st.secrets["google_oauth"].get("client_id", "")
    CLIENT_SECRET = st.secrets["google_oauth"].get("client_secret", "")
else:
    CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", "")
    CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", "")

REDIRECT_URI = "https://enterprise-ke-hqrlscaknjikcwz5kpndrt.streamlit.app"

# Initialize OAuth Component
oauth2 = OAuth2Component(
    CLIENT_ID,
    CLIENT_SECRET,
    "https://accounts.google.com/o/oauth2/v2/auth",
    "https://oauth2.googleapis.com/token"
)

# Initialize Session State Variables
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None

def get_auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

# ----------------------------------------------------------------------------
# 2. AUTHENTICATION PORTAL (GOOGLE ONLY - LOOP-FREE)
# ----------------------------------------------------------------------------
if not st.session_state.access_token:
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="font-size: 2.4rem; font-weight: 700; color: #ffffff;">Enterprise Intelligence</h1>
                <p style="color: #94a3b8; font-size: 1.05rem;">Secure Knowledge Graph & Workspace Discovery</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1.5rem; background: rgba(15, 23, 42, 0.85); padding: 2rem; border-radius: 16px; border: 1px solid rgba(59, 130, 246, 0.4);">
                <p style="color: #94a3b8; font-size: 1rem; margin-bottom: 1.5rem;">Authenticate securely using your official Google Workspace account.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        try:
            result = oauth2.authorize_button(
                name="Sign in with Google",
                icon="https://www.google.com/favicon.ico",
                redirect_uri=REDIRECT_URI,
                scope="openid email profile",
                key="google_sso_btn",
            )
            
            if result and isinstance(result, dict):
                # Safely parse token dictionary structure returned by streamlit-oauth
                token_dict = result.get("token", result)
                id_token_val = token_dict.get("id_token")
                
                if not id_token_val and "id_token" in result:
                    id_token_val = result.get("id_token")

                if id_token_val:
                    with st.spinner("Verifying Google secure token with enterprise backend..."):
                        res = requests.post(
                            f"{BACKEND_URL}/api/v1/auth/google",
                            json={"id_token": id_token_val},
                            timeout=30
                        )
                        
                        if res.status_code == 200:
                            data = res.json()
                            # Save state to grant entry
                            st.session_state.access_token = data.get("access_token")
                            st.session_state.user_info = data
                            
                            # CRITICAL FIX: Clear the OAuth 'code' query parameters from URL bar to prevent infinite loop
                            st.query_params.clear()
                            st.rerun()
                        else:
                            st.error(f"Authentication failed ({res.status_code}): {res.text}")
                else:
                    st.error("Google response did not contain a valid ID Token.")

        except Exception as oauth_err:
            st.error(f"OAuth Handshake Error: {str(oauth_err)}")
            
    st.stop()

# ----------------------------------------------------------------------------
# 3. MAIN APPLICATION DASHBOARD
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("🛡️ Enterprise Portal")
    user_info = st.session_state.user_info or {}
    
    st.write(f"**User ID:** `{user_info.get('user_id', 'N/A')}`")
    st.write(f"**Tenant:** `{user_info.get('tenant_id', 'N/A')}`")
    st.write(f"**Tier:** `{user_info.get('tier', 'PRO_ENTERPRISE')}`")
    
    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.user_info = None
        st.query_params.clear()
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
                        st.subheader(item.get('title', 'Untitled'))
                        st.write(item.get('snippet', 'No preview available.'))
            else:
                st.error(f"Search request failed with status code {response.status_code}.")
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            
