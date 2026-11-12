"""
Unit tests for Phase 5 sample Bronze generator.
"""
import os
import shutil
import tempfile
from scripts.phase5.create_sample_data import generate_sample_transactions, write_partitioned_sample_data


def test_generate_sample_transactions():
    txns = generate_sample_transactions(count=25, seed=101)
    assert len(txns) == 25
    assert txns[0]["transaction_id"] == "TXN-20261112-000001"
    assert "features" in txns[0]
    assert "transaction_count_5m_prior" in txns[0]["features"]
    assert float(txns[0]["amount"]) > 0


def test_write_partitioned_sample_data():
    temp_dir = tempfile.mkdtemp()
    try:
        txns = generate_sample_transactions(count=30, seed=102)
        created_files = write_partitioned_sample_data(txns, temp_dir)

        assert len(created_files) > 0
        for fpath in created_files:
            assert os.path.exists(fpath)
            assert "year=2026" in fpath
            assert "month=11" in fpath
            assert "day=12" in fpath
            assert "hour=" in fpath
    finally:
        shutil.rmtree(temp_dir)
