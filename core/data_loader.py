import pandas as pd
import streamlit as st
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hackathon_dataset")
SHARED_DIR = os.path.join(DATA_DIR, "shared")
PR1_DIR = os.path.join(DATA_DIR, "pr1_procurement")
P2_DIR = os.path.join(DATA_DIR, "p2_sop")


@st.cache_data
def load_all_data():
    """Load all 16 CSVs and return them as a dictionary of DataFrames."""
    data = {}

    files = {
        # Shared master tables
        "suppliers": os.path.join(SHARED_DIR, "supplier_master.csv"),
        "fabrics": os.path.join(SHARED_DIR, "fabric_master.csv"),
        "skus": os.path.join(SHARED_DIR, "sku_master.csv"),
        "plants": os.path.join(SHARED_DIR, "plant_master.csv"),
        "bom": os.path.join(SHARED_DIR, "bom_material.csv"),
        # PR1 - Procurement
        "contracts": os.path.join(PR1_DIR, "supplier_material_contracts.csv"),
        "material_demand": os.path.join(PR1_DIR, "material_demand_forecast.csv"),
        "supplier_perf": os.path.join(PR1_DIR, "supplier_performance_history.csv"),
        "purchase_orders": os.path.join(PR1_DIR, "historical_purchase_orders.csv"),
        # P2 - S&OP Planning
        "demand_forecast": os.path.join(P2_DIR, "seasonal_sku_demand.csv"),
        "inventory": os.path.join(P2_DIR, "current_inventory.csv"),
        "fabric_constraints": os.path.join(P2_DIR, "fabric_constraints.csv"),
        "plant_capacity": os.path.join(P2_DIR, "plant_production_capacity.csv"),
        "sell_through": os.path.join(P2_DIR, "historical_sell_through.csv"),
        "markdowns": os.path.join(P2_DIR, "historical_markdowns.csv"),
        "logistics": os.path.join(P2_DIR, "dc_to_store_logistics.csv"),
    }

    for key, filepath in files.items():
        data[key] = pd.read_csv(filepath)

    # Parse date columns
    date_cols = {
        "skus": ["launch_date"],
        "purchase_orders": ["order_date", "promised_delivery_date", "actual_delivery_date"],
    }
    for key, cols in date_cols.items():
        for col in cols:
            data[key][col] = pd.to_datetime(data[key][col])

    return data


@st.cache_data
def get_supplier_risk_map():
    """Build supplier_id -> base_risk_factor lookup."""
    data = load_all_data()
    return data["suppliers"].set_index("supplier_id")["base_risk_factor"].to_dict()


@st.cache_data
def get_fabric_cost_map():
    """Build fabric_id -> standard_cost_per_meter lookup."""
    data = load_all_data()
    return data["fabrics"].set_index("fabric_id")["standard_cost_per_meter"].to_dict()


@st.cache_data
def get_supplier_names_map():
    """Build supplier_id -> supplier_name lookup."""
    data = load_all_data()
    return data["suppliers"].set_index("supplier_id")["supplier_name"].to_dict()


@st.cache_data
def get_fabric_names_map():
    """Build fabric_id -> fabric_name lookup."""
    data = load_all_data()
    return data["fabrics"].set_index("fabric_id")["fabric_name"].to_dict()


@st.cache_data
def get_sku_details_map():
    """Build sku_id -> dict of details lookup."""
    data = load_all_data()
    return data["skus"].set_index("sku_id").to_dict("index")


def compute_material_requirements(data, period=None):
    """
    Given demand forecast and BOM, compute total fabric requirements.
    If period is specified, filter demand to that period.
    Returns a DataFrame with fabric_id and total_required_meters.
    """
    demand = data["demand_forecast"].copy()
    if period:
        demand = demand[demand["period"] == period]

    # Aggregate demand by SKU
    sku_demand = demand.groupby("sku_id")["forecasted_demand_units"].sum().reset_index()

    # Join with BOM to get fabric requirements per unit
    merged = sku_demand.merge(data["bom"], on="sku_id", how="inner")
    merged["total_fabric_meters"] = (
        merged["forecasted_demand_units"] * merged["fabric_per_unit_meters"]
    )

    # Aggregate by fabric
    fabric_req = (
        merged.groupby("fabric_id")["total_fabric_meters"]
        .sum()
        .reset_index()
        .rename(columns={"total_fabric_meters": "required_meters"})
    )
    return fabric_req


def compute_avg_supplier_performance(data):
    """
    Compute average OTD and quality scores per supplier from performance history.
    """
    perf = data["supplier_perf"]
    avg_perf = (
        perf.groupby("supplier_id")
        .agg(
            avg_otd=("otd_rating_pct", "mean"),
            avg_quality=("quality_pass_rate_pct", "mean"),
            avg_defect_ppm=("defect_ppm", "mean"),
            avg_risk_score=("overall_risk_score", "mean"),
        )
        .reset_index()
    )
    return avg_perf
