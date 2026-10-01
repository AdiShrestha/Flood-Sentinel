"""Bind the final engineering checks; preserve superseded evidence and uncertainty."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[3]
    dest = Path(__file__).resolve().parent
    selected = {"engine": "engine_run04.json", "factory": "factory_run05.json"}
    records = {key: json.loads((dest / name).read_text()) for key, name in selected.items()}
    for record in records.values():
        assert record["exit_status"] == 0
        for rel, expected in record["input_sha256"].items():
            assert sha(root / rel) == expected, rel
        assert sha(dest / record["log"]) == record["log_sha256"]
    engine_log = (dest / records["engine"]["log"]).read_text()
    factory_log = (dest / records["factory"]["log"]).read_text()
    assert re.search(r"\b47 passed\b", engine_log)
    assert re.search(r"Ran 291 tests", factory_log)
    assert re.search(r"\nOK\n", factory_log)
    guard = json.loads(factory_log.splitlines()[-1])
    assert guard["personal_factory_directory_opens"] == 0
    assert guard["fixture_key_file_opens"] == 319
    previous = json.loads((dest / "validation_superseded_before_key_scope_correction.json").read_text())
    retained = previous["retained_attempts"] + [
        {"record": "engine_run03.json", "exit_status": 0, "tests_passed": 47,
         "reason": "superseded complete-input snapshot before test key-isolation correction"},
        {"record": "factory_run04.json", "exit_status": 0, "tests_passed": 291,
         "reason": "superseded key-isolation harness; personal default-key access unknown"},
    ]
    validation = {
        "scope": "engineering fixtures only; no observational performance, research freeze or independent scientific certification",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "engine": {"version": "0.2.0", "tests_passed": 47},
        "factory": {"schema_version": "3.3.0", "local_patch": "3.3.0+flood.1",
                    "tests_passed": 291, "socket_fixture": "executed outside sandbox",
                    "final_key_open_guard": guard},
        "retained_attempts": retained,
        "superseded_metadata": {
            "validation_superseded_before_key_scope_correction.json": {
                "sha256": sha(dest / "validation_superseded_before_key_scope_correction.json"),
                "invalid_claim": "personal_signing_keys_accessed=false; earlier suite fallback access is unknown"},
            "publication_check_superseded_before_key_scope_correction.json": {
                "sha256": sha(dest / "publication_check_superseded_before_key_scope_correction.json"),
                "invalid_claim": "personal_signing_key_accessed=false; byte-pattern scan cannot establish prior key access"},
        },
        "personal_signing_keys_accessed_in_earlier_suites": "unknown",
        "final_key_scope_limit": "parent-process open guard; child processes inherit restored fixture-key environment, without a separate OS-level child access trace",
        "personal_key_intentionally_rotated": False,
        "private_key_material_published": False,
        "no_study_cohort_created": True,
        "no_research_epoch_or_certificate_created": True,
        "current_test_inputs_and_log_hashes_verified": True,
    }
    for key, name in selected.items():
        validation[key].update(record=name, log=records[key]["log"], record_sha256=sha(dest / name))
    (dest / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")

    baseline = json.loads((dest / "before_inventory.json").read_text())
    before = {row["path"]: row["sha256"] for row in baseline["files"]}
    changes = []
    for path in sorted((root / "factory").rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or set(rel.parts) & {"legacy", "__pycache__", ".pytest_cache"} or path.suffix == ".pyc":
            continue
        digest = sha(path)
        if digest != before.get(str(rel)):
            changes.append({"path": str(rel), "before_sha256": before.get(str(rel)), "after_sha256": digest})
    assert not any(row["path"] in {"factory/constitution.md", "factory/CONSTITUTION.md", "factory/VERSION"} for row in changes)
    (dest / "factory_patch_manifest.json").write_text(json.dumps({
        "base_commit": baseline["base_commit"], "schema_version": "3.3.0",
        "local_patch_version": "3.3.0+flood.1",
        "scope": "tightened local integrity; no bypass or scientific certification",
        "changes": changes,
    }, indent=2) + "\n")

    package = json.loads((dest / "package_validation.json").read_text())
    wheel = Path("/private/tmp/flood-engine-revalidation-wheel") / package["wheel"]
    assert sha(wheel) == package["sha256"]
    expected = list((root / "source/flood_sentinel").glob("*.py")) + [root / "source/flood_sentinel/LICENSE"]
    with zipfile.ZipFile(wheel) as archive:
        for path in expected:
            assert archive.read(str(path.relative_to(root / "source"))) == path.read_bytes(), path
        assert "Version: 0.2.0" in archive.read("flood_sentinel_engine-0.2.0.dist-info/METADATA").decode()
    print(json.dumps({"current_input_bindings_verified": True, "engine_tests": 47,
                      "factory_tests": 291, "factory_changed_files": len(changes),
                      "packaged_engine_modules": len(expected) - 1,
                      "earlier_suite_key_access": "unknown", "final_parent_guard": guard}))


if __name__ == "__main__":
    main()
