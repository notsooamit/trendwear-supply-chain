import streamlit as st
from core.data_loader import load_all_data
from utils.formatters import format_currency, format_number

st.set_page_config(page_title="Platform Overview", layout="wide")
st.title("TrendWear Enterprise IBP Control Tower")
st.caption("Integrated Sales & Operations Planning and Procurement Optimization System")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Problem Statement 1: Integrated S&OP (P2)")
    st.markdown("""
    **Demand & Supply Planning:** Reconciles 24-month regional sales projections against multi-plant manufacturing capacity and material requirements planning (MRP). Evaluates rolling gross margins and financial water-falls.
    
    **Markdown Recommender:** Analyzes 52-week sell-through rates to classify inventory velocity (Fast, Normal, Slow) and calculates optimal discount timings to recover working capital before product cycle termination.
    """)

with col2:
    st.subheader("Problem Statement 2: Procurement Optimization (PR1)")
    st.markdown("""
    **Procurement Optimizer:** Formulates a Mixed-Integer Linear Program (MILP) using PuLP to allocate raw material demand across approved suppliers, minimizing landed procurement costs while enforcing MOQ, capacity, and contract bounds.
    
    **Risk Prediction Pipeline:** Supervised Machine Learning models (XGBoost Regressor and Random Forest Classifier) trained on 8,000 purchase order transactions to predict shipment delays and classify risk categories prior to PO commitment.
    """)

st.markdown("---")

st.subheader("Master Data and Transactional Metrics")

data = load_all_data()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Approved Suppliers", len(data["suppliers"]))
col2.metric("Fabric Master Items", len(data["fabrics"]))
col3.metric("SKU Master Styles", len(data["skus"]))
col4.metric("Manufacturing Hubs", len(data["plants"]))

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Contracts", len(data["contracts"]))
col2.metric("Historical PO Records", format_number(len(data["purchase_orders"])))
col3.metric("Demand Forecast Points", format_number(len(data["demand_forecast"])))
col4.metric("Inventory Records", format_number(len(data["inventory"])))

st.markdown("---")
st.caption("Use the primary navigation panel on the left to access module workspaces.")
