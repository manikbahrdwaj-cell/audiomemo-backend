"""
Seed the PostgreSQL transactions table with realistic dummy data.

Usage (from the backend/ directory):
    python -m scripts.seed_transactions

The script is idempotent: running it multiple times will not insert
duplicate rows because the table has a UNIQUE constraint on
(phone_number, merchant, timestamp) and all inserts use ON CONFLICT DO NOTHING.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Resolve DATABASE_URL — try app settings first, fall back to env var.
# ---------------------------------------------------------------------------
try:
    from app.core.config import settings
    DATABASE_URL: str = settings.DATABASE_URL
except Exception:
    DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    print(
        "ERROR: DATABASE_URL is not configured. "
        "Set it in .env or as an environment variable.",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print(
        "ERROR: psycopg2 is not installed. Run: pip install psycopg2-binary",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS transactions (
    id           SERIAL PRIMARY KEY,
    phone_number VARCHAR(20)     NOT NULL,
    amount       NUMERIC(10, 2)  NOT NULL,
    merchant     VARCHAR(100)    NOT NULL,
    category     VARCHAR(50)     NOT NULL,
    timestamp    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (phone_number, merchant, timestamp)
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_transactions_phone ON transactions (phone_number);
"""

INSERT_SQL = """
INSERT INTO transactions (phone_number, amount, merchant, category, timestamp)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT DO NOTHING;
"""

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
    print(f"Connecting to database …")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # Create table and index
            cur.execute(CREATE_TABLE_SQL)
            cur.execute(CREATE_INDEX_SQL)
            conn.commit()
            print("Table and index ensured.")

            # Insert rows
            inserted_by_phone: dict[str, int] = {}

            for row in SEED_DATA:
                phone = row[0]
                cur.execute(INSERT_SQL, row)
                rows_affected = cur.rowcount  # 1 if inserted, 0 on conflict
                inserted_by_phone[phone] = inserted_by_phone.get(phone, 0) + rows_affected

            conn.commit()

        # Summary
        print("\nSeed summary (rows newly inserted):")
        for phone, count in sorted(inserted_by_phone.items()):
            print(f"  {phone}: {count} row(s)")
        total = sum(inserted_by_phone.values())
        print(f"\nTotal rows inserted: {total} / {len(SEED_DATA)}")

    except Exception as exc:
        conn.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
