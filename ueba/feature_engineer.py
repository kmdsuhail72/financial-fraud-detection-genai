"""Behavioral Feature Engineering for User and Entity Behavior Analytics."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import numpy as np
from pydantic import BaseModel

from ueba.models import BehavioralBaseline, BehavioralFeatures


class UEBAFeatureEngineer:
    """Calculates point-in-time deviation metrics between incoming activity and entity baselines."""

    @classmethod
    def extract_features(
        cls,
        event: Union[Dict[str, Any], BaseModel],
        baseline: BehavioralBaseline,
    ) -> BehavioralFeatures:
        """Extracts structured behavioral features comparing event to historical baseline."""
        if isinstance(event, BaseModel):
            event_dict = event.model_dump()
        else:
            event_dict = event

        amount = float(event_dict.get("amount", 0.0))
        hour = event_dict.get("hour_of_day")
        if hour is None and "timestamp" in event_dict:
            try:
                dt = datetime.fromisoformat(str(event_dict["timestamp"]).replace("Z", "+00:00"))
                hour = dt.hour
            except Exception:
                hour = 12

        device_id = event_dict.get("device_id")
        ip_address = event_dict.get("ip_address")
        city = event_dict.get("city")
        v1h = int(event_dict.get("velocity_1h", 1))
        v24h = int(event_dict.get("velocity_24h", 1))

        # 1. Amount deviations
        avg_amt = max(baseline.avg_amount, 1.0)
        std_amt = max(baseline.std_amount, 1.0)
        dev_ratio = amount / avg_amt
        amount_z = (amount - avg_amt) / std_amt

        # 2. Temporal & device/network novelty
        is_off_hours = False
        if hour is not None and baseline.active_hours:
            is_off_hours = int(hour) not in baseline.active_hours

        is_new_dev = False
        if device_id and baseline.known_devices:
            is_new_dev = device_id not in baseline.known_devices

        is_new_ip = False
        if ip_address and baseline.known_ips:
            is_new_ip = ip_address not in baseline.known_ips

        is_new_city = False
        if city and baseline.known_cities:
            is_new_city = city not in baseline.known_cities

        # 3. Velocity deviation
        mean_v24 = max(baseline.daily_velocity_mean, 1.0)
        v_z = (v24h - mean_v24) / max(mean_v24 * 0.5, 1.0)

        # 4. Impossible travel proxy (new city with rapid 1h velocity)
        impossible_travel = bool(is_new_city and v1h >= 2)

        return BehavioralFeatures(
            amount=amount,
            amount_deviation_ratio=round(dev_ratio, 2),
            amount_z_score=round(amount_z, 2),
            is_off_hours=is_off_hours,
            is_new_device=is_new_dev,
            is_new_ip=is_new_ip,
            is_new_city=is_new_city,
            velocity_1h=v1h,
            velocity_24h=v24h,
            velocity_z_score=round(v_z, 2),
            impossible_travel_flag=impossible_travel,
        )

    @classmethod
    def to_feature_vector(cls, features: BehavioralFeatures) -> np.ndarray:
        """Converts BehavioralFeatures into a standardized numpy vector for Isolation Forest."""
        return np.array(
            [
                features.amount_deviation_ratio,
                features.amount_z_score,
                1.0 if features.is_off_hours else 0.0,
                1.0 if features.is_new_device else 0.0,
                1.0 if features.is_new_ip else 0.0,
                1.0 if features.is_new_city else 0.0,
                float(features.velocity_1h),
                features.velocity_z_score,
            ],
            dtype=np.float32,
        )

    @classmethod
    def get_feature_names(cls) -> List[str]:
        return [
            "amount_deviation_ratio",
            "amount_z_score",
            "is_off_hours",
            "is_new_device",
            "is_new_ip",
            "is_new_city",
            "velocity_1h",
            "velocity_z_score",
        ]
