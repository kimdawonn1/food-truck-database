"""
load_and_transform.py
----------------------
Loads the CSVs produced by generate_data.py into a local SQLite database
(foodtruck.db) using the same table structure defined in sql/schema.sql,
then builds a set of downstream analytical VIEWS ("transform" / marts layer)
that answer the original business questions.

Using SQLite here keeps the project runnable with zero external
infrastructure. sql/schema.sql is written in Postgres-flavored DDL for
portfolio purposes — pointing at a real Postgres instance (e.g. via the
included docker-compose.yml) only requires swapping the connection layer
for psycopg2.

Run:
    python3 load_and_transform.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "foodtruck.db"

TABLES = {
    "truck": ["truck_id", "restaurant_name", "food_type", "owner_id"],
    "employee": ["employee_id", "emp_fn", "emp_ln", "emp_dob", "emp_start_date",
                 "emp_salary", "role", "truck_id", "boss_id"],
    "customer": ["customer_id", "customer_fn", "customer_ln", "loyalty_number", "truck_id"],
    "menu_item": ["menu_item_id", "menu_item_name", "price", "calories", "truck_id"],
    "order": ["order_id", "order_date", "order_time", "order_type", "points", "customer_id"],
    "order_has_menu_item": ["order_id", "menu_item_id", "quantity"],
    "inventory": ["item_id", "item_name", "date_purchased", "expiration_date", "truck_id", "menu_item_id"],
}

DDL = {
    "truck": """CREATE TABLE truck (
        truck_id INTEGER PRIMARY KEY, restaurant_name TEXT, food_type TEXT, owner_id INTEGER
    )""",
    "employee": """CREATE TABLE employee (
        employee_id INTEGER PRIMARY KEY, emp_fn TEXT, emp_ln TEXT, emp_dob TEXT,
        emp_start_date TEXT, emp_salary INTEGER, role TEXT, truck_id INTEGER,
        boss_id INTEGER REFERENCES employee(employee_id)
    )""",
    "customer": """CREATE TABLE customer (
        customer_id INTEGER PRIMARY KEY, customer_fn TEXT, customer_ln TEXT,
        loyalty_number TEXT, truck_id INTEGER
    )""",
    "menu_item": """CREATE TABLE menu_item (
        menu_item_id INTEGER PRIMARY KEY, menu_item_name TEXT, price REAL,
        calories INTEGER, truck_id INTEGER
    )""",
    "order": """CREATE TABLE "order" (
        order_id INTEGER PRIMARY KEY, order_date TEXT, order_time TEXT,
        order_type TEXT, points INTEGER, customer_id INTEGER
    )""",
    "order_has_menu_item": """CREATE TABLE order_has_menu_item (
        order_id INTEGER, menu_item_id INTEGER, quantity INTEGER,
        PRIMARY KEY (order_id, menu_item_id)
    )""",
    "inventory": """CREATE TABLE inventory (
        item_id INTEGER PRIMARY KEY, item_name TEXT, date_purchased TEXT,
        expiration_date TEXT, truck_id INTEGER, menu_item_id INTEGER
    )""",
}

# Load order matters for FK sanity even though SQLite FKs are soft by default
LOAD_ORDER = ["truck", "employee", "customer", "menu_item", "order", "order_has_menu_item", "inventory"]


def load_csv_to_table(conn, table, columns):
    csv_name = "order.csv" if table == "order" else f"{table}.csv"
    path = DATA_DIR / csv_name
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = [tuple(r[c] if r[c] != "" else None for c in columns) for r in reader]
    placeholders = ", ".join(["?"] * len(columns))
    quoted_table = f'"{table}"' if table == "order" else table
    conn.executemany(f"INSERT INTO {quoted_table} VALUES ({placeholders})", rows)
    print(f"  loaded {len(rows):>4} rows -> {table}")


TRANSFORM_VIEWS = {
    # mirrors "most popular menu items per truck" (Q3 in original project)
    "vw_top_menu_items_by_truck": """
        CREATE VIEW vw_top_menu_items_by_truck AS
        SELECT t.truck_id, t.restaurant_name, mi.menu_item_id, mi.menu_item_name,
               SUM(ohmi.quantity) AS total_quantity_ordered
        FROM truck t
        JOIN menu_item mi ON t.truck_id = mi.truck_id
        JOIN order_has_menu_item ohmi ON mi.menu_item_id = ohmi.menu_item_id
        GROUP BY t.truck_id, t.restaurant_name, mi.menu_item_id, mi.menu_item_name
    """,
    # mirrors "inventory expiring soon" (Q7)
    "vw_inventory_expiring_30d": """
        CREATE VIEW vw_inventory_expiring_30d AS
        SELECT t.truck_id, t.restaurant_name, COUNT(i.item_id) AS expiring_item_count
        FROM truck t
        JOIN inventory i ON t.truck_id = i.truck_id
        WHERE date(i.expiration_date) BETWEEN date('now') AND date('now', '+30 day')
        GROUP BY t.truck_id, t.restaurant_name
    """,
    # mirrors "revenue / order summary per truck" — new addition beyond original project
    "vw_revenue_by_truck": """
        CREATE VIEW vw_revenue_by_truck AS
        SELECT t.truck_id, t.restaurant_name,
               COUNT(DISTINCT o.order_id) AS order_count,
               ROUND(SUM(mi.price * ohmi.quantity), 2) AS total_revenue
        FROM truck t
        JOIN customer c ON c.truck_id = t.truck_id
        JOIN "order" o ON o.customer_id = c.customer_id
        JOIN order_has_menu_item ohmi ON ohmi.order_id = o.order_id
        JOIN menu_item mi ON mi.menu_item_id = ohmi.menu_item_id
        GROUP BY t.truck_id, t.restaurant_name
    """,
    # mirrors "employees paid more than their boss" (Q8)
    "vw_employees_paid_more_than_boss": """
        CREATE VIEW vw_employees_paid_more_than_boss AS
        SELECT t.restaurant_name AS truck_name, COUNT(e.employee_id) AS employees_paid_more_than_boss
        FROM employee e
        JOIN employee boss ON e.boss_id = boss.employee_id
        JOIN truck t ON e.truck_id = t.truck_id
        WHERE e.emp_salary > boss.emp_salary
        GROUP BY t.restaurant_name
    """,
}


def build_transform_layer(conn):
    for name, ddl in TRANSFORM_VIEWS.items():
        conn.execute(f"DROP VIEW IF EXISTS {name}")
        conn.execute(ddl)
        print(f"  built view -> {name}")


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    print("Creating schema...")
    for table in LOAD_ORDER:
        conn.execute(DDL[table])

    print("Loading data...")
    for table in LOAD_ORDER:
        load_csv_to_table(conn, table, TABLES[table])

    print("Building transform / analytics layer (views)...")
    build_transform_layer(conn)

    conn.commit()

    print("\nSample output — revenue by truck:")
    for row in conn.execute("SELECT * FROM vw_revenue_by_truck ORDER BY total_revenue DESC"):
        print(" ", row)

    conn.close()
    print(f"\nDone. Database written to {DB_PATH}")


if __name__ == "__main__":
    main()
