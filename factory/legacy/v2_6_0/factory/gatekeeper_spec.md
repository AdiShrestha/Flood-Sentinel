# Gatekeeper Specification

Factory Version

2.6.0

---

# Implementation Status

This document describes the full, intended Gatekeeper. As of Factory v2.2.0, `factory/gatekeeper.py` implements a subset of it — not all of it. v2.2.0 forks from v1.4.2's two-role architecture (Architect, Implementor — no separate Auditor) rather than continuing the three-role, registry-heavy v1.5→v2.0→v2.1 line, and adds two genuinely new mechanisms motivated by that line's evidence-backed findings: `tier-check` (fail-closed minimum Scientific Claim Tier inference from a contract's own text, D-034, plus three bundled WARNING-only heuristics, D-035/D-036/D-037) and `release-certify` (an aggregate CERTIFIED/NOT CERTIFIED gate across an entire project, D-038). Everything from v1.4.2 (through its dated amendment) carries forward unchanged. v2.4.0 adds two further WARNING-only heuristics to the same `tier-check` bundle rather than a new command (C46) — ablation-row covariance (D-054) and efficiency-claim measurement language (D-055). v2.5.0 promotes D-054 and D-055 to ACTIVE, activates D-056 through D-061, and introduces deterministic mechanical gates for baseline parity verification, hardware profiling sufficiency, experiment freezing with seed-lottery verification, and foundation model benchmark contamination audits. v2.6.0 ratifies Constitution Section 11 (C65–C69), activates D-062 through D-073, and introduces deterministic mechanical gates for statistical protocol verification, sensitivity analysis verification, 10-step pre-submission audit, failure taxonomy verification, and extended claim-gated physical energy/thermal profiling. Claiming "Gatekeeper PASS" for a check this file doesn't yet run is itself a Constitution C01 violation (fabricated verification).

Currently implemented in `gatekeeper.py` (exit codes 3, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 0 — see Exit Codes):

- Frozen File Validation (hash comparison against a checked-in hash manifest) — `snapshot` for one contract, `snapshot-chunk` for every contract in a manifest at once (v1.1.2). As of v1.4.2, both automatically include a fixed path set (`source/tests/**`, `source/scripts/verify_*.py`, `factory/verifiers/**`) in addition to whatever `--frozen`/`frozen_files` declares, so a project's verification machinery is snapshotted without any contract needing to remember to list it — see `_auto_frozen_verification_paths`.
- Report Validation (required reports exist, required section headers present) — `check`'s `--manifest`-derived `required_reports` paths were fixed in v1.3.0: bare filenames now resolve against the standard `project/chunks/chunkNN/reports/{contract_id}/` location instead of the current working directory, which had been producing false missing-report failures.
- Repository Integrity (clean working tree, no unresolved merge markers) — as of v1.3.2, checks the outer repository *and* the nested `project/` repository independently, if one exists (see Project Repository Isolation). Either root being dirty fails the check, with the specific root named in the failure — this used to only ever see whichever repo happened to be the process's current directory.
- Execution-order lookup (v1.1.2) — `next` reads `execution_order` from `execution_manifest.yaml` and each contract's `contract_report.md` Final Status, and reports which contract is ready to run. This is a deterministic read of information the Architect already committed to the manifest at chunk-generation time, not a new dependency-resolution computation — Gatekeeper still performs no reasoning of its own.
- Dropbox Sort (v1.1.3, revised v1.2.0) — `sort-dropbox` files everything in `DROP_HERE/` to the destination `DROP_HERE/dropbox_manifest.json` declares, checking exact-filename `entries` first, then regex `rules`. Anything dropped that matches neither is left in place and reported, never moved by inference. See `factory_spec.md`'s Dropbox Specification.
- TAKE_THIS Staging / Clearing (v1.2.1) — `stage-takethis --chunk chunkNN` copies a completed chunk's self-contained reports into `TAKE_THIS/`, renamed flat; `clear-takethis` empties it. Both copy/delete operations only ever touch `TAKE_THIS/` itself. See `factory_spec.md`'s TAKE_THIS Specification.
- Materialize (v1.3.0) — `materialize --contract {{ID}}` deterministically extracts `<!-- MATERIALIZE: path --> `-tagged code blocks from a contract file and writes them to their declared destination, byte-for-byte. Closes the gap where turning embedded contract source into real files required manual transcription. See `factory_spec.md`'s Materialize Convention.
- Project Repository Commit (v1.3.2) — `commit-project` runs `git add -A && git commit` scoped entirely to `project/`'s own nested repository. Safe to call routinely; a no-op (not an error) when nothing changed. See `factory_spec.md`'s Project Repository Isolation.
- Self-Check (v1.3.4) — `self-check` is diagnostic only: diffs `gatekeeper.py`'s actual implemented subcommands and exit codes against this document's own Implementation Status and Exit Codes sections, cross-checks `factory_spec.md`'s Artifact Lifecycle table against operative instructions in `implementor_spec.md`/`architect_spec.md`, checks embedded version references across documents against `VERSION`, and lints worked-example contract IDs against the `^C\d{2}-\d{2}$` naming convention. Reports findings as prompts to investigate, not proven defects; never modifies any file; always exits 0. Evidence posture: unit-tested against synthetic drift scenarios, not yet run against a real project's document set beyond the audit that produced this release.
- Release Check (v1.4.0) — `release-check --manuscript {{path}} [--files ...] [--key-facts project/key_facts.md]` scans a release-bound artifact for two things before submission: an absolute local filesystem path (`/Users/`, `/home/`, `C:\Users\`) leaking into the artifact (hard FAIL, exit 10 — unambiguous, deterministic string matching), and a mismatch between a number found near a declared anchor phrase and the value declared for that anchor in `project/key_facts.md` (WARNING — heuristic, framed as requiring human confirmation, not a proven defect). The key-fact check is deliberately bounded: it only catches drift against facts the Architect declared *in advance*, never open-ended semantic fact-checking of prose, which would require AI reasoning Gatekeeper's own Purpose forbids. See `dynamic_rules.md` D-017 and `v1_4_0_scientific_validity_layer.md` Part 5. Evidence posture: unit-tested against synthetic fixtures reproducing the exact GLOF review findings (m6, M3) that motivated this command; not yet run against a real manuscript in production.
- Acquisition Audit (v1.4.0, broadened v1.4.2) — `acquisition-audit [--scripts ...] [--reports ...]` scans data-acquisition **and statistical-computation** scripts and their contract reports for three things before their output is trusted: a function definition matching `generate_`/`simulate_`/`synthesize_`/`fallback_`/`mock_`/`fake_` (hard FAIL, exit 11 — D-022); a distribution-sampled value (`.normal`/`.uniform`/`.randn`) feeding a metrics function (`roc_auc_score` etc.) in the same file (hard FAIL, same exit code — v1.4.2, D-028); and simulation-indicating language in prose (WARNING — heuristic, some matches are legitimate — D-023). Two real incidents motivate this command: Chunk 07 (an acquisition script defined `generate_fallback_timeseries`, called when the target API was unreachable, producing simulated data that passed every Reality Gate property check) and Chunk 08/C08-06 (a bootstrap-CI script read only an already-aggregated scalar AUC from a summary JSON and fabricated per-window scores via `rng.normal(...)` shaped to approximate it, then bootstrapped and significance-tested the fabricated values — reproduced byte-for-byte against the real shipped artifact before this check was written). Catches the common case, not a deliberately obfuscated one — see `dynamic_rules.md` D-022, D-023, D-028 and Constitution C01, C54. Evidence posture: the two original checks are unit-tested against a synthetic reproduction of Chunk 07; the v1.4.2 addition is unit-tested against both a distilled fixture and the real C08-06 script. None has been run against a pipeline beyond the one that motivated it.
- Evidence Check (v1.4.1) — `evidence-check --reports {{path}} [...]` reads a contract report's structured `## Verdict Cross-Check` block and cross-checks it against the JSON artifact it names: does the report's declared `verdict_word` match the artifact's own value at `artifact_key` (hard FAIL, exit 12 — D-024), and, if a bounded criterion is declared (`count_gte`/`count_lte`/`value_gte`/`value_lte`/`bool_true`/`bool_false`, never a free-form expression), does the artifact's own number actually entail the stated verdict (hard FAIL, same exit code — D-025). Separately flags any metric in the artifact's `metrics` array sitting on a degenerate boundary (0.0/0.5/1.0 within tolerance) computed on fewer than 30 samples (WARNING — D-027, SVI-007). A report with no Verdict Cross-Check block is not checked at all, not silently passed. Motivated by a real incident (Chunks 08-09, GLOF project rework): a contract report claimed `SUCCESS` while its own backing artifact recorded `FAILURE`, and separately claimed `SUCCESS` while its own reported count (0 windows flagged) satisfied the pre-registered FAILURE criterion. See `dynamic_rules.md` D-024, D-025, D-027. Evidence posture: unit-tested against a synthetic reproduction of the Chunks 08-09 incident; not yet run against a real project beyond the one that motivated it.
- **Verify Contract (v1.4.2, new)** — `verify-contract --reports {{path}} [...]` re-executes, for real, every command a contract report declares under its own `## Verification` section (any `**...Command...**: `` `cmd` `` ` bullet — the format reports already use, not a new schema), and checks the actual exit code (hard FAIL, exit 13, if nonzero). The report's own claimed result (e.g. "236/236 passed") is read as a human cross-reference only, never trusted as the verification itself. Reuses each command's declared invocation rather than requiring a duplicate declaration. Only declare read-only/idempotent verification commands — a command with side effects will have those side effects again.
- **Lint Contract (v1.4.2, new)** — `lint-contract [--scripts ...] [--contract ...]` runs a deterministic AST scan (Python's own `ast` module, stdlib — no new dependency) for swallowed exceptions: an `except` handler with neither a `raise` nor a recognizable logging/warning call is a hard FAIL (exit 14), since silently continuing after a real failure is indistinguishable from silently substituting a fallback (C01, C54, D-028). A `# GATEKEEPER-EXEMPT: <reason>` comment inside the handler downgrades a specific instance to a warning, visible in the diff, never a silent pass. Also runs `acquisition-audit`'s fabrication scan against the same scripts, and, if `--contract` is given, checks the auto-frozen verification-machinery paths against that contract's snapshot (hard FAIL if tampered). This is a syntactic check, not a semantic one — see this section's Honesty About Scope note in the module docstring; it cannot tell a genuinely necessary broad `except` from a hidden one on its own, which is exactly why the exemption escape exists rather than an unconditional ban.
- **Recompute (v1.4.2, new)** — `recompute --reports {{path}} [...]` reads a report's `## Recompute Declaration` block (`original_script`, `independent_script`, `artifact`, `artifact_key`, `independent_command`, `independent_output_key`, `tolerance`) and, if present, actually runs `independent_command` and compares its output to the artifact's claimed value (hard FAIL, exit 15, on mismatch). Independence is checked mechanically, not merely asserted: if `independent_script`'s SHA-256 hash equals `original_script`'s, that is reported as a hard FAIL in its own right ("duplication, not independent verification (C11)"), since two copies of the same bug agreeing proves nothing. Honesty about scope: this proves two *different* programs agree, which is real evidence — it is not proof either program is correct.
- **Stamp Report / Verify Stamps (v1.4.2, new)** — `stamp-report --report {{path}} [--contract ...]` appends a tamper-evident `## Gatekeeper Verification Stamp #N` section to a contract report containing the real results of the three checks above (verify-contract's re-executed commands, lint-contract's findings, recompute's result if declared), plus `git diff --name-only` and frozen-file status. The stamp embeds a SHA-256 hash of every byte of the report that precedes it. Any later modification to content above a stamp is detected the next time the report is stamped or checked via `verify-stamps` (hard FAIL, exit 16) — the exact hash mismatch is reported, not merely "something changed." Amendments belong in a new section below the last stamp, never as an edit above one; a clean amendment can itself be stamped again, producing stamp #2, #3, etc., each committing to everything before it including all earlier stamps. Stamping is opt-in per report — an unstamped report is never retroactively required to have one (Backward Compatibility); `verify-stamps` on a report with zero stamps always passes.
- **Mandatory Mechanical Gate (v1.4.2, dated amendment — D-032/D-033)** — the four guards above were built as standalone, separately-invoked subcommands; a second-round independent review of v1.4.2 confirmed they work but found none of them were mandatory in the normal Implementor workflow (`implementor_spec.md`'s Phase 3 still only calls `check`, and never references `verify-contract`/`lint-contract`/`recompute`/`stamp-report` by name). `check --manifest {{path}} --contract {{ID}} --reports {{path}}` now reads the manifest contract's `scientific_claim_tier` field (reused unmodified from the existing v1.4.0 field — see `factory_spec.md`'s Scientific Claim Tier — not a new taxonomy) and, when it is `T-COMP` or `T-CAUSAL`, mechanically requires all of the following before the contract can read PASS: (1) every command in the contract's `required_verification_commands` field is present among the report's own declared `## Verification` commands (D-033 — closes the separate, previously-disclosed gap that `verify-contract` alone only proves *a* declared command exited 0, never that it was the *specific* command the contract required); (2) `verify-contract`'s re-execution of every declared command passes; (3) `lint-contract`'s scan passes; (4) the report declares a well-formed `## Recompute Declaration` block and it passes (a *missing* block is a hard FAIL under this gate specifically — unlike the standalone `recompute` subcommand, where no block is simply not checked); (5) the report carries at least one intact `## Gatekeeper Verification Stamp`. Any failure among the five sets exit 17 and is reported by name in the `[Mandatory Mechanical Gate]` section, distinguishing which sub-check failed. `check` never appends a stamp itself — `stamp-report` remains a separate, explicit step the Implementor runs beforehand. A T-DESC contract, or a contract with no `scientific_claim_tier` declared at all, is unaffected — the gate section is printed as `SKIPPED`, not silently omitted. See `dynamic_rules.md` D-032, D-033 and `CHANGELOG.md`'s dated amendment to the v1.4.2 entry. Evidence posture: unit-tested (`test_gatekeeper_v1_4_2_mandatory_gate.py`) against synthetic reproductions of both the "declares a trivially-passing substitute command" evasion and the "otherwise-complete report with the Recompute Declaration or stamp simply omitted" gap the originating review raised; not yet run against a real T-COMP/T-CAUSAL contract in production.
- **Tier Check (v2.2.0, new — D-034/D-035/D-036/D-037; v2.4.0, +D-054/D-055 candidate; v2.5.0 ACTIVE)** — `tier-check --contract {{ID}} [--declared-tier ...] [--reports ...]` mechanically infers a *minimum* `scientific_claim_tier` from a contract's own text (STRONG signals — named statistical tests/effect sizes, p-value/CI notation, "outperforms," SUPPORTED/FALSIFIED language — infer `T-COMP`; a distinct STRONG signal set for robustness/causal/ablation language infers `T-CAUSAL`; a WEAK signal alone — a bare metric name — infers `T-DESC`; no signal infers `NONE`) and hard-fails (exit 18) if the declared tier reads weaker than that inferred minimum. Also wired unconditionally into `check`, alongside the Mandatory Mechanical Gate, so a mis-declared tier is caught even when nothing else about the contract would have triggered T-COMP/T-CAUSAL machinery. Bundles five heuristics: operation-class conflation (D-035), statistical-protocol language (D-036), semantic/operator-test presence (D-037), ablation-row covariance (D-054, promoted to ACTIVE in v2.5.0), and efficiency-claim measurement language (D-055, promoted to ACTIVE in v2.5.0).
- **Release Certify (v2.2.0, new — D-038)** — `release-certify --chunks-dir project/chunks [--manuscript ... --key-facts ... --scripts ...]` aggregates, across every contract report under the given directory, Final Status/evidence-check/recompute/tier-check consistency, plus optionally acquisition-audit and release-check, into one CERTIFIED/NOT CERTIFIED verdict (exit 19 on NOT CERTIFIED), writing `project/RELEASE_CERTIFICATION.md` unconditionally and naming exactly which categories were actually run. Distinct from, and never satisfied merely by, a chunk-level Gatekeeper PASS — see `factory_spec.md`'s Release Certification section and Constitution C59. Evidence posture: unit-tested for the no-reports, all-COMPLETE, single-FLAGGED-contract, and single-under-tiered-contract cases (`test_gatekeeper_v2_2_0.py`); not yet run against a full real project. v2.3.0 additions: (a) before regenerating, prints a staleness comparison against any existing certificate (D-053); (b) a contract report explicitly marked `Superseded-By: {{contract_id}}` is excluded from the active COMPLETE check and reported separately under Historical Findings instead of blocking certification (D-050); (c) `--manuscript`'s scan now also runs the outbound Factory-identifier scan (D-049, see below) alongside the pre-existing local-path scan.
- **Release Status (v2.3.0, new — D-053)** — `release-status [--chunks-dir project/chunks]` reports whether the existing `project/RELEASE_CERTIFICATION.md` is still CERTIFIED and current (no report file changed since it was generated), WITHOUT re-running the full release-certify battery (exit 0 if fresh-and-certified, exit 19 otherwise, including "no certificate exists yet"). Exists for one specific, reported use case: the same underlying model, asked "is this ready" in a brand-new session with no memory of the chunk-by-chunk conversation that produced an earlier verbal claim of readiness, gave a materially different (and, on inspection, more accurate) answer than the original session had — because "is it ready" was being decided by re-asking an LLM's holistic opinion in two different contexts rather than by re-deriving the same deterministic answer. See Constitution C05 (AI opinion is never verification) and C59 (a certificate names exactly what it checked); see `architect_spec.md`/`implementor_spec.md`'s "Answering 'is this ready'" section for the process rule this command exists to make checkable rather than aspirational. Evidence posture: unit-tested against synthetic fresh/stale/missing-certificate fixtures; not yet exercised across the specific cross-tool, cross-session scenario that motivated it.
- **Contract Preflight (v2.3.0, new — D-039/D-040/D-044/D-047)** — `contract-preflight --contract {{ID}} --manifest {{path}} [--acquisition-scripts ... --readonly-verification --executor ...]` reconciles a contract's declared scope against reality BEFORE implementation begins: expands any glob among the contract's own `verification_scripts` (plus anything passed via `--acquisition-scripts`) against the real filesystem and flags any *currently-existing* matched file outside `allowed_files ∪ frozen_files` as a hard FAIL (exit 3 — Manifest Failure, reserved since v1.0 and never emitted until this release; downgradeable to a WARNING with `--readonly-verification` once confirmed the matched command only reads, never modifies, those files); flags any path appearing in both `allowed_files` and `frozen_files` as a direct contradiction; flags a `dependencies` entry with no matching contract `id` in the same manifest; and, if the manifest's `repository_preconditions.previous_chunk_approved` is `true`, confirms the immediately preceding chunk's own `chunk_report.md` actually contains the word APPROVED (D-047 — this field has been in the Execution Manifest Schema since it was written and was never mechanically enforced before this release). Separately, if a High-risk contract's `implementation_owner` does not match its actual executor (passed via `--executor`, or the contract's own `executor` field), requires an active, matching `delegate` record or hard-fails with exit 21 (Delegation Violation — D-044). Motivated directly by a real incident: a wildcard `acquisition-audit --scripts` argument matched more legacy modules than a contract's `allowed_files` permitted modifying, discovered mid-contract rather than at intake, during exactly the highest-risk work in a chunk. Run automatically as the first step of `begin` (below); available standalone. Evidence posture: unit-tested against synthetic overlap/wildcard-reach/missing-dependency/missing-precondition/missing-delegation fixtures reproducing each reported shape; not yet run against a real project's full manifest set.
- **Begin / Finalize (v2.3.0, new — D-041, D-046, D-048; see Constitution C61)** — `begin --contract {{ID}} --manifest {{path}}` and `finalize --contract {{ID}} --manifest {{path}}` collapse the previously five-command, by-hand-in-the-right-order ceremony (snapshot, do the work, check, verify-contract/lint-contract/recompute/stamp-report, append telemetry, append a decision, commit-project — reported as roughly 35% of total time on a 65-contract project) into two lifecycle commands that read the manifest instead of requiring any of it retyped. `begin` runs `contract-preflight`, snapshots this contract's `frozen_files` merged with the same auto-frozen verification paths `snapshot`/`snapshot-chunk` already include, captures a scoped repository baseline (git status at this exact moment, D-041), and writes a report skeleton with every required section header already present (D-046, using the corrected `DEFAULT_REQUIRED_SECTIONS` — see that constant's own comment in `gatekeeper.py` for the drift this replaces) at the manifest-implied report path, if one doesn't exist yet. `finalize` is a **transactional complete-contract**: it re-runs `check` (and, for T-COMP/T-CAUSAL contracts, the Mandatory Mechanical Gate `check` already performs) for real, against the report's *current* content, right now — and writes a completion receipt (`project/.gatekeeper/state/{{contract_id}}.complete.json`, containing a SHA-256 of the report's exact content at that instant plus outer/nested HEAD) **only if** that re-run actually passes **and** the report's own Final Status already reads a COMPLETE-class value (exit 20, Finalize Integrity Failure, otherwise — nothing is written on a failed attempt). This does not replace `parse_contract_status`/`next`'s existing Markdown-based logic; it adds one cross-check on top of it, for anyone who chooses to consult the receipt: a report whose current content-hash no longer matches what its own receipt recorded has changed since it was last actually certified, whatever its Final Status heading currently says. Motivated directly by a real incident: a false `contract_complete` telemetry event and a COMPLETE-status report both existed for a contract whose own Report Validation gate would have failed, had anyone re-run `check` at that exact moment — completion had been claimed, but never transactionally earned. `finalize` also replaces `--allow-dirty`'s blanket bypass with a scoped delta, when a baseline exists (from `begin`): pre-existing dirty files are left alone, files this contract legitimately changed inside `allowed_files` are accepted, and only files changed during this contract *and* outside `allowed_files` block anything (`project/` itself is always excluded from this comparison by construction, per Constitution C60, regardless of a given environment's `.gitignore` state) — a contract not started with `begin` falls back to `check`'s original, unmodified `--allow-dirty` behavior exactly as before. `finalize` auto-populates `self_review_attempts` on its `contract_complete` telemetry event from how many times `finalize` itself was invoked against this contract before it passed (previously reported as hand-typed `1` regardless of actual attempt count, across all 65 contracts of a real project); `violations` is left `[]` deliberately (an honest placeholder, not a fabricated one — see `gatekeeper.py`'s own note beside this field) pending a future release actually wiring it to `check`'s structured findings. Also optionally appends a `decision_log.md` entry (`--decision`) and calls `commit-project` (skip with `--no-commit`); a `commit-project` failure (e.g. no nested repository yet) is reported as a warning, since the receipt/telemetry/decision above are the real completion artifacts and are not undone by it. Evidence posture: unit-tested end-to-end (a synthetic contract carried through `begin` → work → `finalize`, including a deliberate scope violation and a deliberate incomplete-report case) and exercised manually against a live synthetic project during development; not yet run against a real research project.
- **Delegate (v2.3.0, new — D-044; see Constitution C55's delegation note)** — `delegate --chunk {{name}} --original-owner {{architect|implementor}} --executor {{architect|implementor}} --contracts {{ID}} [{{ID}} ...] --authorized-by {{text}}` records a Human-authorized, chunk-scoped, non-precedent-setting exception to the Implementation Owner table, appended to `project/.gatekeeper/delegations.jsonl`. Motivated directly by a real, explicitly Human-authorized incident: the Architect was genuinely unreachable for one chunk, and the Human explicitly directed the Implementor to execute five specific Architect-owned High-risk contracts for that chunk only. This command does not evaluate whether the exception was *warranted* — per Constitution C31, Gatekeeper does not evaluate the wisdom of a Human decision, only whether one was actually given — it only gives an already-given plain-language authorization a structured, checkable record `contract-preflight`/`begin` can verify against, instead of leaving it as conversational context with nothing to check it against. A delegation is scoped to the declared chunk and contract list only, always flags `requires_later_independent_review: true`, and is never treated as precedent for any later chunk. Evidence posture: unit-tested against synthetic matching/non-matching/expired-scope fixtures; not yet exercised on a real Architect-outage chunk under this exact command (the incident that motivated it predates this command's existence and was handled by ad hoc documentation instead).
- **Log Decision (v2.3.0, new — D-048)** — `log-decision --role {{architect|implementor}} --decision {{text}} --reason {{text}} --benefit {{text}} [--title ... --alternatives ... --traces ...]` appends one entry to both `project/evolution/decisions.jsonl` (structured, auto-incrementing `D-{n}`, computed by scanning existing entries rather than requiring the caller to know the current maximum) and `project/evolution/decision_log.md` (rendered, matching that document's existing four-field schema exactly: decision / reason / alternatives / expected benefit). Always appends at the end of `decision_log.md` — never searches for or inserts before any anchor or register section elsewhere in the file, since `decision_log.md`'s own specification has always said append only; a per-project convention requiring insert-before-anchor instead is exactly what made hand-editing a multi-thousand-line decision log expensive to do by hand on a real, reported project. Evidence posture: unit-tested for auto-incrementing IDs across zero, one, and many existing entries, and for both files staying in sync; not yet exercised on a real multi-thousand-entry decision log.
- **Outbound Secrecy Scan (v2.3.0, folded into `release-check`/`release-certify` — D-049)** — the Release Artifact Scan category (both commands) now also scans for Factory-internal identifiers — contract/chunk/decision IDs, `TAKE_THIS`/`DROP_HERE`, `gatekeeper.py`, `project/.gatekeeper`, labeled Architect/Implementor role language, `RELEASE_CERTIFICATION.md` — leaking into a release-bound artifact (hard FAIL, same exit codes as the existing local-path scan: 10 for `release-check`, folded into 19 for `release-certify`). This is the same Project Repository Isolation goal `factory_spec.md` already states ("no visible trace... that a project was built using this Factory"), extended from local-path leaks to this second, textual kind of fingerprint. Deliberately narrow, shape-based patterns rather than a generic word blocklist — bare "Architect"/"Implementor" usage in ordinary architecture/software-implementation prose is not flagged; only role-labeled constructions are ("as the Architect," "the Implementor's"). Evidence posture: unit-tested against synthetic leak fixtures for each pattern category; not yet run against a real manuscript.
- **Verify Baseline Parity (v2.5.0, new — MAR-2, D-059)** — `verify-baseline-parity [--venue-requirements <path>] [--contract-report <path>]` parses the Baseline Parity Ledger and enforces parameter parity ($\pm 2\%$), compute FLOPs parity ($\pm 5\%$), and tuning parity. Fails with exit 23 if parameters or compute diverge without formal justification.
- **Verify Hardware Profile (v2.5.0, extended v2.6.0 — MAR-8, D-056, D-068, D-069)** — `verify-hardware-profile --manifest <path>` parses `hardware_profile_manifest.json` for efficiency or speedup claims. Validates positive latency distributions ($p50, p90, p99$), peak training and inference memory tracking, and explicit exclusion of warmup iterations. In v2.6.0, if efficiency keywords ("efficient", "green", "carbon", "joules") are present in claims, mechanically enforces physical energy consumption (`joules_per_inference`, `wh_per_run`), thermal headroom (`thermal_headroom_celsius`), and FLOPs accounting. Fails with exit 24 if incomplete.
- **Freeze Experiment / Verify Experiment Freeze (v2.5.0, new — MAR-7, C63, D-060)** — `freeze-experiment [--manifest <path>] [--out <path>]` creates a pre-registration manifest locking git commit, environment hash, dataset checksums, and evaluation seeds. `verify-experiment-freeze --freeze-manifest <path> --report <path>` audits contract reports to ensure every pre-registered seed was executed without omission, post-hoc substitution, or cherry-picking. Fails with exit 25 on mismatch.
- **Contamination Check (v2.5.0, new — MAR-6, D-061)** — `contamination-check [--benchmark <path>] [--training-corpus <path>] [--audit-json <path>]` audits evaluation splits for 13-gram overlap with training corpora and verifies temporal cutoff validity. Fails with exit 26 on contamination.
- **Verify Statistical Protocol (v2.6.0, new — C65/C66, D-062/D-063/D-064)** — `verify-statistical-protocol --reports <path>...` parses contract reports and Section 8 of `venue_requirements.md`. Enforces explicit declaration of primary significance tests (paired t-test, Wilcoxon, Friedman/Nemenyi), multiple comparisons correction (Holm, Bonferroni, Benjamini-Hochberg FDR), effect size reporting alongside every p-value, and small-N aggregation strategy (Agarwal et al. IQM with stratified bootstrap CI). Fails with exit 27 on violation.
- **Verify Sensitivity Analysis (v2.6.0, new — D-065)** — `verify-sensitivity-analysis --reports <path>...` audits hyperparameter sensitivity analysis across perturbation grids ($\pm 10\%, \pm 25\%, \pm 50\%$), verifying baseline values, perturbed evaluations, and explicit documentation of degradation failure points. Fails with exit 28 on missing or incomplete sensitivity sweeps.
- **Pre-Submission Audit (v2.6.0, new — D-070)** — `pre-submission-audit --reports <path>...` enforces a 10-step adversarial pre-submission audit protocol (Cold-read triage, Claims-evidence matrix, Statistical audit, Baseline audit, Ablation completeness, Generalization/failure audit, Hardware/efficiency audit, Reproducibility checklist, Adversarial rebuttal rehearsal, Mock meta-review). Steps 1–4 are validity-critical (hard FAIL, exit 29); steps 5–10 issue structured warnings.
- **Verify Failure Taxonomy (v2.6.0, new — C69, D-071)** — `verify-failure-taxonomy --reports <path>...` validates that empirical robustness and generalization claims characterize failure modes with explicit mechanism categories, conditional prevalence $P(\text{failure} \mid \text{condition})$, severity ratings (`SEV-1` through `SEV-4`), error confidence scores, and documented example selection rules. Fails with exit 30 on missing or uncalibrated failure analysis.

Not yet implemented (still AI-attested only, pending future contracts to build them): Bootstrap Validation, Manifest Validation (now partially addressed for scope/dependency/precondition conflicts specifically by `contract-preflight`, D-039/D-040/D-047 — full schema-shape validation of an `execution_manifest.yaml` remains unaddressed), Contract Validation, **Allowed File Validation** (a contract's diff touching only its declared files — `finalize`'s scoped repository delta, D-041, addresses this for a contract that was started with `begin`, but nothing checks it independently of that lifecycle, and a contract not using `begin` gets no coverage at all), Dynamic Rule Validation, Bootstrap Compliance, Git Validation beyond a clean-tree check (or, for a `begin`-started contract, a scoped delta). Verification Script Validation is now fully addressed for T-COMP/T-CAUSAL contracts by the Mandatory Mechanical Gate above (D-033 closes the "right command" gap this section previously flagged as open); for T-DESC contracts and contracts with no declared tier, `verify-contract`/`stamp-report` remain available but optional, and the original caveat still applies to those: neither verifies a script's declared command matches what `implementor_spec.md` required, only that the declared command really ran and really passed.

Also not yet implemented, new to v1.4.0's scope: **Reality Gate**. Reality Gate's four checks (gap statistics, distribution/uniformity, temporal coverage, sensor coverage) plus the provenance-chain requirement (D-014, sharpened) are fully deterministic *in principle*, but automating them requires a standardized `project/data_manifest.json` schema that has not yet been built and exercised against a real project's data pipeline — a concrete design exists (see the Scientific Validity Specification) but claiming it as implemented before it's built would itself be a C01 violation. In v2.6.0, MAR gates 1, 2, 3, 6, 7, 8 now feature mechanical verification tools (`verify-baseline-parity`, `verify-hardware-profile`, `freeze-experiment`, `verify-experiment-freeze`, `contamination-check`, `verify-statistical-protocol`, `verify-sensitivity-analysis`, `pre-submission-audit`, `verify-failure-taxonomy`), while Gates 4-5 (Title-Claim Consistency, Venue Alignment) require genuine adversarial review — for peer-reviewed publication venues, conducted across model boundaries (e.g. Claude Opus/Sonnet vs. Gemini Pro/Flash) rather than same-session self-review.

`gatekeeper.py` prints which checks it actually ran in its output — the Implementor and Architect should both quote that list rather than the full checklist below when reporting a Gatekeeper result, per C02.

---

# Purpose

Gatekeeper is the Factory's deterministic enforcement engine.

Its purpose is to verify that every completed contract satisfies all deterministic requirements before work is accepted.

Gatekeeper never performs AI reasoning.

Gatekeeper never evaluates software quality.

Gatekeeper only determines whether predefined, objective conditions are satisfied.

---

# Philosophy

The Factory prefers deterministic verification over AI judgement whenever possible.

Every responsibility moved from AI reasoning into Gatekeeper reduces future ambiguity.

Gatekeeper is the final automated checkpoint before work is considered complete.

---

# Responsibilities

Gatekeeper is responsible for

- repository validation
- artifact validation
- execution validation
- integrity verification
- deterministic rule enforcement
- contract completion verification

Gatekeeper is not responsible for

- code review
- architecture review
- design decisions
- implementation quality
- research evaluation
- writing reports
- generating fixes

---

# Inputs

Gatekeeper reads

```
bootstrap_manifest.yaml

execution_manifest.yaml

contract_report.md

chunk_report.md

verification scripts

repository state

git metadata

DROP_HERE/dropbox_manifest.json  (v1.1.3 -- sort-dropbox only)

manuscript / release artifact text, project/key_facts.md  (v1.4.0 -- release-check only)
```

Only deterministic artifacts are consumed.

`constitution.md`, `factory_spec.md`, and `dynamic_rules.md` are not read by
`gatekeeper.py` itself (v1.3.4 correction -- they were previously listed
here but the script never opens them). They are read by the Architect and
the Human as part of the judgement-based portions of the Factory's
process; Gatekeeper's own scope is limited to the deterministic artifacts
listed above.

---

# Outputs

Gatekeeper produces

```
PASS
```

or

```
FAIL
```

as a printed console result and process exit code.

As of Factory v1.3.4, `gatekeeper.py` writes no report file -- everything
below is printed to stdout only, not persisted to disk. This gap was
previously undisclosed even in the Implementation Status "not yet
implemented" list; it is now listed there too. A `gatekeeper_report.md`
file generated to disk remains a documented target for a future
contract, containing

- executed checks
- passed checks
- failed checks
- warnings
- execution time
- Factory version
- repository state

---

# Execution Order

Gatekeeper always executes in the same order.

```
Bootstrap Validation

↓

Repository Validation

↓

Manifest Validation

↓

Artifact Validation

↓

Verification Scripts

↓

Report Validation

↓

Dynamic Rule Validation

↓

Repository Integrity

↓

Final Decision
```

Execution order is fixed.

---

# Bootstrap Validation

Verify

- bootstrap_manifest.yaml exists
- manifest is valid
- required directories exist
- required files exist

Failure

↓

STOP

---

# Repository Validation

Verify

- repository is initialized
- required directories exist
- required project files exist
- chunk structure is valid

Missing artifacts

↓

FAIL

---

# Manifest Validation

Verify

- execution_manifest.yaml exists
- dependency order valid
- required contracts listed
- verification scripts declared
- reports declared

Invalid manifest

↓

FAIL

---

# Contract Validation

Verify

- contract exists
- contract completed
- Definition of Done satisfied
- Stop Condition not violated

Failure

↓

FAIL

---

# Frozen File Validation

Verify

- every frozen file hash matches
- no unauthorized modification occurred

Hash mismatch

↓

FAIL

---

# Allowed File Validation

Verify

Only Allowed Files were modified.

Unexpected modification

↓

FAIL

---

# Verification Script Validation

Verify

- required verification scripts exist
- scripts executed successfully
- exit code equals zero

Non-zero exit code

↓

FAIL

---

# Report Validation

Verify

Required reports exist.

Required sections exist.

Mandatory evidence exists.

Missing report

↓

FAIL

---

# Dynamic Rule Validation

Verify

Every ACTIVE Dynamic Rule that can be checked deterministically.

Examples

- required files exist
- provenance recorded
- required reports generated
- frozen hashes verified

Rules requiring judgement are skipped.

## Constitution Rule Validation (planned)

Now that every Constitution rule (C01–C50) carries an Enforcement Level, Gatekeeper can eventually check the mechanically-checkable subset of Level A rules directly (for example: C24 secrets-in-repo via a secret-scan, C23's forbidden git operations via reflog inspection) instead of relying only on the Implementor's Phase 3 self-attestation. This is not implemented in `gatekeeper.py` yet — listed here as the natural next Gatekeeper contract, following the same Observation → Dynamic Rule → Gatekeeper Check → Automatic Enforcement path this document's Design Philosophy already describes.

<!-- Possible v1.3.5 candidate (not yet proposed -- see dynamic_rules.md's Candidate Observations
     table, "Possible v1.3.5 candidates" §3, for full grounding/critique/evidence-status): a
     concrete design for exactly this already exists --
     Automated Risk-Surface Scan, driven by a new Contract Specification field
     (`Risk Surface Scan Required`, see factory_spec.md's Contract Specification section). It
     would add a new Gatekeeper check category here alongside Frozen File and Report Validation:
     presence and pass/fail of the declared scan, nothing judgmental. Gated on completing at least
     one more real project first, per that document's own §4. -->

---

# Repository Integrity

Verify

- clean working tree
- no merge conflicts
- no unresolved files
- no temporary artifacts
- no forbidden files

Failure

↓

FAIL

---

# Bootstrap Compliance

Verify repository matches

```
bootstrap_manifest.yaml
```

Missing required artifact

↓

FAIL

Unexpected files

↓

WARNING

Unknown files are never deleted automatically.

---

# Git Validation

Verify

- repository clean
- commit possible
- required tag exists if specified
- current commit recorded

History is never rewritten.

Gatekeeper's git operations (v1.3.4 correction) are scoped entirely to
`project/`'s own nested repository (`commit-project`, v1.3.2) and never
touch the outer repository. `sort-dropbox`, `stage-takethis`,
`clear-takethis`, and `materialize` move, copy, or write files but are not
git operations themselves. Gatekeeper never rewrites history in either
repository, and never performs any git operation against the outer
repository at all.

---

# Verification Principles

Gatekeeper verifies only facts.

Never interpretations.

Examples

Allowed

```
File exists

Exit code equals zero

Hash matches

Report exists

Directory exists
```

Forbidden

```
Architecture is good

Research is correct

Code looks clean

Algorithm is elegant
```

---

# Failure Policy

Any FAILED check blocks completion.

Gatekeeper never ignores failures.

No partial pass exists.

---

# Warning Policy

Warnings indicate

- non-critical inconsistencies
- unexpected artifacts
- deprecated structures
- obsolete reports

Warnings never override failures.

---

# Exit Codes

```
0

PASS
```

```
1

Bootstrap Failure
```

```
2

Repository Failure
```

```
3

Manifest Failure
```

v2.3.0: this code, reserved since v1.0 but never emitted, is now implemented — `contract-preflight` uses it for a scope/dependency/manifest-precondition conflict (D-039/D-040/D-047). See Implementation Status.

```
4

Contract Failure
```

```
5

Verification Failure
```

```
6

Report Failure
```

```
7

Dynamic Rule Failure
```

```
8

Repository Integrity Failure
```

```
9

Unexpected Internal Error
```

```
10

Release Artifact Failure
```

```
11

Acquisition Audit Failure
```

```
12

Evidence Inconsistency
```

```
13

Verification Execution Failure
```

```
14

Contract Lint Failure
```

```
15

Recompute Mismatch
```

```
16

Report Stamp Tampering
```

```
17

Mandatory Mechanical Gate Failure
```

```
18

Fail-Closed Tier Inference Failure
```

```
19

Release Certification Failure
```

```
20

Finalize Integrity Failure
```

v2.3.0 (D-041; see Constitution C61) — `finalize`'s own re-run of `check` (or the Mandatory Mechanical Gate, if tiered) did not pass against the report's current content, or a scoped repository delta found an unexpected out-of-scope change. No completion receipt, telemetry, or decision-log entry is written when this fires.

```
21

Delegation Violation
```

v2.3.0 (D-044) — a High-risk contract's `implementation_owner` does not match its actual executor, and no active, matching, unexpired `delegate` record authorizes the difference.

```
22

Outbound Secrecy Scan Failure
```

v2.3.0 (D-049) — a release-bound artifact scanned by `release-check` contains a Factory-internal identifier (chunk/contract/decision ID, `TAKE_THIS`/`DROP_HERE`, Gatekeeper/role-name language). Folded into exit 19 when found via `release-certify` instead.

```
23

Baseline Parity Violation
```

v2.5.0 (MAR-2, D-059) — `verify-baseline-parity` detected comparative baseline parameter counts exceeding $\pm 2\%$ tolerance, training FLOPs/compute exceeding $\pm 5\%$ tolerance, or missing mechanism-matched baselines without justified architectural divergence.

```
24

Hardware Profile Sufficiency Failure
```

v2.5.0 (MAR-8, D-056) — `verify-hardware-profile` detected efficiency claims lacking empirical latency distributions ($p50, p90, p99$), missing separate peak training and inference memory, or failing to exclude warmup iterations.

```
25

Experiment Freeze / Seed Mismatch Failure
```

v2.5.0 (MAR-7, C63, D-060) — `verify-experiment-freeze` detected evaluation reports omitting pre-registered seeds, substituting seeds post-hoc, cherry-picking, or failing against `experiment_freeze_manifest.json`.

```
26

Foundation Model Contamination Failure
```

v2.5.0 (MAR-6, D-061) — `contamination-check` detected exact 13-gram overlap between evaluation benchmarks and training corpora or temporal knowledge cutoff contamination.

```
27

Statistical Protocol Violation
```

v2.6.0 (C65, C66, D-062, D-063, D-064) — `verify-statistical-protocol` detected missing primary statistical tests, missing multiple comparisons corrections for multi-contrast comparisons, missing effect sizes alongside reported p-values, failure to use robust aggregation (IQM) for small-N runs ($N < 10$), or missing negative controls.

```
28

Sensitivity Analysis Violation
```

v2.6.0 (D-065) — `verify-sensitivity-analysis` detected missing hyperparameter sensitivity sweeps across standard perturbation grids ($\pm 10\%, \pm 25\%, \pm 50\%$) or omission of performance degradation failure points.

```
29

Pre-Submission Audit Failure
```

v2.6.0 (D-070) — `pre-submission-audit` detected critical validity failures across the 10-step pre-submission protocol (Steps 1–4: Cold-read triage, Claims-evidence matrix, Statistical audit, Baseline audit).

```
30

Failure Case Taxonomy Violation
```

v2.6.0 (C69, D-071) — `verify-failure-taxonomy` detected empirical robustness or generalization claims lacking systematic failure categorization, conditional prevalence $P(\text{failure} \mid \text{condition})$, standard severity tags (`SEV-1` through `SEV-4`), error confidence scores, or explicit selection rules.

Exit codes are stable across Factory versions whenever practical. Codes 10, 11, and 12 are new in v1.4.0/v1.4.1 (`release-check` — a local-path/machine-identity leak; `acquisition-audit` — a data-generation function definition in an acquisition script, broadened in v1.4.2 to also cover a distribution-sampled value feeding a metrics function; `evidence-check` — a report's declared verdict contradicting its own backing artifact or its own declared criterion); codes 13–16 are new in v1.4.2 (`verify-contract` — a declared verification command's real, re-executed exit code was nonzero; `lint-contract` — a swallowed exception, an acquisition-audit finding, or frozen-verification-machinery tampering; `recompute` — an independent recomputation didn't match, or wasn't actually independent; `stamp-report`/`verify-stamps` — content above an existing stamp was modified after it was issued); code 17 is new in v1.4.2's dated amendment (`check`, for a T-COMP/T-CAUSAL contract, did not satisfy the Mandatory Mechanical Gate — Required Verification Commands, verify-contract, lint-contract, a passing Recompute Declaration, and an intact stamp, all five checked together, whichever sub-check failed is named in the printed detail); codes 18 and 19 are new in v2.2.0 (`tier-check`, also wired into `check` — a contract's declared Scientific Claim Tier read weaker than the tier mechanically inferred from its own text; `release-certify` — one or more contract reports under the given chunks directory failed a Final-Status, evidence/recompute-consistency, tier-inference, acquisition-audit, or release-check category, named individually in `project/RELEASE_CERTIFICATION.md`); codes 20, 21, and 22 are new in v2.3.0 (`finalize` — transactional integrity failure; `delegate` — unverified delegation mismatch; `release-check` — outbound secrecy scan leak); codes 23, 24, 25, and 26 are new in v2.5.0 (`verify-baseline-parity` — MAR-2 parameter/compute parity violation; `verify-hardware-profile` — MAR-8 empirical hardware latency/memory profiling insufficiency; `verify-experiment-freeze` — MAR-7/C63 seed pre-registration mismatch or cherry-picking; `contamination-check` — MAR-6 13-gram benchmark contamination or temporal cutoff leak); codes 27, 28, 29, and 30 are new in v2.6.0 (`verify-statistical-protocol` — statistical inference and robust aggregation protocol violation; `verify-sensitivity-analysis` — hyperparameter sensitivity sweep omission; `pre-submission-audit` — critical pre-submission audit protocol failure; `verify-failure-taxonomy` — systematic failure case taxonomy omission); codes 0–9 are unchanged.

---

# Gatekeeper Report

Every execution generates

```
gatekeeper_report.md
```

Minimum contents

- Factory version
- project name
- chunk
- contract
- execution timestamp
- checks executed
- checks passed
- checks failed
- warnings
- execution duration
- exit code
- final status

---

# Extensibility

New deterministic checks may be added over time.

Every new check must

- be deterministic
- have measurable inputs
- produce a boolean result
- avoid AI reasoning

---

# Relationship to Dynamic Rules

Whenever an ACTIVE Dynamic Rule becomes fully deterministic

↓

Implement it inside Gatekeeper.

Dynamic Rules are knowledge.

Gatekeeper is enforcement.

---

# Relationship to Constitution

The Constitution defines behavior.

Gatekeeper enforces only the portions that can be verified objectively.

Behavior requiring judgement remains outside Gatekeeper.

---

# Performance

Gatekeeper should

- minimize execution time
- avoid unnecessary filesystem scans
- reuse existing verification artifacts when safe
- fail fast on critical errors

Correctness always takes priority over speed.

---

# Security

Gatekeeper must never

- modify `source/` or any file governed by contract semantics (frozen files, verification scripts, contract/report content)
- rewrite Git history, in either the outer repository or `project/`'s nested repository
- execute destructive commands
- overwrite an existing report
- delete a permanent artifact under `project/` (only `TAKE_THIS/`, a disposable copy-only staging directory, is ever cleared)

Gatekeeper's actual scope (v1.3.4 correction -- the prior wording claimed
pure read-only status apart from a report file that isn't even written;
see Outputs' DRIFT-2 note): read-only with respect to `source/` and to
contract semantics generally. Within that boundary, `gatekeeper.py`
performs the following enumerated mutations, all of them deterministic and
disclosed in its own Implementation Status:

- writes baseline hash snapshots under `project/.gatekeeper/snapshots/` (`snapshot`, `snapshot-chunk`)
- moves files out of `DROP_HERE/` to manifest-declared destinations (`sort-dropbox`)
- copies files into `TAKE_THIS/` and deletes files from `TAKE_THIS/` only (`stage-takethis`, `clear-takethis`)
- writes new files extracted from a contract's MATERIALIZE-tagged blocks (`materialize`)
- runs `git add`/`git commit` scoped entirely to `project/`'s own nested repository (`commit-project`)

`self-check`, `release-check`, `acquisition-audit`, and `evidence-check` (v1.4.0/v1.4.1) perform no
mutations at all — all are strictly read-only, printing findings to stdout only. `release-check`
reads the manuscript/release artifact and `project/key_facts.md`; `acquisition-audit` reads
acquisition scripts and contract reports; `evidence-check` reads contract reports and the JSON
artifacts they name. None of the four modify anything, and none touch `source/`.

No command writes, moves, or deletes anything under `source/`, and no
command performs any git operation against the outer repository.

---

# Design Philosophy

Gatekeeper exists to eliminate preventable human and AI mistakes through deterministic verification.

The long-term goal of the Factory is that every reusable engineering lesson eventually becomes

```
Observation

↓

Dynamic Rule

↓

Gatekeeper Check

↓

Automatic Enforcement
```

When a mistake becomes impossible instead of merely unlikely, the Factory has improved.