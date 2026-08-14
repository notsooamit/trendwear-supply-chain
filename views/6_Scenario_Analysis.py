import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_loader import load_all_data, get_supplier_names_map
from core.scenario_engine import run_supplier_disruption, run_demand_spike, run_lead_time_increase
from core.sop_engine import get_available_periods
from utils.constants import CATEGORIES
from utils.formatters import format_currency, format_number, format_pct

st.set_page_config(page_title="Scenario Analysis", layout="wide")
st.title("What-If Scenario & Sensitivity Stress-Testing Engine")
st.caption("Simulating supply chain disruptions, demand surges, and lead-time shocks to quantify financial and operational impacts.")

data = load_all_data()
sup_names = get_supplier_names_map()
periods = get_available_periods(data)

scenario_type = st.selectbox(
    "Select Simulation Event Type",
    ["Supplier Disruption", "Demand Surge Spike", "Lead Time Extension"]
)

st.markdown("---")

if scenario_type == "Supplier Disruption":
    st.subheader("1. Supplier Disruption Simulation")
    st.caption("Simulates complete incapacity of a primary supplier and evaluates reallocation via MILP optimizer.")

    col1, col2 = st.columns(2)
    with col1:
        suppliers_list = sorted(data["suppliers"]["supplier_id"].tolist())
        selected_sup = st.selectbox(
            "Target Supplier to Deactivate",
            suppliers_list,
            format_func=lambda x: f"{x} - {sup_names.get(x, x)}"
        )
    with col2:
        selected_period = st.selectbox("Simulation Period", ["All Periods"] + periods, key="sd_period")
        period_filter = None if selected_period == "All Periods" else selected_period

    if st.button("Execute Disruption Simulation", type="primary", key="sd_run"):
        with st.spinner("Re-solving MILP optimization model under disruption constraints..."):
            result = run_supplier_disruption(data, selected_sup, period=period_filter)

        if result["baseline"]["status"] != "Optimal":
            st.error(f"Baseline solver failure: {result['baseline']['status']}")
        elif result["disrupted"]["status"] != "Optimal":
            st.error(f"Infeasible Solution: Capacity shortfall critical. No alternative supplier combination can satisfy demand without {sup_names.get(selected_sup, selected_sup)}.")
        else:
            delta = result["delta"]

            st.subheader("Impact Quantification Summary")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Landed Cost Increase", format_currency(delta["cost_increase"]),
                        delta=f"{delta['cost_increase_pct']:+.1f}%", delta_color="inverse")
            col2.metric("Weighted Risk Shift", f"{delta['risk_change']:+.4f}")
            col3.metric("Lead Time Delta", f"{delta['lead_time_change']:+.1f} days")
            col4.metric("Active Suppliers Lost", delta["suppliers_lost"])

            col1, col2 = st.columns(2)
            bs = result["baseline"]["summary"]
            ds = result["disrupted"]["summary"]

            compare = pd.DataFrame({
                "Operational Metric": ["Total Landed Cost", "Procured Meter Volume", "Active Suppliers",
                                       "Weighted Risk Score", "Mean Lead Time"],
                "Baseline State": [format_currency(bs["total_cost"]), format_number(bs["total_meters"]),
                                   bs["num_suppliers_used"], f"{bs['weighted_avg_risk']:.3f}", f"{bs['weighted_avg_lead_time']:.1f} d"],
                "Disrupted State": [format_currency(ds["total_cost"]), format_number(ds["total_meters"]),
                                    ds["num_suppliers_used"], f"{ds['weighted_avg_risk']:.3f}", f"{ds['weighted_avg_lead_time']:.1f} d"],
            })

            with col1:
                st.markdown("**Baseline vs Disrupted Operational Metrics**")
                st.dataframe(compare, use_container_width=True)

            with col2:
                fig = go.Figure(data=[
                    go.Bar(name="Baseline", x=["Total Cost ($)", "Volume (m)"],
                           y=[bs["total_cost"], bs["total_meters"]], marker_color="#0a6ed1"),
                    go.Bar(name="Disrupted", x=["Total Cost ($)", "Volume (m)"],
                           y=[ds["total_cost"], ds["total_meters"]], marker_color="#bb0000"),
                ])
                fig.update_layout(barmode="group", title="Total Expenditure and Volume Comparison",
                                  margin=dict(t=40, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)

elif scenario_type == "Demand Surge Spike":
    st.subheader("2. Demand Surge Simulation")
    st.caption("Simulates an unexpected surge in SKU demand for a specific product category.")

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_cat = st.selectbox("Product Category", CATEGORIES)
    with col2:
        spike_pct = st.slider("Demand Volume Surge (%)", 10, 200, 50, 10)
    with col3:
        selected_period = st.selectbox("Simulation Period", ["All Periods"] + periods, key="ds_period")
        period_filter = None if selected_period == "All Periods" else selected_period

    if st.button("Execute Surge Simulation", type="primary", key="ds_run"):
        with st.spinner("Re-evaluating S&OP MRP explosion and capacity limits..."):
            result = run_demand_spike(data, selected_cat, spike_pct, period=period_filter)

        if "error" in result.get("baseline", {}):
            st.error("S&OP baseline cycle evaluation failed.")
        elif "error" in result.get("spiked", {}):
            st.error("S&OP spiked cycle evaluation failed.")
        else:
            delta = result["delta"]

            st.subheader("Impact Quantification Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Incremental Demand Volume", f"{format_number(delta['demand_increase'])} units")
            col2.metric("Post-Surge Capacity Feasibility", delta["capacity_status_after"])
            col3.metric("Incremental Material Expenditure", format_currency(delta["material_cost_increase"]))

            if delta["gap_increase"] > 0:
                st.warning(f"Capacity Bottleneck: Manufacturing shortfall increased by {format_number(delta['gap_increase'])} units.")

elif scenario_type == "Lead Time Extension":
    st.subheader("3. Supplier Lead Time Extension Simulation")
    st.caption("Simulates logistics delays or port congestion by extending supplier lead times.")

    col1, col2, col3 = st.columns(3)
    with col1:
        suppliers_list = sorted(data["suppliers"]["supplier_id"].tolist())
        selected_sup = st.selectbox(
            "Target Supplier Entity",
            suppliers_list,
            format_func=lambda x: f"{x} - {sup_names.get(x, x)}",
            key="lt_sup"
        )
    with col2:
        additional_days = st.slider("Additional Lead Time Delay (Days)", 5, 30, 14, 1)
    with col3:
        selected_period = st.selectbox("Simulation Period", ["All Periods"] + periods, key="lt_period")
        period_filter = None if selected_period == "All Periods" else selected_period

    if st.button("Execute Lead Time Simulation", type="primary", key="lt_run"):
        with st.spinner("Re-solving MILP optimization model under updated lead times..."):
            result = run_lead_time_increase(data, selected_sup, additional_days, period=period_filter)

        if result["baseline"]["status"] != "Optimal":
            st.error(f"Baseline solver failure: {result['baseline']['status']}")
        elif result["modified"]["status"] != "Optimal":
            st.error("Modified optimization failed due to lead-time infeasibility constraints.")
        else:
            delta = result["delta"]

            st.subheader("Impact Quantification Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Landed Cost Shift", format_currency(delta["cost_change"]))
            col2.metric("Weighted Risk Shift", f"{delta['risk_change']:+.4f}")
            col3.metric("Mean System Lead Time Shift", f"{delta['lead_time_change']:+.1f} days")
