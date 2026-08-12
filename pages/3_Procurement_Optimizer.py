import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_loader import load_all_data, get_supplier_names_map
from core.optimizer import build_and_solve
from core.sop_engine import get_available_periods

st.set_page_config(page_title="Procurement Optimizer", layout="wide")
st.title("Procurement Optimizer (PR1)")

data = load_all_data()
periods = get_available_periods(data)
sup_names = get_supplier_names_map()

# Sidebar controls
st.sidebar.header("Optimization Parameters")
selected_period = st.sidebar.selectbox("Demand Period", ["All Periods"] + periods)
period_filter = None if selected_period == "All Periods" else selected_period

cost_weight = st.sidebar.slider("Cost Weight", 0.0, 2.0, 1.0, 0.1)
risk_weight = st.sidebar.slider("Risk Weight", 0.0, 2.0, 0.3, 0.05)
lead_time_weight = st.sidebar.slider("Lead Time Weight", 0.0, 2.0, 0.1, 0.05)
quality_threshold = st.sidebar.slider("Min Quality Threshold (%)", 70.0, 99.0, 80.0, 1.0)

run_button = st.sidebar.button("Run Optimization", type="primary")

if run_button:
    with st.spinner("Solving optimization model..."):
        result = build_and_solve(
            data, period=period_filter,
            cost_weight=cost_weight, risk_weight=risk_weight,
            lead_time_weight=lead_time_weight, quality_threshold=quality_threshold
        )

    if result["status"] != "Optimal":
        st.error(f"Optimization failed: {result['status']}")
        st.stop()

    st.session_state["opt_result"] = result
    st.success("Optimization complete.")

# Display results
if "opt_result" not in st.session_state:
    st.info("Set parameters in the sidebar and click 'Run Optimization' to start.")
    st.stop()

result = st.session_state["opt_result"]
summary = result["summary"]
alloc = result["allocations"]
util = result["utilization"]
cost_bd = result["cost_breakdown"]

# KPI Row
st.subheader("Optimization Results")
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total Cost", f"${summary['total_cost']:,.0f}")
col2.metric("Total Meters", f"{summary['total_meters']:,.0f}")
col3.metric("Suppliers Used", summary["num_suppliers_used"])
col4.metric("Fabrics Covered", summary["num_fabrics_covered"])
col5.metric("Fulfillment", f"{summary.get('fulfillment_pct', 100)}%")
col6.metric("Avg Risk", f"{summary['weighted_avg_risk']:.3f}")

if summary.get("total_shortfall", 0) > 0:
    st.warning(f"Demand shortfall: {summary['total_shortfall']:,.0f} meters could not be sourced due to capacity constraints.")

st.markdown("---")

# Allocation details
col1, col2 = st.columns(2)

with col1:
    st.subheader("Cost Breakdown")
    cost_data = pd.DataFrame([
        {"Component": "Procurement Cost", "Value": cost_bd["procurement_cost"]},
        {"Component": "Risk Penalty", "Value": cost_bd["risk_penalty"]},
        {"Component": "Lead Time Penalty", "Value": cost_bd["lead_time_penalty"]},
    ])
    fig = px.pie(cost_data, values="Value", names="Component",
                 color="Component",
                 color_discrete_map={
                     "Procurement Cost": "#3498db",
                     "Risk Penalty": "#e74c3c",
                     "Lead Time Penalty": "#f39c12"
                 })
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

with col2:
    st.subheader("Allocation by Supplier")
    if not alloc.empty:
        sup_alloc = alloc.groupby("supplier_id").agg(
            total_meters=("allocated_meters", "sum"),
            total_cost=("total_cost", "sum"),
        ).reset_index()
        sup_alloc["supplier_name"] = sup_alloc["supplier_id"].map(sup_names)
        fig = px.bar(sup_alloc.nlargest(15, "total_meters"),
                     x="supplier_name", y="total_meters",
                     color="total_cost",
                     labels={"total_meters": "Allocated (meters)", "supplier_name": "Supplier",
                             "total_cost": "Cost ($)"},
                     color_continuous_scale="Blues")
        fig.update_layout(xaxis_tickangle=-45, margin=dict(t=20, b=80, l=20, r=20))
        st.plotly_chart(fig, width='stretch')

st.markdown("---")

# Supplier utilization
st.subheader("Supplier Utilization")
if not util.empty:
    util_display = util.copy()
    util_display["supplier_name"] = util_display["supplier_id"].map(sup_names)
    util_display = util_display.sort_values("utilization_pct", ascending=False)

    fig = px.bar(util_display, x="supplier_name", y="utilization_pct",
                 color="utilization_pct",
                 labels={"utilization_pct": "Utilization %", "supplier_name": "Supplier"},
                 color_continuous_scale="RdYlGn_r")
    fig.add_hline(y=80, line_dash="dash", line_color="red",
                  annotation_text="80% threshold")
    fig.update_layout(xaxis_tickangle=-45, margin=dict(t=20, b=80, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

# Allocation heatmap
st.subheader("Allocation Heatmap (Supplier x Fabric)")
if not alloc.empty:
    pivot = alloc.pivot_table(
        index="supplier_id", columns="fabric_id",
        values="allocated_meters", fill_value=0
    )
    # Only show non-zero columns and rows
    pivot = pivot.loc[(pivot > 0).any(axis=1), (pivot > 0).any(axis=0)]

    if not pivot.empty:
        fig = px.imshow(pivot.values,
                        x=pivot.columns.tolist(),
                        y=pivot.index.tolist(),
                        labels=dict(x="Fabric", y="Supplier", color="Meters"),
                        color_continuous_scale="Blues",
                        aspect="auto")
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=500)
        st.plotly_chart(fig, width='stretch')

# Full allocation table
with st.expander("Full Allocation Table"):
    if not alloc.empty:
        display_alloc = alloc.copy()
        display_alloc["supplier_name"] = display_alloc["supplier_id"].map(sup_names)
        st.dataframe(
            display_alloc[["supplier_name", "fabric_id", "allocated_meters",
                          "unit_price", "total_cost", "lead_time_days", "supplier_risk"]],
            width='stretch'
        )
