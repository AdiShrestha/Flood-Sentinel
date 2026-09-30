# Factory Specification

Version

2.6.0


---

# Purpose

The Factory Specification defines **how the AI Software Factory operates**.

Unlike the Constitution, which defines universal engineering principles, this document defines the implementation of the Factory itself.

The Constitution answers

> What rules govern every project?

The Factory Specification answers

> How does the Factory execute projects?

This document contains no behavioral rules.

Behavior belongs exclusively in `constitution.md`.

---

# Factory Objectives

The Factory exists to

- maximize software quality
- maximize reproducibility
- maximize continuity between AI sessions
- minimize unnecessary AI decision making
- minimize ambiguity
- preserve engineering knowledge
- evolve through evidence instead of intuition

---

# Ownership Model

Every artifact has one owner.

Ownership prevents ambiguity.

---

## Architect (currently bound to Claude)

Responsibilities

- project planning
- architecture
- research
- chunk planning
- contract generation
- invariant definition
- review
- fix package generation
- project level decisions
- splitting an approved chunk plan into individual contract files (see Chunk Specification — this was previously attributed to an undefined "Splitter" role; it is the Architect's responsibility, performed as the last step of Chunk Planning, not a separate actor)

Does not perform implementation for contracts tagged `Risk Tier: Low` or `Medium` in the Contract Specification.

Does perform implementation directly for any contract tagged `Risk Tier: High` — this is an explicit exception, not a fallback. High-risk work (decision thresholds, shared mutable state, cryptographic or security-critical logic, anything where a subtle Implementor error would be expensive to detect after the fact) is scoped to the Architect at contract-generation time, not discovered after a failed Phase 3. See Contract Specification.

---

## Implementor (currently bound to Gemini, or any sufficiently capable coding agent — v2.2.0 renaming; see CHANGELOG.md)

Responsibilities

- implementation
- verification
- testing
- reporting
- continuous logging
- contract execution

Never redesigns architecture.

Never invents requirements.

---

## Gatekeeper

Responsibilities

- deterministic validation
- repository verification
- frozen file checks
- manifest verification
- report existence
- repository cleanliness

Never performs AI reasoning.

---

## Human

Responsibilities

- approve architecture
- approve factory evolution
- approve workflow changes
- manage repositories
- provide external resources
- resolve stop conditions requiring human judgement

---

# Repository Specification

```
AI_Software_Factory/

factory/

project/

source/

DROP_HERE/
```

The Factory directory contains reusable infrastructure.

The Project directory contains project specific artifacts.

Source contains implementation.

DROP_HERE (v1.1.3) is a gitignored inbox for handing files to the
Implementor — see Dropbox Specification below.

---

# Factory Artifacts

---

## constitution.md

Purpose

Universal engineering principles.

Owner

Human

Created

Factory initialization.

Modified

Rarely.

---

## factory_spec.md

Purpose

Factory operating manual.

Owner

Human

Created

Factory initialization.

Modified

Only when Factory workflow changes.

---

## dynamic_rules.md

Purpose

Evidence backed improvements promoted from completed projects.

Owner

Human

Modified

Only after promotion.

### Promoted Rule Schema (illustration)

`dynamic_rules.md` is evidence-only, per its own Purpose statement above — every rule entry it holds is a real, currently-live PROPOSED or ACTIVE rule, never a worked example. This illustration lives here instead (v1.3.4, DRIFT-9) so a future deterministic parser (including the `gatekeeper.py self-check` subcommand) greping `dynamic_rules.md` for `Status` + `ACTIVE` can never mistake a sample entry for a real one.

```
Rule ID

D-001

Category

Gate

Status

ACTIVE

Promoted From

Three independent projects

Evidence

Repeated modification of frozen files.

Description

Verify hashes of every frozen file before commit.

Reason

Prevented accidental edits across multiple projects.

Implementation

Gatekeeper compares stored hashes.

Verification

Automatic.

Date Added

2026-07-14

Projects

3

Notes

First promoted Dynamic Rule.
```

---

## gatekeeper.py

Purpose

Deterministic validation.

Owner

Human.

Modified

As deterministic checks improve.

---

## CHANGELOG.md

Purpose

Factory evolution history.

Owner

Human.

Append only.

---

## VERSION

Purpose

Current Factory version.

Owner

Human.

---

# Project Initialization

The Architect creates

```
project_description.md

architecture.md

roadmap.md

project_knowledge.md

invariants.md
```

These become the initial project knowledge.

**venue_requirements.md and project/key_facts.md (v1.4.0, Frozen Files, created at Project Initialization alongside the five documents above):** required for any project targeting a peer-reviewed venue or any other external release. See the Scientific Validity Specification section immediately below for both artifacts' full schema and the Methodology Adversarial Review (MAR) gate that reviews `venue_requirements.md` before Chunk 01 may begin.

**project_knowledge.md's Assumptions section is living, not one-time (v1.3.0):** assumptions surfaced during execution — not just those known at project start — get appended back here as they're discovered, across every chunk, not only written once at Project Initialization and left static. An assumption discovered in Chunk 4 is exactly as real as one known in Chunk 1; the document's usefulness depends on it staying current.

**technical_debt.md (v1.3.0, created on first use, not necessarily at Project Initialization):** a lightweight, append-only register for debt knowingly accepted rather than fixed — a shortcut taken under a Self Review conservatism fallback, a Chunk Review finding judged not worth a Fix Package, anything deliberately deferred. Each entry:

```
Debt ID (TD-001, permanent, never reused)
Description
Reason Accepted
Introduced In (chunk)
Resolution Status (Open / Resolved — never deleted, only marked)
```

Populated by the Architect, typically at Chunk Review, when something is knowingly deferred rather than fixed. This is distinct from a contract report's Remaining Risks section — Remaining Risks is a point-in-time snapshot inside one report that's easy to lose track of across many chunks; `technical_debt.md` is the persistent, cross-chunk record of what's still owed. Per the Factory's own Design Philosophy, this exists because deferred work silently forgotten is a real, demonstrated failure mode elsewhere in software engineering generally — not speculative.

Only one chunk exists initially.

```
chunk01/
```

Remaining chunks are generated later.

---

# Scientific Validity Specification (v1.4.0)

*Added following the GLOF project retrospective (`v1_4_0_scientific_validity_layer.md`). Every
section before this one verifies that an implementation matches its specification. Nothing before
this section verifies the specification against anything outside the Factory — venue standards,
domain physics, statistical requirements. See Constitution EP-007, C51, C52, C53, and
`dynamic_rules.md` D-011 through D-018.*

## venue_requirements.md

Frozen File, created at Project Initialization. Gives the Architect an external reference point —
per C52, a specification with no external reference point is incomplete. Contains: the target
venue, at least 3 recent venue publications with their methodology/baselines/sample sizes, minimum
expected baselines (operational, statistical, learned), minimum expected sample sizes, a required
statistical method per comparative/causal claim, required ablation types, expected data properties
(feeds Reality Gate), pre-registered falsification criteria per core hypothesis, and title/claim
conventions mapping every anticipated title adjective to its required validating test. Full template:
`venue_requirements_TEMPLATE.md`.

**Domain grounding requirement:** every numeric expectation in venue_requirements.md's "Expected
Data Properties" section must cite one of: (a) a peer-reviewed publication reporting the same
statistic for the same sensor/region/season, (b) the sensor's documented revisit cycle plus known
regional climatology, or (c) a prior dataset from the same region with documented completeness.
"Architect's estimate" is not a valid basis. If none of (a)–(c) is available, state
"UNKNOWN — Reality Gate will use conservative defaults" explicitly, and flag it as an MAR-6 finding
— an unfounded number silently treated as ground truth defeats the entire purpose of this document.

**Pre-registered falsification criteria:** for each core hypothesis, venue_requirements.md declares
what result would falsify it and what action follows, before the experiment runs — e.g. "if Score-A
AUC-ROC < 0.55 on synthetic anomalies, conclude reconstruction error is non-discriminative for this
feature type and exclude it from the combined scorer." This is distinct from MAR-7 (what's
publishable if the hypothesis fails) — it answers a different question: what result changes the
methodology mid-project, decided before anyone has an incentive to rationalize a disappointing
number after the fact. C53 covers the case where this was never declared and a null result shows up
anyway; a declared falsification criterion is the stronger, earlier form of the same protection.

## project/key_facts.md

Frozen-policy file (amended only via Architecture Amendment), created at Project Initialization,
listing every numeric or named fact where inconsistency between the manuscript and the project's own
knowledge base would be embarrassing or critical — casualty figures, coordinates, key dates, named
totals. Each entry is a `## Key Fact:` block with `anchor`, `expected_value`, and `tolerance` fields.
Checked automatically by `gatekeeper.py release-check` (D-017) before submission. Deliberately
bounded: it catches drift only against facts the Architect declared in advance, never open-ended
fact-checking of prose, which would require AI reasoning Gatekeeper's Purpose forbids. Full template:
`key_facts_TEMPLATE.md`.

## Methodology Adversarial Review (MAR)

Mandatory phase, positioned after Project Initialization and before Chunk 01 planning. Blocks
execution. Performed by a session that did not write the founding artifacts.

**v2.2.0 (C55):** this Factory has exactly two AI roles — no standing third reviewer exists to
perform gates 4–7 with genuine cross-model independence as routine workflow. The default,
zero-added-role path is: the Architect performs gates 4–7 itself, in a fresh pass explicitly
adopting an adversarial stance against its own founding documents — attacking its own title
claims, its own venue-alignment argument, its own assumptions, and its own negative-result
contingency as if reviewing someone else's project. This is disclosed in
`methodology_adversarial_review.md` as same-session review, honestly narrower than genuine
cross-model independence, not silently presented as equivalent to it.

Where the Human wants the stronger version, obtaining a genuinely independent opinion (a fresh
session with a different model, a human domain collaborator) remains available for any project —
invoked as an optional, one-time addition for that project specifically, per C55, not as a
standing pipeline role with its own onboarding document or ongoing responsibilities. **For any
project targeting a peer-reviewed venue, this stronger path is recommended for gates 4–7
specifically; whichever path is actually used, the choice and its rationale are recorded in
`methodology_adversarial_review.md` itself, never left implicit** (D-011, C55).

Input: the five founding documents plus `venue_requirements.md`.

Eight ratified gates (v2.5.0, enhanced v2.6.0):

| Gate | Question | Fail condition | Checkable by |
|---|---|---|---|
| MAR-1 Data Authenticity | Real observations or simulation/aggregate? | Simulated, and not labeled as such | Reality Gate + gatekeeper.py acquisition-audit |
| MAR-2 Baseline Sufficiency & Parity | ≥3 baselines covering trivial/sanity, canonical, and SOTA, with Baseline Parity Ledger completed (±2% params, ±5% compute)? | Fewer than 3 baselines, strawman comparisons, or parity ledger absent/exceeded | Structural + mechanical via `gatekeeper.py verify-baseline-parity` |
| MAR-3 Statistical Power & Seed Plan | Sample sizes support the claim with a planned power calculation (n ≈ 7.85/d²), pre-registered protocol, and computed CI/effect sizes? | <10 samples for quantitative, <30 for rate, missing effect sizes, or comparative claim with no computed CI/significance test | Structural + mechanical via `gatekeeper.py freeze-experiment` / `verify-experiment-freeze` & `verify-statistical-protocol` |
| MAR-4 Title-Claim & Generalization Scope | Every title adjective maps to a tested property, tested across the Generalization Ladder? | Any adjective untested, or broad claim backed only by narrow synthetic split | Judgement — Mandatory Cross-Model Adversarial Audit for peer-reviewed venues (see above) |
| MAR-5 Venue Alignment & Provenance | Methodology matches ≥3 recent venue papers, and third-party baselines cite exact commit hashes? | No venue papers referenced, divergence from venue conventions, or unversioned baselines | Judgement — Mandatory Cross-Model Adversarial Audit for peer-reviewed venues |
| MAR-6 Assumption Stress Test & Failure Cases | If each assumption fails, is there still a contribution? Is a systematic failure case taxonomy present? | Single assumption failure destroys project, or failure modes uncharacterized | Judgement + mechanical via `gatekeeper.py verify-failure-taxonomy` |
| MAR-7 Negative Result Contingency | What's the publishable contribution if the core hypothesis fails? | None identified | Judgement — Mandatory Cross-Model Adversarial Audit for peer-reviewed venues |
| MAR-8 Hardware & Efficiency Profiling | Does an efficiency/real-time/throughput claim have a percentile-latency measurement (p50/p90/p99), physical Joules/Wh, and sustained thermal headroom? | Efficiency claim present with missing profile, mean-only latency, unmeasured energy, or warmup included | Structural + mechanical via `gatekeeper.py verify-hardware-profile` |

Output: `methodology_adversarial_review.md` — per-gate verdict (PASS / CONDITIONAL PASS / FAIL),
findings with evidence, required changes, which review path (mandatory cross-model reviewer or self-adversarial)
was actually used for gates 4–7 and why, and a "Hostile Reviewer Simulation" section naming the 5
strongest attacks a real reviewer would make. Any FAIL means Project Initialization is not complete.
CONDITIONAL PASS means Chunk 01 proceeds with the conditions as mandatory Chunk 01 contracts.

Mechanical verification: MAR-2 baseline parity is verified by `gatekeeper.py verify-baseline-parity`;
MAR-3 statistical protocol and power are verified by `gatekeeper.py verify-statistical-protocol` and `verify-experiment-freeze`;
MAR-6 failure taxonomy is verified by `gatekeeper.py verify-failure-taxonomy`;
MAR-8 efficiency profiling is verified by `gatekeeper.py verify-hardware-profile`; confirmatory seed
plans are locked and verified by `gatekeeper.py freeze-experiment` / `verify-experiment-freeze`;
foundation model benchmark contamination is verified by `gatekeeper.py contamination-check`;
hyperparameter sensitivity is verified by `gatekeeper.py verify-sensitivity-analysis`;
pre-submission readiness is verified by `gatekeeper.py pre-submission-audit`.
MAR-4, MAR-5, and MAR-7 require genuine domain judgement and require a separate cross-model session for venue-targeted submissions.


## Reality Gate

Mandatory phase, positioned between data acquisition/preprocessing and model training. Blocks
training. Fully deterministic by design — every check compares a project-reported number against a
number declared in `venue_requirements.md` ahead of time, never a threshold invented after seeing
the data.

Checks, against a `project/data_manifest.json` a data-acquisition contract must produce:

1. **Gap statistics** — % missing observations per time window, vs. the expected gap rate declared
   in venue_requirements.md.
2. **Distribution check** — variance/entropy of feature distributions, flagging suspicious
   uniformity (a discriminative encoder cannot learn from inputs with no discriminative texture).
3. **Temporal coverage** — actual date range vs. the declared invariant.
4. **Sensor coverage** — all expected sensors actually present.
5. **Provenance chain (D-014)** — for every channel in the feature matrix, a documented
   transformation path from raw product → preprocessed data → channel value. Any channel whose
   provenance includes an undocumented aggregation, interpolation, or simulation step is treated as
   simulated for SVI-001 purposes, regardless of what the pipeline calls itself.

`data_manifest.json` schema (produced by the Implementor's data-acquisition contract as part of its own
Phase 2/3 verification output, the same way Verification Script output is already produced and
reported):

```json
{
  "gap_rate_pct": 0.0,
  "distribution_stats": {"channel_name": {"variance": 0.0, "entropy": 0.0}},
  "temporal_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "sensors_present": ["..."],
  "channel_schema": {
    "column_order": ["channel_name_0", "channel_name_1", "..."],
    "units": {"channel_name": "..."},
    "physical_range": {"channel_name": {"min": 0.0, "max": 0.0}}
  },
  "provenance_chain": {
    "channel_name": {
      "raw_product": "...",
      "transformation_steps": ["..."],
      "undocumented_step": false
    }
  }
}
```

`channel_schema` exists so a feature matrix's column order and units are declared once,
machine-readably, rather than assumed identically by every downstream loader and model — a
transposed or renamed channel is a silent, shape-valid, physically-meaningless bug no shape check
catches. This does not require a new validation library; Reality Gate diffs the declared
`column_order` against what the data-loading contract's own verification output reports reading, the
same deterministic string-comparison pattern as every other Reality Gate check.

Output: `reality_gate_report.md`, PASS/FAIL per check. Any FAIL requires an Architecture Amendment —
the existing mechanism, not a new one; a Reality Gate failure is precisely "an earlier architectural
assumption was wrong."

**Reality Gate Limitation (disclosed per C39, added following Chunk 07 of the GLOF project rework
— D-019):** Reality Gate verifies data *properties* — gap rates, distributions, coverage. It cannot
verify data *provenance* — whether the data came from a real observation API or a well-designed
generator. A sufficiently sophisticated simulator will always pass property-based checks, because it
is designed to produce the expected properties. This is not a defect in the checks above; it is a
fundamental limitation of property-based verification applied to a provenance question. Reality Gate
is therefore necessary but not sufficient for SVI-001, and is supplemented by:

- **Acquisition Provenance Verification (D-019)** — a separate, API-call-level manifest
  (`acquisition_provenance.json`, below), harder to fabricate convincingly than data properties
  because it requires evidence of specific calls that either did or didn't happen.
- **Acquisition Script Structural Audit (D-022)** and **Acquisition Report Textual Scan (D-023)** —
  implemented as `gatekeeper.py acquisition-audit`, see `gatekeeper_spec.md`.
- **Network Dependency Pre-Check (D-020)** and **External Service Dependencies** (Contract
  Specification field, below).

Reality Gate catches obvious simulation artifacts — 0% gaps, uniform distributions, impossible
coverage. It does not catch sophisticated simulation that matches expected properties. This
limitation cannot be eliminated by improving Reality Gate's own checks — only by adding
provenance-based checks alongside them, which is what the above do.

## acquisition_provenance.json (v1.4.0, D-019)

Every data-acquisition contract produces this alongside `data_manifest.json` — distinct from and in
addition to `data_manifest.json`'s per-channel `provenance_chain` field, which is self-reported by
the same agent producing the data and is therefore easier to fabricate convincingly than API-call
evidence:

```json
{
  "source": "COPERNICUS/S1_GRD",
  "api_endpoint": "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/assets",
  "authentication_method": "ee.Initialize() via OAuth2",
  "query_parameters": {
    "image_collection": "COPERNICUS/S1_GRD",
    "date_range": ["YYYY-MM-DD", "YYYY-MM-DD"],
    "spatial_filter": "...",
    "band_selection": ["..."]
  },
  "total_api_calls": 0,
  "total_scenes_returned": 0,
  "first_scene_date": "YYYY-MM-DDTHH:MM:SSZ",
  "last_scene_date": "YYYY-MM-DDTHH:MM:SSZ",
  "http_status_codes": [200],
  "response_payload_hash": "sha256:...",
  "downloaded_file_manifest": [
    {"filename": "...", "size_bytes": 0, "checksum": "sha256:..."}
  ],
  "execution_environment": {"network_reachable": true, "sandbox_bypass": true}
}
```

Reality Gate checks this manifest before checking data properties: does the recorded endpoint match
the expected service; is the scene count consistent with the expected revisit frequency for the
declared date range (e.g. a 6-day-revisit sensor over an 8.8-year range implies roughly 535 scenes —
a manifest reporting the window count instead of the scene count, or a suspiciously round number, is
a red flag worth investigating, not an automatic fail); do the first/last scene dates fall within
the declared temporal extent; is `network_reachable` recorded `true`. Not implemented in
`gatekeeper.py` — the revisit-frequency consistency check requires per-sensor domain knowledge that
varies by acquisition source and has not been built and exercised against a real project yet.

## hardware_profile_manifest.json (v2.4.0, D-056 — candidate)

Same pattern as `data_manifest.json`, applied to an efficiency claim instead of a data property.
Produced by whichever contract actually measures the claimed latency/throughput/memory numbers, as
part of that contract's own verification output — only for a project whose
`venue_requirements.md` Efficiency Claim Requirements section (v2.4.0) is not N/A; most projects
will never produce this file, and that's the correct outcome for most projects.

```json
{
  "hardware": {"accelerator": "...", "driver_version": "...", "framework_version": "..."},
  "latency_ms": {"p50": 0.0, "p90": 0.0, "p99": 0.0, "batch_size": 1, "warmup_excluded": true},
  "throughput": {"samples_per_sec": 0.0, "batch_size": 0},
  "memory_mb": {"peak_train": 0.0, "peak_inference": 0.0, "includes_activations": true},
  "flops_macs": {"value": 0.0, "tool": "...", "tool_version": "..."},
  "sustained_load_tested": false
}
```

Checked mechanically by `gatekeeper.py verify-hardware-profile --manifest [path]`:
verifies that `latency_ms` contains valid, positive `p50`, `p90`, `p99` values with `warmup_excluded: true`,
that `throughput` is recorded separately, that `memory_mb` reports `peak_train` and `peak_inference` separately
with `includes_activations: true`, and that `sustained_load_tested` is true if operating on thermally-constrained
or edge hardware. If an efficiency claim is made in a contract or report without this passing manifest,
the contract fails verification under Constitution C64 (MAR-8).

## Baseline Parity Ledger Verification (v2.5.0, D-057 — ratified)

Checks the Baseline Parity Ledger table in `venue_requirements.md` (v2.4.0, ratified v2.5.0) — filled in at Project
Initialization as a plan, revisited and verified mechanically once baseline implementations exist.
At Chunk Review's Baseline Completeness Check (`architect_spec.md` §5c), `gatekeeper.py verify-baseline-parity --venue-requirements project/venue_requirements.md`
is executed. It verifies:
1. Every principal T-COMP/T-CAUSAL baseline has parameters within ±2% of the proposed model.
2. FLOPs/MACs are within ±5% under identical input resolution and counting conventions.
3. Training accelerator compute (GPU-hours or FLOP budget) is within ±5%.
4. Precision (FP16/BF16/FP32) is identical.
5. If comparing against an older baseline, `Old_published`, `Old_modernized`, and `Proposed_matched` are populated.
Any baseline comparison violating parity tolerances without an explicit, documented architectural justification
fails with Exit Code 23.

## experiment_freeze_manifest.json (v2.5.0, D-060 — ratified)

Mandated by Constitution C63 to decouple confirmatory evaluation from hyperparameter search and eliminate
the seed-lottery failure mode. Produced before confirmatory claim evaluation runs by running:
`gatekeeper.py freeze-experiment --chunk NN --seeds 42,43,44,45,46 --split-hash [sha256] --config-hash [sha256]`

```json
{
  "chunk": "chunkNN",
  "git_commit": "...",
  "environment_lock_hash": "sha256:...",
  "data_split_checksum": "sha256:...",
  "config_hash": "sha256:...",
  "registered_seeds": [42, 43, 44, 45, 46],
  "power_target": {"delta_min": 0.5, "sigma_d": 0.5, "planned_n": 10},
  "primary_metrics": ["test_f1", "test_auc_roc"],
  "frozen_at": "YYYY-MM-DDTHH:MM:SSZ"
}
```

Enforced mechanically by `gatekeeper.py verify-experiment-freeze`: reads contract verification outputs and
JSON artifacts to verify that all confirmatory runs used ONLY the registered seeds, that all runs are reported
(no silent deletion of bad seeds), and that no optional stopping occurred.

## contamination_audit.json (v2.5.0, D-059 — ratified)

Mandated for any foundation-model or LLM evaluation to eliminate benchmark leakage. Generated by running
`gatekeeper.py contamination-check --benchmark [path] --training-data [path] --model-cutoff [YYYY-MM-DD]`:

```json
{
  "benchmark_dataset": "...",
  "benchmark_creation_date": "YYYY-MM-DD",
  "model_training_cutoff": "YYYY-MM-DD",
  "temporal_precedence_valid": true,
  "ngram_size": 13,
  "exact_ngram_matches_found": 0,
  "high_similarity_matches_found": 0,
  "audit_verdict": "PASS"
}
```

If benchmark creation date is prior to model training cutoff, or exact n-gram overlap is detected,
the audit fails with Exit Code 26.

## Generalization Ladder Verification (v2.5.0, D-061 — ratified)

Every project making empirical claims of "robustness", "generalization", or "real-world deployment" must
formally declare which rung of the Generalization Ladder the claim targets in `venue_requirements.md`:
- Rung 1: In-Distribution Clean Validation.
- Rung 2: Disjoint Operational Split (site/sensor/temporal disjointness).
- Rung 3: Cross-Dataset / External Domain Validation (fully independent benchmark from distinct source).
- Rung 4: Systematic Perturbation Ladder (severity matrix of domain corruptions, e.g. noise, drift, dropouts).
- Rung 5: Adversarial Perturbation Curve (accuracy vs. budget ε).
- Rung 6: Structured Failure Case Taxonomy (subgroup error clustering).

Title or abstract claims declaring "robust" or "generalizable" supported only by Rung 1 or Rung 2 are hard-rejected
at MAR-4 and Chunk Review under Constitution C51.

## Statistical Inference Protocol Verification (v2.6.0, C65–C66, D-062–D-064)

Mandated by Constitution Section 11 to eliminate unstated, uncorrected, or underpowered significance claims.
Enforced mechanically by `gatekeeper.py verify-statistical-protocol --reports <path>...`.
Verifies:
1. Primary statistical test matches the experimental pairing structure and distributional assumptions (paired t-test, Wilcoxon, Friedman/Nemenyi).
2. Multiple testing corrections (Holm, Bonferroni, Benjamini-Hochberg FDR) are declared and applied when >3 comparisons are evaluated.
3. Every p-value is accompanied by an effect size (Cohen's d, Cliff's delta, paired difference CI) and practical importance evaluation.
4. Robust aggregation (Agarwal et al. IQM with stratified bootstrap CI) is applied for small-N regimes ($N < 10$).
5. Bounded metrics never display symmetric error bars extending past feasible support.
Violations fail with Exit Code 27.

## Sensitivity Analysis Protocol (v2.6.0, D-065)

Mandated for all load-bearing hyperparameters feeding comparative or causal claims.
Enforced mechanically by `gatekeeper.py verify-sensitivity-analysis --reports <path>...`.
Verifies:
1. Systematic perturbation grids ($\pm 10\%, \pm 25\%, \pm 50\%$, log-spaced for learning rates and weight decays).
2. Response curve evaluations showing steady-state behavior across configurations.
3. Explicit documentation of degradation failure points (where performance breaks down).
Violations fail with Exit Code 28.

## Pre-Submission 10-Step Audit Protocol (v2.6.0, D-070)

Mandated prior to release certification (`gatekeeper.py release-certify`) for venue-targeted submissions.
Enforced mechanically by `gatekeeper.py pre-submission-audit --reports <path>...`.
Steps 1–4 are validity-critical and fail with Exit Code 29 on omission or defect:
1. Step 1: Cold-Read Triage Pass (Area Chair 15-minute simulation).
2. Step 2: Claims-Evidence Matrix Audit (no orphan claims, no orphan evidence).
3. Step 3: Statistical Audit (test tree, effect sizes, multiple comparisons).
4. Step 4: Baseline & Tuning Parity Audit.
Steps 5–10 (Ablation completeness, Generalization/failure audit, Hardware/energy audit, Reproducibility checklist, Adversarial rebuttal rehearsal, Mock meta-review) issue structured warnings if incomplete.

## Structured Failure Case Taxonomy (v2.6.0, C69, D-071)

Mandated for claims of robustness, generalization, or deployment suitability.
Enforced mechanically by `gatekeeper.py verify-failure-taxonomy --reports <path>...`.
Verifies:
1. Failure prevalence $P(\text{failure} \mid \text{condition})$, rejecting hand-picked anecdotes.
2. Structured taxonomy categorized by failure mechanism (minimum 3 categories).
3. Severity classification (`SEV-1` to `SEV-4`) and model error confidence levels.
4. Documented, systematic selection rule for presented examples.
Violations fail with Exit Code 30.


## External Service Dependencies (v1.4.0, Contract Specification field, D-021)

For any contract that calls an external API, declared alongside `Dependencies`:

```
External Service Dependencies:
  - service: "Google Earth Engine API"
    authentication: "OAuth2 via ee.Initialize()"
    network_requirement: "Outbound HTTPS to oauth2.googleapis.com and earthengine.googleapis.com"
    failure_behavior: "BLOCKED — HUMAN ACTION REQUIRED. Never fall back to generated data."
```

Forces "what happens if this API is down" to be answered at Chunk Planning time, not discovered
mid-execution. Every such contract's Implementation Instructions must open with a connectivity
pre-check (D-020) whose failure is a Stop Condition under C06 — retry with documented backoff, or
`BLOCKED — HUMAN ACTION REQUIRED`. Never generate, simulate, or synthesize substitute data (C54).
This is project-specific code written per contract, not a generic `gatekeeper.py` feature — every
external API's pre-check looks different.

**Spot-Check Protocol (Human Action Required, D-019 defense in depth):** for any acquisition
contract, the Human independently verifies 3 randomly selected data points against a second,
independent source (e.g. the relevant data provider's own web explorer), recording the comparison in
`results/data_authenticity/spot_check_report.md`. A discrepancy >5% is a Stop Condition. This is not
automatable — it requires an independent path outside the acquisition pipeline, the provenance
manifest, and Reality Gate, all of which a sufficiently determined fabrication could in principle
compromise together.

## Release Artifact Scan

Runs before submission, on any artifact targeted for external release (manuscript,
REPRODUCIBILITY.md, supplementary material). Implemented: `gatekeeper.py release-check`
(D-017) — see `gatekeeper_spec.md`'s Implementation Status for the full command spec. Two checks:
a local-path/machine-identity scan (hard FAIL) and a key-fact consistency check against
`project/key_facts.md` (WARNING, heuristic).

## Release Certification (v2.2.0, D-038)

Distinct from `release-check` above (one artifact, two checks) and distinct from any single
chunk's Gatekeeper PASS (a per-chunk state). "Certified," applied to a project, refers to exactly
one artifact this Factory's tooling produces: `project/RELEASE_CERTIFICATION.md`, written by
`gatekeeper.py release-certify --chunks-dir project/chunks [--manuscript ... --key-facts ...
--scripts ...]` (Constitution C59).

`release-certify` walks every `contract_report.md` under the given chunks directory and
aggregates, in one pass: Final Status COMPLETE for every contract (a single FLAGGED or BLOCKED
status anywhere blocks certification); `evidence-check`'s and `recompute`'s logic against every
report carrying the relevant declared block; `tier-check`'s fail-closed inference (D-034) against
every contract whose file is locatable; and, if invoked with `--scripts`/`--manuscript`,
`acquisition-audit` and `release-check`'s own scans. It writes CERTIFIED or NOT CERTIFIED
unconditionally, together with exactly which categories were actually run — a category not
invoked (no `--manuscript` given, say) is absent from that list, not silently assumed passed. Exits
19 on NOT CERTIFIED.

This is deliberately a thinner mechanism than it might sound: it re-runs checks that already exist
against artifacts that already exist, and produces one Markdown file. It does not introduce a new
registry or schema, and it does not certify scientific truth or publication acceptance — only the
categories it actually lists as checked. See `dynamic_rules.md` D-038.

## Scientific Validity Invariants (SVI)

Distinct from project invariants (INV-XXX). Verified at MAR and at Chunk Review.

| ID | Invariant | Verification | Failure impact |
|---|---|---|---|
| SVI-001 Data Authenticity | Features derive from real observations with documented gaps, or the project is explicitly labeled simulation-based with adjusted claims | Reality Gate, automatic | Critical |
| SVI-002 Baseline Sufficiency | ≥3 baselines: operational, statistical, learned | Check evaluation config | Critical |
| SVI-003 Statistical Power | No quantitative claim on undersized N; every comparative claim has a computed CI/significance test, not just an N above threshold | Check sample counts AND check for a present statistical-method artifact | High |
| SVI-004 Title-Claim Consistency | Every title adjective maps to a validated test | MAR + Chunk Review Title-Claim Audit | High |
| SVI-005 Venue Alignment | Methodology checked against ≥3 recent venue papers | venue_requirements.md populated and referenced | Medium |
| SVI-006 Reality Gate | Data properties match methodology assumptions before training | Automatic | Critical |
| SVI-007 Degenerate Metric Flagging (v1.4.1) | No metric value within tolerance of 0.0/0.5/1.0 is reported unflagged when computed on fewer than 30 samples | `gatekeeper.py evidence-check`, automatic | Medium |

## Verdict Cross-Check (v1.4.1, Contract Specification field, D-024/D-025)

Any contract carrying a pre-registered verdict or T-CAUSAL claim includes a structured block in its
`contract_report.md`:

```
## Verdict Cross-Check
verdict_word: SUCCESS
artifact: protocol_e1_real_data.json
artifact_key: f3_falsification_verdict
criterion: count_gte
criterion_field: pre_event_windows_flagged
criterion_threshold: 2
```

`verdict_word`/`artifact`/`artifact_key` are required; `criterion`/`criterion_field`/`criterion_threshold`
are optional, and when present, `criterion` must be one of a closed set (`count_gte`, `count_lte`,
`value_gte`, `value_lte`, `bool_true`, `bool_false`) — never a free-form expression, since evaluating
arbitrary natural-language criteria would require AI reasoning Gatekeeper's Purpose forbids. Checked
automatically by `gatekeeper.py evidence-check` (D-024, D-025): does `verdict_word` match the
artifact's own value at `artifact_key`, and does the artifact's own value at `criterion_field`
actually satisfy the declared criterion in a way consistent with `verdict_word`. A report without
this block is not checked, not silently passed — the block is the declared interface, the same
tradeoff `key_facts.md` makes for `release-check`.

Any JSON artifact referenced this way that also contains a `metrics` array
(`[{name, value, sample_count}, ...]`) is additionally checked for SVI-007 degenerate values —
see `implementor_spec.md`'s contract report template for the required shape.

## Cross-Contract Metric Supersession (v1.4.1, Chunk Review check, D-026)

When a contract's Outputs re-evaluate metrics an earlier contract already reported (e.g. a unified
evaluation pipeline re-running baselines a standalone contract evaluated independently), the later
contract's report states: which earlier contract's metrics it supersedes, why the numbers differ, and
that its own artifact is now the single source of truth. The earlier contract's report gets a
supersession note appended — never edited (C30) — and any claim-evidence map is updated to point at
the superseding artifact. Not Gatekeeper-checkable: detecting "this re-evaluates an earlier contract"
reliably needs more context than a safe heuristic can provide. Stays a Chunk Review check.

---

# Chunk Specification

Each chunk represents one engineering milestone.

A chunk contains

```
chunkNN/

chunkNN.md

execution_manifest.yaml

contracts/

reports/

notes/

scripts/
```

The Architect generates

- chunkNN.md
- execution_manifest.yaml
- contracts/ (the contract-split step described under Ownership Model — the Architect)

The Implementor creates

- reports/ — one subdirectory per contract: `reports/{{CONTRACT_ID}}/contract_report.md` (v1.1.2 — this path convention was previously undefined; `gatekeeper.py`'s `next` and `check` commands assume it)
- notes/ (working notes the Implementor keeps for itself across Phase 1–4 within the chunk; not a formal artifact, not reviewed by the Architect, safe to be messy)
- scripts/ (one-off verification or setup scripts a contract's Implementation Instructions call for; anything reused across contracts should graduate to the project's `source/` tree instead of living here)

---

# Lightweight Chunk Designation

Every contract still goes through Phase 1–4 and still gets a `contract_report.md` — this designation trims *ceremony*, not verification.

The Architect may mark a chunk `Weight: Lightweight` in `chunkNN.md` when every contract in it is `Risk Tier: Low` (see Contract Specification) and touches no Frozen File, no shared mutable state, and no invariant.

A Lightweight chunk differs from a Standard chunk only in:

- Phase 3 (Self Review) may be combined with Phase 4 (Reporting) into a single pass instead of two separate documents.
- `project/evolution/telemetry.jsonl` is still updated, but `decision_log.md` entries are optional unless something genuinely decision-worthy happened.

A Lightweight chunk does **not** skip: Gatekeeper validation, frozen-file checks, verification scripts, or Chunk Review. If a chunk contains even one `Risk Tier: Medium` or `High` contract, the whole chunk is Standard weight.

This exists because a formal-methods-grade process applied uniformly to a solo or small-team academic project can make maintaining the Factory more work than the project itself — the fix is a smaller, still-verified path for genuinely small work, not skipping verification under deadline pressure.

---

# Contract Specification

Every contract must contain

```
Contract ID

Objective

Context

Dependencies

Risk Tier

Implementation Owner

Allowed Files

Frozen Files

Inputs

Outputs

Implementation Instructions

Verification Scripts

Invariant Checklist

Predicted Failure Modes

Definition of Done

Stop Condition

Traces To (v1.3.0 — see below; write "N/A" explicitly if genuinely nothing applies, rather than omitting the field)
```

<!-- Possible v1.3.5 candidate (not yet proposed -- see dynamic_rules.md's Candidate Observations
     table, "Possible v1.3.5 candidates" §3, for full grounding/critique/evidence-status): a new
     field, `Risk Surface Scan Required`, set true for any
     contract whose Outputs include dependencies, secrets-adjacent code paths, or PII handling.
     When true, the Implementor's existing Phase 2/3 would run dependency/license scanning, secrets
     detection, and static analysis as part of its own verification, reported the same way every
     other Verification Script already is; Gatekeeper would get a new check category (presence +
     pass/fail only, no judgment, matching its existing philosophy exactly). Gated on completing
     at least one more real project first, per that document's own §4. -->

The Architect owns every field.

Contracts become immutable after generation.

---

## Risk Tier

The Architect assigns exactly one of `Low`, `Medium`, `High` when the contract is generated, based on what the contract actually touches — not on how large it is.

`High` applies to any contract that touches: decision thresholds, shared mutable state, cryptographic or authentication logic, anything a Frozen File's invariant depends on, or anything where a subtle, hard-to-notice error would be expensive to catch after the fact. `Medium` is everything with real logic but recoverable stakes. `Low` is mechanical, easily-reviewed work (formatting, boilerplate, straightforward CRUD, test scaffolding).

## Implementation Owner

Derived directly from Risk Tier:

| Risk Tier | Implementation Owner |
|---|---|
| Low | Implementor |
| Medium | Implementor |
| High | Architect |

This is the field that operationalizes the exception in the Ownership Model — high-risk work is routed to the Architect at contract-generation time, not discovered after the Implementor's error rate on it turns out to be a problem partway through a chunk.

## Human Action Required (v1.1.1)

Some contracts depend on something no AI in this Factory can do — training on hardware the Implementor's environment doesn't have, obtaining credentials, physically installing something. This is not an Architect-availability problem (see Human Usage Model) and not a Risk Tier problem; it's a distinct dependency type the Architect marks explicitly when writing the contract:

```
Human Action Required: true
Action: {{exactly what the human needs to do, in enough detail to actually do it —
          e.g. "Run notebook X on Colab with a T4/A100 runtime, download the
          resulting checkpoint, place it at {{exact path}}"}}
Blocks: {{which contract IDs in this chunk cannot proceed without this}}
```

When the Implementor reaches a contract with `Human Action Required: true`, it does not attempt the task itself, does not fabricate a stand-in result, and does not silently substitute a smaller/local version (e.g. training a toy model on CPU instead) unless the contract explicitly says a local fallback is acceptable. It outputs a clearly marked notice with the exact `Action` text, marks the contract `BLOCKED — HUMAN ACTION REQUIRED`, and — per the dependency-skipping rule above — proceeds with any contracts in the chunk that don't depend on it. The Architect should sequence chunks so that everything not blocked on a Human Action item is front-loaded ahead of it wherever the architecture allows, precisely so a GPU/credential dependency doesn't stall an entire chunk.

A chunk report with an unresolved Human Action item must restate its `Action` text in full, exact, imperative form (not a cross-reference back to the chunk plan) — the chunk report is what the Human actually reads at the point the action becomes possible, and by then the original chunk plan may be out of easy reach. See Report Specification.

## Frozen Files

A Frozen File's content must not change for the duration of the contracts that declare it frozen — enforced by `gatekeeper.py snapshot`/`snapshot-chunk` (hash at freeze time) and `check`/`next` (hash comparison thereafter). Any actual change is a hash mismatch, Exit Code 4, and blocks completion.

**A Frozen File set is not limited to one file.** A single behavioral contract can span multiple files — several route handlers together defining one API surface's externally-visible behavior, for instance — and all of them are declared frozen together for exactly the same reason a single header would be: so nothing downstream can silently assume the contract still holds after an edit no one flagged. This is a validated pattern, not an edge case requiring improvisation — treat "the invariant this protects spans several files" as the normal case to plan for, not a special one.

## Materialize Convention (v1.3.0)

Raw implementation source is **never** dropped as a loose file into `DROP_HERE/` — `dropbox_manifest.json`'s rules intentionally have no pattern for arbitrary source, since accepting one would mean either guessing a destination (a C01/EP-002 violation) or maintaining an unbounded rule surface. This applies most often to a `High` tier contract the Architect implements directly, but the convention is available to any contract.

When a contract's Implementation Instructions include source the Architect wrote directly that needs to land on disk verbatim, embed it inside the contract markdown itself, immediately preceded by a tag of the exact form:

```
<!-- MATERIALIZE: path/relative/to/repo/root -->
```language
...file content, verbatim...
```
```

The Implementor (or the Architect, for a contract it's executing itself) runs:

```
gatekeeper.py materialize --contract {{CONTRACT_ID}}
```

which deterministically extracts every tagged block and writes it to its declared path, byte-for-byte — no transcription, no interpretation of "where this code belongs." A destination that already exists is left untouched and reported unless `--force` is passed. A single contract may embed any number of tagged blocks. See `dynamic_rules.md` D-002 for the evidence this closes.

## Verification Parameters (v1.3.0)

A contract whose Verification Scripts assert a formal, formula-based, or mathematically-derived proof — a theoretical ceiling, an invariant bound, a statistical guarantee, anything checked against a computed expected value rather than a fixed expected output — must pin the exact numeric parameters that proof is evaluated against, not only the formula and test scale:

```
Verification Parameters:
  {{param_name}}: {{exact value}}
  {{param_name}}: {{exact value}}
  ...
```

Without pinned parameters, a "PASS" is true but under-specified: it confirms the general shape of a claim without confirming a specific, reproducible instance of it. Independent re-verification (Chunk Review, or a future audit) should be checking the same numbers the original implementation used, not merely confirming that the same math holds under whatever numbers the implementer happened to pick. See `dynamic_rules.md` D-003.

## Adversarial Verification for Concurrency (v1.3.0)

A `High` tier contract whose subject matter includes shared mutable state under concurrency must include an adversarial or boundary-condition concurrency test — not merely a loose contention/throughput smoke test — as part of its own Verification Scripts and Definition of Done, specified now, at Chunk Planning time. "No crash under load" and "the single most adversarial interleaving this code could face is provably handled correctly" are different claims of different strength; only the second is acceptable evidence for a Definition of Done covering concurrency-safety. Do not defer this to Chunk Review to construct after the fact — Chunk Review's independent-verification requirement (see Chunk Review) is a check on what the contract already proves, not a substitute for the contract proving it. See `dynamic_rules.md` D-004.

## Traces To (v1.3.0)

Where applicable, a contract states which `project_description.md` Functional/Non-Functional Requirement IDs (`FR-XXX`) and/or `invariants.md` Invariant IDs (`INV-XXX`) it implements or upholds:

```
Traces To: FR-004, INV-002
```

This is intentionally light — a queryable link from implementation back to the requirement or invariant that justified it, not a full chain-of-custody system (source file ↔ contract ↔ requirement ↔ ADR ↔ review). Write "N/A" explicitly for contracts with no clean mapping (e.g. pure test-harness scaffolding) rather than omitting the field, so its absence is a deliberate statement, not an oversight.

---

## Scientific Claim Tier (v1.4.0)

Every contract whose Outputs include a quantitative or comparative claim declares a tier:

| Tier | Claim type | Minimum evidence |
|---|---|---|
| T-DESC | "We observe X" | Evidence artifact + traceability (existing, unchanged) |
| T-COMP | "X outperforms Y" | ≥2 competitive baselines + a computed significance test |
| T-CAUSAL | "X enables Y" / "X is robust to Z" | Adversarial test of the specific property + ≥3 baselines + an explicit Stop Condition (C53) declared before execution |

A T-COMP claim with one baseline is `COMPLETE — FLAGGED` at best. A T-CAUSAL claim without adversarial testing, or without a declared Stop Condition, is `BLOCKED`. Every hyperparameter feeding a T-COMP or T-CAUSAL claim requires a citation, a sensitivity analysis, or an explicit "arbitrary, disclosed as a limitation" note (D-018) — never a bare unjustified value. Any contract acquiring data from an external API additionally declares External Service Dependencies (below, D-021) and opens its Implementation Instructions with a connectivity pre-check (D-020) — see the Scientific Validity Specification section for full grounding.

**(v1.4.2, dated amendment — D-032) Mandatory Mechanical Gate.** A T-COMP or T-CAUSAL contract's Final Status cannot read `COMPLETE` by AI attestation alone. `gatekeeper.py check --manifest {{path}} --contract {{ID}} --reports {{path}}` mechanically enforces this: it requires every command in the contract's Required Verification Commands (below) to actually appear among the report's own declared `## Verification` commands, requires `verify-contract`'s re-execution of every declared command to pass, requires `lint-contract` to pass, requires a well-formed `## Recompute Declaration` block (see Recompute Declaration, existing v1.4.2 field) that itself passes, and requires the report to carry at least one intact Gatekeeper Verification Stamp. Any one of the five failing is exit 17, reported by name. This is the same machinery `verify-contract`/`lint-contract`/`recompute`/`stamp-report` already provided as standalone, opt-in subcommands as of the original v1.4.2 release — the amendment makes them mandatory for this tier rather than adding new checking logic. A T-DESC contract is unaffected.

**(v2.2.0, D-034) Fail-Closed Tier Inference.** Every mechanism above is only as strong as the `scientific_claim_tier` declaration that triggers it — nothing above stops that declaration itself from being too low. `gatekeeper.py tier-check --contract {{ID}}` (also run unconditionally, alongside the Mandatory Mechanical Gate, inside `check`) mechanically infers a *minimum* tier from the contract's own Objective/Context/Implementation Instructions/Outputs text and hard-fails (exit 18) if the declared tier is weaker than that inferred minimum — see Constitution C56 and `dynamic_rules.md` D-034. Declared assurance may exceed the inferred minimum freely; it may never undercut it. `tier-check` also bundles five WARNING-only heuristics that do not affect this gate's exit code but are worth reading in its output: operation-class conflation (D-035 — an Objective describing implementation, alongside language describing an empirical outcome, is worth a second look at whether this contract actually executes the claim); statistical-protocol language (D-036 — non-significance-as-equivalence and undeclared-pairing patterns); semantic/operator-test presence (D-037 — a contract naming a specific mathematical operator, such as a graph Laplacian or a persistent-homology filtration, should carry at least one Verification Script that tests the operator's actual mathematical property, not only its shape; see `domain_checklists.md`); ablation-row covariance (D-054, v2.4.0, candidate — an ablation-table row whose parameter or training-step count differs from its baseline row without a nearby "held fixed" declaration; see `domain_checklists.md`'s Ablation Design section); and efficiency-claim measurement language (D-055, v2.4.0, candidate — latency/throughput/real-time claim language co-occurring with mean-only language and no percentile terms; see `domain_checklists.md`'s Hardware / Efficiency Claims section). D-054 and D-055 are filed PROPOSED, not ACTIVE — see `dynamic_rules.md`'s v2.4.0 entries for why.

## Required Verification Commands (v1.4.2, dated amendment — D-033)

A T-COMP or T-CAUSAL contract declares, at Chunk Planning time alongside its Verification Scripts, the exact command(s) that constitute its required verification — frozen then, like every other Frozen File, not left to be invented later in the contract report:

```
Required Verification Commands:
  - {{exact shell command}}
  - {{exact shell command}}
  ...
```

This closes a gap `verify-contract` alone left open: `verify-contract` proves that whatever command a report declares under `## Verification` really was re-executed and really exited 0 — it does not prove that command was the one the contract actually required. A report could in principle declare a trivially-passing but irrelevant command (`python3 -c "print('PASS')"`) and `verify-contract` would still pass it. `gatekeeper.py check`'s Mandatory Mechanical Gate cross-checks the report's declared `## Verification` commands against this frozen list; any Required Verification Command missing from the report's own declared set is a hard FAIL under the gate, independent of whether every command the report *did* declare passed. A report may declare additional commands beyond what's required — only a missing required one fails this specific sub-check. Field is optional for T-DESC contracts and contracts with no declared `scientific_claim_tier`; write "N/A" explicitly rather than omitting it if a T-COMP/T-CAUSAL contract genuinely has none (this should be rare, and the Mandatory Mechanical Gate will warn, not silently pass, if it's empty on a tiered contract).

---

# Dropbox Specification (v1.1.3, revised v1.2.0)

## Purpose

`DROP_HERE/` is a generic inbox for handing files to the Implementor
without the Human first sorting them into the correct project
path by hand. It exists purely to remove a manual, repetitive, non-
engineering step from the Human's workflow (see C46/C47 — automate
repeated manual activity before adding process for it).

It is **not** a substitute for the Contract or Chunk Specification, and it
does not change what gets built or how it's verified. It only changes how
a file physically gets from "the Human has it" to "it's at the path a
contract expects it to be."

## What it is not

Dropbox Sort never infers a destination from a file's content. Per
C07/EP-002 (determinism over interpretation) and C01 (never fabricate — a
wrong guessed placement silently corrupting a contract's Inputs is exactly
the kind of thing that must never happen quietly), the mapping from
dropped file to destination is always explicit — either a fixed pattern
the Factory already knows, or an entry the Architect wrote deliberately — never a
judgment call made at drop time.

## dropbox_manifest.json (v1.2.0 — now a permanent Factory file)

As of v1.2.0, `dropbox_manifest.json` is **bootstrapped once**, alongside
every other Factory file, and lives in the repository for the project's
entire life. It is not regenerated per chunk. It lives inside `DROP_HERE/`
itself — not in the chunk directory — so it travels with the inbox rather
than being something to go hunting for elsewhere.

It has two parts:

```json
{
  "rules": [
    {"pattern": "^chunk(\\d+)\\.md$",
     "destination": "project/chunks/chunk{1}/chunk{1}.md"},
    {"pattern": "^C(\\d+)-(\\d+)_contract\\.md$",
     "destination": "project/chunks/chunk{1}/contracts/C{1}-{2}_contract.md"}
  ],
  "entries": [
    {"filename": "training_data.csv",
     "destination": "source/data/training_data.csv"}
  ]
}
```

- **`rules`** — fixed, regex-pattern-based, seeded by `bootstrap.sh` at
  project setup and covering every predictable artifact type this Factory
  defines a naming convention for (chunk plans, execution manifests,
  contract files, contract reports, chunk reports, fix packages, and the
  five project-initialization documents). Capture groups in the pattern
  substitute into the destination template via `{1}`, `{2}`, etc. Capture
  group 1 is always the chunk number by convention, and is zero-padded to
  2 digits by `sort-dropbox` regardless of how it was typed, specifically
  so `chunk1.md` and `chunk01.md` can never resolve to two different
  directories. These rules are Factory infrastructure — the Architect and the
  Implementor should not need to edit this section.
- **`entries`** — exact-filename mappings for project-specific, one-off
  handoffs a fixed pattern can't anticipate (a dataset, a credential file,
  anything produced outside the Factory). The Architect appends to this list
  during Chunk Planning whenever a contract's Inputs implies the Human
  will need to hand something over. Exact-filename entries are checked
  before pattern rules, so a project-specific entry can never be shadowed
  by a generic rule.

A dropped file matching neither an entry nor a rule is left exactly where
it is and reported as unresolved — never moved by inference, never
silently ignored.

## Ownership

The `rules` section is written once by `bootstrap.sh` and is not the Architect's
or the Implementor's to modify. The `entries` section is
The Architect's, appended to during Chunk Planning — see `architect_spec.md`
§6. The Implementor only ever reads this file; it never writes
to it.

## Execution

`gatekeeper.py sort-dropbox` performs the actual move: checks `entries`
(exact filename) first, then `rules` (regex pattern, first match wins in
file order), refuses to overwrite an existing destination file without
`--force`, and reports (never silently drops) anything present in
`DROP_HERE/` that matches neither.

This is a Gatekeeper command, not an Implementor judgment call,
specifically so that "which file goes where" stays a deterministic,
auditable, re-runnable operation — same category as Frozen File Validation
— rather than another thing added to what the Implementor must
interpret correctly under full autonomy.

## Relationship to the Mailbox Protocol

`implementor_spec.md`'s Mailbox Protocol is what actually invokes `sort-dropbox`
— triggered by a short, Human-supplied phrase ("check the mailbox," "chunk
N is here, do it") instead of the Human re-finding and re-typing anything.
The protocol runs `sort-dropbox`, then `gatekeeper.py next`, then proceeds
with whichever contract is ready. The trigger phrase is a session-level
convenience, not a Factory rule — it changes nothing about what gets
verified or how.

---

# TAKE_THIS Specification (v1.2.1)

## Purpose

`TAKE_THIS/` is the reverse direction of `DROP_HERE/`: instead of the Human handing files to the Implementor, the Implementor stages a completed chunk's self-contained reports for the Human to grab in one place, rather than the Human hunting through `project/chunks/chunkNN/reports/C{NN}-{seq}/` by hand. Same motivation as Dropbox (C46/C47 — automate repeated manual activity), opposite direction.

It is **not** a substitute for the permanent record. Everything staged here is always a copy; the actual reports remain under `project/chunks/chunkNN/` for the project's entire life.

## What gets staged

`gatekeeper.py stage-takethis --chunk chunkNN` copies exactly two categories of file, scoped deliberately narrow:

- The chunk's own `chunk_report.md`, renamed `chunkNN_report.md`
- Every `contract_report.md` under that chunk's `reports/` directory, renamed `C{NN}-{seq}_contract_report.md`

This reuses the exact same flat naming convention `dropbox_manifest.json` already uses on the way in — a file staged here is, by construction, already correctly named if it were ever dropped into a `DROP_HERE/` elsewhere. `AI_Note.md`, `fix_package.md`, and raw diffs/verification output are deliberately **not** included — those aren't per-chunk self-contained reports in the same sense, and raw artifacts for Medium/High tier contracts still need to reach the Architect separately (see Chunk Review).

## When it's populated and cleared

Populated as the last step of Chunk Report Compilation (see Report Specification), once `chunk_report.md` exists. Cleared by `gatekeeper.py clear-takethis`, run automatically as the first step of the Mailbox Protocol's "chunk N is here, do it" trigger — not the generic "check the mailbox" trigger, which is also used mid-chunk for things like dataset drops, where clearing `TAKE_THIS/` would discard reports the Human hasn't grabbed yet. `clear-takethis` is self-healing (creates the directory if it's missing) and never touches anything under `project/`.

---

# Project Repository Isolation (v1.3.2)

## Purpose

Some Human operators do not want any visible trace, in an outer repository's structure or history, that a project was built using this Factory — no `chunks/`, no `contracts/`, no `dropbox_manifest.json`, nothing that would read as "AI orchestration pipeline" to anyone who clones or browses the repository normally. This is a legitimate, explicit design constraint, not an oversight to be corrected.

`project/` (chunk plans, contracts, reports, decision log, evolution artifacts) is gitignored from the outer repository for exactly this reason. Before v1.3.2, that meant `project/` had **no git history at all** — a real defect, discovered via a Chunk Review that tried to independently verify a file's edit history and found nothing, for a reason that had nothing to do with the specific question being asked. Hiding the Factory's fingerprint and having real, diffable history for `project/`'s own contents are not actually in conflict; they only look that way if `project/` is either fully tracked (visible) or fully untracked (no history). There's a third option.

## The mechanism: a nested, independent repository

`project/` is its own git repository, created by `bootstrap.sh` (`git init` inside `project/`, idempotent — only initialized if `project/.git` doesn't already exist). It is completely independent of the outer repository: different `.git`, different commit history, different (and deliberately ordinary — see below) author identity.

The outer repository's `.gitignore` rule for `project/` means outer git commands (`git status`, `git log`, `git clone`) never see into it at all — not the directory, not its `.git` folder, nothing. Anyone working with the outer repository normally sees source code, tests, and documentation only. `project/`'s own repository, meanwhile, has completely real, complete history for every chunk plan, contract, report, and decision — nothing is lost, it's just scoped to a repository nobody outside ever has reason to open.

**Commit identity matters here.** The nested repository must use the Human's own, ordinary global git identity — never a distinct "Factory" or automation-branded identity (e.g. `Software Factory <factory@local>`). A distinctive identity would be a bigger giveaway than the directory's mere existence, if the nested repository were ever seen by anyone for any reason. There is no deception in this — these are the Human's own engineering notes, and the commit author should say so plainly, the same as any other local repository on their machine.

## What Gatekeeper does with this

**Repository Integrity** (`gatekeeper.py check`) verifies both roots independently: the outer repository's working tree, and — if `project/.git` exists — `project/`'s own working tree, via `git -C project status --porcelain` rather than assuming a single repository root. Both must be clean for the check to pass; either one being dirty fails it, with the specific root named in the failure.

**`gatekeeper.py commit-project`** is the deterministic commit operation for the nested repository — `git -C project add -A && git -C project commit`. Run routinely, after every contract and after chunk report compilation (see Report Specification), not only when something feels significant. Safe to call with nothing staged: it reports "nothing to commit" and exits cleanly rather than erroring, since a no-op is an expected, common outcome for an operation meant to run this often.

**`.gatekeeper/snapshots/` moved inside `project/` too, on reflection.** Frozen File hashing was originally left untouched by this section's first draft, on the reasoning that pure filesystem hashing has no git dependency — true, but beside the point: `.gatekeeper/snapshots/C{NN}-{seq}.json` is exactly as distinctive and Factory-shaped a fingerprint as anything else this section exists to hide, and it was sitting tracked in the outer repository the whole time regardless of git-independence. Gitignoring it separately would have reintroduced `project/`'s original bug — real history silently lost — for a second directory. Instead, `SNAPSHOT_DIR` now points at `project/.gatekeeper/snapshots/`, inheriting the same nested-repo isolation and `commit-project` history `project/` already has, with zero new git machinery. `check`/`next` read the new location first and fall back to the pre-v1.3.2 repo-root location (`.gatekeeper/snapshots/`) if a snapshot isn't found there — read-compatibility only, not an automatic migration, since moving existing files is a decision worth the Human/Architect seeing happen rather than something silent. `sort-dropbox`, `stage-takethis`, `clear-takethis`, `materialize`, and `next`'s manifest/report reads remain plain filesystem operations with no git dependency and needed no changes.

## What this is not

Not a workaround for a Company Repository / Workspace / synchronization architecture. An earlier, more elaborate proposal along those lines (clone the deliverable repo into a private workspace, do all Factory work there, sync approved changes back out) was considered and rejected — it solves the identical problem this section solves, at higher cost, and it introduces exactly the kind of judgment call (*when* is work "approved enough" to sync?) that this Factory works hard to eliminate everywhere else. Nested repository isolation reaches the same end state — outer repository shows source only, `project/` has full real history — with no new decision points for either AI role and nothing to synchronize, ever.

---

# Execution Manifest Specification

The manifest defines

- dependency order
- execution order
- required reports
- verification sequence
- repository preconditions
- clean worktree requirement
- completion dependencies

It is the Factory control plane.

## Schema

Every `execution_manifest.yaml` follows this shape. Fields may not be renamed; contracts may be added but the keys below are the minimum Gatekeeper checks for.

```yaml
chunk: "chunk03"
factory_version: "1.3.4"
weight: "standard"          # or "lightweight" — see Lightweight Chunk Designation

contracts:
  - id: "C03-01"
    risk_tier: "medium"
    implementation_owner: "gemini"
    depends_on: []
    allowed_files:
      - "src/parser/*.py"
    frozen_files:
      - "src/core/schema.py"
    verification_scripts:
      - "tests/test_parser.py"
    required_reports:
      - "contract_report.md"

  - id: "C03-02"
    risk_tier: "high"
    implementation_owner: "claude"
    depends_on: ["C03-01"]
    allowed_files:
      - "src/auth/threshold.py"
    frozen_files: []
    verification_scripts:
      - "tests/test_threshold.py"
    required_reports:
      - "contract_report.md"

execution_order: ["C03-01", "C03-02"]

repository_preconditions:
  clean_worktree_required: true
  previous_chunk_approved: true
  branch: "chunk-03"

completion_dependencies:
  chunk_report_required: true
  gatekeeper_pass_required: true
```

`risk_tier` and `implementation_owner` must agree with the Risk Tier / Implementation Owner table in the Contract Specification — Gatekeeper flags a mismatch as a Manifest Validation failure, not something the Architect re-decides at execution time.

---

# Execution Pipeline

Factory execution always follows this order.

```
Project Initialization

↓

Chunk Planning

↓

Contract Split

↓

Contract Execution ──────┐
                          │
↓                         │ BLOCKED (architectural)
                          │
Validation                │
                          │
↓                         ↓
                    Architecture Amendment
Reporting                 │
                          │ architecture.md revised (versioned,
↓                         │ old version preserved per C30) +
                          │ affected contracts re-split
Chunk Review              │
                          │
↓                         ↓
                    Resume Contract Execution
Knowledge Promotion

↓

Next Chunk
```

No stage may be skipped. Architecture Amendment is not a shortcut around Contract Execution — it is the only path back to it when a contract turns out to be unimplementable because an earlier architectural assumption was wrong (not because the implementation was merely difficult). It is distinct from a Fix Package: a Fix Package repairs an implementation that didn't satisfy its contract; an Architecture Amendment repairs a contract that was wrong to begin with. See "Architecture Amendment" below.

---

# Architecture Amendment

Triggered when Phase 1 planning, Phase 2 implementation, or Phase 3 self-review concludes that a contract cannot be satisfied as written because `architecture.md` (or `invariants.md`) made an assumption that implementation has now disproven — not because the work is merely hard.

Procedure:

1. The Implementor stops and reports `BLOCKED (architectural)` instead of `NOT READY` or `IMPLEMENTATION BLOCKED` — this status is reserved for this specific case so it routes differently than an ordinary contract-level block.
2. The Architect reviews the evidence and either (a) confirms the amendment is needed, or (b) determines the contract can still be satisfied and returns a corrected contract instead.
3. If confirmed, the Architect revises `architecture.md`. The prior version is preserved, not overwritten (C30) — append a dated revision block rather than editing history away.
4. The Architect re-splits every contract that depended on the changed portion of the architecture. Contracts unaffected by the change remain valid and are not regenerated.
5. Execution resumes from the first re-split contract.

An Architecture Amendment is a normal, expected event on any nontrivial project — it is not a Factory failure, and it does not require a Human-approved Factory version change (that gate is for changing *how the Factory works*, not for a project's own architecture evolving under evidence). It does require an entry in `project/evolution/decision_log.md`, same as any other significant decision, per C30.

---

# Phase Specification

## Phase 1

Purpose

Planning.

Outputs

- execution plan
- affected files
- risks
- verification strategy

No implementation.

---

## Phase 2

Purpose

Implementation.

Only Allowed Files may be modified.

Verification should occur continuously.

---

## Phase 3

Purpose

Self Review.

Review

- verification scripts
- invariant compliance
- contract completion
- constitution compliance

Failures return execution to Phase 2.

After 2 consecutive Self Review failures on the same contract using the originally planned approach, the Implementor does not keep repeating that approach unchanged, and — this is the v1.1.1 correction — does not stop and wait for the Architect either. The Architect is not assumed to be reachable mid-chunk (see Human Usage Model below); a hard stop that waits for a review it may not get for days would stall the entire chunk. Instead:

From the 3rd attempt onward, deliberately switch to the most conservative implementation that can still satisfy every Verification Script, every Stop Condition, and every Invariant — even if that falls short of part of the Definition of Done or diverges from the approach suggested in Implementation Instructions. Simpler-but-verifiably-correct beats elegant-but-still-failing.

If, after five total attempts, Verification Scripts still cannot be made to pass cleanly with any honest implementation:

- If a safe, non-fabricated version exists that passes Verification but falls short of the full Definition of Done or has known rough edges: mark the contract `COMPLETE — FLAGGED`, document exactly what's short and why in `contract_report.md`, and continue to the next contract the execution_manifest.yaml's dependency order allows.
- If no version exists that honestly passes Verification: mark the contract `BLOCKED — CARRIED FORWARD`, document every attempt and why each failed, and skip ahead only to contracts that do not depend on this one (per `depends_on` in `execution_manifest.yaml`). Never weaken, skip, or fabricate a pass on a Verification Script to avoid this status — a false `COMPLETE` is a Constitution C01 violation regardless of how much autonomy this section grants.

Every `FLAGGED` or `BLOCKED` contract must appear, prominently, in `chunk_report.md`'s Outstanding Risks section. **That is the actual escalation point** — reviewed by the Architect at Chunk Review (see below), which is a real, expected the Architect touchpoint, not a mid-chunk one. This exists because a model stuck in a fail/retry loop it doesn't understand burns time without making progress, and a hard stop-and-wait for an unavailable reviewer is worse than autonomous, honestly-labeled degradation.

## Human Usage Model

Stated explicitly because several mechanisms in this document assume it: the Architect is used at exactly two points per chunk — generating the chunk's artifacts (`chunkNN.md`, `execution_manifest.yaml`, `contractNN.md` files) at chunk start, and Chunk Review at chunk end. Nothing in Phase 1–4 execution may assume the Architect is reachable in between. Where a contract or chunk turns out to need something only a human can physically do (train a model on hardware the Implementor doesn't have access to, obtain an API key, etc.), that is a different category from an Architect-availability problem — see the Human Action Required convention under Contract Specification.

If Chunk Review finds problems in a completed chunk, the fix is not a separate immediate round-trip. The Architect folds the necessary corrective work into the **beginning** of the next chunk's contract list — e.g., a chunk planned for 8 contracts becomes 12, with the first 4 addressing the prior chunk's findings before the chunk's own 8 begin. This keeps the Architect's involvement to the same two touchpoints per chunk rather than adding a third.

---

## Phase 4

Purpose

Reporting.

Generate

```
contract_report.md
```

Containing

- work completed
- modified files
- verification
- risks
- unresolved issues
- evidence
- clean pass explanation
- model identifier (which Architect/Implementor model version performed the work — see Evolution Specification)

---

# Chunk Review

Chunk Review is the one point in the pipeline where an agent other than the one who did the work is required to look at it. That independence is the entire point, so this section exists to make sure it doesn't quietly collapse into "the Architect reads the Implementor's summary of the Implementor's work."

The Architect's review has two mandatory inputs, not one:

1. `chunk_report.md` and the individual `contract_report.md` files for the chunk (Implementor-authored — context, not evidence).
2. **Raw output for every `Medium` and `High` Risk Tier contract in the chunk**: the actual diff, the actual verification script output, the actual generated artifacts — not the Implementor's description of them. `Low` tier contracts may be reviewed from the report alone unless something in the report looks off.

If a `High` tier contract was implemented by the Architect directly (per the Implementation Owner table), Chunk Review for that contract is instead a second, independent read by the Architect at a later point — not a self-check immediately after writing it. If that's not practical in a given session, flag it as a known limitation in the chunk report rather than silently skipping the independence requirement.

The Architect records, per contract in the chunk: which raw artifacts were actually inspected (not just "verification passed" — the command and output that showed it). This becomes part of what `AI_Note.md` (below) is for.

## AI_Note.md

The Architect's append-only output from Chunk Review, read by the Implementor before the next chunk starts. It exists for the cases too small to justify a full Fix Package: a clarification, a pattern the Architect noticed across multiple contracts worth avoiding next time, a note that a Risk Tier looked mis-assigned. If the finding is severe enough to require rework, it's a Fix Package instead — `AI_Note.md` is for everything short of that. Never overwritten; each entry is dated and chunk-tagged.

## Chunk Review Decision

Same two-outcome structure as everywhere else in the Factory:

```
APPROVED
```
or
```
FIX PACKAGE
```

`APPROVED` requires every Medium/High contract's raw artifacts to have actually been inspected per this section — not merely that a report claiming PASS exists.

## Scientific Validity Checks (v1.4.0)

Three additional mandatory checks, for any project with `venue_requirements.md`:

1. **Methodology Drift Check** — has any contract's execution subtly changed the methodology (aggregated features instead of raw pixels, fewer baselines than declared, a changed evaluation protocol)? Compare against `venue_requirements.md` and the SVI invariant category.
2. **Baseline Completeness Check** — are all `venue_requirements.md`-declared baselines actually implemented and run? A missing one is a Fix Package finding, not a note for later.
3. **Title-Claim Audit** — re-check every anticipated title adjective against its validating experiment. If a chunk's results invalidate a claim, flag it immediately — don't let it ride to the writing phase and get reframed there (D-016).
4. **(v1.4.1) Verdict Cross-Check completeness** — does every contract report carrying a pre-registered verdict actually include a `## Verdict Cross-Check` block, and has `gatekeeper.py evidence-check` been run against it? A missing block is not automatically checked, so this is the human backstop against a T-CAUSAL contract shipping without one (D-024).
5. **(v1.4.1) Cross-Contract Metric Supersession** — does any contract this chunk re-evaluate metrics an earlier contract already reported? If so, is the supersession explicitly documented per the section above (D-026)?

## Fix Package Structure (v1.1.2)

`fix_package.md` is referenced throughout this document (Chunk Review Decision, Architecture Amendment, `AI_Note.md`) but was never given a structure. The Architect authors it; the Implementor executes only what it contains:

```
# Fix Package — Chunk {{CHUNK_ID}}

## Affected Contracts
{{list of contract IDs this fix package touches}}

## Findings
For each: what's wrong, evidence (the actual diff/output that shows it, not
a description of it), severity.

## Required Changes
Specific, scoped instructions — same rigor as Contract Specification's
Implementation Instructions. Not "improve this" — exactly what changes.

## Acceptance Criteria
How the Architect will know the fix worked at the next Chunk Review.

## Verification Required
Which Verification Scripts (existing or new) must pass.
```

Per the Human Usage Model, this doesn't get executed as a separate round-trip — its contents become the first contracts of the next chunk (see Human Usage Model).

---

# Report Specification

Reports are engineering artifacts.

Every report prioritizes

- raw evidence
- reproducibility
- commands executed
- generated artifacts
- failures
- deviations
- verification

Narrative follows evidence.

**Chunk reports restate open Human Actions in full (v1.3.0):** a chunk report covering a still-unresolved `Human Action Required` contract restates that contract's exact `Action` text, in full imperative form, in the chunk report itself — not a cross-reference back to the original chunk plan. The chunk report is what the Human actually reads at the point the action becomes possible; by then the original plan may not be close at hand. See Contract Specification's Human Action Required section.

**Chunk reports get staged for handoff (v1.2.1):** once a chunk report exists, `gatekeeper.py stage-takethis --chunk chunkNN` copies it and every contract report for that chunk into `TAKE_THIS/` for the Human — see TAKE_THIS Specification. The full templates for `contract_report.md` and `chunk_report.md`, including the Plain-Language Summary and self-containment requirement, live in `implementor_spec.md`, not here, since they're read and applied by the Implementor directly.

---

# Evolution Specification

The evolution folder improves the Factory.

Never the project.

Contains

```
telemetry.jsonl

decision_log.md
```

`evolution.md`, `experiments.yaml`, and `metrics.csv` were removed from this list in v1.3.4: zero writes across two completed real projects (RateLimiter, TeamNotes) failed C46's "must earn its place" test, and `telemetry.jsonl` plus `decision_log.md` already cover the stated space. See `CHANGELOG.md`'s v1.3.4 entry.

Logging is continuous.

Never delayed until project completion.

---

## telemetry.jsonl

Machine readable event stream.

One JSON object per event.

Append only.

### Schema

```json
{
  "timestamp": "2026-07-18T10:32:00Z",
  "chunk": "chunk03",
  "contract": "C03-02",
  "risk_tier": "high",
  "implementation_owner": "architect",
  "phase": "phase_2",
  "event": "verification_run",
  "status": "pass",
  "model_id": "claude-sonnet-5",
  "model_version": "2026-06-01",
  "duration_seconds": 47,
  "verification_script": "tests/test_threshold.py",
  "self_review_attempts": 1,
  "violations": []
}
```

`model_id` and `model_version` are required on every event that involved generating or reviewing content (not on pure filesystem/Gatekeeper events). This exists because "same contract, same prompt, different underlying model" can produce materially different code — reproducibility claims (C27, EP-006) are hollow without recording which model actually did the work.

`self_review_attempts` (v1.3.4 — added to this canonical schema; previously only in `implementor_spec.md` §7's template, an undisclosed asymmetry) records which Self Review attempt (1–5, per the Self Review ceiling) produced this event. Present on `contract_complete` events; optional elsewhere.

This document is the sole authoritative owner of the `telemetry.jsonl` schema (v1.3.4, DRIFT-5). `implementor_spec.md` §7's template must match this schema exactly rather than maintaining its own divergent field set — if the two ever disagree, this schema wins and `implementor_spec.md` is the one that's wrong.

The `approved` field previously appearing in this schema has been removed (v1.3.4): it had no type, semantics, or owner defined anywhere across the Factory's documents. A field with no defined meaning is worse than no field — reintroduce it only with a precise type, a stated owner (who sets it, and when), and a stated consumer (what reads it and acts on the value).

**Architect logging requirement (v1.3.0):** the schema above already supports `"implementation_owner": "architect"` and always has — but in practice, a completed `High` tier contract the Architect implements directly has produced zero `telemetry.jsonl` entries, since only the Implementor's own execution path was actually appending to this file. The Architect must append its own entry, using this same schema, when it completes a `High` tier contract it implemented itself — otherwise a chunk's telemetry record is silently incomplete for exactly the highest-risk work in it. See `dynamic_rules.md` D-005.

---

## decision_log.md

Records

- decision
- reason
- alternatives
- expected benefit

**Not only the Implementor's decisions (v1.3.0):** the Architect logs here too, for its own significant decisions during Chunk Planning or Chunk Review (e.g. an architecture choice, a Risk Tier judgment call, a decision to deviate from a template) — the same four fields, the same append-only file. This is intentionally the same document both roles use, not a separate Architect-only equivalent (an ADR system, a second log) — one running record of "why was this decided" is more useful than two that might drift apart, and the Factory's own closing principle (Design Philosophy) is explicit that a new artifact needs a real failure it prevents before it's added; splitting this into two files doesn't have one.

Append only.

---

# Gatekeeper Specification

Gatekeeper performs deterministic validation only.

Allowed

- file hashes
- required files
- manifest integrity
- repository cleanliness
- verification scripts
- frozen files
- report existence
- execution order

Forbidden

- AI reasoning
- code review
- architecture judgement
- quality scoring
- semantic interpretation

---

# Artifact Lifecycle

Every artifact has one owner.

| Artifact | Owner | Created | Modification Policy | Primary Consumer |
|----------|---------|----------|---------------------|------------------|
| constitution.md | Human | Factory creation | Rare | Everyone |
| factory_spec.md | Human | Factory creation | Rare | Architect |
| dynamic_rules.md | Human | Promotion | Append only | Everyone |
| project_description.md | Architect | Project init | Frozen | Everyone |
| architecture.md | Architect | Project init | Frozen | Everyone |
| roadmap.md | Architect | Project init | Frozen | Architect |
| project_knowledge.md | Architect | Project init | Append if needed | Everyone |
| invariants.md | Architect | Project init | Architect controlled | Everyone |
| chunkNN.md | Architect | Chunk planning | Frozen | Architect (self, for the split step) |
| contractNN.md | Architect | Contract split | Frozen | Implementor |
| execution_manifest.yaml | Architect | Chunk planning | Frozen | Gatekeeper |
| contract_report.md | Implementor | Phase 4 | Frozen after completion | Architect |
| chunk_report.md | Implementor | Chunk completion | Frozen | Architect |
| AI_Note.md | Architect | Review | Append only | Implementor |
| telemetry.jsonl | Implementor, Architect | Continuous | Append only | Factory |
| decision_log.md | Implementor, Architect | Continuous | Append only | Future Projects |
| venue_requirements.md | Architect | Project init | Frozen | Architect (MAR), Implementor (Reality Gate) |
| project/key_facts.md | Architect | Project init | Frozen (Architecture Amendment only) | gatekeeper.py release-check |
| methodology_adversarial_review.md | Architect (self-adversarial by default) or an outside reviewer, per C55 | MAR | Frozen after MAR completes | Architect |
| data_manifest.json | Implementor | Data-acquisition contract | Frozen after Reality Gate passes | Reality Gate |
| reality_gate_report.md | Reality Gate (currently manual — see Scientific Validity Specification) | After data acquisition | Frozen | Architect |

`experiments.yaml`, `metrics.csv`, and `evolution.md` were removed from
this table in v1.3.4: zero writes across two completed real projects
(RateLimiter, TeamNotes) fail C46's "must earn its place" test, and
`decision_log.md` plus `telemetry.jsonl` already cover the stated space.
See `CHANGELOG.md`'s v1.3.4 entry and `dynamic_rules.md`'s Candidate
Observations table. The five v1.4.0 rows above are new — each has a real
producer/consumer instruction in `architect_spec.md` and/or
`implementor_spec.md`, not just a table row (see D-011 through D-018 and
`gatekeeper_spec.md`'s note that self-check's Artifact Lifecycle diff
target would otherwise flag exactly this kind of gap).

---

# Knowledge Promotion

Promotion occurs only after evidence.

Pipeline

```
Observation

↓

Repeated Pattern

↓

Evidence

↓

Promotion Proposal

↓

Human Approval

↓

dynamic_rules.md
```

Ideas never qualify.

Evidence is mandatory.

---

# Factory Retrospective

Performed only after project completion.

Questions

- Which rules prevented failures?
- Which reports were unused?
- Which contracts caused repeated problems?
- Which automation saved the most work?
- Which manual steps remain?
- Which Dynamic Rules deserve promotion?
- Which gatekeeper checks never triggered?
- Which Factory components should be simplified?

The retrospective improves the Factory.

Not the completed project.

---

# Versioning

Patch

```
v1.0.x
```

Clarifications.

Bug fixes.

No workflow change.

---

Minor

```
v1.1
```

Evidence backed workflow improvements.

---

Major

```
v2.0
```

Architectural redesign.

---

# Backward Compatibility

Whenever practical,

new Factory versions should continue understanding artifacts generated by previous versions.

Older projects should remain reproducible without migration whenever possible.

---

# Design Philosophy

The Factory minimizes future decision making.

Every reusable improvement should move from

Human memory

↓

AI memory

↓

Documentation

↓

Automation

↓

Deterministic verification

The highest maturity is achieved when correctness no longer depends on remembering to do the right thing.

# Project Bootstrap Specification

The Project Bootstrap Specification defines how every new project is initialized.

Its purpose is to ensure every project begins from a known, reproducible structure.

Initialization is deterministic.

No project-specific assumptions are made during bootstrapping.

---

# Responsibilities

The Architect is responsible for bootstrapping the project.

Bootstrapping includes

- creating the required directory structure
- generating required artifacts
- verifying existing artifacts
- reporting missing or inconsistent artifacts

Bootstrapping does not include implementation.

---

# Bootstrap Manifest

Every project begins with

```
bootstrap_manifest.yaml
```

This manifest defines the required repository structure.

It is the single source of truth for project initialization.

---

# Bootstrap Procedure

Initialization always follows this order.

```
Read bootstrap_manifest.yaml

↓

Verify repository structure

↓

Create missing directories

↓

Create missing files

↓

Verify existing artifacts

↓

Report inconsistencies

↓

Project Initialization
```

No implementation may begin before bootstrap succeeds.

---

# Directory Creation

Directories listed in the manifest must exist.

If missing

↓

Create them.

If already present

↓

Leave unchanged.

Directories must never be recreated if they already exist.

---

# File Creation

Required artifacts listed in the manifest must exist.

If missing

↓

Generate them.

If already present

↓

Do not overwrite.

Instead

↓

Verify consistency.

---

# Existing Projects

When bootstrapping an existing repository

- never overwrite existing work
- never regenerate completed artifacts
- create only missing components
- report inconsistencies

Bootstrap must always be safe to run.

---

# Idempotency

Project Bootstrap is idempotent. This is a hard requirement, not an aspiration: `bootstrap_manifest.yaml`'s `idempotent` field must be `true`, and `bootstrap.sh` must actually implement gap-filling behavior (check each required directory/file individually; create only what's missing; verify and report on what already exists) rather than refusing to run whenever anything is already present. In v1.0.1 these three things — the prose here, the manifest field, and the script — disagreed with each other; that inconsistency is fixed in this version. If `bootstrap.sh` is ever changed back to strict/one-shot behavior, this section and the manifest field must be updated in the same change, not left to drift again.

Running bootstrap multiple times must produce the same repository state.

Repeated execution must never

- delete files
- duplicate artifacts
- overwrite completed work
- modify frozen artifacts

---

# Verification

Bootstrap verifies

- required directories exist
- required artifacts exist
- manifest integrity
- factory version compatibility
- repository structure

Verification is deterministic.

---

# Bootstrap Report

After initialization the Architect reports

- directories created
- files generated
- files already present
- inconsistencies detected
- actions skipped

No hidden modifications are allowed.

---

# Ownership

Bootstrap Manifest

Owner

Human

Bootstrap Execution

Owner

The Architect

Verification

Owner

Gatekeeper

Approval

Owner

Human

---

# Failure Conditions

Bootstrap fails if

- manifest cannot be parsed
- required artifact cannot be generated
- repository structure is inconsistent
- factory version is incompatible

Implementation must not begin until bootstrap succeeds.