"""
Synthetic Merchant Generator for FinGuard AI Simulator.
Generates realistic merchants across various categories with calibrated risk baselines.
"""
import random
from typing import Dict, List
from transaction_simulator.config import CITIES_INDIA, MERCHANT_CATEGORIES

MERCHANT_NAME_PREFIXES = {
    "GROCERY": ["FreshBazaar", "DailyMart", "Spencers", "SmartSupermarket", "OrganicAcre"],
    "DINING": ["SpiceKitchen", "CurryHouse", "BaristaCorner", "UrbanDiner", "RoyalFeast"],
    "UTILITIES": ["PowerGridDirect", "MetropolitanWater", "CityGasLine", "TelecomBillPay"],
    "ENTERTAINMENT": ["StarCinemas", "PlayZoneHub", "ConcertVibe", "GameWorldNetwork"],
    "ELECTRONICS": ["ApexGigaTech", "ElectroBazaar", "PixelGizmos", "SiliconHaven", "CircuitMaster"],
    "TRAVEL": ["SkyVoyagerAirlines", "GrandPalaceHotels", "GlobalTours", "ExpressRailPay"],
    "JEWELRY": ["KalyanDiamonds", "TanishqAura", "GoldLoomGems", "ImperialJewels"],
    "TRANSFER": ["FastUPIPay", "ExpressWireGateway", "InstantRemit", "P2PNexus"]
}


class MerchantGenerator:
    """Generates synthetic merchants with realistic risk scores."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, count: int = 200) -> List[Dict]:
        merchants = []
        categories = list(MERCHANT_CATEGORIES.keys())
        cities = [c["city"] for c in CITIES_INDIA]

        for i in range(1, count + 1):
            merchant_id = f"MER-{90000 + i:05d}"
            category = self.rng.choice(categories)
            base_risk = MERCHANT_CATEGORIES[category]["risk"]

            # Add minor noise to baseline risk
            risk_score = round(max(0.01, min(0.99, base_risk + self.rng.uniform(-0.04, 0.04))), 4)

            name_prefix = self.rng.choice(MERCHANT_NAME_PREFIXES.get(category, ["Merchant"]))
            name = f"{name_prefix} {self.rng.choice(cities)}"
            city = self.rng.choice(cities)

            merchant = {
                "merchant_id": merchant_id,
                "merchant_name": name,
                "merchant_category": category,
                "merchant_risk": risk_score,
                "country": "IN",
                "city": city,
                "is_active": True
            }
            merchants.append(merchant)

        return merchants
