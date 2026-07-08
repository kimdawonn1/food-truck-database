"""
generate_data.py
-----------------
Synthetic data generator for the Food Truck data platform.

This replaces the manual "ask ChatGPT for N rows, count them, ask again"
workflow from the original class project with a deterministic, seeded,
referential-integrity-safe generator. Output is a set of CSV files in /data
that mirror the tables defined in sql/schema.sql, ready to be loaded by
scripts/load_and_transform.py.

Run:
    python3 generate_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
TRUCKS = [
    {"truck_id": 1, "restaurant_name": "Lex Mex", "food_type": "Mexican"},
    {"truck_id": 2, "restaurant_name": "Mac Mart", "food_type": "Mac & Cheese"},
    {"truck_id": 3, "restaurant_name": "Oink-Moo BBQ", "food_type": "BBQ"},
    {"truck_id": 4, "restaurant_name": "Mr. H's Donuts", "food_type": "Donuts"},
]

MENU_BY_TRUCK = {
    1: [("Taco", 3.50, 300), ("Burrito", 8.00, 650), ("Quesadilla", 6.50, 550),
        ("Nachos", 7.00, 720), ("Tacos al Pastor", 9.00, 610), ("Mexican Street Corn", 4.00, 240),
        ("Churros", 4.50, 380)],
    2: [("Classic Mac & Cheese", 7.00, 540), ("Bacon Mac & Cheese", 8.50, 680),
        ("BBQ Mac & Cheese", 8.50, 660), ("Buffalo Chicken Mac & Cheese", 9.00, 700),
        ("Truffle Mac & Cheese", 10.00, 610), ("Veggie Mac & Cheese", 7.50, 480)],
    3: [("Pulled Pork Sandwich", 8.50, 640), ("Beef Brisket Sandwich", 9.50, 700),
        ("BBQ Ribs", 12.00, 820), ("BBQ Sliders", 7.00, 460), ("Grilled Chicken Sandwich", 8.00, 520),
        ("Mac & Cheese", 6.00, 450), ("Cornbread", 3.00, 260), ("Sweet Potato Fries", 4.50, 380)],
    4: [("Glazed Donut", 2.00, 240), ("Chocolate-Filled Donut", 2.50, 310), ("Maple Bacon Donut", 3.00, 350),
        ("Powdered Donut", 2.00, 230), ("Lemon Glazed Donut", 2.50, 260), ("Vegan Donut", 3.00, 220),
        ("Cinnamon Sugar Donut", 2.25, 250), ("Donut Holes", 3.50, 300), ("Ice Cream Sandwich Donut", 4.50, 420)],
}

ROLES = ["Owner", "Manager", "Cook", "Cashier", "Prep Cook", "Server"]
ORDER_TYPES = ["Dine-In", "Pickup", "Delivery"]


def rand_date(start_year=2022, end_year=2025):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


# ---------------------------------------------------------------------------
# Employees (100), with per-truck boss hierarchy + recursive bossID
# ---------------------------------------------------------------------------
def generate_employees(n=100):
    employees = []
    emp_id = 1
    per_truck = n // len(TRUCKS)

    for truck in TRUCKS:
        truck_id = truck["truck_id"]
        # Head boss for this truck (bossID = NULL) — this becomes the owner
        head_boss_id = emp_id
        employees.append({
            "employee_id": emp_id,
            "emp_fn": fake.first_name(),
            "emp_ln": fake.last_name(),
            "emp_dob": fake.date_of_birth(minimum_age=30, maximum_age=65).isoformat(),
            "emp_start_date": rand_date(2018, 2021).isoformat(),
            "emp_salary": random.randint(65000, 95000),
            "role": "Owner",
            "truck_id": truck_id,
            "boss_id": "",
        })
        emp_id += 1

        # Managers report to head boss
        n_managers = 2
        manager_ids = []
        for _ in range(n_managers):
            employees.append({
                "employee_id": emp_id,
                "emp_fn": fake.first_name(),
                "emp_ln": fake.last_name(),
                "emp_dob": fake.date_of_birth(minimum_age=25, maximum_age=55).isoformat(),
                "emp_start_date": rand_date(2019, 2023).isoformat(),
                "emp_salary": random.randint(45000, 60000),
                "role": "Manager",
                "truck_id": truck_id,
                "boss_id": head_boss_id,
            })
            manager_ids.append(emp_id)
            emp_id += 1

        # Remaining staff report to a random manager
        remaining = per_truck - 1 - n_managers
        for _ in range(remaining):
            if emp_id > n:
                break
            employees.append({
                "employee_id": emp_id,
                "emp_fn": fake.first_name(),
                "emp_ln": fake.last_name(),
                "emp_dob": fake.date_of_birth(minimum_age=18, maximum_age=45).isoformat(),
                "emp_start_date": rand_date(2020, 2025).isoformat(),
                "emp_salary": random.randint(28000, 42000),
                "role": random.choice(["Cook", "Cashier", "Prep Cook", "Server"]),
                "truck_id": truck_id,
                "boss_id": random.choice(manager_ids),
            })
            emp_id += 1

    # Fill any remainder (rounding) onto random trucks as staff
    while emp_id <= n:
        truck = random.choice(TRUCKS)
        employees.append({
            "employee_id": emp_id,
            "emp_fn": fake.first_name(),
            "emp_ln": fake.last_name(),
            "emp_dob": fake.date_of_birth(minimum_age=18, maximum_age=45).isoformat(),
            "emp_start_date": rand_date(2020, 2025).isoformat(),
            "emp_salary": random.randint(28000, 42000),
            "role": random.choice(["Cook", "Cashier", "Prep Cook", "Server"]),
            "truck_id": truck["truck_id"],
            "boss_id": "",
        })
        emp_id += 1

    return employees


def assign_owners(employees):
    """Set truck.owner_id = the head boss (bossID IS NULL) for each truck."""
    owners = {}
    for e in employees:
        if e["boss_id"] == "" and e["role"] == "Owner":
            owners[e["truck_id"]] = e["employee_id"]
    for truck in TRUCKS:
        truck["owner_id"] = owners.get(truck["truck_id"], "")
    return TRUCKS


# ---------------------------------------------------------------------------
# Customers (60)
# ---------------------------------------------------------------------------
def generate_customers(n=60):
    customers = []
    for cid in range(1, n + 1):
        has_loyalty = random.random() < 0.75  # ~25% not enrolled, useful for query 2
        customers.append({
            "customer_id": cid,
            "customer_fn": fake.first_name(),
            "customer_ln": fake.last_name(),
            "loyalty_number": f"LP{cid:05d}" if has_loyalty else "",
            "truck_id": random.choice(TRUCKS)["truck_id"],
        })
    return customers


# ---------------------------------------------------------------------------
# Menu items
# ---------------------------------------------------------------------------
def generate_menu_items():
    menu_items = []
    mid = 1
    for truck_id, items in MENU_BY_TRUCK.items():
        for name, price, calories in items:
            menu_items.append({
                "menu_item_id": mid,
                "menu_item_name": name,
                "price": price,
                "calories": calories,
                "truck_id": truck_id,
            })
            mid += 1
    return menu_items


# ---------------------------------------------------------------------------
# Orders (100) + order_has_menu_item
# ---------------------------------------------------------------------------
def generate_orders_and_lines(customers, menu_items, n_orders=100):
    menu_by_truck = {}
    for mi in menu_items:
        menu_by_truck.setdefault(mi["truck_id"], []).append(mi)

    orders = []
    lines = []
    for oid in range(1, n_orders + 1):
        customer = random.choice(customers)
        truck_id = customer["truck_id"]
        candidates = menu_by_truck[truck_id]
        n_items = random.randint(1, 4)
        chosen = random.sample(candidates, k=min(n_items, len(candidates)))

        order_total = 0.0
        for mi in chosen:
            qty = random.randint(1, 3)
            order_total += mi["price"] * qty
            lines.append({
                "order_id": oid,
                "menu_item_id": mi["menu_item_id"],
                "quantity": qty,
            })

        points = int(order_total * 10)  # simple loyalty-points rule
        orders.append({
            "order_id": oid,
            "order_date": rand_date(2023, 2025).isoformat(),
            "order_time": fake.time(),
            "order_type": random.choice(ORDER_TYPES),
            "points": points,
            "customer_id": customer["customer_id"],
        })
    return orders, lines


# ---------------------------------------------------------------------------
# Inventory (95)
# ---------------------------------------------------------------------------
INGREDIENTS = [
    "Cheddar Cheese Block", "Ground Beef", "Flour Tortillas", "Corn Tortillas", "Pork Shoulder",
    "Beef Brisket", "BBQ Sauce", "Elbow Macaroni", "Heavy Cream", "Chicken Breast", "Donut Mix",
    "Powdered Sugar", "Cinnamon", "Maple Syrup", "Bacon", "Sweet Potatoes", "Cornmeal",
    "Lettuce", "Tomatoes", "Onions", "Cilantro", "Limes", "Jalapenos", "Vegetable Oil",
    "Butter", "Eggs", "Milk", "Yeast", "Chocolate Chips", "Lemon Zest",
]


def generate_inventory(menu_items, n=95):
    inventory = []
    for iid in range(1, n + 1):
        mi = random.choice(menu_items)
        purchased = rand_date(2025, 2026)
        expires = purchased + timedelta(days=random.randint(3, 60))
        inventory.append({
            "item_id": iid,
            "item_name": random.choice(INGREDIENTS),
            "date_purchased": purchased.isoformat(),
            "expiration_date": expires.isoformat(),
            "truck_id": mi["truck_id"],
            "menu_item_id": mi["menu_item_id"],
        })
    return inventory


def write_csv(rows, filename, fieldnames):
    path = DATA_DIR / filename
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows):>4} rows -> {path.relative_to(DATA_DIR.parent)}")


def main():
    print("Generating synthetic Food Truck dataset...")

    employees = generate_employees(100)
    trucks = assign_owners(employees)
    customers = generate_customers(60)
    menu_items = generate_menu_items()
    orders, lines = generate_orders_and_lines(customers, menu_items, 100)
    inventory = generate_inventory(menu_items, 95)

    write_csv(trucks, "truck.csv", ["truck_id", "restaurant_name", "food_type", "owner_id"])
    write_csv(employees, "employee.csv",
              ["employee_id", "emp_fn", "emp_ln", "emp_dob", "emp_start_date",
               "emp_salary", "role", "truck_id", "boss_id"])
    write_csv(customers, "customer.csv",
              ["customer_id", "customer_fn", "customer_ln", "loyalty_number", "truck_id"])
    write_csv(menu_items, "menu_item.csv",
              ["menu_item_id", "menu_item_name", "price", "calories", "truck_id"])
    write_csv(orders, "order.csv",
              ["order_id", "order_date", "order_time", "order_type", "points", "customer_id"])
    write_csv(lines, "order_has_menu_item.csv", ["order_id", "menu_item_id", "quantity"])
    write_csv(inventory, "inventory.csv",
              ["item_id", "item_name", "date_purchased", "expiration_date", "truck_id", "menu_item_id"])

    print("Done.")


if __name__ == "__main__":
    main()
