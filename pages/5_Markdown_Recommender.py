import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_loader import load_all_data
from core.markdown_engine import analyze_sell_through

st.set_page_config(page_title="Markdown Recommender", layout="wide")
st.title("Markdown Recommender (P2)")

data = load_all_data()

# Run analysis
sku_metrics, recommendations, weekly_trends = analyze_sell_through(data)

# Section 1: SKU Classification Summary
st.subheader("SKU Classification Overview")
class_counts = sku_metrics["classification"].value_counts().reset_index()
class_counts.columns = ["Classification", "Count"]

col1, col2, col3, col4 = st.columns(4)
total = len(sku_metrics)
fast = len(sku_metrics[sku_metrics["classification"] == "Fast Mover"])
normal = len(sku_metrics[sku_metrics["classification"] == "Normal"])
slow = len(sku_metrics[sku_metrics["classification"] == "Slow Mover"])

col1.metric("Total SKUs", total)
col2.metric("Fast Movers", fast)
col3.metric("Normal", normal)
col4.metric("Slow Movers", slow)

col1, col2 = st.columns(2)

with col1:
    fig = px.pie(class_counts, values="Count", names="Classification",
                 color="Classification",
                 color_discrete_map={
                     "Fast Mover": "#27ae60",
                     "Normal": "#f39c12",
                     "Slow Mover": "#e74c3c"
                 },
                 title="SKU Classification Distribution")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

with col2:
    fig = px.scatter(sku_metrics, x="avg_sell_through_rate", y="weeks_of_stock",
                     color="classification",
                     hover_data=["sku_id", "category", "current_stock"],
                     color_discrete_map={
                         "Fast Mover": "#27ae60",
                         "Normal": "#f39c12",
                         "Slow Mover": "#e74c3c"
                     },
                     title="Sell-Through Rate vs Weeks of Stock",
                     labels={"avg_sell_through_rate": "Avg Sell-Through Rate",
                             "weeks_of_stock": "Weeks of Stock"})
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

st.markdown("---")

# Section 2: Weekly Trends
st.subheader("Weekly Sell-Through Trends")
fig = go.Figure()
fig.add_trace(go.Scatter(x=weekly_trends["selling_week"], y=weekly_trends["avg_st_rate"],
                         mode="lines+markers", name="Avg Sell-Through Rate",
                         line=dict(color="#3498db")))
fig.update_layout(xaxis_title="Week", yaxis_title="Avg Sell-Through Rate",
                  margin=dict(t=20, b=20, l=20, r=20))
st.plotly_chart(fig, width='stretch')

st.markdown("---")

# Section 3: Markdown Recommendations
st.subheader("Markdown Recommendations")
md_actions = recommendations["markdown_actions"]
stockout_alerts = recommendations["stockout_alerts"]

if not md_actions.empty:
    col1, col2 = st.columns(2)
    col1.metric("SKUs Needing Markdown", len(md_actions))
    col2.metric("Total Estimated Recovery",
                f"${md_actions['estimated_revenue_recovery'].sum():,.0f}")

    # Filter by urgency
    urgency_filter = st.multiselect("Filter by Urgency",
                                    ["High", "Medium", "Low"],
                                    default=["High", "Medium", "Low"])
    filtered = md_actions[md_actions["urgency"].isin(urgency_filter)]

    st.dataframe(
        filtered.sort_values("weeks_of_stock", ascending=False),
        width='stretch'
    )

    # Urgency distribution
    fig = px.histogram(filtered, x="urgency", color="urgency",
                       color_discrete_map={"High": "#e74c3c", "Medium": "#f39c12", "Low": "#27ae60"},
                       title="Markdown Urgency Distribution")
    fig.update_layout(showlegend=False, margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')
else:
    st.info("No markdown recommendations at this time. All SKUs are performing within acceptable ranges.")

st.markdown("---")

# Section 4: Stock-Out Alerts
st.subheader("Stock-Out Risk Alerts (Fast Movers)")
if not stockout_alerts.empty:
    st.warning(f"{len(stockout_alerts)} fast-moving SKUs are at risk of stock-out.")
    st.dataframe(stockout_alerts, width='stretch')
else:
    st.success("No immediate stock-out risks detected.")

st.markdown("---")

# Section 5: Historical Discount Effectiveness
st.subheader("Historical Discount Effectiveness")
disc_eff = recommendations["discount_effectiveness"]
if not disc_eff.empty:
    disc_eff["discount_label"] = (disc_eff["discount_percentage"] * 100).astype(int).astype(str) + "%"
    fig = px.bar(disc_eff, x="discount_label", y="clearance_ratio",
                 color="avg_units_sold",
                 labels={"discount_label": "Discount %", "clearance_ratio": "Clearance Ratio",
                         "avg_units_sold": "Avg Units Sold"},
                 title="Clearance Ratio by Discount Tier")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

# Section 6: Detailed SKU Table
with st.expander("Full SKU Performance Table"):
    display_cols = ["sku_id", "category", "season", "classification",
                    "avg_sell_through_rate", "avg_weekly_sales",
                    "current_stock", "weeks_of_stock", "target_unit_price"]
    st.dataframe(
        sku_metrics[display_cols].sort_values("avg_sell_through_rate"),
        width='stretch'
    )
