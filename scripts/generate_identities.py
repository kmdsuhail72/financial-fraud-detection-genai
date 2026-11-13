"""
FinGuard AI — Phase 27: Synthetic Identity Data Generator
Generates synthetic customer identities with controlled collision rates across phones,
emails, physical addresses, devices, and documents.
"""
import argparse
import json
import random
import os
from pathlib import Path

FIRST_NAMES = [
    "Alex", "Jordan", "Morgan", "Taylor", "Casey", "Riley", "Sam", "Chris",
    "Pat", "Jamie", "Robin", "Logan", "Jesse", "Avery", "Cameron", "Dakota"
]
LAST_NAMES = [
    "Mercer", "Vance", "Cross", "Hayes", "Sinclair", "Sterling", "Hawthorne",
    "Barrett", "Fletcher", "Montgomery", "Carrington", "Prescott", "Blackwood"
]
STREETS = [
    "742 Evergreen Terr", "100 Industrial Pkwy", "452 Elm Street",
    "88 Ocean Avenue", "1200 Sunset Blvd", "350 5th Avenue", "221B Baker St"
]
CITIES = ["Springfield", "Metropolis", "Gotham", "Starling", "Coast City", "Keystone"]


def generate_synthetic_dataset(num_customers: int, shared_rate: float, seed: int):
    random.seed(seed)
    customers = []

    # Shared pools for collision planting
    shared_phones = [f"+1-555-88{i:02d}" for i in range(5)]
    shared_addresses = [f"{random.choice(STREETS)}, {random.choice(CITIES)}" for _ in range(5)]
    shared_devices = [f"DEV-EMULATOR-{i:03d}" for i in range(5)]
    shared_emails = [f"shared.syndicate.{i}@tempinbox-demo.com" for i in range(5)]

    for i in range(1, num_customers + 1):
        cid = f"CUST-SYN-{i:04d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        full_name = f"{fname} {lname}"

        # Decide if this customer shares attributes
        if random.random() < shared_rate:
            phone = random.choice(shared_phones)
            address = random.choice(shared_addresses)
            device_id = random.choice(shared_devices)
            email = random.choice(shared_emails) if random.random() < 0.5 else f"{fname.lower()}.{lname.lower()}{i}@example-demo.com"
            doc_id = f"DOC-SYN-COLLIDE-{random.randint(1, 3):03d}" if random.random() < 0.25 else f"DOC-SYN-{i:04d}"
            kyc_status = "EDD_REQUIRED" if random.random() < 0.7 else "PENDING_REVIEW"
            doc_status = "INCONSISTENT_FIELDS" if random.random() < 0.4 else "VERIFIED_AUTHENTIC_BYTES"
        else:
            phone = f"+1-555-{random.randint(1000, 9999)}"
            address = f"{random.randint(10, 999)} {random.choice(STREETS)}, {random.choice(CITIES)}"
            device_id = f"DEV-MOB-{uuid_segment(i)}"
            email = f"{fname.lower()}.{lname.lower()}{i}@legit-demo.org"
            doc_id = f"DOC-SYN-{i:04d}"
            kyc_status = "APPROVED" if random.random() < 0.8 else "PENDING_REVIEW"
            doc_status = "VERIFIED_AUTHENTIC_BYTES"

        customers.append({
            "customer_id": cid,
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "address": address,
            "device_id": device_id,
            "ip_address": f"198.51.{random.randint(1, 254)}.{random.randint(1, 254)}",
            "document_id": doc_id,
            "kyc_status": kyc_status,
            "doc_verification_status": doc_status
        })

    return customers


def uuid_segment(n: int) -> str:
    return f"{n:06x}".upper()


def main():
    parser = argparse.ArgumentParser(description="FinGuard AI Phase 27 Synthetic Identity Generator")
    parser.add_argument("--customers", type=int, default=100, help="Number of customer identities to generate")
    parser.add_argument("--shared-entity-rate", type=float, default=0.12, help="Proportion of entities sharing attributes")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="examples/synthetic_identities.json", help="Output path")
    args = parser.parse_args()

    data = generate_synthetic_dataset(args.customers, args.shared_entity_rate, args.seed)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Generated {len(data)} synthetic identities with shared rate {args.shared_entity_rate} to {out_path}")


if __name__ == "__main__":
    main()
