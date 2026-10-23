
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
        color: white;
        border-radius: 8px;
        border: 1px solid #334155;
    }

    div[data-testid="stMetric"] {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid #1e293b;
        padding: 1rem;
        border-radius: 12px;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. CONFIGURATION
# ---------------------------------------------------------
DEFAULT_BACKEND_URL = "https://enterprise-ke-3.onrender.com"


def read_secret(key, default=None):
    """Read a Streamlit secret safely."""
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


# Prefer an explicitly configured URL, then environment variables.
# The known Render URL prevents an absent secret from stopping startup.
GOOGLE_CONFIG = read_secret("google_oauth", {})
if not GOOGLE_CONFIG:
    GOOGLE_CONFIG = read_secret("web", {})

if not hasattr(GOOGLE_CONFIG, "get"):
    GOOGLE_CONFIG = {}

BACKEND_URL = str(
    read_secret("BACKEND_URL")
    or os.getenv("BACKEND_URL")
    or GOOGLE_CONFIG.get("BACKEND_URL")
    or DEFAULT_BACKEND_URL
).strip().rstrip("/")

CLIENT_ID = str(
    GOOGLE_CONFIG.get("client_id")
    or os.getenv("GOOGLE_CLIENT_ID")
    or ""
).strip()

CLIENT_SECRET = str(
    GOOGLE_CONFIG.get("client_secret")
    or os.getenv("GOOGLE_CLIENT_SECRET")
    or ""
).strip()

REDIRECT_URI = (
    "https://enterprise-ke-hqrlscaknjikcwz5kpndrt.streamlit.app"
)

# ---------------------------------------------------------
# 4. SESSION STATE
# ---------------------------------------------------------
DEFAULT_STATE = {
    "access_token": None,
    "user_info": None,
    "last_search": None,
}

for key, default in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default


def get_auth_headers():
    """Return the application's backend-issued JWT."""
    token = st.session_state.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def backend_error_message(response):
    """Extract a safe, readable message from an API response."""
    try:
        body = response.json()
        if isinstance(body, dict):
            detail = body.get("detail") or body.get("message")
            if detail:
                return str(detail)[:700]
        elif isinstance(body, str):
            return body[:700]
    except (ValueError, TypeError):
        pass

    return response.text[:500] or "No error details were returned."


def show_backend_failure(response, operation):
    """Display actionable messages for common backend failures."""
    if response.status_code == 503:
        st.error(
            f"{operation}: Render returned HTTP 503. "
            "The backend service may be unavailable or failing "
            "during startup. Check the Render service logs."
        )
    elif response.status_code == 502:
        st.error(
            f"{operation}: Render returned HTTP 502. "
            "Check the backend service and its startup logs."
        )
    elif response.status_code >= 500:
        st.error(
            f"{operation}: backend error "
            f"({response.status_code}). "
            f"{backend_error_message(response)}"
        )
    else:
        st.error(
            f"{operation} failed ({response.status_code}): "
            f"{backend_error_message(response)}"
        )


# ---------------------------------------------------------
# 5. VALIDATE CONFIGURATION
# ---------------------------------------------------------
if not BACKEND_URL.startswith("https://"):
    st.error(
        "BACKEND_URL must be a valid HTTPS URL. "
        "Check your Streamlit Secrets configuration."
    )
    st.stop()

if not CLIENT_ID or not CLIENT_SECRET:
    st.error(
        "Google OAuth credentials are missing. Configure "
        "client_id and client_secret in the google_oauth "
        "section of Streamlit Secrets."
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
            <div style="text-align:center; padding:1rem 0 2rem;">
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
                "Authenticate with Google to access your "
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

                if isinstance(result, dict) and result:
                    token_data = result.get("token", result)

                    if not isinstance(token_data, dict):
                        st.error(
                            "Google returned an unexpected token response."
                        )
                    else:
                        google_id_token = token_data.get("id_token")

                        if not google_id_token:
                            st.error(
                                "Google did not return an ID token. "
                                "Confirm that the OAuth client, redirect "
                                "URI, and OpenID scopes are configured "
                                "correctly."
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
                                try:
                                    data = response.json()
                                except ValueError:
                                    st.error(
                                        "The backend returned an invalid "
                                        "JSON response during sign-in."
                                    )
                                    st.stop()

                                app_token = data.get("access_token")

                                if not app_token:
                                    st.error(
                                        "The backend did not return an "
                                        "application access token."
                                    )
                                else:
                                    st.session_state.access_token = app_token
                                    st.session_state.user_info = data
                                    st.session_state.last_search = None
                                    st.rerun()
                            else:
                                show_backend_failure(
                                    response,
                                    "Google authentication",
                                )

            except requests.Timeout:
                st.error(
                    "The backend timed out during sign-in. "
                    "Check whether the Render service is running."
                )
            except requests.ConnectionError:
                st.error(
                    "Could not connect to the backend at "
                    f"{BACKEND_URL}. Check the Render service status."
                )
            except requests.RequestException:
                st.error(
                    "A network error occurred while contacting "
                    "the backend. Please retry."
                )
            except Exception as exc:
                # Avoid displaying credentials or token data.
                st.error(
                    "The sign-in component encountered an error: "
                    f"{type(exc).__name__}. Check the Streamlit logs "
                    "for details."
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

# ---------------------------------------------------------
# 8. KNOWLEDGE SEARCH
# ---------------------------------------------------------
with st.form("enterprise_search_form"):
    query = st.text_input(
        "Knowledge search",
        placeholder=(
            "Ask about a document, project, policy, or relationship..."
        ),
    )

    search_clicked = st.form_submit_button(
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
                try:
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise ValueError("Expected a JSON object")
                    st.session_state.last_search = payload
                except ValueError:
                    st.error(
                        "The search backend returned an invalid response."
                    )

            elif response.status_code == 401:
                st.session_state.access_token = None
                st.session_state.user_info = None
                st.session_state.last_search = None
                st.warning(
                    "Your session was rejected. Please sign in again."
                )
                st.rerun()

            elif response.status_code == 403:
                st.error(
                    "Access denied. Your account may not have permission "
                    "to search this workspace."
                )

            else:
                show_backend_failure(response, "Search")

        except requests.Timeout:
            st.error(
                "Search timed out. The backend may be slow or unavailable."
            )
        except requests.ConnectionError:
            st.error(
                "Could not connect to the search backend. "
                "Check the Render service."
            )
        except requests.RequestException:
            st.error(
                "A network error occurred while executing the search."
            )

# ---------------------------------------------------------
# 9. DISPLAY SEARCH RESPONSE
# ---------------------------------------------------------
search_data = st.session_state.last_search

if search_data:
    synthesis = search_data.get("ai_synthesis") or {}
    summary = (
        synthesis.get("summary")
        if isinstance(synthesis, dict)
        else None
    )

    if summary:
        st.subheader("Intelligence summary")
        st.info(summary)

    results = search_data.get("results") or []

    if not isinstance(results, list):
        results = []

    st.subheader(f"Search results ({len(results)})")

    if not results:
        st.write("No results were returned for this query.")

    for index, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue

        with st.container(border=True):
            title = item.get("title") or "Untitled result"
            st.markdown(f"**{index}. {title}**")

            snippet = item.get("snippet")
            if snippet:
                st.write(snippet)
            else:
                st.caption("No preview was provided.")

            # Display source metadata when supplied by the backend.
            source = item.get("source") or item.get("source_name")
            if source:
                st.caption(f"Source: {source}")

            citation = item.get("citation") or item.get("document_id")
            if citation:
                st.caption(f"Evidence reference: {citation}")

st.divider()
st.caption(
    "Enterprise Intelligence Platform · "
    "Authenticated access to your configured backend"
    )
                                    
