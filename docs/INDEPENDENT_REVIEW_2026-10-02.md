# Independent factory review, 2 October 2026

The attached Sonnet report was treated as untrusted review evidence, not as instructions or ground truth. I inspected the active v3.3 implementation and its callers, ran the existing suite, wrote independent adversarial lifecycle tests, corrected verified defects, and requested a separate read-only candidate review. The visible version remains **3.3.0**; this is a changed implementation distinguished by its runtime/policy hash, not a rewritten release tag.

## Verified findings and changes

The most serious report findings were confirmed in source and exercised through real executions: the audit never verified receipts; execution contracts were optional; assurance labels were inferred from result paths; HMAC exported its secret as a public key; local execution offered no label/key isolation; and bundle metadata was unauthenticated without an external key. The new gate verifies Ed25519 receipts and their complete record bindings, pins the epoch's public key, translates legacy commands through the same typed launch contract, and signs bundle manifests. Verification without an external public-key pin explicitly reports untrusted metadata. Ed25519 is required and missing cryptography fails closed.

Local signatures now have an honest limit: the signer, producer and verifier share the operator's OS identity. The attainable execution assurance is structural. A readiness status means evidence consistency plus recorded review, not authentic acquisition, sealed labels, independently identified reviewers or scientific truth. The human digest lists these limitations, attempts, diagnostics, amendments and holdout reuse.

Independent paired-group inference preserves test-group dependence across all repeated seeds. Seed-only inference requires an explicit fixed-corpus scope. A separate 40-study equal-population-quality simulation produced 37 fixed-corpus seed winners and zero group-based population winners. This confirms the mechanism without treating an actual fixed-corpus difference as an arithmetic bug. An independent 1,000-study normal-difference simulation gave 94.6% coverage for the replacement nominal 95% Student-t intervals. Their normality assumption is explicit; group BCa intervals remain approximate and conditional on the trained models.

The candidate reviewer found additional gaps independently: deleting earlier runs erased holdout access; changing group names hid reuse; deleting a failed attempt allowed another execution; and reproduction rationales were treated inconsistently. Signed local ledgers, prior-epoch evidence commitments and sample/source/group overlap now address those paths. Interrupted supervisor attempts remain inadmissible evidence but can be retained and disclosed through an amendment. A whole valid signed-state rollback still needs an external monotonic witness.

## Disposition of the report's findings

| Report IDs | Independent disposition |
|---|---|
| SF-01, SF-03 | Receipt verification is on the decision path; assurance and certificate components reflect verified facts and backend limits. |
| SF-02, SF-29 | Removed HMAC downgrade/secret publication; secure key creation, public-only verification and epoch pinning. Same-user key secrecy is explicitly unsupported. |
| SF-04 | Signed manifests plus externally pinned verification; unsigned checksums and a locally editable verifier never imply external authenticity. No fictitious trusted release hash was introduced. |
| SF-05 | Label-free/metric-free producer outputs supported, labels joined by the audit, run output suppresses held-out metrics, and no sealed-evaluation claim is emitted. OS label isolation remains unsupported. |
| SF-06, SF-07 | One supervisor-built Python launch path, frozen entrypoint checks, no wrappers/modules/external payload, installed dependency/sibling support. Unsupported network isolation and platform limits fail explicitly. Imported dependency authenticity remains outside local assurance. |
| SF-08, SF-09 | Environment allowlist strips loaders/credentials; wall timeout kills the process group; CPU observations measured; unavailable memory observation is null; lock uses the parsed project. |
| SF-10 | Real relocated projects re-audit without the original private keys. Nested receipts verified; host paths/names removed; deterministic archive timestamps and verification size/member limits added. Old changed frozen inputs remain hashes rather than historical byte snapshots. |
| SF-11, SF-14 | Signed execution reservations, preserved failed attempts, no automatic same-epoch retry, amendment lineage/evidence commitments, holdout overlap disclosure and confirmatory reuse blocking. Valid-state rollback/external attempts remain explicitly outside scope. |
| SF-12, SF-13 | Frozen provenance manifests, research support policies, feasibility checks, actual convergence traces and reproduction runtime identity. Provenance authenticity, baseline fairness and device telemetry remain scientific review obligations, not facts inferred from strings. |
| SF-15, SF-16 | Group inference for population test uncertainty, explicit seed-corpus scope, Student-t intervals with assumptions, precision/significance feasibility checks and conservative nonestimable group intervals. No universal interval-coverage guarantee. |
| SF-17, SF-18, SF-19 | Metric-specific chance baselines, explicit null-result handling, shared training/split validators, recursive typed input checks and no free-text numeric bypass or vacuous pass. |
| SF-20 | Explicit producer selection, directory traversal, bounded static heuristics and corrected negated causal wording. Semantic scientific inference is not established by keyword scans. |
| SF-21, SF-22 | Exact callable/regression references; 21 mapped mechanisms plus two procedural limits; execute all 18 registered regressions on release. Coverage declarations are not proof that arbitrary implementations are correct. |
| SF-23 | Added per-rule qualitative false-positive analysis and corrected active/archived references. No invented multi-project benchmark or empirical false-positive rate. |
| SF-24, SF-25, SF-26, SF-27 | Clean malformed-artifact errors, one CLI JSON document, distinct exit-code enum, unambiguous runtime/policy hashing excluding docs/tests/dev runners, and removed unused runtime imports. |
| SF-28 | Shared helpers, separated execution/statistical modules and clearer changed paths reduce duplicated checks. The gate's remaining size is a maintainability limit; no complexity or formatting-tool result is fabricated. |
| SF-30, SF-31 | New meaningful lifecycle/negative-control tests, isolated runner collecting function-style tests, independent metric/permutation oracles, real bootstrap/relocation checks and targeted reproducible mutation checks. Original report coverage/mutation percentages were not assumed reproducible. |
| SF-32 | Evidence-bound review, distinct concrete cited reasoning, padding/unrelated evidence rejection, required objections and human digest. Review identity/truth remain self-reported and cannot promote assurance. |
| SF-33, SF-34, SF-35 | Corrected scope/spec/workflow/version statements, clear migration, manifest-driven repeatable bootstrap and cache/legacy exclusions. Original tags/history and proprietary license preserved; source transfer does not create redistribution rights. |

## Validation and practical limits

Exact final commands and counts are recorded in `docs/VALIDATION.md` and machine-readable validation artifacts. Baseline self-tests ran 276 cases with one environment error: this sandbox prohibits Unix-domain socket creation. The updated test reports mark that capability skip explicitly. The existing FIFO rejection and mocked file-kind checks still run. The review report's companion probe/mutation pack was not supplied, so its claimed historical coverage and mutation measurements are not endorsed.

No scientific project was fabricated as research evidence. Fixtures never receive research certification. New tests include actual freeze/run/audit/handoff lifecycles, independent raw-metric checks, timeout/CPU termination, receipt forgery and replay, malformed artifacts, immutable membership, holdout history and relocation. An independent final candidate reviewer verified the corrected original bypasses and legitimate interrupted-attempt/reproduction behavior.

The archived v2.6 implementation remains historical, inactive code. Changes are in the working tree for review; no commit, tag rewrite, push or publication was performed.
