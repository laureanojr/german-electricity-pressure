"""Run the findings SQL and print every number behind findings.md.

Nothing in findings.md is hand-typed: each query in sql/findings/*.sql carries a
`-- name: <label>` marker, and this runner executes them read-only against
gep.duckdb and prints the labelled result. Run it to reproduce or re-verify the
report after a data rebuild:

    python scripts/run_findings.py                 # all files, all queries
    python scripts/run_findings.py residual_load   # one file by stem
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "gep.duckdb"
SQL_DIR = ROOT / "sql" / "findings"


def parse_blocks(text: str) -> list[tuple[str, str]]:
    """Split a .sql file into (name, sql) pairs on `-- name:` markers."""
    blocks: list[tuple[str, str]] = []
    name: str | None = None
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-- name:"):
            if name is not None:
                blocks.append((name, "\n".join(lines)))
            name = stripped.removeprefix("-- name:").strip()
            lines = []
        elif name is not None:
            lines.append(line)
    if name is not None:
        blocks.append((name, "\n".join(lines)))
    return blocks


def main() -> None:
    if not DB.exists():
        sys.exit(f"missing {DB} — build the data layer first (see README).")

    wanted = set(sys.argv[1:])
    files = sorted(SQL_DIR.glob("*.sql"))
    if wanted:
        files = [f for f in files if f.stem in wanted]

    con = duckdb.connect(str(DB), read_only=True)
    for path in files:
        print(f"\n{'#' * 70}\n# {path.name}\n{'#' * 70}")
        for name, sql in parse_blocks(path.read_text()):
            # only run blocks that actually contain a statement
            if not sql.strip().rstrip(";"):
                continue
            print(f"\n-- {name}")
            print(con.execute(sql).df().to_string(index=False))


if __name__ == "__main__":
    main()
