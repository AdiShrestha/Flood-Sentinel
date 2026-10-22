#!/usr/bin/env python3
"""Replay the declared daily-quality matrix from caller-supplied raw pages."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from flood_sentinel.daily_quality_replay import replay


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Recompute a daily aggregate quality-support matrix from exact, "
                     "caller-provided raw response pages. No network access is performed.")
    )
    parser.add_argument("--manifest", required=True, type=Path,
                        help="project-facing source manifest JSON")
    parser.add_argument("--raw-dir", required=True, type=Path,
                        help="directory containing the manifest's hash-named raw page files")
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="new destination; existing directories are never overwritten")
    args = parser.parse_args(argv)
    result = replay(args.manifest, args.raw_dir, args.output_dir)
    print(json.dumps({
        "status": "replayed",
        "output_directory": str(args.output_dir),
        "counts_derived_from_consumed_pages": result["counts_derived_from_consumed_pages"],
        "quality_thresholds_exact": result["quality_thresholds_exact"],
        "outputs": result["outputs"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
