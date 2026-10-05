# Implemented checks and practical limits

The gate binds declared plan/source/data bytes, normalizes evidence paths, rejects symlinks and unsafe input types, parses strict JSON/CSV, validates typed execution contracts, and rechecks input/output membership. It launches argv without a shell using an environment allowlist and verifies signed local receipts against the pinned key. Same-user execution remains outside a security isolation boundary.

Prediction CSVs require unique `sample_id,score`; optional supplied labels are checked against frozen cohort labels. The audit joins source IDs and split/group/entity membership, verifies binary support and probability range, and recomputes AUROC, average precision, accuracy, F1, Brier and log loss. Constant/saturated outputs are diagnostics; below-baseline support needs explicit null/inconclusive scope and cannot be excused with padding.

Research policies require at least 30 test groups and 10 observations per class. Training checks use the observed contiguous loss history, preregistered stopping rule and selected checkpoint. Small counts and stable losses are necessary guards, not scientific sufficiency proofs. Group-paired inference is conditional on trained models; seed-only inference is explicitly conditional on the fixed test corpus. One declared Holm family, effect floor, precision target and test feasibility are checked.

Configured failure analyses derive denominators from joined predictions; sensitivity needs registered levels and repeat seeds; ablations need executed boolean cells and replication, with a disclosed alias structure for large fractional designs. Hardware checks compare measured rows to declared trial/sustained-workload requirements but cannot independently establish truthful instrumentation.

Acquisition/tier scans are heuristics with regression controls. They cannot prove honest source use or semantic claim strength. Reviews must point to current evidence, give specific distinct reasoning, resolve diagnostics and disclose mode. Human evidence inspection, data authenticity, representativeness, operator semantics and external reviewer identity remain outside automatic assurance.
