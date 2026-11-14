"""
Phase 39: Cache-Aside Implementation Primitives
Implements read-through caching and explicit invalidation for financial data entities.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from caching.base import BaseCache
from caching.models import CustomerProfile, ProfileUpdateRequest

# Standard TTL Policies
TTL_CUSTOMER_PROFILE = 300      # 5 minutes
TTL_MERCHANT_METADATA = 900     # 15 minutes
TTL_TRANSACTION_LOOKUP = 60     # 1 minute


class CacheAsideManager:
    """Manages read-through caching and entity invalidation."""

    def __init__(self, cache: BaseCache):
        self._cache = cache
        # Simulated authoritative DB (e.g. DynamoDB / RDS)
        self._authoritative_profiles: Dict[str, CustomerProfile] = {
            "CUST-1001": CustomerProfile(
                customer_id="CUST-1001",
                name="Aarav Sharma",
                risk_tier="LOW",
                country="IN",
                kyc_status="VERIFIED",
                email="aarav.sharma@example.com",
                updated_at="2026-11-14T10:00:00Z",
            ),
            "CUST-1002": CustomerProfile(
                customer_id="CUST-1002",
                name="Priya Patel",
                risk_tier="HIGH",
                country="IN",
                kyc_status="MANUAL_REVIEW",
                email="priya.patel@example.com",
                updated_at="2026-11-14T10:15:00Z",
            ),
            "CUST-1003": CustomerProfile(
                customer_id="CUST-1003",
                name="Vikram Mehta",
                risk_tier="MEDIUM",
                country="AE",
                kyc_status="VERIFIED",
                email="vikram.mehta@example.com",
                updated_at="2026-11-14T10:30:00Z",
            ),
        }
        self._authoritative_merchants: Dict[str, Dict[str, Any]] = {
            "MERCH-501": {
                "merchant_id": "MERCH-501",
                "name": "Reliance Retail UPI",
                "category": "GROCERY",
                "risk_rating": 0.05,
                "verified": True,
            },
            "MERCH-502": {
                "merchant_id": "MERCH-502",
                "name": "Global Crypto Gateway",
                "category": "HIGH_RISK_FINANCE",
                "risk_rating": 0.88,
                "verified": False,
            },
        }

    # --- Customer Profile Operations ---

    def get_customer_profile(self, customer_id: str) -> Optional[CustomerProfile]:
        """Cache-aside read-through for customer profile."""
        cache_key = f"profile:{customer_id}"
        cached = self._cache.get(cache_key)

        if cached is not None:
            data = cached if isinstance(cached, dict) else cached
            return CustomerProfile(**data)

        # Cache Miss: Fetch from authoritative DB
        profile = self._authoritative_profiles.get(customer_id)
        if profile is not None:
            self._cache.set(cache_key, profile.model_dump(), ttl_seconds=TTL_CUSTOMER_PROFILE)
        return profile

    def update_customer_profile(self, customer_id: str, updates: ProfileUpdateRequest) -> CustomerProfile:
        """Update authoritative record and explicitly invalidate the cache entry."""
        profile = self.get_customer_profile(customer_id)
        if not profile:
            now = datetime.now(timezone.utc).isoformat()
            profile = CustomerProfile(
                customer_id=customer_id,
                name=updates.name or "New Customer",
                risk_tier=updates.risk_tier or "MEDIUM",
                country=updates.country or "IN",
                kyc_status=updates.kyc_status or "PENDING",
                email=updates.email or f"{customer_id.lower()}@example.com",
                updated_at=now,
            )
        else:
            dump = profile.model_dump()
            for field, val in updates.model_dump(exclude_unset=True).items():
                if val is not None:
                    dump[field] = val
            dump["updated_at"] = datetime.now(timezone.utc).isoformat()
            profile = CustomerProfile(**dump)

        # 1. Write to authoritative database
        self._authoritative_profiles[customer_id] = profile

        # 2. Invalidate cache-aside entry
        self.invalidate_customer_profile(customer_id)

        return profile

    def invalidate_customer_profile(self, customer_id: str) -> bool:
        """Explicitly evict customer profile from cache."""
        cache_key = f"profile:{customer_id}"
        return self._cache.delete(cache_key)

    # --- Merchant Metadata Operations ---

    def get_merchant_metadata(self, merchant_id: str) -> Optional[Dict[str, Any]]:
        """Cache-aside lookup for merchant metadata."""
        cache_key = f"merchant:{merchant_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        data = self._authoritative_merchants.get(merchant_id)
        if data is not None:
            self._cache.set(cache_key, data, ttl_seconds=TTL_MERCHANT_METADATA)
        return data

    def invalidate_merchant(self, merchant_id: str) -> bool:
        """Invalidate cached merchant metadata."""
        return self._cache.delete(f"merchant:{merchant_id}")

    # --- Transaction Lookups ---

    def get_transaction_lookup(self, tx_id: str, loader: Optional[Callable[[str], Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """Short-lived cached lookup for recent transactions."""
        cache_key = f"tx_lookup:{tx_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if loader:
            val = loader(tx_id)
            if val:
                self._cache.set(cache_key, val, ttl_seconds=TTL_TRANSACTION_LOOKUP)
                return val
        return None

