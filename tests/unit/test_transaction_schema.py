"""
Unit test for Transaction JSON Schema and Pydantic validation.
"""
import json
import os
import jsonschema
import pytest
from backend.app.schemas.transaction import TransactionCreate


def test_sample_transaction_matches_json_schema():
    schema_path = os.path.join("data", "schemas", "transaction.schema.json")
    sample_path = os.path.join("data", "samples", "sample_transaction.json")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    with open(sample_path, "r", encoding="utf-8") as f:
        sample = json.load(f)

    # Validate against JSON schema draft 2020-12
    jsonschema.validate(instance=sample, schema=schema)


def test_pydantic_transaction_create():
    sample_path = os.path.join("data", "samples", "sample_transaction.json")
    with open(sample_path, "r", encoding="utf-8") as f:
        sample = json.load(f)

    txn = TransactionCreate.model_validate(sample)
    assert txn.transaction_id == "TXN-20261112-000001"
    assert txn.amount == 87500.00
    assert txn.location.city == "Kolkata"

