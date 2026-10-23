# Initial daily aggregate-completion benchmark

This is a temporal development benchmark on previously inspected data from four monitored stations: 01013500, 02046000, 05291000 and 06037500. Training issues cover 2010–2017, validation 2018–2020, and test 2021–2024. Local discharge Q99 thresholds use only the fixed 1990–2009 reference. The target is the existing qualifying daily high-flow aggregate completion at 24/48/72 hours, not instantaneous flood onset.

Inputs are 365-day discharge/temperature/precipitation histories with explicit observation masks. Scalers fit unique observed training-window cells only. Discharge inputs retain the approved/unflagged rule; estimated-retaining target truth is separate. Missing values use masked placeholders and never become observed zeros or negative labels. Fixed-standard discharge days, UTC weather days and closure-plus-24-hour availability are retrospective assumptions, not verified historical publication times. See the [daily sources](daily_source_expansion.md) and [meteorological feasibility limits](meteorological_source_feasibility.md).

The comparison below uses the same 4,609 known, scoreable test issues at every horizon, within the predeclared complete-weather interval through 2 November 2024 noon UTC. Positive issue counts are 12, 23 and 35 respectively. The later 236-issue calendar tail has missing weather and no positive labels; it provides no tail discrimination estimate. Thresholds maximize validation F1 and remain fixed on test. AP is non-interpolated average precision.

| Method | AP 24h | AP 48h | AP 72h | F1 at 24/48/72h |
|---|---:|---:|---:|---|
| Persistence | 0.013222 | 0.018942 | 0.026757 | 0.000000 / 0.000000 / 0.000000 |
| EWMA | 0.010600 | 0.018390 | 0.027811 | 0.000000 / 0.000000 / 0.000000 |
| One-sided raw CUSUM | 0.005047 | 0.008757 | 0.013201 | 0.000000 / 0.014728 / 0.021858 |
| EA-LSTM, seed 11 | 0.012349 | 0.020153 | 0.030415 | 0.000000 / 0.016000 / 0.069620 |
| Causal TCN, seed 11 | 0.012444 | 0.020106 | 0.024990 | 0.000000 / 0.000000 / 0.000000 |

The TCN has nine dilated causal layers, width 32, no attention and 57,411 trainable parameters. Training completed 14 epochs; the lowest validation unweighted masked BCE selected epoch 6 (0.0462624). Class weights came from training labels. Its sigmoid outputs are uncalibrated. The selected thresholds detected no positive test issues; these initial results establish no consistent TCN advantage or convergence.

The full known test panel contains 14 distinct completing source records across horizons. Repeated horizon labels and training seeds do not multiply the number of hydrological events. Only four sites and one fitted neural seed are represented here; network independence, physical warning lead and population generalization are not established. EA-LSTM seed 11 completed 36 epochs; validation selected epoch 28 (unweighted masked BCE 0.043046372). It has 4,195 parameters and additional static inputs, so the architecture comparison is not capacity/information matched. Its results establish no consistent advantage.

Future-aggregate pretraining and supervised transfer also executed, but an epoch reducer swapped a loss numerator with its weight denominator. Minibatch gradients used the intended loss; validation checkpoint selection and early stopping used the wrong objective. Those results are retained as diagnostic and excluded from the declared method comparison pending a corrected rerun. The teacher predicts the next completed daily aggregate, whose interval may overlap issue time; it does not establish instantaneous physical warning.
