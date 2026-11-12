"""
Unit tests for S3 processed transaction storage sink.
"""
from unittest.mock import MagicMock
from lambda_app.s3_sink import S3ProcessedSink


def test_s3_sink_path_partitioning():
    mock_s3 = MagicMock()
    sink = S3ProcessedSink(
        s3_client=mock_s3,
        bucket_name="finguard-data-processed-dev",
        prefix="processed/transactions"
    )

    enriched = {
        "transaction_id": "TXN-20261112-000001",
        "account_id": "ACC-100045",
        "amount": 5000.0,
        "transaction_timestamp": "2026-11-12T10:30:00Z",
        "features": {"transaction_count_5m_prior": 0}
    }

    key = sink.store_enriched_transaction(enriched)

    assert key == "processed/transactions/year=2026/month=11/day=12/TXN-20261112-000001.json"
    assert mock_s3.put_object.call_count == 1
    call_kwargs = mock_s3.put_object.call_args[1]
    assert call_kwargs["Bucket"] == "finguard-data-processed-dev"
    assert call_kwargs["Key"] == key
    assert call_kwargs["ContentType"] == "application/json"
