# Coverage matrix: supplied findings and v2.7 proposals

| Finding / proposal | v3 treatment | Hard machine gate? |
|---|---|---|
| F-001, F-014 / D-075 | Recomputed sensitivity curves, planned levels, repeats; flat curves become diagnostics requiring review | Evidence audit + review |
| F-002, F-024 / D-076 | Declared producer scan; no synthetic fallback as admissible evidence; output is independently recomputed | Diagnostics + recomputation |
| F-003, F-004 / D-074, D-078 | Per-experiment stopping trace, checkpoint rule, min/max budget; no fixed epoch number is treated as proof | Yes |
| F-005 / D-077 | Source joins, class minimum, group/entity/source split disjointness | Yes |
| F-006, F-007 | Failure rows must join actual prediction/sample/source IDs; phantom IDs fail | Yes |
| F-008, F-009 | Constant/saturated/below-chance and non-finite predictions are surfaced; constant/null outcomes are not automatically falsified | Diagnostics; review |
| F-010, F-011 | Tuning/configuration and raw train/validation trace are part of frozen plan/receipt | Yes when claim requires them |
| F-012 | Test groups and class minimums are enforced; prospective precision target and correct sampling unit are required | Yes |
| F-013 | Generalization claim requires an OOD experiment; otherwise scope must be narrowed | Yes |
| F-015, F-016 | Negative/surprising results are retained as diagnostics and must be explained in review | Yes for unresolved diagnostics |
| F-017, F-020, F-021, F-022 | Certificate scope is narrow; review has nine concrete topics and objections, no regex-only PASS | Yes |
| F-018, F-019 | Hashes bind current bytes; fresh replay and independent metric implementation required | Yes |
| F-023 | Claims include exact estimand/population/scope and evidence experiments; review checks artifact pointers | Yes |
| D-074–D-078 | Included as stricter v3 invariants, with explicit exceptions only for deterministic methods and declared simulations | Yes |

V3 also closes previously unlisted bypasses: duplicate JSON keys, NaN/Inf, symlink/escape paths, plan/source mutation after freeze, command shell injection, repeated successful attempts, stale review, metric aliases, and unmeasured hardware quantities. It does not claim to detect an honest-looking lie in a correctly hashed artifact.
