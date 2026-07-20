"""Build mart_conditions_hourly from fact_hourly via a DuckDB SQL transform.

The SQL lives in ``sql/mart_conditions_hourly.sql`` (CTEs + NTILE window
functions). This module just loads and runs it, and can export the result to
Parquet.
"""

from __future__ import annotations

from pathlib import Path

SQL_PATH = (
    Path(__file__).resolve().parents[1] / "sql" / "mart_conditions_hourly.sql"
)


def mart_sql() -> str:
    return SQL_PATH.read_text()


def build_mart(con) -> None:
    """Create/replace mart_conditions_hourly in an open DuckDB connection.

    Requires a ``fact_hourly`` table/view to already exist in ``con``.
    """
    con.execute(
        "CREATE OR REPLACE TABLE mart_conditions_hourly AS " + mart_sql()
    )


def build_from_duckdb(
    duckdb_path: Path, processed_dir: Path | None = None
) -> int:
    """Build the mart in an existing gep.duckdb; optionally export Parquet.

    Returns the mart row count.
    """
    import duckdb

    con = duckdb.connect(str(duckdb_path))
    try:
        build_mart(con)
        n = con.execute(
            "SELECT count(*) FROM mart_conditions_hourly"
        ).fetchone()[0]
        if processed_dir is not None:
            processed_dir.mkdir(parents=True, exist_ok=True)
            out = processed_dir / "mart_conditions_hourly.parquet"
            con.execute(
                "COPY mart_conditions_hourly TO ? (FORMAT PARQUET)", [str(out)]
            )
    finally:
        con.close()
    return n
