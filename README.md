# Food Truck Data Pipeline

A small data pipeline for a fictional multi-location food truck business:
generate synthetic data → load it into a database → validate it → analyze it.

Originally a database design project for a business analytics class (ER model
+ hand-written SQL queries). Rebuilt as a scripted, reproducible pipeline.

**→ [See the analysis notebook](notebook/analysis.ipynb)** for a full walkthrough
with charts and results — start there.

## Quick start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python3 scripts/run_pipeline.py
```

That command generates the data, loads it into `foodtruck.db`, builds the
analytics views, and validates the result.

## Repo structure

```
├── notebook/analysis.ipynb     the write-up — start here
├── scripts/
│   ├── generate_data.py        builds synthetic source data
│   ├── load_and_transform.py   loads data + builds analytics views
│   ├── data_quality_checks.py  validates row counts, nulls, foreign keys, PKs
│   └── run_pipeline.py         runs everything above, in order
├── sql/schema.sql              table definitions, keys, relationships
├── docs/
│   ├── PROJECT_WALKTHROUGH.md  plain-English file-by-file guide
│   └── original_queries.sql    the 10 original business-question queries
└── docker-compose.yml          optional: run the schema against real Postgres
```

## Optional: run against Postgres instead of SQLite

```bash
docker compose up -d
psql postgresql://foodtruck:foodtruck@localhost:5432/foodtruck -f sql/schema.sql
```
