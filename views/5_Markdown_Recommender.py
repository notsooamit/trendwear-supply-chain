import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_loader import load_all_data
from core.markdown_engine import analyze_sell_through
from utils.formatters import format_currency, format_number, format_pct

st.set_page_config(page_title="Markdown Recommender", layout="wide")
st.title("In-Season Markdown & Sell-Through Optimization")
st.caption("Analyzing weekly sell-through velocity to classify SKUs, optimize markdown schedules, and mitigate inventory obsolescence.")

data = load_all_data()

sku_metrics, recommendations, weekly_trends = analyze_sell_through(data)

st.subheader("1. Inventory Velocity Classification")
class_counts = sku_metrics["classification"].value_counts().reset_index()
class_counts.columns = ["Classification", "Count"]

col1, col2, col3, col4 = st.columns(4)
total = len(sku_metrics)
fast = len(sku_metrics[sku_metrics["classification"] == "Fast Mover"])
normal = len(sku_metrics[sku_metrics["classification"] == "Normal"])
slow = len(sku_metrics[sku_metrics["classification"] == "Slow Mover"])

col1.metric("Total Active SKUs", total)
col2.metric("Fast Movers", fast)
col3.metric("Normal Velocity", normal)
col4.metric("Slow Movers", slow)

col1, col2 = st.columns(2)

with col1:
    fig = px.pie(
        class_counts, values="Count", names="Classification",
        color="Classification",
        color_discrete_map={
            "Fast Mover": "#107e3e",
            "Normal": "#e9730c",
            "Slow Mover": "#bb0000"
        },
        title="SKU Inventory Velocity Distribution"
    )
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.scatter(
        sku_metrics, x="avg_sell_through_rate", y="weeks_of_stock",
        color="classification",
        hover_data=["sku_id", "category", "current_stock"],
        color_discrete_map={
            "Fast Mover": "#107e3e",
            "Normal": "#e9730c",
            "Slow Mover": "#bb0000"
        },
        title="Sell-Through Rate vs Weeks of Stock On Hand",
        labels={"avg_sell_through_rate": "Avg Sell-Through Rate Ratio", "weeks_of_stock": "Weeks of Stock"}
    )
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("2. Weekly Sell-Through Velocity Trend")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=weekly_trends["selling_week"], y=weekly_trends["avg_st_rate"],
    mode="lines+markers", name="Mean Sell-Through Ratio",
    line=dict(color="#0a6ed1", width=2)
))
fig.update_layout(xaxis_title="Selling Week", yaxis_title="Mean Sell-Through Ratio",
                  margin=dict(t=20, b=20, l=20, r=20))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("3. Recommended Markdown Actions")
md_actions = recommendations["markdown_actions"]
stockout_alerts = recommendations["stockout_alerts"]

if not md_actions.empty:
    col1, col2 = st.columns(2)
    col1.metric("SKUs Requiring Price Adjustments", len(md_actions))
    col2.metric("Projected Working Capital Recovery", format_currency(md_actions["estimated_revenue_recovery"].sum()))

    urgency_filter = st.multiselect(
        "Filter Action Priority",
        ["High", "Medium", "Low"],
        default=["High", "Medium", "Low"]
    )
    filtered = md_actions[md_actions["urgency"].isin(urgency_filter)]

    st.dataframe(
        filtered.sort_values("weeks_of_stock", ascending=False),
        use_container_width=True
    )

    fig = px.histogram(
        filtered, x="urgency", color="urgency",
        color_discrete_map={"High": "#bb0000", "Medium": "#e9730c", "Low": "#107e3e"},
        title="Markdown Action Urgency Profile"
    )
    fig.update_layout(showlegend=False, margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No immediate markdown triggers identified. Inventory velocity across active SKUs meets operational targets.")

st.markdown("---")

st.subheader("4. Stock-Out Vulnerability Alerts (Fast Movers)")
if not stockout_alerts.empty:
    st.warning(f"Stock-Out Warning: {len(stockout_alerts)} high-velocity SKUs maintain less than 3 weeks of available inventory buffer.")
    st.dataframe(stockout_alerts, use_container_width=True)
else:
    st.success("Zero stock-out risks detected for fast-moving inventory items.")

st.markdown("---")

st.subheader("5. Historical Discount Elasticity & Clearance Efficiency")
disc_eff = recommendations["discount_effectiveness"]
if not disc_eff.empty:
    # Fix: discount_percentage is already integer 15, 25, 35, 50
    disc_eff["discount_label"] = disc_eff["discount_percentage"].astype(int).astype(str) + "%"
    fig = px.bar(
        disc_eff, x="discount_label", y="clearance_ratio",
        color="avg_units_sold",
        labels={
            "discount_label": "Discount Tier",
            "clearance_ratio": "Clearance Ratio",
            "avg_units_sold": "Mean Units Sold"
        },
        title="Inventory Clearance Ratio by Discount Depth",
        color_continuous_scale="Blues"
    )
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with st.expander("Full SKU Inventory Performance Table"):
    display_cols = ["sku_id", "category", "season", "classification",
                    "avg_sell_through_rate", "avg_weekly_sales",
                    "current_stock", "weeks_of_stock", "target_unit_price"]
    st.dataframe(
        sku_metrics[display_cols].sort_values("avg_sell_through_rate"),
        use_container_width=True
    )
