#!/usr/bin/env python3
"""Run saved Flood Sentinel models from a user-supplied local manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "source"))

from flood_sentinel.replay import run_replay  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to a local replay manifest JSON file")
    args = parser.parse_args()
    report = run_replay(args.manifest)
    print(json.dumps({
        "status": "REPLAY_VERIFIED" if report["all_prediction_and_metric_checks_pass"] else "REPLAY_MISMATCH",
        "runs": len(report["runs"]),
        "all_prediction_and_metric_checks_pass": report["all_prediction_and_metric_checks_pass"],
        "report": "replay_report.json",
    }, sort_keys=True))
    return 0 if report["all_prediction_and_metric_checks_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
