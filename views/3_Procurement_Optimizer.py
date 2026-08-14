import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_loader import load_all_data, get_supplier_names_map
from core.optimizer import build_and_solve
from core.sop_engine import get_available_periods
from utils.formatters import format_currency, format_number, format_pct

st.set_page_config(page_title="Procurement Optimizer", layout="wide")
st.title("Raw Material Procurement Optimizer (MILP Formulation)")
st.caption("Mixed-Integer Linear Programming mathematical model minimizing total landed procurement costs subject to supplier capacity, MOQ, and contract risk constraints.")

data = load_all_data()
periods = get_available_periods(data)
sup_names = get_supplier_names_map()

st.sidebar.markdown("### Optimization Controls & Weights")
selected_period = st.sidebar.selectbox("Target Demand Period", ["All Periods"] + periods)
period_filter = None if selected_period == "All Periods" else selected_period

cost_weight = st.sidebar.slider("Cost Weight Factor (w_cost)", 0.0, 2.0, 1.0, 0.1)
risk_weight = st.sidebar.slider("Supplier Risk Penalty Weight (w_risk)", 0.0, 2.0, 0.3, 0.05)
lead_time_weight = st.sidebar.slider("Lead Time Penalty Weight (w_lt)", 0.0, 2.0, 0.1, 0.05)
quality_threshold = st.sidebar.slider("Minimum Supplier Quality Threshold (%)", 70.0, 99.0, 80.0, 1.0)

run_button = st.sidebar.button("Execute Optimizer Engine", type="primary")

if run_button:
    with st.spinner("Executing PuLP CBC Solver..."):
        result = build_and_solve(
            data, period=period_filter,
            cost_weight=cost_weight, risk_weight=risk_weight,
            lead_time_weight=lead_time_weight, quality_threshold=quality_threshold
        )

    if result["status"] != "Optimal":
        st.error(f"Solver termination status: {result['status']}")
        st.stop()

    st.session_state["opt_result"] = result
    st.success("Mathematical Optimization Model Solved Successfully.")

if "opt_result" not in st.session_state:
    st.info("Configure decision criteria weights in the control panel and click 'Execute Optimizer Engine'.")
    st.stop()

result = st.session_state["opt_result"]
summary = result["summary"]
alloc = result["allocations"]
util = result["utilization"]
cost_bd = result["cost_breakdown"]

st.subheader("Optimal Procurement Allocation Summary")
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total Landed Cost", format_currency(summary["total_cost"]))
col2.metric("Procured Fabric Volume", f"{format_number(summary['total_meters'])} m")
col3.metric("Suppliers Selected", summary["num_suppliers_used"])
col4.metric("Fabrics Sourced", summary["num_fabrics_covered"])
col5.metric("Demand Fulfillment", format_pct(summary.get("fulfillment_pct", 100)))
col6.metric("Weighted Risk Index", f"{summary['weighted_avg_risk']:.3f}")

if summary.get("total_shortfall", 0) > 0:
    st.warning(f"Unmet Demand Penalty Triggered: {format_number(summary['total_shortfall'])} meters could not be allocated due to capacity constraints.")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Objective Function Cost Components")
    cost_data = pd.DataFrame([
        {"Component": "Landed Procurement Cost", "Value": cost_bd["procurement_cost"]},
        {"Component": "Supplier Risk Penalty", "Value": cost_bd["risk_penalty"]},
        {"Component": "Lead Time Penalty", "Value": cost_bd["lead_time_penalty"]},
    ])
    fig = px.pie(
        cost_data, values="Value", names="Component",
        color="Component",
        color_discrete_map={
            "Landed Procurement Cost": "#0a6ed1",
            "Supplier Risk Penalty": "#bb0000",
            "Lead Time Penalty": "#e9730c"
        }
    )
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Procurement Volume Allocation by Supplier")
    if not alloc.empty:
        sup_alloc = alloc.groupby("supplier_id").agg(
            total_meters=("allocated_meters", "sum"),
            total_cost=("total_cost", "sum"),
        ).reset_index()
        sup_alloc["supplier_name"] = sup_alloc["supplier_id"].map(sup_names)
        fig = px.bar(
            sup_alloc.nlargest(15, "total_meters"),
            x="supplier_name", y="total_meters",
            color="total_cost",
            labels={
                "total_meters": "Allocated Meters",
                "supplier_name": "Supplier Entity",
                "total_cost": "Total Value ($)"
            },
            color_continuous_scale="Blues"
        )
        fig.update_layout(xaxis_tickangle=-45, margin=dict(t=20, b=80, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("Supplier Contract Capacity Utilization")
if not util.empty:
    util_display = util.copy()
    util_display["supplier_name"] = util_display["supplier_id"].map(sup_names)
    util_display = util_display.sort_values("utilization_pct", ascending=False)

    fig = px.bar(
        util_display, x="supplier_name", y="utilization_pct",
        color="utilization_pct",
        labels={"utilization_pct": "Capacity Utilization (%)", "supplier_name": "Supplier Entity"},
        color_continuous_scale="RdYlGn_r"
    )
    fig.add_hline(y=80, line_dash="dash", line_color="#bb0000",
                  annotation_text="80% High Load Threshold")
    fig.update_layout(xaxis_tickangle=-45, margin=dict(t=20, b=80, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Matrix Allocation Distribution (Supplier x Fabric)")
if not alloc.empty:
    pivot = alloc.pivot_table(
        index="supplier_id", columns="fabric_id",
        values="allocated_meters", fill_value=0
    )
    pivot = pivot.loc[(pivot > 0).any(axis=1), (pivot > 0).any(axis=0)]

    if not pivot.empty:
        fig = px.imshow(
            pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            labels=dict(x="Fabric Material", y="Supplier Entity", color="Allocated Meters"),
            color_continuous_scale="Blues",
            aspect="auto"
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=450)
        st.plotly_chart(fig, use_container_width=True)

with st.expander("Detailed Allocation Table"):
    if not alloc.empty:
        display_alloc = alloc.copy()
        display_alloc["supplier_name"] = display_alloc["supplier_id"].map(sup_names)
        st.dataframe(
            display_alloc[["supplier_name", "fabric_id", "allocated_meters",
                          "unit_price", "total_cost", "lead_time_days", "supplier_risk"]],
            use_container_width=True
        )
