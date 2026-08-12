import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from core.data_loader import load_all_data, compute_avg_supplier_performance

st.set_page_config(page_title="Executive Dashboard", layout="wide")
st.title("Executive Dashboard")

data = load_all_data()

# KPI Row 1: High level numbers
st.subheader("Key Metrics")
col1, col2, col3, col4, col5 = st.columns(5)

pos = data["purchase_orders"]
total_po_value = pos["total_po_value"].sum()
avg_delay = pos["delayed_days"].mean()
otd_rate = pos["is_on_time"].mean() * 100
high_risk_pct = (pos["risk_category"] == "High").mean() * 100

inv = data["inventory"]
total_stock = inv["available_stock_units"].sum()

col1.metric("Total PO Value", f"${total_po_value:,.0f}")
col2.metric("Avg Delay (days)", f"{avg_delay:.1f}")
col3.metric("On-Time Delivery", f"{otd_rate:.1f}%")
col4.metric("High Risk POs", f"{high_risk_pct:.1f}%")
col5.metric("Available Stock", f"{total_stock:,}")

st.markdown("---")

# Row 2: Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Risk Distribution (Purchase Orders)")
    risk_counts = pos["risk_category"].value_counts().reset_index()
    risk_counts.columns = ["Risk Category", "Count"]
    fig = px.pie(risk_counts, values="Count", names="Risk Category",
                 color="Risk Category",
                 color_discrete_map={"Low": "#27ae60", "Medium": "#f39c12", "High": "#e74c3c"})
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

with col2:
    st.subheader("Supplier Performance Overview")
    avg_perf = compute_avg_supplier_performance(data)
    avg_perf = avg_perf.merge(
        data["suppliers"][["supplier_id", "supplier_name"]], on="supplier_id"
    )
    fig = px.scatter(avg_perf, x="avg_otd", y="avg_quality",
                     size="avg_defect_ppm", color="avg_risk_score",
                     hover_name="supplier_name",
                     labels={"avg_otd": "Avg OTD %", "avg_quality": "Avg Quality %",
                             "avg_risk_score": "Risk Score"},
                     color_continuous_scale="RdYlGn_r")
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

# Row 3: Demand and Capacity
col1, col2 = st.columns(2)

with col1:
    st.subheader("Demand by Category")
    demand = data["demand_forecast"].merge(data["skus"][["sku_id", "category"]], on="sku_id")
    cat_demand = demand.groupby("category")["forecasted_demand_units"].sum().reset_index()
    fig = px.bar(cat_demand, x="category", y="forecasted_demand_units",
                 labels={"forecasted_demand_units": "Total Demand (units)", "category": "Category"},
                 color="category")
    fig.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

with col2:
    st.subheader("Plant Capacity Utilization")
    cap = data["plant_capacity"].copy()
    plant_util = cap.groupby("plant_id").agg(
        max_cap=("max_units_capacity", "sum"),
        alloc=("allocated_units_capacity", "sum"),
    ).reset_index()
    plant_util["utilization"] = round(plant_util["alloc"] / plant_util["max_cap"] * 100, 1)

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Allocated", x=plant_util["plant_id"], y=plant_util["alloc"],
                         marker_color="#3498db"))
    fig.add_trace(go.Bar(name="Remaining", x=plant_util["plant_id"],
                         y=plant_util["max_cap"] - plant_util["alloc"],
                         marker_color="#bdc3c7"))
    fig.update_layout(barmode="stack", margin=dict(t=20, b=20, l=20, r=20),
                      yaxis_title="Units")
    st.plotly_chart(fig, width='stretch')

# Row 4: Inventory alerts
st.subheader("Inventory Alerts")
inv_check = inv.copy()
inv_check["below_safety"] = inv_check["available_stock_units"] < inv_check["safety_stock_threshold"]
alerts = inv_check[inv_check["below_safety"]]
st.metric("SKUs Below Safety Stock", len(alerts))
if not alerts.empty:
    st.dataframe(
        alerts[["inventory_id", "sku_id", "location_id", "available_stock_units",
                "safety_stock_threshold"]].head(20),
        width='stretch'
    )
else:
    st.info("No inventory items below safety stock threshold.")
