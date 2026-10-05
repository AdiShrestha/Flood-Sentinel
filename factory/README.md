# Active v3.3.0 policy

Start with the root README. Authority: user brief → constitution → factory specification → frozen project methodology/plan → implementation. Only v3.3.0 files outside `legacy/` govern active projects.

`gatekeeper.py` provides lifecycle operations and standalone evidence checks; `--help` lists the executable surface. `run . all` executes each registered experiment once and validates its outputs. Failed attempts require a disclosed new epoch before further execution. `record` rechecks an existing attempt; it never manufactures execution provenance.

`engine/metrics.py` recomputes supported metrics and paired inference. `engine/audit.py` joins current evidence and verifies receipt bindings. `engine/plan.py` defines the accepted plan; `engine/io.py` checks strict parsing and paths. Typed launch contracts are validated and legacy argv is translated through the same launch policy. `engine/supervisor.py` signs local Ed25519 receipts; `cryptography` is required. Local signatures provide tamper detection relative to a pinned key, without isolation from the OS user that owns the key.

Certification records a scientific assessment and local structural checks. Both certification commands run fresh attack, mutation and seeded-fault QA checks before research readiness and bind their reports/corpus to the certificate. A stored report never skips execution. Review mode is disclosed; same-session review does not acquire independent-review assurance. Read the human evidence digest and cited raw data before a consequential decision.

`python3 factory/run_self_tests.py` runs active unittest and function-style regressions with a temporary signing key. The archive verifier checks bytes and membership; external identity and same-user honesty remain outside the gate.

Project publication safeguards install with `init`: neutral `.gitignore` rules, private policy/report files and chained commit/push hooks. `verify-publication .` checks staged content and current reachable history. See [PUBLICATION_POLICY.md](PUBLICATION_POLICY.md) for supported public paths, artifact review and the limits of local hooks. Private review ZIPs must not be published.
