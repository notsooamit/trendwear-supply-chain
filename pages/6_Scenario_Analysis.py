import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_loader import load_all_data, get_supplier_names_map
from core.scenario_engine import run_supplier_disruption, run_demand_spike, run_lead_time_increase
from core.sop_engine import get_available_periods
from utils.constants import CATEGORIES

st.set_page_config(page_title="Scenario Analysis", layout="wide")
st.title("Scenario Analysis")

data = load_all_data()
sup_names = get_supplier_names_map()
periods = get_available_periods(data)

# Scenario selector
scenario_type = st.selectbox(
    "Select Scenario",
    ["Supplier Disruption", "Demand Spike", "Lead Time Increase"]
)

st.markdown("---")

if scenario_type == "Supplier Disruption":
    st.subheader("Supplier Disruption Scenario")
    st.markdown("Simulate removing a supplier from the procurement pool and see the cost/risk impact.")

    col1, col2 = st.columns(2)
    with col1:
        suppliers_list = sorted(data["suppliers"]["supplier_id"].tolist())
        selected_sup = st.selectbox(
            "Supplier to Remove",
            suppliers_list,
            format_func=lambda x: f"{x} - {sup_names.get(x, x)}"
        )
    with col2:
        selected_period = st.selectbox("Period", ["All Periods"] + periods, key="sd_period")
        period_filter = None if selected_period == "All Periods" else selected_period

    if st.button("Run Scenario", type="primary", key="sd_run"):
        with st.spinner("Running disruption scenario..."):
            result = run_supplier_disruption(data, selected_sup, period=period_filter)

        if result["baseline"]["status"] != "Optimal":
            st.error(f"Baseline optimization failed: {result['baseline']['status']}")
        elif result["disrupted"]["status"] != "Optimal":
            st.error(f"Cannot find a feasible solution without {sup_names.get(selected_sup, selected_sup)}. "
                     f"This supplier is critical for demand fulfillment.")
        else:
            delta = result["delta"]

            st.subheader("Impact Summary")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Cost Increase", f"${delta['cost_increase']:,.0f}",
                        delta=f"{delta['cost_increase_pct']:+.1f}%")
            col2.metric("Risk Change", f"{delta['risk_change']:+.4f}")
            col3.metric("Lead Time Change", f"{delta['lead_time_change']:+.1f} days")
            col4.metric("Suppliers Lost", delta["suppliers_lost"])

            # Before/After comparison
            col1, col2 = st.columns(2)
            bs = result["baseline"]["summary"]
            ds = result["disrupted"]["summary"]

            compare = pd.DataFrame({
                "Metric": ["Total Cost ($)", "Total Meters", "Suppliers Used",
                          "Avg Risk", "Avg Lead Time"],
                "Before": [bs["total_cost"], bs["total_meters"], bs["num_suppliers_used"],
                          bs["weighted_avg_risk"], bs["weighted_avg_lead_time"]],
                "After": [ds["total_cost"], ds["total_meters"], ds["num_suppliers_used"],
                         ds["weighted_avg_risk"], ds["weighted_avg_lead_time"]],
            })

            with col1:
                st.markdown("**Before vs After**")
                st.dataframe(compare, width='stretch')

            with col2:
                fig = go.Figure(data=[
                    go.Bar(name="Before", x=["Cost", "Meters"], y=[bs["total_cost"], bs["total_meters"]],
                           marker_color="#3498db"),
                    go.Bar(name="After", x=["Cost", "Meters"], y=[ds["total_cost"], ds["total_meters"]],
                           marker_color="#e74c3c"),
                ])
                fig.update_layout(barmode="group", title="Before vs After",
                                  margin=dict(t=40, b=20, l=20, r=20))
                st.plotly_chart(fig, width='stretch')

elif scenario_type == "Demand Spike":
    st.subheader("Demand Spike Scenario")
    st.markdown("Simulate increasing demand for a product category and check capacity/cost impact.")

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_cat = st.selectbox("Category", CATEGORIES)
    with col2:
        spike_pct = st.slider("Demand Increase (%)", 10, 200, 50, 10)
    with col3:
        selected_period = st.selectbox("Period", ["All Periods"] + periods, key="ds_period")
        period_filter = None if selected_period == "All Periods" else selected_period

    if st.button("Run Scenario", type="primary", key="ds_run"):
        with st.spinner("Running demand spike scenario..."):
            result = run_demand_spike(data, selected_cat, spike_pct, period=period_filter)

        if "error" in result.get("baseline", {}):
            st.error("S&OP cycle failed for baseline.")
        elif "error" in result.get("spiked", {}):
            st.error("S&OP cycle failed for spiked scenario.")
        else:
            delta = result["delta"]

            st.subheader("Impact Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Additional Demand", f"{delta['demand_increase']:,} units")
            col2.metric("Capacity Status", delta["capacity_status_after"],
                        delta=f"was: {delta['capacity_status_before']}")
            col3.metric("Material Cost Increase", f"${delta['material_cost_increase']:,.0f}")

            if delta["gap_increase"] > 0:
                st.warning(f"Capacity gap increased by {delta['gap_increase']:,} units.")

            # Compare capacity
            col1, col2 = st.columns(2)
            with col1:
                base_cap = result["baseline"]["capacity_check"]
                st.markdown("**Baseline Capacity**")
                st.json(base_cap)

            with col2:
                spike_cap = result["spiked"]["capacity_check"]
                st.markdown("**After Spike Capacity**")
                st.json(spike_cap)

elif scenario_type == "Lead Time Increase":
    st.subheader("Lead Time Increase Scenario")
    st.markdown("Simulate a supplier's lead time increasing (e.g., due to logistics disruptions).")

    col1, col2, col3 = st.columns(3)
    with col1:
        suppliers_list = sorted(data["suppliers"]["supplier_id"].tolist())
        selected_sup = st.selectbox(
            "Supplier",
            suppliers_list,
            format_func=lambda x: f"{x} - {sup_names.get(x, x)}",
            key="lt_sup"
        )
    with col2:
        additional_days = st.slider("Additional Lead Time (days)", 5, 30, 14, 1)
    with col3:
        selected_period = st.selectbox("Period", ["All Periods"] + periods, key="lt_period")
        period_filter = None if selected_period == "All Periods" else selected_period

    if st.button("Run Scenario", type="primary", key="lt_run"):
        with st.spinner("Running lead time scenario..."):
            result = run_lead_time_increase(data, selected_sup, additional_days, period=period_filter)

        if result["baseline"]["status"] != "Optimal":
            st.error(f"Baseline optimization failed: {result['baseline']['status']}")
        elif result["modified"]["status"] != "Optimal":
            st.error("Modified optimization failed. The lead time increase makes the problem infeasible.")
        else:
            delta = result["delta"]

            st.subheader("Impact Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Cost Change", f"${delta['cost_change']:,.0f}")
            col2.metric("Risk Change", f"{delta['risk_change']:+.4f}")
            col3.metric("Avg Lead Time Change", f"{delta['lead_time_change']:+.1f} days")

            # Utilization comparison
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Baseline Supplier Utilization**")
                base_util = result["baseline"].get("utilization", pd.DataFrame())
                if not base_util.empty:
                    base_util["supplier_name"] = base_util["supplier_id"].map(sup_names)
                    st.dataframe(base_util[["supplier_name", "utilization_pct"]],
                                 width='stretch')

            with col2:
                st.markdown("**Modified Supplier Utilization**")
                mod_util = result["modified"].get("utilization", pd.DataFrame())
                if not mod_util.empty:
                    mod_util["supplier_name"] = mod_util["supplier_id"].map(sup_names)
                    st.dataframe(mod_util[["supplier_name", "utilization_pct"]],
                                 width='stretch')
