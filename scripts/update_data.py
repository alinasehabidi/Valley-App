"""Merge all current cluster source files into the persistent processed CSVs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_pipeline import write_processed  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incoming", type=Path, default=ROOT / "data" / "incoming")
    parser.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    args = parser.parse_args()

    sales, rentals, warnings = write_processed(args.incoming, args.processed)
    print(f"Saved {len(sales):,} sales and {len(rentals):,} rental records.")
    for warning in warnings:
        print(f"WARNING: {warning}")
    if sales.empty and rentals.empty:
        print("ERROR: no recognised source data was found.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
