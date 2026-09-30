# Agent workflow (Human sees only the final gate)

1. Architect makes one `research_plan.json`: claims, estimands, populations, data access, group split, seeds, stopping, baselines, factorial ablations, sensitivity grid, OOD/limits, and command paths. Implementor challenges it before freeze.
2. Architect runs `gatekeeper.py freeze .`. This is the preregistration boundary. No confirmatory source/data/plan mutation is accepted afterward.
3. Implementor runs `gatekeeper.py run . EXP_ID`. It executes all seeds, keeps stdout/stderr and failed attempts, and calls `record` for each completed prediction file.
4. Agents run `audit .`, inspect raw rows and figures, then produce `review.json`. The review has nine checks, three concrete objections, responses, and limitations. Same-model review is disclosed.
5. Architect runs `gatekeeper.py certify .`; the Human reads `audit_report.json` plus `RELEASE_CERTIFICATION.json`. A failed gate becomes the next plan epoch; it is never patched by deleting evidence.
6. Agent runs `gatekeeper.py handoff .`. The Human moves the single ZIP; the receiving agent runs `gatekeeper.py verify-bundle <zip>` before using it.

For a claim that cannot be represented in this schema, stop and add a domain adapter with a lossless conversion, hashes, independent recomputation, and tests. Do not weaken the gate or call a structural check scientific.
