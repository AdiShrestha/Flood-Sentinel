# CHANGELOG — Factory v3.3.0

## v3.3.0 — trust-boundary hardening

### Typed Execution Contracts
- Projects now declare `execution_contract` with `runtime_id` and `entrypoint` instead of free-form command arrays. The supervisor constructs the actual command with hardening flags (`-I -P -B -S`).
- Legacy `command` arrays remain accepted but emit a deprecation diagnostic and are internally converted to contracts.
- Attached inline-code flags (`-cexec(...)`) are now rejected alongside separate flags.
- Resource limits (`cpu_seconds`, `memory_bytes`, `process_limit`) enforced via `setrlimit` on child processes.

### Immutable Content-Addressed Snapshots
- Freeze now computes a Merkle root over all frozen files (sorted path + SHA-256). Stored in `freeze.json` as `snapshot_merkle_root`.
- Inventory rejects device files (FIFOs, sockets, block/char devices).
- Importable binaries (`.pyc`, `.pyo`, `.so`, `.dylib`, `.dll`, `.pyd`) are rejected in frozen paths unless explicitly whitelisted.
- Dot-segment path tricks (`project/./audit_report.json`) are normalized and rejected.

### Supervisor-Signed Receipts
- New `engine/supervisor.py` generates Ed25519-signed (or HMAC-SHA256 fallback) execution receipts.
- Receipts bind 16 fields: run nonce, project ID, epoch, experiment ID, snapshot Merkle root, input root, runtime ID, interpreter hash, dependency lock hash, launch spec, seed, output root, exit status, resource observations, timestamps, supervisor/policy version.
- Signing key stored outside the workspace (`~/.factory/supervisor.key`).
- Receipt verification rejects tampered signatures, replayed receipts, and unknown signing keys.

### Strict Typed Schema Validation
- New `engine/schema.py` provides `expect_bool`, `expect_int`, `expect_float`, `expect_str`, `expect_list`, `expect_dict`, `expect_enum`, `expect_id` — all reject type confusion.
- `"false"` is no longer truthy. `True`/`1` no longer accepted as integers. Empty structures no longer satisfy vacuous checks.
- Training, split, plausibility, and reproduction validators rewritten to use strict typed schemas.
- Single code path: standalone CLI and certification use the same validator.

### Recursive Plausibility Analysis
- `_deep_result_findings()` recursively traverses `computed_runs`, `comparisons`, `derived_analyses`, and nested result containers.
- Zero p-values, below-chance metrics, and implausibly narrow CIs detected at any nesting depth.
- Investigation notes now support optional `investigation_disposition` field (`explained`, `claim_narrowed`, `unresolved`).

### Reproduction Identity Binding
- Reproductions must match the original's `model` identity, `config` digest, and `training.mode`.
- Relabeling an easier baseline as a reproduction of the target is a hard provenance failure.

### Multi-Level Assurance Statuses
- Audit reports and certificates now include `assurance_level`: `STRUCTURALLY_VALIDATED`, `SUPERVISOR_ATTESTED`, `SEALED_EVALUATION_ATTESTED`, `INDEPENDENT_REVIEW_COMPLETE`, `READY_FOR_HUMAN_SUBMISSION_REVIEW`.
- Certificates include `assurance_components` breaking down byte integrity, execution provenance, runtime integrity, evaluation integrity, and statistical validity.

### Portable Bundle Verification
- Bundles include `assurance_level` and `release_status` in the manifest.
- New `verify_bundle_standalone.py` verifies bundle integrity without importing gatekeeper or engine modules.

### Attack Registry
- New `engine/attacks.py` registers 18 concrete attacks with invariant, implementation, fixture, and expected transition.
- All attacks covered by behavioral mutation tests in `test_v3_3_hardening.py`.

### Runtime Attestation
- Execution records include `runtime_attestation` capturing interpreter hash, Python version, platform, locale, timezone, encoding, and byte order.
- `run_nonce` (UUID4) uniquely identifies each execution attempt.
- `PYTHONDONTWRITEBYTECODE=1` set in execution environment.
- `dependency_lock_hash` and `interpreter_hash` bound in execution records.

### Documentation
- Constitution principles C85–C92 added for trust-boundary mechanisms.
- Coverage YAML maps C85–C92 to implementations.
- Dynamic rules D-095 through D-102 document new mechanisms.

### Tests
- 91 new tests in `test_v3_3_hardening.py` covering all 18 attack registry entries.
- Total test count: 161 (from 70).

## v3.2.0 — stability and adversarial hardening

- Fixed macOS `/var` and `/private/var` alias handling across freezes, inventories, and run artifacts.
- Added strict direct-attempt binding for recovery recording and canonical operation locking.
- Treats record-error attempts as retained failures so a clean rerun cannot create a duplicate-success dead end.
- Closed malformed-manifest loopholes in reproducibility, training, split, traceability, sensitivity, and numeric validation checks.
- Prevented generated audit/review/certification files from being declared frozen inputs.
- Rejects inline shell/interpreter execution modes, including wrapped and versioned interpreters.
- Requires each experiment command to name a declared frozen source path, blocking module-only execution outside the declared producer.
- Rejects interpreter/library injection environment hooks and binds Python hash randomization to the experiment seed.
- Revokes release certification when the active evidence or execution state changes.
- Adds a checksum manifest and `verify-bundle` command for safe handoff verification.

## v3.1.1 — coverage-liveness repair

### Context

The build distributed as "v3.1.0 final" added `_is_trivial` but never called it from
`verify_coverage_liveness`, and separately deleted the `training_sufficiency()` and
`analyses_ablation()` call sites from `training()`/`analyses()` without extracting real
logic into them or updating `constitution_coverage.yaml`. The net effect, confirmed by
running the shipped test suite: `verify_coverage_liveness` failed unconditionally
(`C72`/`C84` unreachable), and because `_finalize_release_checks` folds its result into
`certify()`'s error list, `certify()` could not succeed for any project, including a
correct one. `test_coverage_liveness_is_clean`, `test_missing_review_withholds_release`,
and `test_stale_review_withholds_release` failed as a result.

### Fixed

- `training_sufficiency`, `analyses_traceability`, and `analyses_ablation` are no longer
  `return True` markers. Each now contains the real assertions that previously sat
  inline in `training()`/`analyses()` (history contiguity and budget; failure-analysis ID
  tracing against the immutable cohort; factorial/fractional-design and replication
  checks), called with the arguments needed to do that work, at the point in the method
  where that data first exists.
- `verify_coverage_liveness` now actually calls its own triviality check. Fixed the
  check itself along the way: the first version flagged `_acquisition_findings` as
  trivial because it is a thin dispatcher with no control flow of its own — it delegates
  to two real scanner functions. Replaced the body-only check with `_is_substantive`,
  which walks the call graph transitively, so a dispatcher counts as substantive through
  what it calls, and only a function whose entire reachable subgraph is inert gets
  flagged.
- Fixed `_call_graph`'s module attribution: `engine/metrics.py` and `engine/io.py`
  functions were being labeled `gatekeeper.*` instead of `engine.metrics.*` /
  `engine.io.*`, which is why `paired_inference`, `binary_metrics`, and `read_json` had
  to be hand-exempted from the reachability check in v3.1.0. They resolve correctly now
  and the exemption list is gone.
- Fixed `engine/plan.py`'s accepted-version check: it was `('3.0.0','3.1.0','3.1.0')` —
  a duplicate with `3.0.1` silently missing — contradicting the v3.0.1 changelog entry's
  own claim that 3.0.1 plans remain valid. Now `('3.0.0','3.0.1','3.1.0','3.1.1')`.
- Fixed CWD-relative temp-file paths in `tests/test_v3_1_hardening.py` that made 4 tests
  fail when run via `python -m unittest discover` from inside `factory/` instead of via
  `run_self_tests.py` from the repo root. Paths are now relative to the test file.

### Added

- `AcquisitionAuditBlocksCertifyTests`: the missing end-to-end regression guard for the
  fix that mattered most in v3.1.0. Plants a phantom-input-fabrication pattern (unused
  parameter, literal-dense dict, `build_`-prefixed return) in a fixture's `code_paths`,
  runs the real `freeze → run → certify` lifecycle, and asserts `certify()` returns
  non-zero with `ACQUISITION_AUDIT` in the audit report's errors — plus a negative
  control confirming the unmodified fixture does not trip the same check.

### Validation

Ran the full suite via `python3 factory/run_self_tests.py` from the repo root and via
`python3 -m unittest discover -s tests` from inside `factory/`: 56/56 pass both ways
(54 prior + 2 new). Directly invoked `verify_coverage_liveness` against this tree:
`{"status": "PASS", "principles_checked": 15, "callables_resolved": 15}`. Adversarially
reintroduced a `return True` stub for `training_sufficiency` in an isolated copy and
confirmed `verify_coverage_liveness` still catches it — the check was tested against a
known failure, not just observed to pass once.

## v3.1.0 — closed-loop hardening

### Fixed

- Wired the AST acquisition/provenance scanner into `certify`; hard findings now block release and disclosed warnings become review diagnostics.
- Replaced the aliased statistical, pre-submission, and failure-taxonomy commands with distinct value-level validators (exit codes 27, 29, and 30).
- Replaced keyword-only `check` validation with strict JSON contracts containing registered executable checks and bound artifacts.
- Added `verify-coverage-liveness`, which resolves coverage mechanisms to callables, checks reachability from `certify`/`Audit.run`, rejects duplicate callable attribution, and detects drift against `dynamic_rules.md`.
- Corrected Constitution coverage to point at the live audit and metric implementations; added liveness markers for traceability and ablation coverage.

### Operator workflow

The normal path remains `init` → `freeze` → `run . all` → `certify` → `handoff`. Certification now runs provenance, tier (when declared), plausibility, and coverage-liveness gates automatically. The separate verification commands remain available for diagnostics and CI.

### Validation

The offline regression suite passes with 54 tests, plus v3.1.0 hardening checks. The release remains evidence-admissibility tooling; population validity, causal identification, source authenticity, and venue acceptance stay explicitly unautomated.

## v3.0.0

Ground-up scientific evidence architecture, informed by the v2.6 audit and supplied failed project. Active policy is the new `gatekeeper.py` and the v3 role/constitution documents; v2.6 is retained under `factory/legacy/v2_6_0/` for historical migration only.

### Closed failure classes

- F-001/F-014: response curves require planned perturbation levels and non-degenerate recomputed outputs; convergence is checked per run.
- F-002/F-024: result-producer static audit rejects synthetic RNG, mock/fabrication paths, and result literals; evidence must point to run receipts and predictions.
- F-003/F-004: five preregistered seeds, minimum neural budget of ten epochs, real loss trace, and explicit early stopping/justification.
- F-005: class minimums, unique IDs, and group-disjoint splits are checked from raw prediction rows.
- F-006/F-007: failure analysis must carry prediction IDs and source condition IDs; phantom IDs cannot be certified.
- F-008/F-009: constant scores, one-class test sets, non-finite values, and metric recomputation failures hard-fail.
- F-015/F-016: below-chance or surprising outcomes are retained as findings requiring explanation, never silently converted to support.
- F-017/F-020/F-021/F-022: certification names exactly what was checked and requires substantive adversarial review, not regex theater.
- F-019: independent metric implementation (`engine/metrics.py`) is mandatory.

### Metric correction

The supplied project’s “AUROC” ranks scores in the reverse direction and its “AUPRC” is precision at a threshold. V3 uses the standard Mann–Whitney AUROC and non-interpolated average precision, with tests against known vectors.

### v2.1 lesson

The Auditor role and registry explosion are not reintroduced. Agents keep the two-role workflow. Evidence is carried by one frozen plan, run receipts, and a review record; internal validation complexity is hidden from the Human.

## v3.0.1 — verification-surface repair and hardening

### Context
The supplied 3.0.0 archive contained a strong evidence lifecycle but omitted the command surface and coverage mechanisms described by its upgrade specification. This release repairs that mismatch and incorporates the addendum's parser, attempt, reproducibility, temporal, ablation, and execution-safety protections.

### Added
Constitution principles C70–C84, `constitution_coverage.yaml`, rules D-074–D-094, commands 31–36, AST provenance scans, result plausibility checks, cross-artifact tracing, tier paraphrase detection, and fresh-process reproducibility validation.

### Changed
The lifecycle remains backward compatible in shape. Version metadata was 3.0.1; v3.1.0 accepts 3.0.0, 3.0.1, and 3.1.0 plans. Existing strict JSON/CSV/path parsing and independent metric recomputation remain active.

### Evidence and limits
Evidence for D-074–D-086 is one thoroughly audited project; D-087–D-094 originated as mechanisms observed in a noncompliant build and are not multi-project findings. The checks are deterministic and best effort; they do not prove the scientific truth of arbitrary prose, and the remaining judgment calls stay visible in review.
