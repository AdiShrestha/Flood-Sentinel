# Agent workflow and human evidence review

1. Architect writes `research_plan.json`: exact claims, estimands, population, provenance, groups/splits, seeds, stopping, baselines, ablations, sensitivity, OOD limits, and launch contract. Implementor challenges it before freeze.
2. Architect runs `gatekeeper.py freeze .`. The snapshot binds the declared plan, code, data and methodology. This local timestamp cannot prove an independently witnessed preregistration.
3. Implementor runs `gatekeeper.py run . EXP_ID` or `run . all`. Each experiment gets one retained attempt. Prediction files need `sample_id,score`; the gate joins frozen labels and recomputes metrics. Supplied labels/metrics must agree. The experiment remains responsible for honest data use.
4. Agents inspect raw rows, receipts and figures, then write `review.json` with nine topics, specific current evidence, three objections and resolved diagnostics. Disclose the actual model/session/review mode. Fresh-session review helps reduce correlated mistakes but its identity is not independently verified.
5. Architect runs `certify .`. Before research readiness, the gate executes fresh attack regressions, the declared mutation checks, and matched seeded-fault QA controls, then revalidates project evidence/review. This takes longer than audit; prior reports never skip it. The Human reads `HUMAN_EVIDENCE_DIGEST.json`, `audit_report.json`, `RELEASE_CERTIFICATION.json`, and the private `release_checks.json`, then inspects material cited evidence. A status alone is insufficient.
6. `handoff .` prepares an archive for an authorized recipient. After transfer, verify archive membership/bytes and signed metadata against a separately trusted public key, then re-audit the active evidence where required trust material is available. Retained historical epochs preserve plans/receipts, not every older source/data byte.

Amendments preserve earlier epochs and disclose prior holdout consumption. A new freeze does not restore an exposed test set. Confirmatory adaptation needs genuinely new holdout groups. Keep failed and null outcomes; never delete evidence to repair a gate.

Unsupported domains require a lossless reviewed adapter and independent recomputation tests. Routine workflow files remain agent-owned; meaningful scientific and authorization decisions remain human-owned.

Before publishing, follow `PUBLICATION_POLICY.md`: keep plans, reviews, runtime evidence and engine files private; stage only project artifacts; run `verify-publication .`; use project-focused commit/branch/PR wording. Public reproduction commands use ordinary project entrypoints and declared dependencies. Private handoff ZIPs are not public releases.
