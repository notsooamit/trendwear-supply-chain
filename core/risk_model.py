import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, f1_score, classification_report, confusion_matrix
)
import xgboost as xgb
import streamlit as st


def prepare_features(data):
    """
    Build feature matrix from purchase orders + supplier master + performance history.
    Returns X (features), y_delay (regression target), y_risk (classification target),
    and feature_names.
    """
    pos = data["purchase_orders"].copy()
    suppliers = data["suppliers"].copy()
    avg_perf = (
        data["supplier_perf"]
        .groupby("supplier_id")
        .agg(
            avg_otd=("otd_rating_pct", "mean"),
            avg_quality=("quality_pass_rate_pct", "mean"),
            avg_defect_ppm=("defect_ppm", "mean"),
        )
        .reset_index()
    )

    # Merge supplier info
    df = pos.merge(
        suppliers[["supplier_id", "base_risk_factor", "tier_rating", "location"]],
        on="supplier_id", how="left"
    )
    df = df.merge(avg_perf, on="supplier_id", how="left")

    # Fill missing perf data with median
    for col in ["avg_otd", "avg_quality", "avg_defect_ppm"]:
        df[col] = df[col].fillna(df[col].median())

    # Encode categoricals
    le_tier = LabelEncoder()
    df["tier_encoded"] = le_tier.fit_transform(df["tier_rating"])

    le_loc = LabelEncoder()
    df["location_encoded"] = le_loc.fit_transform(df["location"])

    # Extract month from order date
    df["order_month"] = df["order_date"].dt.month

    # Compute order size relative to typical (strain ratio)
    median_qty = df["order_quantity_meters"].median()
    df["qty_strain_ratio"] = df["order_quantity_meters"] / median_qty

    # Interaction features (mirror the delay generation formula)
    df["risk_x_qty"] = df["base_risk_factor"] * df["order_quantity_meters"]
    df["risk_x_lead_time"] = df["base_risk_factor"] * df["contracted_lead_time_days"]
    df["risk_x_quality"] = df["base_risk_factor"] * (100 - df["avg_quality"])

    # Feature columns
    feature_cols = [
        "order_quantity_meters",
        "unit_price",
        "total_po_value",
        "contracted_lead_time_days",
        "base_risk_factor",
        "tier_encoded",
        "location_encoded",
        "avg_otd",
        "avg_quality",
        "avg_defect_ppm",
        "order_month",
        "qty_strain_ratio",
        "risk_x_qty",
        "risk_x_lead_time",
        "risk_x_quality",
    ]

    X = df[feature_cols].values
    y_delay = df["delayed_days"].values
    y_risk = df["risk_category"].values

    return X, y_delay, y_risk, feature_cols, df


@st.cache_resource
def train_delay_model(data):
    """
    Train an XGBoost regressor to predict delivery delay in days.
    Returns the model, test metrics, and feature importances.
    """
    X, y_delay, _, feature_cols, _ = prepare_features(data)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_delay, test_size=0.2, random_state=42
    )

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    metrics = {
        "mae": round(mean_absolute_error(y_test, y_pred), 3),
        "rmse": round(np.sqrt(mean_squared_error(y_test, y_pred)), 3),
        "r2": round(r2_score(y_test, y_pred), 3),
    }

    # Cross-validation
    cv_scores = cross_val_score(model, X, y_delay, cv=5, scoring="r2")
    metrics["cv_r2_mean"] = round(cv_scores.mean(), 3)
    metrics["cv_r2_std"] = round(cv_scores.std(), 3)

    importances = dict(zip(feature_cols, model.feature_importances_))

    return model, metrics, importances, feature_cols, (y_test, y_pred)


@st.cache_resource
def train_risk_model(data):
    """
    Train a Random Forest classifier to predict risk category (Low/Medium/High).
    Returns the model, test metrics, feature importances, and label encoder.
    """
    X, _, y_risk, feature_cols, _ = prepare_features(data)

    le = LabelEncoder()
    y_encoded = le.fit_transform(y_risk)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred), 3),
        "f1_macro": round(f1_score(y_test, y_pred, average="macro"), 3),
        "f1_weighted": round(f1_score(y_test, y_pred, average="weighted"), 3),
    }

    # Per-class report
    class_report = classification_report(
        y_test, y_pred, target_names=le.classes_, output_dict=True
    )

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)

    importances = dict(zip(feature_cols, model.feature_importances_))

    return model, metrics, importances, feature_cols, le, class_report, cm, (y_test, y_pred)


def predict_new_po(delay_model, risk_model, risk_le, feature_cols, data,
                   supplier_id, fabric_id, order_qty):
    """
    Predict delay and risk category for a new purchase order.
    """
    suppliers = data["suppliers"]
    avg_perf = (
        data["supplier_perf"]
        .groupby("supplier_id")
        .agg(
            avg_otd=("otd_rating_pct", "mean"),
            avg_quality=("quality_pass_rate_pct", "mean"),
            avg_defect_ppm=("defect_ppm", "mean"),
        )
        .reset_index()
    )

    sup_row = suppliers[suppliers["supplier_id"] == supplier_id].iloc[0]
    contracts = data["contracts"]
    contract_row = contracts[
        (contracts["supplier_id"] == supplier_id) & (contracts["fabric_id"] == fabric_id)
    ]

    if contract_row.empty:
        return None

    contract_row = contract_row.iloc[0]

    perf_row = avg_perf[avg_perf["supplier_id"] == supplier_id]
    if perf_row.empty:
        avg_otd = 90.0
        avg_quality = 95.0
        avg_defect = 300
    else:
        perf_row = perf_row.iloc[0]
        avg_otd = perf_row["avg_otd"]
        avg_quality = perf_row["avg_quality"]
        avg_defect = perf_row["avg_defect_ppm"]

    # Encode categoricals using same scheme as training
    tier_map = {"Tier 1": 0, "Tier 2": 1, "Tier 3": 2}
    location_list = sorted(suppliers["location"].unique())
    loc_map = {loc: i for i, loc in enumerate(location_list)}

    median_qty = data["purchase_orders"]["order_quantity_meters"].median()
    unit_price = contract_row["unit_price"]

    risk_factor = sup_row["base_risk_factor"]
    lead_time = contract_row["contracted_lead_time_days"]

    features = np.array([[
        order_qty,
        unit_price,
        order_qty * unit_price,
        lead_time,
        risk_factor,
        tier_map.get(sup_row["tier_rating"], 1),
        loc_map.get(sup_row["location"], 0),
        avg_otd,
        avg_quality,
        avg_defect,
        6,  # default month (June)
        order_qty / median_qty,
        risk_factor * order_qty,        # risk_x_qty
        risk_factor * lead_time,        # risk_x_lead_time
        risk_factor * (100 - avg_quality),  # risk_x_quality
    ]])

    predicted_delay = max(0, round(delay_model.predict(features)[0], 1))
    predicted_risk_idx = risk_model.predict(features)[0]
    predicted_risk = risk_le.inverse_transform([predicted_risk_idx])[0]

    return {
        "supplier_id": supplier_id,
        "supplier_name": sup_row["supplier_name"],
        "fabric_id": fabric_id,
        "order_quantity": order_qty,
        "contracted_lead_time": contract_row["contracted_lead_time_days"],
        "predicted_delay_days": predicted_delay,
        "predicted_total_lead_time": contract_row["contracted_lead_time_days"] + predicted_delay,
        "predicted_risk_category": predicted_risk,
        "supplier_risk_factor": sup_row["base_risk_factor"],
        "avg_otd": round(avg_otd, 1),
        "avg_quality": round(avg_quality, 1),
    }
