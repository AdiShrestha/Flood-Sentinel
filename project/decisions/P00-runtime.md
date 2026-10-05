# Decision Record P00: Runtime, Dependencies, and Domain-Interface Feasibility

**Status:** APPROVED (Architect Decision)  
**Date:** 2026-10-05  
**Scope:** Factory v3.3.0 execution contract, dependency isolation, macOS ARM M3 platform limits, and domain schema mapping.

---

## 1. Context and Problem Statement

The initial Flood Sentinel audit identified three foundational runtime barriers in Factory v3.3:
1. **Isolated Import Blockade:** Previous supervisor isolation flags (`-I -P -B -S`) stripped `site-packages` via `-S`, causing third-party dependencies (`numpy`, `torch`, `scipy`) to raise `ModuleNotFoundError`.
2. **Execution Contract Alignment:** Strict supervisor contracts construct argv deterministically from `runtime_id`, `entrypoint`, and positional placeholders (`{run_dir}`, `{seed}`, `{experiment_id}`). Project scripts must strictly accept this format rather than arbitrary ad-hoc flags.
3. **Platform Resource Semantics:** macOS Darwin does not support `RLIMIT_AS` (address space / memory bytes) or `RLIMIT_NPROC` (unprivileged Linux process limits). Requesting them in a contract fails closed under strict enforcement.

---

## 2. Architectural Decisions

### 2.1 Runtime Identity and Flag Specification
- **Runtime ID:** `python-cpu-v1`
- **Binary:** Active Python interpreter (`/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`)
- **Flags:** `['-s', '-B']`
  - `-s`: Disables user-site directory (`~/.local/lib/python3.12/site-packages`), preventing ambient user environment pollution.
  - `-B`: Prevents `.pyc` bytecode creation during execution, maintaining Merkle root inventory integrity.
  - Omission of `-S`: Preserves installed virtualenv/system site-packages, allowing verified dependencies (`numpy 2.5.0`, `torch 2.12.1`, `scipy 1.16.2`) to import cleanly.

### 2.2 Execution Contract Schema
All experiment contracts declared in `project/research_plan.json` must conform to:
```json
{
  "runtime_id": "python-cpu-v1",
  "entrypoint": "source/runners/run_smoke.py",
  "arguments": [
    "--experiment-id", "{experiment_id}",
    "--run-dir", "{run_dir}",
    "--seed", "{seed}"
  ],
  "network": "unrestricted",
  "wall_seconds": 300
}
```
*Note on Network and Limits:*
- `network` must be declared `"unrestricted"` or `"allowed"`. Declaring `"disabled"` fails closed because local supervisor execution cannot enforce kernel network isolation without containerization.
- `memory_bytes` and `process_limit` must **not** be declared on macOS Darwin. Resource bounds are managed via `wall_seconds` (enforced by supervisor timeout) and `cpu_seconds` (enforced via `RLIMIT_CPU`).

### 2.3 Dependency Locking
- The environment lock at `source/requirements.lock` records installed versions and SHA-256 package hashes.
- Prior to confirmatory execution, the supervisor binds `interpreter_hash` and `dependency_lock_hash` into Ed25519-signed execution receipts.

### 2.4 Domain-Interface & Schema Architecture
- Native factory profile `binary_classification` requires:
  - Cohort CSV with columns: `sample_id,label,group_id,split,source_ids`.
  - Predictions CSV with columns: `sample_id,score`.
- For Flood Sentinel hydrological forecasting:
  - `sample_id`: Formatted as `{site_no}_{issue_timestamp_utc}`.
  - `group_id`: Assigned to independent hydrological river basin / HUC-8 cluster (not temporal slice) to prevent spatial autocorrelation leakage.
  - `label`: Evaluated on future window $(t_{\text{issue}}, t_{\text{issue}} + H]$ with strictly prospective visibility.
  - Scores: Output continuous scalar anomaly or prediction scores.
  - Lossless adapters map full hydrological records into the binary schema without discarding timing metadata.

---

## 3. P00 Acceptance Criteria for Implementor

1. **Smoke Fixture Runner:** Implement a minimal, non-scientific runner (`source/runners/run_smoke.py`) that:
   - Accepts `--experiment-id`, `--run-dir`, `--seed`.
   - Imports `flood_sentinel`, `torch`, `numpy`, and `scipy`.
   - Produces a valid `predictions.csv` with `sample_id,score`.
2. **Supervisor Execution:** Execute through `factory/gatekeeper.py run . EXP_ID`.
3. **Receipt Validation:** Confirm supervisor generates a valid Ed25519-signed execution receipt binding outputs and interpreter hashes.
4. **Negative Mutation Test:** Verify that tampering with output files or receipts causes `audit` to fail closed.
5. **Fixture Disclosure:** The smoke fixture must be explicitly designated `"intent": "fixture"` and excluded from research claims.
