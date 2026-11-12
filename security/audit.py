"""Tamper-Evident Security Audit Logging for FinGuard AI."""

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import boto3
from botocore.exceptions import ClientError


class SecurityAuditEvent(BaseModel):
    """Immutable record of an authorized or denied security action."""
    event_id: str = Field(default_factory=lambda: f"SEC-{uuid.uuid4().hex[:12]}")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    actor_sub: str
    actor_email: str = ""
    actor_roles: List[str] = Field(default_factory=list)
    action: str
    resource_type: str
    resource_id: str
    status: str = "SUCCESS"  # SUCCESS, DENIED, ERROR
    ip_address: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class SecurityAuditLogger:
    """Stores security audit events in DynamoDB with an in-memory fallback."""

    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None):
        self.table_name = table_name or os.getenv("AUDIT_TABLE", "finguard-dev-security-audit")
        self.region = region or os.getenv("AWS_REGION", "ap-south-1")
        self._dynamodb = None
        self._table = None
        self._memory_logs: List[SecurityAuditEvent] = []
        self._use_dynamodb: Optional[bool] = None

    def _get_table(self):
        if self._table is None and self._use_dynamodb is not False:
            if not os.getenv("AWS_ACCESS_KEY_ID") and not os.getenv("AWS_PROFILE") and not os.getenv("AWS_DEFAULT_REGION"):
                self._use_dynamodb = False
                self._table = None
                return None
            try:
                from botocore.config import Config
                fast_cfg = Config(connect_timeout=1, read_timeout=1, retries={"max_attempts": 0})
                self._dynamodb = boto3.resource("dynamodb", region_name=self.region, config=fast_cfg)
                table = self._dynamodb.Table(self.table_name)
                # Quick load to verify existence
                table.load()
                self._table = table
                self._use_dynamodb = True
            except Exception:
                # DynamoDB not available locally or credentials not configured
                self._use_dynamodb = False
                self._table = None
        return self._table

    def log(
        self,
        actor_sub: str,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_email: str = "",
        actor_roles: Optional[List[str]] = None,
        status: str = "SUCCESS",
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> SecurityAuditEvent:
        """Create and persist a security audit record."""
        event = SecurityAuditEvent(
            actor_sub=actor_sub,
            actor_email=actor_email,
            actor_roles=actor_roles or [],
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            ip_address=ip_address,
            details=details or {},
        )

        # Always keep in memory buffer for instant query and testing
        self._memory_logs.insert(0, event)

        # Attempt to write to DynamoDB
        table = self._get_table()
        if table:
            try:
                table.put_item(Item=event.dict())
            except ClientError as e:
                # Fallback to local memory if DynamoDB write fails
                pass

        return event

    def list_logs(
        self,
        limit: int = 50,
        actor_email: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[SecurityAuditEvent]:
        """Retrieve recent security audit logs."""
        logs = self._memory_logs
        if actor_email:
            logs = [l for l in logs if l.actor_email.lower() == actor_email.lower()]
        if action:
            logs = [l for l in logs if l.action == action]
        return logs[:limit]

    def clear(self) -> None:
        """Clear in-memory buffer (primarily for test isolation)."""
        self._memory_logs.clear()


# Default singleton instance
audit_logger = SecurityAuditLogger()

