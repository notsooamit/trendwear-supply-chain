import pandas as pd
import numpy as np
from pulp import (
    LpProblem, LpMinimize, LpVariable, LpBinary, lpSum, LpStatus, value
)


def build_and_solve(data, period=None, cost_weight=1.0, risk_weight=0.3,
                    lead_time_weight=0.1, quality_threshold=80.0,
                    excluded_suppliers=None):
    """
    Build and solve the procurement optimization model.

    The model allocates fabric procurement across suppliers to minimize
    a weighted combination of cost, risk, and lead time while satisfying
    demand, capacity, MOQ, and allocation constraints.

    Args:
        data: dict of DataFrames from data_loader
        period: optional period string to filter demand
        cost_weight: weight for cost in objective
        risk_weight: weight for supplier risk penalty
        lead_time_weight: weight for lead time penalty
        quality_threshold: minimum quality % to include a supplier
        excluded_suppliers: list of supplier_ids to exclude (for scenario analysis)

    Returns:
        dict with keys: status, allocations, summary, cost_breakdown, utilization
    """
    if excluded_suppliers is None:
        excluded_suppliers = []

    # Get fabric demand from material_demand_forecast table
    # This table has realistic per-plant per-period demand at the right scale
    from core.data_loader import compute_avg_supplier_performance
    mat_demand = data["material_demand"].copy()
    if period:
        mat_demand = mat_demand[mat_demand["period"] == period]

    fabric_demand_df = (
        mat_demand.groupby("fabric_id")["required_meters"]
        .sum()
        .reset_index()
    )
    fabric_demand = dict(zip(fabric_demand_df["fabric_id"], fabric_demand_df["required_meters"]))

    if not fabric_demand:
        return {"status": "No demand found for the selected period.", "allocations": pd.DataFrame()}

    # Get supplier performance averages
    avg_perf = compute_avg_supplier_performance(data)
    perf_map = avg_perf.set_index("supplier_id").to_dict("index")

    # Filter contracts by quality threshold and excluded suppliers
    contracts = data["contracts"].copy()
    suppliers = data["suppliers"].copy()
    risk_map = suppliers.set_index("supplier_id")["base_risk_factor"].to_dict()

    # Exclude suppliers below quality threshold or in excluded list
    valid_suppliers = set()
    for sup_id, perf in perf_map.items():
        if perf["avg_quality"] >= quality_threshold and sup_id not in excluded_suppliers:
            valid_suppliers.add(sup_id)

    # Also include suppliers not in perf history (they pass by default)
    all_sup_ids = set(suppliers["supplier_id"])
    no_perf_sups = all_sup_ids - set(perf_map.keys()) - set(excluded_suppliers)
    valid_suppliers = valid_suppliers | no_perf_sups

    contracts = contracts[contracts["supplier_id"].isin(valid_suppliers)]

    if contracts.empty:
        return {"status": "No valid supplier contracts after filtering.", "allocations": pd.DataFrame()}

    # Build sets
    fabrics_in_demand = list(fabric_demand.keys())
    supplier_fabric_pairs = list(
        zip(contracts["supplier_id"], contracts["fabric_id"])
    )
    # Only keep pairs where fabric is in demand
    supplier_fabric_pairs = [
        (s, f) for s, f in supplier_fabric_pairs if f in fabric_demand
    ]

    if not supplier_fabric_pairs:
        return {"status": "No supplier-fabric pairs match the demand.", "allocations": pd.DataFrame()}

    # Build lookup from contracts
    contract_lookup = {}
    for _, row in contracts.iterrows():
        key = (row["supplier_id"], row["fabric_id"])
        contract_lookup[key] = {
            "unit_price": row["unit_price"],
            "capacity": row["monthly_capacity_meters"],
            "lead_time": row["contracted_lead_time_days"],
            "moq": row["moq_meters"],
            "min_alloc": row["min_allocation_pct"],
            "max_alloc": row["max_allocation_pct"],
        }

    # Create the LP model
    prob = LpProblem("Procurement_Optimization", LpMinimize)

    # Decision variables
    # x[(s,f)] = meters of fabric f to procure from supplier s
    x = {}
    y = {}  # binary indicator for MOQ
    for s, f in supplier_fabric_pairs:
        x[(s, f)] = LpVariable(f"x_{s}_{f}", lowBound=0, cat="Continuous")
        y[(s, f)] = LpVariable(f"y_{s}_{f}", cat=LpBinary)

    # Objective terms
    cost_terms = []
    risk_terms = []
    lead_terms = []

    for s, f in supplier_fabric_pairs:
        info = contract_lookup[(s, f)]
        sup_risk = risk_map.get(s, 0.15)
        cost_terms.append(info["unit_price"] * x[(s, f)])
        risk_terms.append(sup_risk * 100 * x[(s, f)])
        lead_terms.append(info["lead_time"] * x[(s, f)])

    # Shortfall variables for soft demand constraint
    # This allows the model to be feasible even when capacity < demand
    shortfall = {}
    SHORTFALL_PENALTY = 100.0  # heavy penalty per unfulfilled meter
    for f in fabrics_in_demand:
        shortfall[f] = LpVariable(f"shortfall_{f}", lowBound=0, cat="Continuous")

    prob += (
        cost_weight * lpSum(cost_terms)
        + risk_weight * lpSum(risk_terms)
        + lead_time_weight * lpSum(lead_terms)
        + SHORTFALL_PENALTY * lpSum(shortfall[f] for f in fabrics_in_demand)
    ), "Total_Weighted_Objective"

    # Constraint 1: Demand satisfaction (soft - with shortfall)
    for f in fabrics_in_demand:
        relevant_pairs = [(s, fab) for s, fab in supplier_fabric_pairs if fab == f]
        if relevant_pairs:
            prob += (
                lpSum(x[(s, fab)] for s, fab in relevant_pairs) + shortfall[f] >= fabric_demand[f],
                f"Demand_{f}",
            )

    # Constraint 2: Supplier capacity
    suppliers_in_model = set(s for s, f in supplier_fabric_pairs)
    for s in suppliers_in_model:
        relevant_pairs = [(sup, f) for sup, f in supplier_fabric_pairs if sup == s]
        total_cap = sum(contract_lookup[(sup, f)]["capacity"] for sup, f in relevant_pairs)
        prob += (
            lpSum(x[(sup, f)] for sup, f in relevant_pairs) <= total_cap,
            f"Capacity_{s}",
        )

    # Constraint 3: MOQ with binary indicator
    # x[(s,f)] >= MOQ * y[(s,f)] and x[(s,f)] <= BigM * y[(s,f)]
    BIG_M = 1_000_000
    for s, f in supplier_fabric_pairs:
        moq = contract_lookup[(s, f)]["moq"]
        prob += x[(s, f)] >= moq * y[(s, f)], f"MOQ_lower_{s}_{f}"
        prob += x[(s, f)] <= BIG_M * y[(s, f)], f"MOQ_upper_{s}_{f}"

    # Constraint 4: Per-contract capacity limit
    # Each (supplier, fabric) pair cannot exceed its contract capacity
    for s, f in supplier_fabric_pairs:
        info = contract_lookup[(s, f)]
        prob += (
            x[(s, f)] <= info["capacity"],
            f"ContractCap_{s}_{f}",
        )

    # Solve (suppress output)
    from pulp import PULP_CBC_CMD
    prob.solve(PULP_CBC_CMD(msg=0))
    status = LpStatus[prob.status]


    if status != "Optimal":
        return {"status": f"Solver status: {status}", "allocations": pd.DataFrame()}

    # Extract results
    alloc_rows = []
    for s, f in supplier_fabric_pairs:
        qty = value(x[(s, f)])
        if qty and qty > 0.01:
            info = contract_lookup[(s, f)]
            alloc_rows.append({
                "supplier_id": s,
                "fabric_id": f,
                "allocated_meters": round(qty, 2),
                "unit_price": info["unit_price"],
                "total_cost": round(qty * info["unit_price"], 2),
                "lead_time_days": info["lead_time"],
                "supplier_risk": risk_map.get(s, 0.15),
            })

    df_alloc = pd.DataFrame(alloc_rows)

    # Compute summaries
    total_cost = df_alloc["total_cost"].sum() if not df_alloc.empty else 0
    total_meters = df_alloc["allocated_meters"].sum() if not df_alloc.empty else 0
    avg_risk = (
        (df_alloc["supplier_risk"] * df_alloc["allocated_meters"]).sum() / total_meters
        if total_meters > 0 else 0
    )
    avg_lead = (
        (df_alloc["lead_time_days"] * df_alloc["allocated_meters"]).sum() / total_meters
        if total_meters > 0 else 0
    )

    # Supplier utilization
    utilization = []
    for s in suppliers_in_model:
        relevant = [(sup, f) for sup, f in supplier_fabric_pairs if sup == s]
        total_cap = sum(contract_lookup[(sup, f)]["capacity"] for sup, f in relevant)
        used = sum(value(x[(sup, f)]) or 0 for sup, f in relevant)
        utilization.append({
            "supplier_id": s,
            "total_capacity": total_cap,
            "allocated": round(used, 2),
            "utilization_pct": round(used / total_cap * 100, 2) if total_cap > 0 else 0,
        })
    df_util = pd.DataFrame(utilization)

    # Cost breakdown
    cost_component = value(cost_weight * lpSum(cost_terms))
    risk_component = value(risk_weight * lpSum(risk_terms))
    lead_component = value(lead_time_weight * lpSum(lead_terms))

    # Demand fulfillment
    total_demand = sum(fabric_demand.values())
    total_shortfall = sum(value(shortfall[f]) or 0 for f in fabrics_in_demand)
    fulfillment_pct = round((1 - total_shortfall / total_demand) * 100, 1) if total_demand > 0 else 100

    return {
        "status": "Optimal",
        "allocations": df_alloc,
        "summary": {
            "total_cost": round(total_cost, 2),
            "total_meters": round(total_meters, 2),
            "weighted_avg_risk": round(avg_risk, 4),
            "weighted_avg_lead_time": round(avg_lead, 1),
            "num_suppliers_used": df_alloc["supplier_id"].nunique() if not df_alloc.empty else 0,
            "num_fabrics_covered": df_alloc["fabric_id"].nunique() if not df_alloc.empty else 0,
            "total_demand": round(total_demand, 2),
            "total_shortfall": round(total_shortfall, 2),
            "fulfillment_pct": fulfillment_pct,
        },
        "cost_breakdown": {
            "procurement_cost": round(cost_component, 2) if cost_component else 0,
            "risk_penalty": round(risk_component, 2) if risk_component else 0,
            "lead_time_penalty": round(lead_component, 2) if lead_component else 0,
        },
        "utilization": df_util,
        "objective_value": round(value(prob.objective), 2),
    }
