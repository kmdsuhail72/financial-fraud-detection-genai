"""
Configuration, Constants and Reference Data for Banking Transaction Simulator.
"""
from datetime import datetime, timezone
from typing import Dict, List

# Indian and global major cities for realistic location synthesis
CITIES_INDIA = [
    {"city": "Mumbai", "country": "IN", "weight": 0.25},
    {"city": "Delhi", "country": "IN", "weight": 0.20},
    {"city": "Bengaluru", "country": "IN", "weight": 0.18},
    {"city": "Kolkata", "country": "IN", "weight": 0.12},
    {"city": "Hyderabad", "country": "IN", "weight": 0.10},
    {"city": "Chennai", "country": "IN", "weight": 0.08},
    {"city": "Pune", "country": "IN", "weight": 0.07},
]

CITIES_INTERNATIONAL = [
    {"city": "London", "country": "GB"},
    {"city": "Dubai", "country": "AE"},
    {"city": "Singapore", "country": "SG"},
    {"city": "New York", "country": "US"},
    {"city": "Bangkok", "country": "TH"},
    {"city": "Paris", "country": "FR"},
]

# Merchant categories and their baseline fraud risk weighting (0.0 to 1.0)
MERCHANT_CATEGORIES: Dict[str, Dict] = {
    "GROCERY": {"risk": 0.05, "avg_amount": 2500, "std_amount": 1200},
    "DINING": {"risk": 0.08, "avg_amount": 1800, "std_amount": 900},
    "UTILITIES": {"risk": 0.03, "avg_amount": 3200, "std_amount": 1500},
    "ENTERTAINMENT": {"risk": 0.12, "avg_amount": 1500, "std_amount": 800},
    "ELECTRONICS": {"risk": 0.42, "avg_amount": 42000, "std_amount": 25000},
    "TRAVEL": {"risk": 0.38, "avg_amount": 35000, "std_amount": 20000},
    "JEWELRY": {"risk": 0.55, "avg_amount": 75000, "std_amount": 40000},
    "TRANSFER": {"risk": 0.25, "avg_amount": 20000, "std_amount": 15000},
}

TRANSACTION_TYPES = [
    "CARD_PAYMENT",
    "UPI_TRANSFER",
    "ATM_WITHDRAWAL",
    "WIRE_TRANSFER",
    "ONLINE_BANKING",
]

CHANNELS = ["MOBILE", "WEB", "POS", "ATM"]

ACCOUNT_TYPES = ["SAVINGS", "CURRENT", "CREDIT_CARD"]

RISK_SEGMENTS = ["LOW", "STANDARD", "HIGH_NET_WORTH"]

# Synthetic First and Last Names for Banking Customers
FIRST_NAMES = [
    "Aarav", "Aditi", "Amit", "Ananya", "Arjun", "Deepak", "Divya", "Ishaan",
    "Kavita", "Manish", "Meera", "Neha", "Nikhil", "Pooja", "Pranav", "Priya",
    "Rahul", "Rakesh", "Riya", "Rohan", "Sanjay", "Shreya", "Sneha", "Suhail",
    "Sunita", "Tarun", "Varun", "Vikas", "Vikram", "Zoya"
]

LAST_NAMES = [
    "Agarwal", "Bose", "Chatterjee", "Das", "Dutta", "Gupta", "Joshi", "Kapoor",
    "Khan", "Kumar", "Mehta", "Mishra", "Mukherjee", "Nair", "Patel", "Reddy",
    "Roy", "Sen", "Sharma", "Singh", "Verma", "Yadav"
]

# Reserved documentation IP blocks (RFC 5737) to prevent collisions with real IPs
DOC_IP_PREFIXES = [
    "192.0.2.",
    "198.51.100.",
    "203.0.113."
]

DEFAULT_SIMULATION_START = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
