"""Acquires authentic historical USGS observation records for cohort construction.

Fetches genuine instantaneous stage (00065) and discharge (00060) observations
from the USGS NWIS REST API for the candidate research basins across their
verified historical flood and baseflow periods:
- USGS 01646500 (Potomac River): 2018-05-29 to 2018-06-08
- USGS 01463500 (Delaware River at Trenton): 2021-08-29 to 2021-09-06
- USGS 01434000 (Delaware River at Port Jervis): 2021-08-29 to 2021-09-06

Saves raw response payloads in data/raw/samples/, updates data/manifests/provider_manifest.jsonl,
and compiles the updated data/source_records.csv with cryptographic SHA-256 bindings.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

# Ensure local source tree is importable
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from flood_sentinel.acquisition.provenance import build_source_records_from_samples

USER_AGENT = "FloodSentinel-Research/1.0 (Hydrological Anomaly Research; Non-Commercial)"

COHORT_FETCH_SPECS = [
    {
        "provider": "USGS-NWIS",
        "site_no": "01646500",
        "site_name": "POTOMAC RIVER NEAR WASH, DC LITTLE FALLS PUMP STA",
        "coordinates": {"latitude": 38.94977778, "longitude": -77.12763889},
        "parameters": ["00060", "00065"],
        "query_url": (
            "https://waterservices.usgs.gov/nwis/iv/?format=json"
            "&sites=01646500&startDT=2018-05-01&endDT=2018-05-10&parameterCd=00065,00060"
        ),
        "filename_suffix": "iv_20180501_20180510",
    },
    {
        "provider": "USGS-NWIS",
        "site_no": "01646500",
        "site_name": "POTOMAC RIVER NEAR WASH, DC LITTLE FALLS PUMP STA",
        "coordinates": {"latitude": 38.94977778, "longitude": -77.12763889},
        "parameters": ["00060", "00065"],
        "query_url": (
            "https://waterservices.usgs.gov/nwis/iv/?format=json"
            "&sites=01646500&startDT=2018-05-29&endDT=2018-06-08&parameterCd=00065,00060"
        ),
        "filename_suffix": "iv_20180529_20180608",
    },
    {
        "provider": "USGS-NWIS",
        "site_no": "01463500",
        "site_name": "Delaware River at Trenton NJ",
        "coordinates": {"latitude": 40.22166667, "longitude": -74.77805556},
        "parameters": ["00060", "00065"],
        "query_url": (
            "https://waterservices.usgs.gov/nwis/iv/?format=json"
            "&sites=01463500&startDT=2021-08-29&endDT=2021-09-06&parameterCd=00065,00060"
        ),
        "filename_suffix": "iv_20210829_20210906",
    },
    {
        "provider": "USGS-NWIS",
        "site_no": "01434000",
        "site_name": "DELAWARE RIVER AT PORT JERVIS NY",
        "coordinates": {"latitude": 41.3705833, "longitude": -74.69713889},
        "parameters": ["00060", "00065"],
        "query_url": (
            "https://waterservices.usgs.gov/nwis/iv/?format=json"
            "&sites=01434000&startDT=2021-08-29&endDT=2021-09-06&parameterCd=00065,00060"
        ),
        "filename_suffix": "iv_20210829_20210906",
    },
]


def fetch_and_update(workspace_root: Path) -> int:
    """Fetch raw payloads, update manifest, and recompile source_records.csv."""
    samples_dir = workspace_root / "data/raw/samples"
    manifest_path = workspace_root / "data/manifests/provider_manifest.jsonl"
    source_records_path = workspace_root / "data/source_records.csv"

    samples_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing manifest entries to avoid duplicates
    existing_urls = set()
    existing_lines = []
    if manifest_path.is_file():
        with manifest_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    existing_urls.add(entry.get("query_url"))
                    existing_lines.append(line.strip())

    new_entries = []
    for spec in COHORT_FETCH_SPECS:
        query_url = spec["query_url"]
        site_no = spec["site_no"]
        provider = spec["provider"]
        suffix = spec["filename_suffix"]

        payload_rel = f"data/raw/samples/{provider.lower().replace('-', '_')}_{site_no}_{suffix}.json"
        meta_rel = f"data/raw/samples/{provider.lower().replace('-', '_')}_{site_no}_{suffix}_meta.json"
        payload_file = workspace_root / payload_rel
        meta_file = workspace_root / meta_rel

        if query_url in existing_urls and payload_file.is_file():
            print(f"Skipping already cached: {site_no} ({suffix})")
            continue

        print(f"Fetching genuine observations for site {site_no}...")
        req = urllib.request.Request(
            query_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate",
            },
        )
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_bytes = resp.read()
            latency = time.monotonic() - t0
            status_code = resp.status
            headers_dict = dict(resp.headers.items())

            if resp.headers.get("Content-Encoding") == "gzip":
                raw_bytes = gzip.decompress(raw_bytes)

        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()

        # Write raw bytes
        payload_file.write_bytes(raw_bytes)

        # Write metadata
        metadata = {
            "provider": provider,
            "site_no": site_no,
            "site_name": spec["site_name"],
            "query_url": query_url,
            "http_status": status_code,
            "headers": headers_dict,
            "retrieval_timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "sha256": sha256_hash,
            "byte_length": len(raw_bytes),
            "response_latency_sec": round(latency, 4),
        }
        meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        manifest_entry = {
            "provider": provider,
            "site_no": site_no,
            "site_name": spec["site_name"],
            "coordinates": spec["coordinates"],
            "parameters": spec["parameters"],
            "query_url": query_url,
            "retrieval_timestamp_utc": metadata["retrieval_timestamp_utc"],
            "sha256": sha256_hash,
            "raw_path": payload_rel,
            "meta_path": meta_rel,
            "byte_length": len(raw_bytes),
            "http_status": status_code,
            "response_latency_sec": round(latency, 4),
        }
        new_entries.append(manifest_entry)
        existing_urls.add(query_url)
        print(f" -> Saved {len(raw_bytes)} bytes, SHA-256: {sha256_hash[:16]}...")

    # Write combined manifest
    if new_entries:
        with manifest_path.open("w", encoding="utf-8") as f:
            for line in existing_lines:
                f.write(line + "\n")
            for entry in new_entries:
                f.write(json.dumps(entry) + "\n")
        print(f"Appended {len(new_entries)} entries to {manifest_path}")

    # Rebuild source_records.csv
    print(f"Recompiling {source_records_path}...")
    total_records = build_source_records_from_samples(
        manifest_path=manifest_path,
        workspace_root=workspace_root,
        output_csv_path=source_records_path,
    )
    print(f"Successfully compiled {total_records} source records into {source_records_path}")
    return total_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch historical observations for research cohort.")
    parser.parse_args()
    root = Path(".").resolve()
    fetch_and_update(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
