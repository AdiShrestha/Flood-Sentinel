# Active v3.3 policy

Start with the root README. Authority: user brief → constitution → factory specification → frozen project methodology/plan → implementation. Only v3.3.0 files outside `legacy/` govern active projects.

`gatekeeper.py` provides init, freeze, run, record, audit, certify, status, and handoff. Certification also runs provenance, tier, plausibility, coverage-liveness, and attack-registry gates automatically; the diagnostic commands remain available for CI. `run . all` automatically records and validates outputs, preserving failed attempts. `record` is a recovery/diagnostic command, normally unnecessary. `engine/metrics.py` recomputes independently from the project's metric code; `engine/audit.py` joins and validates current evidence; `engine/plan.py` defines the accepted plan contract; `engine/io.py` rejects malformed JSON and unsafe evidence paths; `engine/contract.py` enforces typed execution contracts; `engine/supervisor.py` provides Ed25519/HMAC receipt signing; `engine/schema.py` provides strict typed validators; `engine/attacks.py` defines the 18-entry attack registry.

Machine checks establish evidence admissibility within their declared scope. Review establishes a recorded scientific assessment, not independent proof. A stale or missing review never passes the release gate.

Scientific commands include `verify-constitution-coverage`, `verify-training-sufficiency`, `verify-split-integrity`, `verify-result-plausibility`, `verify-cross-artifact-traceability`, `verify-reproducibility`, `acquisition-audit`, `tier-check`, and `verify-bundle`. Use `python3 factory/run_self_tests.py` for the complete offline suite.
