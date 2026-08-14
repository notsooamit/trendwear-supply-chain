"""
Deep Data Quality Audit for TrendWear Hackathon Dataset
Checks: referential integrity, distributions, logical consistency, coverage
"""
import pandas as pd
import numpy as np
import os

BASE = "./hackathon_dataset"
S = f"{BASE}/shared"
PR1 = f"{BASE}/pr1_procurement"
P2 = f"{BASE}/p2_sop"

# Load all datasets
print("=" * 70)
print("TRENDWEAR DATA QUALITY AUDIT")
print("=" * 70)

suppliers = pd.read_csv(f"{S}/supplier_master.csv")
fabrics = pd.read_csv(f"{S}/fabric_master.csv")
skus = pd.read_csv(f"{S}/sku_master.csv")
plants = pd.read_csv(f"{S}/plant_master.csv")
bom = pd.read_csv(f"{S}/bom_material.csv")

contracts = pd.read_csv(f"{PR1}/supplier_material_contracts.csv")
mat_demand = pd.read_csv(f"{PR1}/material_demand_forecast.csv")
sup_perf = pd.read_csv(f"{PR1}/supplier_performance_history.csv")
pos = pd.read_csv(f"{PR1}/historical_purchase_orders.csv")

demand = pd.read_csv(f"{P2}/seasonal_sku_demand.csv")
inventory = pd.read_csv(f"{P2}/current_inventory.csv")
fab_constraints = pd.read_csv(f"{P2}/fabric_constraints.csv")
plant_cap = pd.read_csv(f"{P2}/plant_production_capacity.csv")
sell_through = pd.read_csv(f"{P2}/historical_sell_through.csv")
markdowns = pd.read_csv(f"{P2}/historical_markdowns.csv")
logistics = pd.read_csv(f"{P2}/dc_to_store_logistics.csv")

issues = []
warnings = []
good = []

def issue(msg):
    issues.append(msg)
    print(f"  [ISSUE] {msg}")

def warn(msg):
    warnings.append(msg)
    print(f"  [WARN]  {msg}")

def ok(msg):
    good.append(msg)
    print(f"  [OK]    {msg}")


# ============================================================
print("\n1. ROW COUNTS & BASIC STATS")
print("-" * 50)
datasets = {
    "supplier_master": suppliers, "fabric_master": fabrics,
    "sku_master": skus, "plant_master": plants, "bom_material": bom,
    "contracts": contracts, "material_demand": mat_demand,
    "supplier_perf": sup_perf, "purchase_orders": pos,
    "demand_forecast": demand, "inventory": inventory,
    "fabric_constraints": fab_constraints, "plant_capacity": plant_cap,
    "sell_through": sell_through, "markdowns": markdowns, "logistics": logistics,
}
total = 0
for name, df in datasets.items():
    nulls = df.isnull().sum().sum()
    total += len(df)
    status = f"  {name}: {len(df)} rows, {len(df.columns)} cols"
    if nulls > 0:
        status += f", {nulls} nulls"
        warn(f"{name} has {nulls} null values")
    print(status)
print(f"  TOTAL: {total} rows across 16 datasets")


# ============================================================
print("\n2. REFERENTIAL INTEGRITY")
print("-" * 50)

sup_ids = set(suppliers["supplier_id"])
fab_ids = set(fabrics["fabric_id"])
sku_ids = set(skus["sku_id"])
plant_ids = set(plants["plant_id"])

# BOM -> SKU, Fabric
orphan_sku = set(bom["sku_id"]) - sku_ids
orphan_fab = set(bom["fabric_id"]) - fab_ids
if orphan_sku: issue(f"BOM has {len(orphan_sku)} SKU IDs not in sku_master: {orphan_sku}")
else: ok("BOM -> sku_master: all SKU IDs valid")
if orphan_fab: issue(f"BOM has {len(orphan_fab)} fabric IDs not in fabric_master: {orphan_fab}")
else: ok("BOM -> fabric_master: all fabric IDs valid")

# Contracts -> Supplier, Fabric
orphan_sup = set(contracts["supplier_id"]) - sup_ids
orphan_fab = set(contracts["fabric_id"]) - fab_ids
if orphan_sup: issue(f"Contracts have supplier IDs not in master: {orphan_sup}")
else: ok("Contracts -> supplier_master: valid")
if orphan_fab: issue(f"Contracts have fabric IDs not in master: {orphan_fab}")
else: ok("Contracts -> fabric_master: valid")

# POs -> Supplier, Fabric
orphan_sup = set(pos["supplier_id"]) - sup_ids
orphan_fab = set(pos["fabric_id"]) - fab_ids
if orphan_sup: issue(f"POs have supplier IDs not in master: {orphan_sup}")
else: ok("POs -> supplier_master: valid")
if orphan_fab: issue(f"POs have fabric IDs not in master: {orphan_fab}")
else: ok("POs -> fabric_master: valid")

# POs -> Contracts (does every PO's supplier-fabric combo exist in contracts?)
contract_pairs = set(zip(contracts["supplier_id"], contracts["fabric_id"]))
po_pairs = set(zip(pos["supplier_id"], pos["fabric_id"]))
orphan_po_pairs = po_pairs - contract_pairs
if orphan_po_pairs:
    issue(f"POs have {len(orphan_po_pairs)} (supplier, fabric) combos NOT in contracts")
else:
    ok("POs -> contracts: all (supplier, fabric) pairs have contracts")

# Demand -> SKU
orphan_sku = set(demand["sku_id"]) - sku_ids
if orphan_sku: issue(f"Demand has SKU IDs not in master: {orphan_sku}")
else: ok("Demand -> sku_master: valid")

# Inventory -> SKU
orphan_sku = set(inventory["sku_id"]) - sku_ids
if orphan_sku: issue(f"Inventory has SKU IDs not in master: {orphan_sku}")
else: ok("Inventory -> sku_master: valid")

# Sell-through -> SKU
orphan_sku = set(sell_through["sku_id"]) - sku_ids
if orphan_sku: issue(f"Sell-through has SKU IDs not in master: {orphan_sku}")
else: ok("Sell-through -> sku_master: valid")

# Markdowns -> SKU
orphan_sku = set(markdowns["sku_id"]) - sku_ids
if orphan_sku: issue(f"Markdowns has SKU IDs not in master: {orphan_sku}")
else: ok("Markdowns -> sku_master: valid")

# Material demand -> Fabric, Plant
orphan_fab = set(mat_demand["fabric_id"]) - fab_ids
orphan_plant = set(mat_demand["plant_id"]) - plant_ids
if orphan_fab: issue(f"Material demand has fabric IDs not in master: {orphan_fab}")
else: ok("Material demand -> fabric_master: valid")
if orphan_plant: issue(f"Material demand has plant IDs not in master: {orphan_plant}")
else: ok("Material demand -> plant_master: valid")

# Supplier perf -> Supplier
orphan_sup = set(sup_perf["supplier_id"]) - sup_ids
if orphan_sup: issue(f"Supplier perf has supplier IDs not in master: {orphan_sup}")
else: ok("Supplier perf -> supplier_master: valid")

# Plant capacity -> Plant
orphan_plant = set(plant_cap["plant_id"]) - plant_ids
if orphan_plant: issue(f"Plant capacity has plant IDs not in master: {orphan_plant}")
else: ok("Plant capacity -> plant_master: valid")

# Fabric constraints -> Fabric, Plant
orphan_fab = set(fab_constraints["fabric_id"]) - fab_ids
orphan_plant = set(fab_constraints["plant_id"]) - plant_ids
if orphan_fab: issue(f"Fabric constraints has fabric IDs not in master: {orphan_fab}")
else: ok("Fabric constraints -> fabric_master: valid")
if orphan_plant: issue(f"Fabric constraints has plant IDs not in master: {orphan_plant}")
else: ok("Fabric constraints -> plant_master: valid")


# ============================================================
print("\n3. COVERAGE ANALYSIS")
print("-" * 50)

# Do all SKUs appear in demand forecast?
skus_in_demand = set(demand["sku_id"])
missing = sku_ids - skus_in_demand
if missing: warn(f"{len(missing)} SKUs have no demand forecast: {missing}")
else: ok("All 50 SKUs have demand forecasts")

# Do all SKUs appear in BOM?
skus_in_bom = set(bom["sku_id"])
missing = sku_ids - skus_in_bom
if missing: issue(f"{len(missing)} SKUs have no BOM (cannot do MRP): {missing}")
else: ok("All 50 SKUs have BOM entries")

# Do all fabrics in BOM have at least one supplier contract?
fabrics_in_bom = set(bom["fabric_id"])
fabrics_in_contracts = set(contracts["fabric_id"])
missing = fabrics_in_bom - fabrics_in_contracts
if missing: issue(f"{len(missing)} fabrics in BOM have no supplier contract: {missing}")
else: ok("All BOM fabrics have supplier contracts")

# Do all suppliers have performance history?
sups_in_perf = set(sup_perf["supplier_id"])
missing = sup_ids - sups_in_perf
if missing: warn(f"{len(missing)} suppliers have no performance history: {missing}")
else: ok("All 25 suppliers have performance data")

# Do all plants have capacity data?
plants_in_cap = set(plant_cap["plant_id"])
missing = plant_ids - plants_in_cap
if missing: issue(f"{len(missing)} plants have no capacity data: {missing}")
else: ok("All 5 plants have capacity data")

# Do all SKUs have sell-through data?
skus_in_st = set(sell_through["sku_id"])
missing = sku_ids - skus_in_st
if missing: warn(f"{len(missing)} SKUs have no sell-through data")
else: ok("All 50 SKUs have sell-through data")

# Do all SKUs have inventory?
skus_in_inv = set(inventory["sku_id"])
missing = sku_ids - skus_in_inv
if missing: warn(f"{len(missing)} SKUs have no inventory records")
else: ok("All 50 SKUs have inventory records")


# ============================================================
print("\n4. PURCHASE ORDER LOGICAL CONSISTENCY")
print("-" * 50)

pos["order_date"] = pd.to_datetime(pos["order_date"])
pos["promised_delivery_date"] = pd.to_datetime(pos["promised_delivery_date"])
pos["actual_delivery_date"] = pd.to_datetime(pos["actual_delivery_date"])

# Check delayed_days = actual - promised
pos["calc_delay"] = (pos["actual_delivery_date"] - pos["promised_delivery_date"]).dt.days
mismatch = pos[pos["calc_delay"] != pos["delayed_days"]]
if len(mismatch) > 0:
    issue(f"{len(mismatch)} POs have delayed_days mismatch (calc vs stored)")
    print(f"         Sample: calc={mismatch['calc_delay'].iloc[0]}, stored={mismatch['delayed_days'].iloc[0]}")
else:
    ok("delayed_days matches actual-promised for all POs")

# Check is_on_time consistency
pos["calc_on_time"] = (pos["delayed_days"] <= 0).astype(int)
mismatch_ot = pos[pos["calc_on_time"] != pos["is_on_time"]]
if len(mismatch_ot) > 0:
    issue(f"{len(mismatch_ot)} POs have is_on_time mismatch")
    # Show some examples
    sample = mismatch_ot[["po_id", "delayed_days", "is_on_time", "calc_on_time"]].head(5)
    print(f"         Sample:\n{sample.to_string()}")
else:
    ok("is_on_time consistent with delayed_days for all POs")

# Check risk_category vs delayed_days makes sense
risk_delay = pos.groupby("risk_category")["delayed_days"].agg(["mean", "median", "count"])
print(f"  Risk category delay distribution:")
for cat, row in risk_delay.iterrows():
    print(f"    {cat}: mean={row['mean']:.1f} days, median={row['median']:.0f}, count={int(row['count'])}")

# Are there negative delayed_days?
neg_delay = pos[pos["delayed_days"] < 0]
if len(neg_delay) > 0:
    warn(f"{len(neg_delay)} POs have negative delayed_days (early delivery)")
    print(f"         Range: {neg_delay['delayed_days'].min()} to {neg_delay['delayed_days'].max()}")

# Order date before promised date?
bad_dates = pos[pos["order_date"] >= pos["promised_delivery_date"]]
if len(bad_dates) > 0:
    issue(f"{len(bad_dates)} POs have order_date >= promised_delivery_date")
else:
    ok("All POs have order_date before promised_delivery_date")

# Lead time (promised - order) distribution
pos["lead_time_calc"] = (pos["promised_delivery_date"] - pos["order_date"]).dt.days
print(f"  Lead time distribution: min={pos['lead_time_calc'].min()}, max={pos['lead_time_calc'].max()}, mean={pos['lead_time_calc'].mean():.1f}")


# ============================================================
print("\n5. CONTRACT vs MATERIAL DEMAND SCALE CHECK")
print("-" * 50)

# Per-fabric monthly capacity from contracts
fab_cap = contracts.groupby("fabric_id")["monthly_capacity_meters"].sum()
# Per-fabric single-period demand from material_demand_forecast
for period in ["2026-M01"]:
    single = mat_demand[mat_demand["period"] == period]
    fab_dem = single.groupby("fabric_id")["required_meters"].sum()
    
    feasible = 0
    infeasible = 0
    for fab in fab_dem.index:
        if fab in fab_cap.index:
            if fab_dem[fab] > fab_cap[fab]:
                infeasible += 1
            else:
                feasible += 1
    
    ratio = infeasible / (feasible + infeasible) * 100 if (feasible + infeasible) > 0 else 0
    if infeasible > 0:
        warn(f"Period {period}: {infeasible}/{feasible+infeasible} fabrics have demand > total capacity ({ratio:.0f}%)")
    else:
        ok(f"Period {period}: all fabrics have demand within capacity")


# ============================================================
print("\n6. DEMAND FORECAST DISTRIBUTION")
print("-" * 50)

# Periods covered
periods = sorted(demand["period"].unique())
print(f"  Periods: {periods[0]} to {periods[-1]} ({len(periods)} periods)")

# Regions
regions = demand["region"].unique()
print(f"  Regions: {list(regions)} ({len(regions)})")

# SKUs per period
skus_per_period = demand.groupby("period")["sku_id"].nunique()
print(f"  SKUs per period: min={skus_per_period.min()}, max={skus_per_period.max()}")

# Demand distribution
print(f"  Demand units: min={demand['forecasted_demand_units'].min()}, max={demand['forecasted_demand_units'].max()}, mean={demand['forecasted_demand_units'].mean():.0f}")


# ============================================================
print("\n7. SELL-THROUGH DATA CHECK")
print("-" * 50)

# sell_through_rate should be between 0 and 1
bad_st = sell_through[(sell_through["sell_through_rate"] < 0) | (sell_through["sell_through_rate"] > 1)]
if len(bad_st) > 0:
    issue(f"{len(bad_st)} sell-through records have rate outside [0, 1]")
else:
    ok("All sell-through rates between 0 and 1")

# units_sold should not exceed units_available
bad_sold = sell_through[sell_through["units_sold"] > sell_through["units_available"]]
if len(bad_sold) > 0:
    issue(f"{len(bad_sold)} sell-through records have units_sold > units_available")
else:
    ok("units_sold <= units_available for all records")

# Verify sell_through_rate = units_sold / units_available
sell_through["calc_rate"] = sell_through["units_sold"] / sell_through["units_available"]
rate_diff = (sell_through["sell_through_rate"] - sell_through["calc_rate"]).abs()
bad_rate = rate_diff[rate_diff > 0.01]
if len(bad_rate) > 0:
    warn(f"{len(bad_rate)} sell-through records have rate mismatch (> 0.01 diff)")
else:
    ok("sell_through_rate matches units_sold/units_available")

# Weeks covered
weeks = sorted(sell_through["selling_week"].unique())
print(f"  Weeks: {weeks[0]} to {weeks[-1]} ({len(weeks)} weeks)")


# ============================================================
print("\n8. SUPPLIER PERFORMANCE DATA CHECK")
print("-" * 50)

# OTD and quality should be 0-100 range
if sup_perf["otd_rating_pct"].min() < 0 or sup_perf["otd_rating_pct"].max() > 100:
    issue("OTD rating outside 0-100 range")
else:
    ok(f"OTD rating range: {sup_perf['otd_rating_pct'].min():.1f} to {sup_perf['otd_rating_pct'].max():.1f}")

if sup_perf["quality_pass_rate_pct"].min() < 0 or sup_perf["quality_pass_rate_pct"].max() > 100:
    issue("Quality pass rate outside 0-100 range")
else:
    ok(f"Quality range: {sup_perf['quality_pass_rate_pct'].min():.1f} to {sup_perf['quality_pass_rate_pct'].max():.1f}")

# Check overall_risk_score = 100 - (otd*0.5 + quality*0.5)
sup_perf["calc_risk"] = 100 - (sup_perf["otd_rating_pct"] * 0.5 + sup_perf["quality_pass_rate_pct"] * 0.5)
risk_diff = (sup_perf["overall_risk_score"] - sup_perf["calc_risk"]).abs()
bad_risk = risk_diff[risk_diff > 0.1]
if len(bad_risk) > 0:
    warn(f"{len(bad_risk)} supplier perf records have risk score mismatch")
else:
    ok("overall_risk_score formula verified for all records")

# Supplier perf periods
perf_periods = sorted(sup_perf["evaluation_period"].unique())
print(f"  Performance periods: {perf_periods[0]} to {perf_periods[-1]} ({len(perf_periods)} periods)")

# Do high-risk suppliers (from master) actually perform worse?
risk_map = suppliers.set_index("supplier_id")["base_risk_factor"].to_dict()
sup_perf["base_risk"] = sup_perf["supplier_id"].map(risk_map)
high_risk = sup_perf[sup_perf["base_risk"] >= 0.25]
low_risk = sup_perf[sup_perf["base_risk"] <= 0.10]
print(f"  High-risk suppliers (base_risk>=0.25) avg OTD: {high_risk['otd_rating_pct'].mean():.1f}")
print(f"  Low-risk suppliers (base_risk<=0.10) avg OTD: {low_risk['otd_rating_pct'].mean():.1f}")
if high_risk["otd_rating_pct"].mean() >= low_risk["otd_rating_pct"].mean():
    warn("High-risk suppliers perform EQUAL/BETTER on OTD than low-risk (no signal)")
else:
    ok("High-risk suppliers perform worse on OTD (realistic signal)")


# ============================================================
print("\n9. CONTRACT BUSINESS RULES CHECK")
print("-" * 50)

# min_alloc + max_alloc should make sense
bad_alloc = contracts[contracts["min_allocation_pct"] >= contracts["max_allocation_pct"]]
if len(bad_alloc) > 0:
    issue(f"{len(bad_alloc)} contracts have min_alloc >= max_alloc")
else:
    ok("All contracts have min_alloc < max_alloc")

# MOQ should not exceed monthly capacity
bad_moq = contracts[contracts["moq_meters"] > contracts["monthly_capacity_meters"]]
if len(bad_moq) > 0:
    issue(f"{len(bad_moq)} contracts have MOQ > monthly capacity")
else:
    ok("All contracts have MOQ <= monthly capacity")

# Unit price range
print(f"  Unit price range: ${contracts['unit_price'].min():.2f} to ${contracts['unit_price'].max():.2f}")
print(f"  Monthly capacity range: {contracts['monthly_capacity_meters'].min()} to {contracts['monthly_capacity_meters'].max()}")
print(f"  MOQ range: {contracts['moq_meters'].min()} to {contracts['moq_meters'].max()}")
print(f"  Lead time range: {contracts['contracted_lead_time_days'].min()} to {contracts['contracted_lead_time_days'].max()} days")

# Duplicate (supplier, fabric) pairs?
dup_pairs = contracts.groupby(["supplier_id", "fabric_id"]).size()
dups = dup_pairs[dup_pairs > 1]
if len(dups) > 0:
    warn(f"{len(dups)} duplicate (supplier, fabric) pairs in contracts")
else:
    ok("No duplicate (supplier, fabric) pairs in contracts")


# ============================================================
print("\n10. MARKDOWN DATA CHECK")
print("-" * 50)

# markdown_pct should be > 0 and < 100
bad_md = markdowns[(markdowns["discount_percentage"] <= 0) | (markdowns["discount_percentage"] >= 100)]
if len(bad_md) > 0:
    issue(f"{len(bad_md)} markdowns with pct outside (0, 100)")
else:
    ok(f"Markdown pct range: {markdowns['discount_percentage'].min():.1f}% to {markdowns['discount_percentage'].max():.1f}%")

# discounted_price < original_price
bad_price = markdowns[markdowns["discounted_price"] >= markdowns["original_price"]]
if len(bad_price) > 0:
    issue(f"{len(bad_price)} markdowns where discounted_price >= original_price")
else:
    ok("All discounted prices are below original prices")


# ============================================================
print("\n11. INVENTORY UNIQUENESS CHECK")
print("-" * 50)

# Unique (sku_id, location_id) pairs
inv_dups = inventory.groupby(["sku_id", "location_id"]).size()
inv_dup_count = inv_dups[inv_dups > 1]
if len(inv_dup_count) > 0:
    issue(f"{len(inv_dup_count)} duplicate (sku, location) pairs in inventory")
else:
    ok("All (sku, location) pairs are unique in inventory")

# Safety stock should be reasonable vs available
bad_safety = inventory[inventory["safety_stock_threshold"] > inventory["available_stock_units"]]
pct_below = len(bad_safety) / len(inventory) * 100
print(f"  {len(bad_safety)}/{len(inventory)} ({pct_below:.0f}%) locations below safety stock")


# ============================================================
print("\n12. PERIOD ALIGNMENT ACROSS TABLES")
print("-" * 50)

demand_periods = set(demand["period"].unique())
matdem_periods = set(mat_demand["period"].unique())
perf_periods_set = set(sup_perf["evaluation_period"].unique())
plantcap_periods = set(plant_cap["period"].unique())

print(f"  Demand forecast periods:    {len(demand_periods)} ({sorted(demand_periods)[0]} to {sorted(demand_periods)[-1]})")
print(f"  Material demand periods:    {len(matdem_periods)} ({sorted(matdem_periods)[0]} to {sorted(matdem_periods)[-1]})")
print(f"  Supplier perf periods:      {len(perf_periods_set)} ({sorted(perf_periods_set)[0]} to {sorted(perf_periods_set)[-1]})")
print(f"  Plant capacity periods:     {len(plantcap_periods)} ({sorted(plantcap_periods)[0]} to {sorted(plantcap_periods)[-1]})")

# Check overlap
common = demand_periods & matdem_periods & plantcap_periods
if len(common) == 0:
    issue("No common periods across demand, material demand, and plant capacity")
else:
    ok(f"{len(common)} common periods across demand/material/capacity tables")


# ============================================================
print("\n13. DATA DISTRIBUTION REALISM")
print("-" * 50)

# Supplier tier distribution
tier_dist = suppliers["tier_rating"].value_counts()
print(f"  Supplier tiers: {tier_dist.to_dict()}")

# Category distribution in SKUs
cat_dist = skus["category"].value_counts()
print(f"  SKU categories: {cat_dist.to_dict()}")

# Season distribution  
season_dist = skus["season"].value_counts()
print(f"  SKU seasons: {season_dist.to_dict()}")

# PO risk category distribution
risk_dist = pos["risk_category"].value_counts()
print(f"  PO risk categories: {risk_dist.to_dict()}")

# OTD rate
otd_rate = pos["is_on_time"].mean() * 100
print(f"  Overall OTD rate: {otd_rate:.1f}%")
if otd_rate > 50:
    ok(f"OTD rate ({otd_rate:.1f}%) is realistic")
elif otd_rate < 15:
    warn(f"OTD rate ({otd_rate:.1f}%) seems unusually low")


# ============================================================
print("\n" + "=" * 70)
print("AUDIT SUMMARY")
print("=" * 70)
print(f"  Issues found:   {len(issues)}")
print(f"  Warnings:       {len(warnings)}")
print(f"  Checks passed:  {len(good)}")

if issues:
    print("\n  CRITICAL ISSUES:")
    for i, iss in enumerate(issues, 1):
        print(f"    {i}. {iss}")

if warnings:
    print("\n  WARNINGS:")
    for i, w in enumerate(warnings, 1):
        print(f"    {i}. {w}")
