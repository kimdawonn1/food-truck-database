# Food Truck Data Pipeline

A small end-to-end data pipeline for a fictional multi-location food truck business.

This started as a database design project for a business analytics class. I built the ER model and wrote the SQL queries by hand. I rebuilt it here with a proper schema, seed scripts, and Docker setup so it's actually runnable instead of just screenshots in a report.


## Repo Structure
```
├── data/
│   ├── customer.csv           Customer records
│   ├── employee.csv           Employee records
│   ├── inventory.csv          Inventory records
│   ├── menu_item.csv          Menu item records
│   ├── order.csv              Order records
│   ├── order_has_menu_item.csv  Order line items (associative table)
│   └── truck.csv              Truck records
├── sql/
│   └── schema.sql             Table definitions, keys, relationships
├── scripts/
│   ├── generate_data.py       Builds seed data
│   ├── load_and_transform.py  Loads CSVs into the database
│   ├── data_quality_checks.py Validates row counts, foreign keys, nulls
│   └── run_pipeline.py        Runs the full pipeline end to end
├── docs/
│   └── original_queries.sql   The 10 business-question queries
├── docker-compose.yml         Spins up the database for local development
├── requirements.txt           Python dependencies
└── README.md
```

## Architecture

```
Faker (synthetic source data)
        │
        ▼
generate_data.py  ──►  data/*.csv        (Extract / synthetic source layer)
        │
        ▼
load_and_transform.py  ──►  foodtruck.db  (Load: raw tables, SQLite)
        │
        ▼
        views (vw_*)                     (Transform: analytics-ready marts)
```

Run everything with one command via `scripts/run_pipeline.py`, or run each stage
independently for development/debugging.

## Data model

7 tables, matching `sql/schema.sql`:

- **truck** — 4 locations (Lex Mex, Mac Mart, Oink-Moo BBQ, Mr. H's Donuts)
- **employee** — includes a recursive `boss_id` self-reference (org hierarchy) and a
  1:1 relationship to `truck` via `owner_id`
- **customer** — 1:many with `truck` (loyalty program is non-transferable per truck)
- **menu_item** — 1:many with `truck`
- **order** / **order_has_menu_item** — many:many associative table between orders and
  menu items, with `quantity`
- **inventory** — tracks individual stocked items with purchase/expiration dates,
  linked to both `truck` and `menu_item`

## Tech stack

- **Python 3 + Faker** — deterministic, seeded synthetic data generation (no more
  manually counting rows out of a chatbot)
- **SQLite** — local warehouse for the runnable demo (zero external dependencies)
- **PostgreSQL (via Docker Compose)** — production-flavored DDL in `sql/schema.sql`;
  optional `docker-compose.yml` included to run the same schema against real Postgres
- **SQL views** — a lightweight transform/marts layer answering business questions
  directly in the warehouse instead of ad hoc one-off queries

## Getting started

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run the full pipeline
python3 scripts/run_pipeline.py

# Or run stages individually
python3 scripts/generate_data.py
python3 scripts/load_and_transform.py
```

This produces `foodtruck.db`, a queryable SQLite database:

```bash
sqlite3 foodtruck.db "SELECT * FROM vw_revenue_by_truck ORDER BY total_revenue DESC;"
```

### Optional: run against Postgres instead of SQLite

```bash
docker compose up -d
psql postgresql://foodtruck:foodtruck@localhost:5432/foodtruck -f sql/schema.sql
```

## Analytics layer (views)

| View | Business question answered |
|---|---|
| `vw_top_menu_items_by_truck` | What are the most popular menu items at each truck? |
| `vw_inventory_expiring_30d` | Which trucks have inventory expiring in the next 30 days? |
| `vw_revenue_by_truck` | What's total revenue and order volume per truck? |
| `vw_employees_paid_more_than_boss` | Are there pay-structure anomalies by truck? |

`docs/original_queries.sql` preserves the original 10 ad hoc SQL queries from the
class project (subqueries, self-joins, `REGEXP`, correlated subqueries, etc.) for
reference — the views above are the automated, reusable version of that same analysis.

## Possible next steps

- Orchestrate with Airflow or Prefect instead of a single script
- Replace CSV intermediate files with a proper staging schema + `dbt` models
  (staging → intermediate → marts)
- Swap SQLite for the included Postgres service permanently
- Add data quality checks (e.g. Great Expectations) on the load step
- Containerize the whole pipeline

## Background

Originally an ER-modeling and SQL exercise for a database management course
(schema + 10 business-question queries, documented in `docs/original_queries.sql`).
Rebuilt as a scripted pipeline to move from "manually generated fake data pasted into
MySQL Workbench" to a reproducible, seeded, version-controlled data pipeline.
