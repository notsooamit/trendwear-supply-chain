import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from core.data_loader import load_all_data, get_supplier_names_map, get_fabric_names_map
from core.risk_model import train_delay_model, train_risk_model, predict_new_po
from utils.formatters import format_number, format_pct

st.set_page_config(page_title="Supplier Risk Prediction", layout="wide")
st.title("Machine Learning Risk Prediction Pipeline")
st.caption("Predicting purchase order delivery delays and evaluating supplier risk categories using XGBoost Regressor and Random Forest Classifier models.")

data = load_all_data()
sup_names = get_supplier_names_map()
fab_names = get_fabric_names_map()

with st.spinner("Training predictive models on 8,000 purchase order records..."):
    delay_model, delay_metrics, delay_importances, feature_cols, delay_test = train_delay_model(data)
    risk_model, risk_metrics, risk_importances, _, risk_le, class_report, cm, risk_test = train_risk_model(data)

st.subheader("1. Model Performance and Evaluation Metrics")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Delay Regression Model (XGBoost Regressor)**")
    m = delay_metrics
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("MAE", f"{m['mae']:.2f} d")
    mcol2.metric("RMSE", f"{m['rmse']:.2f} d")
    mcol3.metric("R² Score", f"{m['r2']:.3f}")
    mcol4.metric("CV R²", f"{m['cv_r2_mean']:.3f}")

    y_test, y_pred = delay_test
    sample_idx = np.random.RandomState(42).choice(len(y_test), min(400, len(y_test)), replace=False)
    fig = px.scatter(
        x=y_test[sample_idx], y=y_pred[sample_idx],
        labels={"x": "Actual Delay (Days)", "y": "Predicted Delay (Days)"},
        title="Actual vs Predicted Delivery Delay (Test Partition)"
    )
    fig.add_trace(go.Scatter(
        x=[0, max(y_test)], y=[0, max(y_test)],
        mode="lines", line=dict(dash="dash", color="#bb0000"),
        name="Parity Line"
    ))
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("**Risk Classification Model (Random Forest Classifier)**")
    m = risk_metrics
    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("Accuracy", format_pct(m["accuracy"] * 100))
    mcol2.metric("F1 (Macro)", f"{m['f1_macro']:.3f}")
    mcol3.metric("F1 (Weighted)", f"{m['f1_weighted']:.3f}")

    fig = px.imshow(
        cm,
        x=risk_le.classes_.tolist(),
        y=risk_le.classes_.tolist(),
        text_auto=True,
        labels=dict(x="Predicted Class", y="Actual Class", color="Sample Count"),
        title="Classification Confusion Matrix",
        color_continuous_scale="Blues"
    )
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("2. Feature Importance Metrics")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Delay Regressor Feature Importances**")
    imp_df = pd.DataFrame(
        sorted(delay_importances.items(), key=lambda x: x[1], reverse=True),
        columns=["Feature", "Importance Score"]
    )
    fig = px.bar(
        imp_df, x="Importance Score", y="Feature", orientation="h",
        color="Importance Score", color_continuous_scale="Blues"
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("**Risk Classifier Feature Importances**")
    imp_df = pd.DataFrame(
        sorted(risk_importances.items(), key=lambda x: x[1], reverse=True),
        columns=["Feature", "Importance Score"]
    )
    fig = px.bar(
        imp_df, x="Importance Score", y="Feature", orientation="h",
        color="Importance Score", color_continuous_scale="Reds"
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("3. Pre-Commitment Purchase Order Risk Simulation")

contracts = data["contracts"]
available_suppliers = sorted(contracts["supplier_id"].unique().tolist())

col1, col2, col3 = st.columns(3)
with col1:
    selected_supplier = st.selectbox(
        "Supplier Entity",
        available_suppliers,
        format_func=lambda x: f"{x} - {sup_names.get(x, x)}"
    )
with col2:
    sup_fabrics = contracts[contracts["supplier_id"] == selected_supplier]["fabric_id"].unique().tolist()
    selected_fabric = st.selectbox(
        "Target Fabric Material",
        sorted(sup_fabrics),
        format_func=lambda x: f"{x} - {fab_names.get(x, x)}"
    )
with col3:
    order_qty = st.number_input("Order Volume (Meters)", min_value=500, max_value=50000, value=5000, step=500)

if st.button("Evaluate PO Risk Profile", type="primary"):
    prediction = predict_new_po(
        delay_model, risk_model, risk_le, feature_cols, data,
        selected_supplier, selected_fabric, order_qty
    )

    if prediction is None:
        st.error("No valid contract mapping found for the selected supplier and fabric combination.")
    else:
        st.markdown("---")
        st.subheader("Predictive Assessment Results")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Predicted Delay", f"{prediction['predicted_delay_days']:.1f} days")
        col2.metric("Assigned Risk Level", prediction["predicted_risk_category"])
        col3.metric("Estimated Total Lead Time", f"{prediction['predicted_total_lead_time']} days")
        col4.metric("Supplier Risk Coefficient", f"{prediction['supplier_risk_factor']:.2f}")

st.markdown("---")

st.subheader("4. Supplier Risk Mapping Overview")
pos = data["purchase_orders"]
risk_by_supplier = pos.groupby("supplier_id").agg(
    total_orders=("po_id", "count"),
    avg_delay=("delayed_days", "mean"),
    otd_rate=("is_on_time", "mean"),
    high_risk_pct=("risk_category", lambda x: (x == "High").mean()),
).reset_index()
risk_by_supplier["supplier_name"] = risk_by_supplier["supplier_id"].map(sup_names)
risk_by_supplier["otd_rate"] = (risk_by_supplier["otd_rate"] * 100).round(1)
risk_by_supplier["high_risk_pct"] = (risk_by_supplier["high_risk_pct"] * 100).round(1)

fig = px.scatter(
    risk_by_supplier, x="avg_delay", y="otd_rate",
    size="total_orders", color="high_risk_pct",
    hover_name="supplier_name",
    labels={
        "avg_delay": "Avg Delay (Days)",
        "otd_rate": "On-Time Delivery (%)",
        "high_risk_pct": "High Risk Order Share (%)"
    },
    color_continuous_scale="RdYlGn_r",
    title="Supplier Performance Matrix (Delay vs OTD Rate)"
)
fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
st.plotly_chart(fig, use_container_width=True)

with st.expander("Detailed Supplier Risk Table"):
    st.dataframe(
        risk_by_supplier[["supplier_name", "total_orders", "avg_delay",
                          "otd_rate", "high_risk_pct"]].sort_values(
            "avg_delay", ascending=False
        ),
        use_container_width=True
    )
