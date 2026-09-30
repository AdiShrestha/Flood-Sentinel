# Migration validation and limits

The results below concern engineering and forensic checks, not flood prediction performance or scientific certification. Constructed test fixtures are disclosed in `source/tests/test_engine.py` and never enter a research cohort.

| Check | Observed outcome | Evidence |
|---|---|---|
| New engine: `python3 -m pytest source/tests -q` | 31 passed in 2.37 seconds | `logs/engine_tests.log` |
| Supplied active factory: `python3 factory/run_self_tests.py`, restricted execution | 275 passed; one Unix-socket bind denied by sandbox | `logs/factory_sandbox.log` |
| Same factory suite with permitted local socket operation | 276 passed | `logs/factory_permitted.log` |
| Isolated factory interpreter imports NumPy | Exit 1: `ModuleNotFoundError` under `-I -P -B -S` | `factory_compatibility.json` |
| Wheel packaging and isolated development import | All nine source modules and inherited notice included; imports succeeded | `package_validation.json`, `logs/package_build.log` |
| Legacy independent formula/cadence/label/metric audit | Completed, full outputs saved | `legacy_observations.json` |
| Legacy file/archive inventory | 2,186 files; 5,983 archive members; 921 unique hashes | `legacy_inventory.json`, `.csv` |

Engine checks cover issue availability and future-horizon/interval boundaries; confirmation at the correct alert time/gap reset; missing/zero distinction and train-fit scaling; robust/latent calibration degeneracy; actual fitted Mahalanobis distance; independently checked tie-aware ranking/probability metrics; causal prefix values/gradients; hidden-target input exclusion and observed-only losses; dtype/shape validation; true persistence and continuously carried detector state; and rejection of finite-input numerical overflow in fitted references, scores and reconstruction losses. Four probability cases are compared against the independently supplied factory oracle, including boundary probabilities.

The raw logs preserve the real outputs. Their timing is environment-specific and not a hardware benchmark. `environment.json` records the actual installed dependency/interpreter environment. `source/requirements.lock` is explicitly an installed-version snapshot; P00 must replace/supplement it with hash-verified installation evidence. The first package-smoke harness incorrectly expected ten modules; it was corrected to compare the actual source manifest and its failure is recorded. Packaging/import success does not solve the factory's `-S` dependency loading. Supplied factory/history whitespace and standard CSV CRLF are preserved; authored changes are checked separately.

Tests do not establish raw provider authenticity, split independence, representative sampling, model convergence, calibrated flood skill, population inference, operational deployment, completed research freeze or publication readiness. No legacy code was run as an acquisition/training producer, and no legacy checkpoint was transferred. Inspection scripts read stored values independently. Factory compatibility blockers and required adapters are documented in root `plan.md` and `factory_compatibility.json`.
