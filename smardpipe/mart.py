"""Build mart_conditions_hourly from fact_hourly via a DuckDB SQL transform.

The SQL lives in ``sql/mart_conditions_hourly.sql`` (CTEs + NTILE window
functions). This module just loads and runs it, and can export the result to
Parquet.
"""

from __future__ import annotations

from pathlib import Path

_SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
CONDITIONS_SQL_PATH = _SQL_DIR / "mart_conditions_hourly.sql"
DAILY_SQL_PATH = _SQL_DIR / "mart_daily_summary.sql"


def mart_sql() -> str:
    return CONDITIONS_SQL_PATH.read_text()


def daily_sql() -> str:
    return DAILY_SQL_PATH.read_text()


def build_mart(con) -> None:
    """Create/replace mart_conditions_hourly. Requires ``fact_hourly`` in con."""
    con.execute(
        "CREATE OR REPLACE TABLE mart_conditions_hourly AS " + mart_sql()
    )


def build_daily(con) -> None:
    """Create/replace mart_daily_summary. Requires mart_conditions_hourly."""
    con.execute(
        "CREATE OR REPLACE TABLE mart_daily_summary AS " + daily_sql()
    )


def build_from_duckdb(
    duckdb_path: Path, processed_dir: Path | None = None
) -> dict[str, int]:
    """Build both marts in an existing gep.duckdb; optionally export Parquet.

    Returns row counts keyed by table name.
    """
    import duckdb

    con = duckdb.connect(str(duckdb_path))
    counts: dict[str, int] = {}
    try:
        build_mart(con)
        build_daily(con)
        for table in ("mart_conditions_hourly", "mart_daily_summary"):
            counts[table] = con.execute(
                f"SELECT count(*) FROM {table}"
            ).fetchone()[0]
            if processed_dir is not None:
                processed_dir.mkdir(parents=True, exist_ok=True)
                out = processed_dir / f"{table}.parquet"
                con.execute(
                    f"COPY {table} TO ? (FORMAT PARQUET)", [str(out)]
                )
    finally:
        con.close()
    return counts
