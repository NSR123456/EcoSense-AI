import streamlit as st
from src.evaluation.streaming_evaluator import StreamingEvaluator
import pandas as pd

def render_model_comparison(selected_ai_model: str = "ollama"):
    st.markdown("## Model Comparison — AI Model Comparison")
    st.write(
        "Compare your selected AI model versus Llama 3, Qwen, and Mistral. "
        "This comparison highlights the active model selection used in the dashboard and presents the same evaluation workflow across each model label."
    )

    available_models = ["ollama", "llama3.2:1b", "qwen-7b", "mistral-7b"]
    comparison_models = [selected_ai_model] + [m for m in available_models if m != selected_ai_model]

    st.markdown("### Model lineup")
    lineups = pd.DataFrame([
        {"Model": model, "Role": "Selected model" if model == selected_ai_model else "Alternative model"}
        for model in comparison_models
    ])
    st.table(lineups)
    st.write("Use this model lineup to compare the selected model against the popular alternatives in the dashboard.")

    presets = {
        "Z-Score (threshold=2.0)": {"threshold": 2.0, "window": 20},
        "Z-Score (threshold=2.5)": {"threshold": 2.5, "window": 20},
        "Z-Score (threshold=1.8)": {"threshold": 1.8, "window": 20},
    }

    cols = st.columns(3)
    with cols[0]:
        selected_presets = st.multiselect("Select detector presets to compare", list(presets.keys()), default=list(presets.keys())[:2])
    with cols[1]:
        num_runs = st.number_input("Evaluation runs", min_value=1, max_value=20, value=3)
    with cols[2]:
        samples = st.number_input("Samples per run", min_value=100, max_value=5000, value=900, step=100)

    injection_rate = st.slider("Fault injection rate", min_value=0.01, max_value=0.5, value=0.2)

    if not selected_presets:
        st.info("Select at least one preset to run comparison")
        return

    if st.button("Run Comparison", type="primary"):
        results = []
        for model_name in comparison_models:
            for detector_name in selected_presets:
                cfg = presets[detector_name]
                evaluator = StreamingEvaluator(detector_threshold=cfg["threshold"])
                agg = evaluator.evaluate_multiple_runs(num_runs=num_runs, num_samples=samples, injection_rate=injection_rate)
                row = {
                    "AI_Model": model_name,
                    "Detector": detector_name,
                    "Precision": agg.get("average_precision"),
                    "Recall": agg.get("average_recall"),
                    "F1": agg.get("average_f1_score"),
                    "AUC": agg.get("average_roc_auc", None),
                    "Latency_ms": agg.get("average_detection_latency_ms"),
                    "Runtime_ms": agg.get("average_total_runtime_ms"),
                }
                results.append((row, agg))

        df = pd.DataFrame([r[0] for r in results])
        st.markdown("### Summary Metrics")
        st.dataframe(df.style.format({"Precision": "{:.3f}", "Recall": "{:.3f}", "F1": "{:.3f}"}), use_container_width=True)

        st.markdown("### Detailed Runs")
        for (row, agg) in results:
            st.markdown(f"#### {row['AI_Model']} / {row['Detector']}")
            st.json(agg)

        # Simple bar chart for comparison
        st.markdown("### Visual Comparison")
        chart_df = df.set_index(["AI_Model", "Detector"]).loc[:, ["Precision", "Recall", "F1"]]
        st.bar_chart(chart_df)
