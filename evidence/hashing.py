"""
FinGuard AI — Phase 22 Cryptographic Evidence Hashing & Verification.
Enforces SHA-256 canonical integrity digests on evidence payloads.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def serialize_canonical_payload(payload: Any) -> bytes:
    """
    Serializes arbitrary dict/list payload into canonical, sorted UTF-8 JSON bytes.
    Ensures identical SHA-256 hashes regardless of dictionary key ordering.
    """
    def default_encoder(obj: Any) -> str:
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)

    canonical_json_str = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        default=default_encoder,
        separators=(",", ":"),
    )
    return canonical_json_str.encode("utf-8")


def compute_sha256(payload: Any) -> str:
    """Computes standard 64-character hex SHA-256 digest of canonical payload."""
    payload_bytes = serialize_canonical_payload(payload)
    return hashlib.sha256(payload_bytes).hexdigest()


def verify_sha256(payload: Any, expected_hash: str) -> bool:
    """Verifies whether payload's recomputed SHA-256 digest matches expected hash."""
    computed = compute_sha256(payload)
    return computed.lower() == expected_hash.strip().lower()

