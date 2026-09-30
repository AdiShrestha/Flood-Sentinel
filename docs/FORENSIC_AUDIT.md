# Forensic audit of the supplied v2.6 test project

This is an independent read-only audit. It does not import the test project's model, training, analysis, or hardware modules. `docs/audit_tools/audit_v26_project.py` reads Parquet with PyArrow, computes standard metrics with scikit-learn, extracts the original metric function with Python AST, and cross-references taxonomy IDs. Its output is `docs/v26_forensic_results.json`.

## What is established from bytes

- 50 run manifests were inspected. All recorded `epochs` as 2 and all had 12 prediction rows.
- Recomputed Mann–Whitney AUROC disagreed with the recorded AUROC in 43 runs. The source function assigns rank in the opposite direction, so a perfect positive ordering can be recorded as AUROC 0.0.
- The project’s `auprc` function is threshold precision/recall logic, not standard average precision. It disagreed with standard average precision in 26 runs. V3 calls the metric `average_precision` and tests exact positive, reversed, and tied cases.
- Six files contain only 0.0/1.0 probabilities. Four runs are below chance after correct AUROC recomputation, while 39 are below chance in the stored metric field. Both are diagnostics; neither is silently reframed as support.
- There are 24 unique candidate IDs in predictions. Four IDs in `project/failure_taxonomy.json` are absent: `cand_aml_fan_009`, `cand_aml_ring_k6_004`, `cand_aml_ring_k7_012`, and `cand_aml_ring_temp_021`.
- `source/scripts/build_failure_taxonomy.py` writes a literal taxonomy without reading `predictions_dir`; `source/src/analysis/hypothesis_evaluator.py` has a synthetic fallback; `source/scripts/profile_hardware_energy.py` uses `create_mock_batch()` and estimates memory with multipliers while writing fixed energy/thermal fields. The v3 migration gate therefore accepts none of these artifacts as evidence.

## Interpretation

The original review was right about the structural danger—schema and hash checks were being mistaken for scientific checks—but its numerical conclusion should not be quoted without metric correction. V2.6’s evidence cannot establish model performance, convergence, failure prevalence, hardware energy, or publication readiness. V3 preserves this report so the correction is auditable and requires a prospective rerun from real source records.

This review also finds a limitation in V3 itself: byte hashes prove identity, not truthful acquisition or sensor calibration. Those remain explicit review questions and certificate limits.
