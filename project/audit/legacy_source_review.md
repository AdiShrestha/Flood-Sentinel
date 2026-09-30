# Legacy source disposition ledger

Each of the 139 primary source files was inventoried and AST/text inspected. Critical computational paths were read and challenged directly; this ledger is a migration disposition, not a declaration that every line is correct. All historical outputs are excluded from new research evidence. Source bytes and flagged contexts are available by hash in `legacy_inventory.json`.

| Legacy path | Disposition and research consequence |
|---|---|
| `source/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/ablation/architecture_ablation.py` | Reject historical mechanism conclusions; retrain every architecture/component condition with own calibration, seed pairing and tuning parity; inference perturbations have separate estimands. |
| `source/ablation/audit_title_claims.py` | Reject historical mechanism conclusions; retrain every architecture/component condition with own calibration, seed pairing and tuning parity; inference perturbations have separate estimands. |
| `source/ablation/causal_masking_ablation.py` | Reject historical mechanism conclusions; retrain every architecture/component condition with own calibration, seed pairing and tuning parity; inference perturbations have separate estimands. |
| `source/ablation/hyperparameter_sensitivity.py` | Reject historical mechanism conclusions; retrain every architecture/component condition with own calibration, seed pairing and tuning parity; inference perturbations have separate estimands. |
| `source/ablation/sensor_ablation.py` | Reject historical mechanism conclusions; retrain every architecture/component condition with own calibration, seed pairing and tuning parity; inference perturbations have separate estimands. |
| `source/ablation/verify_chunk08_reality_gate.py` | Reject historical mechanism conclusions; retrain every architecture/component condition with own calibration, seed pairing and tuning parity; inference perturbations have separate estimands. |
| `source/acquisition/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/acquisition/acquire_attributes.py` | Reject attribute constants and regional rules; reacquire versioned source tables with per-field joins. |
| `source/acquisition/acquire_attributes_full.py` | Reject attribute constants and regional rules; reacquire versioned source tables with per-field joins. |
| `source/acquisition/acquire_events.py` | Rewrite: peak-date noon is not onset, full-period discharge quantiles are a distinct target, literal corroboration catalogs are unverified. |
| `source/acquisition/acquire_events_full.py` | Rewrite: peak-date noon is not onset, full-period discharge quantiles are a distinct target, literal corroboration catalogs are unverified. |
| `source/acquisition/acquire_gridmet.py` | Rewrite parser around NetCDF metadata and raw-byte retention; audit scale/offset, coordinate extraction, day boundary and historical vintages. |
| `source/acquisition/acquire_gridmet_full.py` | Rewrite parser around NetCDF metadata and raw-byte retention; audit scale/offset, coordinate extraction, day boundary and historical vintages. |
| `source/acquisition/acquire_nwm_retro.py` | Reject producer: USGS-derived values represented as NWM; reacquire provider bytes and validate reach crosswalk. |
| `source/acquisition/acquire_nwm_retro_full.py` | Reject producer: USGS-derived values represented as NWM; reacquire provider bytes and validate reach crosswalk. |
| `source/acquisition/acquire_snodas.py` | Reject producer: sparse interpolation or degree-day modeled values represented as daily SNODAS; download actual date-specific rasters. |
| `source/acquisition/acquire_snodas_full.py` | Reject producer: sparse interpolation or degree-day modeled values represented as daily SNODAS; download actual date-specific rasters. |
| `source/acquisition/acquire_thresholds.py` | Rewrite NWPS identifier mapping, units, effective-date history and missing-vintage handling; remove invented date/entropy. |
| `source/acquisition/acquire_thresholds_full.py` | Rewrite NWPS identifier mapping, units, effective-date history and missing-vintage handling; remove invented date/entropy. |
| `source/acquisition/acquire_usgs.py` | Reuse provider/parameter concepts only; reacquire with OGC v1, preserve statistic code, missing sentinel, timezone, qualifiers and raw response. |
| `source/acquisition/acquire_usgs_full.py` | Reuse provider/parameter concepts only; reacquire with OGC v1, preserve statistic code, missing sentinel, timezone, qualifiers and raw response. |
| `source/acquisition/build_stratification_report.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/compute_response_time.py` | Exclude eligibility proxy: generated attributes and uncalibrated fixed wave speed/headwater delay cannot restrict primary cohort. |
| `source/acquisition/compute_sample_adequacy.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/precheck_nwm_operational.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/select_full_panel.py` | Retain IDs only as unverified historical candidates; rebuild selection from a public sampling frame without hardcoded regimes. |
| `source/acquisition/select_pilot_panel.py` | Retain IDs only as unverified historical candidates; rebuild selection from a public sampling frame without hardcoded regimes. |
| `source/acquisition/verify_attributes.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_attributes_full.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_events.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_events_full.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_full_panel.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_gridmet.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_gridmet_full.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_kf113_declaration.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_nwm_op_precheck.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_nwm_retro.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_nwm_retro_full.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_pilot_panel.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_response_time.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_sample_adequacy.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_snodas.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_snodas_full.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_stratification_report.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_thresholds.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_thresholds_full.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_usgs.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/acquisition/verify_usgs_full.py` | Do not treat manifest presence, text declarations or expected counts as provider authentication; replace with independent raw-source checks. |
| `source/baseline/baseline_learn.py` | Rewrite label horizon, train-only scaling, subset budgets, stopping and threshold protocols; literal PASS checks and USGS-derived NWM cannot establish fairness. |
| `source/baseline/baseline_op.py` | Rewrite label horizon, train-only scaling, subset budgets, stopping and threshold protocols; literal PASS checks and USGS-derived NWM cannot establish fairness. |
| `source/baseline/baseline_stat.py` | Retain causal difference/climatology/CUSUM concepts; remove backward fill, fabricated calibration, per-window reset and persistence misnaming. |
| `source/baseline/baseline_sup.py` | Rewrite label horizon, train-only scaling, subset budgets, stopping and threshold protocols; literal PASS checks and USGS-derived NWM cannot establish fairness. |
| `source/baseline/ea_lstm.py` | Retain static-input-gate recurrence concept; migrate with input/dtype validation and raw static-data provenance; no old learned weights. |
| `source/baseline/label_budget_sweep.py` | Rewrite label horizon, train-only scaling, subset budgets, stopping and threshold protocols; literal PASS checks and USGS-derived NWM cannot establish fairness. |
| `source/baseline/threshold_registry.py` | Rewrite label horizon, train-only scaling, subset budgets, stopping and threshold protocols; literal PASS checks and USGS-derived NWM cannot establish fairness. |
| `source/baseline/verify_all_baselines.py` | Rewrite label horizon, train-only scaling, subset budgets, stopping and threshold protocols; literal PASS checks and USGS-derived NWM cannot establish fairness. |
| `source/baselines/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/encoder/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/evaluation/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/feature/causal_feature_matrix.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/compute_normalization.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/feature_windowing.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/latency_registry.json` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/recompute_causal_check.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/recompute_split_check.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/split_generator.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/tag_eligibility.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/test_causal_correctness.py` | Do not migrate old PASS status; replace with mutation tests for issue-time causality, label horizon, missingness, cadence and independent metric arithmetic. |
| `source/feature/test_causal_feature_matrix.py` | Do not migrate old PASS status; replace with mutation tests for issue-time causality, label horizon, missingness, cadence and independent metric arithmetic. |
| `source/feature/test_split_correctness.py` | Do not migrate old PASS status; replace with mutation tests for issue-time causality, label horizon, missingness, cadence and independent metric arithmetic. |
| `source/feature/test_split_generator.py` | Do not migrate old PASS status; replace with mutation tests for issue-time causality, label horizon, missingness, cadence and independent metric arithmetic. |
| `source/feature/verify_eligibility_tags.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/verify_feature_matrix.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/verify_latency_registry.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/verify_normalization.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/verify_split.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/verify_vintage_ledger.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/verify_windowing.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/feature/vintage_ledger.py` | Rewrite issue-time availability, historical vintage, daily raw normalization, explicit missingness and connected-basin/time split invariants; forecast-target checks are insufficient. |
| `source/features/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/figures/fig1_basin_map.py` | Regenerate figures solely from new validated tables with exact source hashes; preserve old SVGs only at legacy tag. |
| `source/figures/fig2_roc_curves.py` | Regenerate figures solely from new validated tables with exact source hashes; preserve old SVGs only at legacy tag. |
| `source/figures/fig3_per_basin_auc_distribution.py` | Regenerate figures solely from new validated tables with exact source hashes; preserve old SVGs only at legacy tag. |
| `source/figures/fig4_km_survival_curves.py` | Regenerate figures solely from new validated tables with exact source hashes; preserve old SVGs only at legacy tag. |
| `source/figures/fig5_label_budget_curve.py` | Regenerate figures solely from new validated tables with exact source hashes; preserve old SVGs only at legacy tag. |
| `source/figures/fig6_ablation_bars.py` | Regenerate figures solely from new validated tables with exact source hashes; preserve old SVGs only at legacy tag. |
| `source/figures/fig7_architecture_diagram.py` | Regenerate figures solely from new validated tables with exact source hashes; preserve old SVGs only at legacy tag. |
| `source/gate/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/gate/reality_gate.py` | Exclude obsolete reality gate: variance, entropy, schema and self-written HTTP status do not authenticate a provider; use factory v3.3 plus domain adapter. |
| `source/gate/recompute_provenance_check.py` | Exclude obsolete reality gate: variance, entropy, schema and self-written HTTP status do not authenticate a provider; use factory v3.3 plus domain adapter. |
| `source/gate/run_reality_gate.py` | Exclude obsolete reality gate: variance, entropy, schema and self-written HTTP status do not authenticate a provider; use factory v3.3 plus domain adapter. |
| `source/gate/test_data_level_checks.py` | Do not migrate old PASS status; replace with mutation tests for issue-time causality, label horizon, missingness, cadence and independent metric arithmetic. |
| `source/gate/test_reality_gate.py` | Do not migrate old PASS status; replace with mutation tests for issue-time causality, label horizon, missingness, cadence and independent metric arithmetic. |
| `source/model/c_encoder.py` | Migrate architecture after removing hardcoded data demo, implicit dimensions, NaN concealment and result claims; add suffix and gradient tests. |
| `source/model/pretrain_dataset.py` | Rewrite: absent files must fail, missing observations require masks, train statistics must fit daily values rather than window means. |
| `source/model/pretrain_encoder.py` | Retain masked-learning concept; replace fixed-epoch single-seed loop with masked observed-only loss, validation stopping and immutable receipts. |
| `source/model/recompute_receptive_field_check.py` | Replace narrow assertions/AST label scans with executed prefix causality, observed-mask, learning, checkpoint and replay tests. |
| `source/model/test_causal_receptive_field.py` | Do not migrate old PASS status; replace with mutation tests for issue-time causality, label horizon, missingness, cadence and independent metric arithmetic. |
| `source/model/timing_pilot.py` | Discard hardware claim: random tensor timing and extrapolated duration are not measured corpus throughput or convergence. |
| `source/model/verify_encoder_convergence.py` | Replace narrow assertions/AST label scans with executed prefix causality, observed-mask, learning, checkpoint and replay tests. |
| `source/model/verify_no_label_leakage.py` | Replace narrow assertions/AST label scans with executed prefix causality, observed-mask, learning, checkpoint and replay tests. |
| `source/release/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/release/backfill_ablation_numbers.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/build_final_results_manifest.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/package_replication.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/prepare_dataport.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/rehash_dataport_manifest.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/scan_banned_claims.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/verify_ai_disclosure.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/verify_all_tabular_data.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/verify_baseline_parity.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/verify_final_synthesis.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/verify_key_facts.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/verify_references.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/verify_release_integrity.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/verify_sc008.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/release/verify_venue_requirements_refs.py` | Replace report/text consistency checks with artifact-to-claim joins, source license verification and honest release status; old manifests/figures/verdicts cannot be carried forward. |
| `source/scorer/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/scorer/calibration.py` | Rewrite calibration isolation: heldout gauges have one calibration window and floor-generated scale, overlapping evaluation boundaries. |
| `source/scorer/score_a.py` | Replace unmasked inference with deterministic leave-channel-out reconstruction; missing target entries never contribute loss. |
| `source/scorer/score_b.py` | Replace origin norm after LayerNorm with fitted baseline covariance distance; do not call Euclidean radius Mahalanobis. |
| `source/scorer/score_c.py` | Rename latent-step change honestly; future prediction requires a separately trained past-only predictor. |
| `source/scorer/verify_calibration_isolation.py` | Rewrite calibration isolation: heldout gauges have one calibration window and floor-generated scale, overlapping evaluation boundaries. |
| `source/split/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/stats/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/stats/collapse_events.py` | Recompute only on new admissible predictions; undefined basin AUROC is null, seeds are not basins, 30-day series cannot support daily persistence, onset uncertainty must be retained. |
| `source/stats/effective_sample_audit.py` | Recompute only on new admissible predictions; undefined basin AUROC is null, seeds are not basins, 30-day series cannot support daily persistence, onset uncertainty must be retained. |
| `source/stats/eval_discrimination.py` | Recompute only on new admissible predictions; undefined basin AUROC is null, seeds are not basins, 30-day series cannot support daily persistence, onset uncertainty must be retained. |
| `source/stats/eval_lead_time_survival.py` | Recompute only on new admissible predictions; undefined basin AUROC is null, seeds are not basins, 30-day series cannot support daily persistence, onset uncertainty must be retained. |
| `source/stats/eval_sample_adequacy.py` | Recompute only on new admissible predictions; undefined basin AUROC is null, seeds are not basins, 30-day series cannot support daily persistence, onset uncertainty must be retained. |
| `source/stats/h2_cohort_accounting.py` | Recompute only on new admissible predictions; undefined basin AUROC is null, seeds are not basins, 30-day series cannot support daily persistence, onset uncertainty must be retained. |
| `source/stats/recompute_bootstrap_check.py` | Recompute only on new admissible predictions; undefined basin AUROC is null, seeds are not basins, 30-day series cannot support daily persistence, onset uncertainty must be retained. |
| `source/stats/test_metric_dispatch.py` | Do not migrate old PASS status; replace with mutation tests for issue-time causality, label horizon, missingness, cadence and independent metric arithmetic. |
| `source/stats/verify_chunk07_reality_gate.py` | Recompute only on new admissible predictions; undefined basin AUROC is null, seeds are not basins, 30-day series cannot support daily persistence, onset uncertainty must be retained. |
| `source/utils/__init__.py` | Omit empty historical namespace; use the new package. |
| `source/utils/config.py` | Replace chunk-specific path/logging/manifest scaffolding with standalone package and factory receipts; no scientific claim attaches to utility reuse. |
| `source/utils/logging_config.py` | Replace chunk-specific path/logging/manifest scaffolding with standalone package and factory receipts; no scientific claim attaches to utility reuse. |
| `source/utils/manifest.py` | Replace chunk-specific path/logging/manifest scaffolding with standalone package and factory receipts; no scientific claim attaches to utility reuse. |
