"""Scan publication bytes for selected credential formats; never print matches."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


def main():
    root = Path(__file__).resolve().parents[3]
    dest = Path(__file__).resolve().parent
    patterns = {
        "private_key_block": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----\s*\n[A-Za-z0-9+/=]{24,}"),
        "github_token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
        "openai_token": re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{48,}\b"),
        "aws_access_key": re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    }
    raw = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root)
    findings, checked = [], 0
    for name in sorted(set(raw.decode().split("\0")) - {"", "project/audit/revalidation/publication_check.json"}):
        path = root / name
        if not path.is_file():
            continue
        data = path.read_bytes()
        checked += 1
        for key, pattern in patterns.items():
            if pattern.search(data):
                findings.append({"path": name, "pattern": key})
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": "whole nonignored working-tree byte scan for selected credential formats; not a guarantee of no secrets or a data license approval",
        "files_scanned": checked, "findings": findings,
        "inherited_license_sha256": hashlib.sha256((root / "source/flood_sentinel/LICENSE").read_bytes()).hexdigest(),
        "root_license_sha256": hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest(),
        "raw_study_data_created": False,
        "personal_signing_key_accessed_in_earlier_suites": "unknown",
        "key_scope_evidence": "validation.json; this byte scan does not observe signing-key access",
        "external_response_role": "user-supplied secondary context; no provider raw data copied",
    }
    (dest / "publication_check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
