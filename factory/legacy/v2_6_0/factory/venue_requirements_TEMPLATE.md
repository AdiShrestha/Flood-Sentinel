# Venue Requirements

Status: Frozen File (same policy as architecture.md — see C43, C50's Backward Compatibility
section). Created at Project Initialization. Reviewed at MAR (`methodology_adversarial_review.md`).
Checked for drift at every Chunk Review's Methodology Drift Check and Baseline Completeness Check.

This document exists to give the Architect an external reference point. A specification with no
external reference point is incomplete (C52).

---

## Target Venue

{{VENUE_NAME}} — e.g. IEEE Transactions on Geoscience and Remote Sensing (TGRS)

## Recent Venue Publications (minimum 3, required — MAR-5 fails without these)

Fill with real papers, read closely enough to extract these fields honestly. Do not fabricate
entries or approximate from memory alone (C01, C08) — locate and read the actual paper.

| Paper | Year | Methodology | Baselines used | Sample size | Key convention worth matching |
|---|---|---|---|---|---|
| {{citation 1}} | | | | | |
| {{citation 2}} | | | | | |
| {{citation 3}} | | | | | |

## Minimum Expected Baselines For This Venue (4 Essential Classes — MAR-2)

Elite venues (CVPR, NeurIPS, Nature MI) require baseline portfolios spanning four distinct conceptual classes, not merely convenient comparisons:

1. **Sanity / Trivial Baseline**: Detects whether the task is inherently trivial, linear, or dataset-biased (majority class, nearest-neighbor, linear regression). Nature Portfolio explicitly includes trivial baselines.
2. **Canonical Historical Baseline**: The recognized historical standard architecture/algorithm everyone in the subfield references.
3. **Strong Contemporary SOTA Baseline**: High-performing, peer-reviewed model from the last 2 years (2024–2026) under identical task and compute bounds.
4. **Mechanism-Matched Competitor**: Directly tests the claimed novelty against the closest alternative mechanism (e.g. if novelty is routing, compare against alternative routing; if loss, compare against competitive losses). Include incumbent non-ML production methods where applicable.

Fewer than 3 distinct baseline classes or absence of a contemporary SOTA baseline causes an automatic MAR-2 FAIL at Project Initialization.


## Baseline Parity Ledger (v2.4.0, extended v2.4.1 — complete for every T-COMP/T-CAUSAL baseline before Chunk 01)

A baseline category count (above) answers "are there enough baselines." This answers a different
question: "was each one given a fair chance." For every principal baseline this project will
compare against, fill in what's actually knowable before Chunk 01 begins (leave a row blank with
"TBD — depends on [contract]" if it genuinely can't be known yet, rather than guessing):

| Dimension | Baseline | Proposed | Parity established? | Tolerance |
|---|---:|---:|---|---|
| Train examples | | | | exact match preferred |
| External/pretraining data | | | | |
| Augmentation | | | | |
| Optimizer/scheduler | | | | |
| Training steps/epochs | | | | |
| HPO trials / HPO compute | | | | |
| Parameters | | | | ±2% |
| MACs/FLOPs | | | | ±5% |
| Training accelerator-hours | | | | ±5% |
| Precision | | | | exact match |

**If comparing against an architecture with an existing published number**, also declare these
three, so an improvement from the proposed method is separated from an improvement that's really
just five years of better training recipes applied to an old architecture:

- `Old_published`: {{the number as originally reported by that baseline's own paper}}
- `Old_modernized`: {{same baseline architecture, re-run with this project's own current
  optimizer/augmentation/training practice}}
- `Proposed_matched`: {{the proposed method, matched to the baseline on the dimensions above}}

**(v2.4.1) Three more items belong in this ledger:**

- **Reimplementation validation.** If a baseline is reimplemented rather than run from the
  original authors' code/checkpoint, report the reimplementation's score against the *originally
  published* number on the *original* benchmark first, as a sanity check, before showing it in
  this project's own setting: {{reimplementation validation result, or "N/A — original
  authors' code/checkpoint used directly"}}.
- **Baseline provenance.** Exact commit hash / version of every baseline implementation and
  checkpoint used, the same way this project's own generated artifacts are already required to
  carry provenance (C17): {{baseline name: commit hash/version, for each}}.
- **Cross-hardware-generation note.** If a baseline was originally benchmarked on older hardware,
  FLOPs parity alone is not sufficient — FLOPs and real latency can diverge sharply depending on
  hardware parallelism. Was the baseline re-run on this project's own hardware for a real
  wall-clock comparison, rather than relying on FLOPs normalization as a substitute? {{Y/N, and
  where the measurement lives if Y — see `venue_requirements.md`'s Efficiency Claim Requirements
  section and `domain_checklists.md`'s Hardware / Efficiency Claims section for the same reasoning}}

A ledger row left blank because the information genuinely isn't available yet is not itself a
problem — an unfilled row silently treated as "close enough" without anyone checking is. Revisit
this table at Chunk Review's Baseline Completeness Check (`architect_spec.md` §5c) once the actual
baseline implementations exist, not only at Project Initialization when it's still a plan.

## Minimum Expected Sample Sizes

Set real numbers for this project, derived from the venue table above and the actual data
available — not copied from a generic template:

- Evaluation units (lakes / subjects / sessions / whatever the unit is): {{N}}
- Synthetic/injected instances per condition, if applicable: {{N}}
- Real events available for retrospective validation: {{N}} — if this is fewer than 3, state the
  implication for what claims are and aren't supportable up front, here, not after the paper is
  written.

## Statistical Method Requirement

For every comparative (T-COMP) or causal (T-CAUSAL) claim this project will make, name the specific
statistical method that will support it (bootstrap CI, permutation test, paired significance test,
cross-validation with reported variance). A raw point estimate with no method named here is not
sufficient evidence for a T-COMP or T-CAUSAL claim (SVI-003) — a sample count above the minimum
threshold is necessary but not sufficient; the method itself must exist and be named.

## Minimum Meaningful Effect Size

For every T-CAUSAL claim's core metric, state not just the null/below-chance threshold (AUC-ROC ≤
0.5, no significant correlation) but the minimum value that would count as *meaningful*, not just
*technically above chance*. A result that clears 0.5 but sits far below this line is still a
Constitution C53 Stop Condition, not a positive finding to report and move past.

| Core metric | Below-chance threshold | Minimum meaningful value | Basis for the meaningful threshold |
|---|---|---|---|
| {{e.g. AUC-ROC, primary detection task}} | 0.5 | {{e.g. 0.65}} | {{cite the venue table above, or a domain-standard threshold — not an arbitrary round number}} |

## Pre-Registered Falsification Criteria

For each core hypothesis, state what result would falsify it and what action follows — declared now,
before anyone has an incentive to rationalize a disappointing number after the fact. This is
distinct from MAR-7 (what's publishable if the hypothesis fails): this answers what result changes
the methodology *mid-project*, not what's salvageable at the end.

| Hypothesis | Falsifying result | Action if falsified |
|---|---|---|
| {{e.g. "TS-MAE detects precursors"}} | {{e.g. "Score-C AUC-ROC < 0.65 on real-event retrospective"}} | {{e.g. "Reframe as feasibility study, do not claim detection"}} |

If a falsifying result occurs and is not caught here, Constitution C53 is the fallback — but a
declared criterion is the stronger, earlier form of the same protection, and costs nothing to write
down before the experiment runs.

## Required Ablation Types

State which apply to this project's architecture:

- Sensor/channel ablation
- Architecture ablation (if a novel architecture)
- Threshold/hyperparameter sensitivity analysis — name every hyperparameter that will need one
  (D-018): {{list}}

Every ablation this project runs is subject to `domain_checklists.md`'s Ablation Design questions
(v2.4.0) at Chunk Review — in particular, whether each row changes exactly one factor relative to
the baseline row. State here, if already known, which of the ablations above are likely to
covary more than one factor (e.g. removing an architectural module that also changes parameter
count) so the Implementor can plan a "held fixed" declaration or a re-tuned counterpart ablation
from the start rather than discovering the confound at Chunk Review.

## Efficiency Claim Requirements (v2.4.0 — skip entirely if no efficiency/real-time/latency/
throughput claim is anticipated; most projects will skip this section)

Fill in only if this project's title, abstract, or Title/Claim Conventions table (below) uses a
word like "real-time," "low-latency," "efficient," "lightweight," or makes any throughput/memory
claim. See `domain_checklists.md`'s Hardware / Efficiency Claims section (v2.4.0) for the
reasoning behind each line.

- Named hardware/software stack: {{exact accelerator, driver, framework versions}}
- Latency protocol: {{batch=1 percentile distribution — p50/p90/p99}} + {{throughput at a
  realistic batch size, reported separately}}
- Memory reporting: {{peak training memory}} / {{peak inference memory}} — method named, includes
  activation memory
- FLOPs/MACs tool (if reported): {{named, versioned}} — reported alongside, never instead of,
  a measured latency number
- Sustained-load behavior (if edge/thermally-constrained hardware is in scope): {{tested? Y/N,
  protocol}}
- `hardware_profile_manifest.json` (D-056) location once measured: {{path, or "not yet
  measured — planned for chunk {{NN}}"}}

## Expected Data Properties (feeds Reality Gate — do not skip this)

State real, domain-grounded expectations now, before any data is acquired. Reality Gate checks
actual data against these numbers; a threshold invented after seeing the data is not a real gate.

**Domain grounding requirement:** every number below must cite one of: **(a)** a peer-reviewed
publication reporting the same statistic for the same sensor/region/season, **(b)** the sensor's
documented revisit cycle plus known regional climatology, or **(c)** a prior dataset from the same
region with documented completeness. "Architect's estimate" is not a valid basis. If none of (a)–(c)
is available, write "UNKNOWN — Reality Gate will use conservative defaults" explicitly, and flag it
as an MAR-6 finding — an unfounded number silently treated as ground truth defeats the entire
purpose of this section.

- Expected missing-data / gap rate for this domain, region, and season: {{N}}% — basis: {{(a)/(b)/(c), cited}}
- Expected temporal coverage: {{date range}}
- Expected sensors/channels present: {{list}}
- Expected revisit frequency (feeds `acquisition_provenance.json`'s scene-count consistency check): {{e.g. "6-day nominal for Sentinel-1 dual-satellite operation"}} — basis: {{cited}}
- Any property whose real-data value being *suspiciously better than expected* (e.g. suspiciously
  complete, suspiciously uniform) should itself be treated as a red flag, not a convenience: state
  which properties, and why, here.

## Title/Claim Conventions

- Every adjective in the eventual title must correspond to a specific, named experimental test —
  list the adjectives you expect to use and the test each one requires, now, before writing begins:

| Anticipated title adjective | Required validating test |
|---|---|
| {{e.g. "cloud-robust"}} | {{e.g. must be tested against cloud-contaminated inputs, not simulated features}} |
| {{e.g. "real-time"}} | {{e.g. latency measurement under realistic load}} |
| {{e.g. "precursor detection"}} | {{e.g. successful detection on ≥1 real event, with the threshold declared before the test runs, not chosen afterward}} |

## Release Documentation (v2.4.0 — skip entirely if this project releases neither a trained
model nor a constructed/repackaged dataset; most course-scale projects will only need the first
line, if that)

- Model Card completed for {{model name}}, per Mitchell et al. 2019? {{Y/N — link, or "N/A — no
  model released"}}
- Datasheet completed for {{dataset name}}, per Gebru et al. 2018, if constructed or repackaged
  from existing sources? {{Y/N — link, or "N/A — no constructed dataset released"}}
- Disaggregated evaluation across relevant subgroups (region, season, sensor, or whatever
  dimension this domain's failure modes cluster on) included, not only an aggregate metric?
  {{Y/N — which dimension(s)}}

## Foundation Model Benchmark Contamination Audit (v2.5.0, D-059 — skip if not using/evaluating foundation models)

- Target Benchmark Creation Date: {{YYYY-MM-DD}}
- Model Pretraining/Instruction Cutoff Date: {{YYYY-MM-DD}} (must strictly precede benchmark creation)
- Contamination Check Executed via `gatekeeper.py contamination-check`: {{PASS / FAIL / N/A}}
- Exact 13-gram substring matches against training/prompt corpora: {{count, must be 0}}
- Contamination audit artifact location: {{project/contamination_audit.json}}

## Generalization Ladder Target Declaration (v2.5.0, D-061)

Every empirical project must specify the highest rung of the Generalization Ladder evaluated and supported by experiments:

- Target Ladder Rung: {{Rung 1 (In-Distribution) / Rung 2 (Disjoint Split) / Rung 3 (Cross-Dataset) / Rung 4 (Perturbation Ladder) / Rung 5 (Adversarial Curve) / Rung 6 (Failure Taxonomy)}}
- Cross-Dataset / External Benchmark Name: {{name and citation, required if claiming "generalizable" or submitting to Nature Portfolio}}
- Corruption Severity Matrix Defined: {{list corruptions and levels, required if claiming "robust"}}
- Adversarial Budget Curve Plotted: {{ε range, required if claiming security/defense}}
- Structured Failure Case Taxonomy Included: {{Y/N, clustering of error modes across subgroups}}

## Release Artifact Notes

Any known personal-machine paths, credentials, or internal-only identifiers that must not appear in
anything targeted for external release: {{list, or "none identified at initialization — re-check at
release via gatekeeper.py release-check"}}

---

## Statistical Inference Protocol (v2.6.0, D-062/D-063/D-064 — required for T-COMP/T-CAUSAL)

For every comparative or causal claim, declare the statistical test, effect-size measure, and
multiplicity correction up front. This section is verified by `gatekeeper.py verify-statistical-protocol`.

### Significance Test Selection

| Comparison Type | Test | Justification |
|---|---|---|
| Paired seeds on single dataset | {{e.g. Wilcoxon signed-rank, paired t-test}} | {{why this test matches the pairing and distribution}} |
| >2 methods across multiple datasets | {{e.g. Friedman + Holm post-hoc}} | {{cite Demšar 2006 or justify}} |
| Equivalence/non-inferiority claim | {{e.g. TOST with Δ = ±X}} | {{why this margin is meaningful}} |

### Effect Size Reporting

For every p-value reported, the following will also be reported:
- Effect-size measure: {{Cohen's d / Hedge's g / paired difference with CI / other}}
- Minimum practically important threshold: {{declared in "Minimum Meaningful Effect Size" above}}
- Confidence interval type: {{bootstrap CI / t-distribution CI / other}}, level: {{95%}}

### Multiplicity Correction

- Primary contrasts (exempt from correction): {{list the pre-declared primary hypotheses}}
- Correction method for secondary/exploratory: {{Holm / Benjamini-Hochberg FDR / other}}
- Total planned pairwise comparisons: {{N}}

### Small-N Reporting (if N < 10 seeds/runs)

- Aggregation method: {{IQM with stratified bootstrap CI / median + IQR / other}}
- Confidence interval method: {{bootstrap CI, percentile method, B=10000 / other}}

---

## Sensitivity Analysis Plan (v2.6.0, D-065 — required for T-COMP/T-CAUSAL)

For every hyperparameter feeding a core claim, declare the perturbation grid. Verified by
`gatekeeper.py verify-sensitivity-analysis`. A `sensitivity_analysis_manifest.json` should be
created when results are available.

| Hyperparameter | Scale | Perturbation Grid | Expected Response |
|---|---|---|---|
| {{e.g. learning_rate}} | log | h × {0.5, 0.75, 1.0, 1.5, 2.0} | {{monotonic / peaked / plateau}} |
| {{e.g. hidden_dim}} | linear | h × {0.50, 0.75, 0.90, 1.00, 1.10, 1.25, 1.50} | {{plateau expected}} |

### Architecture Sensitivity (at least one variation beyond published config)

| Axis | Variations | Rationale |
|---|---|---|
| {{e.g. backbone family}} | {{ResNet-50 / ViT-B / Swin-T}} | {{tests architecture generality}} |
| {{e.g. with/without pretraining}} | {{random init / ImageNet pretrained}} | {{tests pretraining dependence}} |

---

## LLM Usage Declaration (v2.6.0, D-072 — mandatory for all venues)

NeurIPS 2026 checklist item 16, CVPR 2026 author guidelines, and IEEE policy require disclosure
of any Large Language Model usage in the research process. Complete this section honestly.

- LLM used in methodology/data processing: {{Y/N — if Y, describe role}}
- LLM used in code generation: {{Y/N — if Y, name model and describe scope}}
- LLM used in evaluation prompt design: {{Y/N — if Y, describe}}
- LLM used in manuscript writing/editing: {{Y/N — if Y, describe scope}}
- LLM model(s) and version(s): {{e.g. Claude 3.5 Sonnet, GPT-4o, Gemini 2.5 Pro}}
- Disclosure included in paper methodology section: {{Y/N — required before release}}

---

## Calibration Analysis (v2.6.0, D-073 — required if confidence-dependent deployment claimed)

Skip this section if the project makes no claims about model confidence, uncertainty, or selective
prediction. Required if any of: "high-confidence predictions," "uncertainty-aware," "selective
prediction," "confidence thresholding."

- Calibration metric(s): {{Expected Calibration Error (ECE), Adaptive ECE, other}}
- Reliability diagram: {{planned for chunk {{NN}}, or N/A}}
- Confidence-vs-accuracy analysis across: {{subgroups, severity levels, conditions}}
- Post-hoc calibration applied: {{temperature scaling / Platt scaling / isotonic / none}}

---

## Failure Taxonomy Schema (v2.6.0, C69, D-071 — required for robustness/generalization/deployment claims)

Skip this section if no robustness, generalization, or deployment claim is anticipated. Verified
by `gatekeeper.py verify-failure-taxonomy`. A `project/failure_taxonomy.json` should be created
when results are available.

### Planned Failure Categories (minimum 3)

| Category | Expected Mechanism | Measurement |
|---|---|---|
| {{e.g. occlusion failures}} | {{partial object occlusion}} | {{P(failure \| occlusion > 50%)}} |
| {{e.g. rare class errors}} | {{class imbalance}} | {{P(failure \| class freq < 1%)}} |
| {{e.g. sensor noise}} | {{low-SNR conditions}} | {{P(failure \| SNR < 10dB)}} |

### Selection Rule for Displayed Examples

How failure examples will be chosen for the paper: {{e.g. "random sample from worst decile of
predictions," "highest-confidence errors," "stratified sample across categories"}}

### Comparative Analysis

- Will failures be compared between baseline and proposed method: {{Y/N}}
- Unique failure modes (does the proposed method introduce failure types absent in the baseline): {{to be analyzed}}

---

## Venue-Specific Checklist (v2.6.0 — fill the applicable venue section only)

### NeurIPS Checklist Items (if targeting NeurIPS)

- Contribution type: {{Empirical / Methodological / Negative Results / Theory}}
- NeurIPS Paper Checklist completed: {{Y/N — must be YES for submission}}
- Compute reporting (total GPU-hours + CO2 estimate): {{planned for section {{X}}}}
- Broader Impact statement: {{planned / not required for this contribution type}}
- Code + data availability commitment: {{anonymous repo at review, public at acceptance}}

### CVPR / ICCV Checklist Items (if targeting CVPR/ICCV)

- Novelty vs closest prior art explicitly stated: {{section {{X}} paragraph {{Y}}}}
- Rebuttal preparation: {{strongest anticipated reviewer objection and response sketch}}
- Supplementary material: {{what goes in supplementary vs main paper}}

### Nature Machine Intelligence / Nature Portfolio (if targeting Nature MI)

- Significance-to-broad-readership paragraph: {{planned for introduction}}
- 3500-word limit compliance: {{estimated word count: {{N}}}}
- Cover letter topics: {{significance, fit to scope, suggested reviewers}}
- External validation dataset: {{required — name: {{dataset}}, source: {{citation}}}}

### IEEE (TPAMI, TGRS, etc.) / INFOCOM (if targeting IEEE venues)

- Journal-level expanded methodology: {{difference from conference version, if applicable}}
- Triple-blind compliance (INFOCOM): {{no author-identifying info in paper or supplementary}}
- External supplementary links (INFOCOM): {{prohibited — all content in submission package}}
- Real protocol implementation (INFOCOM): {{if networking paper, real testbed or NS-3/Mininet}}

