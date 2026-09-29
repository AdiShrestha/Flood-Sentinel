"""CLI entry point for running Reality Gate across all acquisition manifests (C01-11 / C02-13).

Evaluates all dataset manifests against the Reality Gate checks (Checks 1-5 and Check 6
data-level consistency cross-check per TD-002) and formats the structured Reality Gate Report.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.gate.reality_gate import evaluate_source_manifest
from source.utils.config import CHUNK01_DIR, CHUNK01_MANIFESTS_DIR, CHUNK02_DATA_DIR, CHUNK02_DIR, CHUNK02_MANIFESTS_DIR
from source.utils.logging_config import get_logger

logger = get_logger("run_reality_gate")

MANIFEST_SOURCE_MAP = {
    "usgs_data_manifest.json": "usgs",
    "gridmet_data_manifest.json": "gridmet",
    "snodas_data_manifest.json": "snodas",
    "attributes_data_manifest.json": "attributes",
    "thresholds_data_manifest.json": "thresholds",
    "events_data_manifest.json": "events",
    "nwm_retro_data_manifest.json": "nwm_retro",
    "response_time_data_manifest.json": "response_time",
    "feature_matrix_data_manifest.json": "feature_matrix",
    "causal_ledger_data_manifest.json": "causal_ledger",
    "vintage_ledger_data_manifest.json": "vintage_ledger",
    "normalization_data_manifest.json": "normalization",
}


def find_source_data_paths(manifest_dir: Path, source_key: str) -> Optional[List[Path]]:
    """Locate underlying Parquet or JSON data files for a source to enable Check 6 data cross-check."""
    chunk_dir = manifest_dir.parent
    data_dir = chunk_dir / "data" / source_key

    if not data_dir.exists():
        return None

    # Find parquet files
    parquet_files = sorted(list(data_dir.glob("**/*.parquet")))
    if parquet_files:
        return parquet_files

    # Find json files if no parquet
    json_files = sorted(list(data_dir.glob("*.json")))
    if json_files:
        return json_files

    return None


def build_reality_gate_markdown_report(results: List[Dict[str, Any]], output_path: Path) -> Path:
    """Format and write the structured Reality Gate markdown report."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    is_chunk03 = "chunk03" in str(output_path)
    is_chunk02 = "chunk02" in str(output_path)
    if is_chunk03:
        title = "# Reality Gate Report — Chunk 03 Feature Matrix"
    elif is_chunk02:
        title = "# Reality Gate Report — Chunk 02 Full Panel"
    else:
        title = "# Reality Gate Report — Chunk 01 Pilot Panel"

    lines = [
        title,
        "",
        f"**Timestamp:** {now_utc}  ",
        "**Gate Version:** v1.4.2 (factory_spec.md § Reality Gate Specification & TD-001/TD-002)  ",
        "**Verification Engine:** `source/gate/reality_gate.py`  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Source | Check 1 (Gaps) | Check 2 (Dist) | Check 3 (Coverage) | Check 4 (Sensors) | Check 5 (Provenance) | Check 6 (Data Cross-Check) | Overall |",
        "|---|---|---|---|---|---|---|---|"
    ]

    all_passed = True

    for r in results:
        src = r["source_key"].upper()
        ch = r["checks"]
        c1 = ch.get("check1_gap_statistics", {}).get("verdict", "N/A")
        c2 = ch.get("check2_distribution", {}).get("verdict", "N/A")
        c3 = ch.get("check3_temporal_coverage", {}).get("verdict", "N/A")
        c4 = ch.get("check4_sensor_coverage", {}).get("verdict", "N/A")
        c5 = ch.get("check5_provenance_chain", {}).get("verdict", "N/A")
        c6 = ch.get("check6_data_consistency", {}).get("verdict", "N/A")
        overall = r["overall_verdict"]

        if overall == "FAIL":
            all_passed = False

        lines.append(f"| {src} | {c1} | {c2} | {c3} | {c4} | {c5} | {c6} | **{overall}** |")

    lines.extend([
        "",
        "---",
        "",
        "## Per-Source Detail",
        ""
    ])

    for r in results:
        src = r["source_key"]
        lines.append(f"### Source: {src.upper()}")
        lines.append(f"**Manifest:** `{r['manifest_path']}`  ")
        lines.append(f"**Overall Status:** {r['overall_verdict']}")
        lines.append("")

        for ch_key, ch_data in r["checks"].items():
            verdict = ch_data.get("verdict", "N/A")
            reason = ch_data.get("reason", "")
            lines.append(f"#### {ch_key.replace('_', ' ').title()} — [{verdict}]")
            lines.append(f"- {reason}")
            lines.append("")

    content = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Reality Gate Report written to {output_path}")
    return output_path


def run_gate(manifest_dir: Path, output_file: Path) -> int:
    """Run all checks on manifests in directory and output report."""
    logger.info(f"Scanning manifest directory: {manifest_dir}...")

    manifest_files = sorted(list(manifest_dir.glob("*_data_manifest.json")))
    if not manifest_files:
        logger.error(f"No *_data_manifest.json files found in {manifest_dir}")
        return 1

    results = []
    has_hard_fail = False

    for m_path in manifest_files:
        source_key = MANIFEST_SOURCE_MAP.get(m_path.name, m_path.name.replace("_data_manifest.json", ""))
        logger.info(f"Evaluating {m_path.name} (Source: {source_key})...")

        data_paths = find_source_data_paths(manifest_dir, source_key)
        res = evaluate_source_manifest(m_path, source_key, data_paths=data_paths)
        results.append(res)
        if res["overall_verdict"] == "FAIL":
            has_hard_fail = True

    build_reality_gate_markdown_report(results, output_file)

    if has_hard_fail:
        logger.error("Reality Gate execution completed with FAILURES.")
        return 1
    else:
        logger.info("Reality Gate execution completed: ALL MANIFESTS PASSED.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Reality Gate checks on data manifests.")
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=CHUNK02_MANIFESTS_DIR,
        help="Directory containing *_data_manifest.json files"
    )
    parser.add_argument(
        "--expected-properties",
        type=Path,
        default=None,
        help="Path to venue_requirements.md or properties file"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to output markdown report"
    )
    args = parser.parse_args()

    out_file = args.output or (args.manifest_dir.parent / "reality_gate_report.md")
    code = run_gate(args.manifest_dir, out_file)
    sys.exit(code)


if __name__ == "__main__":
    main()
