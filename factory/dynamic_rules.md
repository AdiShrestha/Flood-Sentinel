# Active dynamic rules — v3.3.0

**DR-001 Evidence before status:** output schemas, hashes, and exit codes establish integrity only; predictions and observations must be recomputed.

**DR-002 Every attempt remains:** a failed, interrupted, or evidence-rejected attempt remains under its epoch; a second favorable attempt needs a new frozen design.

**DR-003 Correct metric names:** `average_precision` is not threshold precision; AUROC score direction is tested with known vectors; aliases are rejected.

**DR-004 Denominator integrity:** IDs, source records, labels, groups, entities, and splits are joined before calculating error or failure prevalence. Empty or phantom denominators block.

**DR-005 Convergence is a measured protocol:** validation checkpoint selection, patience/tolerance, raw history, and budget are checked. “10 epochs” alone is not convergence and “not significant” is not equivalence.

**DR-006 Interactions need design:** ≤5 ablation components require full factorial coverage and repeated units; sensitivity curves need registered levels and repeats; flat curves are diagnostic findings.

**DR-007 Measure resources:** device, synchronization, warmups, raw timings, memory scopes, energy readings, and sustained interval are observations. Estimates are not observations.

**DR-008 Review binds evidence:** semantic review must reference current file hashes and resolve every diagnostic; same-session review is useful but disclosed as such.

Each rule is enforced only where `gatekeeper_spec.md` says it is. The remainder belongs in the review and is printed as a limit. New rules require a reproducing regression test and an explicit false-positive analysis.

## v3.2.0–v3.3.0 verification rules

### D-074 (Category: Scientific sufficiency, Status: ACTIVE)
Training convergence evidence is required for comparative claims. Evidence: one incident, this project. Implementation: `Audit.training` and `Audit.training_sufficiency` check epochs, loss slope, criterion, and justification. Verification: regression fixtures cover short, declining, and converged traces.

### D-075 (Category: Sensitivity, Status: ACTIVE)
A sensitivity sweep with a degenerate flat response is surfaced for investigation unless explicitly expected. Evidence: one incident, this project. Implementation: `Audit.analyses` and audit diagnostics. Verification: flat-curve fixture.

### D-076 (Category: Provenance, Status: ACTIVE)
Unused real-data inputs paired with literal-heavy result sinks are a hard provenance failure. Evidence: one incident, this project. Implementation: `_acquisition_findings` via `acquisition_audit` AST scan. Verification: phantom-input fixture.

### D-077 (Category: Sampling, Status: ACTIVE)
Comparative claims require minimum total and per-class sample support and an explicit imbalance treatment. Evidence: one incident, this project. Implementation: `Audit.cohort`. Verification: small-N and 100:1 imbalance fixtures.

### D-078 (Category: Provenance, Status: ACTIVE)
Undisclosed synthetic fallbacks are blocked; disclosed test-only fallbacks remain visible warnings. Evidence: one incident, this project. Implementation: `acquisition_audit`. Verification: fallback fixtures.

### D-079 (Category: Results, Status: ACTIVE)
Below-chance results are mandatory stops unless explicitly reported as null. Evidence: one incident, this project. Implementation: `verify_result_plausibility`. Verification: AUROC fixture.

### D-080 (Category: Results, Status: ACTIVE)
Suspiciously perfect evidence requires an investigation note. Evidence: one incident, this project. Implementation: `verify_result_plausibility`. Verification: p=0 and all-supported fixtures.

### D-081 (Category: Traceability, Status: ACTIVE)
Cross-artifact identifiers must resolve to declared source records. Evidence: one incident, this project. Implementation: `Audit.analyses_traceability`. Verification: missing-ID fixture.

### D-082 (Category: Governance, Status: ACTIVE)
Every Mandatory Constitution principle is represented in the machine-checked coverage matrix. Evidence: one incident, this project. Implementation: `verify_coverage_liveness`. Verification: drift and null-mechanism fixtures.

### D-083 (Category: Statistics, Status: ACTIVE)
Statistical and pre-submission checks inspect cited artifact values rather than keyword proximity. Evidence: one incident, this project. Implementation: `_result_findings`, `verify_statistical_protocol`, and `pre_submission_audit` inspect value-level plausibility. Verification: value-level fixtures.

### D-084 (Category: Tier inference, Status: ACTIVE)
Tier inference recognizes plural and paraphrased verdict vocabulary and ships paraphrase tests. Evidence: one incident, this project. Implementation: `tier_check` and `_detects_verdict_enum`. Verification: comma-separated verdict fixture.

### D-085 (Category: Release, Status: ACTIVE)
Release certification aggregates project-wide scientific findings and Constitution coverage. Evidence: one incident, this project. Implementation: `certify`. Verification: aggregate blocking fixture.

### D-086 (Category: Mechanical gate, Status: ACTIVE)
Comparative and causal contracts require scientific sufficiency, split, and plausibility gates. Evidence: one incident, this project. Implementation: Mandatory Mechanical Gate in `check`/certification. Verification: missing-gate fixture.

### D-087 (Category: Evidence parsing, Status: ACTIVE)
Evidence parsing rejects duplicate keys, non-finite constants, and symlink/path escapes at every component. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `engine.io.read_json` and shared readers. Verification: parser and path fixtures.

### D-088 (Category: Attempts, Status: ACTIVE)
Every execution attempt is retained and only the latest successful attempt can certify. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: epoch attempt records and audit. Verification: failed-then-success fixture.

### D-089 (Category: Reproducibility, Status: ACTIVE)
Benchmark-critical nondeterministic results require fresh-process replay within tolerance. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `Audit.claims`. Verification: mismatch fixture.

### D-090 (Category: Permutation inference, Status: ACTIVE)
Monte Carlo p-values use add-one correction; exact enumeration is used when tractable. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `engine.metrics.paired_inference`. Verification: finite-draw fixture.

### D-091 (Category: Independent arithmetic, Status: ACTIVE)
Gatekeeper-owned metric implementations are used for verification. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `engine.metrics.binary_metrics`. Verification: known direction and AP vectors.

### D-092 (Category: Temporal leakage, Status: ACTIVE)
Temporal splits enforce train < validation < test ordering. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `Audit.cohort`. Verification: temporal-order fixture.

### D-093 (Category: Ablations, Status: ACTIVE)
Ablations above five components require a disclosed fractional-factorial alias structure. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `Audit.analyses_ablation`. Verification: large-design fixture.

### D-094 (Category: Execution safety, Status: ACTIVE)
Experiment commands execute as argv lists with allowlisted experiment IDs. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `engine.plan.validate` and `safe_args`. Verification: shell metacharacter fixture.

## v3.3.0 trust-boundary rules

### D-095 (Category: Execution contract, Status: ACTIVE)
Experiment execution uses typed contracts; the supervisor constructs the launch command from `runtime_id` and `entrypoint`. Shell wrappers, inline-code flags, and free-form interpreter flags are rejected. Evidence: trust-boundary analysis. Implementation: `validate_contract` and `resolve_contract`. Verification: ATK-001, ATK-002, ATK-018 fixtures.

### D-096 (Category: Content addressing, Status: ACTIVE)
Frozen file inventories produce a Merkle root over sorted (path, SHA-256) pairs. Symlinks, device files, FIFOs, sockets, and importable binaries (.pyc, .so, .dylib) are rejected. Evidence: trust-boundary analysis. Implementation: `engine.io.merkle_root` and `inventory`. Verification: ATK-004, ATK-005 fixtures.

### D-097 (Category: Receipt signing, Status: ACTIVE)
Execution receipts are signed by the supervisor using Ed25519 (or HMAC-SHA256 fallback). Receipts bind 16 fields including run nonce, snapshot root, interpreter hash, dependency lock hash, and timestamps. Evidence: trust-boundary analysis. Implementation: `build_receipt` and `verify_receipt_signature`. Verification: ATK-007, ATK-008 fixtures.

### D-098 (Category: Schema validation, Status: ACTIVE)
All evidence validators use strict typed schemas that reject boolean/string/integer confusion, empty structures satisfying vacuous checks, and justification strings bypassing numeric requirements. Evidence: trust-boundary analysis. Implementation: `expect_str` and `engine.schema`. Verification: ATK-012 fixtures.

### D-099 (Category: Recursive plausibility, Status: ACTIVE)
Plausibility analysis recursively traverses all result containers (computed_runs, comparisons, derived_analyses) to detect zero p-values, below-chance metrics, and implausibly narrow CIs at any nesting depth. Evidence: trust-boundary analysis. Implementation: `_deep_result_findings`. Verification: ATK-013 fixtures.

### D-100 (Category: Reproduction identity, Status: ACTIVE)
Reproductions must match the original's model identity, config digest, training mode, and runtime. Relabeling a different model as a reproduction is a hard provenance failure. Evidence: trust-boundary analysis. Implementation: `_compute_assurance_level` and `engine.audit.Audit.claims`. Verification: ATK-014 fixtures.

### D-101 (Category: Assurance level, Status: ACTIVE)
Audit reports and release certifications declare explicit machine-readable assurance levels with checkable prerequisites. Levels: STRUCTURALLY_VALIDATED, SUPERVISOR_ATTESTED, SEALED_EVALUATION_ATTESTED, INDEPENDENT_REVIEW_COMPLETE, READY_FOR_HUMAN_SUBMISSION_REVIEW. Evidence: trust-boundary analysis. Implementation: `_assurance_with_review`. Verification: assurance level fixtures.

### D-102 (Category: Attack registry, Status: ACTIVE)
An attack registry of 18 behavioral mutation tests maps each security invariant to a concrete attack fixture. A release candidate is blocked until every listed attack fails through the complete lifecycle. Evidence: trust-boundary analysis. Implementation: `verify_attack_registry`. Verification: attack registry well-formedness and all 18 ATK fixtures.
