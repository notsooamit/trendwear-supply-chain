import streamlit as st

st.set_page_config(
    page_title="TrendWear Supply Chain",
    page_icon="TW",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">TrendWear Supply Chain Intelligence</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Integrated Procurement Optimization and S&OP Planning Platform</p>', unsafe_allow_html=True)

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("PR1: Procurement")
    st.markdown("""
    **Procurement Optimizer** - Allocate fabric procurement across suppliers using
    linear programming to minimize cost while respecting capacity, MOQ, and quality constraints.

    **Risk Prediction** - ML models (XGBoost, Random Forest) trained on 8000 historical
    purchase orders to predict delivery delays and classify risk before PO release.
    """)

with col2:
    st.subheader("P2: S&OP Planning")
    st.markdown("""
    **Demand & Supply Planning** - Reconcile demand forecasts with plant capacity and
    material requirements. Rolling S&OP cycle with financial rollup.

    **Markdown Recommender** - Analyze sell-through signals to recommend markdown
    timing for slow movers and flag stock-out risks for fast movers.
    """)

st.markdown("---")

st.subheader("Data Summary")

from core.data_loader import load_all_data
data = load_all_data()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Suppliers", len(data["suppliers"]))
col2.metric("Fabrics", len(data["fabrics"]))
col3.metric("SKUs", len(data["skus"]))
col4.metric("Plants", len(data["plants"]))

col1, col2, col3, col4 = st.columns(4)
col1.metric("Contracts", len(data["contracts"]))
col2.metric("Purchase Orders", f"{len(data['purchase_orders']):,}")
col3.metric("Demand Forecasts", f"{len(data['demand_forecast']):,}")
col4.metric("Inventory Records", len(data["inventory"]))

st.markdown("---")
st.caption("Use the sidebar to navigate between modules.")
