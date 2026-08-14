import streamlit as st

st.set_page_config(
    page_title="TrendWear Enterprise IBP Control Tower",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional SAP IBP / Fiori Custom CSS
st.markdown("""
<style>
    /* SAP Fiori Corporate Header */
    .stApp > header {
        background-color: #0f2537 !important;
    }
    
    /* Global Background & Fonts */
    .main {
        background-color: #f4f6f9;
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    }
    
    /* Sidebar Base Styling */
    [data-testid="stSidebar"] {
        background-color: #1c2d42 !important;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span {
        color: #e1e6eb !important;
    }
    
    /* Sidebar Navigation Items */
    [data-testid="stSidebarNav"] a {
        color: #c0cad5 !important;
    }
    
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: #2b3e56 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-left: 4px solid #0a6ed1 !important;
    }

    /* Sidebar Buttons (Sign Out, etc.) */
    [data-testid="stSidebar"] button {
        background-color: #0a6ed1 !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 4px !important;
    }
    
    [data-testid="stSidebar"] button * {
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] button:hover {
        background-color: #0854a0 !important;
        color: #ffffff !important;
    }

    /* Sidebar Selectbox & Text Input Fields */
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: #2b3e56 !important;
        color: #ffffff !important;
        border: 1px solid #415775 !important;
        border-radius: 4px !important;
    }
    
    [data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] input {
        background-color: #2b3e56 !important;
        color: #ffffff !important;
        border: 1px solid #415775 !important;
    }
    
    /* Login Form styling */
    .login-box {
        max-width: 480px;
        margin: 5vh auto;
        padding: 2.5rem;
        background-color: #ffffff;
        border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-top: 5px solid #0a6ed1;
    }
    
    .login-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f2537;
        margin-bottom: 0.2rem;
    }
    
    .login-subtitle {
        font-size: 0.95rem;
        color: #5b6b7c;
        margin-bottom: 1.8rem;
    }
    
    /* Role Badge */
    .role-badge {
        display: inline-block;
        padding: 0.3em 0.7em;
        font-size: 0.8rem;
        font-weight: 600;
        border-radius: 3px;
        background-color: #0a6ed1;
        color: #ffffff !important;
        margin-left: 8px;
    }
    
    /* Metric Card Styling & Font Overflow Overrides */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 0.9rem 1.1rem !important;
        border-radius: 4px !important;
        border: 1px solid #e1e6eb !important;
        border-left: 4px solid #0a6ed1 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: #0f2537 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: clip !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: #5b6b7c !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    /* Table Styling */
    .dataframe {
        font-size: 0.85rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Authentication System State
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None

USER_DB = {
    "admin": {"password": "password", "role": "System Administrator", "name": "System Administrator"},
    "planner": {"password": "password", "role": "S&OP Planner", "name": "Lead S&OP Planner"},
    "procurement": {"password": "password", "role": "Procurement Manager", "name": "Global Procurement Manager"},
    "exec": {"password": "password", "role": "Executive Leader", "name": "Executive Leadership"}
}

def login():
    st.markdown("""
    <div class="login-box">
        <div class="login-title">TrendWear Enterprise IBP</div>
        <div class="login-subtitle">Integrated Business Planning & Procurement Control Tower</div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("User Identification")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign In", use_container_width=True)
        
        if submit:
            if username in USER_DB and USER_DB[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.role = USER_DB[username]["role"]
                st.session_state.username = USER_DB[username]["name"]
                st.rerun()
            else:
                st.error("Authentication failed. Please verify user credentials.")
    
    st.markdown("""
    <br>
    <p style="font-size:0.85rem; font-weight:600; color:#0f2537; margin-bottom:0.5rem;">Demonstration Credentials:</p>
    <table style="width:100%; font-size:0.8rem; border-collapse:collapse; border:1px solid #e1e6eb;">
        <thead>
            <tr style="background-color:#f4f6f9; text-align:left;">
                <th style="padding:6px; border:1px solid #e1e6eb;">User ID</th>
                <th style="padding:6px; border:1px solid #e1e6eb;">Password</th>
                <th style="padding:6px; border:1px solid #e1e6eb;">Role</th>
            </tr>
        </thead>
        <tbody>
            <tr><td style="padding:6px; border:1px solid #e1e6eb;">admin</td><td style="padding:6px; border:1px solid #e1e6eb;">password</td><td style="padding:6px; border:1px solid #e1e6eb;">System Administrator</td></tr>
            <tr><td style="padding:6px; border:1px solid #e1e6eb;">planner</td><td style="padding:6px; border:1px solid #e1e6eb;">password</td><td style="padding:6px; border:1px solid #e1e6eb;">S&OP Planner</td></tr>
            <tr><td style="padding:6px; border:1px solid #e1e6eb;">procurement</td><td style="padding:6px; border:1px solid #e1e6eb;">password</td><td style="padding:6px; border:1px solid #e1e6eb;">Procurement Manager</td></tr>
            <tr><td style="padding:6px; border:1px solid #e1e6eb;">exec</td><td style="padding:6px; border:1px solid #e1e6eb;">password</td><td style="padding:6px; border:1px solid #e1e6eb;">Executive Leader</td></tr>
        </tbody>
    </table>
    </div>
    """, unsafe_allow_html=True)

def logout():
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()

# ---------------------------------------------------------
# Application Router (RBAC Routing without Emojis)
# ---------------------------------------------------------

if not st.session_state.logged_in:
    login()
else:
    with st.sidebar:
        st.markdown(f"**User:** {st.session_state.username}")
        st.markdown(f"**Role:** <span class='role-badge'>{st.session_state.role}</span>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True):
            logout()
        st.markdown("---")

    # Define Pages (NO EMOJIS)
    p_home = st.Page("views/0_Home.py", title="Platform Overview")
    p_exec = st.Page("views/1_Executive_Dashboard.py", title="Executive Dashboard")
    
    # S&OP Pages
    p_demand = st.Page("views/2_Demand_Supply_Planning.py", title="Demand & Supply Planning")
    p_markdown = st.Page("views/5_Markdown_Recommender.py", title="Markdown Recommender")
    
    # Procurement Pages
    p_procure = st.Page("views/3_Procurement_Optimizer.py", title="Procurement Optimizer")
    p_risk = st.Page("views/4_Risk_Prediction.py", title="Supplier Risk Prediction")
    
    # Advanced Analytics Pages
    p_scenario = st.Page("views/6_Scenario_Analysis.py", title="Scenario Analysis")
    
    role = st.session_state.role
    pages = {}
    
    if role == "System Administrator":
        pages["Overview"] = [p_home, p_exec]
        pages["S&OP Planning (P2)"] = [p_demand, p_markdown]
        pages["Procurement Optimization (PR1)"] = [p_procure, p_risk]
        pages["Advanced Analytics"] = [p_scenario]
        
    elif role == "S&OP Planner":
        pages["Overview"] = [p_home]
        pages["S&OP Planning (P2)"] = [p_demand, p_markdown]
        
    elif role == "Procurement Manager":
        pages["Overview"] = [p_home]
        pages["Procurement Optimization (PR1)"] = [p_procure, p_risk]
        
    elif role == "Executive Leader":
        pages["Overview"] = [p_home, p_exec]
        pages["Advanced Analytics"] = [p_scenario]
        
    pg = st.navigation(pages)
    pg.run()
