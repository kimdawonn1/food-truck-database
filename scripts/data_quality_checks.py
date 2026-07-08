"""
data_quality_checks.py
-----------------------
Lightweight, dependency-free data quality gate for the warehouse layer
(foodtruck.db). Runs after load_and_transform.py and validates:

  1. Row-count sanity   — every table has data, and falls within an
                           expected range (catches empty/partial loads).
  2. Null-rate checks   — required (NOT NULL, per sql/schema.sql) columns
                           have 0% nulls in the loaded data.
  3. Referential integrity — every foreign key value actually exists in
                           its parent table (SQLite does not enforce
                           this by default even with PRAGMA foreign_keys
                           ON for data inserted out of order/via CSV).
  4. Primary key uniqueness — no duplicate PKs slipped in.

Each check is assert-based and self-contained. Failures are collected
(not raised immediately) so a single run reports everything wrong at
once, then the script exits non-zero if anything failed — the same
signal a CI job or orchestrator (Airflow/Prefect) would key off of.

Run:
    python3 scripts/data_quality_checks.py

Exit code:
    0  -> all checks passed
    1  -> one or more checks failed (see printed report)
"""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "foodtruck.db"

# ---------------------------------------------------------------------------
# Expectations, derived from scripts/generate_data.py volumes and
# sql/schema.sql NOT NULL / FK constraints. Row-count ranges are loose
# on purpose -- they're meant to catch "load produced 0 rows" or
# "load silently truncated," not to hardcode exact fixture sizes.
# ---------------------------------------------------------------------------
EXPECTED_ROW_RANGES = {
    "truck": (4, 4),
    "employee": (90, 110),
    "customer": (55, 65),
    "menu_item": (25, 40),
    "order": (90, 110),
    "order_has_menu_item": (90, 400),
    "inventory": (85, 105),
}

# columns that are NOT NULL in sql/schema.sql
REQUIRED_NOT_NULL = {
    "truck": ["restaurant_name", "food_type"],
    "employee": ["emp_fn", "emp_ln"],
    "customer": ["customer_fn", "customer_ln"],
    "menu_item": ["menu_item_name", "price"],
    "order": ["order_date", "order_time"],
    "order_has_menu_item": ["order_id", "menu_item_id", "quantity"],
    "inventory": ["item_name"],
}

# (child_table, fk_column, parent_table, parent_pk) -- nullable FKs are
# skipped automatically (a NULL FK, e.g. employee.boss_id for a head
# boss, is valid and not an integrity violation).
FOREIGN_KEYS = [
    ("employee", "truck_id", "truck", "truck_id"),
    ("employee", "boss_id", "employee", "employee_id"),
    ("customer", "truck_id", "truck", "truck_id"),
    ("menu_item", "truck_id", "truck", "truck_id"),
    ("order", "customer_id", "customer", "customer_id"),
    ("order_has_menu_item", "order_id", "order", "order_id"),
    ("order_has_menu_item", "menu_item_id", "menu_item", "menu_item_id"),
    ("inventory", "truck_id", "truck", "truck_id"),
    ("inventory", "menu_item_id", "menu_item", "menu_item_id"),
]

PRIMARY_KEYS = {
    "truck": "truck_id",
    "employee": "employee_id",
    "customer": "customer_id",
    "menu_item": "menu_item_id",
    "order": "order_id",
    "inventory": "item_id",
}


class CheckFailure(Exception):
    pass


def q(table):
    """Quote table names that collide with SQL keywords."""
    return f'"{table}"' if table == "order" else table


def check_row_counts(conn, failures):
    print("\n[1/4] Row-count sanity checks")
    for table, (lo, hi) in EXPECTED_ROW_RANGES.items():
        count = conn.execute(f"SELECT COUNT(*) FROM {q(table)}").fetchone()[0]
        try:
            assert count > 0, f"{table} is EMPTY (0 rows)"
            assert lo <= count <= hi, (
                f"{table} row count {count} outside expected range [{lo}, {hi}]"
            )
            print(f"  OK   {table:<24} {count} rows")
        except AssertionError as e:
            print(f"  FAIL {table:<24} {e}")
            failures.append(str(e))


def check_null_rates(conn, failures):
    print("\n[2/4] Null-rate checks (required columns)")
    for table, columns in REQUIRED_NOT_NULL.items():
        for col in columns:
            total = conn.execute(f"SELECT COUNT(*) FROM {q(table)}").fetchone()[0]
            if total == 0:
                continue  # already flagged by the row-count check
            nulls = conn.execute(
                f"SELECT COUNT(*) FROM {q(table)} WHERE {col} IS NULL"
            ).fetchone()[0]
            null_rate = nulls / total
            try:
                assert null_rate == 0, (
                    f"{table}.{col} has {nulls}/{total} nulls "
                    f"({null_rate:.1%}) -- expected 0"
                )
                print(f"  OK   {table}.{col:<20} 0% null")
            except AssertionError as e:
                print(f"  FAIL {table}.{col:<20} {e}")
                failures.append(str(e))


def check_referential_integrity(conn, failures):
    print("\n[3/4] Referential integrity checks")
    for child, fk_col, parent, parent_pk in FOREIGN_KEYS:
        orphans = conn.execute(f"""
            SELECT COUNT(*) FROM {q(child)}
            WHERE {fk_col} IS NOT NULL
              AND {fk_col} NOT IN (SELECT {parent_pk} FROM {q(parent)})
        """).fetchone()[0]
        label = f"{child}.{fk_col} -> {parent}.{parent_pk}"
        try:
            assert orphans == 0, f"{label} has {orphans} orphaned reference(s)"
            print(f"  OK   {label}")
        except AssertionError as e:
            print(f"  FAIL {label:<45} {e}")
            failures.append(str(e))


def check_primary_key_uniqueness(conn, failures):
    print("\n[4/4] Primary key uniqueness checks")
    for table, pk in PRIMARY_KEYS.items():
        total = conn.execute(f"SELECT COUNT(*) FROM {q(table)}").fetchone()[0]
        distinct = conn.execute(f"SELECT COUNT(DISTINCT {pk}) FROM {q(table)}").fetchone()[0]
        try:
            assert total == distinct, (
                f"{table}.{pk} has {total - distinct} duplicate value(s)"
            )
            print(f"  OK   {table}.{pk}")
        except AssertionError as e:
            print(f"  FAIL {table}.{pk:<20} {e}")
            failures.append(str(e))

    # order_has_menu_item has a composite PK, not a single-column one
    total = conn.execute("SELECT COUNT(*) FROM order_has_menu_item").fetchone()[0]
    distinct = conn.execute(
        "SELECT COUNT(*) FROM (SELECT DISTINCT order_id, menu_item_id FROM order_has_menu_item)"
    ).fetchone()[0]
    try:
        assert total == distinct, (
            f"order_has_menu_item (order_id, menu_item_id) has "
            f"{total - distinct} duplicate composite key(s)"
        )
        print("  OK   order_has_menu_item(order_id, menu_item_id)")
    except AssertionError as e:
        print(f"  FAIL order_has_menu_item(order_id, menu_item_id)  {e}")
        failures.append(str(e))


def main():
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found. Run load_and_transform.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    failures = []

    print("Running data quality checks against foodtruck.db")
    print("=" * 60)

    check_row_counts(conn, failures)
    check_null_rates(conn, failures)
    check_referential_integrity(conn, failures)
    check_primary_key_uniqueness(conn, failures)

    conn.close()

    print("\n" + "=" * 60)
    if failures:
        print(f"RESULT: {len(failures)} check(s) FAILED\n")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("RESULT: all data quality checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
