# Assurance boundaries — v3.3.0

This implementation is a local evidence-consistency gate. It reports `STRUCTURALLY_VALIDATED`; `READY_FOR_HUMAN_SUBMISSION_REVIEW` means implemented checks and a recorded evidence-bound review passed. Neither status proves scientific truth, isolated execution or independent review identity.

## Actors and capabilities

| Actor | Assumed capability | Supported property | Limit |
| --- | --- | --- | --- |
| Project producer or agent | Writes project code, data, plans, results and review text; executes code under the supervisor's OS user | Detects inconsistency relative to the current frozen files, signed records and declared plan; recomputes metrics without importing project metric code | Producer can read labels and locate the signing key, run unreported experiments, fabricate acquisition/telemetry or modify the verifier |
| Local workspace owner | Controls engine, keys, Git config/hooks, snapshots and local state | Ordinary edits invalidate current bindings; missing/changed retained attempts and nonce reuse are rejected relative to the retained signed ledger | Owner can rewrite and sign a consistent fictional state, disable hooks, restore an earlier valid workspace or relabel data; no external monotonic witness exists |
| Reviewer | Supplies a model/session/mode declaration, evidence citations, objections and resolutions | Current cited bytes and audit digest must agree; stale, repetitive and incomplete reviews are rejected | Identity and scientific reasoning are self-reported; different models or fresh sessions are not authenticated independence |
| Handoff recipient | Verifies bounded archive bytes against a public key trusted through a separate channel | Signed manifest membership and metadata authenticate against that pin; altered/missing/extra archive bytes are rejected | An embedded key alone is untrusted. A verified archive does not establish acquisition truth or automatically re-run scientific audit |
| Public project viewer | Sees pushed Git objects and public project artifacts | Allowlisted content, reachable history, commit/ref/tag text and supported artifact bytes are checked by private local publication hooks | Hooks are owner-controlled; semantic leaks and GitHub PR/issues/releases or external uploads need separate review |

## Assets and trust boundaries

The plan, frozen source/data inventory, execution identity, prediction membership, recomputed results, amendment history, review digest and release/preflight bindings are checked for consistency. Execution nonces must be canonical UUID4 values, match signed reservations and remain unique across retained epochs. This prevents accidental duplication and detectable replay inside that recorded state; it does not prevent an owner from replacing the entire history.

The executable experiment and local signer share an OS identity and filesystem. Sanitized launch environment, typed argv, process timeouts and explicit supported resource limits reduce accidental drift and unsafe launch forms. They are not an OS sandbox. Python imports may read files outside frozen source; installed dependencies are recorded but not isolated or proven to match a lockfile. Network access is allowed only when explicitly declared unrestricted; denied-network contracts fail because this backend cannot enforce them. No claim of hidden test labels or protected private keys is supported.

Signed records bind bytes to a local key. Their checks cannot turn the key holder into an independent authority. Honest acquisition, genuine new holdouts, causal identification, population representativeness, training/operator semantics, real sensor telemetry and novelty remain human/domain responsibilities. Stronger execution or label-isolation claims require a separately provisioned external trust boundary, restricted data access and an independently trusted verifier; no such backend is shipped here.

## Evidence and its scope

Both certification commands execute fresh attack regressions, the declared mutation benchmark and matched synthetic fault/clean projects before research readiness. Certificates pin the engine, QA corpus and report bytes, and evidence/review are checked again after preflight. These are regressions for specified behavior, not proof against arbitrary same-user compromise.

The seeded benchmark uses 12 flaw families and three generated variants per family. Its 36 clean controls measure false rejections only for those constructed inputs. Label-peeking and false observational-origin cases are expected to remain undetected and are reported as limits. Exact per-family binomial intervals assume independent variants from that generator; three trials yield wide intervals. No pooled real-world detection rate, universal false-positive rate or representative usability study is claimed.

`run_statistical_simulations.py` describes conditional seed and group inference under declared null/unequal synthetic laws across sample sizes, recording raw outcomes and Monte Carlo uncertainty. It is an empirical description, not a release gate selected to force favorable results. Seed-based inference remains conditional on one test corpus; group inference is conditional on trained models and appropriate independent test groups. Other dependence, heavy tails, adaptive analysis, training variability and domain changes require additional scientific evaluation.

## Publication boundary

This repository distributes the engine itself, so its own source and documentation name it. Project repositories retain private engine/evidence/procedure files locally and publish project-focused code, scientifically relevant methods, limitations, reproduction instructions and required licenses/credits. The updated review's factory-worded paper boilerplate must not be copied into public project artifacts. Tool privacy never authorizes changing scientific results, omitting material methodological limitations or removing required attribution.
