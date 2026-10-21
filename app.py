# app.py — Enterprise Intelligence Platform Frontend

import os
import requests
import streamlit as st
from streamlit_oauth import OAuth2Component

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Enterprise Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# 2. PROFESSIONAL DARK THEME
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(
            circle at 50% 0%, #111827 0%, #06090f 100%
        );
        color: #f1f5f9;
    }

    div.stButton > button {
        background: linear-gradient(135deg, #3b82f6, #6366f1);
        color: white;
        border: 0;
        border-radius: 8px;
        min-height: 2.8rem;
        font-weight: 600;
    }

    div[data-testid="stTextInput"] input {
        background-color: #0b0f19;
        color: #ffffff;
        border-radius: 8px;
        border: 1px solid #334155;
    }

    div[data-testid="stMetric"] {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid #1e293b;
        padding: 1rem;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. CONFIGURATION
# ---------------------------------------------------------
BACKEND_URL = str(
    st.secrets.get(
        "BACKEND_URL",
        os.getenv("BACKEND_URL", ""),
    )
).strip().rstrip("/")

try:
    GOOGLE_CONFIG = st.secrets.get("google_oauth", {})
    if not GOOGLE_CONFIG:
        GOOGLE_CONFIG = st.secrets.get("web", {})

    CLIENT_ID = GOOGLE_CONFIG.get("client_id", "")
    CLIENT_SECRET = GOOGLE_CONFIG.get("client_secret", "")
except Exception:
    CLIENT_ID = ""
    CLIENT_SECRET = ""

REDIRECT_URI = (
    "https://enterprise-ke-hqrlscaknjikcwz5kpndrt.streamlit.app"
)

# ---------------------------------------------------------
# 4. SESSION STATE
# ---------------------------------------------------------
if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "user_info" not in st.session_state:
    st.session_state.user_info = None

if "last_search" not in st.session_state:
    st.session_state.last_search = None


def get_auth_headers():
    """Return the application token issued by our backend."""
    token = st.session_state.get("access_token")

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def backend_error_message(response):
    """Extract a useful error from a backend response."""
    try:
        body = response.json()
        detail = body.get("detail", body)
        return str(detail)
    except (ValueError, AttributeError):
        return response.text[:500] or "No error details were returned."


# ---------------------------------------------------------
# 5. CHECK CONFIGURATION BEFORE STARTING OAUTH
# ---------------------------------------------------------
if not BACKEND_URL:
    st.error(
        "Backend URL is missing. Set BACKEND_URL in "
        "Streamlit Secrets to your actual Render service URL."
    )
    st.stop()

if not CLIENT_ID or not CLIENT_SECRET:
    st.error(
        "Google OAuth credentials are missing. Check the "
        "google_oauth section in Streamlit Secrets."
    )
    st.stop()

oauth2 = OAuth2Component(
    CLIENT_ID,
    CLIENT_SECRET,
    "https://accounts.google.com/o/oauth2/v2/auth",
    "https://oauth2.googleapis.com/token",
)

# ---------------------------------------------------------
# 6. GOOGLE SIGN-IN
# ---------------------------------------------------------
if not st.session_state.access_token:
    st.markdown("<br><br>", unsafe_allow_html=True)

    _, center, _ = st.columns([1, 1.5, 1])

    with center:
        st.markdown(
            """
            <div style="text-align:center; padding:1rem 0 2rem 0;">
                <h1 style="color:#ffffff;">
                    Enterprise Intelligence
                </h1>
                <p style="color:#94a3b8;">
                    Secure Knowledge Retrieval & Workspace Discovery
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.subheader("Secure sign-in")
            st.write(
                "Authenticate with Google to access the "
                "Enterprise Intelligence workspace."
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
                    token_data = result.get("token", result)

                    # The backend verifies Google ID tokens.
                    # Never substitute an OAuth access token here.
                    google_id_token = token_data.get("id_token")

                    if not google_id_token:
                        st.error(
                            "Google did not return an ID token. "
                            "Check the OAuth configuration and scopes."
                        )
                    else:
                        with st.spinner(
                            "Verifying your Google identity..."
                        ):
                            response = requests.post(
                                f"{BACKEND_URL}/api/v1/auth/google",
                                json={"id_token": google_id_token},
                                timeout=30,
                            )

                        if response.status_code == 200:
                            data = response.json()
                            app_token = data.get("access_token")

                            if not app_token:
                                st.error(
                                    "The backend response did not "
                                    "contain an application access token."
                                )
                            else:
                                st.session_state.access_token = app_token
                                st.session_state.user_info = data
                                st.session_state.last_search = None
                                st.rerun()
                        else:
                            st.error(
                                "Google authentication was rejected "
                                f"({response.status_code}): "
                                f"{backend_error_message(response)}"
                            )

            except requests.Timeout:
                st.error(
                    "The backend took too long to respond. "
                    "Check whether your Render service is awake."
                )
            except requests.RequestException as exc:
                st.error(f"Could not reach the backend: {exc}")
            except Exception as exc:
                st.error(
                    "Google sign-in encountered an error. "
                    f"Details: {exc}"
                )

    st.stop()

# ---------------------------------------------------------
# 7. AUTHENTICATED WORKSPACE
# ---------------------------------------------------------
user_info = st.session_state.user_info or {}

with st.sidebar:
    st.title("🛡️ Enterprise Portal")
    st.caption("Authenticated workspace")

    email = user_info.get("email")
    user_id = user_info.get("user_id", "Authenticated user")
    tenant_id = user_info.get("tenant_id", "Unknown tenant")
    tier = user_info.get("tier", "STANDARD")

    st.write(f"**Account:** {email or user_id}")
    st.write(f"**Access tier:** {tier}")
    st.caption(f"Tenant: {tenant_id}")

    st.divider()

    if st.button("Sign out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.user_info = None
        st.session_state.last_search = None
        st.rerun()

st.title("Enterprise Context & Intelligence")
st.caption(
    "Search your connected knowledge sources and retrieve "
    "relevant enterprise context."
)

query = st.text_input(
    "Knowledge search",
    placeholder="Ask about a document, project, policy, or relationship...",
)

search_clicked = st.button(
    "Execute intelligence query",
    type="primary",
    use_container_width=False,
)

if search_clicked:
    if not query.strip():
        st.warning("Enter a search query first.")
    else:
        try:
            with st.spinner("Searching enterprise knowledge..."):
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/search",
                    headers=get_auth_headers(),
                    json={
                        "query": query.strip(),
                        "page": 1,
                        "page_size": 10,
                    },
                    timeout=45,
                )

            if response.status_code == 200:
                st.session_state.last_search = response.json()
            elif response.status_code == 401:
                st.error(
                    "Your session was rejected. Sign out and sign in "
                    "again. The backend token-validation code also "
                    "needs to be checked."
                )
            elif response.status_code == 403:
                st.error(
                    "Your account does not have permission to access "
                    "this resource."
                )
            else:
                st.error(
                    f"Search failed ({response.status_code}): "
                    f"{backend_error_message(response)}"
                )

        except requests.Timeout:
            st.error("Search timed out. Please try again.")
        except requests.RequestException as exc:
            st.error(f"Could not reach the search service: {exc}")

# ---------------------------------------------------------
# 8. DISPLAY SEARCH RESPONSE
# ---------------------------------------------------------
search_data = st.session_state.last_search

if search_data:
    synthesis = search_data.get("ai_synthesis") or {}
    summary = synthesis.get("summary")

    if summary:
        st.subheader("Intelligence summary")
        st.info(summary)

    results = search_data.get("results") or []

    st.subheader(f"Search results ({len(results)})")

    if not results:
        st.write("No results were returned for this query.")

    for index, item in enumerate(results, start=1):
        with st.container(border=True):
            st.markdown(
                f"**{index}. {item.get('title') or 'Untitled result'}**"
            )

            snippet = item.get("snippet")
            if snippet:
                st.write(snippet)
            else:
                st.caption("No preview was provided.")

            # Evidence and citations will be added after the backend
            # returns real document IDs and source metadata.
