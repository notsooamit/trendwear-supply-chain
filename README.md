# TrendWear Supply Chain Intelligence Platform

An integrated Sales and Operations Planning (S&OP) and Procurement Optimization Control Tower built for apparel manufacturing supply chains.

---

## 1. Project Overview

The TrendWear platform addresses two core operational problems faced by multi-region fashion and apparel enterprises:

1. **Problem Statement 1: Integrated S&OP (P2)**
   - Reconciles multi-region demand projections with plant manufacturing capacity and raw material lead times.
   - Executes Material Requirements Planning (MRP) explosions across Bill of Materials (BOM) structures.
   - Evaluates inventory sell-through velocity to recommend markdown schedules and prevent inventory obsolescence.

2. **Problem Statement 2: Procurement Optimization and Risk Prediction (PR1)**
   - Formulates Mixed-Integer Linear Programming (MILP) models using PuLP to allocate fabric demand across candidate suppliers.
   - Minimizes total landed costs while enforcing Minimum Order Quantities (MOQs), supplier capacity bounds, and contract risk penalties.
   - Deploys supervised Machine Learning algorithms (XGBoost Regressor and Random Forest Classifier) to predict purchase order delivery delays and classify supplier risk profiles before order emission.

---

## 2. System Architecture

```
                                +----------------------------------+
                                |  Streamlit Enterprise UI Router  |
                                |       Role-Based Access Control  |
                                +----------------+-----------------+
                                                 |
                       +-------------------------+-------------------------+
                       |                                                   |
        +--------------v--------------+                     +--------------v--------------+
        |   S&OP Planning Engine      |                     |   Procurement Optimizer     |
        |   (core/sop_engine.py)      |                     |   (core/optimizer.py)       |
        +--------------+--------------+                     +--------------+--------------+
                       |                                                   |
                       | Gross Material                                    | Optimal Sourcing
                       | Requirements                                     | Allocation
                       |                                                   |
        +--------------v--------------+                     +--------------v--------------+
        |   Markdown Recommender      |                     |   ML Delay & Risk Pipeline  |
        | (core/markdown_engine.py)   |                     |   (core/risk_model.py)      |
        +-----------------------------+                     +-----------------------------+
                                                 |
                                +----------------v-----------------+
                                |   What-If Scenario Simulation    |
                                |    (core/scenario_engine.py)     |
                                +----------------------------------+
```

---

## 3. Core Mathematical Formulations and Logic

### 3.1 Material Requirements Planning (MRP) Explosion
Given a set of SKUs `k`, fabrics `f`, and planning period `t`:

```
RequiredMeters(f, t) = Sum over k of [ Demand(k, t) * BOM(k, f) ]
```

Where `Demand(k, t)` represents total forecasted demand units for SKU `k` in period `t`, and `BOM(k, f)` is the fabric meters required per SKU unit.

### 3.2 Mixed-Integer Linear Programming Procurement Model (PuLP)
Minimize total landed cost, weighted risk penalties, lead time penalties, and unfulfilled demand penalties:

```
Minimize TotalCost = 
    Sum_{s, f} [ w_cost * Price(s, f) * x(s, f) ]
  + Sum_{s, f} [ w_risk * RiskScore(s) * Price(s, f) * x(s, f) ]
  + Sum_{s, f} [ w_lt * LeadTime(s, f) * Price(s, f) * x(s, f) ]
  + Sum_{f}    [ BigM * z(f) ]
```

**Subject to:**
1. **Demand Satisfaction:** `Sum_s [ x(s, f) ] + z(f) = RequiredMeters(f, t)` for all fabrics `f`.
2. **Capacity Bounds:** `x(s, f) <= Capacity(s, f) * y(s, f)` for all `s, f`.
3. **Minimum Order Quantities:** `x(s, f) >= MOQ(s, f) * y(s, f)` for all `s, f`.
4. **Contract Minimum Allocation:** `x(s, f) >= MinAllocPct(s, f) * RequiredMeters(f, t) * y(s, f)` for all `s, f`.
5. **Contract Maximum Allocation:** `x(s, f) <= MaxAllocPct(s, f) * RequiredMeters(f, t)` for all `s, f`.

Where `x(s, f) >= 0` is the continuous volume allocation variable, `y(s, f) in {0, 1}` is the binary contract activation variable, and `z(f) >= 0` is the shortfall variable penalized by Big-M coefficient `BigM = 10,000`.

### 3.3 Supervised Machine Learning Pipelines
- **Delay Regressor (XGBoost):** Predicts continuous delivery delay in days using order quantity, lead time, historical supplier OTD %, quality pass rate, defect PPM, and risk interaction terms.
- **Risk Classifier (Random Forest):** Classifies purchase orders into Low, Medium, or High risk categories.

---

## 4. Synthetic Datasets

The repository includes 16 synthetic CSV datasets comprising 23,935 rows organized under `hackathon_dataset/`:

```
hackathon_dataset/
|-- shared/                      # Master Data Tables
|   |-- supplier_master.csv      # 25 Suppliers (ID, Name, Tier, Location, Base Risk)
|   |-- fabric_master.csv        # 30 Fabrics (ID, Name, Type, Standard Cost, Lead Time)
|   |-- sku_master.csv           # 50 SKUs (ID, Style, Category, Season, Target Price)
|   |-- plant_master.csv         # 5 Plants (ID, Name, Region, Max Monthly Units)
|   +-- bom_material.csv         # 201 BOM Mappings (SKU to Fabric Consumption)
|-- pr1_procurement/             # Problem Statement 1 Data
|   |-- supplier_material_contracts.csv # 254 Contracts (Price, Capacity, MOQ, Min/Max Alloc)
|   |-- material_demand_forecast.csv    # 2,000 Period Material Demands
|   |-- supplier_performance_history.csv# 2,000 Historical Performance Records
|   +-- historical_purchase_orders.csv  # 8,000 PO Records for ML Training
+-- p2_sop/                      # Problem Statement 2 Data
    |-- seasonal_sku_demand.csv  # 4,000 SKU Demand Forecasts (24 Periods x 4 Regions)
    |-- current_inventory.csv     # 500 SKU Inventory Balances (5 Location DCs)
    |-- fabric_constraints.csv   # 150 Plant Fabric Allocation Constraints
    |-- plant_production_capacity.csv # 120 Plant Monthly Capacity Records
    |-- historical_sell_through.csv  # 2,600 Weekly Sell-Through Records (52 Weeks)
    |-- historical_markdowns.csv # 2,000 Historical Discount Records
    +-- dc_to_store_logistics.csv# 2,000 DC-to-Store Logistics Routes
```

---

## 5. Software Requirements and Installation

### Prerequisites
- Python 3.10 or higher
- C++ Compiler / Coin-OR Solver binaries (included via PuLP `PULP_CBC_CMD`)

### Dependencies
Install required Python packages:

```bash
pip install -r requirements.txt
```

Core packages used: `streamlit`, `pandas`, `numpy`, `pulp`, `xgboost`, `scikit-learn`, `plotly`.

### Execution
Run the Streamlit application router:

```bash
streamlit run app.py
```

### Demonstration Credentials
The application implements Role-Based Access Control (RBAC). Use the following credentials to authenticate:

| User ID | Password | Assigned Role | Scope of Module Access |
| :--- | :--- | :--- | :--- |
| `admin` | `password` | System Administrator | Full System Access (All Modules) |
| `planner` | `password` | S&OP Planner | Demand & Supply Planning, Markdown Recommender |
| `procurement` | `password` | Procurement Manager | Procurement Optimizer, Supplier Risk Prediction |
| `exec` | `password` | Executive Leader | Executive Summary, What-If Scenario Analysis |

---

## 6. Directory Structure

```
trendwear/
|-- app.py                       # Main Streamlit Application Router & Auth System
|-- generate_data.py             # Synthetic Data Generation Script
|-- requirements.txt             # Environment Dependencies
|-- core/                        # Business Logic & Analytical Engines
|   |-- data_loader.py           # Dataset Ingestion & Caching
|   |-- sop_engine.py            # S&OP MRP & Financial Rollup Engine
|   |-- optimizer.py             # PuLP MILP Procurement Optimization Solver
|   |-- risk_model.py            # XGBoost Regressor & Random Forest Classifier
|   |-- markdown_engine.py       # Sell-Through Analysis & Markdown Engine
|   +-- scenario_engine.py       # What-If Simulation Engine
|-- views/                       # Streamlit UI View Modules
|   |-- 0_Home.py                # Platform Overview Page
|   |-- 1_Executive_Dashboard.py # Executive KPI Summary Page
|   |-- 2_Demand_Supply_Planning.py # S&OP Planning Workspace
|   |-- 3_Procurement_Optimizer.py # MILP Optimization Workspace
|   |-- 4_Risk_Prediction.py     # ML Delay & Risk Workspace
|   |-- 5_Markdown_Recommender.py# Markdown Recommendation Workspace
|   +-- 6_Scenario_Analysis.py   # Simulation Workspace
|-- utils/                       # Utility Helpers & Constants
|   |-- constants.py             # System Domain Constants
|   +-- formatters.py            # Currency & Number Formatting Helpers
+-- hackathon_dataset/           # Partitioned Synthetic CSV Datasets
    |-- shared/
    |-- pr1_procurement/
    +-- p2_sop/
```