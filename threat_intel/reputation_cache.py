"""Thread-safe SQLite Reputation Cache with TTL for Threat Intelligence Indicators."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from threat_intel.models import (
    AnalystFeedback,
    IOCRecord,
    IOCSeverity,
    IOCStatus,
    IOCType,
)
from threat_intel.risk_engine import IOCRiskEngine

logger = logging.getLogger("finguard-threat-intel")


class SQLiteReputationCache:
    """Persistent local SQLite cache for enriched indicators with TTL eviction."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to persistent file in data/ or in-memory
            base_dir = Path("data")
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(base_dir / "threat_intel_cache.db")
        else:
            self.db_path = db_path

        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS iocs (
                        ioc_id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        value TEXT NOT NULL UNIQUE,
                        reputation_score REAL NOT NULL,
                        confidence REAL NOT NULL,
                        severity TEXT NOT NULL,
                        status TEXT NOT NULL,
                        expires_at TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        data JSON NOT NULL
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_iocs_value ON iocs (value)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_iocs_type ON iocs (type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_iocs_severity ON iocs (severity)")

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS analyst_feedback (
                        feedback_id TEXT PRIMARY KEY,
                        ioc_id TEXT NOT NULL,
                        analyst_id TEXT NOT NULL,
                        verdict TEXT NOT NULL,
                        notes TEXT,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (ioc_id) REFERENCES iocs (ioc_id)
                    )
                    """
                )
                conn.commit()

    def get_ioc(self, value: str) -> Optional[IOCRecord]:
        """Looks up cached indicator by raw value, respecting expiration."""
        norm_val = value.strip().lower()
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT data, expires_at, status FROM iocs WHERE lower(value) = ?",
                    (norm_val,),
                ).fetchone()
                if not row:
                    return None

                expires_at_str = row["expires_at"]
                if expires_at_str and expires_at_str < now and row["status"] != IOCStatus.REVOKED.value:
                    # Expired
                    return None

                raw_json = json.loads(row["data"])
                return IOCRecord.model_validate(raw_json)

    def get_ioc_by_id(self, ioc_id: str) -> Optional[IOCRecord]:
        """Looks up cached indicator by unique ioc_id."""
        with self._lock:
            with self._get_connection() as conn:
                row = conn.execute("SELECT data FROM iocs WHERE ioc_id = ?", (ioc_id,)).fetchone()
                if not row:
                    return None
                return IOCRecord.model_validate(json.loads(row["data"]))

    def set_ioc(self, record: IOCRecord, ttl_seconds: int = 86400 * 30) -> None:
        """Stores or updates an enriched IOC record in SQLite with TTL."""
        now = datetime.now(timezone.utc)
        if record.expires_at is None:
            expires_at = now + timedelta(seconds=ttl_seconds)
            record.expires_at = expires_at
        else:
            expires_at = record.expires_at

        data_json = record.model_dump_json()
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO iocs (
                        ioc_id, type, value, reputation_score, confidence,
                        severity, status, expires_at, created_at, updated_at, data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(value) DO UPDATE SET
                        reputation_score = excluded.reputation_score,
                        confidence = excluded.confidence,
                        severity = excluded.severity,
                        status = excluded.status,
                        expires_at = excluded.expires_at,
                        updated_at = excluded.updated_at,
                        data = excluded.data
                    """,
                    (
                        record.ioc_id,
                        record.type.value if hasattr(record.type, "value") else str(record.type),
                        record.value,
                        record.reputation_score,
                        record.confidence,
                        record.severity.value if hasattr(record.severity, "value") else str(record.severity),
                        record.status.value if hasattr(record.status, "value") else str(record.status),
                        expires_at.isoformat(),
                        record.first_seen.isoformat(),
                        now.isoformat(),
                        data_json,
                    ),
                )
                conn.commit()

    def list_iocs(
        self,
        ioc_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[IOCRecord]:
        """Lists cached indicators with filtering."""
        query = "SELECT data FROM iocs WHERE 1=1"
        params: List[Any] = []

        if ioc_type:
            query += " AND type = ?"
            params.append(ioc_type.lower())
        if severity:
            query += " AND severity = ?"
            params.append(severity.upper())
        if status:
            query += " AND status = ?"
            params.append(status.upper())
        if min_score is not None:
            query += " AND reputation_score >= ?"
            params.append(min_score)

        query += " ORDER BY reputation_score DESC, updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._lock:
            with self._get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                return [IOCRecord.model_validate(json.loads(r["data"])) for r in rows]

    def add_analyst_feedback(self, feedback: AnalystFeedback) -> IOCRecord:
        """Appends analyst review verdict, recalibrates score, and updates cache."""
        record = self.get_ioc_by_id(feedback.ioc_id)
        if not record:
            raise KeyError(f"IOC with ID '{feedback.ioc_id}' not found.")

        record.analyst_verdicts.append(feedback)
        # Recalculate risk using risk engine
        new_score, new_conf, new_sev, new_stat, _ = IOCRiskEngine.evaluate_risk(
            base_reputation=record.reputation_score,
            base_confidence=record.confidence,
            threat_types=record.threat_types,
            source_feeds=record.source_feeds,
            analyst_verdicts=record.analyst_verdicts,
            expires_at=record.expires_at,
        )
        record.reputation_score = new_score
        record.confidence = new_conf
        record.severity = new_sev
        record.status = new_stat
        record.last_seen = datetime.now(timezone.utc)

        # Update in database
        self.set_ioc(record)
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO analyst_feedback (feedback_id, ioc_id, analyst_id, verdict, notes, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        feedback.feedback_id,
                        feedback.ioc_id,
                        feedback.analyst_id,
                        feedback.verdict.value if hasattr(feedback.verdict, "value") else str(feedback.verdict),
                        feedback.notes,
                        feedback.timestamp.isoformat(),
                    ),
                )
                conn.commit()

        return record

    def purge_expired(self) -> int:
        """Removes expired indicators that are not explicitly revoked or under review."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM iocs WHERE expires_at < ? AND status NOT IN ('REVOKED', 'UNDER_REVIEW')",
                    (now,),
                )
                conn.commit()
                return cursor.rowcount

    def clear(self) -> None:
        """Wipes all records (primarily for test fixtures)."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM analyst_feedback")
                conn.execute("DELETE FROM iocs")
                conn.commit()
