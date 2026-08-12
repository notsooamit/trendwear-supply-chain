import pandas as pd
import numpy as np


def run_sop_cycle(data, period=None):
    """
    Run the S&OP reconciliation for a given period.

    Steps:
    1. Aggregate demand by SKU
    2. Explode through BOM to get material requirements
    3. Check plant capacity feasibility
    4. Compute net inventory position
    5. Build a financial rollup

    Returns dict with demand_summary, material_plan, capacity_check,
    inventory_position, and financial_summary.
    """
    demand = data["demand_forecast"].copy()
    if period:
        demand = demand[demand["period"] == period]

    if demand.empty:
        return {"error": "No demand data for selected period."}

    # Step 1: Demand aggregation by SKU and region
    demand_by_sku = (
        demand.groupby("sku_id")
        .agg(
            total_demand=("forecasted_demand_units", "sum"),
            avg_confidence=("confidence_interval_pct", "mean"),
            num_regions=("region", "nunique"),
        )
        .reset_index()
    )

    # Merge with SKU master for category/season info
    demand_by_sku = demand_by_sku.merge(
        data["skus"][["sku_id", "category", "season", "target_unit_price"]],
        on="sku_id", how="left"
    )

    demand_by_region = (
        demand.groupby(["region"])
        .agg(total_demand=("forecasted_demand_units", "sum"))
        .reset_index()
    )

    # Step 2: Material Requirements Planning (MRP)
    bom = data["bom"].copy()
    mrp = demand_by_sku[["sku_id", "total_demand"]].merge(bom, on="sku_id", how="inner")
    mrp["required_meters"] = mrp["total_demand"] * mrp["fabric_per_unit_meters"]

    material_plan = (
        mrp.groupby("fabric_id")
        .agg(
            total_required_meters=("required_meters", "sum"),
            num_skus=("sku_id", "nunique"),
        )
        .reset_index()
    )

    # Merge with fabric master
    material_plan = material_plan.merge(
        data["fabrics"][["fabric_id", "fabric_name", "standard_cost_per_meter", "standard_lead_time_days"]],
        on="fabric_id", how="left"
    )
    material_plan["estimated_material_cost"] = (
        material_plan["total_required_meters"] * material_plan["standard_cost_per_meter"]
    )

    # Step 3: Capacity feasibility
    capacity = data["plant_capacity"].copy()
    if period:
        capacity = capacity[capacity["period"] == period]

    total_demand_units = demand_by_sku["total_demand"].sum()
    total_max_capacity = capacity["max_units_capacity"].sum()
    total_allocated = capacity["allocated_units_capacity"].sum()
    remaining_capacity = total_max_capacity - total_allocated

    capacity_check = {
        "total_demand_units": int(total_demand_units),
        "total_max_capacity": int(total_max_capacity),
        "total_allocated_capacity": int(total_allocated),
        "remaining_capacity": int(remaining_capacity),
        "utilization_pct": round(total_allocated / total_max_capacity * 100, 1) if total_max_capacity > 0 else 0,
        "demand_vs_remaining": "Feasible" if total_demand_units <= remaining_capacity else "Over capacity",
        "gap_units": int(max(0, total_demand_units - remaining_capacity)),
    }

    # Per-plant breakdown
    plant_breakdown = (
        capacity.groupby("plant_id")
        .agg(
            max_capacity=("max_units_capacity", "sum"),
            allocated=("allocated_units_capacity", "sum"),
        )
        .reset_index()
    )
    plant_breakdown["remaining"] = plant_breakdown["max_capacity"] - plant_breakdown["allocated"]
    plant_breakdown["utilization_pct"] = round(
        plant_breakdown["allocated"] / plant_breakdown["max_capacity"] * 100, 1
    )

    # Step 4: Net inventory position
    inv = data["inventory"].copy()
    inv_by_sku = (
        inv.groupby("sku_id")
        .agg(
            total_available=("available_stock_units", "sum"),
            total_safety_stock=("safety_stock_threshold", "sum"),
        )
        .reset_index()
    )

    inventory_position = demand_by_sku[["sku_id", "total_demand", "category"]].merge(
        inv_by_sku, on="sku_id", how="left"
    )
    inventory_position["total_available"] = inventory_position["total_available"].fillna(0)
    inventory_position["total_safety_stock"] = inventory_position["total_safety_stock"].fillna(0)
    inventory_position["net_requirement"] = (
        inventory_position["total_demand"]
        - inventory_position["total_available"]
        + inventory_position["total_safety_stock"]
    )
    inventory_position["net_requirement"] = inventory_position["net_requirement"].clip(lower=0)
    inventory_position["coverage_pct"] = round(
        inventory_position["total_available"] / inventory_position["total_demand"] * 100, 1
    )

    # Step 5: Financial summary
    total_material_cost = material_plan["estimated_material_cost"].sum()
    total_revenue = (demand_by_sku["total_demand"] * demand_by_sku["target_unit_price"]).sum()

    # Estimate logistics cost
    avg_transport_cost = data["logistics"]["transportation_cost_per_unit"].mean()
    est_logistics_cost = total_demand_units * avg_transport_cost

    financial_summary = {
        "estimated_revenue": round(total_revenue, 2),
        "estimated_material_cost": round(total_material_cost, 2),
        "estimated_logistics_cost": round(est_logistics_cost, 2),
        "estimated_gross_margin": round(total_revenue - total_material_cost - est_logistics_cost, 2),
        "gross_margin_pct": round(
            (total_revenue - total_material_cost - est_logistics_cost) / total_revenue * 100, 1
        ) if total_revenue > 0 else 0,
    }

    return {
        "demand_summary": demand_by_sku,
        "demand_by_region": demand_by_region,
        "material_plan": material_plan,
        "capacity_check": capacity_check,
        "plant_breakdown": plant_breakdown,
        "inventory_position": inventory_position,
        "financial_summary": financial_summary,
    }


def get_available_periods(data):
    """Get sorted list of periods from demand forecast."""
    return sorted(data["demand_forecast"]["period"].unique().tolist())
