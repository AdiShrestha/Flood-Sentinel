"""rehash_dataport_manifest.py -- Re-hash and verify SHA-256 checksums in dataport_manifest.json.

Usage:
    python3 source/release/rehash_dataport_manifest.py --verify
    python3 source/release/rehash_dataport_manifest.py --update
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("rehash_dataport_manifest")

MANIFEST_PATH = _PROJECT_ROOT / "project" / "chunks" / "chunk09" / "dataport_manifest.json"


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def process_manifest(verify_only: bool = True) -> bool:
    """Check or update checksums in dataport_manifest.json."""
    if not MANIFEST_PATH.exists():
        logger.error(f"Manifest not found: {MANIFEST_PATH}")
        return False

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    files_list = manifest_data.get("files", [])
    stale_count = 0
    missing_count = 0
    total_size = 0

    logger.info(f"Auditing {len(files_list)} cataloged artifacts in {MANIFEST_PATH.name}...")

    for item in files_list:
        rel_path = item["relative_path"]
        target_path = _PROJECT_ROOT / rel_path

        if not target_path.exists():
            logger.error(f"  [MISSING] File not found: {rel_path}")
            missing_count += 1
            continue

        actual_size = target_path.stat().st_size
        actual_hash = compute_sha256(target_path)
        recorded_hash = item.get("sha256_checksum", "")
        recorded_size = item.get("size_bytes", 0)

        total_size += actual_size

        if actual_hash != recorded_hash or actual_size != recorded_size:
            stale_count += 1
            if verify_only:
                logger.error(
                    f"  [STALE] {item['filename']} ({rel_path})\n"
                    f"          Recorded: size={recorded_size}, sha256={recorded_hash[:16]}...\n"
                    f"          Actual:   size={actual_size}, sha256={actual_hash[:16]}..."
                )
            else:
                logger.info(f"  [UPDATING] {item['filename']} -> hash={actual_hash[:16]}..., size={actual_size}")
                item["size_bytes"] = actual_size
                item["sha256_checksum"] = actual_hash
        else:
            logger.info(f"  [VALID] {item['filename']} (SHA-256 match)")

    if not verify_only:
        manifest_data["total_size_bytes"] = total_size
        manifest_data["total_cataloged_files"] = len(files_list)
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        logger.info(f"\nSuccessfully re-hashed and updated {MANIFEST_PATH.name} (Total size: {total_size:,} bytes).")
        return missing_count == 0

    if stale_count == 0 and missing_count == 0:
        logger.info(f"\nVerification SUCCESS: 0 stale hashes, 0 missing files across {len(files_list)} artifacts.")
        return True
    else:
        logger.error(f"\nVerification FAILED: {stale_count} stale hashes, {missing_count} missing files.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Re-hash and verify dataport_manifest.json")
    parser.add_argument("--verify", action="store_true", help="Verify hashes without modifying")
    parser.add_argument("--update", action="store_true", help="Update hashes and sizes in place")
    args = parser.parse_args()

    if args.update:
        ok = process_manifest(verify_only=False)
        sys.exit(0 if ok else 1)
    elif args.verify:
        ok = process_manifest(verify_only=True)
        sys.exit(0 if ok else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
