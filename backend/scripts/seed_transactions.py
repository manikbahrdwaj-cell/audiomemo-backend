"""
Seed the MongoDB transactions collection with realistic dummy data.

Usage (from the backend/ directory):
    python -m scripts.seed_transactions

The script is idempotent: a compound unique index on (phone_number, merchant,
timestamp) ensures that re-running the script does not create duplicates.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import DuplicateKeyError
except ImportError:
    print("ERROR: pymongo is not installed. Run: pip install pymongo", file=sys.stderr)
    sys.exit(1)

try:
    from app.core.config import settings
    MONGODB_URL: str = settings.MONGODB_URL
    DATABASE_NAME: str = settings.DATABASE_NAME
except Exception:
    import os
    MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "voice_biometric")

# ---------------------------------------------------------------------------
# Seed data — fixed timestamps so reruns are idempotent
# ---------------------------------------------------------------------------
# Anchor point: 90 days before 2026-02-26 UTC
_BASE = datetime(2026, 2, 26, tzinfo=timezone.utc)


def _ts(days_ago: int, hour: int = 12) -> datetime:
    """Return a fixed UTC datetime *days_ago* days before the anchor."""
    return _BASE - timedelta(days=days_ago, hours=-hour)


SEED_DATA: list[tuple] = [
    # -------------------------------------------------------------------------
    # Phone +14155551001
    # -------------------------------------------------------------------------
    ("+14155551001", 47.32,  "Whole Foods Market",     "Grocery",       _ts(85, 9)),
    ("+14155551001",  4.75,  "Blue Bottle Coffee",     "Coffee",        _ts(80, 8)),
    ("+14155551001", 62.10,  "Shell Gas Station",      "Fuel",          _ts(72, 17)),
    ("+14155551001", 129.99, "Amazon",                 "Online Retail", _ts(60, 14)),
    ("+14155551001", 23.50,  "Chipotle Mexican Grill", "Restaurant",    _ts(45, 13)),
    ("+14155551001",  5.25,  "Starbucks",              "Coffee",        _ts(30, 8)),
    ("+14155551001", 89.40,  "Safeway",                "Grocery",       _ts(15, 18)),
    ("+14155551001", 310.00, "Apple Store",            "Online Retail", _ts(5, 11)),

    # -------------------------------------------------------------------------
    # Phone +14155551002
    # -------------------------------------------------------------------------
    ("+14155551002",  3.50,  "Peet's Coffee",          "Coffee",        _ts(88, 7)),
    ("+14155551002", 54.80,  "Trader Joe's",           "Grocery",       _ts(75, 16)),
    ("+14155551002", 450.00, "Best Buy",               "Online Retail", _ts(65, 13)),
    ("+14155551002", 38.95,  "Chevron",                "Fuel",          _ts(50, 10)),
    ("+14155551002", 19.99,  "Panda Express",          "Restaurant",    _ts(40, 12)),
    ("+14155551002", 210.00, "Nike.com",               "Online Retail", _ts(22, 20)),
    ("+14155551002",  7.80,  "Dunkin'",                "Coffee",        _ts(10, 8)),

    # -------------------------------------------------------------------------
    # Phone +14155551003
    # -------------------------------------------------------------------------
    ("+14155551003", 112.45, "Costco",                 "Grocery",       _ts(82, 11)),
    ("+14155551003",  6.10,  "Philz Coffee",           "Coffee",        _ts(70, 8)),
    ("+14155551003",  78.60, "BP Gas",                 "Fuel",          _ts(58, 15)),
    ("+14155551003", 39.99,  "Uber Eats",              "Restaurant",    _ts(48, 20)),
    ("+14155551003", 199.00, "Walmart",                "Online Retail", _ts(35, 14)),
    ("+14155551003",  11.75, "The Cheesecake Factory", "Restaurant",    _ts(20, 19)),
    ("+14155551003",  55.00, "Target",                 "Online Retail", _ts(8, 10)),

    # -------------------------------------------------------------------------
    # Phone +14155551004  (bonus 4th number)
    # -------------------------------------------------------------------------
    ("+14155551004", 28.40,  "Sprouts Farmers Market", "Grocery",       _ts(87, 9)),
    ("+14155551004",  4.20,  "Verve Coffee Roasters",  "Coffee",        _ts(76, 7)),
    ("+14155551004", 45.00,  "76 Gas Station",         "Fuel",          _ts(55, 16)),
    ("+14155551004", 375.00, "Newegg",                 "Online Retail", _ts(42, 13)),
    ("+14155551004", 14.60,  "Subway",                 "Restaurant",    _ts(28, 12)),
    ("+14155551004",  8.95,  "Intelligentsia Coffee",  "Coffee",        _ts(12, 8)),
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Connecting to MongoDB at {MONGODB_URL} …")
    client = MongoClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    col = db["transactions"]

    # Ensure compound unique index for idempotency.
    col.create_index(
        [("phone_number", ASCENDING), ("merchant", ASCENDING), ("timestamp", ASCENDING)],
        unique=True,
        name="uq_phone_merchant_ts",
    )
    col.create_index([("phone_number", ASCENDING), ("timestamp", DESCENDING)])
    print("Indexes ensured.")

    inserted_by_phone: dict[str, int] = {}

    for phone, amount, merchant, category, timestamp in SEED_DATA:
        doc = {
            "phone_number": phone,
            "amount": float(amount),
            "merchant": merchant,
            "category": category,
            "timestamp": timestamp,
        }
        try:
            col.insert_one(doc)
            inserted_by_phone[phone] = inserted_by_phone.get(phone, 0) + 1
        except DuplicateKeyError:
            pass  # already seeded

    client.close()

    print("\nSeed summary (rows newly inserted):")
    for phone, count in sorted(inserted_by_phone.items()):
        print(f"  {phone}: {count} row(s)")
    total = sum(inserted_by_phone.values())
    print(f"\nTotal rows inserted: {total} / {len(SEED_DATA)}")


if __name__ == "__main__":
    main()
