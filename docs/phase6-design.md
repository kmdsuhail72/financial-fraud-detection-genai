# FinGuard AI — Phase 6: Real-Time Fraud Detection Machine Learning Platform

## 1. Executive Summary

Phase 6 implements the machine learning engine for FinGuard AI. The system learns multi-dimensional fraud and anomaly patterns from the 20,000 synthetic banking transactions produced in Phase 2, integrates supervised classification with unsupervised anomaly detection, and exposes a high-throughput, sub-10ms real-time scoring interface.

A fundamental design principle is that the ML model estimates transaction risk without independently executing irreversible account terminations or ledger reversals. Configurable thresholds and downstream human investigation workflows govern transaction holds, alerts, and approvals.

---

## 2. Architecture & Inference Pipeline

```
+-----------------------------------------------------------------------------------------+
|                               Real-Time Scoring Workflow                                |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   Inbound Event (HTTP / Kinesis / Streaming)                                            |
|        │                                                                                |
|        ▼                                                                                |
|   +───────────────────────────────────────────────────────────+                         |
|   | FeaturePreprocessor                                       |                         |
|   |  - Alias normalization (e.g. amount -> transaction_amount)|                         |
|   |  - Missing feature imputation (historical medians)        |                         |
|   |  - Standard scaling & schema alignment                    |                         |
|   +─────────────────────────────┬─────────────────────────────+                         |
|                                 │ Aligned & Scaled Matrix                               |
|                ┌────────────────┴────────────────┐                                      |
|                ▼                                 ▼                                      |
|   +──────────────────────────+     +──────────────────────────+                         |
|   | Supervised Classifier    |     | Unsupervised Detector    |                         |
|   | Random Forest / XGBoost  |     | Isolation Forest         |                         |
|   |                          |     |                          |                         |
|   | -> P(Fraud) in [0.0, 1.0]|     | -> Anomaly A in [0.0,1.0]|                         |
|   +────────────┬─────────────+     +─────────────┬────────────+                         |
|                │                                 │                                      |
|                └────────────────┬────────────────┘                                      |
|                                 ▼                                                       |
|   +───────────────────────────────────────────────────────────+                         |
|   | Composite Risk Engine                                     |                         |
|   |  Risk Score R = 0.65 * P(Fraud) + 0.35 * A(Anomaly)       |                         |
|   |                                                           |                         |
|   |  Tier Classification:                                     |                         |
|   |   - R >= 0.80: CRITICAL (Automated Hold / Urgent Case)    |                         |
|   |   - R >= 0.60: HIGH (Flagged for Investigator Queue)      |                         |
|   |   - R >= 0.35: MEDIUM (Step-up Auth / Enhanced Monitor)   |                         |
|   |   - R <  0.35: LOW (Immediate Approval)                  |                         |
|   +─────────────────────────────┬─────────────────────────────+                         |
|                                 ▼                                                       |
|   FastAPI / SageMaker JSON Response                                                     |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Key Machine Learning Engineering Decisions

### 3.1 Strict Target Leakage Prevention
To guarantee valid generalization, ground truth indicators (`is_fraud`, `fraud_scenario`, `scenario_name`, `label`, `is_flagged`) are strictly isolated from the feature matrix $X$ during data ingestion. Features are computed strictly using transaction history known *prior to or at the transaction timestamp*.

### 3.2 Supervised Classifier with Class Imbalance Handling
- **Random Forest:** Trained with `class_weight="balanced"` to balance majority normal transactions (~98%) against minority fraud attacks (~2%).
- **XGBoost:** Configured with `scale_pos_weight = N_neg / N_pos` to optimize the gradient loss across rare fraud attacks.

### 3.3 Unsupervised Anomaly Detection for Zero-Day Attacks
Supervised models only recognize historical attack signatures. The `IsolationForest` identifies outliers and previously unobserved transaction behaviors without labels. The raw decision function is normalized to $[0.0, 1.0]$:
$$A(x) = \text{clip}\left(\frac{\text{raw}_{\max} - s(x)}{\text{raw}_{\max} - \text{raw}_{\min}}, 0.0, 1.0\right)$$

### 3.4 Threshold Tuning on Validation Holdout
Standard 0.5 classification cutoffs are suboptimal for highly imbalanced fraud detection. We evaluate thresholds from 0.01 to 0.99 on the validation set across 4 optimization strategies:
1. **Best F1:** Harmonic mean of precision and recall.
2. **Cost-Optimal Threshold:** Minimizes the business cost function:
   $$\text{Cost} = C_{\text{FN}} \cdot \text{FN} + C_{\text{FP}} \cdot \text{FP}$$
   where missed fraud costs $C_{\text{FN}} = \$500$ (chargeback, ledger loss) and false positive alerts cost $C_{\text{FP}} = \$25$ (compliance investigator review overhead).
3. **High-Recall ($\ge 0.90$):** Catches $\ge 90\%$ of fraud with highest available precision.
4. **High-Precision ($\ge 0.90$):** Used for automated blocking policies with $< 10\%$ false positive rate.

---

## 4. Model Artifacts & Governance

Every training run writes 5 audit artifacts to `artifacts/`:
1. `model.joblib`: Complete serializable `EnsembleFraudModel` bundle containing preprocessor, supervised model, isolation forest, and threshold policy.
2. `metrics.json`: Train, validation, and held-out test evaluation metrics (Precision, Recall, F1, ROC-AUC, PR-AUC, Confusion Matrix, Brier score).
3. `feature_manifest.json`: Feature registry listing names, aliases, types, default values, and distribution statistics.
4. `thresholds.json`: Candidate cutoffs for F1, cost, high recall, and high precision.
5. `model_card.json`: Machine Learning Model Card complying with financial risk governance (SR 11-7 model risk management).

---

## 5. Model Performance Benchmark (Held-out Test Set)

| Metric | Random Forest | XGBoost | Target |
| :--- | :--- | :--- | :--- |
| **ROC-AUC** | **0.9817** | **0.9737** | $\ge 0.95$ |
| **PR-AUC** | **0.8909** | **0.8747** | $\ge 0.80$ |
| **Precision** | **90.74%** | **87.27%** | $\ge 85.0\%$ |
| **Recall** | **81.67%** | **80.00%** | $\ge 75.0\%$ |
| **F1-Score** | **0.8596** | **0.8348** | $\ge 0.80$ |
| **False Positives** | **5 / 2,940** | **7 / 2,940** | $< 1\%$ |

---

## 6. AWS SageMaker Integration

The platform provides cloud training and hosting pathways:
- `ml/sagemaker/train_entrypoint.py`: Docker container entrypoint reading from `/opt/ml/input/data/train` and exporting to `/opt/ml/model/`.
- `ml/sagemaker/inference_handler.py`: Standard SageMaker endpoint handler implementing `model_fn`, `input_fn`, `predict_fn`, and `output_fn`.
- `infrastructure/terraform/modules/sagemaker/`: Terraform infrastructure defining the S3 model artifacts bucket, IAM execution role, and optional real-time endpoint configuration.
