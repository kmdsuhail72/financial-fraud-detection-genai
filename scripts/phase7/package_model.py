#!/usr/bin/env python3
"""
FinGuard AI — SageMaker Model Packaging Script (Phase 7).

Packages trained model.joblib and SageMaker inference script into
the exact model.tar.gz structure required by Amazon SageMaker endpoints:

model.tar.gz
├── model.joblib
└── code/
    └── inference.py

Usage:
    python scripts/phase7/package_model.py \\
      --model artifacts/model.joblib \\
      --inference sagemaker/inference.py \\
      --output artifacts/sagemaker/model.tar.gz
"""
import argparse
import logging
import os
import tarfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("finguard-packager")


def package_model_artifact(
    model_path: str,
    inference_path: str,
    output_path: str,
) -> Path:
    """
    Creates a gzipped tar archive conforming to SageMaker's standard layout.
    """
    model_file = Path(model_path)
    inference_file = Path(inference_path)
    out_file = Path(output_path)

    if not model_file.exists():
        raise FileNotFoundError(f"Model file not found at: {model_file}")
    if not inference_file.exists():
        raise FileNotFoundError(f"Inference script not found at: {inference_file}")

    out_file.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Packaging SageMaker model archive...")
    logger.info("  Model:     %s (%d bytes)", model_file, model_file.stat().st_size)
    logger.info("  Inference: %s", inference_file)
    logger.info("  Output:    %s", out_file)

    with tarfile.open(out_file, "w:gz") as tar:
        # Add model.joblib at the root of the archive
        tar.add(str(model_file), arcname="model.joblib")

        # Add inference.py under code/inference.py
        tar.add(str(inference_file), arcname="code/inference.py")

    archive_size = out_file.stat().st_size
    logger.info("Successfully packaged model.tar.gz (%d bytes) at %s", archive_size, out_file)

    # Verify archive contents
    with tarfile.open(out_file, "r:gz") as tar:
        members = tar.getnames()
        logger.info("Verified archive members: %s", members)
        if "model.joblib" not in members or "code/inference.py" not in members:
            raise ValueError(f"Archive missing required members. Found: {members}")

    return out_file


def parse_args():
    parser = argparse.ArgumentParser(description="Package FinGuard AI model for SageMaker hosting")
    parser.add_argument("--model", type=str, default="artifacts/model.joblib", help="Path to model.joblib")
    parser.add_argument("--inference", type=str, default="sagemaker/inference.py", help="Path to inference.py")
    parser.add_argument("--output", type=str, default="artifacts/sagemaker/model.tar.gz", help="Output tar.gz path")
    return parser.parse_args()


def main():
    args = parse_args()
    package_model_artifact(
        model_path=args.model,
        inference_path=args.inference,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
