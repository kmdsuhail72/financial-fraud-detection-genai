"""Profile storage and baseline repository for FinGuard AI UEBA."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ueba.models import (
    BehavioralBaseline,
    EntityRiskLevel,
    PeerGroup,
    UserEntityProfile,
)


class ProfileStore:
    """In-memory and file-backed entity profile repository."""

    def __init__(self, persistence_path: Optional[str] = None):
        self._profiles: Dict[str, UserEntityProfile] = {}
        self._persistence_path = Path(persistence_path) if persistence_path else None

        if self._persistence_path and self._persistence_path.exists():
            self._load_from_disk()
        else:
            self._seed_default_profiles()

    def get_profile(self, entity_id: str) -> Optional[UserEntityProfile]:
        return self._profiles.get(entity_id)

    def save_profile(self, profile: UserEntityProfile) -> UserEntityProfile:
        profile.last_updated = datetime.now(timezone.utc)
        self._profiles[profile.entity_id] = profile
        if self._persistence_path:
            self._save_to_disk()
        return profile

    def list_profiles(
        self,
        peer_group: Optional[PeerGroup] = None,
        risk_level: Optional[EntityRiskLevel] = None,
        min_risk: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserEntityProfile]:
        profiles = list(self._profiles.values())

        if peer_group:
            profiles = [p for p in profiles if p.peer_group == peer_group]
        if risk_level:
            profiles = [p for p in profiles if p.risk_level == risk_level]
        if min_risk is not None:
            profiles = [p for p in profiles if p.current_risk_score >= min_risk]

        # Sort descending by risk score
        profiles.sort(key=lambda p: p.current_risk_score, reverse=True)
        return profiles[offset : offset + limit]

    def count(self) -> int:
        return len(self._profiles)

    def _seed_default_profiles(self) -> None:
        """Seeds 35 diverse initial entity profiles with realistic behavioral baselines."""
        cohort_configs = [
            (
                PeerGroup.RETAIL,
                75.0,
                35.0,
                350.0,
                [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
                ["dev_iphone_14", "dev_chrome_mac"],
                ["198.51.100.12", "198.51.100.45"],
                ["New York", "Boston"],
                2.5,
                0.2,
            ),
            (
                PeerGroup.HIGH_NET_WORTH,
                2450.0,
                950.0,
                15000.0,
                [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
                ["dev_ipad_pro", "dev_safari_mac", "dev_work_laptop"],
                ["203.0.113.10", "203.0.113.88"],
                ["San Francisco", "London", "Zurich"],
                3.8,
                0.35,
            ),
            (
                PeerGroup.COMMERCIAL,
                4800.0,
                1800.0,
                28000.0,
                [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                ["dev_office_win11", "dev_finance_station"],
                ["192.0.2.24", "192.0.2.99"],
                ["Chicago", "Dallas"],
                8.0,
                0.9,
            ),
            (
                PeerGroup.CORPORATE,
                15500.0,
                5500.0,
                90000.0,
                [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
                ["dev_treasury_terminal_1", "dev_treasury_terminal_2"],
                ["192.0.2.150", "198.51.100.201"],
                ["New York", "Charlotte"],
                18.0,
                1.8,
            ),
            (
                PeerGroup.INTERNAL_OPERATIONS,
                350.0,
                120.0,
                1800.0,
                [9, 10, 11, 12, 13, 14, 15, 16, 17],
                ["dev_ops_bastion_01"],
                ["10.100.4.15", "10.100.4.16"],
                ["Reston", "Austin"],
                4.0,
                0.4,
            ),
        ]

        total_to_generate = 35
        for i in range(1, total_to_generate + 1):
            entity_id = f"CUS-{100000 + i}"
            cohort_idx = (i - 1) % len(cohort_configs)
            group, avg_amt, std_amt, max_amt, hours, devices, ips, cities, d_vel, h_vel = cohort_configs[cohort_idx]

            # Introduce small variations per user
            user_avg = round(avg_amt * (0.85 + (i % 5) * 0.08), 2)
            user_std = round(std_amt * (0.90 + (i % 4) * 0.07), 2)
            user_max = round(max(max_amt, user_avg * 3.5), 2)

            baseline = BehavioralBaseline(
                avg_amount=user_avg,
                std_amount=user_std,
                max_amount_historical=user_max,
                active_hours=list(hours),
                known_devices=[f"{dev}_{i}" for dev in devices],
                known_ips=[f"{ip[:-2]}.{int(ip[-2:]) + i % 10}" for ip in ips],
                known_cities=list(cities),
                daily_velocity_mean=round(d_vel * (0.9 + (i % 3) * 0.1), 2),
                hourly_velocity_mean=round(h_vel * (0.9 + (i % 3) * 0.1), 2),
            )

            # Assign a few high risk entities for realistic dashboard display
            if i in (7, 18):
                risk_score = 88.5
                risk_lvl = EntityRiskLevel.CRITICAL
                anomalies = ["IMPOSSIBLE_TRAVEL_VELOCITY", "UNUSUAL_AMOUNT_SPIKE", "NEW_DEVICE_BURST"]
            elif i in (3, 12, 27):
                risk_score = 68.0
                risk_lvl = EntityRiskLevel.HIGH
                anomalies = ["OFF_HOURS_ELEVATED_VALUE", "UNRECOGNIZED_IP_OFF_HOURS"]
            elif i in (5, 15, 23, 31):
                risk_score = 42.0
                risk_lvl = EntityRiskLevel.MEDIUM
                anomalies = ["NEW_DEVICE_BURST"]
            else:
                risk_score = round(8.0 + (i % 15) * 1.2, 1)
                risk_lvl = EntityRiskLevel.LOW
                anomalies = []

            profile = UserEntityProfile(
                entity_id=entity_id,
                entity_type="CUSTOMER" if group != PeerGroup.INTERNAL_OPERATIONS else "IAM_USER",
                peer_group=group,
                baseline=baseline,
                total_events_observed=120 + i * 15,
                current_risk_score=risk_score,
                risk_level=risk_lvl,
                active_anomalies=anomalies,
            )
            self._profiles[entity_id] = profile

    def _save_to_disk(self) -> None:
        if not self._persistence_path:
            return
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
        data = {eid: p.model_dump(mode="json") for eid, p in self._profiles.items()}
        with open(self._persistence_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_from_disk(self) -> None:
        if not self._persistence_path or not self._persistence_path.exists():
            return
        with open(self._persistence_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._profiles = {eid: UserEntityProfile.model_validate(p) for eid, p in data.items()}


_global_store: Optional[ProfileStore] = None


def get_profile_store(persistence_path: Optional[str] = None) -> ProfileStore:
    """Returns singleton profile store instance."""
    global _global_store
    if _global_store is None:
        _global_store = ProfileStore(persistence_path)
    return _global_store
