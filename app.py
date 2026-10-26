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
            # returns real document IDs and source metadata.import streamlit as st
from neo4j import GraphDatabase
from neo4j_viz.model import Node, Relationship, VisualizationGraph
from neo4j_viz.streamlit import display_widget  # High-fidelity two-way widget sync

# 1. PREMIUM LAYOUT AND THEME CONFIGURATION
st.set_page_config(
    page_title="Enterprise Knowledge RAG",
    page_icon="🧬",
    layout="wide",  # Forces the premium edge-to-edge dashboard layout
    initial_sidebar_state="expanded"
)

# Initialize global state variables to track navigation and user clicks
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "selected_node_id" not in st.session_state:
    st.session_state.selected_node_id = None
if "current_cypher_query" not in st.session_state:
    # Fallback default query to show data initially
    st.session_state.current_cypher_query = "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 15"

# 2. NEO4J CONNECTION HELPER
# Replace credentials with your enterprise Neo4j URI and password
NEO4J_URI = "neo4j+s://your-instance.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_secure_password"

@st.cache_resource
def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 3. NEO4J TO VIZ TRANSLATION ENGINE
def fetch_and_format_graph(cypher_query):
    """Executes a Cypher query and formats it perfectly for neo4j-viz."""
    driver = get_neo4j_driver()
    nodes_map = {}
    relationships = []
    
    with driver.session() as session:
        result = session.run(cypher_query)
        for record in result:
            # Process paths, nodes, and relationships returned by the query
            for key in record.keys():
                value = record[key]
                
                # If the value is a singular Node
                if data_type := getattr(value, "labels", None):  
                    node_id = value.element_id
                    if node_id not in nodes_map:
                        # Grab a primary property (like 'name' or 'title') for the visible caption
                        caption = value.get("name") or value.get("title") or str(node_id)
                        nodes_map[node_id] = Node(
                            id=node_id, 
                            caption=caption,
                            size=25,
                            properties=dict(value.items()) # Keep all metadata for drill-down views
                        )
                
                # If the value is a singular Relationship
                elif hasattr(value, "type") and hasattr(value, "start_node"):
                    relationships.append(Relationship(
                        source=value.start_node.element_id,
                        target=value.end_node.element_id,
                        caption=value.type
                    ))
                    
    # Compile objects into a renderable VisualizationGraph
    viz_graph = VisualizationGraph(nodes=list(nodes_map.values()), relationships=relationships)
    # Give different node types unique professional colors out-of-the-box
    viz_graph.color_nodes(field="caption") 
    return viz_graph


# 4. BUILDING THE PREMIUM SCREEN LAYOUT
# Split the layout into unequal columns (35% Chat Interface, 65% Graph Interactive Canvas)
chat_col, graph_col = st.columns([35, 65])

# --- LEFT COLUMN: THE RAG CHAT ASSISTANT ---
with chat_col:
    st.subheader("🧬 GraphAI Assistant")
    st.caption("Enterprise RAG Engine connected directly to Neo4j AuraDB")
    
    # Scrollable container for the chat log
    chat_container = st.container(height=500)
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
    # Input field at the bottom of the column
    if user_prompt := st.chat_input("Ask a question about the knowledge network..."):
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_prompt)
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        
        # --- PLACEHOLDER FOR YOUR LLM / RAG LOGIC ---
        # 1. Vector search Neo4j or prompt your LLM.
        # 2. Suppose your LLM outputs an answer and says: "I used these specific nodes."
        # 3. Dynamically rewrite the Cypher query based on the entities found!
        simulated_answer = f"Based on the retrieved context for '{user_prompt}', I found a deep relationship path..."
        
        # Update the query state so the right side column immediately updates
        st.session_state.current_cypher_query = """
            MATCH (n)-[r]->(m) 
            WHERE n.name CONTAINS 'Active' OR m.name CONTAINS 'Active'
            RETURN n, r, m LIMIT 20
        """
        
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(simulated_answer)
        st.session_state.chat_history.append({"role": "assistant", "content": simulated_answer})
        st.rerun()


# --- RIGHT COLUMN: INTERACTIVE VISUALIZATION & DRILL-DOWN ---
with graph_col:
    st.subheader("🌐 Knowledge Sub-Graph Explorer")
    
    # Fetch the graph structured perfectly for the widget
    current_viz_graph = fetch_and_format_graph(st.session_state.current_cypher_query)
    
    # Display the interactive component with two-way sync
    # If a user clicks a node, 'widget_events' catches it live!
    widget_events = display_widget(
        current_viz_graph, 
        width="100%", 
        height="500px",
        show_hover_tooltip=True
    )
    
    # 5. ENTERING THE "NEW PLACE" (DRILL-DOWN ENGINE)
    # Detect if a user clicked a node on the frontend canvas
    if widget_events and widget_events.get("selected_node_ids"):
        clicked_id = widget_events["selected_node_ids"][0]
        
        # Enter the deep dive interface
        st.markdown("---")
        st.markdown(f"### 🕳️ Deep-Dive: Node Profile Details")
        
        # Find the specific node object from our fetched data map
        matching_node = next((n for n in current_viz_graph.nodes if n.id == clicked_id), None)
        
        if matching_node:
            node_props = matching_node.properties
            
            # Split the new drill-down area into sub-tabs for a clean premium look
            tab1, tab2, tab3 = st.tabs(["📊 Core Attributes", "📝 Raw Source Text", "⚡ Isolated Neighbors"])
            
            with tab1:
                # Format properties into clean key-value pairs
                for key, val in node_props.items():
                    st.markdown(f"**{key.title()}:** `{val}`")
                    
            with tab2:
                # Show the massive text chunk that built this node
                raw_chunk = node_props.get("text_content", "No raw document chunk mapped to this entity.")
                st.info(raw_chunk)
                
            with tab3:
                # Give a button to alter the map layout and focus strictly on this new neighborhood
                st.write("Isolate this node to explore its deep hidden relationships.")
                if st.button(f"🎯 Focus Canvas on {matching_node.caption}"):
                    # Rewrite the query to expand deeply on ONLY the clicked item
                    st.session_state.current_cypher_query = f"""
                        MATCH (n)-[r*1..2]-(m)
                        WHERE elementId(n) = '{clicked_id}'
                        RETURN n, r, m LIMIT 30
                    """
                    st.rerun()
