"""
Phase 40: Event Contracts & Versioned JSON Event Envelope
Defines the enterprise event envelope with semver checks and serialization.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class EventEnvelope(BaseModel):
    """
    Standard FinGuard AI Versioned Event Envelope.
    Enforces correlation, causation, tenant scoping, and semver schema compatibility.
    """
    event_id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    event_type: str = Field(..., description="Canonical event classification (e.g., transaction.created)")
    version: str = Field(default="1.0.0", description="Semantic schema version (MAJOR.MINOR.PATCH)")
    producer: str = Field(default="finguard-gateway", description="Service originating the event")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tenant_id: str = Field(default="default-tenant", description="Owning tenant for multi-tenant isolation")
    correlation_id: str = Field(default_factory=lambda: f"corr-{uuid.uuid4().hex[:10]}")
    causation_id: Optional[str] = Field(default=None, description="Event that directly caused this event")
    schema_url: str = Field(default="https://schemas.finguard.ai/v1/event.json")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Domain event payload")

    model_config = ConfigDict(extra="allow")

    def serialize(self) -> str:
        """Serialize event to formatted JSON string."""
        return self.model_dump_json()

    @classmethod
    def deserialize(cls, data: Any) -> "EventEnvelope":
        """Deserialize from JSON string or dict."""
        if isinstance(data, str):
            parsed = json.loads(data)
            return cls(**parsed)
        elif isinstance(data, dict):
            return cls(**data)
        raise ValueError(f"Cannot deserialize type {type(data)} into EventEnvelope")

    def get_major_version(self) -> int:
        """Extract the major version integer from semver string."""
        try:
            parts = self.version.split(".")
            return int(parts[0])
        except Exception:
            return 1

    def is_compatible_with(self, expected_major: int = 1) -> bool:
        """Verify backwards-compatible major version check."""
        return self.get_major_version() == expected_major
