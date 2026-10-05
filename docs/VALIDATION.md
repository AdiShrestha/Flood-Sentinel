# Current review-addendum validation — 3 October 2026, v3.3.0

Version remains **3.3.0**. The runtime/policy revision is `1632a7117a671242b9733ae8606ccaced50dc1c11c5773e0f7c070af0fd3830c`; the current executable QA corpus is separately pinned in [validation_addendum_2026-10-03.json](validation_addendum_2026-10-03.json). The [updated-review disposition](REVIEW_ADDENDUM_2026-10-03.md) distinguishes new recommendations, previously corrected findings and unsupported claims.

- Self-test runner: **469 collected, 468 passed, 1 sandbox socket skip**, no failures/errors; source/policy/corpus unchanged during tests.
- Pytest: **468 passed, 1 skipped, 73 subtests passed**.
- Mutation benchmark: **35 baseline tests passed, 35/35 declared mutants killed**, no survivors, collection errors, skips or infrastructure errors. Operators include call deletion/replacement, comparisons, boolean conditions and arithmetic. The 80% gate applies only to this declared benchmark. [Artifact](mutation_checks_addendum_2026-10-03.json).
- Seeded-fault benchmark: **36 faulted synthetic projects plus 36 matched clean controls**, through actual CLI operations. **30/30 supported faults detected; 0/36 clean rejections; six label-peeking/false-origin faults remain undetected**. PASS reflects registered guard/control behavior and explicit known limits, not detection of every fault. Per-family samples are three variants with wide conditional intervals. [Artifact](seeded_fault_benchmark_2026-10-03.json).
- Registered attacks: **22/22 passed** in the complete `release-certify` smoke. Both certification paths now require fresh preflight before research readiness, and certificates bind the private report and QA corpus. The fixture smoke passed all stages, emitted one JSON document and correctly refused research certification with exit 43. [Artifact](release_smoke_addendum_2026-10-03.json).
- Repeated bootstrap, private hooks and real local push/clone passed. The clone contains only `.gitignore`, `README.md` and `source/main.py`, and executes without the private engine. [Artifact](publication_smoke_addendum_2026-10-03.json).
- Python/shell syntax, exact callable liveness (24 principles, 22 mechanisms, two procedural limits) and `git diff --check` passed. No source Git metadata or remote repository was changed.

The independently confirmed nonce/reservation and signed receipt-error probes are recorded [before](review_addendum_probes_before_2026-10-03.json), in the [stronger receipt probe](review_addendum_receipt_probe_before_2026-10-03.json), and [after repair](review_addendum_probes_after_2026-10-03.json). Their valid signatures/bindings isolate the intended semantic checks. Execution identity and signed bindings also reject JSON type confusion.

The [statistical simulations](statistical_simulations_2026-10-03.json) contain **6,000 studies**, 500 per cell: normal paired differences at 5/7/10/30 seed units under null/shifted means, and Brier comparisons at 30/60 independent balanced groups under equal/unequal model laws. Normal Student-t interval coverage was **93.0–95.8%**; group BCa coverage **92.4–95.8%**. Group null two-sided rejection rates were **4.0% and 5.2%**. Five seed units never reject at alpha 0.05 because the exact minimum two-sided p is 0.0625. Group intervals remain approximate; the 60-group unequal-law case covered only 92.4% (conditional binomial interval about 89.7–94.6%). These are observed synthetic results, not a uniform nominal-coverage guarantee or real-project performance estimate.

The simulation artifact preserves its original generation hash. The later binomial-accounting overflow repair leaves the runtime/policy and metric simulations unchanged. [Independent accounting verification](statistical_accounting_2026-10-03.json) pins the current QA corpus, recomputes counts from raw outcomes and validates 54 intervals against SciPy's beta-quantile implementation, including 5,000-trial cases; maximum absolute discrepancy is below `3.2e-15`. SciPy is an installed QA oracle, not a new engine dependency.

The [assurance boundary document](ASSURANCE_BOUNDARIES.md) defines actors/capabilities and supported properties. Same-user key/verifier isolation, hidden labels, truthful acquisition, authenticated review identity and external monotonic history remain unsupported. Private tooling never substitutes for truthful public project methods, scientific limitations or required attribution.

---

# Prior publication-boundary validation — 3 October 2026, v3.3.0

The visible version remains 3.3.0. This publication-boundary revision is identified by the runtime/policy hash in [validation_2026-10-03.json](validation_2026-10-03.json).

- Self-test runner: **447 collected, 446 passed, 1 sandbox socket skip**, no failures or errors. The suite includes **43 project publication regressions** over real Git repositories.
- Pytest: **446 passed, 1 skipped, 51 subtests passed**.
- Focused mutation benchmark: **25 baseline tests passed; 24/24 declared guard deletions killed (100%)**, including five publication guards. No survivors or infrastructure errors. This is a selected deletion benchmark, not repository-wide mutation coverage. [Full artifact](mutation_checks_2026-10-03.json).
- Release registry: **22/22 attacks passed**, including four publication regressions. Callable liveness: **24 principles, 22 mapped mechanisms, two procedural limits**.
- Full fixture `release-certify` smoke passed attack/mutation preflight and correctly refused research certification with exit 43. Its output is one JSON document. [Release artifact](release_smoke_2026-10-03.json).
- Bootstrap/reinitialization and local push/clone smoke passed. The clone contains only `.gitignore`, `README.md` and the project entrypoint, which executes without the private engine. [Publication artifact](publication_smoke_2026-10-03.json).
- Active Python syntax, bootstrap shell syntax and `git diff --check` passed; visible version is unchanged.

These checks include staged-versus-working bytes, forced internal/cache files, neutral ignore rules, nested exclusions, professional domain vocabulary, comments/docs/notebooks/CI, old history, commit/ref/tag metadata, assistant trailers, secret redaction, renamed archives, binary approval identity, LFS rejection, hook chaining and linked worktrees. They validate local guard behavior; they do not establish universal semantic detection or server enforcement. Public PR/issue/release text and external uploads require separate review. The [publication review](PUBLICATION_REVIEW_2026-10-03.md) records the change and its limits. Prior scientific validation below remains evidence about its stated revision.

---

# Prior independent review validation — 2 October 2026, v3.3.0

The visible version remains 3.3.0. These results apply to the hardened runtime/policy hash recorded in [validation_2026-10-02.json](validation_2026-10-02.json), not the earlier release tag.

- `python3 factory/run_self_tests.py`: **404 collected, 403 passed, 1 capability skip**, no failures/errors. The runner includes function-style regressions and isolates its signing keys.
- `python3 -m pytest factory/tests -q`: **403 passed, 1 skipped, 28 subtests passed**.
- `python3 -B factory/run_mutation_checks.py`: **20 baseline tests passed; 19/19 declared guard deletions killed (100%)**, no survivors/infrastructure errors/skips. The gate floor is 80%. This is a focused benchmark, not a repository-wide mutation score. [Full artifact](mutation_checks_2026-10-02.json).
- Registered attack regressions: **18/18 passed**. Exact callable liveness: 21 mapped mechanisms and two explicit procedural limits.
- Complete `release-certify` fixture smoke: attacks and mutation benchmark passed, output parsed as one JSON document, and research release was correctly refused with exit 43. Real relocated handoff projects re-audit without the original private keys.
- Syntax compilation, unused-runtime-import inspection and `git diff --check` passed. Bootstrap repeatability, cache exclusion and preservation of modified installations were tested.

Environment: macOS, Python 3.12.8, cryptography 49.0.0, pytest 9.1.1. The sandbox prohibits creation of UNIX sockets; that single capability test is explicitly skipped. FIFO rejection and other special-file checks run. Linux-specific limits were not executed here; unsupported local policies fail explicitly.

The independent normal-difference simulation covered the true mean in 946/1000 nominal 95% Student-t intervals. The 40-study equal-quality example gave 37 conditional fixed-corpus seed decisions and zero group-based population decisions. These are stylized checks under stated assumptions, not empirical error estimates for real projects.

Receipts and signed manifests establish consistency against their declared keys. Local signer/producer isolation, hidden labels, acquisition honesty, external review identity and monotonic history under signed-state rollback remain unsupported. Historical byte hashes are retained but changed prior frozen inputs are not reconstructed. Archived v2.6 code is inactive and excluded from the active release suite.

The [independent review](INDEPENDENT_REVIEW_2026-10-02.md) explains what was verified, corrected and bounded. Historical records below are retained as prior statements; their obsolete assurance claims do not apply to this checkout.

---

> October 2026 correction within v3.3.0: earlier entries describe historical claims and test runs. Local execution now requires Ed25519 (`cryptography`), verifies receipt bindings, and reports structural same-user assurance. Sealed evaluation and independent reviewer identity are not provided. Current validation must be read from the new machine report; historical counts are not a guarantee about this checkout.

# Validation record for v3.3.0

On 2026-09-16 UTC, the standard-library self-test suite ran with Python 3.12:
**276 tests passed**. The full Pytest suite passed **281 tests**. Added v3.3 checks cover typed execution contracts, supervisor signing keys and receipts, Merkle root frozen file inventories, strict typed schema validation, recursive plausibility analysis, reproduction identity binding, multi-level assurance statuses, 18 behavioral mutation attack registry tests, and standalone bundle verification.

The transfer archive is independently checked by both `verify-bundle` and `verify_bundle_standalone.py`, which validate member names, manifest membership, assurance level, and SHA-256 bytes without extracting files. This proves archive integrity, not source honesty or scientific truth.

The earlier validation records are retained below for historical provenance.

## Validation record for v3.2.0

On 2026-09-14 UTC, the standard-library self-test suite ran with Python 3.12:
**65 tests passed**. The full Pytest suite, including retained legacy regression
coverage, passed **283 tests and 1 subtest**. Added v3.2 checks cover inline
interpreter smuggling, JSON number overflow, bundle checksum tampering, generated
report freezing, certificate revocation, direct-attempt recovery binding, and
macOS `/var`/`/private/var` path aliases.

The transfer archive is independently checked by `verify-bundle`, which validates
member names, manifest membership, and SHA-256 bytes without extracting files.
This proves archive integrity, not source honesty or scientific truth.

The earlier v3.0.0 validation record is retained below for historical provenance.

The read-only v2.6 forensic tool ran against all 50 supplied Parquet runs using PyArrow and scikit-learn. Its machine-readable result is `docs/v26_forensic_results.json`. The active factory gate itself has no third-party dependency. Torch, GUDHI, pandas, device drivers, energy sensors, and domain libraries are intentionally not bundled: agents declare and lock them inside the project and the gate records their exact environment.

The suite includes adversarial fixtures, but a fixture cannot prove the honesty of arbitrary production code. Any claim beyond the binary-classification profile requires a reviewed lossless adapter and domain-specific mutation tests.
