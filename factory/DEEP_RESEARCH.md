# Deep research protocol (v3)

Use this file as an agent checklist before calling a result submission-ready. Define the estimand and population; identify the independent unit; preregister split, metric, threshold, seed, budget, stopping, baseline and multiplicity family; audit labels/source IDs and leakage; rerun every seed; recompute results; quantify uncertainty/effect size; complete factorial ablations and ±10/25/50% sensitivity; test realistic OOD/corruption/adversarial conditions; report subgroup failures and ceilings; measure hardware with raw synchronized trials if claimed; disclose data/code/protocol availability; perform a cold claims-evidence matrix, hostile objections, and venue checklist.

The gate enforces only the binary-classification subset documented in `docs/SCHEMA.md`. The Architect must adapt these questions to the domain and write the reasoning in `project/review.json`. A generic “all checks pass” sentence is inadmissible.
