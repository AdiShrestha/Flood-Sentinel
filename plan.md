# Flood Sentinel — forensic findings, audited migration, and research completion plan

**Prepared:** 30 September–1 October 2026 (Asia/Kathmandu). **Project:** `flood-sentinel-research-rebuild`. **Factory:** supplied Software Factory 3.3.0. **Current research status:** **NOT SUBMISSION READY; no legacy scientific claim is admitted as new evidence.** **Current engineering status:** a small corrected engine has been migrated and tested; acquisition, experiment execution, domain inference and research certification remain to be implemented.

This document is the research brief and implementation roadmap for an Architect and an Implementor working in separate sessions with access only to this repository. It is deliberately detailed so they do not need the old local folder or this conversation. Read the complete document before choosing the study design. The goal is defensible, reproducible research, including a valid negative or inconclusive outcome. Neither venue prestige nor a desired performance number may determine labels, exclusion rules, model budgets, thresholds, stopping or conclusions.

## 0. Start here: what is authoritative and what has actually been done

The user requests a comprehensive audit, a clean mathematical engine, preservation of the legacy GitHub work, replacement of the active GitHub tree with this new folder, and a completion plan compatible with factory v3.3. The intended machine is an ARM Apple M3 MacBook Air with 8 CPU cores, 10 GPU cores, 16 GB unified memory and 512 GB internal storage. These are **user-provided specifications**, not measurements from a research hardware benchmark. Treat available disk space, device accessibility, sustained throughput, temperature and energy as unknown until measured.

Authority is the user brief, then the supplied `factory/constitution.md`, `factory/factory_spec.md`, the frozen study methodology and executable `project/research_plan.json`, and finally implementation. This `plan.md` supplies the scientific design and work sequence; it does not substitute for a machine-valid frozen research plan. All factory code in the supplied new scaffold is retained. `factory/legacy/v2_6_0/` is factory history, not Flood Sentinel research evidence. The existing `docs/FORENSIC_AUDIT.md` and `docs/v26_forensic_results.json` describe the factory author's other test project, including AML candidate IDs. Their numerical findings **must not be attributed to Flood Sentinel**. Flood Sentinel-specific evidence is under `project/audit/`.

The current migration contains:

- `source/flood_sentinel/model.py`: migrated left-padded causal convolutions, residual TCN, causal attention, per-time LayerNorm and reconstruction head, with input/mask checks and rejection of nonfinite attention instead of concealment.
- `source/flood_sentinel/reconstruction.py`: an explicit observation-mask input, observed-only masked MSE and deterministic leave-channel-out reconstruction. No legacy checkpoint is loaded. Changing the input dimension makes old checkpoints incompatible by design.
- `source/flood_sentinel/ea_lstm.py`: the static-input-gate recurrence concept, with aligned input checks and dtype-preserving recurrent state. This is an architectural primitive; it is not a trained benchmark.
- `source/flood_sentinel/temporal.py`: timezone-aware observation intervals, explicit availability basis, issue-time filtering, uncertain onset intervals, future-onset labels and alert confirmation at the last required observation.
- `source/flood_sentinel/preprocessing.py`: normalization fitted on supplied raw training observations, distinct observed masks, train-median imputation and rejection of absent/constant channels.
- `source/flood_sentinel/scoring.py`: fitted robust scale with no one-point or zero-IQR substitute; regularized baseline Mahalanobis distance; honestly named latent-step change.
- `source/flood_sentinel/metrics.py`: tie-aware AUROC, grouped-threshold average precision, probability metrics, Holm adjustment and a paired independent-cluster interval primitive. Undefined subgroup AUROC remains null. The cluster primitive assumes independent effects supplied by the caller; it does not establish independence.
- `source/flood_sentinel/baselines.py`: actual constant persistence forecasts, separately named rate-of-change, and continuously carried EWMA/CUSUM state.
- `source/tests/test_engine.py`: isolated engineering fixtures for the concrete failure modes. Constructed inputs are disclosed test data. They are never research observations or evidence of flood skill.

This package is a **research foundation**, not a repaired empirical study. It contains no operational flood service, no acquired research cohort, no trained research model, no measured model comparison and no publication claim. Do not add a dummy result runner that writes valid-looking receipts to make the scaffold pass. The supplied `project/research_plan.json` is kept as a clearly unregistered design draft until acquisition and prospective decisions exist. `project/methodology.md` records current boundaries; it is not a retroactive preregistration of the old results.

A passing engineering test proves only its tested software property. The factory's own 276 self-tests passed outside the execution sandbox. Inside the sandbox, the Unix-socket fixture was denied permission: this was an environment restriction, not evidence of a failed scientific check. The new engine's final 31 engineering test cases passed, including independent factory-oracle checks of probability metrics and numerical-overflow rejection. See `project/audit/validation.md` and saved logs for verification. No complete research experiment was run during this migration.

## 1. Audit method, coverage and evidential limits

The legacy Git repository was clean at initial inspection. Its tracked head and remote `main` were `6078b04f4c104e7b14a96a4719c3f744b0782dd8`; the remote initially contained no tags. Only one commit was present. The old `.gitignore` omitted factory, project artifacts and handoff bundles from the published tree. Thus the published code/claims and the supplied local artifacts are related but not identical archival scopes.

The file audit read every regular legacy file outside `.git`, including ignored files, copied handoff material, caches and operating-system metadata. It inspected archive contents without extracting or running them. The result is **2,186 filesystem files**, **5,983 archive members**, and **921 distinct content hashes including archive members**. Files comprise 139 primary source files, 1,289 handoff copies, 713 other historical artifacts and 45 cache/OS files. No symlink was omitted. The large file with an opaque name was recognized as an archive by its bytes; filenames alone were not trusted.

`project/audit/legacy_inventory.csv` provides path, role, size and SHA-256 for every filesystem file. `legacy_inventory.json` additionally maps archive members to hashes, stores unique content inspections, Python definitions and line ranges, flagged textual contexts, JSON structure/duplicate-key diagnostics, and complete unique Parquet reads with schemas, null counts and numerical diagnostics. Copies are represented individually but inspected by content identity to avoid mistaking duplication for replication. Binary cache files with no text extension may produce UTF-8 diagnostics; those diagnostics do not imply malformed scientific records. Model checkpoints are hashed and the primary checkpoint is loaded using `weights_only=True` for numerical inspection; no arbitrary pickle code is intentionally executed.

The 139-file source disposition ledger is `project/audit/legacy_source_review.md`. It assigns each primary source file to rejection, rewrite, architectural-concept reuse or regenerated verification. Critical acquisition, preprocessing, training, scoring, baseline, evaluation and ablation paths were read directly and challenged. Full file/AST/column coverage is **not a claim that every line received an independent domain proof**. Historical narrative documents were read/indexed and scanned for conflicting claims; their contents are assertions, not automatically accepted observations. Figures were inventoried as rendered artifacts and traced to their producing scripts; visual polish does not authenticate numbers.

The independent script `project/audit/tools/inspect_legacy_evidence.py` does not import legacy producers. It loads their stored tables, independently reproduces the disclosed USGS-to-NWM and meteorology-to-SWE formulas, checks cadence and calibration support, and recomputes ranking metrics with scikit-learn. Its output, `project/audit/legacy_observations.json`, is portable to future sessions. `audit_legacy.py` can repeat the broader inventory when an archive or legacy folder is available. Neither script fetches or authenticates the original providers. Raw observation authenticity remains unverified even where stored values look plausible.

No allegation about the human author's intent follows from these findings. The code and artifacts demonstrate generated or unsupported quantities represented as stronger evidence than they are. Whether earlier AI assistance or another process introduced them is irrelevant to their scientific admissibility. Rebuild the affected paths, disclose the correction and preserve history.

## 2. Findings and consequences: the legacy results cannot be promoted

Severity terms here concern research validity: **critical** invalidates a central estimand, source or result; **major** invalidates a comparison or inference; **moderate** limits reproducibility/reporting. A failure may have several downstream consequences. Repairing one script does not repair old predictions, fitted weights or already-observed test choices.

### F01 — Supposed NWM retrospective values are transformed USGS observations (critical, confirmed in code and bytes)

`source/acquisition/acquire_nwm_retro.py:101` sets `nwm_sim = obs_cms.copy().values`, where `obs_cms` is USGS discharge multiplied by 0.0283168. It never reads the declared NWM Zarr source in this function. Missing files become zeros. `acquire_nwm_retro_full.py:144` computes `nwm_cms = obs_cms * 0.95 + 0.05 * sin(linspace(0,100,N))`, clips to 0.01, and uses a constant 5.0 if observations are absent. Records still identify NWM retrospective v3 output and contain literal successful HTTP fields.

The independent audit reproduces **all 54 stored NWM site series exactly at their serialized four-decimal precision** using these formulas, including the pilot copy/reuse branch. This establishes that the supplied comparison series are not independent NOAA NWM output. It is not merely suspicion from a high correlation. The H3a comparison and claims about physics-based routing are invalid. Even an unfavorable Score-A result against this series is not a valid comparison against NWM.

Remedy: delete these producers from the active engine, reacquire actual provider objects, verify versioned reach IDs and timestamps, and rerun all affected comparisons. The registry says NWM v3.0 CONUS retrospective coverage is February 1979 through **January 2023**, not the legacy declaration of a complete 1990–December 2023 NWM series. The precise downloaded time coordinate is authoritative. Intersect comparison coverage prospectively; never fill the unavailable period with observation-derived values. Retrospective NWM is model output forced with retrospective meteorology, not an as-issued operational forecast. [Official dataset registry](https://registry.opendata.aws/nwm-archive/).

### F02 — SNODAS is partly sparse interpolation and partly an undisclosed degree-day model (critical, confirmed)

`acquire_snodas.py` samples just 20 dates over roughly two decades, interpolates between them and fills remaining dates with zero (`:212`). Future samples therefore influence interpolated earlier values. Negative raster fill is converted to zero. These are not independently acquired daily SWE observations. Some date-specific raw raster requests may be real, but that does not authenticate the generated daily panel.

`acquire_snodas_full.py:210–225` uses `current_swe += precipitation` when average temperature is nonpositive and otherwise subtracts `2.5 * temperature`, bounded below at zero. Missing meteorology becomes zero. Missing coordinates can fall back to 40°N, 105°W. The derived output is described in provenance as an NSIDC SNODAS series. The audit independently reproduces **all 24 expansion snow-basin series exactly**. Non-snow declarations also generate daily zeros rather than establish measurements.

Remedy: acquire actual date-specific SNODAS product bytes and retain no-data flags, product metadata and aggregation provenance. SNODAS itself is a model/data-assimilation product; use its scientifically accurate origin description rather than calling it a raw snow gauge. A degree-day model may be a separately named, fully disclosed modeling baseline; it cannot stand in for acquired SNODAS. Until actual SWE coverage and vintages are verified, exclude that channel from the primary study by a prospective scope decision, not by a favorable test result. [NSIDC product page](https://nsidc.org/data/g02158/versions/1).

### F03 — Static catchment attributes and regulation checks are assigned or unsupported (critical)

`acquire_attributes.py:33` defines a long literal table of pilot attributes, including slope, forest, imperviousness, soil permeability, curve number, CAMELS coverage, aridity, baseflow index and upstream dams. The source archives and exact record joins supporting each value are absent from the producing path. Treat these fields as **unverified**, not all provably invented: manually entered values could be correct, but correctness is not established.

`acquire_attributes_full.py:98` assigns expansion attributes from HUC/regime rules: regional elevation, slope, forest percentage, permeability, curve number, aridity and baseflow constants; channel length is a drainage-area formula; dam counts are derived from reference class and logarithmic area. `camels = True` is asserted. Agreement between generated dam counts and the class used to generate them is circular, not an independent GAGES-II/NID cross-check. A GAGES-II reference designation is not equivalent to a universal zero-upstream-dam rule.

Remedy: build versioned joins to actual GAGES-II/CAMELS/NHDPlus/NID tables or honestly omit unavailable fields. Preserve source row IDs, units, dataset dates, catchment geometry and spatial join logic. Unknown CAMELS coverage remains unknown. The entire static EA-LSTM branch and response-time subgroup assignments require a rerun.

### F04 — Event onset is fabricated from the peak date (critical, confirmed)

Both event producers assign `crossing_timestamp = peak_date + 'T12:00:00Z'` (`acquire_events.py:106`, `acquire_events_full.py:109`). Peak date and threshold-crossing onset are different quantities, and daily records do not justify noon precision. The independent audit finds that **all 2,838 primary stored events use exactly peak date plus noon**. Historical reports subsequently call these exact official onset timestamps.

Remedy: derive first threshold crossings from appropriately resolved raw stage observations and retain a last-below/first-above onset interval. When only daily aggregates exist, report interval/date-resolution endpoints; do not claim exact hourly warning lead. Daily mean stage is not instantaneous crossing truth. If an event is already above threshold at the start of the available record, record left censoring. Missing observations and gaps must not be treated as a proven return below threshold. Final incomplete episodes require right-censoring status and correct start/peak/end separation.

### F05 — Official stage thresholds and data-driven discharge thresholds are mixed into one target (critical)

When enough stage data or a stage threshold is absent, `acquire_events_full.py:65` estimates the 98.5th percentile of **the entire observation record**, including later evaluation years, and tags resulting events as minor/primary `usgs_nwps_crossing`. A local discharge quantile is not an official stage category. Thresholds from a current NWPS metadata query also do not automatically apply to historical stages across rating curves, datum changes or threshold revisions.

Remedy: maintain separate target definitions: official minor flood stage with verified threshold/datum history; action-stage exceedance as an explicit secondary target; and high-flow quantile exceedance as a separately named retrospective hydrological target using train/calibration-only thresholds. Never merge these into one label. Unknown historical official thresholds can justify excluding a site from that target or narrowing the study; they cannot justify relabeling a proxy as official truth.

### F06 — FLASH/NCEI corroboration catalogs are literal, unverified lists (major)

`acquire_secondary_flash_events` and `acquire_contextual_storm_events` return small dictionary lists of named events, numeric unit discharges, episode IDs and narratives; they do not acquire the advertised archives. These may mention real historical floods, but exact IDs and numerical fields are unsupported in this source path. Combining those lists with primary events can also expose contextual events to the same label-generation code.

Remedy: acquire actual source archives and preserve record identifiers, geographic mapping and time-zone/uncertainty rules. County-level Storm Events descriptions do not establish basin-level stage onset. Context is not interchangeable with primary truth; matched descriptions are not independent measurements of a model's score. Use corroboration only where a declared join can be inspected.

### F07 — The causality gate uses the target time instead of the issue time (critical)

`causal_feature_matrix.py:103` sets its cutoff to window end plus 24 hours. Its asserted source delays are at most 24 hours, so it mechanically passes even when a feature is unavailable at prediction issue. The valid constraint is `available_at <= issue_time`, **not** `available_at <= target_time`. The function emits `causally_valid: True` in every output row (`:227`) rather than using a verified per-row filtration. The report's “zero exclusions” therefore follows from the construction, not a convincing operational audit.

Remedy: define issue time before forming the prediction tensor. Evaluate every input record's observation interval end and availability against issue. A later target does not create earlier access. Inspect all transforms, not just one terminal feature per channel. Daily accumulation at date midnight cannot represent a complete day's precipitation available at that same midnight. Record the source's day convention and aggregation completion.

### F08 — Fixed latency and date-based vintage labels do not recover historical as-issued products (critical for operational claims)

The latency registry assumes USGS 0h, gridMET 14h, SNODAS 24h and uses a 2013 date switch to identify gridMET near-real-time proxies. Modern downloads of revised histories do not prove what was available at an old issue time. The gridMET documentation describes changing near-real-time inputs and subsequent replacement, plus a day defined nominally in Mountain Standard Time. It does not establish the legacy fixed 14h delay for every historical variable/date. [Provider documentation](https://www.climatologylab.org/gridmet.html).

Remedy: distinguish final retrospective, assumed-latency replay, archived as-issued replay and prospective monitored collection. An assumption may define an explicitly qualified retrospective study, but it is not observational proof of operational access. If vintages cannot be recovered, do not make real-time or actionable-deployment claims. Begin prospective vintage capture only after an explicitly defined collection policy; preserve actual publication/receipt timestamps and revisions.

### F09 — gridMET numeric decoding and spatial extraction require provider-metadata verification (major, unresolved)

The source hardcodes precipitation/temperature scale factors and offsets, grid origins, cell size, index rounding and OPeNDAP ASCII parsing. Packed NetCDF values and server-decoded responses need different handling; applying scale twice or ignoring fill metadata can bias physical inputs. No re-download was performed during this audit, so this is a concrete **unverified transformation**, not a demonstrated claim that all temperatures are wrong. The legacy reads one grid cell at a gauge point, which is not a catchment-average forcing.

Remedy: retain raw metadata and a reference provider slice; use one explicit CF decoding path, verify units/ranges/fill flags and coordinates, and compare independently with manual values. Adopt basin-area aggregation where the hydrological estimand requires catchment forcing, or clearly restrict the claim to station-cell proxies. Require precipitation totals and min/max temperatures to obey appropriate physically plausible diagnostics without rewriting unusual observations to typical values.

### F10 — Missing data become physical zero, including entire absent sequences (critical)

`pretrain_dataset.py:147` zero-fills missing channels; `:170` creates an all-zero 365×6 array when gauge data are absent. Missing SNODAS files, pre-2003 SWE, absent stage and missing days can therefore become model targets. Other paths forward-fill, backward-fill and replace missing calibration with constants. Backward fill and interpolation can import later information.

Remedy: distinguish absent files (hard acquisition failure), missing observations (explicit masks and exclusion), non-applicable channels (a declared domain status), and genuine measured zero. Reconstruction loss and calibration must exclude missing targets. Fit imputation only on training data, document its assumptions, and carry an observation indicator into the model. Never convert missing labels into negatives.

### F11 — Neural normalization uses statistics of window means to scale individual daily values (major)

`compute_normalization.py` fits the columns `discharge_cfs_mean`, `gage_height_ft_mean`, etc.; `HydroPretrainDataset` then applies those parameters to daily sequences. Variance of a 365-day mean is not variance of daily observations. Overlapping windows also reweight the same raw observations. This mismatch changes relative channel loss contributions and anomaly behavior. A floor or arbitrary replacement variance hides the problem.

Remedy: fit intended transforms on unique eligible raw training observations, with explicitly chosen basin weighting and per-channel policy. Separate any normalization of aggregate baseline features. Handle discharge skew and disparate basin sizes through preregistered transforms, not unexplained ad hoc scale. Constant or empty channels require a scope decision. Include tests showing that changing test values does not alter fitted preprocessing.

### F12 — Static-feature normalization includes held-out basins (major)

`baseline_sup.py:66` computes static attribute means/std over the full 54-gauge attribute table. Although static covariates are not flood labels, this is transductive preprocessing that conflicts with a strict held-out-basin claim. It is compounded by generated expansion attributes.

Remedy: fit static transforms on training basins only for the inductive protocol. A separately declared transductive setting may use known unlabeled target covariates; report that setting accurately and apply it consistently across comparators. Do not conflate it with an ungauged/no-target-data study.

### F13 — Supervised labels describe a past event, not a future precursor (critical)

`baseline_sup.py:extract_tensors_and_labels` assigns a positive when an event falls in `[window_end−7 days, window_end]`. Event matching and discrimination then compare scores at or after the peak against this trailing label. A pooled AUROC can be arithmetically correct while measuring recognition of recent/present high water instead of future warning.

Remedy: the primary prediction target must be a new qualifying onset in `(issue, issue+horizon]`, with currently flooded periods handled explicitly. Past/recent-event detection is a separate retrospective task with separate claims. Do not call a good trailing-event score precursor forecasting. The new engine exposes future-event labels, but the production adapter must still establish complete coverage and onset intervals.

### F14 — Sparse prediction cadence makes the reported negative H2 result structurally unavoidable (critical, confirmed)

`feature_windowing.py:112` uses stride 30. All 792 within-gauge prediction gaps in the supplied evaluation window matrix are **30 days**. `eval_lead_time_survival.py` requires scores at exactly one-day spacing for a two-day persistent alert. No pair in these matrices can satisfy that condition. Consequently 0/8 primary detections cannot establish that a correctly sampled anomaly method lacks warning ability. This failure remains unacceptable even though it produces a negative headline.

Remedy: generate predictions at every declared issue time, typically daily or subdaily, and audit achieved cadence and eligible monitored exposure. Training-window subsampling is a compute choice; evaluation cadence is a scientific choice and must cover the operational alert rule. Sparse or missing monitoring is not equivalent to an observed nondetection. Re-evaluate both positive and negative claims from the new stream.

### F15 — Persistent alert lead is credited before confirmation (major)

`eval_lead_time_survival.py:261` uses the first of two threshold crossings as alert time. A two-observation alert cannot be issued until the second required observation and any computation/data latency have arrived. This would overstate warning lead even after cadence were repaired.

Remedy: alert timestamp is the confirmation issue plus measured processing delay. A secondary earliest-elevation time may be reported with its distinct non-operational interpretation. If onset is uncertain, compute bounds on lead, not invented precise hours.

### F16 — The H2 action-only filter omits more severe crossing events (major)

Events are labeled by their maximum attained category, then lead-time analysis filters `threshold_level == 'action'`. An episode reaching minor/moderate/major still crosses action, but it is excluded by this equality filter. Action stage itself is not synonymous with flooding. The cohort combines this selection with the unsupported response-time proxy and sparse monitoring.

Remedy: derive crossing times for each threshold separately and select the target crossing regardless of later peak severity. Choose official minor flood stage for flood claims when validated; action-stage warning is secondary and precisely named. Publish the complete denominator waterfall, including site coverage, thresholds, left censoring, ongoing events, data gaps and observation resolution.

### F17 — Calibration of all validation and test gauges uses one sample (major, confirmed)

Every one of the 11 validation and 11 test gauges has `calibration_window_count=1`. A one-year span with 365-day windows yields one scored window; IQR/std are then forced to 1e−4. Default score calibration parameters are also 1.0 in several scoring branches. The test calibration period is the first test year; the first evaluated 365-day endpoint lies at the calibration boundary, allowing the calibrated observations to overlap the evaluation history/score.

Remedy: establish an adequate multi-issue calibration series, exact calibration/evaluation separation, and a declared warm-start or no-target-history setting. One sample cannot estimate a distributional scale. Calibration minima and precision need a reason, not a denominator trick. Target-gauge calibration requires available historical observations and therefore narrows “ungauged” claims. Scores from non-estimable calibration must fail or be explicitly unavailable.

### F18 — Score-A is evaluated with a different masking condition than its objective (major)

Training hides targets and optimizes masked reconstruction; legacy inference passes fully visible input and computes error against that visible input. The model can see the contemporaneous target channel in this inference path. This does not automatically falsify every reconstruction anomaly method, but it does not evaluate the declared target-withheld reconstruction operator consistently and may reward copying/suppress residuals.

Remedy: define masked reconstruction, cross-channel reconstruction or past-only forecasting as distinct operators. The migrated scorer withholds a channel before scoring it. It needs a compatible preregistered training-mask distribution and validation checks; architectural causality alone cannot make an unmasked reconstruction score a future forecast. Do not claim its superiority before a real comparison.

### F19 — Score-B is an origin norm, not the advertised Mahalanobis distance (major)

`score_b.py:68` computes `norm(z,2)` without a fitted baseline mean or covariance. A final LayerNorm largely fixes embedding radius when affine parameters are near their default; that makes origin norm a particularly poor generic anomaly distance. Small learned affine changes may still produce numerical variation, so do not claim exact constancy without evaluating the fitted model.

Remedy: use a training/calibration-only baseline distribution and a declared shrinkage covariance or distance alternative. Measure covariance conditioning, dimensionality and reference support. Report Euclidean norms honestly if retained as controls. The migrated primitive performs a genuine regularized Mahalanobis calculation; a high distance still does not prove imminent flooding.

### F20 — Score-C is latent change, not learned future prediction (major)

`score_c.py:70` computes `z[t]−z[t−1]`. There is no trained future-latent predictor. The old names/reporting overstate the executed mathematical operator.

Remedy: use the name latent-step change, which the migration adopts, or implement a separately trained past-only prediction head with explicit target and horizon. Do not silently reinterpret a derivative as prediction error.

### F21 — Training sufficiency is not established by the legacy checks (major)

The stored primary pretraining summary records **10 epochs**, 9,760 windows and a 146,950-parameter checkpoint. It is wrong to call this Flood Sentinel checkpoint a two-epoch run: the factory's unrelated v2.6 forensic document concerns another project. The recorded loss falls from 6.660817 to 5.423724 but is not monotonically decreasing, and there is no held-out masked-objective loss trace or validation checkpoint selection in this producer. It uses a single unrecorded primary randomness trajectory. Its convergence check compares first/final training loss and a small train-dataset latent sample; a code comment calling that validation does not create a validation experiment.

Remedy: seed every stochastic component, separate validation, log all losses and optimizer state, preregister stopping and max-budget criteria, retain initial and selected checkpoints, and test extended-budget stability. Decreasing training loss, ten epochs, nonzero latent variance and small parameter count do not establish statistical or optimization convergence.

### F22 — Learned comparator budgets and label percentages do not match the headline interpretation (major)

The unsupervised learned branch uses at most 1,000 windows, the nominal fully supervised branch at most 1,500, and the label-budget sweep a pool of at most 1,200 from 9,760 primary training windows. Supervised training uses five fixed epochs. “100%” in the sweep means all labels in that restricted pool, not all available training data; the reference SSL model can use substantially more unlabeled windows. One primary SSL run is reused against multiple seeded supervised runs.

Remedy: define unlabeled observation opportunity, labeled independent-event/site counts, data selection, model fitting, hyperparameter opportunity and compute separately. Quantify resource differences instead of asserting parity. Use matched seed pairs for trained models and hierarchical interpretation. At a low label budget, zero-positive training sets are possible; retain and report them without inventing examples or selecting better subsets.

### F23 — Architecture ablations contain untrained layers and inherited calibration (major)

The TCN-only branch copies three pretrained TCN blocks into a four-block model; the Transformer-only branch copies two blocks into a four-block model. Additional layers remain randomly initialized, and the models are not retrained as the declared architectures. The hybrid final normalization is not uniformly transferred. Hybrid calibration is reused. Such comparisons measure a destructive checkpoint surgery intervention, not trained architecture quality.

Remedy: train each architecture from its own seeded initialization with validation stopping and its own calibration, or explicitly call inference surgery a robustness intervention. Include training/tuning/compute opportunity and uncertainty. A full factorial table is insufficient if the cells do not execute valid matched operators.

### F24 — Mask-ratio sensitivity changes test corruption, not pretraining mask ratio (major)

`hyperparameter_sensitivity.py:113` randomly zeros test values using `abs(r−0.15)`, evaluates the same checkpoint and labels the output “Pretrain masking ratio”. Thus some nominal ratios create the same corruption rate, and the experiment does not change training. Window-length changes also reuse one trained model and calibration.

Remedy: retrain under each declared training hyperparameter; separate inference missingness/robustness tests from training sensitivity. Freeze grids before test. Do not manufacture a curved sensitivity figure if a correct sweep is flat.

### F25 — Removing a within-prefix attention mask is not automatically future-data leakage (major)

A bidirectional encoder over a window containing only information already available by issue can remain issue-time causal for its terminal prediction. It may use later positions relative to interior tokens, so it violates a different per-token online filtration if interior outputs are claimed. The old causal-mask ablation transfers a checkpoint rather than training both modes and labels full-prefix bidirectional processing as future peak leakage without establishing that the peak was unavailable at issue.

Remedy: distinguish per-token causal encoding from issue-time access. Define which outputs are emitted at each time. Use explicit unavailable-record and future-suffix attacks to test leakage. Treat bidirectional processing of an available prefix as a legitimate comparator where the task allows it. Never build a strawman “noncausal” baseline by withholding information incorrectly.

### F26 — Undefined basin AUROCs are replaced with 0.5 (major, confirmed)

The stored test event matrix has **520 rows but only 7 positive rows**, across 11 nominal basins. Only **7 basins** have both classes; the other four cannot estimate basin AUROC. `eval_discrimination.py:190` inserts 0.5, and `effective_sample_audit.py` infers non-estimability from an AUROC equal to 0.5 rather than directly checking label counts. A valid two-class basin can truly have AUROC 0.5.

Remedy: use actual label support for estimability. Store undefined metrics as null with reason, report all basins, and define the population of the estimable-basin average explicitly. Do not select test basins after seeing performance. Pooled AUROC/AP are contextual and heavily affected by site prevalence/scale. Seven positive rows do not constitute continental validation.

### F27 — Bootstrap blocks over sorted gauge identifiers lack a meaningful adjacency model (major)

The discrimination interval samples length-two circular blocks from gauges sorted by ID. Gauge identifiers are not a defensible temporal or hydrological spatial ordering. The method label says moving-block bootstrap, but its block order does not establish dependence handling. Thousands of bootstrap draws do not increase the number of independent basins/events.

Remedy: derive the resampling hierarchy from the estimand and actual network/storm dependence: connected catchment components, basins, water years and storm episodes. Preserve pairings across models. For a mean of independent basin effects, sample basin effects; for pooled discrimination, resample entire declared clusters and recompute the pooled metric. Those are different estimands.

### F28 — Event collapse and score joins introduce asymmetric and incomplete evidence risks (major)

Positive windows are grouped by episode and scores maximized; negatives remain overlapping windows. This gives positive events multiple score opportunities and a different unit from controls. `groupby` can discard positives with missing episode IDs. Several joins are inner merges without cardinality validation, and missing score lookups become zero. Ablations align to a representative window from a collapsed episode rather than necessarily repeating the same maximum operation used by the original score.

Remedy: keep an immutable complete issue-level prediction ledger, explicit one-to-one join validation, a separate event/alert ledger and matched aggregation rules. Score aggregation may not depend on knowing the true class at prediction time. Do not use label-dependent max pooling to construct a forecasting ROC without a carefully named estimand and comparable controls. Missing IDs fail; missing scores are not zero evidence.

### F29 — Hypothesis decisions overstate what p-values can establish (major)

Non-significance against a strong comparator does not establish parity or equivalence; an equivalence study needs a justified margin and adequate precision. H5's one-sided five-seed sign-rank result has coarse attainable p-values and conditions on one test corpus/SSL checkpoint, not new basins. Families of hypotheses, sensors, scores, budgets and sensitivity choices are not a single convincingly preregistered confirmatory family. A failed conventional threshold is not logically a falsification of all useful forecasting behavior.

Remedy: distinguish supported within scope, unsupported, inconclusive, adverse and protocol-invalid outcomes. Report effect sizes and intervals, prespecify multiplicity and direction, and keep seed variation separate from population uncertainty. Avoid calling a structurally broken negative test a scientific negative result.

### F30 — Survival and lead-time reports do not establish operational utility (major)

Conditional median lead among detected events omits misses; an empty lead sample is reported as zero hours rather than undefined. A Kaplan–Meier table from retrospectively selected event lookbacks and sparse monitoring requires censoring assumptions that are not demonstrated. A pre-onset alarm can belong to another event; event-only evaluation omits false alarms during non-event exposure.

Remedy: report coverage, event recall, false alerts per monitored basin-year, alarm duration, confirmation latency, and joint detection-plus-lead utility. Undetected is a categorical outcome, not zero-hour detected lead. Preserve uncertain onset intervals and right/left censoring. Survival analysis is optional; include it only with a defensible time origin, risk set, observation process and censoring model.

### F31 — Reality/release gates check self-written structure and texture, not authentic science (major)

Variance/entropy, data type, expected row counts, stored HTTP status, `undocumented_step=False`, textual declarations and stored hashes can all pass for generated values. `verify_all_baselines.py` and multiple reports initialize literal successful scientific flags. Rehashing a generated artifact authenticates the generated bytes, not their advertised provider. Some release scripts check strings against a central results manifest, creating consistency without independent experimental proof.

Remedy: use provider raw bytes, executed transform replay, ID joins, independently recomputed arithmetic, behavioral mutation attacks and documented semantic review. Never require noisy/high-entropy observations merely to look real: zero SWE or constant stage can be legitimate. Reject provenance substitution, not physically unusual data.

### F32 — Hardware assertions and reproducibility claims exceed captured execution evidence (moderate/major)

The timing pilot uses random tensors, measures a short CPU slice, extrapolates total time and enforces an arbitrary two-hour budget. Random tensors can be legitimate engineering microbenchmarks if labeled, but they are not observed corpus throughput, sustained M3 performance, memory, energy or scientific training sufficiency. Legacy dependency pins and checkpoint existence do not provide a clean-room replay. Full local artifacts are ignored by the old Git tree, while published reproduction instructions depend on them.

Remedy: lock and verify dependencies, measure representative real batches and sustained runs, synchronize accelerators, preserve raw trials and report unavailable telemetry. Package acquisition recipes, provider metadata and immutable evidence manifests, with actual restoration tests. Do not reduce methodological sufficiency to fit a preset timing target.

### F33 — Publication, licensing and provenance statements need correction (moderate)

The legacy README supplies an IEEE Access article citation with `Under Peer Review`; that status is not independently established by supplied evidence. Current code has an MIT legacy license naming a research consortium; the new scaffold has the user's proprietary factory license. Generic CC-BY assertions for all derived provider data need actual source rights analysis. Embedded historical Git SHAs in result manifests do not match the one tracked legacy commit; intermediate histories may have existed elsewhere, but this archive does not prove them.

Remedy: use software citation metadata with an actual release commit/tag, no invented DOI or journal status. Preserve original migrated-code notices in `source/flood_sentinel/LICENSE`; do not silently relicense the proprietary factory. The user selects the final research release license after the scope is concrete. Resolve provider redistribution rights per dataset and verify all manuscript references by exact bibliographic identity and supporting content. No legal conclusion is inferred merely from a public URL.

### Claim disposition

| Legacy claim | Present evidential status | What a future admissible claim requires |
|---|---|---|
| H1: zero-label flood precursor discrimination | Withdraw from active evidence; trailing-event target, mixed truth, unsupported inputs, sparse positives | Prospective future-onset target, verified sources, sufficient untouched test sites/events, fair baselines |
| H2: anomaly method fails operational two-day warning | Protocol-invalid negative result; cadence precludes detection and onset is invented | Complete daily/subdaily stream, actual/interval onset, confirmation-time alerts, false-alarm exposure |
| H3a: comparison with NWM retrospective | Invalid comparator; all series derived from USGS | Actual provider output, reach/time crosswalk, matched coverage and honest retrospective scope |
| H3b: operational archive unavailable | Not established by a few old URL probes; no comparison was performed | Current archive investigation; scoped unavailability record or real as-issued archive |
| H4: comparable to fully supervised EA-LSTM | No equivalence established; different budgets/labels/static leakage | Valid common target/data opportunity, trained/tuned comparator, paired uncertainty or justified equivalence design |
| H5: label efficiency at 10% | Conditional legacy result on a restricted pool, no paired SSL seed ensemble | Labeled event/site counts, nested subsets, comparable training and tuning opportunity, new test data |
| Multi-sensor synergy / hybrid superiority | Unsupported by inference surgery and generated channels | Valid trained factorial interventions and interaction uncertainty |
| Exact causal/operational latency guarantees | Wrong issue cutoff, no authentic vintage replay | Per-record as-issued/explicit assumed availability and transform replay |
| Lightweight/M3 efficiency | Parameter count can be counted; claimed runtime scope needs measurement | Representative sustained synchronized runs, real memory scopes and repeatable raw trials |

The audit independently reproduces legacy AUROC values, including Score-A approximately 0.82957 and the supposed NWM approximately 0.90699. **These are forensic properties of the stored, invalid pipeline tables**, not validation of early warning and not result targets for the new study. Reproducing a number cannot repair the estimand that generated it.

## 3. Select a defensible research question before rebuilding the entire pipeline

The most credible contribution is not “a small hybrid network achieves impressive AUC.” Established hydrological learning already includes regional/EA-LSTM models and large-scale forecasting. A hybrid TCN/Transformer alone is unlikely to establish a strong methodological contribution. A useful research question could concern when self-supervised anomaly representations help **future** flood-stage warning under honest information availability, label scarcity, regulation, spatial transfer and a controlled false-alarm budget. A valid negative result might show that retrospective anomaly discrimination disappears when issue-time restrictions and future-onset labels are enforced. That conclusion requires complete experiments; it cannot be inferred from the broken legacy H2 test.

The Architect should write a short novelty matrix before committing to expensive models. Compare flood-stage warning, high-flow forecasting, anomaly detection, hydrological self-supervision, missing-data learning and vintage-aware evaluation separately. For each nearest work, record task, inputs, label definitions, information available at issue, geography, horizons, training data, baselines, code access and limitations. Retrieve and read the actual paper/code for any claimed gap. Cite the original EA-LSTM work and large-scale flood forecasting rather than reducing them to caricatures. The published EA-LSTM study develops regional learning using static catchment descriptors; adapting it to binary flood labels is a new task specification that must be reported. [Kratzert et al., HESS 2019](https://hess.copernicus.org/articles/23/5089/2019/). A prominent 2024 Nature flood-forecasting paper is a relevant benchmark in scope and evaluation ambition, not an automatically reproducible local baseline: [Nearing et al., paper page](https://www.nature.com/articles/s41586-024-07145-1). Its full page did not reliably load during this audit; the Architect must retrieve the manuscript/methods before relying on detailed protocol claims.

Use a staged scope with clear scientific exits:

1. **Integrity and feasibility study:** verified hydrometry plus independently decoded meteorology; genuine future-onset labels; simple causal baselines; pilot precision and real compute measurements. No publication headline from this stage.
2. **Primary retrospective research study:** an untouched spatial and temporal test design with final historical inputs honestly named, or a genuinely archived as-issued study if recoverable. An assumed-latency replay is a separate explicit sensitivity setting.
3. **Optional operational extension:** prospective collection, actual publication vintages, realistic missingness, end-to-end latency and a larger warning utility evaluation. Claim operational readiness only after this extension has sufficient exposure and legitimate truth.

Do not require SNODAS, NWM, every static attribute and every novel head to exist before determining whether the primary task is viable. Their inclusion depends on authentic access and scientific relevance. Removal of an unavailable sensor must occur prospectively and appear in the scope/novelty matrix. It must not follow the test score. Conversely, do not label a four-variable prototype a complete multisensor operational warning system.

### 3.1 Candidate primary estimand and label

Default candidate: event warning performance for verified official minor flood-stage onsets, for monitored gauges with sufficiently reliable threshold/datum history, using hydrometeorological records available at an issue time. The primary horizon should be one practically justified value, provisionally 24 hours for daily issuance or another value chosen **only from development data and observation resolution**. Report additional prespecified horizons as secondary with appropriate multiplicity. If only daily stage means are available, exact 24-hour onset timing may be unresolvable; select date/interval-level targets and restrict claims, or acquire subdaily stage.

For gauge `g` and issue `t`, let `I_t` be the records admissible by issue and let the output be a score `s_g(t)` or probability `p_g(t;h)` of a new onset in `(t,t+h]`. Let `tau_e` denote onset of event `e`. The binary target is:

`Y_g(t;h) = 1{at least one qualifying new onset tau_e in (t,t+h]}`.

An ongoing flood at `t` is not a future onset. Declare whether those issue times are excluded from the onset task or assigned a separate “already flooded” state. A negative requires sufficient monitored future truth throughout the horizon, not merely absence of a catalog entry. Unknown coverage, datum, threshold, onset interval crossing a decision boundary or unresolved censoring produces an unavailable label and an exclusion reason.

For an interval onset `(L_e,U_e]`, a definitely future in-horizon event requires `L_e >= t` and `U_e <= t+h`; an exact onset has the corresponding strict-left rule. Intervals straddling issue/horizon remain ambiguous. Do not round them into a favorable class. Where appropriate, report sensitivity bounds under the earliest/latest compatible onset, and interval-censored endpoints rather than falsely exact labels.

The initial migrated `future_event_label` function encodes these basic rules. Its `coverage_complete` and current-state inputs must be derived from independent source checks by the production label adapter. Passing `True` because a caller wants a label is a provenance failure.

### 3.2 Candidate primary operating endpoint

A physically meaningful default is **event recall at a preregistered false-alert rate per monitored basin-year**, with confirmed alert lead relative to onset. Decide the operating target from hydrological/application rationale and development data; do not insert a arbitrary favorable false-alarm limit into the manuscript. If no application-specific cost exists, publish the complete recall/false-alert/lead tradeoff with uncertainty and a small prespecified set of operating points.

Define an alert episode from the issued score stream, not retrospectively from positives. For a `k`-issue persistence rule, the alert starts at the `k`th confirming issue after data processing completes; gaps break persistence unless a prospective tolerance policy explicitly permits them. Define reset, refractory period and alert expiration. Match alerts to future events with a prespecified horizon, deterministic tie rules and one-to-one accounting. Publish unmatched alerts as false alerts and unmatched events as misses. Account for alerts in non-event exposure and overlapping events.

Possible primary scalar: recall of new minor-stage events with positive confirmed lead at a validation-selected false-alert budget. Lead distribution conditional on detections, median lead bounds, lead-weighted recall and monitored coverage are separate endpoints. Keep them separate to avoid letting a detector with one early warning and many misses look useful. AUROC and average precision over issued future-event probabilities are secondary discrimination descriptors, with prevalence and unit definitions.

### 3.3 Scope statements that must be explicit

The primary population is the actual eligible sampling frame, not all CONUS basins. Monitored gauge histories are not ungauged inputs. Warm-start target-gauge calibration is different from zero-target-history transfer. Daily historical reanalysis is different from real-time operational access. Stage-exceedance warning is different from spatial inundation prediction, damage forecasting or emergency decision support. A label-free pretraining loss can still contain flood periods and use labeled validation decisions later; “zero labels anywhere” is a stronger claim that may be false.

The paper should explain which knowledge is used at each stage: raw observations, static covariates, labels for supervised training, labels for validation/selection, labels for calibration, evaluation labels and any target-gauge historical data. Do not market independence from labels if the operating threshold or best anomaly head was selected using labeled validation and conceal that cost in the comparison.

## 4. Data acquisition and provenance architecture

### 4.1 Minimal evidence graph

Use a content-addressed raw object store plus normalized tables. Suggested organization:

```text
data/
  raw/<provider>/<sha256>.<original-format>
  manifests/acquisitions.jsonl
  manifests/provider_versions.json
  manifests/field_provenance.parquet
  normalized/hydrometry/<site>/<period>.parquet
  normalized/meteorology/<basin>/<period>.parquet
  normalized/static_attributes.parquet
  normalized/threshold_history.parquet
  normalized/onsets.parquet
  cohorts/<cohort-id>/issues.parquet
  source_records.csv
  cohort.csv
project/
  methodology.md
  research_plan.json
  design/data_access.md
  design/estimands.md
  design/split_policy.md
  design/precision.md
  design/protocol_dependencies.md
  domain_audit/
  .factory/epoch_NNNN/...
```

These are planned paths, not a claim that the files already exist. Avoid a proliferation of hand-maintained registries when a single generated provenance table can express the mapping. Keep raw object hashes stable and never overwrite old downloads. The manifest may refer to local content addresses; a friendly provider filename must not be the only identity.

Every acquired object should record actual request URL/object key, resolved provider and version, retrieval start/end, HTTP status/headers where available, server modification metadata, byte length, raw SHA-256, source license/access conditions and a meaningful error state. Redact secrets from URLs/headers. Persist response bytes before transformation. Capture unsuccessful attempts and missing objects. A local file reuse record has `transport=local_reuse` and a parent hash; it is not a fresh HTTP 200 response.

Each normalized row links to one or more raw objects and an extraction record: provider variable, units, valid/aggregation start/end, availability time/basis, revision version, site/reach/catchment ID, source row index, decoding/aggregation transform version, observation/model origin, no-data/quality flag and coordinates/geometry version. Separate a provider-produced model product from a locally simulated series. Preserve raw source qualifiers rather than discard them once data are numerical.

Hashes prove byte identity. External authenticity additionally depends on the acquisition path, provider response, independently sampled extraction and semantic review. A malicious producer could still manufacture a correctly hashed file; state this boundary. Add impossible-source substitution tests and a negative control in which the advertised NWM input is replaced by observed discharge and must be rejected by the adapter's source-identity checks.

### 4.2 USGS hydrometry

The old implementation relies on WaterServices endpoints. As of this audit, USGS announced OGC API v1 in September 2026 and plans retirement of WaterServices in early 2027. Build the new acquisition adapter around current official API documentation and pin endpoint schema/retrieval dates. Recheck release notes when implementing; do not preserve a soon-retired API because old code already uses it. [USGS v1 announcement](https://waterdata.usgs.gov/blog/api-v1-release/), [official API guide](https://api.waterdata.usgs.gov/docs/ogcapi/).

Acquire monitoring-location metadata and distinct time-series identities for discharge/stage/statistic. Preserve leading-zero site IDs as strings. Verify parameter and statistic codes, unit conversions, no-data sentinels, qualifiers, provisional/approved status, timezone, valid period, and date aggregation semantics. A daily mean is not a value at midnight and not a daily maximum. Do not accidentally merge multiple time series into one day without a declared selection/aggregation rule. Query limits/pagination must be exhausted and verified with record counts/time coverage; a successful first page is not complete acquisition.

For exact onset and subdaily warning, obtain instantaneous stage with enough historical coverage and documented datum changes. Retain measurement outages, instrument changes, ice/backwater/estimated flags and exceptional quality conditions. Choose a quality policy before test: exclude, analyze separately or retain with flagged uncertainty, but do not replace unusual high water with a smooth typical value.

Use a bounded real-provider development acquisition first. Validate representative source rows manually against the saved raw response. Independently convert cfs to cubic meters per second if necessary using the exact defined factor; record both original and normalized units. The correct unit conversion does not authenticate the old NWM substitution. Cache long histories in site/period partitions and stream extraction instead of making every training run redownload observations.

### 4.3 Meteorological forcing

Choose catchment-area meteorology when available. Basin boundaries and gauge-to-basin mapping need source version, coordinate reference system and geometry checks. A station-cell proxy may be legitimate for a scoped comparison, but all models should receive the same declared opportunity or the difference must be reported. Areas/weights should sum as intended; non-intersecting/invalid catchments fail rather than fall back to a default coordinate.

Decode NetCDF with recorded scale_factor, add_offset, fill/missing values, unit metadata, time coordinate and grid coordinate orientation. Test one known packed slice and one decoded slice through separate implementations. Establish whether the serving endpoint has already unpacked the data. Reconstruct grid indexing from actual coordinate arrays; reject out-of-bounds sites. Correctly distinguish Kelvin and Celsius, daily total and rate, local-day and UTC interval. Do not silently round acquisition values to a paper's displayed precision.

Current historical gridMET is a final blended product. If an as-issued archive is absent, scope primary results as retrospective final-product analysis. Use an availability-assumption sensitivity ladder only with justified alternative delay distributions and a clear assumption label. Training/testing with later revisions can inflate replay utility; a fixed scalar delay cannot undo revisions. If operational validation is essential, use authentic archived vintages or start actual collection.

### 4.4 SWE and cryosphere

Do not initially attempt a full national raster download into 512 GB. Inspect product metadata, date coverage and storage cost using actual object listings and a bounded sample. Acquire/extract requested catchments or stream daily rasters, verifying that raw-cache eviction still leaves a reproducible object identity/source key. All sites for a date should share one retrieved raster when appropriate. Avoid fetching the same large raster separately per gauge.

Daily SNODAS must be date-specific provider output. Verify file selection, raster shape, projection, nodata and scale against product metadata. Extract/aggregate with independently validated spatial weights. Pre-product dates remain missing, not zero. Non-snow-influenced is a climatic interpretation, not proof that every day has zero SWE. Record product assimilation/forcing and known limitations. A locally modeled SWE series can appear only as a separately named simulation with parameter justification and its own validation.

If genuine daily SWE and operational vintages cannot be acquired within the study resources, preregister a no-SWE primary model and make the cryosphere extension conditional. Report a measured access constraint. Do not invent weather-derived SWE to keep a six-channel input tensor.

### 4.5 Static properties and threshold history

Use genuine site-to-catchment crosswalks and source tables. Preserve exact metadata fields and units; distinguish percent slope from fractions/degrees, square miles from square kilometers, stage height from elevation and gauge datum from geodetic datum. NID regulation needs a hydrologically relevant upstream relation, source date and meaningful classification. Spatially overlapping or nested catchments can create dependence between sites.

Threshold records need threshold type, value/unit, gauge/LID mapping, effective/known dates, source vintage, stage datum/rating applicability and uncertainty. A `producedTime` of the latest forecast is not automatically the creation/effective date of a flood threshold. Never default a missing vintage to 2024-03-27 or any convenient date. The NWPS API exposes forecast/observation and category metadata, but current fields alone do not reconstruct a decades-long threshold history. [NWPS API information](https://water.noaa.gov/about/api).

Build the primary truth with official minor flood-stage history only where defensible. Derive action crossing separately; later peak category does not remove earlier crossings. If historical thresholds are incomplete, a modern threshold applied to old stage is a specifically qualified retrospective target, not an operationally known historical threshold. Any train-only discharge-quantile target has a different name and cohort.

### 4.6 Actual NWM comparison

Fetch the provider's actual NetCDF/Zarr output and inspect version/time/feature coordinates before selecting records. Validate site-to-reach IDs using a documented crosswalk and location/topology review; legacy hand-written COMIDs are candidates, not verified IDs. Enforce correct hourly-to-daily aggregation and temporal coverage. Retain modeled-origin metadata even though the study cohort is observational.

NWM retrospective comparisons belong to a retrospective scenario with declared inputs/coverage; compare actual model output, not routing “physics” inferred from hydrometry. For a future warning target, decide how retrospective discharge is used: a streamflow forecast issued in advance is fundamentally different from concurrent retrospective model flow. It may be a contextual nowcast/analysis comparator, not a causal operational forecasting baseline. All claimed horizon parity must be demonstrated.

Search current genuine forecast archives if operational comparisons are desired, using issue and valid times, model version and assimilation status. An archive probe establishes only that a particular endpoint/object was unavailable, not global nonexistence of a forecast archive. If no suitable history exists, record that limitation and omit the comparison. Do not force the dataset dates to match the primary paper by filling gaps.

## 5. Cohort, splits and information filtration

### 5.1 Sampling frame and independent units

Start from a real public sampling frame. The old 54 IDs may seed a historical candidate list, but their claimed climate, reference and dam strata cannot define eligibility without verification. Generate the candidate/exclusion table programmatically from source coverage, geography, threshold support, quality and resolution. Report all exclusion reasons. Avoid choosing “good” basins after viewing future labels or model scores.

The statistical unit depends on the question: basin/network component for spatial population generalization; storm episode/water-year blocks for repeated temporal events; seed for conditional training variability; issue for issued prediction accounting; event for warning recall. Never multiply `number_of_seeds × number_of_overlapping_windows` into a population sample size. Floods across neighboring sites during one storm are correlated. Define connected catchment and storm grouping prospectively where feasible and quantify residual dependence.

Select a development panel, a validation panel and an untouched confirmation panel before modeling. The entire old 2019–2023 test design has been observed in the legacy work and this audit; merely rebuilding the old files does not create an untouched confirmatory test. Use newly withheld basins/regions and/or later untouched periods, documenting which aggregate metadata were inspected for feasibility. Define historical results as exploratory if reused. A new factory epoch preserves choices; it does not restore ignorance of previously inspected outcomes.

### 5.2 Evaluation settings

Recommended separate settings are:

| Setting | Available target-site history | Appropriate scope |
|---|---|---|
| Temporal forecasting at known gauges | Preregistered local past observations and calibration | Future periods at monitored sites; not unseen-site transfer |
| Spatial inductive transfer | No fitting to held-out basin labels/statistics; covariates as declared | New eligible catchments within the sampling frame |
| Warm-start spatial transfer | A fixed past-only calibration span at target sites | Adaptation to monitored new sites; explicitly account for history |
| Region/network holdout | Whole connected/region groups withheld | Transfer under a specified spatial shift |
| Retrospective final-product setting | Final historical products with retrospective scope | Historical associations/predictive skill under final data |
| As-issued/prospective setting | Authentic recorded vintage/availability | Actual operational information state, after separate validation |

Do not mix these settings inside one convenient split. A crossed space/time design helps separate spatial transfer from temporal climate shift; the legacy combined both into one estimate. Select one primary setting for feasible local computation and describe extensions as secondary.

### 5.3 Split construction and purge

Partition source records and sites/components before windowing and all fitted transformations. Do not let overlapping windows, copied raw objects, basin entities or storm episodes cross boundaries inadvertently. A validation/test input may use past context before an evaluation cutoff only under a declared forecasting-history policy; that context must not be used to fit held-out labels or new scaling. Avoid excessively rigid purges that remove legitimate history without reason, and document any purge length relative to lookback/horizon/storm overlap.

Disjoint site sets alone do not imply disjoint hydrological systems. Check catchment overlap, upstream/downstream relations and shared gauge records. Define group IDs as actual independence clusters. Test global time order if a temporal split is claimed. Use group-safe selection; class-balancing never permits moving future observations into training. Preserve natural test prevalence. If too few positive test events exist, add prospectively eligible data, narrow claims or report insufficient precision; do not resample positives to make the test look balanced.

Preserve stable row IDs throughout raw extraction, preprocessing, sampling, scoring and prediction. Every join must declare expected cardinality and check dropped/duplicated/unmatched IDs. One-to-many raw provenance is acceptable when explicit. Label or score defaults for unmatched IDs are forbidden. Content duplication must not be counted as a new observation.

### 5.4 Per-record filtration

For every feature actually consumed at issue `t`, require `observation_end <= t` and `available_at <= t` for the chosen vintage. For forecast forcings, their own issue time must be <= the prediction issue and their valid interval may be in the future; classify them as issued forecasts rather than pretending they are observed weather. The current `Observation` primitive intentionally represents completed observations; add a distinct reviewed forecast-record type if using NWP.

Run issue-time filtering before aggregation/windowing. Aggregates carry maximum constituent availability and all raw parent IDs. Imputation, smoothing and normalization cannot use later records. All calendar effects must derive from the known issue calendar. Batch caching cannot accidentally expose a final revised whole-record table to an earlier as-issued prediction. Include suffix/value and availability mutation tests that traverse the entire data-to-prediction path, not only the neural network.

The declared `data_origin='observational'` for factory cohort/source records describes the observational research cohort. Actual NWM/SNODAS/model products have their own origin in domain provenance. The native factory uniform source-origin schema is insufficient for a rich mixed observation/model evidence graph; implement a lossless adapter and retain the richer records. Never call local generated values observational just to satisfy the native schema.

## 6. Learning, scoring and uncertainty-aware prediction

### 6.1 Preprocessing choices

Freeze transformations on raw train observations, channel definitions, basin weights, clipping/log rules, imputation/missing indicators and outlier handling. Standardize daily channels using daily distributions. A `log1p` discharge transform can be reasonable for skew but needs units, nonnegative-domain checks and a physical rationale; it must not be chosen because it improves the observed test AUC. Do not pool raw stage values across incompatible gauge datums without an explicit relative-stage or per-site policy.

Missing data treatment should preserve signal absence. Use observed masks, quality masks and age-since-observation features where justified. A completely absent required source fails acquisition. Missing individual observations may be excluded or imputed from training-only parameters with masks. Causal forward fill needs maximum age, source-specific justification and uncertainty; backward fill is excluded from online filtration. Include missingness-specific evaluation and a simple missingness-only classifier as a diagnostic for acquisition artifacts.

The migrated `Normalizer` is intentionally narrow: it accepts an already identified matrix of unique raw training rows. It cannot verify which split a caller actually selected. The production adapter must hash/join those row IDs to the frozen split. Its train-median fill and the neural model's masked-zero representation are explicit preprocessing decisions; record both, including which representation is consumed by each model. Channel dropping due to zero variance is explicit, not a fabricated variance floor.

### 6.2 Self-supervised objective

Choose one primary self-supervised method with a precise mathematical target. For masked reconstruction, sample a training corruption mask `M` only within genuinely observed targets `O`, compute the model input using visible observations, and optimize:

`L = sum_{b,t,c} M_btc O_btc (xhat_btc−x_btc)^2 / sum_{b,t,c} M_btc O_btc`.

Reject batches with no observed withheld targets or resample masks under a declared deterministic policy; never quietly record zero loss. Log counts/coverage per channel so a mostly missing sensor cannot dominate by being imputed. A mask indicator and observation-availability indicator have different semantics; avoid teaching the model that missing SWE is measured zero.

The new leave-channel-out scorer hides a physical channel throughout a supplied available prefix and evaluates only observed targets. It does not use the target's visible value inside the encoder. The training corruption distribution must include the intended structured channel/temporal masks or any distribution mismatch must be explicitly investigated. Another valid design is a one-step/horizon past-only forecasting head; if selected, train and validate that actual operator. Do not add several scores and choose the best on test.

The causal architecture can be a control or candidate. Per-time LayerNorm is causal; normalization across the time dimension can leak. Causal conv receptive field depends on two convolutions per block: for kernel size `k`, two convs and dilations `2^i`, the TCN stack receptive field is `1 + 2(k−1) sum_i 2^i`, subject to actual residual wiring. Attention may see the entire available prefix; do not mislabel this as a short finite TCN receptive field for the full hybrid. Verify receptive field by perturbation and gradients.

Do not equate positional masking with scientific causal identification. “Causal” means temporal filtration in this model, not proof of a causal physical mechanism or intervention effect on flooding.

### 6.3 Learned anomaly scores

Predeclare which score is primary. Candidate reconstruction scores require target withholding, channel weighting and missing-target coverage. Latent distance requires a genuine train/calibration reference mean/covariance and conditioning diagnostics. Latent-step change is a temporal derivative. A future-prediction residual needs a separately trained predictor. Report operator names matching execution.

Tune reference/shrinkage/scale choices on development data only. The migrated covariance primitive requires positive shrinkage and rejects collapsed representations. An arbitrary diagonal floor may be a modeling regularizer if frozen and sensitivity-tested, but never an undisclosed invented calibration variance. IQR calibration cannot use one sample; unstable scale must be a flagged failure or a justified alternative.

Per-site calibration needs a sufficiently long pre-evaluation span and a declared minimum number of distinct issue observations plus support/precision analysis. Overlapping windows are not independent calibration samples even when their row count is large. For uncalibrated unseen basins, use a train-fit global/reference model or report unavailable; do not silently use target-year statistics.

### 6.4 Probabilities and the factory profile

Raw anomaly scores can be negative or unbounded. They are not probabilities. Brier/log loss require a fitted probabilistic mapping. Do not min-max normalize on test or apply a sigmoid chosen only to force the native schema into [0,1]. Monotone score transforms preserve within-setting ranks but can change pooling/site comparability, thresholds and proper scoring rules.

If predicting event probability, fit a declared logistic/isotonic or other calibration mapping on a separate labeled calibration set with leakage-safe cross-fitting or sample separation; count those labels in the label-efficiency story. Validate reliability with sample-support-aware intervals and proper scores. For zero-event-label methods, retain raw scores and ranking/operating-point evaluations via a domain adapter; do not publish arbitrary Brier/log loss as calibrated probability performance. A frozen unlabeled quantile alert threshold is a detector operating rule, not a calibrated probability.

The native factory binary profile may certify a legitimate probability-output subset of the study. It cannot, without extension, certify raw-score warning utility, interval-onset survival inference or basin-population generalization. Build that extension with independent recomputation and tests; never let schema convenience choose the scientific task.

### 6.5 Training protocol

At least five independent preregistered training seeds per trained condition, as required by the supplied factory's enforced policy. Record Python/NumPy/PyTorch seeds, DataLoader/worker seeds, mask stream seeds, split/subset seeds separately and backend deterministic settings. Seed identity represents training variability conditional on data; it is not an independent hydrological sample.

Use genuine validation masked/supervised losses and prespecified checkpoint selection. Record full epoch/batch-weighted loss, target counts, validation loss, optimizer/scheduler settings, learning rate, gradient diagnostics, initial weights and selected checkpoint hash. Weighted loss summaries must not average differently sized batches without accounting for eligible targets. Use validation early stopping with a minimum viable optimization budget, patience/min_delta selected prospectively, and a maximum budget disclosed as a cap. Record exhaustion without convergence as an inconclusive training result, not successful completion.

The active v3.3 parser requires at least two declared minimum epochs for trained modes; fixed-budget modes also require two tail windows. The audit checks the registered history/stopping rule, not a universal ten-epoch guarantee. Factory prose/history mentioning ten epochs must not be promoted into a scientific convergence criterion. Validate learning with a controlled overfit test on development observations, train vs validation trajectories, correct target masking, noncollapsed representation diagnostics, and extended-budget sensitivity. Such tests are engineering/development evidence, not test performance claims. Prohibit label leakage via direct function access and source/ID tracing; an AST search for the word “label” cannot prove isolation.

The Implementor must not retain only the best seed. Preserve failures, nonconvergence, device fallback, interrupted execution and rejected attempts. Do not combine checkpoints trained with different data/configuration under one claimed seed. Resume requires complete optimizer/RNG/config/data state and an explicitly recorded attempt policy.

## 7. Comparator fairness and label efficiency

### 7.1 Minimum useful baseline ladder

Include a meaningful simple baseline before a complex network:

- Natural-prevalence/seasonal prior probability or a deterministic no-alert policy, with the appropriate endpoint and honest no-training evidence.
- True persistence or calibrated current stage/discharge relative to threshold. Rate-of-change is a separate rising-flow baseline; do not call it persistence.
- Train-fit seasonal climatology with adequate historical support and correct leap-year/circular day handling.
- Causal EWMA/CUSUM with continuously carried state and fixed/tuned development parameters, not reset every overlapping window.
- Regularized logistic regression or a tree-boosting model on causal recent-flow/weather/missingness features, with development-only tuning.
- A well-trained LSTM/EA-LSTM where genuine static attributes exist, plus a dynamic-only LSTM when they do not.
- A mechanism-matched reconstruction/forecasting alternative, such as a TCN-only or LSTM autoencoder trained under the same observation/masking protocol.
- Actual NWM output in a clearly scoped retrospective or forecast comparator setting, only if authentic coverage exists.

A current credible method should be selected from the literature/code review at freeze. Do not insert “current” as a label on an old untrained model. Baseline categories in factory metadata must reflect actual role/reference. NeuralHydrology implementations are potential reference paths; verify exact version, target adaptation and hyperparameters rather than imply that the migrated EA-LSTM primitive reproduces the original regression study.

### 7.2 Fair opportunity rather than identical arbitrary hyperparameters

Declare data opportunity, label budget, validation labels, unlabeled pretraining, target-site history, hyperparameter trials, wall-clock/device opportunities and inference latency separately. All comparators share issue/target/coverage and primary test IDs where their comparison claims require it. A method requiring extra inputs has a named input setting or a restriction, not a hidden advantage.

Use algorithm-appropriate validation optimization. Identical learning rate/epochs across architectures is not necessarily fair, while dramatically smaller comparator data/budget is not parity. Give each trained model a convergence/optimization check. Report parameter count, training observations, eligible targets, optimization steps, validation trials and measured time. If full parity is unaffordable, restrict the claim to the measured budget and disclose unmatched resources.

Freeze threshold selection with a validation-only false-alert/utility procedure applied to the **same score aggregation** later used on test. The legacy terminal-score quantile applied to a max-seven-day score violates that consistency. Quantile thresholds fitted on an event-enriched validation subset do not identify a natural-exposure false-alert rate. Use complete validation issue streams.

### 7.3 Label-efficiency design

Define what costs a label: independent onset episode, site-day annotation, event catalog acquisition or individual binary issue. Thousands of overlapping windows from one labeled flood do not mean thousands of independent labels. Publish actual positive/negative event counts, basin coverage and label acquisition assumptions for each budget.

Create nested label subsets from training only so higher budgets include lower-budget labeled units where the design permits. Repeat subset draws independently of model initialization, preserving both random factors. Freeze their IDs, do not resample until each subset looks favorable, and retain zero-positive/degenerate subsets as design outcomes. Specify whether all unlabeled training observations are available to every method; supervised methods may have a corresponding SSL initialization control.

Train a seed ensemble of the SSL method too. Compare paired conditions on the same untouched test corpus with uncertainty over seeds and independent basins/events, not one fixed SSL checkpoint against five supervised initializations. “10% labels” must identify the denominator and absolute counts; never quietly restrict that denominator to 1,200 convenient windows. Validation/calibration labels are counted or clearly declared shared fixed overhead.

Treat non-inferiority/equivalence as separate designs with practical margins and prospective precision. A label-efficient negative finding could be that SSL fails to improve on a simple supervised baseline at small verified label budgets, with intervals tight enough to bound a useful effect. If intervals are wide, the result is inconclusive; do not turn lack of significance into a publication-friendly negative statement.

## 8. Statistical analysis that answers the declared question

### 8.1 Separate three sources of uncertainty

Algorithmic variability across initialization seeds, variability across flood events, and generalization to new basins are different quantities. Repeating a model five times on seven positive rows does not create 35 independent floods. Multiple gauges on the same river and multiple overlapping issues for one storm are correlated. The native factory's `seed_fixed_test` interval is conditional on the fixed test corpus; label it that way. It cannot establish population generalization by itself.

Construct a basin/river-network grouping from authentic geometry and connectivity before splitting. Record nested gauges, shared storms and cross-basin dependence. Use a scientifically justified independent unit, such as independent river systems with event nesting, for the primary population interval. With few independent systems, show their individual results and acknowledge limited precision. A block length is chosen from temporal dependence and the estimand, not from a convenient row count. Resampling alphabetically sorted gauge IDs in adjacent groups is not spatial resampling.

For paired methods, compute both methods on identical eligible units and resample paired units together. A hierarchical bootstrap can sample independent systems, then eligible events/exposure blocks within systems, then paired seed replicates if the target averages training variability. State exactly what is randomized at each level. Keep a deterministic reference implementation and compare with an independent implementation on constructed examples. The migrated `paired_cluster_interval` only bootstraps supplied cluster differences; it does not determine hydrological independence or substitute for a hierarchical design.

### 8.2 Precision and a practical effect before expensive training

Choose a primary endpoint, an operating constraint and a smallest practically relevant improvement with a hydrologically defensible rationale. Examples are additional independent flood episodes warned within the target horizon at the same false-alert exposure, or earlier useful warnings at comparable recall. Specify a practical degradation bound too. Do not choose margins after seeing effect estimates.

Use development-only counts, prevalence, dependence and pilot variability to simulate precision under plausible null, small benefit and degradation scenarios. Simulated precision calculations are explicitly simulation artifacts with generators, parameters, seeds and assumptions; they are not flood observations. A binomial interval on independent episode recall can be a first approximation, but dependence and threshold estimation require a fuller calculation. AUROC precision alone does not guarantee precision of operational recall or false-alert rate. Publish the range of required independent systems/events under the assumptions, and the achievable precision under the available corpus.

If the data cannot bound a practically important effect, reduce the scope or report a feasibility study. Do not compensate by generating extra window rows, claiming overlapping negatives are independent, weakening the minimum effect, or treating unavailable outcomes as negatives. The factory's schema floors are mechanical minimums, not a power calculation.

### 8.3 Endpoint definitions and estimability

For issue-level discrimination, retain every eligible issue under the frozen coverage rule and report positive count, negative count, prevalence, number of independent episodes, basins and exposure duration. AUROC requires both classes. Average precision with no positive support is undefined for this project, and its prevalence dependence must be explained. Report a null value plus an explicit reason for an unestimable metric. Do not use 0.5, zero or a removed gauge as a successful substitute. Aggregate metrics only over a declared estimable population and show which units are excluded from each metric.

Macro-basin and pooled micro metrics answer different questions; neither is universally superior. A pooled metric can be dominated by large/long-record basins; macro metrics can give an extremely sparse site equal weight. Report the chosen primary weighting and relevant alternatives with support counts. Where a basin has no observed flood, false-alert exposure is still estimable even if basin AUROC is not. Do not drop its negative exposure from operational evaluation.

Brier score and log loss require probabilities for the declared future label, not raw anomaly magnitudes. A calibrated anomaly-to-probability mapping must be fitted on development/calibration labels only, with support counts, reliability diagnostics and uncertainty. Small calibration sets may make probability claims impossible. The native factory expects probability-like prediction values; implement a reviewed separate ranking-score adapter if justified, rather than normalize arbitrary scores until the gate passes. A decision threshold tuned to a false-alert constraint is a different object from probability calibration.

### 8.4 Continuous alert evaluation and warning time

Run the actual issue cadence continuously. An alert is emitted at the issue when the persistence/confirmation rule is satisfied. Define cooldown, merging, resets after missing data and recovery from ongoing floods. Match alerts to episodes with a fixed one-to-one policy, maximum look-ahead horizon and explicit handling of overlapping event intervals. A duplicate warning for an already matched episode must not count as an additional detected flood.

For exact onset, warning time is onset minus the first **confirmed** matched alert. For interval-censored onset `(L, U]`, report the compatible warning-time interval `(L - alert, U - alert]`; the interval may straddle zero. Do not replace it with noon or its midpoint as an exact observation. A left-censored episode cannot establish a new onset during the observation window. Keep missed episodes in recall and clearly label any detected-only warning-time summary as conditional. Missing detections do not have a measured zero warning time.

Report false alerts per monitored basin-time with denominator derived from actual eligible exposure, event recall, number of warnings, missed episodes and warning-time distribution. State whether exposure excludes ongoing flood periods and why. At a fixed alert budget, threshold estimation and its uncertainty must be part of the analysis. Include a no-alert policy and a current-condition baseline to reveal whether useful advance warning is achieved.

Do not make a survival or restricted-mean-warning-time claim using an ordinary classification table. Such a claim needs a defined risk set, time origin, censoring mechanism, competing events if relevant, interval-censoring handling and assumptions about informative missingness. Add a domain adapter and independently recompute the endpoint before using it. If that is not feasible, retain the more transparent recall/false-alert/interval-warning analysis.

### 8.5 Hypotheses, multiplicity and reporting

Maintain a hypothesis register with ID, estimand, direction, endpoint, eligible population, effect scale, practical margin, uncertainty method and confirmatory/exploratory status. Select a small confirmatory family. Freeze the multiple-comparison correction across all primary method contrasts and primary endpoints that jointly support the headline claim; Holm is available as a primitive. Secondary sensitivity/OOD results are labeled exploratory or placed in a separately justified family. Do not split a family after seeing its p-values.

Report raw and adjusted p-values where meaningful, effect estimates and compatible intervals. Five paired seed differences produce very coarse sign/permutation inference and address initialization, not event independence; never advertise their nominal significance as broad basin evidence. A large improvement with a wide interval is uncertain. A non-significant test does not establish equivalence. Equivalence/non-inferiority requires an appropriate predeclared margin and interval/test, adequate precision, and a valid comparator.

Predeclare a reporting policy for all planned experiments, failed seeds, training divergence, unavailable baselines and missing source coverage. The result table includes failures and reasons. Test-driven amendments move the affected claim to exploratory status or require a genuinely fresh held-out cohort and a new plan epoch. Keep the original record; never erase the unsuccessful attempt to restore apparent preregistration.

## 9. Ablations, sensitivity, out-of-distribution evaluation and falsification

### 9.1 A trainable factorial design

Use a small justified design that separates temporal convolution, attention and pretraining. At minimum, compare the full architecture with appropriately retrained TCN-only, attention-only and a matched recurrent/control model. Add a no-SSL initialization control and a masking/observation-indicator control. Declare whether parameter count, training compute or architecture family is matched; report the unmatched dimension rather than imply simultaneous parity.

Every architecture condition must train its own missing/hidden-target protocol, normalization, latent reference and alert calibration. A checkpoint may be transferred only with a named transfer-learning hypothesis and a recorded compatibility map. Newly initialized layers are trained under that protocol. Copying a subset of layers into a larger untrained model and calling its loss an ablation is forbidden. Sensitivity to pretraining corruption rate requires actual retraining at each rate; test-time corruption is a distinct robustness experiment.

Register the conditions, seeds, trial budgets and stopping criteria before confirmatory execution. If a complete factorial exceeds the laptop budget, choose a smaller scientifically motivated set before looking at outcomes. Use interactions only where the design and precision support them. Do not select the most impressive single seed/condition for the headline figure.

### 9.2 Development sensitivity and held-out stress sets

Sensitivity axes may include causal lookback, forecast horizon, latency scenario, calibration support, missingness, confirmed-alert cadence/persistence, scale/covariance shrinkage and event separation. Each axis needs a plausible range and scientific justification. The point selected for primary testing is selected from development data only. Test-set sensitivity is reported as a frozen grid, not a second optimization loop.

Create OOD strata from source-grounded descriptors: season, basin size, regulation, climate/snow regime, observation coverage, extreme discharge and geography. Do not derive a “snow basin” class from a synthetic SWE generator or default coordinates. Distinguish a held-out basin, a held-out time period and a rare-event severity stratum; these are different shifts. An OOD stratum with inadequate labels remains descriptive. Table every stratum's exposure and support before estimating performance.

Missingness tests must separate naturally missing data from constructed perturbations. Constructed outages have a disclosed mechanism and seed, and cannot become observational evidence. For timing perturbations, shift only inputs that could arrive late, preserving the original source time/availability fields. Track whether an observed deterioration comes from altered coverage, altered labels, or model behavior. Negative controls should test the exact failure mechanism they are intended to detect.

### 9.3 Required adversarial scientific checks

Create a domain integrity suite that deliberately introduces the following mutations and confirms rejection or a documented change in the correct output:

| Mutation | Required response |
|---|---|
| Input observed or released after issue time | Reject the sample or exclude the record; never silently include it. |
| Revised observation substituted for a stored vintage | Manifest/hash mismatch and a distinct final-data setting. |
| Gauge-derived series relabeled as independent NWM | Provenance/type violation; comparator cannot run under that name. |
| Unknown latitude/area filled with another basin's value | Missing authentic attribute; explicit exclusion/dynamic-only method. |
| Missing numeric observation changed to an observed zero | Different observation mask and loss eligibility. |
| Normalizer/calibrator fitted with a test row | Split-boundary violation and failed audit. |
| Hidden reconstruction target copied into a visible input channel | A hook/gradient test detects exposure; objective fails the contract. |
| Value after a requested prefix changed | Past causal outputs unchanged within declared tolerance. |
| Entire prediction day/site omitted | Coverage audit fails; missing rows cannot improve the denominator. |
| Two alert points separated by a cadence gap | Confirmation counter resets. |
| Event whose peak category exceeds action excluded | Action-crossing episode coverage test fails. |
| Peak date plus arbitrary hour substituted for interval onset | Label provenance/interval semantics reject exact-onset claim. |
| Constant score or single-class test subset | Honest degeneracy/undefined metric, without a neutral pseudo-result. |
| Extra successful replay counted as a new seed | Reproduction status; no extra independent trial. |
| Duplicate/nested basins split across train/test contrary to setting | Network-group check fails. |
| Test label shuffled | Ranking/calibration/operational metric changes as expected; no fixed table. |
| Source content changed without updating a digest | Freeze/source-chain failure. |
| Experiment exits zero without complete predictions | Runtime success does not become scientific completion. |

Use tiny disclosed construction fixtures for these software checks; their expected answers come from independently reasoned examples. Keep them outside observational source/cohort tables. Supplement unit tests with a lossless export/recompute check against a second implementation and manual inspection of randomly selected real episodes. A large number of mirror-image tests is not an independent scientific audit.

## 10. A measured execution plan for the M3 MacBook Air

### 10.1 Resource assumptions and pilot decisions

The user-supplied machine has an ARM M3, 8 CPU cores, 10 GPU cores, 16 GB unified memory and 512 GB nominal storage. Those are planning inputs, not measured free capacity or performance results. Record actual OS, Python, accelerator availability, usable/free storage, active memory pressure and thermally relevant conditions at execution. The Air's sustained performance must be measured; a short synthetic tensor forward pass cannot predict a long training run.

Start with CPU correctness and a small authentic development shard. Compare CPU and MPS outputs/gradients within scientifically justified tolerances and record unsupported operations. Freeze a fallback policy in advance. Set all relevant RNG seeds and document deterministic settings and residual backend nondeterminism. Mixed precision is a measured optional condition, not a default that silently changes the numerical protocol. If MPS cannot meet reproducibility/tolerance requirements, use CPU or a separately declared backend setting.

Measure one complete training configuration including acquisition decode, batching, forward/backward, optimizer update, validation and checkpoint writing. Use the actual objective and representative sequence lengths/missingness. Include warm-up, repeated measurements and sustained runs. Measure batch-one inference at the operational input shape with device synchronization where required. Report p50/p95 and throughput separately, along with failed/out-of-memory attempts and units.

### 10.2 Memory and compute controls

Stream site/time chunks from columnar files; do not materialize every overlapping window as an independent dense array. Use causal slicing at access time, train-fit normalization and a cached validity/index table. Cache normalized data only under a digest of raw records, split, normalizer and feature policy. Keep a cap on loader workers and prefetch buffers; excessive workers can exhaust unified memory on this device.

Standard attention memory grows roughly with batch × heads × time² per attention matrix; layers/backward increase it further. Model parameter memory is separate: float32 parameters, gradients and two Adam moment arrays alone require about 16 bytes per trainable parameter, before activations/workspaces. These are analytical planning estimates, not measured peaks. Profile actual allocations and total process/system pressure. Start with a modest batch and increase only after measured headroom. Gradient accumulation, shorter lookbacks or a simpler architecture are preregistered resource adaptations with stated scientific implications.

Do not prescribe arbitrary epoch counts as evidence of convergence. The development pilot determines feasible optimization steps, validation frequency, early stopping patience, best-checkpoint rule and trial budget. Record loss by step/eligible target, validation score, learning-rate schedule, stopping reason and resource usage. Non-monotonic training is possible; a decrease from first to last loss alone proves neither convergence nor a useful representation.

Use an explicit budget ledger: configuration × seeds × expected measured step cost, plus validation, baseline optimization, ablations, replay and data preparation. Apply a measured contingency for sustained thermal performance and failures. If the resulting budget is unacceptable, simplify the design before freeze and limit the claim. Do not truncate a poor-performing baseline earlier while allowing the proposed model extra training. Run seeds sequentially on this laptop unless measured headroom and reproducibility support concurrency.

### 10.3 Data/storage strategy

Query the needed USGS sites/time ranges and gridMET basin/time subsets. For SNODAS and NWM, estimate full source/subset size from authentic metadata before downloading; their national archives can exceed local capacity. Prefer traceable remote subsetting/read-only streaming with version identifiers and save the exact raw objects/chunks actually used. If an immutable vintage cannot be preserved or retrieved, disclose that reproducibility limitation and reconsider its role. Do not claim a full national data product was archived locally when only a small sample exists.

Keep raw data and large checkpoints out of ordinary Git. Publish manifests, acquisition code, license/access instructions and small lawful reference examples. Use a suitable versioned public repository for redistributable study artifacts at submission, or provide a lawful retrieval path plus checksums if redistribution is restricted. Git LFS is optional with an actual quota/cost review; never assume free unlimited storage. Retain local failed attempts/checkpoints under an explicit retention policy and back up irreplaceable vintages before cleanup.

Monitor available disk before each stage and require a reserve based on the pilot's peak temporary use and the operating system's needs. Record actual bytes, compression and temporary duplication. Do not choose a confident “fits in 512 GB” statement from the nominal disk label. An initial space/time/resource audit is a deliverable; if it fails, reduce scientifically redundant inputs or arrange storage before running the study.

### 10.4 Hardware evidence boundaries

Factory hardware checks require at least five trials and at least 30 seconds of sustained measurement; this is a schema floor. A thermal/long-training claim needs a substantially relevant sustained workload, selected from pilot evidence, and the actual completed training history. Training and inference peak-memory scopes are separate. MPS allocator statistics, process RSS and total unified-memory pressure measure different things; record their meanings rather than add or interchange them.

Use a monotonic clock, synchronized accelerator timing and documented warm-up. Battery/AC state and simultaneous workload should be recorded for repeatability. If accurate energy sensors are unavailable, omit energy-efficiency claims. Extrapolated “two-hour training” from a tiny batch is labeled an estimate and cannot establish completed training or publication-ready efficiency. The final reproducibility experiment runs from an empty environment/data cache as far as lawful retrieval allows and reproduces the claimed artifact pipeline, not merely a model forward pass.

## 11. Software Factory v3.3 integration contract

### 11.1 Preserve the supplied factory and its evidence boundary

The supplied active version is `factory/VERSION = 3.3.0`. Its active source was not changed by this migration. `factory/legacy/v2_6_0/` and the supplied `docs/` include factory history and a forensic demonstration for another project. They are not Flood Sentinel observations, experiments or certification. Keep their context explicit; never cite their sample counts/training logs as this project's results.

Read `factory/constitution.md`, `SCIENCE_PROTOCOL.md`, `architect_spec.md`, `implementor_spec.md`, `gatekeeper_spec.md`, `AGENT_WORKFLOW.md`, the schema template and relevant engine code. The intended lifecycle is plan → challenge → freeze → supervised execution/record → audit → evidence-bound review → certify → handoff → independent bundle verification. Mechanical completion is necessary where applicable but is not a substitute for source authenticity, correct hydrology or sufficient statistical precision.

The current `project/research_plan.json` is deliberately a **draft**, with no fabricated experiments, cohort or claims. Do not freeze it yet. No Flood Sentinel certification was produced. The migrated dependency file is an exact snapshot of installed package versions, explicitly not a resolver-produced hash-verified lock or evidence that all packages are needed. P00 below resolves runtime/dependency issues before a valid research freeze.

### 11.2 P00: resolve runtime execution before planning a large study

Inspection of `factory/engine/contract.py` and a direct probe found that `python-cpu-v1` resolves to the current interpreter with `-I -P -B -S`. `-S` excludes normal site-packages and isolation excludes the script directory from automatic imports. In this environment, `import numpy` under those flags fails with `ModuleNotFoundError`. A NumPy/PyTorch runner will therefore not execute by copying a conventional training script into the template.

Design a reviewable dependency loading/runtime solution: for example an explicitly allowed, hashed dependency root and frozen loader that imports only verified packages and the frozen engine, with the contract recording the interpreter/environment. Determine whether this can be expressed within v3.3's constraints; otherwise add a versioned domain/runtime extension with independent review. Preserve isolation goals and the supervisor. Do not globally remove `-I/-S`, set a hidden `PYTHONPATH`, switch to arbitrary shell execution or bypass audited execution to make imports work. The loader must be frozen, and its dependency hashes/interpreter must be checked before execution. Wheel hashes and platform/ABI compatibility must be recorded for the actual ARM environment.

The current contract appends typed argument dictionary **values** in sorted-key order as positional arguments. For example keys `experiment_id`, `run_dir`, `seed` produce `E01`, the resolved run directory and the seed, with no option names. The audit independently compares the resulting argv against `experiment.command` literally, including interpreter, isolation flags, substitutions and order. Provide a runner with this actual positional interface, or extend the contract with an audited named-argument interface. Test plan/contract/receipt round trips, including spaces in this project's path. Do not assume the older `python script.py --seed ...` command matches typed execution.

The typed `network = disabled` declaration does not itself implement OS network isolation. Document enforced versus declared properties. The experiment runner should consume frozen local inputs and not acquire live/revised data during model execution. If a no-network claim is required, add a verified enforcement mechanism with a test that attempted network use fails. Resource limits in the contract are best-effort platform mechanisms, not measured hardware evidence. Inspect macOS support and failure reporting before relying on them.

P00 acceptance: a tiny **non-scientific** smoke fixture executed through the real supervisor loads the frozen engine/dependencies, emits complete receipt/prediction artifacts, passes argv/hash checks, records a failed import/hash mutation, and is classified as a fixture rather than observational evidence. Then execute one small authentic development-only experiment through the same path. No final claim depends on the fixture.

### 11.3 Domain/schema gaps must have lossless adapters

The native binary-classification cohort requires `sample_id`, `label`, `group_id`, `split`, `source_ids`; source IDs are pipe-separated references to registered source records. Source-origin declarations must reflect reality. A single file containing training and test observations cannot simply be declared a single source reused across splits when the source-overlap guard disallows it. Create lossless record-level/time-slice source identities linked to parent bytes, actual row selection and deterministic decode, or extend the domain representation with explicit audited ancestry. Do not duplicate/rename the same raw bytes to manufacture split independence.

The domain representation also needs issue time, observation and availability intervals, immutable vintage, basin/network group, label interval/evidence, coverage, warm-up eligibility, calibration versus training role and alert/exposure relationships. These must be audited even when they are extra CSV fields. Calibration or causal target-basin history cannot be smuggled through the test table as ordinary training. A transductive/adaptation setting needs its own explicit permissions and estimand. Mixed observational labels/model-derived inputs need truthful typed records; a global `observational` string does not turn NWM simulations into measurements.

Unbounded ranking scores, event/exposure metrics, interval-censored warning times, hierarchical population inference and equivalence are not fully represented by the current native profile. Add a versioned adapter for each needed extension, with a declared input schema, lossless conversion, complete hashes, independent numerical recomputation, failure/mutation tests and review. If an adapter is not available, restrict the claim to the native profile's actual scope. Factory `seed_fixed_test` certificates cannot be used as proof of population-level event inference.

Do not weaken minimum counts, origin checks, missingness checks or freeze checks to fit a sparse study. Native validation enforces at least five paired seeds for comparisons, at least two test groups and at least two examples of each class in each train/validation/test split; fewer than 30 test groups raises a diagnostic. These are mechanical floors, not proof of independent data or adequate power. Five identical repetitions of a deterministic baseline may be required for interface parity, but must be identified as the same deterministic result with no training-seed uncertainty. They must not be counted as five independent scientific observations. An appropriate adapter can represent deterministic comparators without pretending they are stochastic.

### 11.4 What goes into the eventual frozen plan

Populate the real plan from verified acquisitions and development evidence, not placeholder target numbers. Each native experiment entry has a stable ID and one scalar seed; encode each method/condition/seed execution as a distinct entry and pair their IDs explicitly. Record role, model/method identity, genuine baseline citation where applicable, exact code/data/dependency paths, execution contract and matching command, training/validation/test IDs, preprocessing/calibration objects, stopping rule, corruption/label budget and expected artifact schema. “Expected” means format/coverage invariants, not a desired improvement or fixed metric.

Comparisons identify paired experiments, metric/direction, effect scale, alpha/multiplicity, sampling unit and practical minimum effect. Analyses register failures, OOD strata, sensitivity and retrained ablations, with complete condition membership and the appropriate adapters. Claims list what observation would support, refute or leave the hypothesis inconclusive; the default state is untested. Hardware claims point to measured trials on the actual device. Release files are explicitly hashed. Frozen paths include the actual source, acquisition/adapter definitions, relevant manifests/cohorts and methodology; huge external data are represented by immutable verified references with a replay policy.

Every seed result has predictions for all required sample IDs, labels identical to the frozen cohort, finite scores/probabilities of the correct type, timestamp/eligibility trace and method evidence. Store receipts, stdout/stderr, training/validation traces, configuration, checkpoint digest, all failures and the best-checkpoint selection rationale. A metrics summary JSON is a derived convenience, not the source of truth. Recompute headline metrics independently from exported rows. Audit plot inputs as carefully as table inputs.

### 11.5 Freeze, amendments, review and handoff

Run the actual factory self-tests after any factory extension and record the environment/exit status. During this migration all 276 supplied active self-tests passed outside the restricted filesystem/network sandbox; the first restricted run's single Unix-socket permission failure is recorded, not hidden. That validates the supplied test suite's expectations, not hydrological correctness or future adapters.

After the Architect/Implementor challenge is resolved, freeze before confirmatory execution. If a bug changes labels, cutoff, source coverage, objective, thresholds or metrics, stop the affected claim, preserve the old plan epoch and failed evidence, and preregister a repaired epoch. Assess test exposure explicitly. A code-only patch can still invalidate untouched-test status if its choice was informed by outcomes. Do not retroactively edit plan bytes or delete receipts to produce a green gate.

The evidence-bound review follows the template's nine checks and at least three concrete objections, with specific artifact hashes, responses and surviving limitations. Disclose when reviewer and implementor are the same model/person or share context; seek independent hydrology/statistics review where the claim needs it. Certification wording must state the covered profile, estimand, conditional/population scope, adapters and unresolved limitations. No “scientifically verified” banner based solely on passing structural checks.

Produce the factory handoff ZIP and verify it from a clean destination using `verify-bundle`. Also test that the receiving agent can reconstruct environment/data selections and run the relevant analysis without absolute paths into the old folder. Repository version, factory version, plan epoch and source/checkpoint digests must be distinguishable; a single commit ID cannot stand in for all of them.

## 12. Ordered implementation contracts for the Architect and Implementor

Treat the following packages as dependency-constrained work. Their completion is based on the listed evidence, not optimistic prose. Each work package gets a brief issue/decision record, exact changed paths, validation output and remaining limits. The initial engine migration is already present; improve it only when a new contract or justified failure requires it.

### P00 — Runtime, dependencies and domain-interface feasibility

**Inputs:** this plan, active factory code, `project/audit/factory_compatibility.json`, migrated engine/tests and the actual ARM Python environment. **Depends on:** none.

**Work:** resolve isolated third-party/package imports, exact typed/legacy argv agreement, dependency/interpreter hashes, permission/resource semantics and schema gaps. Write `project/decisions/P00-runtime.md` and a versioned domain schema proposal. Produce a minimal supervisor smoke fixture and a hash-verified platform lock. Record which native gates and which proposed adapters enforce each scientific invariant.

**Acceptance:** the real supervised round trip passes without gate bypass; import/hash/argv mutations fail; all supplied factory self-tests and relevant new extension tests pass. The fixture never enters observational cohorts. **Stop:** no defensible runtime or adapter can preserve required evidence; resolve the infrastructure before training.

### P01 — Source feasibility, rights and sampling-frame inventory

**Inputs:** official provider documentation, target geographic/temporal scope and user resource constraints. **Depends on:** P00's representation decisions; acquisition exploration can proceed in parallel conceptually without model/test work.

**Work:** implement small genuine USGS/NWPS/gridMET requests with saved bytes, response metadata and schema validation; assess SNODAS/NWM/static products only if needed. Enumerate candidate sites, river-network relationships, authentic attributes, threshold/datum history, available vintages and covered periods. Write `project/data_feasibility.md`, `data/manifests/provider_manifest.jsonl`, `project/data_rights.md` and a storage/time estimate. Clearly distinguish current-final versus as-issued data feasibility.

**Acceptance:** independently inspect several saved responses against provider content; zero silently generated observational fields; all exclusions have reasons; rights/access paths are recorded. **Stop:** unavailable historical thresholds/vintages prevent the primary claim; adopt a narrower disclosed estimand before proceeding.

### P02 — Acquisition, decode and immutable provenance

**Inputs:** P01 feasible sources and permissions. **Depends on:** P01.

**Work:** implement bounded/retryable fetchers, raw-byte persistence, record-level provenance, CF units/time decoding, basin extraction, duplicate/revision handling and retrieval replay. Create `source/flood_sentinel/acquisition/`, `data/source_records.csv` from actual records, source manifests and raw storage outside Git. Represent model-derived/simulation products truthfully.

**Acceptance:** decode oracle examples and unit conversions match official metadata; hashes bind exact bytes; source substitutions/missing endpoints produce failures, never zeros or synthetic fallbacks; retrieval reproduces selected records or reports an authentic version limitation. **Stop:** ambiguous units/time grids/provider changes remain unresolved for a required input.

### P03 — Event definitions, threshold validity and coverage

**Inputs:** authentic gauge/stage/discharge observations and threshold histories. **Depends on:** P02.

**Work:** implement datum-aware thresholds, exact versus interval onset, ongoing/receding state, event separation and coverage rules. Save `data/event_intervals.parquet`, an evidence-linked episode catalog and `project/label_policy.md`. Hand-review a randomly selected, reproducibly drawn sample plus edge cases, including higher-category peaks, missing intervals and threshold changes.

**Acceptance:** label oracle cases pass; no peak-noon exact onset; no quantile labeled official; all eligible severity-crossing events retained; agreement/disagreements and adjudication are recorded. **Stop:** onset/threshold support cannot answer the planned horizon; adjust the label/claim rather than fabricate precision.

### P04 — Split, availability and precision design

**Inputs:** P01–P03 support/exposure/network relationships, development-only evidence. **Depends on:** P03.

**Work:** define basin/time/train-validation-calibration-test assignments, purge/embargo and allowable target history. Build an issue manifest using observation and release/vintage filtration. Simulate design precision under disclosed assumptions. Write `project/split_policy.md`, `project/precision.md`, `data/cohort.csv` and a test-access policy. Audit discarded samples and natural prevalence.

**Acceptance:** no prohibited source/event/network overlap; post-issue/revised mutations rejected; sufficient independent support for the scope or a narrower honest design; untouched future test dates/units specified. **Stop:** overlap or insufficient support makes the planned confirmatory claim unidentifiable. Old legacy test results are development knowledge, not fresh test evidence.

### P05 — Domain adapters and independently recomputed endpoints

**Inputs:** actual source/cohort/event records and P00 schema proposal. **Depends on:** P04.

**Work:** implement lossless ranking, mixed-origin, record ancestry, availability, event/exposure and population-inference adapters that the chosen claim actually requires. Keep original domain rows, native projection and conversion digests. Build an independent recomputation tool that does not import the metric implementation being checked. Write `project/domain_adapter.md` with boundaries and threat/mutation tests.

**Acceptance:** every native row maps to real domain evidence; no source-ID duplication trick; probability/ranking distinction retained; independently recomputed endpoints agree on hand-derived and authentic development examples; deliberate denominator/cutoff/label mutations fail. **Stop:** an adapter cannot represent the claim losslessly; remove that claim or change the representation through review.

### P06 — Data pipeline, missingness and model objective

**Inputs:** verified P04 splits/issues, P05 interfaces and the migrated primitives. **Depends on:** P05.

**Work:** implement streaming causal datasets, train-only scaler persistence, explicit masks, objective/corruption generator and observation counts. Define score A leave-channel-out behavior, score B fitted covariance/reference and any genuine forecasting head. Add shape/version compatibility checks. Keep `source/flood_sentinel/reconstruction.py`'s withholding contract; no checkpoint from the legacy project qualifies.

**Acceptance:** future perturbation, hidden-target hook/gradient, missing versus zero, train-fit and calibration-degeneracy checks pass; a small real development batch has finite loss/gradients; objective counts and input lineage can be inspected. **Stop:** insufficient observed support, collapsed reference, hidden target exposure or unexplained normalization.

### P07 — Pilot optimization and comparator implementation

**Inputs:** P06 genuine development data and P04 endpoints. **Depends on:** P06.

**Work:** train small development pilots for the proposed model and baseline ladder; implement true persistence, continuous CUSUM/EWMA, tabular and neural baselines with appropriate stopping. Measure hardware and sample counts. Determine hyperparameter/tuning budget, mask/label subset design, calibration support, operating rule and feasible retrained ablations. Write `project/pilot.md` and a complete compute ledger.

**Acceptance:** each claimed comparator trained under its actual objective and input setting; best-checkpoint rule and loss/convergence traces exist; actual NWM only if acquired; no test-informed selection; reliable resource estimate. **Stop:** proposed method does not learn, calibrator lacks support, or study is unaffordable; simplify before freeze. A poor pilot is useful information.

### P08 — Scientific challenge and preregistration freeze

**Inputs:** P00–P07 artifacts and original source/endpoint evidence. **Depends on:** P07.

**Work:** replace the draft with a schema-valid `project/research_plan.json` and executable methods document. Register primary/secondary claims, paired experiments/seeds, multiplicity, precision, scope, ablations, failures/OOD, hardware and release paths. Implementor independently challenges availability, labels, denominator, source authenticity, compute fairness and scope. Resolve or record disagreements. Run factory validation and freeze.

**Acceptance:** successful immutable freeze of real inputs/plan/code/dependencies; no placeholders or desired results; test access remains consistent with declaration; all critical challenge points resolved. **Stop:** a green structural gate with unresolved scientific flaws is not acceptance.

### P09 — Supervised main experiments and continuous predictions

**Inputs:** frozen P08 epoch and untouched test corpus. **Depends on:** P08.

**Work:** execute all registered seeds/methods through the supervisor; export complete issue-level predictions and continuous alert state, traces, checkpoint evidence and failures. Run the registered daily/subdaily cadence, not stride-30 samples for consecutive-day alerts. Record exactly which data were used at each issue. No opportunistic tuning on test outcomes.

**Acceptance:** complete frozen-cohort coverage, successful hash/argv audits, all failures retained, independently recalculated metrics. **Stop:** a discovered critical defect triggers a preserved failed epoch/amendment, not an edited success table.

### P10 — Retrained ablations, label efficiency and sensitivity

**Inputs:** P08 registered grids and P09 pipeline. **Depends on:** P09 unless execution order was frozen differently.

**Work:** run each registered condition with its own training/calibration/reference. Execute nested real label budgets and independent subset draws. Export all OOD/sensitivity rows including sparse/undefined conditions. Record training costs and support, not just a favorable effect summary.

**Acceptance:** no random untrained replacement layers; no test corruption misnamed pretraining; all registered cells accounted for; valid paired units. **Stop:** unplanned follow-up is exploratory or requires a fresh epoch/test cohort.

### P11 — Statistical analysis and scientific failure review

**Inputs:** all complete frozen outputs including failures. **Depends on:** P09–P10.

**Work:** independently compute registered discrimination, calibrated probability and operational endpoints; implement hierarchical inference/multiplicity with appropriate support; plot effect intervals and unit results; diagnose misses/false alarms/calibration/OOD without changing the primary estimator. Write `project/results.md`, `project/statistical_report.md`, machine-readable metric/coverage tables and traceable figure inputs.

**Acceptance:** numbers derive from authentic rows, two implementations agree, conclusions distinguish benefit/degradation/equivalence/inconclusive/invalid protocol. A negative conclusion has valid methodology and stated precision. **Stop:** missing denominator/support or independent recomputation disagreement; resolve before drafting claims.

### P12 — Hardware validation and clean reproducibility

**Inputs:** final frozen implementation/environment and P09–P11 artifacts. **Depends on:** P11.

**Work:** measure the actual registered sustained workload/inference trials, validate memory scopes and reproduce the artifact pipeline in a clean environment. Verify checkpoint/normalizer/reference/calibrator compatibility and lawful source retrieval. Generate environment/device/runtime tables and replay logs. Audit exported figures/tables against canonical metric rows.

**Acceptance:** replay agrees within predeclared numerical tolerance; resource claims are measured with units/device synchronization; missing source vintages are honestly disclosed. **Stop:** no clean replay or required inputs inaccessible; repair reproducibility or reduce the release claim.

### P13 — Manuscript, rights and submission review

**Inputs:** valid P11 conclusions, P12 replay and chosen current venue requirements. **Depends on:** P12.

**Work:** write methods/results/limitations with exact settings and all failed/null findings; create data/code/model cards, ethics/application limits, citations and rights statements. Obtain hydrology/statistical review appropriate to the claims. Remove unsupported submission/review status. Complete evidence-bound factory review/certification only within its actual supported scope.

**Acceptance:** every numerical/novelty/status claim has a traceable source; venue policies verified; figure/table values independently checked; no legacy results presented as current evidence; license boundaries explicit. **Stop:** novelty, inference, data rights or scientific objections remain unresolved; submission readiness is not certified.

### P14 — Versioned release, verified handoff and submission package

**Inputs:** P13 reviewed manuscript and lawful artifacts. **Depends on:** P13.

**Work:** create a versioned repository/data release, immutable references/digests, factory handoff ZIP and standalone verification. Test another-session instructions using only the new folder and published lawful sources. Archive all plan epochs and attempts. Package the venue-specific submission; actual submission is the user's later decision unless separately authorized.

**Acceptance:** an independent recipient can verify and reproduce the supported claims; final release status is truthful. **Stop:** unverifiable bundle, inaccessible essential evidence or manuscript/release mismatch. The present migration is a development checkpoint, not P14 completion.

## 13. Manuscript and venue readiness

### 13.1 A contribution must survive the audit

Combining a TCN, causal attention and reconstruction is an implementation choice, not by itself proof of scientific novelty. A publishable contribution might instead be a carefully measured comparison of causal SSL against simple baselines; a verified label-efficiency result; an availability-aware flood benchmark; or a reproducible finding that an apparent advance disappears under authentic inputs and fair protocols. These are possible research directions, not claims established by this migration.

Conduct a structured literature review before freeze. Record search date, query, inclusion rules, problem/horizon/input setting, dataset/split, labels, availability assumptions, baselines, uncertainty and code/version for relevant papers. Read full methods and supplements. Compare the proposed question against authentic current work, including learned hydrological models and operational/retrospective forecasting distinctions. Do not invent citations, infer a paper's procedure from its title or present a reconstruction detector as equivalent to a trained forecast model.

The EA-LSTM paper is a verified architectural reference, not evidence that this migrated recurrence reproduces its experiments: [Kratzert et al., HESS 2019](https://hess.copernicus.org/articles/23/5089/2019/). The large-scale learned flood-forecasting paper is relevant context, but its complete protocol must be retrieved and reviewed before comparison: [Nature 2024 article](https://www.nature.com/articles/s41586-024-07145-1). The page's full text could not be retrieved in this audit session; do not attribute a detailed benchmark design to it from the accessible title/summary alone.

### 13.2 Venue fit follows the actual contribution

HESS or Water Resources Research are possible hydrology-focused targets if the completed study offers a defensible hydrological question, sound source/label methodology, independent evaluation and insight beyond a network combination. A machine-learning venue such as TMLR or a future appropriate conference cycle requires a contribution meaningful to that community and comparison against relevant methods. These are scope suggestions, not acceptance predictions, journal rankings or claims of affiliation/submission. Choose the venue after the feasibility/literature work and reconfirm its current requirements before submission.

HESS's current author page requires manuscript preparation and data/code availability components and describes disclosure of AI-generated manuscript content. Use its actual template and linked policies, with a persistent artifact archive where appropriate. [Official submission guidance](https://www.hydrology-and-earth-system-sciences.net/submission.html). AGU's guidance covers access to the supporting data/software for review, availability/citation statements and preservation; a development GitHub URL alone is not an archival release. [AGU data/software guidance](https://data.agu.org/resources/agu-data-software-sharing-guidance). Consult the [TMLR author guide](https://jmlr.org/tmlr/author-guide.html) or the actual chosen conference year's rules, rather than assuming one template applies to every venue. The [NeurIPS checklist](https://neurips.cc/public/guides/PaperChecklist) is a useful transparency reference, not evidence of a NeurIPS submission or compliance with a future year's call.

Store `project/venue_requirements.md` with verified URLs, retrieval dates, manuscript type/scope, anonymization/preprint rules, page/supplement limits, artifact/data/code requirements, AI/authorship policies and charges/funding considerations. Do not record an invented deadline, acceptance rate or publication status. Venue prestige cannot repair invalid measurement or inadequate precision.

### 13.3 Required manuscript contents and artifact trace

The introduction states the actual task and why its endpoint matters. Methods describe source versions/vintages, sampling frame, units/time conventions, thresholds/datum, interval onset, event separation, missingness, issue filtration, splits/purge, model/objective, score interpretation, comparator opportunities, tuning/stopping, calibration, operational alert rule, inference and hardware. Give exact counts and equations where they establish reproducibility.

Results begin with corpus support, exclusions and exposure, then primary paired effects/intervals and operational trade-offs. Include all registered conditions and failure outcomes. Distinguish development choices from confirmatory results. Figures should show support and uncertainty, with interpretable units; maps use authentic coordinates/geometry and lawful basemaps. Every figure/table references its canonical input rows, computation script, configuration and digest. A plotting function may not contain the result numbers as handwritten literals.

Limitations address availability/vintage assumptions, interval-censored labels, missingness/selection, independent-unit count, geographic scope, regulation/static coverage, tuning budget, hardware/backend variability and untested deployment. Report the actual intervention cost and risks of false/missed warnings only where evidence exists. Do not describe this foundation as a life-safety operational warning product. Calibration and retrospective skill alone do not validate emergency deployment.

Create `project/model_card.md`, `project/data_card.md`, `project/reproducibility.md`, `project/claim_ledger.csv` and `project/data_rights.md`. The claim ledger maps each assertion to registered hypothesis, eligible population, endpoint, result artifact, uncertainty, scope and status. Claims such as “under peer review,” “accepted” or a journal citation appear only when a real submission/publication record supports them. The legacy IEEE Access/Under Peer Review language is removed from the active README.

### 13.4 License boundaries and scientific accountability

The supplied root `LICENSE` governs the factory and is retained unchanged. The old engine's MIT notice is preserved in `source/flood_sentinel/LICENSE`. Do not erase authorship or blanket-relicense the factory, inherited code or providers' data. Before release, resolve ownership/permission for newly written engine additions and select their explicit license with the rights holder. Maintain a path-specific license/attribution table. A public GitHub repository does not itself grant reuse rights.

Provider licenses/terms and third-party maps/reports are assessed separately. Do not mark all acquired data CC-BY merely because a manuscript uses that license. Generated fixtures are identified as constructed and kept separate from observations. AI assistance is disclosed where venue policy requires it and wherever its role materially affects reproducibility/accountability. Human authors remain responsible for scientific claims. Independent review should challenge the actual data and mathematics, not merely proofread the paper.

## 14. Legacy preservation and the new GitHub development tree

### 14.1 Preservation scope

The original public `main` is `6078b04f4c104e7b14a96a4719c3f744b0782dd8`. The migration creates an annotated tag, `legacy-pre-research-rebuild-2026-10-01`, at that exact commit before replacing active `main`. The tag description says the snapshot preserves legacy work and does not validate its scientific claims. Do not force-push, rewrite the old commit, retag a different commit under the same name or delete the original history.

The tag preserves the **published tracked tree**. Ignored local raw artifacts, handoff ZIPs and factory/project files were not in that commit. They remain in the old local folder, and their hashes/structure are inventoried in the new audit. A tag is not a backup of ignored files. The complete supplied local archive should be retained/backed up separately if the user needs to preserve those bytes; no invalid/large legacy dataset is silently republished as new research data.

The old local folder is retained. “Clear everything” is implemented as replacement of the active repository tree with this new folder's contents, while preserving recoverable history. The new folder becomes the working Git checkout for subsequent development. A normal successor commit removes old scripts/claims/figures/checkpoint references and adds the corrected engine, new audit/plan and supplied v3.3 scaffold. Old result files do not remain on the active branch under a misleading new name.

### 14.2 Verification and future hygiene

Immediately before publishing, recheck the actual remote head/tag state. If another human changed `main`, preserve their work and reconcile the migration; never force-push over it. Push the legacy tag first, then the ordinary successor commit to `main`. Read back the remote branch and dereferenced tag, inspect the new tracked tree and confirm the old checkout's tracked status is unchanged. Record the operations in `project/audit/migration_status.json`; final Git commit identity is obtained from Git itself rather than self-referentially embedded in committed content.

Exclude caches, virtual environments, credentials, local factory runtime/operation locks, raw/large data and checkpoints from ordinary Git. Keep research manifests, acquisition code, plan epochs and lawful evidence intended for release. Ignoring runtime files is not authorization to delete failed research attempts: preserve/archive them under the declared evidence policy and include the required evidence in handoff/release artifacts. Scan staged contents for secrets before pushing; hashes of legacy files do not require publishing their underlying credentials or personal data.

Future commits use this new folder and this repository's remote. A later valid study release gets a distinct tag and artifact archive; it must not reuse the legacy tag or label this migration as an accepted paper. Keep Git version, factory version, plan epoch, data digest and checkpoint digest separate in all receipts and citations.

## 15. Decision rules, unresolved questions and honest conclusions

### 15.1 Classify the outcome correctly

| Outcome | Evidence needed | Permitted conclusion |
|---|---|---|
| Useful benefit | Valid source/endpoint, fair comparator, practical effect and appropriate precision | Benefit within the measured population/setting and operating constraint. |
| Meaningful degradation | Same valid protocol, compatible interval below practical bound | Proposed method performs worse within the studied setting. |
| Equivalence/non-inferiority | Registered margins, suitable analysis, adequate precision and comparator validity | Bounded differences on the specified scale/population. |
| Inconclusive | Valid study but intervals/support cannot discriminate relevant outcomes | Available evidence is insufficient; report interval/support. |
| Feasibility failure | Authentic sources/vintages/labels/resources cannot support intended design | That intended claim is presently untestable; explain what is missing. |
| Invalid methodology | Fake source, leakage, wrong task, broken comparator or denominator | Results are inadmissible, even if they appear negative. |

The current legacy study falls in the last category for several central claims. It is **not** a valid negative result simply because Score A appears worse than the faux NWM series or the lead-time pipeline reports no detection. A future negative or inconclusive study can be scientifically useful when its design is valid and its limits are understood; publication still depends on contribution and venue judgment.

### 15.2 Questions to resolve with evidence, not pause the whole project

The Architect should document decisions about geographic scope, primary forecast horizon, official-stage versus hydrological exceedance target, daily versus subdaily issue cadence, actual as-issued archive access, independent network groups, static/source rights, primary useful effect, baseline tuning budget, test cohort freshness and code licensing. Many can be resolved through P01–P07 feasibility and development evidence. Do not ask the user to choose arbitrary hyperparameters or supply a desired performance number.

Reasonable starting assumptions are a modest source-verifiable study, final-retrospective status until vintage evidence proves otherwise, minimal authentic input channels, CPU correctness before MPS acceleration, and no inherited weights/results. These are workflow defaults, not frozen scientific design choices. Site IDs, dates, horizons, support counts and priors remain **undetermined** until evidence supports them. The old 54-site selection may inform exploration but is not automatically representative or confirmatorily untouched.

Ask the user only for genuinely human constraints that evidence cannot resolve: paid/storage resources, inaccessible accounts, collaborator/expert availability, a rights-holder license decision or a substantive application preference among feasible designs. Meanwhile continue independent tasks within authorization. Do not manufacture an unavailable raw archive, log, permission, DOI or collaborator review to remove a blocker.

### 15.3 Submission blockers and completion criteria

Submission readiness requires: authentic and lawful inputs; defensible endpoint/availability/sampling; appropriate independent support and scope; valid preprocessing/objective; fair trained comparators; complete frozen predictions/failures; independent metrics/inference; measured resource claims; clean replay; reviewed limitations; evidence-bound figures/claims; venue-policy compliance and accessible artifacts. Each item has an artifact and reviewer check, not an unchecked prose promise.

Presently missing are real acquisitions/cohorts, trained models, corrected empirical results, runtime/domain integration, precision design, final license resolution, preregistration, population inference, independent scientific review and a manuscript/release. The engine and exhaustive audit are completed migration groundwork. Future agents must not report the system complete until the required packages and evidence are present.

## 16. Another-session handoff instructions

### 16.1 Architect starting brief

“Read `AGENTS.md`, all of `plan.md`, `project/methodology.md`, the Flood Sentinel audit under `project/audit/` and the active v3.3 factory specifications. Treat legacy metrics as invalid forensic diagnostics and the current JSON as an unregistered draft. First resolve P00 runtime/domain feasibility and P01 source/rights/coverage. Use only this new folder and authentic lawful sources. Prepare an evidence-supported design and implementation contracts; challenge statistical scope and availability before freeze. Do not invent data, results, acquisition logs or certification, and do not use desired significance as a planning criterion. Keep unresolved limits visible.”

### 16.2 Implementor starting brief

“Read the same documents and independently challenge the Architect's design. Reuse the migrated tested primitives with their explicit limits. Implement the earliest accepted work package, recording authentic provenance and meaningful tests. Use the supervised factory lifecycle after runtime integration. No legacy checkpoints, faux NWM/SNODAS, arbitrary onset hours, test-fit statistics, hidden-target reconstruction, biased comparator budgets or hardcoded metrics. A critical defect preserves the failed epoch and stops the affected claim. Export complete evidence and independent recomputation; report negative/inconclusive outcomes honestly.”

### 16.3 Local engineering verification and boundaries

From the repository root, with the documented local environment, run:

```sh
python3 -m pytest source/tests -q
python3 factory/run_self_tests.py
```

The first command is engine software verification. The second is supplied factory software verification; a restricted execution environment may deny a Unix-socket fixture, in which case record the environmental restriction and rerun where that local operation is permitted. Neither command runs a flood study. Do not invoke `freeze`/`certify` on the unregistered draft just to create status files. Once P08 exists, use the actual documented `python3 factory/gatekeeper.py freeze .`, `run . EXP_ID`, `audit .`, `certify .`, `handoff .` and standalone bundle-verification commands with the registered artifacts.

The audit tools accept a legacy root for optional reinventory. The saved inventory/observations are already sufficient to understand the findings without access to the old folder; rerunning them is not required for research execution. They may require their separately recorded forensic dependencies. Only observational acquisition, labels and experiments created under the new design may enter the new scientific evidence chain.

### 16.4 Reference register and verification dates

Primary provider/venue pages consulted during 30 September–1 October 2026 are listed below. Recheck mutable API/venue rules at execution/submission. This register is not a complete literature review; it identifies sources supporting feasibility and integration decisions in this plan.

| Source | Purpose | Verification boundary |
|---|---|---|
| [USGS API v1 announcement](https://waterdata.usgs.gov/blog/api-v1-release/) | Current API migration/legacy endpoint planning | Official page; do not assume old scripts remain compatible. |
| [USGS OGC API documentation](https://api.waterdata.usgs.gov/docs/ogcapi/) | Collection/filter/format acquisition design | Verify each actual response/schema and time/qualifier behavior. |
| [NOAA NWPS API](https://water.noaa.gov/about/api) | Gauge categories/stage metadata feasibility | Current metadata alone does not prove historical threshold validity. |
| [gridMET documentation](https://www.climatologylab.org/gridmet.html) | Units, day convention and final/near-real-time distinction | Actual CF metadata/raw version controls decoding. |
| [NSIDC SNODAS](https://nsidc.org/data/g02158/versions/1) | Authentic SWE product nature/access | Need exact daily objects and no-data handling. |
| [NWM archive registry](https://registry.opendata.aws/nwm-archive/) | Retrospective coverage/origin/access | Actual object time/reach coordinates and downloaded bytes required. |
| [EA-LSTM primary paper](https://hess.copernicus.org/articles/23/5089/2019/) | Static-gated recurrent architectural reference | No inherited regression result claimed. |
| [Learned flood forecasting, Nature 2024](https://www.nature.com/articles/s41586-024-07145-1) | Relevant research context | Full protocol retrieval remains required. |
| [HESS submissions](https://www.hydrology-and-earth-system-sciences.net/submission.html) | Candidate venue preparation/policies | Mutable; recheck selected manuscript type and linked policies. |
| [AGU data/software guidance](https://data.agu.org/resources/agu-data-software-sharing-guidance) | Preservation/access/citation | Preserve exact study artifacts and resolve access rights. |
| [TMLR author guide](https://jmlr.org/tmlr/author-guide.html) | Candidate ML venue | Reconfirm fit and rules after actual contribution exists. |
| [NeurIPS checklist](https://neurips.cc/public/guides/PaperChecklist) | Transparency/reproducibility questions | Does not establish a conference submission or future-cycle compliance. |

The strongest source for a numerical Flood Sentinel finding here is the saved local code/data evidence and independent recomputation, not a provider's generic homepage. The strongest source for a future result will be the new frozen authentic records and executable analysis. Keep that distinction throughout the project.
