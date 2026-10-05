# Flood Sentinel: Executable Research Methodology

**Document Status:** Preregistered Executable Research Methodology (Epoch 1 Freeze)  
**Governing Standard:** Upstream Software Factory v3.3.0 Fail-Closed Specification  
**Project Identifier:** `flood-sentinel-research-rebuild`  
**Execution Profile:** `binary_classification` (`python-cpu-v1`)

---

## 1. Research Objectives & Scope

Flood Sentinel evaluates whether causal, availability-aware hydrological representations learned via self-supervised masked autoencoding improve early detection of downstream flood precursor episodes compared to traditional statistical and recurrent hydrological baselines.

The study protocol enforces strict non-leakage, genuine source verification, explicit observation masks, and train-only calibration. The current evaluation is conducted on candidate USGS and NOAA NWPS river systems (Potomac River Basin and Delaware River Basin). In accordance with Factory Principle C03 and C93, this prototype evaluation is designated with intent `fixture` and origin `observational` to transparently reflect the candidate gauge frame without manufacturing synthetic basins to satisfy large-cohort research floors.

---

## 2. Authentic Sourcing and Causal Data Pipeline

### 2.1 Primary Observation Endpoints
Observations derive from authentic REST endpoints:
1. **USGS NWIS Instantaneous Values Service:** 15-minute time series of gage height (`00065`, converted to SI meters) and streamflow discharge (`00060`, converted to SI cubic meters per second).
2. **NOAA NWPS Flood Stages:** Verified official flood stages (action, minor, moderate, major) bound to specific gauge IDs and vertical datums (NAVD88/NGVD29).

### 2.2 Causal Issue Framing
- **Lookback Window:** $T = 25$ steps (24 hours prior to issue time $t_{\text{issue}}$ sampled at hourly discretization).
- **Target Horizon:** 24 hours post-issue $(t_{\text{issue}}, t_{\text{issue}} + 24\text{h}]$.
- **Causal Availability Guard:** Every observation record must satisfy $t_{\text{obs}} \le t_{\text{issue}}$. Future observations are strictly withheld from model input.
- **Explicit Observation Masks:** Values are passed alongside binary observation indicators $O \in \{0, 1\}^{T \times C}$. Missing observations are masked, retaining their physical distinction from zero flow/stage.

### 2.3 Train-Only Normalization Persistence
All feature standardizations derive exclusively from the `train` split via `PersistentScaler`:
$$\mu_c = \frac{1}{N_{\text{obs}}} \sum_{i, t: O_{i,t,c}=1} X_{i,t,c}, \quad \sigma_c = \sqrt{\frac{1}{N_{\text{obs}}} \sum_{i, t: O_{i,t,c}=1} (X_{i,t,c} - \mu_c)^2}$$
Fitted scalers are cryptographically bound via SHA-256 digest and frozen prior to evaluation.

---

## 3. Preregistered Model Families & Comparator Ladder

The study registers 7 model families spanning 4 hierarchical tiers:

### Tier 1: Persistence Comparator (`persistence`)
- **Mechanism:** Stage velocity forward projection over the lookback horizon.
- **Reference:** Trivial kinematic persistence baseline.
- **Training Mode:** Deterministic closed-form.
- **Probability Mapping:** Monotonic Platt logistic scaling fitted on training split.

### Tier 2: EWMA-CUSUM Comparator (`ewma_cusum`)
- **Mechanism:** Continuous statistical process control tracking cumulative sum deviations on exponentially weighted moving average standardized stage.
- **Reference:** Historical statistical anomaly detection baseline.
- **Training Mode:** Deterministic calibration fitted on training split observations.
- **Probability Mapping:** Monotonic Platt logistic scaling fitted on training split.

### Tier 3: Tabular Ridge Logistic Comparator (`tabular_ridge`)
- **Mechanism:** $L_2$-regularized logistic regression over a 10-dimensional causal feature summary (mean, std, min, max, latest, delta for stage and discharge).
- **Reference:** Current linear statistical baseline.
- **Training Mode:** Deterministic Newton-Raphson optimization ($L_2$ penalty $\lambda = 1.0$).
- **Probability Mapping:** Direct sigmoid logistic response $P(Y=1|X) \in (0, 1)$.

### Tier 4: Supervised EA-LSTM Baseline (`ea_lstm`)
- **Mechanism:** Entity-Aware Long Short-Term Memory network incorporating static catchment embeddings into input gates, processing dynamic lookback sequences.
- **Reference:** Current state-of-the-art recurrent hydrological neural architecture.
- **Training Mode:** Early stopping on validation loss (min epochs: 2, max epochs: 10, patience: 3, min delta: $1 \times 10^{-4}$).

### Tier 5: Masked Hydro Foundation Model — Score A (`masked_hydro_score_a`)
- **Mechanism:** Causal temporal convolutional encoder coupled to self-attention transformer with leave-channel-out masked reconstruction. Evaluates residual MSE on withheld sensor channels.
- **Reference:** Proposed self-supervised masked reconstruction benchmark.
- **Training Mode:** Early stopping on masked reconstruction validation loss.
- **Probability Mapping:** Monotonic Platt logistic scaling fitted on training split.

### Tier 6: Masked Hydro Foundation Model — Score B (`masked_hydro_score_b`)
- **Mechanism:** Latent space Mahalanobis distance evaluated against an empirical Gaussian reference fitted on training representations with Ledoit-Wolf shrinkage.
- **Reference:** Proposed latent representation covariance benchmark.
- **Training Mode:** Early stopping on masked reconstruction validation loss.
- **Probability Mapping:** Monotonic Platt logistic scaling fitted on training split.

### Supervised Benchmark: Causal Forecasting Head (`causal_forecasting_head`)
- **Mechanism:** Frozen or co-trained causal temporal encoder coupled to a binary classification projection head trained directly on precursor labels.
- **Reference:** End-to-end causal neural forecasting model.
- **Training Mode:** Early stopping on validation binary cross-entropy loss.

---

## 4. Experimental Design & Multiplicity Control

### 4.1 Independent Training Seeds
All 7 model families are executed across 5 independent seeds:
$$\mathcal{S} = \{42, 100, 2026, 31415, 99999\}$$
Yielding $7 \times 5 = 35$ preregistered experiments.

### 4.2 Paired Seed Contrasts
Comparisons are evaluated pairwise across identical seeds on the fixed test corpus:
1. `cmp_causal_vs_persistence`: `causal_forecasting_head` vs. `persistence`
2. `cmp_causal_vs_ea_lstm`: `causal_forecasting_head` vs. `ea_lstm`
3. `cmp_causal_vs_tabular_ridge`: `causal_forecasting_head` vs. `tabular_ridge`
4. `cmp_causal_vs_ewma_cusum`: `causal_forecasting_head` vs. `ewma_cusum`
5. `cmp_masked_a_vs_masked_b`: `masked_hydro_score_a` vs. `masked_hydro_score_b`

### 4.3 Statistical Multiplicity & Inference Scope
- **Metric:** Non-interpolated Average Precision (`average_precision`).
- **Sampling Unit:** `seed_fixed_test` with explicit `inference_scope: "fixed_test_corpus"`.
- **Multiplicity Adjustment:** Family-wise error rate controlled at $\alpha = 0.05$ via the Holm step-down procedure.
- **Assertion:** Prospective point estimation and confidence intervals (`assertion: "estimate"`), avoiding unevidenced claims of confirmatory population superiority.

---

## 5. Hardware Benchmarking Protocol

Resource consumption is empirically measured on the target Apple M3 CPU runtime:
- **Assigned Experiment:** `exp_masked_hydro_score_a_s42`
- **Minimum Trials:** 5 sustained evaluation iterations.
- **Minimum Sustained Duration:** $\ge 30.0$ wall-clock seconds.
- **Observed Metrics:** Peak resident set size (Peak RSS MB via `getrusage`), wall-clock seconds, sample throughput (samples/sec), and trainable parameter counts.
