# Validation record for v3.3.0

On 2026-09-16 UTC, the standard-library self-test suite ran with Python 3.12:
**276 tests passed**. The full Pytest suite passed **281 tests**. Added v3.3 checks cover typed execution contracts, supervisor signing keys and receipts, Merkle root frozen file inventories, strict typed schema validation, recursive plausibility analysis, reproduction identity binding, multi-level assurance statuses, 18 behavioral mutation attack registry tests, and standalone bundle verification.

The transfer archive is independently checked by both `verify-bundle` and `verify_bundle_standalone.py`, which validate member names, manifest membership, assurance level, and SHA-256 bytes without extracting files. This proves archive integrity, not source honesty or scientific truth.

The earlier validation records are retained below for historical provenance.

## Validation record for v3.2.0

On 2026-09-14 UTC, the standard-library self-test suite ran with Python 3.12:
**65 tests passed**. The full Pytest suite, including retained legacy regression
coverage, passed **283 tests and 1 subtest**. Added v3.2 checks cover inline
interpreter smuggling, JSON number overflow, bundle checksum tampering, generated
report freezing, certificate revocation, direct-attempt recovery binding, and
macOS `/var`/`/private/var` path aliases.

The transfer archive is independently checked by `verify-bundle`, which validates
member names, manifest membership, and SHA-256 bytes without extracting files.
This proves archive integrity, not source honesty or scientific truth.

The earlier v3.0.0 validation record is retained below for historical provenance.

The read-only v2.6 forensic tool ran against all 50 supplied Parquet runs using PyArrow and scikit-learn. Its machine-readable result is `docs/v26_forensic_results.json`. The active factory gate itself has no third-party dependency. Torch, GUDHI, pandas, device drivers, energy sensors, and domain libraries are intentionally not bundled: agents declare and lock them inside the project and the gate records their exact environment.

The suite includes adversarial fixtures, but a fixture cannot prove the honesty of arbitrary production code. Any claim beyond the binary-classification profile requires a reviewed lossless adapter and domain-specific mutation tests.
