import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from core.data_loader import load_all_data, compute_avg_supplier_performance
from utils.formatters import format_currency, format_number, format_pct

st.set_page_config(page_title="Executive Dashboard", layout="wide")
st.title("Executive Control Tower Summary")
st.caption("High-level key performance indicators across procurement, S&OP, supplier risk, and inventory positions.")

data = load_all_data()

pos = data["purchase_orders"]
total_po_value = pos["total_po_value"].sum()
avg_delay = pos["delayed_days"].mean()
otd_rate = pos["is_on_time"].mean() * 100
high_risk_pct = (pos["risk_category"] == "High").mean() * 100

inv = data["inventory"]
total_stock = inv["available_stock_units"].sum()

st.subheader("Key Performance Indicators")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total PO Value", format_currency(total_po_value))
col2.metric("Avg Delay (Days)", f"{avg_delay:.1f}")
col3.metric("On-Time Delivery", format_pct(otd_rate))
col4.metric("High Risk PO Ratio", format_pct(high_risk_pct))
col5.metric("Available Stock", format_number(total_stock))

st.markdown("---")

# SAP Fiori Color Palette
SAP_COLORS = {"Low": "#107e3e", "Medium": "#e9730c", "High": "#bb0000"}

col1, col2 = st.columns(2)

with col1:
    st.subheader("Purchase Order Risk Classification")
    risk_counts = pos["risk_category"].value_counts().reset_index()
    risk_counts.columns = ["Risk Category", "Count"]
    fig = px.pie(
        risk_counts, values="Count", names="Risk Category",
        color="Risk Category",
        color_discrete_map=SAP_COLORS,
        hole=0.4
    )
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Supplier Performance Matrix")
    avg_perf = compute_avg_supplier_performance(data)
    avg_perf = avg_perf.merge(
        data["suppliers"][["supplier_id", "supplier_name"]], on="supplier_id"
    )
    fig = px.scatter(
        avg_perf, x="avg_otd", y="avg_quality",
        size="avg_defect_ppm", color="avg_risk_score",
        hover_name="supplier_name",
        labels={
            "avg_otd": "Avg OTD %",
            "avg_quality": "Avg Quality %",
            "avg_risk_score": "Risk Index"
        },
        color_continuous_scale="RdYlGn_r"
    )
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Demand Distribution by Product Category")
    demand = data["demand_forecast"].merge(data["skus"][["sku_id", "category"]], on="sku_id")
    cat_demand = demand.groupby("category")["forecasted_demand_units"].sum().reset_index()
    fig = px.bar(
        cat_demand, x="category", y="forecasted_demand_units",
        labels={"forecasted_demand_units": "Units Demand", "category": "Category"},
        color_discrete_sequence=["#0a6ed1"]
    )
    fig.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Manufacturing Plant Capacity Allocation")
    cap = data["plant_capacity"].copy()
    plant_util = cap.groupby("plant_id").agg(
        max_cap=("max_units_capacity", "sum"),
        alloc=("allocated_units_capacity", "sum"),
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Allocated Units", x=plant_util["plant_id"], y=plant_util["alloc"],
        marker_color="#0a6ed1"
    ))
    fig.add_trace(go.Bar(
        name="Available Buffer", x=plant_util["plant_id"],
        y=plant_util["max_cap"] - plant_util["alloc"],
        marker_color="#d9d9d9"
    ))
    fig.update_layout(barmode="stack", margin=dict(t=20, b=20, l=20, r=20), yaxis_title="Units")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("Inventory Stock-Out Alerts")
inv_check = inv.copy()
inv_check["below_safety"] = inv_check["available_stock_units"] < inv_check["safety_stock_threshold"]
alerts = inv_check[inv_check["below_safety"]]

col1, col2 = st.columns([1, 4])
with col1:
    st.metric("Critical Stock Alerts", len(alerts))

with col2:
    if not alerts.empty:
        st.dataframe(
            alerts[["inventory_id", "sku_id", "location_id", "available_stock_units",
                    "safety_stock_threshold"]].head(15),
            use_container_width=True
        )
    else:
        st.info("All inventory locations maintain adequate stock levels above safety thresholds.")
