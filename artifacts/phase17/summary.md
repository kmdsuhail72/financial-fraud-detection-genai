# FinGuard AI — Phase 17 Advanced Graph Analytics Report

- **Executed Timestamp:** 2026-11-13 05:47:57 UTC
- **Total Entities Evaluated:** 38
- **Total Relationships Evaluated:** 33
- **Topological Communities Detected:** 9

## 1. Top Communities by Risk Score

| Community ID | Members Count | Density | Risk Score | Risk Classification | Suspicious Flags |
|---|---|---|---|---|---|
| `COMM-01` | 9 | 0.333 | `1.00` | **CRITICAL** | Shared physical device infrastructure in community, Shared network IP ingress hub in community, Circular fund transfer loop identified in community |
| `COMM-03` | 4 | 0.500 | `0.25` | **MEDIUM** | Abnormally high internal interconnectivity (density: 0.5) |
| `COMM-04` | 4 | 0.500 | `0.25` | **MEDIUM** | Abnormally high internal interconnectivity (density: 0.5) |
| `COMM-05` | 4 | 0.500 | `0.25` | **MEDIUM** | Abnormally high internal interconnectivity (density: 0.5) |
| `COMM-02` | 11 | 0.182 | `0.05` | **LOW** | Nominal |

## 2. Top PageRank Authority Prominence

| Entity ID | PageRank Score |
|---|---|
| `ACC-P17-03` | `0.09642` |
| `ACC-P17-02` | `0.08546` |
| `ACC-P17-01` | `0.07257` |
| `DEV-P17-04` | `0.06144` |
| `ACC-P17-06` | `0.05715` |

## 3. Shortest Path Routing Analysis
- **Route:** `ACC-P17-01` $\rightarrow$ `MER-P17-01`
- **Path Exists:** `True`
- **Hops:** `3`
- **Path Sequence:** `ACC-P17-01 -> ACC-P17-02 -> ACC-P17-03 -> MER-P17-01`

## 4. Investigative Note
> [!NOTE]
> All graph risk scores and predictive ratings are **heuristic indicators** intended to guide human investigators during fraud triage. Autonomous adverse actions (e.g. account blocking) are never executed without investigator verification.
