"""
Tests for SageMaker Model Packaging Script.
"""
import tarfile
import tempfile
from pathlib import Path
import pytest

from scripts.phase7.package_model import package_model_artifact


def test_package_model_creates_valid_tarball():
    """Verify package_model_artifact creates valid model.tar.gz with required members."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        dummy_model = tmp_path / "model.joblib"
        dummy_inference = tmp_path / "inference.py"
        output_tar = tmp_path / "model.tar.gz"

        dummy_model.write_bytes(b"dummy joblib bytes")
        dummy_inference.write_text("def model_fn(x): pass")

        out_path = package_model_artifact(
            model_path=str(dummy_model),
            inference_path=str(dummy_inference),
            output_path=str(output_tar),
        )

        assert out_path.exists()
        assert out_path.stat().st_size > 0

        # Verify tar contents
        with tarfile.open(out_path, "r:gz") as tar:
            names = tar.getnames()
            assert "model.joblib" in names
            assert "code/inference.py" in names

            # Check extracted contents
            extracted_joblib = tar.extractfile("model.joblib").read()
            assert extracted_joblib == b"dummy joblib bytes"
