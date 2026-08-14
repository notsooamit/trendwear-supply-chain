import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_loader import load_all_data
from core.sop_engine import run_sop_cycle, get_available_periods
from utils.formatters import format_currency, format_number, format_pct

st.set_page_config(page_title="Demand & Supply Planning", layout="wide")
st.title("Sales and Operations Planning (S&OP)")
st.caption("Reconciling SKU demand forecasts with Material Requirements Planning (MRP) and manufacturing plant capacity.")

data = load_all_data()
periods = get_available_periods(data)

st.sidebar.markdown("### S&OP Configuration Controls")
selected_period = st.sidebar.selectbox("Planning Horizon Period", ["All Periods"] + periods)
period_filter = None if selected_period == "All Periods" else selected_period

results = run_sop_cycle(data, period=period_filter)

if "error" in results:
    st.error(results["error"])
    st.stop()

st.subheader("1. Demand Projections Overview")
col1, col2, col3 = st.columns(3)
demand_summary = results["demand_summary"]
col1.metric("Total Forecasted Demand", f"{format_number(demand_summary['total_demand'].sum())} units")
col2.metric("Active SKUs in Forecast", len(demand_summary))
col3.metric("Mean Forecast Confidence", format_pct(demand_summary["avg_confidence"].mean() * 100))

col1, col2 = st.columns(2)
with col1:
    cat_demand = demand_summary.groupby("category")["total_demand"].sum().reset_index()
    fig = px.bar(
        cat_demand, x="category", y="total_demand",
        labels={"total_demand": "Demand (Units)", "category": "Category"},
        title="Demand Breakdown by Product Category",
        color_discrete_sequence=["#0a6ed1"]
    )
    fig.update_layout(showlegend=False, margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    region_demand = results["demand_by_region"]
    fig = px.pie(
        region_demand, values="total_demand", names="region",
        title="Regional Demand Allocation Share",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("2. Material Requirements Planning (MRP Explosion)")
material_plan = results["material_plan"]

col1, col2 = st.columns(2)
col1.metric("Total Gross Fabric Requirement", f"{format_number(material_plan['total_required_meters'].sum())} meters")
col2.metric("Estimated Material Expenditure", format_currency(material_plan["estimated_material_cost"].sum()))

top_fabrics = material_plan.nlargest(15, "total_required_meters")
fig = px.bar(
    top_fabrics, x="fabric_name", y="total_required_meters",
    color="standard_lead_time_days",
    labels={
        "total_required_meters": "Required Meters",
        "fabric_name": "Fabric Item",
        "standard_lead_time_days": "Lead Time (Days)"
    },
    title="Top 15 Fabric Requirements and Contract Lead Times",
    color_continuous_scale="Viridis"
)
fig.update_layout(xaxis_tickangle=-45, margin=dict(t=40, b=80, l=20, r=20))
st.plotly_chart(fig, use_container_width=True)

with st.expander("Detailed Material Requirements Table"):
    st.dataframe(
        material_plan[["fabric_id", "fabric_name", "total_required_meters",
                       "standard_cost_per_meter", "standard_lead_time_days",
                       "estimated_material_cost", "num_skus"]].sort_values(
            "total_required_meters", ascending=False
        ),
        use_container_width=True
    )

st.markdown("---")

st.subheader("3. Plant Production Capacity Feasibility")
cap = results["capacity_check"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total SKU Demand", format_number(cap["total_demand_units"]))
col2.metric("Available Capacity Buffer", format_number(cap["remaining_capacity"]))
col3.metric("Capacity Utilization", f"{cap['utilization_pct']:.1f}%")
col4.metric("Feasibility Status", cap["demand_vs_remaining"])

if cap["gap_units"] > 0:
    st.warning(f"Capacity Shortfall Identified: {format_number(cap['gap_units'])} units exceed plant allocation limits.")

plant_bd = results["plant_breakdown"]
fig = go.Figure()
fig.add_trace(go.Bar(
    name="Allocated Volume", x=plant_bd["plant_id"], y=plant_bd["allocated"],
    marker_color="#0a6ed1"
))
fig.add_trace(go.Bar(
    name="Remaining Capacity", x=plant_bd["plant_id"], y=plant_bd["remaining"],
    marker_color="#d9d9d9"
))
fig.update_layout(barmode="stack", title="Plant Production Load Distribution",
                  yaxis_title="Units", margin=dict(t=40, b=20, l=20, r=20))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("4. Inventory Netting and Replenishment Analysis")
inv_pos = results["inventory_position"]

col1, col2 = st.columns(2)

with col1:
    fig = px.histogram(
        inv_pos, x="coverage_pct", nbins=20,
        title="Inventory Stock Coverage Ratio (%) Distribution",
        labels={"coverage_pct": "Coverage Ratio (%)"},
        color_discrete_sequence=["#107e3e"]
    )
    fig.add_vline(x=100, line_dash="dash", line_color="#bb0000",
                  annotation_text="100% Target Coverage")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    top_needs = inv_pos.nlargest(10, "net_requirement")
    fig = px.bar(
        top_needs, x="sku_id", y="net_requirement",
        color="category",
        title="Top 10 SKUs Requiring Replenishment Netting",
        labels={"net_requirement": "Net Required Units", "sku_id": "SKU Identifier"}
    )
    fig.update_layout(xaxis_tickangle=-45, margin=dict(t=40, b=80, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("5. Integrated Financial Rollup Waterfall")
fin = results["financial_summary"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Gross Projected Revenue", format_currency(fin["estimated_revenue"]))
col2.metric("Total Material Cost", format_currency(fin["estimated_material_cost"]))
col3.metric("Logistics Cost", format_currency(fin["estimated_logistics_cost"]))
col4.metric("Gross Profit Margin", format_pct(fin["gross_margin_pct"]))

fig = go.Figure(go.Waterfall(
    name="Financial Rollup",
    orientation="v",
    measure=["absolute", "relative", "relative", "total"],
    x=["Projected Revenue", "Material Costs", "Logistics Costs", "Gross Margin"],
    y=[fin["estimated_revenue"], -fin["estimated_material_cost"],
       -fin["estimated_logistics_cost"], fin["estimated_gross_margin"]],
    connector={"line": {"color": "#6a6d70"}},
    decreasing={"marker": {"color": "#bb0000"}},
    increasing={"marker": {"color": "#107e3e"}},
    totals={"marker": {"color": "#0a6ed1"}},
))
fig.update_layout(title="S&OP Profitability Waterfall Analysis", margin=dict(t=40, b=20, l=20, r=20))
st.plotly_chart(fig, use_container_width=True)
