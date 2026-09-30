# v3 scientific protocol

Every claim is registered with an ID, estimand, population, split, metric definition, preregistered direction, and evidence artifact. Every result row carries dataset fingerprint, code commit, dependency lock hash, hardware, seed, fold, training steps, checkpoint hash, and wall-clock telemetry. Predictions are immutable parquet/CSV with IDs and labels; metrics are recomputed by a separate implementation.

Minimum release evidence: five independent seeds (or a written power-based exception), untouched test set, convergence trace with stopping rule, confidence interval and effect size, multiplicity correction, trivial/canonical/current/mechanism-matched baselines with tuning/compute parity, full factorial ablation for ≤5 components, sensitivity at ±10/25/50%, at least one legitimate OOD or explicit scope limitation, subgroup failure analysis, and model/data cards. Any synthetic/demo artifact is tagged and cannot support a claim.

Certification is a scientific decision, not a completeness score. Any critical FAIL or unresolved provenance warning yields NOT_CERTIFIED.
