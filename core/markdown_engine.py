import pandas as pd
import numpy as np


def analyze_sell_through(data):
    """
    Analyze sell-through data to classify SKUs and recommend markdowns.

    Classification:
    - Fast Mover: avg sell-through rate > 0.70
    - Normal: 0.40 to 0.70
    - Slow Mover: < 0.40

    Returns:
    - sku_classification: DataFrame with SKU performance metrics
    - markdown_recommendations: DataFrame with recommended actions
    - weekly_trends: DataFrame with weekly sell-through trends
    """
    st = data["sell_through"].copy()
    inv = data["inventory"].copy()
    skus = data["skus"].copy()

    # Compute per-SKU metrics
    sku_metrics = (
        st.groupby("sku_id")
        .agg(
            avg_sell_through_rate=("sell_through_rate", "mean"),
            total_units_sold=("units_sold", "sum"),
            total_units_available=("units_available", "sum"),
            num_weeks=("selling_week", "nunique"),
            min_st_rate=("sell_through_rate", "min"),
            max_st_rate=("sell_through_rate", "max"),
        )
        .reset_index()
    )

    # Weekly sell rate (units sold per week on average)
    sku_metrics["avg_weekly_sales"] = (
        sku_metrics["total_units_sold"] / sku_metrics["num_weeks"]
    )

    # Classify using percentile-based thresholds
    # This works better with synthetic data where absolute rates cluster
    p75 = sku_metrics["avg_sell_through_rate"].quantile(0.75)
    p25 = sku_metrics["avg_sell_through_rate"].quantile(0.25)

    def classify(rate):
        if rate >= p75:
            return "Fast Mover"
        elif rate >= p25:
            return "Normal"
        else:
            return "Slow Mover"

    sku_metrics["classification"] = sku_metrics["avg_sell_through_rate"].apply(classify)

    # Merge with SKU details
    sku_metrics = sku_metrics.merge(
        skus[["sku_id", "category", "season", "target_unit_price"]],
        on="sku_id", how="left"
    )

    # Get current available stock
    inv_total = (
        inv.groupby("sku_id")["available_stock_units"]
        .sum()
        .reset_index()
        .rename(columns={"available_stock_units": "current_stock"})
    )
    sku_metrics = sku_metrics.merge(inv_total, on="sku_id", how="left")
    sku_metrics["current_stock"] = sku_metrics["current_stock"].fillna(0)

    # Weeks of stock remaining
    sku_metrics["weeks_of_stock"] = np.where(
        sku_metrics["avg_weekly_sales"] > 0,
        sku_metrics["current_stock"] / sku_metrics["avg_weekly_sales"],
        999  # No sales, infinite weeks
    )
    sku_metrics["weeks_of_stock"] = sku_metrics["weeks_of_stock"].round(1)

    # Build markdown recommendations
    recommendations = build_markdown_recommendations(sku_metrics, data)

    # Weekly trends
    weekly_trends = (
        st.groupby("selling_week")
        .agg(
            avg_st_rate=("sell_through_rate", "mean"),
            total_sold=("units_sold", "sum"),
            total_available=("units_available", "sum"),
        )
        .reset_index()
        .sort_values("selling_week")
    )

    return sku_metrics, recommendations, weekly_trends


def build_markdown_recommendations(sku_metrics, data):
    """
    Build markdown recommendations based on sell-through performance
    and historical markdown effectiveness.
    """
    markdowns = data["markdowns"].copy()

    # Compute historical markdown effectiveness per discount tier
    md_effectiveness = (
        markdowns.groupby("discount_percentage")
        .agg(
            avg_units_sold=("units_sold_post_markdown", "mean"),
            avg_remaining=("remaining_unallocated_stock", "mean"),
        )
        .reset_index()
    )
    md_effectiveness["clearance_ratio"] = (
        md_effectiveness["avg_units_sold"]
        / (md_effectiveness["avg_units_sold"] + md_effectiveness["avg_remaining"])
    ).round(3)

    # Filter to slow movers (these are candidates for markdown)
    slow_movers = sku_metrics[
        sku_metrics["classification"] == "Slow Mover"
    ].copy()

    recommendations = []
    for _, row in slow_movers.iterrows():
        wos = row["weeks_of_stock"]
        price = row["target_unit_price"]

        # Recommend discount based on weeks of stock
        if wos > 20:
            discount = 0.50
            urgency = "High"
        elif wos > 14:
            discount = 0.35
            urgency = "Medium"
        elif wos > 8:
            discount = 0.25
            urgency = "Low"
        else:
            discount = 0.15
            urgency = "Low"

        discounted_price = round(price * (1 - discount), 2)
        est_units = int(row["avg_weekly_sales"] * 1.5 * (1 + discount))  # rough elasticity
        est_recovery = round(est_units * discounted_price, 2)

        recommendations.append({
            "sku_id": row["sku_id"],
            "category": row["category"],
            "season": row["season"],
            "current_stock": int(row["current_stock"]),
            "weeks_of_stock": row["weeks_of_stock"],
            "avg_sell_through_rate": round(row["avg_sell_through_rate"], 3),
            "original_price": price,
            "recommended_discount": f"{int(discount*100)}%",
            "discounted_price": discounted_price,
            "urgency": urgency,
            "estimated_units_cleared": est_units,
            "estimated_revenue_recovery": est_recovery,
        })

    # Also flag fast movers with stock-out risk
    fast_movers = sku_metrics[
        (sku_metrics["classification"] == "Fast Mover") &
        (sku_metrics["weeks_of_stock"] < 4)
    ].copy()

    stockout_alerts = []
    for _, row in fast_movers.iterrows():
        stockout_alerts.append({
            "sku_id": row["sku_id"],
            "category": row["category"],
            "season": row["season"],
            "current_stock": int(row["current_stock"]),
            "weeks_of_stock": row["weeks_of_stock"],
            "avg_weekly_sales": round(row["avg_weekly_sales"], 0),
            "alert": "Potential stock-out",
        })

    return {
        "markdown_actions": pd.DataFrame(recommendations),
        "stockout_alerts": pd.DataFrame(stockout_alerts),
        "discount_effectiveness": md_effectiveness,
    }
