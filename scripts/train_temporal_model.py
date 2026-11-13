"""Phase 19 — PyTorch GRU Temporal Sequence Model Training with Chronological Train/Test Split.

Usage:
    python scripts/train_temporal_model.py --input examples/training_record.jsonl --epochs 20 --output artifacts/phase19
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from temporal.gru_model import TemporalGRUClassifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("temporal-train")


def load_chronological_dataset(
    file_path: Path,
    split_ratio: float = 0.80,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Loads JSONL records and strictly splits chronologically (no future lookahead leakage).
    """
    records: List[Dict[str, Any]] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # Sort strictly by timestamp
    records.sort(key=lambda r: r["timestamp"])

    x_list = [r["sequence"] for r in records]
    y_list = [r["label"] for r in records]

    x_tensor = torch.tensor(x_list, dtype=torch.float32)
    y_tensor = torch.tensor(y_list, dtype=torch.long)

    split_idx = int(len(records) * split_ratio)

    x_train, x_test = x_tensor[:split_idx], x_tensor[split_idx:]
    y_train, y_test = y_tensor[:split_idx], y_tensor[split_idx:]

    return x_train, y_train, x_test, y_test


def train_temporal_gru(
    input_path: str = "examples/training_record.jsonl",
    epochs: int = 20,
    lr: float = 0.01,
    output_dir: str = "artifacts/phase19",
) -> Dict[str, Any]:
    in_file = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_file.exists():
        logger.info("Dataset not found at %s. Generating synthetic event stream...", in_file)
        from scripts.generate_events import generate_synthetic_temporal_events, generate_training_records
        events = generate_synthetic_temporal_events(500)
        recs = generate_training_records(events)
        in_file.parent.mkdir(parents=True, exist_ok=True)
        with open(in_file, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")

    x_train, y_train, x_test, y_test = load_chronological_dataset(in_file, split_ratio=0.80)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Chronological split: %d train records, %d test records. Device: %s", len(x_train), len(x_test), device)

    model = TemporalGRUClassifier(
        input_dim=12,
        hidden_dim=64,
        num_layers=2,
        num_classes=2,
        dropout=0.2,
    ).to(device)

    x_tr = x_train.to(device)
    y_tr = y_train.to(device)
    x_te = x_test.to(device)
    y_te = y_test.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    logger.info("Training GRU sequence classifier for %d epochs...", epochs)
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits, _ = model(x_tr)
        loss = criterion(logits, y_tr)
        loss.backward()
        optimizer.step()

        if epoch % 5 == 0 or epoch == epochs:
            logger.info("Epoch %02d/%d - Train Loss: %.4f", epoch, epochs, loss.item())

    # Evaluation on Chronological Test Set
    model.eval()
    with torch.no_grad():
        test_logits, _ = model(x_te)
        test_probs = torch.softmax(test_logits, dim=-1)[:, 1].cpu().numpy()
        test_preds = torch.argmax(test_logits, dim=-1).cpu().numpy()

    y_true = y_te.cpu().numpy()
    precision = float(precision_score(y_true, test_preds, zero_division=1))
    recall = float(recall_score(y_true, test_preds, zero_division=1))
    f1 = float(f1_score(y_true, test_preds, zero_division=1))
    roc_auc = float(roc_auc_score(y_true, test_probs)) if len(np.unique(y_true)) > 1 else 1.0

    logger.info("Chronological Evaluation: Precision=%.4f, Recall=%.4f, F1=%.4f, ROC-AUC=%.4f", precision, recall, f1, roc_auc)

    # Save Model Weights
    ckpt_path = out_dir / "gru_temporal_model.pt"
    torch.save(model.state_dict(), ckpt_path)
    logger.info("Saved GRU temporal model checkpoint to: %s", ckpt_path)

    # Save Evaluation Report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "architecture": "2-Layer PyTorch GRU (Hidden Dim: 64)",
        "epochs": epochs,
        "input_records": str(in_file),
        "split_method": "Chronological (80% Train / 20% Test, zero lookahead leakage)",
        "dataset_statistics": {
            "train_samples": len(x_train),
            "test_samples": len(x_test),
            "feature_dim": 12,
            "sequence_length": x_train.size(1),
        },
        "evaluation_metrics": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
        },
        "advisory_notice": "Model predictions are advisory decision-support signals. Human investigators retain decision authority.",
    }

    report_path = out_dir / "evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Train PyTorch GRU temporal sequence model.")
    parser.add_argument("--input", type=str, default="examples/training_record.jsonl", help="Input JSONL records")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs")
    parser.add_argument("--lr", type=float, default=0.01, help="Learning rate")
    parser.add_argument("--output", type=str, default="artifacts/phase19", help="Output directory")
    args = parser.parse_args()

    report = train_temporal_gru(
        input_path=args.input,
        epochs=args.epochs,
        lr=args.lr,
        output_dir=args.output,
    )

    metrics = report["evaluation_metrics"]
    print("\n" + "=" * 60)
    print(" FinGuard AI — Phase 19 Temporal GRU Benchmark Results")
    print("=" * 60)
    print(f" Precision: {metrics['precision']:.2f}")
    print(f" Recall:    {metrics['recall']:.2f}")
    print(f" F1-score:  {metrics['f1_score']:.2f}")
    print(f" ROC-AUC:   {metrics['roc_auc']:.2f}")
    print("=" * 60)
    print("Chronological split: Evaluated strictly forward in time (no data leakage).\n")


if __name__ == "__main__":
    main()

