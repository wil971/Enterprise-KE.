# ============================================================================
# app.py - GOOGLE IDENTITY SERVICES ENTERPRISE FRONTEND (Zero 401 Errors)
# ============================================================================

import streamlit as st
import streamlit.components.v1 as components
import requests

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
    input {
        background-color: #0b0f19 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #1e293b !important;
    }
    </style>
""", unsafe_allow_html=True)

# Configuration Constants
BACKEND_URL = "https://enterprise-ke-3.onrender.com"
CLIENT_ID = "29092714487-abig455o3s1b2vhkkiyv5o5343dqn82.apps.googleusercontent.com"

# Initialize Session State
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None

def get_auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

# ----------------------------------------------------------------------------
# HANDLE GOOGLE TOKEN FROM URL CALLBACK
# ----------------------------------------------------------------------------
query_params = st.query_params
id_token_val = query_params.get("id_token")

if id_token_val and not st.session_state.access_token:
    with st.spinner("Verifying secure token with enterprise backend..."):
        try:
            res = requests.post(
                f"{BACKEND_URL}/api/v1/auth/google",
                json={"id_token": id_token_val},
                timeout=30
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state.access_token = data.get("access_token")
                st.session_state.user_info = data
                st.query_params.clear()
                st.rerun()
            else:
                st.error(f"Backend Authentication Failed: {res.text}")
        except Exception as e:
            st.error(f"Connection error to backend: {str(e)}")

# ----------------------------------------------------------------------------
# AUTHENTICATION PORTAL (OFFICIAL GOOGLE IDENTITY SERVICES BUTTON)
# ----------------------------------------------------------------------------
if not st.session_state.access_token:
    st.markdown("<br><br>", unsafe_allow_html=True)
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
            <div style="text-align: center; margin-bottom: 1.5rem; background: rgba(15, 23, 42, 0.85); padding: 2.5rem; border-radius: 16px; border: 1px solid rgba(59, 130, 246, 0.4);">
                <p style="color: #94a3b8; font-size: 1rem; margin-bottom: 1.5rem;">Authenticate securely using your official Google Workspace account.</p>
            """, 
            unsafe_allow_html=True
        )
        
        # Official Google Identity Services HTML/JS snippet
        gis_html = f"""
        <div style="display: flex; justify-content: center; width: 100%;">
            <script src="https://accounts.google.com/gsi/client" async defer></script>
            <div id="g_id_onload"
                 data-client_id="{CLIENT_ID}"
                 data-callback="handleCredentialResponse"
                 data-auto_prompt="false">
            </div>
            <div class="g_id_signin"
                 data-type="standard"
                 data-size="large"
                 data-theme="filled_blue"
                 data-text="sign_in_with"
                 data-shape="rectangular"
                 data-logo_alignment="left">
            </div>
            <script>
                function handleCredentialResponse(response) {{
                    const idToken = response.credential;
                    const targetUrl = window.location.origin + window.location.pathname + "?id_token=" + encodeURIComponent(idToken);
                    window.location.href = targetUrl;
                }}
            </script>
        </div>
        </div>
        """
        components.html(gis_html, height=100)
            
    st.stop()

# ----------------------------------------------------------------------------
# MAIN APPLICATION DASHBOARD
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("🛡️ Enterprise Portal")
    user_info = st.session_state.user_info or {}
    st.write(f"**Email:** `{user_info.get('email', 'N/A')}`")
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
        
