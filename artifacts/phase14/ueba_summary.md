# FinGuard AI — Phase 14 UEBA & Anomaly Detection Summary

- **Generated Timestamp:** 2026-11-13 05:20:02 UTC
- **Total Training & Evaluation Events:** 5,000
- **Distinct Behavioral Entities:** 100
- **Ground Truth Injected Anomalies:** 384 (7.68%)

## Model Performance Metrics

| Metric | Score |
|---|---|
| **ROC-AUC** | `1.0000` |
| **Anomaly Precision** | `0.0768` |
| **Anomaly Recall** | `1.0000` |
| **Anomaly F1-Score** | `0.1426` |
| **Normal Class F1-Score** | `0.0000` |

## Behavioral Features Evaluated
- `amount`: Raw point-in-time value.
- `amount_deviation_ratio`: Amount divided by historical mean.
- `amount_z_score`: Standard deviations from entity average.
- `is_off_hours`: Binary indicator outside regular user hours.
- `is_new_device`: Device fingerprint unrecognized in entity baseline.
- `is_new_ip`: Unrecognized IP address prefix.
- `is_new_city`: Geolocation deviation indicator.
- `velocity_1h` & `velocity_24h`: Transaction burst frequency.
- `impossible_travel_flag`: Geographically disjointed activity under velocity thresholds.

## Correlation & Threat Fusion
Top 50 high-deviation events were fused with Phase 6/7 Fraud Probability ($P_{\text{fraud}}$), Phase 13 Threat Intel IOC Reputation ($R_{\text{ioc}}$), and Phase 12 Cloud Finding Severity ($Sev_{\text{cloud}}$). Output saved to `entity_risk_report.json`.
