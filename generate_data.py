import os
import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

np.random.seed(42)
random.seed(42)

OUTPUT_DIR = "./hackathon_dataset"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Generating dataset...")

# ==========================================
# 1. MASTER TABLES
# ==========================================

# Supplier Master (25 rows)
supplier_names = [
    "Apex Textiles", "Vanguard Fabrics", "Omni Thread Works", "Titan Weavers",
    "Elysian Mills", "Nordic Fiber Co", "SilkRoad Logistics", "Atlas Yarn Corp",
    "Zenith Weaving", "Pinnacle Yarns", "Quantum Mills", "Horizon Textiles",
    "Apex Materials", "Bayfront Weavers", "Crestline Yarns", "Delta Fabrics",
    "EcoFiber Solutions", "Frontier Textiles", "Global Weave", "Heritage Yarns",
    "Imperial Fabrics", "Jubilee Thread", "Kestrel Textiles", "Lumina Fibers",
    "Matrix Weavers",
]
locations = ["Bangalore", "Tirupur", "Surat", "Ludhiana", "Ahmedabad", "Coimbatore"]

suppliers = []
for i in range(1, 26):
    suppliers.append({
        "supplier_id": f"SUP_{i:03d}",
        "supplier_name": supplier_names[i - 1],
        "location": random.choice(locations),
        "tier_rating": random.choice(["Tier 1", "Tier 2", "Tier 3"]),
        "base_risk_factor": round(random.uniform(0.05, 0.35), 2),
    })
df_suppliers = pd.DataFrame(suppliers)
df_suppliers.to_csv(f"{OUTPUT_DIR}/supplier_master.csv", index=False)

# Fabric Master (30 rows)
fabric_types = ["Cotton", "Polyester", "Denim", "Linen", "Wool Blend", "Silk", "Nylon", "Rayon"]
fabrics = []
for i in range(1, 31):
    fabrics.append({
        "fabric_id": f"FAB_{i:03d}",
        "fabric_name": f"{random.choice(fabric_types)} Type-{i}",
        "unit_of_measure": "Meters",
        "standard_lead_time_days": random.randint(14, 45),
        "standard_cost_per_meter": round(random.uniform(3.5, 18.0), 2),
    })
df_fabrics = pd.DataFrame(fabrics)
df_fabrics.to_csv(f"{OUTPUT_DIR}/fabric_master.csv", index=False)

# SKU Master (50 rows)
categories = ["Jackets", "Shirts", "Trousers", "Dresses", "Activewear", "Outerwear"]
seasons = ["SS26", "FW26", "SS27", "FW27"]
used_style_names = set()
skus = []
for i in range(1, 51):
    # Ensure unique style names
    while True:
        sname = f"Style-{random.randint(100, 999)}"
        if sname not in used_style_names:
            used_style_names.add(sname)
            break
    skus.append({
        "sku_id": f"SKU_{i:04d}",
        "style_name": sname,
        "category": random.choice(categories),
        "season": random.choice(seasons),
        "target_unit_price": round(random.uniform(25.0, 150.0), 2),
        "launch_date": (datetime(2026, 1, 1) + timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d"),
    })
df_skus = pd.DataFrame(skus)
df_skus.to_csv(f"{OUTPUT_DIR}/sku_master.csv", index=False)

# Plant Master (5 rows)
plants = []
for i in range(1, 6):
    plants.append({
        "plant_id": f"PLANT_{i:02d}",
        "plant_name": f"Manufacturing Hub {i}",
        "city": random.choice(locations),
        "weekly_capacity_units": random.randint(10000, 25000),
    })
df_plants = pd.DataFrame(plants)
df_plants.to_csv(f"{OUTPUT_DIR}/plant_master.csv", index=False)


# ==========================================
# 2. BRIDGE & CONFIGURATION TABLES
# ==========================================

# BOM Material (~200 rows) - Maps SKUs to Fabrics
# Each SKU gets 3-5 fabrics. We finish the current SKU even if we cross 200.
bom = []
bom_id = 1
for sku in df_skus["sku_id"]:
    if bom_id > 200:
        break
    selected_fabrics = random.sample(list(df_fabrics["fabric_id"]), random.randint(3, 5))
    for fab in selected_fabrics:
        bom.append({
            "bom_id": f"BOM_{bom_id:05d}",
            "sku_id": sku,
            "fabric_id": fab,
            "fabric_per_unit_meters": round(random.uniform(1.2, 4.5), 2),
        })
        bom_id += 1
df_bom = pd.DataFrame(bom)
df_bom.to_csv(f"{OUTPUT_DIR}/bom_material.csv", index=False)

# Current Inventory (500 rows) - Unique (sku, location) pairs
plant_ids = [p["plant_id"] for p in plants]
dc_ids = [f"DC_{i:02d}" for i in range(1, 6)]
locations_all = plant_ids + dc_ids

inv_pairs = set()
all_sku_ids = list(df_skus["sku_id"])
while len(inv_pairs) < 500:
    sku = random.choice(all_sku_ids)
    loc = random.choice(locations_all)
    inv_pairs.add((sku, loc))

inventory = []
for idx, (sku, loc) in enumerate(inv_pairs, 1):
    opening = random.randint(500, 5000)
    allocated = random.randint(100, opening)
    inventory.append({
        "inventory_id": f"INV_{idx:05d}",
        "sku_id": sku,
        "location_id": loc,
        "opening_stock_units": opening,
        "allocated_units": allocated,
        "available_stock_units": opening - allocated,
        "safety_stock_threshold": random.randint(300, 800),
    })
df_inventory = pd.DataFrame(inventory)
df_inventory.to_csv(f"{OUTPUT_DIR}/current_inventory.csv", index=False)

# Supplier Material Contracts (~250 rows)
# Each supplier handles 8-12 fabrics. Finish each supplier before checking limit.
fabric_cost_map = df_fabrics.set_index("fabric_id")["standard_cost_per_meter"].to_dict()
contracts = []
contract_id = 1
for sup in df_suppliers["supplier_id"]:
    if contract_id > 250:
        break
    fabs = random.sample(list(df_fabrics["fabric_id"]), random.randint(8, 12))
    for fab in fabs:
        base_cost = fabric_cost_map[fab]
        contracts.append({
            "contract_id": f"CNT_{contract_id:05d}",
            "supplier_id": sup,
            "fabric_id": fab,
            "unit_price": round(base_cost * random.uniform(0.9, 1.15), 2),
            "monthly_capacity_meters": random.randint(5000, 30000),
            "contracted_lead_time_days": random.randint(14, 40),
            "moq_meters": random.choice([500, 1000, 2500, 5000]),
            "min_allocation_pct": random.choice([0.10, 0.15, 0.20]),
            "max_allocation_pct": random.choice([0.50, 0.60, 0.70]),
        })
        contract_id += 1
df_contracts = pd.DataFrame(contracts)
df_contracts.to_csv(f"{OUTPUT_DIR}/supplier_material_contracts.csv", index=False)

# Fabric Constraints (300 rows) - Unique (fabric, plant) pairs
fc_pairs = set()
all_fab_ids = list(df_fabrics["fabric_id"])
all_plant_ids = list(df_plants["plant_id"])
while len(fc_pairs) < min(300, len(all_fab_ids) * len(all_plant_ids)):
    fab = random.choice(all_fab_ids)
    plant = random.choice(all_plant_ids)
    fc_pairs.add((fab, plant))

fabric_constraints = []
for idx, (fab, plant) in enumerate(fc_pairs, 1):
    fabric_constraints.append({
        "constraint_id": f"FC_{idx:05d}",
        "fabric_id": fab,
        "plant_id": plant,
        "max_weekly_throughput_meters": random.randint(8000, 20000),
        "mcq_meters": random.choice([200, 500, 1000]),
        "fabric_lead_time_weeks": random.randint(2, 6),
    })
df_fabric_constraints = pd.DataFrame(fabric_constraints)
df_fabric_constraints.to_csv(f"{OUTPUT_DIR}/fabric_constraints.csv", index=False)


# ==========================================
# 3. S&OP DATASETS
# ==========================================

forecast_periods = [f"2026-M{m:02d}" for m in range(1, 13)] + [f"2027-M{m:02d}" for m in range(1, 13)]
regions = ["North_America", "Europe", "Asia_Pacific", "Latin_America"]

# Seasonal SKU Demand Forecast - Unique (sku, region, period) combos
# 50 SKUs x 4 regions x 24 periods = 4800 max
max_demand_combos = min(4000, len(all_sku_ids) * len(regions) * len(forecast_periods))
demand_combos = set()
while len(demand_combos) < max_demand_combos:
    sku = random.choice(all_sku_ids)
    region = random.choice(regions)
    period = random.choice(forecast_periods)
    demand_combos.add((sku, region, period))

demand_forecast = []
for idx, (sku, region, period) in enumerate(demand_combos, 1):
    demand_forecast.append({
        "forecast_id": f"FCT_{idx:06d}",
        "sku_id": sku,
        "region": region,
        "period": period,
        "forecasted_demand_units": random.randint(1000, 15000),
        "confidence_interval_pct": round(random.uniform(0.80, 0.95), 2),
    })
df_demand_forecast = pd.DataFrame(demand_forecast)
df_demand_forecast.to_csv(f"{OUTPUT_DIR}/seasonal_sku_demand.csv", index=False)

# Historical Sell-Through - Unique (sku, week) combos
# 50 SKUs x 52 weeks = 2600 max unique combos
weeks = [f"2026-W{w:02d}" for w in range(1, 53)]
st_combos = set()
max_st_combos = min(2600, len(all_sku_ids) * len(weeks))
while len(st_combos) < max_st_combos:
    sku = random.choice(all_sku_ids)
    week = random.choice(weeks)
    st_combos.add((sku, week))

sell_through = []
for idx, (sku, week) in enumerate(st_combos, 1):
    avail = random.randint(2000, 10000)
    sold = random.randint(200, avail)
    sell_through.append({
        "sell_through_id": f"ST_{idx:06d}",
        "sku_id": sku,
        "selling_week": week,
        "units_available": avail,
        "units_sold": sold,
        "sell_through_rate": round(sold / avail, 4),
    })
df_sell_through = pd.DataFrame(sell_through)
df_sell_through.to_csv(f"{OUTPUT_DIR}/historical_sell_through.csv", index=False)

# Historical Markdowns (2000 rows)
sku_price_map = df_skus.set_index("sku_id")["target_unit_price"].to_dict()
markdowns = []
for i in range(1, 2001):
    sku = random.choice(all_sku_ids)
    orig_price = sku_price_map[sku]
    discount = random.choice([0.15, 0.25, 0.35, 0.50])
    markdowns.append({
        "markdown_id": f"MKD_{i:05d}",
        "sku_id": sku,
        "period": f"2026-W{random.randint(1, 52):02d}",
        "original_price": orig_price,
        "discount_percentage": discount,
        "discounted_price": round(orig_price * (1 - discount), 2),
        "units_sold_post_markdown": random.randint(300, 3000),
        "remaining_unallocated_stock": random.randint(100, 1500),
    })
df_markdowns = pd.DataFrame(markdowns)
df_markdowns.to_csv(f"{OUTPUT_DIR}/historical_markdowns.csv", index=False)

# DC to Store Logistics (2000 rows)
stores = [f"STORE_{i:04d}" for i in range(1, 101)]
logistics = []
for i in range(1, 2001):
    logistics.append({
        "route_id": f"ROUTE_{i:05d}",
        "dc_id": random.choice(dc_ids),
        "store_id": random.choice(stores),
        "transit_lead_time_days": random.randint(1, 7),
        "transportation_cost_per_unit": round(random.uniform(0.80, 4.50), 2),
        "expedited_cost_per_unit": round(random.uniform(5.00, 12.00), 2),
    })
df_logistics = pd.DataFrame(logistics)
df_logistics.to_csv(f"{OUTPUT_DIR}/dc_to_store_logistics.csv", index=False)

# Plant Production Capacity (~500 rows)
# Finish each plant's periods before checking limit
plant_capacity = []
pc_id = 1
for plant in df_plants["plant_id"]:
    if pc_id > 500:
        break
    for period in forecast_periods:
        max_cap = random.randint(15000, 40000)
        alloc_cap = random.randint(10000, max_cap)
        plant_capacity.append({
            "capacity_id": f"CAP_{pc_id:05d}",
            "plant_id": plant,
            "period": period,
            "total_available_hours": random.randint(1200, 2000),
            "max_units_capacity": max_cap,
            "allocated_units_capacity": alloc_cap,
        })
        pc_id += 1
df_plant_capacity = pd.DataFrame(plant_capacity)
df_plant_capacity.to_csv(f"{OUTPUT_DIR}/plant_production_capacity.csv", index=False)


# ==========================================
# 4. PROCUREMENT & ML DATASETS
# ==========================================

# Material Demand Forecast (2000 rows)
material_demand = []
for i in range(1, 2001):
    material_demand.append({
        "material_demand_id": f"MD_{i:05d}",
        "plant_id": random.choice(all_plant_ids),
        "fabric_id": random.choice(all_fab_ids),
        "period": random.choice(forecast_periods),
        "required_meters": random.randint(2000, 25000),
        "urgency_level": random.choice(["Normal", "High", "Critical"]),
    })
df_material_demand = pd.DataFrame(material_demand)
df_material_demand.to_csv(f"{OUTPUT_DIR}/material_demand_forecast.csv", index=False)

# Supplier Performance History (2000 rows)
supplier_perf = []
for i in range(1, 2001):
    sup = random.choice(list(df_suppliers["supplier_id"]))
    otd = round(random.uniform(75.0, 99.5), 2)
    quality = round(random.uniform(85.0, 99.9), 2)
    supplier_perf.append({
        "perf_id": f"PERF_{i:05d}",
        "supplier_id": sup,
        "evaluation_period": random.choice(forecast_periods),
        "otd_rating_pct": otd,
        "quality_pass_rate_pct": quality,
        "defect_ppm": random.randint(50, 1200),
        "overall_risk_score": round(100 - (otd * 0.5 + quality * 0.5), 2),
    })
df_supplier_perf = pd.DataFrame(supplier_perf)
df_supplier_perf.to_csv(f"{OUTPUT_DIR}/supplier_performance_history.csv", index=False)

# Historical Purchase Orders (8000 rows) - ML Training Data
print("Generating 8000 Purchase Orders...")
sup_risk_map = df_suppliers.set_index("supplier_id")["base_risk_factor"].to_dict()
base_start_date = datetime(2024, 1, 1)

pos = []
for i in range(1, 8001):
    contract = df_contracts.sample(1).iloc[0]
    sup_id = contract["supplier_id"]
    fab_id = contract["fabric_id"]
    sup_risk = sup_risk_map[sup_id]

    order_qty = random.randint(500, 20000)
    promised_days = contract["contracted_lead_time_days"]

    # Delay simulation using negative binomial distribution
    qty_strain = 1.0 + (order_qty / 20000) * 0.3
    expected_delay = sup_risk * 15 * qty_strain
    actual_delay = max(0, int(np.random.negative_binomial(n=2, p=2 / (2 + expected_delay))))

    actual_days = promised_days + actual_delay
    otd_flag = 1 if actual_delay <= 0 else 0

    # Quality score simulation
    base_quality = 98.0 - (sup_risk * 20)
    quality_score = round(
        np.clip(np.random.normal(loc=base_quality, scale=3.5), a_min=65.0, a_max=100.0), 2
    )

    order_date = base_start_date + timedelta(days=random.randint(0, 700))
    promised_date = order_date + timedelta(days=int(promised_days))
    actual_date = order_date + timedelta(days=int(actual_days))

    pos.append({
        "po_id": f"PO_{i:06d}",
        "supplier_id": sup_id,
        "fabric_id": fab_id,
        "order_quantity_meters": order_qty,
        "unit_price": contract["unit_price"],
        "total_po_value": round(order_qty * contract["unit_price"], 2),
        "order_date": order_date.strftime("%Y-%m-%d"),
        "promised_delivery_date": promised_date.strftime("%Y-%m-%d"),
        "actual_delivery_date": actual_date.strftime("%Y-%m-%d"),
        "contracted_lead_time_days": promised_days,
        "actual_lead_time_days": actual_days,
        "delayed_days": actual_delay,
        "is_on_time": otd_flag,
        "quality_pass_rate_pct": quality_score,
        "risk_category": (
            "High" if actual_delay > 7 or quality_score < 85
            else ("Medium" if actual_delay > 0 else "Low")
        ),
    })

df_pos = pd.DataFrame(pos)
df_pos.to_csv(f"{OUTPUT_DIR}/historical_purchase_orders.csv", index=False)

# Validation
print("\nValidation Summary:")
datasets = {
    "supplier_master": (df_suppliers, 25),
    "fabric_master": (df_fabrics, 30),
    "sku_master": (df_skus, 50),
    "plant_master": (df_plants, 5),
    "bom_material": (df_bom, None),
    "current_inventory": (df_inventory, 500),
    "supplier_material_contracts": (df_contracts, None),
    "fabric_constraints": (df_fabric_constraints, None),
    "seasonal_sku_demand": (df_demand_forecast, 4000),
    "historical_sell_through": (df_sell_through, 4000),
    "historical_markdowns": (df_markdowns, 2000),
    "dc_to_store_logistics": (df_logistics, 2000),
    "plant_production_capacity": (df_plant_capacity, None),
    "material_demand_forecast": (df_material_demand, 2000),
    "supplier_performance_history": (df_supplier_perf, 2000),
    "historical_purchase_orders": (df_pos, 8000),
}

total_rows = 0
for name, (df, expected) in datasets.items():
    actual = len(df)
    total_rows += actual
    status = "OK" if expected is None or actual >= expected else "LOW"
    print(f"  {name}: {actual} rows [{status}]")

print(f"\nTotal rows: {total_rows}")
print("Done. All 16 datasets saved to", OUTPUT_DIR)
