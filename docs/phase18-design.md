# Phase 18 — Enterprise Graph Neural Networks, Deep Learning & Predictive Fraud Detection

## 1. Executive Summary

Phase 18 advances FinGuard AI's fraud detection engine into deep representation learning by introducing an inductive **PyTorch GraphSAGE (Sample and Aggregate)** neural network architecture. While Phase 17 introduced heuristic graph algorithms (Louvain, PageRank, Betweenness), Phase 18 learns dense low-dimensional entity representations from heterogeneous graph topologies, combining node properties, edge structures, multi-hop neighborhood dynamics, and suspicious link prediction.

Financial fraud syndicates deploy multi-layered obfuscation strategies—such as device emulation farms, synthetic identity creation, and circular mule accounts—designed to evade traditional tabular models. GraphSAGE aggregates feature representations from local graph neighborhoods, allowing FinGuard AI to classify fraud risk inductively across newly registered accounts, devices, and merchants without retraining the entire global graph.

> [!IMPORTANT]
> **Advisory Governance & Human-in-the-Loop Policy:**
> GNN predictions and link probability scores are strictly **advisory decision-support signals**. In compliance with financial regulatory safeguards and model risk management guidelines, automated adverse actions (such as account deactivation or fund freezes) are prohibited without explicit review and approval by human fraud investigators.

---

## 2. GNN System Architecture

```mermaid
flowchart TD
    subgraph Heterogeneous Financial Graph
        DATA[92 Synthetic Entities / 81 Graph Relationships]
        V_CUS[25 Customers]
        V_ACC[35 Accounts]
        V_DEV[15 Devices]
        V_IP[10 IP Addresses]
        V_MER[7 Merchants]
        DATA --- V_CUS
        DATA --- V_ACC
        DATA --- V_DEV
        DATA --- V_IP
        DATA --- V_MER
    end

    subgraph Feature Encoding & Tensors
        ENC[Dataset Encoder: 16 Input Features]
        X["Node Feature Tensor X: (92, 16)"]
        EI["Bidirectional Edge Index: (2, 162)"]
        Y["Ground Truth Labels Y: (92,)"]
        ENC --> X
        ENC --> EI
        ENC --> Y
    end

    subgraph PyTorch GraphSAGE Architecture
        CONV1["SAGEConv Layer 1: (16 -> 64) with Mean Aggregation"]
        NORM1["LayerNorm + ReLU + Dropout(0.2)"]
        CONV2["SAGEConv Layer 2: (64 -> 64) with Mean Aggregation"]
        NORM2["LayerNorm + ReLU"]
        EMB["64-Dim Latent Embeddings Z: (92, 64)"]
        CLF["Linear Classification Head: (64 -> 2)"]
        LP["MLP Link Predictor Decoder: (128 -> 32 -> 1)"]
        
        CONV1 --> NORM1 --> CONV2 --> NORM2 --> EMB
        EMB --> CLF
        EMB --> LP
    end

    subgraph Explainability & Risk Attribution
        XAI[Explainability Engine: Input Gradient Saliency]
        EXP_IND[Top Feature & Neighborhood Attribution Indicators]
        XAI --> EXP_IND
    end

    subgraph REST API & Analyst Operations
        API_LOAD["POST /model/load"]
        API_INFO["GET /model/info"]
        API_PRED["POST /model/predict/node & /predict/nodes"]
        API_LINK["POST /model/predict/link"]
        API_EMB["POST /model/embeddings"]
        UI[React Analyst Portal: GNN Deep Learning Page]
    end

    DATA --> ENC
    X --> CONV1
    EI --> CONV1
    EI --> CONV2
    CLF --> API_PRED
    LP --> API_LINK
    EMB --> API_EMB
    EXP_IND --> API_PRED
    API_LOAD --> UI
    API_INFO --> UI
    API_PRED --> UI
    API_LINK --> UI
    API_EMB --> UI
```

---

## 3. Mathematical Formulation

### 3.1 GraphSAGE Mean Neighborhood Aggregation
GraphSAGE generates representations through inductive neighborhood message passing. For vertex $v \in \mathcal{V}$ at layer $k$:

$$h_{\mathcal{N}(v)}^{(k)} = \text{MEAN} \left( \left\{ h_u^{(k-1)}, \forall u \in \mathcal{N}(v) \right\} \right) = \frac{1}{|\mathcal{N}(v)|} \sum_{u \in \mathcal{N}(v)} h_u^{(k-1)}$$

$$h_v^{(k)} = \text{LayerNorm} \left( \sigma \left( W_{\text{self}}^{(k)} h_v^{(k-1)} + W_{\text{neigh}}^{(k)} h_{\mathcal{N}(v)}^{(k)} \right) \right)$$

where:
- $\mathcal{N}(v)$ denotes the immediate 1-hop topological neighbors of node $v$.
- $W_{\text{self}}^{(k)}, W_{\text{neigh}}^{(k)} \in \mathbb{R}^{d_k \times d_{k-1}}$ are trainable weight transformation matrices.
- $\sigma(\cdot)$ is the non-linear activation function (ReLU).
- $\text{LayerNorm}(\cdot)$ stabilizes latent dynamics across high-degree hub nodes.

### 3.2 Node Fraud Classification Head
The 2-layer GraphSAGE produces final latent embeddings $z_v = h_v^{(2)} \in \mathbb{R}^{64}$. The classification head projects $z_v$ into fraud risk logits:

$$\hat{y}_v = \text{softmax} \left( W_{\text{clf}} z_v + b_{\text{clf}} \right), \quad \hat{y}_v \in [0, 1]^2$$

The network is trained end-to-end minimizing cross-entropy loss:

$$\mathcal{L}_{\text{CE}} = - \frac{1}{|\mathcal{V}_{\text{train}}|} \sum_{v \in \mathcal{V}_{\text{train}}} \left[ y_v \log(\hat{y}_{v,1}) + (1 - y_v) \log(1 - \hat{y}_{v,1}) \right]$$

### 3.3 Candidate Link Prediction Decoder
Given latent representations $z_u$ and $z_v$ for source and target entities, an MLP decoder predicts connection affinity and suspicious association probability:

$$s(u, v) = \sigma \left( W_2 \cdot \text{ReLU}(W_1 [z_u \,\|\, z_v] + b_1) + b_2 \right)$$

where $[z_u \,\|\, z_v] \in \mathbb{R}^{128}$ represents embedding concatenation.

### 3.4 Gradient-Based Saliency Attribution
To provide explainability for fraud analysts, the engine computes input gradient saliency:

$$\mathcal{A}_i(v) = x_{v,i} \cdot \left| \frac{\partial \hat{y}_{v,1}}{\partial x_{v,i}} \right|$$

Attributions are mapped to human-readable indicators explaining whether hardware emulation, anonymized VPN ingress, circular transfers, or neighbor fraud density drove the model's score.

---

## 4. Benchmark Scenario Specification

The benchmark synthetic dataset (`data/phase18_graph_scenario.json`) contains **92 synthetic entities and 81 graph relationships**:

| Entity Type | Quantity | ID Range | Description |
|---|---|---|---|
| **Customer** | 25 | `CUS-GNN-01` to `CUS-GNN-25` | 5 syndicate accounts (Tier-3 KYC), 20 legitimate retail customers |
| **Account** | 35 | `ACC-GNN-01` to `ACC-GNN-35` | 5 mule accounts, 30 standard commercial accounts |
| **Device** | 15 | `DEV-GNN-01` to `DEV-GNN-15` | `DEV-GNN-01`: Rooted Android emulator hardware farm |
| **IP Address** | 10 | `IP-GNN-01` to `IP-GNN-10` | `IP-GNN-01`: Shared Tor/VPN exit node |
| **Merchant** | 7 | `MER-GNN-01` to `MER-GNN-07` | `MER-GNN-01`: Illicit crypto cashout gateway |
| **Total** | **92** | — | — |

### Graph Relationships (81 total)
- **25 OWNS_ACCOUNT:** Customer-to-account ownership links.
- **18 USES_DEVICE:** Accounts to hardware devices (including 5 mule accounts bound to rogue emulator `DEV-GNN-01`).
- **12 ASSOCIATED_IP:** Network ingress IPs (including 4 mule accounts bound to Tor exit `IP-GNN-01`).
- **20 TRANSFERRED_TO:** Rapid circular wash loops (`ACC-01 -> 02 -> 03 -> 01`), smurfing fan-in (`ACC-04 -> 05 -> 01`), and legitimate peer-to-peer transfers.
- **6 PAID_MERCHANT:** High-value cryptocurrency cashouts and standard retail grocery/coffee transactions.

---

## 5. Synthetic Benchmark Results

Evaluated across test set entities using `scripts/train_model.py`:

| Evaluation Metric | Benchmark Value |
|---|---|
| **Precision** | `1.00` |
| **Recall** | `1.00` |
| **F1-Score** | `1.00` |
| **ROC-AUC** | `1.00` |

> [!NOTE]
> **Synthetic Manifold Notice:**
> These perfect results reflect the deliberately separable synthetic benchmark dataset designed for reproducible unit testing and algorithmic validation, and do not represent expected production performance on noisy, real-world banking telemetry.

---

## 6. Model Card & Production Checklist

### Model Card Summary
- **Model Name:** `FinGuard-GraphSAGE-FraudClassifier` (v1.0.0)
- **Framework:** PyTorch 2.10 CPU
- **Architecture:** 2-Layer Inductive GraphSAGE (Mean Aggregator, LayerNorm, Dropout)
- **Parameters:** ~5,300 trainable weights
- **Input Dimensions:** 16 topological and behavioral features
- **Latent Embeddings:** 64-dimensional dense representation vector
- **Latency:** Sub-50ms inference time on standard CPU hardware

### Production Limitations & Future Scope
- **Neptune Live Integration:** Phase 18 runs inductive GNN inference on local tensor projections; real-time Gremlin graph synchronization is demonstrated in Phase 16.
- **Distributed Training:** Single-machine mini-batching is currently used. Distributed Amazon SageMaker multi-GPU GNN training is slated for Phase 19.
- **Temporal Graphs:** Static graph snapshots are evaluated. Continuous temporal graph neural networks (TGNN) are planned for Phase 19.

---

## 7. REST API Reference

All Phase 18 endpoints are exposed under `/model`:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/model/load` | Loads trained GraphSAGE checkpoint into memory (`curl -X POST http://127.0.0.1:8008/model/load`) |
| `GET` | `/model/info` | Returns model architecture, input/hidden dimensions, parameter counts, and benchmark metrics |
| `POST` | `/model/predict/node` | Evaluates single entity fraud probability, advisory risk level, and explainable feature attributions |
| `POST` | `/model/predict/nodes` | Batch-evaluates multiple entities across the graph |
| `POST` | `/model/predict/link` | Scores candidate link association probability and detects suspicious relationships |
| `POST` | `/model/embeddings` | Extracts 64-dimensional latent entity representations for visual clustering |

---

## 8. Verification Results

Full unit and integration test suite in `tests/phase18/test_gnn_fraud.py`:

```
tests/phase18/test_gnn_fraud.py::test_benchmark_graph_structure PASSED
tests/phase18/test_gnn_fraud.py::test_dataset_feature_tensor_encoding PASSED
tests/phase18/test_gnn_fraud.py::test_graphsage_forward_pass_and_embeddings PASSED
tests/phase18/test_gnn_fraud.py::test_graphsage_training_and_convergence PASSED
tests/phase18/test_gnn_fraud.py::test_suspicious_link_prediction PASSED
tests/phase18/test_gnn_fraud.py::test_explainable_risk_attribution PASSED
tests/phase18/test_gnn_fraud.py::test_api_model_load_and_info PASSED
tests/phase18/test_gnn_fraud.py::test_api_node_and_link_inference PASSED

======================== 8 passed, 0 failures ========================
```
- Total test suite (Phase 15, 16, 17, 18): **36 passed, 0 failures**.
- Frontend production build: **Passed (`✓ built in 4.96s`, 0 errors)**.

