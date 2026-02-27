"""
Seed the MongoDB transactions collection with realistic dummy data.

Usage (from the backend/ directory):
    python -m scripts.seed_transactions

Transactions are identified by ``user_id``, which is the str(_id) of the
corresponding ``voice_embeddings`` document.  The script looks up each phone
number in ``voice_embeddings`` first; phones that have not been enrolled are
skipped with a warning.

The script is idempotent: a compound unique index on (user_id, merchant,
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
# SEED_DATA: (phone_number, amount, merchant, category, timestamp)
# phone_number is resolved to a voice_embeddings _id at runtime.
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
    # Phone 1234567890  (test user)
    # -------------------------------------------------------------------------
    ("1234567890", 52.30,  "Whole Foods Market",     "Grocery",       _ts(83, 10)),
    ("1234567890",  4.50,  "Starbucks",              "Coffee",        _ts(78, 8)),
    ("1234567890", 71.20,  "Shell Gas Station",      "Fuel",          _ts(65, 17)),
    ("1234567890", 149.99, "Amazon",                 "Online Retail", _ts(50, 14)),
    ("1234567890", 18.75,  "Chipotle Mexican Grill", "Restaurant",    _ts(35, 13)),
    ("1234567890",  6.00,  "Blue Bottle Coffee",     "Coffee",        _ts(20, 8)),
    ("1234567890", 95.40,  "Safeway",                "Grocery",       _ts(10, 18)),
    ("1234567890", 249.00, "Apple Store",            "Online Retail", _ts(3, 11)),
    ("1234567890", 33.60,  "Uber Eats",              "Restaurant",    _ts(1, 20)),
    ("1234567890",  8.25,  "Peet's Coffee",          "Coffee",        _ts(0, 9)),

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
    embeddings_col = db["voice_embeddings"]
    col = db["transactions"]

    # --- Build phone → user_id map from voice_embeddings ----------------------
    phone_to_user_id: dict[str, str] = {}
    all_phones = {row[0] for row in SEED_DATA}
    for phone in all_phones:
        doc = embeddings_col.find_one({"phone_number": phone}, {"_id": 1})
        if doc:
            phone_to_user_id[phone] = str(doc["_id"])
        else:
            print(f"  WARNING: no voice_embedding found for phone {phone!r} — skipping their transactions")

    if not phone_to_user_id:
        print("No enrolled phones found in voice_embeddings. Enroll users first, then re-run.")
        client.close()
        return

    print(f"Resolved {len(phone_to_user_id)} phone(s) to user_id(s):")
    for phone, uid in sorted(phone_to_user_id.items()):
        print(f"  {phone} → {uid}")

    # --- Ensure indexes --------------------------------------------------------
    col.create_index(
        [("user_id", ASCENDING), ("merchant", ASCENDING), ("timestamp", ASCENDING)],
        unique=True,
        name="uq_user_merchant_ts",
    )
    col.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
    print("Indexes ensured.")

    inserted_by_phone: dict[str, int] = {}

    for phone, amount, merchant, category, timestamp in SEED_DATA:
        user_id = phone_to_user_id.get(phone)
        if user_id is None:
            continue  # phone not enrolled — already warned above
        doc = {
            "user_id": user_id,
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
        uid = phone_to_user_id.get(phone, "?")
        print(f"  {phone} ({uid[:8]}…): {count} row(s)")
    total = sum(inserted_by_phone.values())
    print(f"\nTotal rows inserted: {total} / {len([r for r in SEED_DATA if r[0] in phone_to_user_id])}")


if __name__ == "__main__":
    main()
