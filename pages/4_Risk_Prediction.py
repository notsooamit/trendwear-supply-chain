import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from core.data_loader import load_all_data, get_supplier_names_map, get_fabric_names_map
from core.risk_model import train_delay_model, train_risk_model, predict_new_po

st.set_page_config(page_title="Risk Prediction", layout="wide")
st.title("Risk Prediction (PR1)")

data = load_all_data()
sup_names = get_supplier_names_map()
fab_names = get_fabric_names_map()

# Train models (cached)
with st.spinner("Training models (first run only)..."):
    delay_model, delay_metrics, delay_importances, feature_cols, delay_test = train_delay_model(data)
    risk_model, risk_metrics, risk_importances, _, risk_le, class_report, cm, risk_test = train_risk_model(data)

# Section 1: Model Performance
st.subheader("Model Performance")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Delay Prediction (XGBoost Regressor)**")
    m = delay_metrics
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("MAE", f"{m['mae']:.3f} days")
    mcol2.metric("RMSE", f"{m['rmse']:.3f} days")
    mcol3.metric("R²", f"{m['r2']:.3f}")
    mcol4.metric("CV R² (5-fold)", f"{m['cv_r2_mean']:.3f} ± {m['cv_r2_std']:.3f}")

    # Predicted vs Actual scatter
    y_test, y_pred = delay_test
    sample_idx = np.random.RandomState(42).choice(len(y_test), min(500, len(y_test)), replace=False)
    fig = px.scatter(x=y_test[sample_idx], y=y_pred[sample_idx],
                     labels={"x": "Actual Delay (days)", "y": "Predicted Delay (days)"},
                     title="Predicted vs Actual Delay")
    fig.add_trace(go.Scatter(x=[0, max(y_test)], y=[0, max(y_test)],
                             mode="lines", line=dict(dash="dash", color="red"),
                             name="Perfect prediction"))
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

with col2:
    st.markdown("**Risk Classification (Random Forest)**")
    m = risk_metrics
    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("Accuracy", f"{m['accuracy']:.3f}")
    mcol2.metric("F1 (Macro)", f"{m['f1_macro']:.3f}")
    mcol3.metric("F1 (Weighted)", f"{m['f1_weighted']:.3f}")

    # Confusion matrix
    fig = px.imshow(cm,
                    x=risk_le.classes_.tolist(),
                    y=risk_le.classes_.tolist(),
                    text_auto=True,
                    labels=dict(x="Predicted", y="Actual", color="Count"),
                    title="Confusion Matrix",
                    color_continuous_scale="Blues")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

st.markdown("---")

# Section 2: Feature Importance
st.subheader("Feature Importance")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Delay Model**")
    imp_df = pd.DataFrame(
        sorted(delay_importances.items(), key=lambda x: x[1], reverse=True),
        columns=["Feature", "Importance"]
    )
    fig = px.bar(imp_df, x="Importance", y="Feature", orientation="h",
                 color="Importance", color_continuous_scale="Blues")
    fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

with col2:
    st.markdown("**Risk Classification Model**")
    imp_df = pd.DataFrame(
        sorted(risk_importances.items(), key=lambda x: x[1], reverse=True),
        columns=["Feature", "Importance"]
    )
    fig = px.bar(imp_df, x="Importance", y="Feature", orientation="h",
                 color="Importance", color_continuous_scale="Reds")
    fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, width='stretch')

st.markdown("---")

# Section 3: Predict New PO
st.subheader("Predict Risk for New Purchase Order")

# Get available supplier-fabric pairs from contracts
contracts = data["contracts"]
available_suppliers = sorted(contracts["supplier_id"].unique().tolist())

col1, col2, col3 = st.columns(3)
with col1:
    selected_supplier = st.selectbox(
        "Supplier",
        available_suppliers,
        format_func=lambda x: f"{x} - {sup_names.get(x, x)}"
    )
with col2:
    # Filter fabrics for selected supplier
    sup_fabrics = contracts[contracts["supplier_id"] == selected_supplier]["fabric_id"].unique().tolist()
    selected_fabric = st.selectbox(
        "Fabric",
        sorted(sup_fabrics),
        format_func=lambda x: f"{x} - {fab_names.get(x, x)}"
    )
with col3:
    order_qty = st.number_input("Order Quantity (meters)", min_value=500, max_value=50000,
                                value=5000, step=500)

if st.button("Predict", type="primary"):
    prediction = predict_new_po(
        delay_model, risk_model, risk_le, feature_cols, data,
        selected_supplier, selected_fabric, order_qty
    )

    if prediction is None:
        st.error("No contract found for this supplier-fabric combination.")
    else:
        st.markdown("---")
        st.subheader("Prediction Results")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Predicted Delay", f"{prediction['predicted_delay_days']:.1f} days")
        col2.metric("Risk Category", prediction["predicted_risk_category"])
        col3.metric("Total Lead Time", f"{prediction['predicted_total_lead_time']} days")
        col4.metric("Supplier Risk Factor", f"{prediction['supplier_risk_factor']:.2f}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Supplier", prediction["supplier_name"])
        col2.metric("Avg OTD", f"{prediction['avg_otd']}%")
        col3.metric("Avg Quality", f"{prediction['avg_quality']}%")

st.markdown("---")

# Section 4: Supplier Risk Heatmap
st.subheader("Supplier Risk Profile")
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

fig = px.scatter(risk_by_supplier, x="avg_delay", y="otd_rate",
                 size="total_orders", color="high_risk_pct",
                 hover_name="supplier_name",
                 labels={"avg_delay": "Avg Delay (days)", "otd_rate": "OTD Rate %",
                         "high_risk_pct": "High Risk %"},
                 color_continuous_scale="RdYlGn_r",
                 title="Supplier Risk Map")
fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
st.plotly_chart(fig, width='stretch')

with st.expander("Supplier Risk Table"):
    st.dataframe(
        risk_by_supplier[["supplier_name", "total_orders", "avg_delay",
                          "otd_rate", "high_risk_pct"]].sort_values(
            "avg_delay", ascending=False
        ),
        width='stretch'
    )
