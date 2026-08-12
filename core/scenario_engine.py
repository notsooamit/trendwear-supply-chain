import pandas as pd
import numpy as np
from core.optimizer import build_and_solve
from core.sop_engine import run_sop_cycle


def run_supplier_disruption(data, excluded_supplier_id, period=None,
                            cost_weight=1.0, risk_weight=0.3,
                            lead_time_weight=0.1, quality_threshold=80.0):
    """
    Simulate removing a supplier and re-running procurement optimization.
    Returns baseline results, disrupted results, and the delta.
    """
    # Baseline (all suppliers)
    baseline = build_and_solve(
        data, period=period, cost_weight=cost_weight,
        risk_weight=risk_weight, lead_time_weight=lead_time_weight,
        quality_threshold=quality_threshold
    )

    # Disrupted (exclude one supplier)
    disrupted = build_and_solve(
        data, period=period, cost_weight=cost_weight,
        risk_weight=risk_weight, lead_time_weight=lead_time_weight,
        quality_threshold=quality_threshold,
        excluded_suppliers=[excluded_supplier_id]
    )

    delta = {}
    if baseline["status"] == "Optimal" and disrupted["status"] == "Optimal":
        bs = baseline["summary"]
        ds = disrupted["summary"]
        delta = {
            "cost_increase": round(ds["total_cost"] - bs["total_cost"], 2),
            "cost_increase_pct": round(
                (ds["total_cost"] - bs["total_cost"]) / bs["total_cost"] * 100, 2
            ) if bs["total_cost"] > 0 else 0,
            "risk_change": round(ds["weighted_avg_risk"] - bs["weighted_avg_risk"], 4),
            "lead_time_change": round(ds["weighted_avg_lead_time"] - bs["weighted_avg_lead_time"], 1),
            "suppliers_lost": bs["num_suppliers_used"] - ds["num_suppliers_used"],
        }

    return {
        "baseline": baseline,
        "disrupted": disrupted,
        "delta": delta,
        "excluded_supplier": excluded_supplier_id,
    }


def run_demand_spike(data, category, spike_pct, period=None):
    """
    Simulate a demand spike for a given category.
    Increases demand by spike_pct% and re-runs S&OP.
    Returns baseline and spiked results.
    """
    # Baseline S&OP
    baseline = run_sop_cycle(data, period=period)

    # Create modified data with spiked demand
    modified_data = {k: v.copy() if isinstance(v, pd.DataFrame) else v for k, v in data.items()}

    # Get SKUs in the target category
    target_skus = data["skus"][data["skus"]["category"] == category]["sku_id"].tolist()

    # Increase demand for those SKUs
    modified_demand = modified_data["demand_forecast"].copy()
    mask = modified_demand["sku_id"].isin(target_skus)
    modified_demand.loc[mask, "forecasted_demand_units"] = (
        modified_demand.loc[mask, "forecasted_demand_units"] * (1 + spike_pct / 100)
    ).astype(int)
    modified_data["demand_forecast"] = modified_demand

    # Re-run S&OP
    spiked = run_sop_cycle(modified_data, period=period)

    delta = {}
    if "error" not in baseline and "error" not in spiked:
        delta = {
            "demand_increase": (
                spiked["capacity_check"]["total_demand_units"]
                - baseline["capacity_check"]["total_demand_units"]
            ),
            "capacity_status_before": baseline["capacity_check"]["demand_vs_remaining"],
            "capacity_status_after": spiked["capacity_check"]["demand_vs_remaining"],
            "gap_increase": (
                spiked["capacity_check"]["gap_units"]
                - baseline["capacity_check"]["gap_units"]
            ),
            "material_cost_increase": round(
                spiked["financial_summary"]["estimated_material_cost"]
                - baseline["financial_summary"]["estimated_material_cost"], 2
            ),
        }

    return {
        "baseline": baseline,
        "spiked": spiked,
        "delta": delta,
        "category": category,
        "spike_pct": spike_pct,
    }


def run_lead_time_increase(data, supplier_id, additional_days, period=None):
    """
    Simulate increasing a supplier's lead time by additional_days.
    Shows impact on procurement optimization.
    """
    # Create modified data
    modified_data = {k: v.copy() if isinstance(v, pd.DataFrame) else v for k, v in data.items()}
    modified_contracts = modified_data["contracts"].copy()
    mask = modified_contracts["supplier_id"] == supplier_id
    modified_contracts.loc[mask, "contracted_lead_time_days"] += additional_days
    modified_data["contracts"] = modified_contracts

    # Run baseline optimization
    baseline = build_and_solve(data, period=period)

    # Run modified optimization
    modified = build_and_solve(modified_data, period=period)

    delta = {}
    if baseline["status"] == "Optimal" and modified["status"] == "Optimal":
        bs = baseline["summary"]
        ms = modified["summary"]
        delta = {
            "cost_change": round(ms["total_cost"] - bs["total_cost"], 2),
            "risk_change": round(ms["weighted_avg_risk"] - bs["weighted_avg_risk"], 4),
            "lead_time_change": round(ms["weighted_avg_lead_time"] - bs["weighted_avg_lead_time"], 1),
        }

    return {
        "baseline": baseline,
        "modified": modified,
        "delta": delta,
        "supplier_id": supplier_id,
        "additional_days": additional_days,
    }
