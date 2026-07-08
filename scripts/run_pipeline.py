"""
run_pipeline.py
----------------
Single entry point that runs the full pipeline: generate -> load -> transform.
This is the kind of thing a scheduler (cron, Airflow, Prefect) would call.

Run:
    python3 scripts/run_pipeline.py
"""

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def run_step(name, script):
    print(f"\n{'=' * 60}\nSTEP: {name}\n{'=' * 60}")
    start = time.time()
    result = subprocess.run([sys.executable, str(SCRIPTS_DIR / script)])
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"FAILED: {name} (exit code {result.returncode})")
        sys.exit(result.returncode)
    print(f"OK: {name} completed in {elapsed:.2f}s")


def main():
    run_step("Generate synthetic source data", "generate_data.py")
    run_step("Load + transform into warehouse (SQLite)", "load_and_transform.py")
    run_step("Data quality checks", "data_quality_checks.py")
    print("\nPipeline run complete.")


if __name__ == "__main__":
    main()
