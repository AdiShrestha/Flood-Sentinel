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
Training convergence evidence is required for comparative claims. Evidence: one incident, this project. Implementation: `Audit.training` and `Audit.training_sufficiency` check actual contiguous history, checkpoint selection and the frozen stopping rule; justification cannot waive a budget or stopping event. Verification: regression fixtures cover short, declining, and converged traces.

False-positive analysis: Legitimate analytic methods have no training trace; they declare deterministic method evidence. Slowly converging models must extend a prospective budget rather than receive a prose waiver.

### D-075 (Category: Sensitivity, Status: ACTIVE)
A sensitivity sweep with a degenerate flat response is surfaced for investigation unless explicitly expected. Evidence: one incident, this project. Implementation: `Audit.analyses` and audit diagnostics. Verification: flat-curve fixture.

False-positive analysis: True invariance can produce a flat sweep. Investigate and disclose it; lifecycle flatness is a diagnostic and expected-flat standalone flags require structured evidence.

### D-076 (Category: Provenance, Status: ACTIVE)
Unused real-data inputs paired with literal-heavy result sinks are a hard provenance failure. Evidence: one incident, this project. Implementation: `_acquisition_findings` via `acquisition_audit` AST scan. Verification: phantom-input fixture.

False-positive analysis: Static inputs may be consumed indirectly through closures, attribute access or external APIs. The AST pattern is a conservative signal; inspect the exact producer and retain clean controls before treating it as a fabrication finding.

### D-077 (Category: Sampling, Status: ACTIVE)
Comparative claims require minimum total and per-class sample support and an explicit imbalance treatment. Evidence: one incident, this project. Implementation: `Audit.cohort`. Verification: small-N and 100:1 imbalance fixtures.

False-positive analysis: Rare classes and clustered populations may make fixed floors costly. Floors do not establish power; use a supported prospective design or a reviewed adapter rather than changing class semantics.

### D-078 (Category: Provenance, Status: ACTIVE)
Undisclosed synthetic fallbacks are blocked; disclosed test-only fallbacks remain visible warnings. Evidence: one incident, this project. Implementation: `acquisition_audit`. Verification: fallback fixtures.

False-positive analysis: Randomness may be legitimate training augmentation or declared simulation. Disclose its role and ensure fixture fallbacks never become research observations.

### D-079 (Category: Results, Status: ACTIVE)
Below-chance results are mandatory stops unless explicitly reported as null. Evidence: one incident, this project. Implementation: `verify_result_plausibility`. Verification: AUROC fixture.

False-positive analysis: AP/F1/accuracy baselines depend on prevalence and threshold. Use metric-specific constant baselines and explicit null/inconclusive scope; below-chance ranking need not imply fraud.

### D-080 (Category: Results, Status: ACTIVE)
Suspiciously perfect evidence requires an investigation note. Evidence: one incident, this project. Implementation: `verify_result_plausibility`. Verification: p=0 and all-supported fixtures.

False-positive analysis: A narrow interval can reflect deterministic identity. Explain its derivation, units and exact values; finite permutation p-values must still respect their mathematical resolution.

### D-081 (Category: Traceability, Status: ACTIVE)
Cross-artifact identifiers must resolve to declared source records. Evidence: one incident, this project. Implementation: `Audit.analyses_traceability`. Verification: missing-ID fixture.

False-positive analysis: Identifier conventions differ. Supply an explicit capture pattern and actual source joins; zero recognized IDs cannot establish traceability.

### D-082 (Category: Governance, Status: ACTIVE)
Every Mandatory Constitution principle is represented in the machine-checked coverage matrix. Evidence: one incident, this project. Implementation: `verify_coverage_liveness`. Verification: drift and null-mechanism fixtures.

False-positive analysis: Some mandatory obligations are procedural and cannot be mapped truthfully to a callable. Preserve a specific limitation rationale; mapped test existence is not behavioral proof.

### D-083 (Category: Statistics, Status: ACTIVE)
Statistical and pre-submission checks inspect cited artifact values rather than keyword proximity. Evidence: one incident, this project. Implementation: `_result_findings`, `verify_statistical_protocol`, and `pre_submission_audit` inspect value-level plausibility. Verification: value-level fixtures.

False-positive analysis: Different metrics have different ranges and zero conventions. Typed validation checks stated definitions rather than guessing from keyword substrings.

### D-084 (Category: Tier inference, Status: ACTIVE)
Tier inference recognizes plural and paraphrased verdict vocabulary and ships paraphrase tests. Evidence: one incident, this project. Implementation: `tier_check` and `_detects_verdict_enum`. Verification: comma-separated verdict fixture.

False-positive analysis: Negated causal language and mechanism-matched baselines are not causal claims. Paraphrase and negation controls limit heuristic errors; semantic claim strength remains a review task.

### D-085 (Category: Release, Status: ACTIVE)
Release certification aggregates project-wide scientific findings and Constitution coverage. Evidence: one incident, this project. Implementation: `certify`. Verification: aggregate blocking fixture.

False-positive analysis: A domain unsupported by the binary profile may be scientifically valid. It requires a reviewed adapter; schema rejection is not a verdict on the research.

### D-086 (Category: Mechanical gate, Status: ACTIVE)
Comparative and causal contracts require scientific sufficiency, split, and plausibility gates. Evidence: one incident, this project. Implementation: `engine.plan.validate` and `engine.audit.Audit`; `check` validates a structured check list only and does not execute it. Verification: missing-gate fixture.

False-positive analysis: Descriptive/null results do not require an unsupported superiority claim. Checks follow the explicitly registered claim and disclose unsupported domain scope.

### D-087 (Category: Evidence parsing, Status: ACTIVE)
Evidence parsing rejects duplicate keys, non-finite constants, and symlink/path escapes at every component. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `engine.io.read_json` and shared readers. Verification: parser and path fixtures.

False-positive analysis: Scientific libraries may emit nonstandard JSON or missing values. Convert losslessly with explicit unavailable fields; duplicate keys/non-finite numbers must never silently replace evidence.

### D-088 (Category: Attempts, Status: ACTIVE)
Every execution attempt is retained in a signed reservation ledger. Only one attempt per experiment per epoch is admissible; a failed/interrupted attempt requires a disclosed new epoch. A successful attempt needs verified signed bindings and a unique nonce matching its reservation. Evidence: observed undocumented mechanism in a noncompliant build and independent replay probes. Implementation: epoch attempt records, shared reservation validation and audit. Verification: retained-attempt and nonce consistency fixtures.

False-positive analysis: Infrastructure failures are legitimate but can contaminate selection. Retain the failed epoch and disclose a new design/holdout where confirmation is affected; no same-epoch favorable retry.

### D-089 (Category: Reproducibility, Status: ACTIVE)
Benchmark-critical nondeterministic results require fresh-process replay within tolerance. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `Audit.claims`. Verification: mismatch fixture.

False-positive analysis: Nondeterministic hardware can change predictions. Freeze a scientifically justified tolerance prospectively and retain disagreement; do not tune tolerance after a favorable replay.

### D-090 (Category: Permutation inference, Status: ACTIVE)
Monte Carlo p-values use add-one correction; exact enumeration is used when tractable. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `engine.metrics.paired_inference`. Verification: finite-draw fixture.

False-positive analysis: Exact enumeration can yield coarse p-values. Plans check feasible alpha/family resolution; an infeasible superiority assertion must change before experiments, not after.

### D-091 (Category: Independent arithmetic, Status: ACTIVE)
Gatekeeper-owned metric implementations are used for verification. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `engine.metrics.binary_metrics`. Verification: known direction and AP vectors.

False-positive analysis: Average precision and interpolated PR area are distinct. Use exact metric definitions and adapters for alternatives rather than treating alias rejection as mathematical invalidity.

### D-092 (Category: Temporal leakage, Status: ACTIVE)
Temporal splits enforce train < validation < test ordering. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `Audit.cohort`. Verification: temporal-order fixture.

False-positive analysis: Tied timestamps or retrospective cohorts may not permit strict temporal order. Choose a supported split rationale prospectively or disclose that temporal inference is unavailable.

### D-093 (Category: Ablations, Status: ACTIVE)
Ablations above five components require a disclosed fractional-factorial alias structure. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `Audit.analyses_ablation`. Verification: large-design fixture.

False-positive analysis: Fractional designs intentionally omit cells. They require alias disclosure and restricted interaction claims; coverage does not prove an isolated mechanism.

### D-094 (Category: Execution safety, Status: ACTIVE)
Experiment commands execute as argv lists with allowlisted experiment IDs. Evidence: observed undocumented mechanism in a noncompliant build. Implementation: `engine.plan.validate` and `safe_args`. Verification: shell metacharacter fixture.

## v3.3.0 trust-boundary rules

False-positive analysis: Scientific executables can be safe yet outside the allowlist. Add a reviewed runtime contract rather than accepting arbitrary wrappers as trusted execution.

### D-095 (Category: Execution contract, Status: ACTIVE)
Experiment execution uses typed contracts; the supervisor constructs the launch command from `runtime_id` and `entrypoint`. Shell wrappers, inline-code flags, and free-form interpreter flags are rejected. Evidence: trust-boundary analysis. Implementation: `validate_contract` and `resolve_contract`. Verification: ATK-001, ATK-002, ATK-018 fixtures.

False-positive analysis: Installed scientific imports and frozen sibling modules are legitimate. The validated script path and environment allowlist preserve them; explicit unsupported network isolation fails rather than pretending enforcement.

### D-096 (Category: Content addressing, Status: ACTIVE)
Frozen file inventories produce a Merkle root over sorted (path, SHA-256) pairs. Symlinks, device files, FIFOs, sockets, and importable binaries (.pyc, .so, .dylib) are rejected. Evidence: trust-boundary analysis. Implementation: `engine.io.merkle_root` and `inventory`. Verification: ATK-004, ATK-005 fixtures.

False-positive analysis: Generated caches and platform metadata are not scientific inputs. Explicitly excluded cache paths do not count as frozen evidence; executable binary dependencies require a declared supported trust model.

### D-097 (Category: Receipt signing, Status: ACTIVE)
Execution receipts are signed by the supervisor using Ed25519, with cryptography required and HMAC downgrade rejected. Receipts bind the declared execution identity, input/output digests and runtime fields including run nonce, snapshot root, interpreter hash, dependency lock hash, and timestamps. Identity and exit fields preserve JSON types; signed receipt-error states are rejected. Canonical UUID4 nonces match reservation identity and cannot repeat across retained epochs. Evidence: trust-boundary analysis and signed inconsistency probes. Implementation: `build_receipt`, `verify_execution_record` and shared ledger validation. Verification: ATK-007, ATK-008 and review addendum fixtures.

False-positive analysis: Key rotation invalidates old signatures unless the original trusted public key remains available. Rotation is explicit; unavailable keys do not downgrade to HMAC or external assurance.

### D-098 (Category: Schema validation, Status: ACTIVE)
All evidence validators use strict typed schemas that reject boolean/string/integer confusion, empty structures satisfying vacuous checks, and justification strings bypassing numeric requirements. Evidence: trust-boundary analysis. Implementation: `expect_str` and `engine.schema`. Verification: ATK-012 fixtures.

False-positive analysis: Counts and booleans that look numeric may be serialized differently. Reject coercion and require a lossless adapter; text never overrides numeric science.

### D-099 (Category: Recursive plausibility, Status: ACTIVE)
Plausibility analysis recursively traverses all result containers (computed_runs, comparisons, derived_analyses) to detect zero p-values, below-chance metrics, and implausibly narrow CIs at any nesting depth. Evidence: trust-boundary analysis. Implementation: `_deep_result_findings`. Verification: ATK-013 fixtures.

False-positive analysis: Nested unrelated metadata may contain numbers resembling statistics. Only recognized fields are checked; typed schemas and metric definitions constrain interpretation, with excessive nesting rejected.

### D-100 (Category: Reproduction identity, Status: ACTIVE)
Reproductions must match the original's model identity, config digest, training mode, and runtime. Relabeling a different model as a reproduction is a hard provenance failure. Evidence: trust-boundary analysis. Implementation: `engine.audit.Audit.claims`. Verification: ATK-014 fixtures.

False-positive analysis: A reproduction can intentionally study a different model. Register it as a new experiment rather than relabeling it as an identity-preserving replay.

### D-101 (Category: Assurance level, Status: ACTIVE)
Audit reports and release certifications declare explicit machine-readable assurance levels with checkable prerequisites. Local assurance: STRUCTURALLY_VALIDATED. READY_FOR_HUMAN_SUBMISSION_REVIEW is the review-complete workflow status, with same-user/label/reviewer limits disclosed. Evidence: trust-boundary analysis. Implementation: `_assurance_with_review`. Verification: assurance level fixtures.

False-positive analysis: A cold review can be valuable even without external identity verification. Record mode and evidence while retaining structural local assurance; do not infer independence.

### D-102 (Category: Attack registry, Status: ACTIVE)
The attack registry maps each concrete invariant to a resolvable fixture and its actual scope. Release checks execute all registered fixtures and block missing, failed or skipped regressions. Known regressions do not prove every attack fails through the full lifecycle. Evidence: trust-boundary analysis. Implementation: `verify_attack_registry`. Verification: attack registry well-formedness and all 18 ATK fixtures.

False-positive analysis: A restricted environment can skip a fixture. Release checks treat skipped registered attacks as unverified; report environment limitations rather than counting them as passed.

These are qualitative risk analyses and regression controls, not measured per-rule false-positive rates. The historical rule base derives from limited incidents; no representative multi-project benchmark or general detection-rate claim has been established.

## Project publication

Follow `PUBLICATION_POLICY.md` for all project delivery. Stage project files explicitly, verify the staged content and outgoing history, keep internal evidence local, and review external PR/issue/release text before publication. Maintain scientific provenance and required credits while presenting project behavior and verification in professional language.
