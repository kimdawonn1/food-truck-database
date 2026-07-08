-- =========================================================
-- Food Truck Data Platform — Schema DDL
-- Target: PostgreSQL 14+ (also runs on SQLite via scripts/load_and_transform.py
-- with minor type coercion handled in code for local/demo use)
-- =========================================================

DROP TABLE IF EXISTS order_has_menu_item CASCADE;
DROP TABLE IF EXISTS inventory CASCADE;
DROP TABLE IF EXISTS "order" CASCADE;
DROP TABLE IF EXISTS menu_item CASCADE;
DROP TABLE IF EXISTS customer CASCADE;
DROP TABLE IF EXISTS employee CASCADE;
DROP TABLE IF EXISTS truck CASCADE;

CREATE TABLE truck (
    truck_id        INTEGER PRIMARY KEY,
    restaurant_name VARCHAR(40) NOT NULL,
    food_type       VARCHAR(40) NOT NULL,
    owner_id        INTEGER  -- FK to employee.employee_id, added after employee table is populated
);

CREATE TABLE employee (
    employee_id     INTEGER PRIMARY KEY,
    emp_fn          VARCHAR(40) NOT NULL,
    emp_ln          VARCHAR(40) NOT NULL,
    emp_dob         DATE,
    emp_start_date  DATE,
    emp_salary      INTEGER,
    role            VARCHAR(40),
    truck_id        INTEGER REFERENCES truck(truck_id),
    boss_id         INTEGER REFERENCES employee(employee_id)  -- recursive self-reference
);

ALTER TABLE truck
    ADD CONSTRAINT fk_truck_owner FOREIGN KEY (owner_id) REFERENCES employee(employee_id);

CREATE TABLE customer (
    customer_id     INTEGER PRIMARY KEY,
    customer_fn     VARCHAR(40) NOT NULL,
    customer_ln     VARCHAR(40) NOT NULL,
    loyalty_number  VARCHAR(20),
    truck_id        INTEGER REFERENCES truck(truck_id)
);

CREATE TABLE menu_item (
    menu_item_id    INTEGER PRIMARY KEY,
    menu_item_name  VARCHAR(60) NOT NULL,
    price           NUMERIC(6,2) NOT NULL,
    calories        INTEGER,
    truck_id        INTEGER REFERENCES truck(truck_id)
);

CREATE TABLE "order" (
    order_id        INTEGER PRIMARY KEY,
    order_date      DATE NOT NULL,
    order_time      TIME NOT NULL,
    order_type      VARCHAR(40),
    points          INTEGER,
    customer_id     INTEGER REFERENCES customer(customer_id)
);

CREATE TABLE order_has_menu_item (
    order_id        INTEGER REFERENCES "order"(order_id),
    menu_item_id    INTEGER REFERENCES menu_item(menu_item_id),
    quantity        INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (order_id, menu_item_id)
);

CREATE TABLE inventory (
    item_id         INTEGER PRIMARY KEY,
    item_name       VARCHAR(60) NOT NULL,
    date_purchased  DATE,
    expiration_date DATE,
    truck_id        INTEGER REFERENCES truck(truck_id),
    menu_item_id    INTEGER REFERENCES menu_item(menu_item_id)
);

-- Helpful indexes for common analytical access patterns
CREATE INDEX idx_employee_boss ON employee(boss_id);
CREATE INDEX idx_employee_truck ON employee(truck_id);
CREATE INDEX idx_order_customer ON "order"(customer_id);
CREATE INDEX idx_order_date ON "order"(order_date);
CREATE INDEX idx_ohmi_order ON order_has_menu_item(order_id);
CREATE INDEX idx_ohmi_menuitem ON order_has_menu_item(menu_item_id);
CREATE INDEX idx_inventory_truck ON inventory(truck_id);
CREATE INDEX idx_inventory_expiration ON inventory(expiration_date);
