import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_loader import load_all_data
from core.sop_engine import run_sop_cycle, get_available_periods

st.set_page_config(page_title="Demand & Supply Planning", layout="wide")
st.title("Demand & Supply Planning (S&OP)")

data = load_all_data()
periods = get_available_periods(data)

# Sidebar controls
st.sidebar.header("S&OP Controls")
selected_period = st.sidebar.selectbox("Select Period", ["All Periods"] + periods)
period_filter = None if selected_period == "All Periods" else selected_period

# Run S&OP
results = run_sop_cycle(data, period=period_filter)

if "error" in results:
    st.error(results["error"])
    st.stop()

# Section 1: Demand Summary
st.subheader("Demand Summary")
col1, col2, col3 = st.columns(3)
demand_summary = results["demand_summary"]
col1.metric("Total Demand", f"{demand_summary['total_demand'].sum():,} units")
col2.metric("SKUs with Demand", len(demand_summary))
col3.metric("Avg Confidence", f"{demand_summary['avg_confidence'].mean():.1%}")

# Demand by category
col1, col2 = st.columns(2)
with col1:
    cat_demand = demand_summary.groupby("category")["total_demand"].sum().reset_index()
    fig = px.bar(cat_demand, x="category", y="total_demand",
                 labels={"total_demand": "Demand (units)", "category": "Category"},
                 title="Demand by Category", color="category")
    fig.update_layout(showlegend=False, margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

with col2:
    region_demand = results["demand_by_region"]
    fig = px.pie(region_demand, values="total_demand", names="region",
                 title="Demand by Region")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

st.markdown("---")

# Section 2: Material Requirements Plan
st.subheader("Material Requirements Plan (MRP)")
material_plan = results["material_plan"]

col1, col2 = st.columns(2)
col1.metric("Total Fabric Required", f"{material_plan['total_required_meters'].sum():,.0f} meters")
col2.metric("Estimated Material Cost", f"${material_plan['estimated_material_cost'].sum():,.0f}")

# Top fabrics by requirement
top_fabrics = material_plan.nlargest(15, "total_required_meters")
fig = px.bar(top_fabrics, x="fabric_name", y="total_required_meters",
             color="standard_lead_time_days",
             labels={"total_required_meters": "Required (meters)", "fabric_name": "Fabric",
                     "standard_lead_time_days": "Lead Time (days)"},
             title="Top 15 Fabrics by Requirement",
             color_continuous_scale="YlOrRd")
fig.update_layout(xaxis_tickangle=-45, margin=dict(t=40, b=80, l=20, r=20))
st.plotly_chart(fig, width='stretch')

with st.expander("Full Material Plan Table"):
    st.dataframe(
        material_plan[["fabric_id", "fabric_name", "total_required_meters",
                       "standard_cost_per_meter", "standard_lead_time_days",
                       "estimated_material_cost", "num_skus"]].sort_values(
            "total_required_meters", ascending=False
        ),
        width='stretch'
    )

st.markdown("---")

# Section 3: Capacity Check
st.subheader("Capacity Feasibility")
cap = results["capacity_check"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Demand", f"{cap['total_demand_units']:,}")
col2.metric("Remaining Capacity", f"{cap['remaining_capacity']:,}")
col3.metric("Utilization", f"{cap['utilization_pct']}%")

status_color = "green" if cap["demand_vs_remaining"] == "Feasible" else "red"
col4.metric("Status", cap["demand_vs_remaining"])
if cap["gap_units"] > 0:
    st.warning(f"Capacity gap: {cap['gap_units']:,} units need to be addressed.")

# Plant breakdown
plant_bd = results["plant_breakdown"]
fig = go.Figure()
fig.add_trace(go.Bar(name="Allocated", x=plant_bd["plant_id"], y=plant_bd["allocated"],
                     marker_color="#3498db"))
fig.add_trace(go.Bar(name="Remaining", x=plant_bd["plant_id"], y=plant_bd["remaining"],
                     marker_color="#95a5a6"))
fig.update_layout(barmode="stack", title="Plant Capacity Breakdown",
                  yaxis_title="Units", margin=dict(t=40, b=20, l=20, r=20))
st.plotly_chart(fig, width='stretch')

st.markdown("---")

# Section 4: Inventory Position
st.subheader("Net Inventory Position")
inv_pos = results["inventory_position"]

col1, col2 = st.columns(2)

with col1:
    # Coverage distribution
    fig = px.histogram(inv_pos, x="coverage_pct", nbins=20,
                       title="Inventory Coverage Distribution (%)",
                       labels={"coverage_pct": "Coverage %"})
    fig.add_vline(x=100, line_dash="dash", line_color="red",
                  annotation_text="100% coverage")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

with col2:
    # Top SKUs needing replenishment
    top_needs = inv_pos.nlargest(10, "net_requirement")
    fig = px.bar(top_needs, x="sku_id", y="net_requirement",
                 color="category",
                 title="Top 10 SKUs by Net Requirement",
                 labels={"net_requirement": "Net Requirement (units)", "sku_id": "SKU"})
    fig.update_layout(xaxis_tickangle=-45, margin=dict(t=40, b=80, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

st.markdown("---")

# Section 5: Financial Summary
st.subheader("Financial Summary")
fin = results["financial_summary"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Estimated Revenue", f"${fin['estimated_revenue']:,.0f}")
col2.metric("Material Cost", f"${fin['estimated_material_cost']:,.0f}")
col3.metric("Logistics Cost", f"${fin['estimated_logistics_cost']:,.0f}")
col4.metric("Gross Margin", f"{fin['gross_margin_pct']}%")

# Cost waterfall
fig = go.Figure(go.Waterfall(
    name="Financial Flow",
    orientation="v",
    measure=["absolute", "relative", "relative", "total"],
    x=["Revenue", "Material Cost", "Logistics Cost", "Gross Margin"],
    y=[fin["estimated_revenue"], -fin["estimated_material_cost"],
       -fin["estimated_logistics_cost"], fin["estimated_gross_margin"]],
    connector={"line": {"color": "rgb(63, 63, 63)"}},
    decreasing={"marker": {"color": "#e74c3c"}},
    increasing={"marker": {"color": "#27ae60"}},
    totals={"marker": {"color": "#3498db"}},
))
fig.update_layout(title="Cost Waterfall", margin=dict(t=40, b=20, l=20, r=20))
st.plotly_chart(fig, width='stretch')
