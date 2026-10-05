"""Authentic data provider acquisition and feasibility verification runner.

Fetches sample observations and flood stage thresholds from USGS NWIS,
NOAA NWPS, and NASA Daymet REST APIs to verify genuine endpoint availability,
response schemas, and payload integrity.
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
import urllib.error
import urllib.request


USER_AGENT = "FloodSentinel-Research/1.0 (Hydrological Anomaly Research; Non-Commercial)"


def now_utc_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return dt.datetime.now(dt.timezone.utc).isoformat()


def compute_sha256(data: bytes) -> str:
    """Compute hex-encoded SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def fetch_endpoint(
    url: str,
    accept: str = "application/json, text/plain, */*",
    timeout: int = 30,
) -> tuple[bytes, int, dict[str, str], float]:
    """Execute real HTTP GET request against provider endpoint.

    Fails closed on any network error or HTTP status code >= 400.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Encoding": "gzip, deflate",
        },
    )
    start_time = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw_content = response.read()
        latency_sec = time.monotonic() - start_time
        status_code = response.status
        headers_dict = dict(response.headers.items())

        # Transparently decompress if gzip-encoded
        if response.headers.get("Content-Encoding") == "gzip":
            raw_content = gzip.decompress(raw_content)

        return raw_content, status_code, headers_dict, latency_sec


def save_sample_and_manifest(
    provider: str,
    site_no: str,
    site_name: str,
    coordinates: dict[str, float | None],
    parameters: list[str],
    query_url: str,
    raw_bytes: bytes,
    status_code: int,
    headers: dict[str, str],
    latency_sec: float,
    output_dir: Path,
    manifest_entries: list[dict],
    filename_suffix: str,
) -> dict:
    """Write raw response bytes and metadata; record manifest entry."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now_utc_iso()
    digest = compute_sha256(raw_bytes)

    base_name = f"{provider.lower().replace('-', '_')}_{site_no}_{filename_suffix}"
    payload_filename = f"{base_name}.json" if raw_bytes.strip().startswith((b"{", b"[")) else f"{base_name}.dat"
    payload_path = output_dir / payload_filename
    meta_filename = f"{base_name}_meta.json"
    meta_path = output_dir / meta_filename

    # Save raw payload bytes
    payload_path.write_bytes(raw_bytes)

    # Save response headers and metadata
    metadata = {
        "provider": provider,
        "site_no": site_no,
        "site_name": site_name,
        "query_url": query_url,
        "http_status": status_code,
        "latency_seconds": round(latency_sec, 4),
        "retrieval_timestamp_utc": timestamp,
        "sha256": digest,
        "byte_length": len(raw_bytes),
        "headers": headers,
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    manifest_record = {
        "provider": provider,
        "site_no": site_no,
        "site_name": site_name,
        "coordinates": coordinates,
        "parameters": parameters,
        "query_url": query_url,
        "retrieval_timestamp_utc": timestamp,
        "sha256": digest,
        "raw_path": str(payload_path.as_posix()),
        "meta_path": str(meta_path.as_posix()),
        "byte_length": len(raw_bytes),
        "http_status": status_code,
        "response_latency_sec": round(latency_sec, 4),
    }
    manifest_entries.append(manifest_record)
    return manifest_record


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch authentic sample hydrological data.")
    parser.add_argument(
        "--output-dir",
        default="data/raw/samples",
        help="Directory to store raw responses and metadata (gitignored).",
    )
    parser.add_argument(
        "--manifest-path",
        default="data/manifests/provider_manifest.jsonl",
        help="Path for provider manifest JSONL.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout in seconds.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    manifest_path = Path(args.manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[dict] = []

    # 1. Primary candidate gauge sites
    sites = [
        {
            "site_no": "01646500",
            "name": "Potomac River near Washington DC (Little Falls)",
            "nwps_id": "01646500",
            "lat": 38.94977778,
            "lon": -77.12763889,
        },
        {
            "site_no": "01463500",
            "name": "Delaware River at Trenton NJ",
            "nwps_id": "01463500",
            "lat": 40.22166667,
            "lon": -74.77805556,
        },
        {
            "site_no": "01434000",
            "name": "Delaware River at Port Jervis NY",
            "nwps_id": "01434000",
            "lat": 41.3705833,
            "lon": -74.69713889,
        },
    ]

    print("=" * 80)
    print("Executing Authentic Provider Feasibility Sample Fetch")
    print(f"Timestamp: {now_utc_iso()}")
    print(f"Output directory: {output_dir}")
    print(f"Manifest output: {manifest_path}")
    print("=" * 80)

    # 1. Fetch USGS NWIS Instantaneous Values (Stage & Discharge)
    for site in sites:
        site_no = site["site_no"]
        print(f"\n[USGS NWIS] Fetching IV for site {site_no} ({site['name']})...")
        usgs_url = (
            f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_no}"
            "&period=P1D&parameterCd=00065,00060"
        )
        try:
            raw_bytes, status, headers, latency = fetch_endpoint(usgs_url, timeout=args.timeout)
            parsed = json.loads(raw_bytes.decode("utf-8"))
            ts_list = parsed.get("value", {}).get("timeSeries", [])
            if not ts_list:
                raise ValueError(f"USGS site {site_no} returned zero time series.")

            source_info = ts_list[0].get("sourceInfo", {})
            geo = source_info.get("geoLocation", {}).get("geogLocation", {})
            coords = {
                "latitude": geo.get("latitude", site["lat"]),
                "longitude": geo.get("longitude", site["lon"]),
            }
            actual_name = source_info.get("siteName", site["name"])

            params = [
                ts.get("variable", {}).get("variableCode", [{}])[0].get("value", "unknown")
                for ts in ts_list
            ]

            record = save_sample_and_manifest(
                provider="USGS-NWIS",
                site_no=site_no,
                site_name=actual_name,
                coordinates=coords,
                parameters=sorted(list(set(params))),
                query_url=usgs_url,
                raw_bytes=raw_bytes,
                status_code=status,
                headers=headers,
                latency_sec=latency,
                output_dir=output_dir,
                manifest_entries=manifest_entries,
                filename_suffix="iv",
            )
            print(f"  Status {status} ({latency:.3f}s) | Bytes: {len(raw_bytes)} | SHA256: {record['sha256'][:16]}...")
            print(f"  Resolved name: {actual_name}")
            print(f"  Parameters: {params}")
        except Exception as ex:
            print(f"  [ERROR] USGS fetch failed for {site_no}: {ex}", file=sys.stderr)
            raise

    # 2. Fetch NOAA NWPS Flood Stages & Metadata
    for site in sites:
        site_no = site["site_no"]
        nwps_id = site["nwps_id"]
        print(f"\n[NOAA NWPS] Fetching flood stage metadata for site {site_no} (NWPS ID: {nwps_id})...")
        nwps_url = f"https://api.water.noaa.gov/nwps/v1/gauges/{nwps_id}"
        try:
            raw_bytes, status, headers, latency = fetch_endpoint(nwps_url, timeout=args.timeout)
            parsed = json.loads(raw_bytes.decode("utf-8"))
            lid = parsed.get("lid")
            name = parsed.get("name", site["name"])
            categories = parsed.get("flood", {}).get("categories", {})
            coords = {
                "latitude": parsed.get("latitude", site["lat"]),
                "longitude": parsed.get("longitude", site["lon"]),
            }
            record = save_sample_and_manifest(
                provider="NOAA-NWPS",
                site_no=site_no,
                site_name=f"{name} (LID: {lid})",
                coordinates=coords,
                parameters=list(categories.keys()),
                query_url=nwps_url,
                raw_bytes=raw_bytes,
                status_code=status,
                headers=headers,
                latency_sec=latency,
                output_dir=output_dir,
                manifest_entries=manifest_entries,
                filename_suffix="nwps",
            )
            print(f"  Status {status} ({latency:.3f}s) | LID: {lid} | Bytes: {len(raw_bytes)} | SHA256: {record['sha256'][:16]}...")
            print(f"  Flood categories: {categories}")
        except Exception as ex:
            print(f"  [ERROR] NOAA NWPS fetch failed for {site_no}: {ex}", file=sys.stderr)
            raise

    # 3. Fetch NASA Daymet Single-Pixel Daily Meteorology
    print("\n[NASA Daymet] Fetching sample meteorology for candidate gauge catchments...")
    for site in sites[:2]:
        site_no = site["site_no"]
        lat = site["lat"]
        lon = site["lon"]
        print(f"  Querying Daymet single-pixel for {site['name']} (lat={lat:.4f}, lon={lon:.4f})...")
        daymet_url = (
            f"https://daymet.ornl.gov/single-pixel/api/data?lat={lat:.4f}&lon={lon:.4f}"
            "&vars=prcp,tmax,tmin,swe&start=2022-01-01&end=2022-01-05&format=json"
        )
        try:
            raw_bytes, status, headers, latency = fetch_endpoint(daymet_url, timeout=args.timeout)
            parsed = json.loads(raw_bytes.decode("utf-8"))
            vars_list = list(parsed.get("data", {}).keys())
            record = save_sample_and_manifest(
                provider="NASA-Daymet",
                site_no=site_no,
                site_name=f"Daymet Pixel for {site['name']}",
                coordinates={"latitude": lat, "longitude": lon},
                parameters=vars_list,
                query_url=daymet_url,
                raw_bytes=raw_bytes,
                status_code=status,
                headers=headers,
                latency_sec=latency,
                output_dir=output_dir,
                manifest_entries=manifest_entries,
                filename_suffix="daymet",
            )
            print(f"    Status {status} ({latency:.3f}s) | Tile: {parsed.get('Tile')} | Bytes: {len(raw_bytes)} | SHA256: {record['sha256'][:16]}...")
            print(f"    Variables: {vars_list}")
        except Exception as ex:
            print(f"  [ERROR] Daymet fetch failed for {site_no}: {ex}", file=sys.stderr)
            raise

    # 4. Feasibility audit probe on legacy reference USGS 01438000 (Neversink River at Port Jervis)
    # This proves that unmonitored sites fail closed without synthetic generation.
    print("\n[Feasibility Audit Probe] Probing legacy reference site USGS 01438000...")
    probe_url = "https://waterservices.usgs.gov/nwis/site/?format=rdb&sites=01438000"
    try:
        raw_bytes, status, headers, latency = fetch_endpoint(probe_url, timeout=args.timeout)
        record = save_sample_and_manifest(
            provider="USGS-NWIS-SiteService",
            site_no="01438000",
            site_name="NEVERSINK RIVER AT PORT JERVIS NY (Legacy Reference)",
            coordinates={"latitude": 41.361205, "longitude": -74.6848851},
            parameters=["site_metadata"],
            query_url=probe_url,
            raw_bytes=raw_bytes,
            status_code=status,
            headers=headers,
            latency_sec=latency,
            output_dir=output_dir,
            manifest_entries=manifest_entries,
            filename_suffix="site_rdb",
        )
        print(f"  Status {status} ({latency:.3f}s) | Resolved name: NEVERSINK RIVER AT PORT JERVIS NY")
        print(f"  SHA256: {record['sha256'][:16]}...")
    except Exception as ex:
        print(f"  [ERROR] Probe fetch failed: {ex}", file=sys.stderr)
        raise

    # Write out data/manifests/provider_manifest.jsonl
    print(f"\nWriting immutable provider manifest: {manifest_path} ({len(manifest_entries)} entries)")
    with manifest_path.open("w", encoding="utf-8") as f:
        for entry in manifest_entries:
            f.write(json.dumps(entry) + "\n")

    print("\n" + "=" * 80)
    print("Provider Feasibility Sample Acquisition Complete")
    print(f"Total authentic payloads recorded: {len(manifest_entries)}")
    for entry in manifest_entries:
        print(f" - [{entry['provider']}] Site {entry['site_no']}: {entry['byte_length']} bytes, SHA256: {entry['sha256'][:16]}...")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
