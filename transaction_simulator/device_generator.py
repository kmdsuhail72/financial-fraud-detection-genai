"""
Device Registry Generator for Banking Simulator.
Maintains known customer device fingerprints and IP allocations.
"""
import random
from typing import Dict, List
from transaction_simulator.config import DOC_IP_PREFIXES

DEVICE_TYPES = ["iOS_Smartphone", "Android_Smartphone", "MacOS_Workstation", "Windows_Laptop"]


class DeviceGenerator:
    """Generates customer device registry records."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, customers: List[Dict]) -> List[Dict]:
        devices = []
        dev_seq = 40000

        for cust in customers:
            customer_id = cust["customer_id"]
            num_devices = self.rng.choices([1, 2, 3], weights=[0.60, 0.30, 0.10], k=1)[0]

            for d_idx in range(num_devices):
                dev_seq += 1
                device_id = f"DEV-{dev_seq:05d}"
                device_type = self.rng.choice(DEVICE_TYPES)
                prefix = self.rng.choice(DOC_IP_PREFIXES)
                ip_address = f"{prefix}{self.rng.randint(2, 250)}"

                device = {
                    "device_id": device_id,
                    "customer_id": customer_id,
                    "device_type": device_type,
                    "primary_ip": ip_address,
                    "is_primary": (d_idx == 0),
                    "registered_at": "2025-06-01T00:00:00Z"
                }
                devices.append(device)

        return devices

