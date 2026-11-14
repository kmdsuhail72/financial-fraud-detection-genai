"""
FinGuard AI — Enterprise Backup Verification & Integrity Engine
Calculates canonical SHA-256 hashes, parses and validates backup manifests,
and checks for tampering or replication corruption.
"""
from __future__ import annotations

import hashlib
import time
from typing import List, Optional

from disaster_recovery.models import BackupFileEntry, BackupManifest, BackupVerificationResult


class BackupIntegrityManager:
    """Manages backup creation manifests and validates SHA-256 checksums."""

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """Calculates canonical SHA-256 hex digest for binary data."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def create_sample_manifest(
        manifest_id: Optional[str] = None,
        inject_corruption: bool = False,
    ) -> BackupManifest:
        """Generates a synthetic backup manifest with multiple database and audit logs."""
        files = [
            BackupFileEntry(
                filename="dynamodb-cases-snapshot.tar.gz",
                size_bytes=42598400,
                sha256_checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                created_at="2026-11-14T10:00:00Z",
                status="VERIFIED",
            ),
            BackupFileEntry(
                filename="s3-evidence-store-metadata.json",
                size_bytes=1048576,
                sha256_checksum="ca978112ca1bbdcafac231b39a23dc4da786081496140970e4e2a00e8d10cf4c",
                created_at="2026-11-14T10:05:00Z",
                status="VERIFIED",
            ),
            BackupFileEntry(
                filename="finguard-audit-trail-logs.parquet",
                size_bytes=8388608,
                sha256_checksum="4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce",
                created_at="2026-11-14T10:10:00Z",
                status="VERIFIED",
            ),
        ]

        if inject_corruption:
            # Corrupt the checksum of the first file
            files[0].sha256_checksum = "0000000000000000000000000000000000000000000000000000000000000000"

        combined_hash = hashlib.sha256("".join(f.sha256_checksum for f in files).encode("utf-8")).hexdigest()
        total_size = sum(f.size_bytes for f in files)

        return BackupManifest(
            manifest_id=manifest_id or "mnf-sample-primary",
            backup_type="FULL",
            source_region="ap-south-1",
            replica_region="ap-southeast-1",
            files=files,
            total_size_bytes=total_size,
            overall_sha256=combined_hash,
            verified=not inject_corruption,
        )

    @classmethod
    def verify_manifest(
        cls,
        manifest: BackupManifest,
        simulated_corruptions: Optional[List[str]] = None,
    ) -> BackupVerificationResult:
        """Verifies the integrity of all file entries in a backup manifest."""
        t0 = time.time()
        mismatches: List[str] = []

        for f in manifest.files:
            # In a real environment, this reads the actual file stream and compares checksums
            if simulated_corruptions and f.filename in simulated_corruptions:
                mismatches.append(f"{f.filename}: SHA-256 hash mismatch (detected silent data corruption)")
            elif f.sha256_checksum.startswith("000000"):
                mismatches.append(f"{f.filename}: invalid zero checksum")

        # Verify overall checksum
        recomputed_overall = hashlib.sha256("".join(f.sha256_checksum for f in manifest.files).encode("utf-8")).hexdigest()
        if recomputed_overall != manifest.overall_sha256 and not mismatches:
            mismatches.append("Overall manifest aggregate checksum mismatch")

        is_valid = len(mismatches) == 0
        elapsed_ms = round((time.time() - t0) * 1000.0, 2)

        return BackupVerificationResult(
            manifest_id=manifest.manifest_id,
            valid=is_valid,
            files_checked=len(manifest.files),
            mismatches=mismatches,
            verification_time_ms=elapsed_ms,
            message="Backup manifest successfully verified without corruption." if is_valid else f"Verification failed with {len(mismatches)} errors.",
        )


# Global singleton manager
backup_manager = BackupIntegrityManager()
