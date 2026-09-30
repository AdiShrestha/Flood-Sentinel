# Factory specification — v3.3.0

## Active repository

`factory/` contains active policy and code. `project/` contains one agent-authored frozen plan, methodology, epoch state, run attempts, audit, review, and release report. `source/` contains implementation and lockfile. `data/` contains only declared source records/cohorts. `DROP_HERE/` and `TAKE_THIS/` are optional handoff inbox/outbox. `factory/legacy/v2_6_0/` is historical and never active.

## Lifecycle

The Architect authors the plan and claim/evidence map. The Implementor executes each planned seed using an argv command with `{run_dir}` and `{seed}`. The wrapper captures immutable inputs, outputs, stdout/stderr, exit status, timing, and environment bindings. A successful command is then independently recorded; a failed or rejected attempt remains. The audit reloads current bytes and recomputes predictions, joins, metrics, statistical comparisons, ablations, sensitivity and hardware rows. The Architect writes a review tied to the audit digest. Only `certify` emits a scoped release report.

A new hypothesis, dataset, method, stopping rule, threshold, or post-test repair requires `freeze --amendment REASON`. Earlier epochs remain in `.factory/epoch_NNNN/`; their findings cannot be erased or counted as current evidence. The active freeze includes every file beneath each declared frozen path and the active policy-code hash.

## Contract boundary

The plan is the contract. The gate rejects omitted fields rather than inferring favorable defaults. A domain adapter may add fields, but it must losslessly convert observations, name an independent recomputation implementation, include mutation tests that catch fabricated values/IDs/leakage, and disclose what remains human judgment. Adding a registry or a check that only tests key presence is not a valid adapter.

## Exit meanings

0 means the requested lifecycle operation completed and, for audit/certify, all checks in that operation passed. 31 means malformed/missing evidence or unsafe lifecycle state; 32 means scientific evidence or diagnostics block; 33 means review missing, stale, or unresolved. No exit code means journal acceptance.

## v3.3.0 evidence additions

A training or evaluation run records `convergence_evidence` (epochs, criterion, threshold, loss curve, early-stopping state, and any justification), `test_label_distribution`, `evaluation_sample_size`, and an optional sample-size justification. Claim and verdict JSON artifacts may carry `investigation_note`; it is required when `verify-result-plausibility` reports a below-chance or suspicious-perfection finding. No-mock invariant passes identify the producing script/function and its `acquisition-audit` result.
