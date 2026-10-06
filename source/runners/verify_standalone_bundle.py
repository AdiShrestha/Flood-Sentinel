#!/usr/bin/env python3
"""Standalone bundle and release verification runner.

Independently extracts and verifies cryptographic digests across all published
source code, dataset artifacts, research cards, and handoff archives. Tests
another-session offline reproduction instructions without external dependencies.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ensure source is on sys.path
SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from flood_sentinel.release import (
    create_handoff_archive,
    generate_release_manifest,
    verify_handoff_archive,
    verify_release_manifest,
    verify_standalone_reproduction,
)


def run_standalone_bundle_verification(
    root: Path,
    manifest_path: Path | None = None,
    handoff_path: Path | None = None,
    generate_if_missing: bool = True,
) -> dict[str, Any]:
    """Execute complete standalone verification across manifest, handoff, and reproduction."""
    root = Path(root).resolve()
    manifest_file = manifest_path or (root / "project/release_manifest.json")
    handoff_file = handoff_path or (root / "handoff_epoch0007_verified.zip")

    # Generate if missing or requested
    if generate_if_missing:
        if not manifest_file.is_file():
            print(f"Generating release manifest at {manifest_file}...")
            manifest_payload = generate_release_manifest(root)
            manifest_file.parent.mkdir(parents=True, exist_ok=True)
            manifest_file.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

        if not handoff_file.is_file():
            print(f"Creating verified handoff archive at {handoff_file}...")
            create_handoff_archive(root, handoff_file)

    # 1. Verify Release Manifest
    print(f"[1/3] Verifying release manifest integrity ({manifest_file.name})...")
    manifest_res = verify_release_manifest(root, manifest_file)

    # 2. Verify Handoff Archive
    print(f"[2/3] Verifying handoff archive integrity ({handoff_file.name})...")
    handoff_res = verify_handoff_archive(handoff_file) if handoff_file.is_file() else {
        "status": "SKIPPED",
        "detail": "Archive not present",
    }

    # 3. Verify Offline Reproduction
    print("[3/3] Verifying offline standalone reproduction...")
    repro_res = verify_standalone_reproduction(root)

    overall_pass = (
        manifest_res["status"] == "PASS"
        and handoff_res.get("status") in {"PASS", "SKIPPED"}
        and repro_res["status"] == "PASS"
    )

    summary = {
        "status": "PASS" if overall_pass else "FAIL",
        "root_directory": str(root),
        "manifest_verification": manifest_res,
        "handoff_verification": handoff_res,
        "standalone_reproduction": repro_res,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone bundle and release verification")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--manifest", default=None, help="Path to release manifest")
    parser.add_argument("--handoff", default=None, help="Path to handoff archive")
    parser.add_argument("--generate", action="store_true", help="Force generation of manifest and archive")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest_p = Path(args.manifest).resolve() if args.manifest else root / "project/release_manifest.json"
    handoff_p = Path(args.handoff).resolve() if args.handoff else root / "handoff_epoch0007_verified.zip"

    if args.generate:
        print("Regenerating release manifest and handoff archive...")
        man_payload = generate_release_manifest(root)
        manifest_p.parent.mkdir(parents=True, exist_ok=True)
        manifest_p.write_text(json.dumps(man_payload, indent=2), encoding="utf-8")
        create_handoff_archive(root, handoff_p)

    report = run_standalone_bundle_verification(
        root,
        manifest_path=manifest_p,
        handoff_path=handoff_p,
        generate_if_missing=True,
    )

    print("\nStandalone Verification Report:")
    print(f"Overall Status: {report['status']}")
    print(f"Manifest Verified: {report['manifest_verification']['status']} ({report['manifest_verification']['verified_files']}/{report['manifest_verification']['total_declared_files']} files)")
    print(f"Handoff Archive: {report['handoff_verification']['status']} (Receipts: {report['handoff_verification'].get('execution_receipts_found', 0)})")
    print(f"Offline Reproduction: {report['standalone_reproduction']['status']}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
