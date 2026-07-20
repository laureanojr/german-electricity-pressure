"""CLI: download raw SMARD weekly JSON into data/raw and write a manifest.

Live network run — intended to run on your machine, not in CI.

    python scripts/download_smard.py                 # full 2019-2025 window
    python scripts/download_smard.py --start 2024-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smardpipe import download  # noqa: E402
from smardpipe import series as S  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Download raw SMARD series.")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--start", default=S.WINDOW_START)
    ap.add_argument("--end", default=S.WINDOW_END)
    ap.add_argument("--overwrite", action="store_true",
                    help="re-fetch files even if already cached")
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    rows = download.download_all(
        raw_dir, start=args.start, end=args.end, overwrite=args.overwrite
    )
    download.write_manifest(rows, raw_dir / "manifest.csv")
    print(f"Downloaded/verified {len(rows)} weekly files -> {raw_dir}")
    print(f"Manifest: {raw_dir / 'manifest.csv'}")


if __name__ == "__main__":
    main()
