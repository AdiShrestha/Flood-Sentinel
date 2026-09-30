# What v3 actually checks

The active gate reads the frozen plan and run receipts. It hashes every declared source and dataset byte, rejects symlinks and unsafe paths, disallows duplicate JSON keys and non-finite values, and refuses plan or source changes after freeze. Experiment commands use an argument vector without a shell. Each preregistered seed gets an immutable attempt directory; failed attempts remain visible.

Before an experiment starts, the gate rejects common interpreter and loader
injection variables (`PYTHONPATH`, `LD_PRELOAD`, `DYLD_*`, `NODE_OPTIONS`, and
similar hooks) and sets `PYTHONHASHSEED` from the preregistered seed. This keeps
fresh-process runs tied to the recorded environment while preserving ordinary
project variables that are not code-loading hooks.

A run is admissible only when its prediction CSV has unique sample IDs, nonempty source IDs, two labels with at least two examples each in test, no group crossing train/validation/test, probabilities in range, nonconstant scores, and independently recomputed AUROC, average precision, accuracy, F1, Brier, and log loss. Reported numbers must agree to machine precision. A real loss trace, stopping reason, minimum training budget, source hashes, and hardware/dependency information are required. The engine uses paired bootstrap intervals and sign-flip tests only for aligned independent units, and Holm correction for a declared family; it does not infer independence from row count.

Static scans are defense in depth, not proof. They flag random sampling and mock/fabrication language in declared result producers; agents must explain training-only randomness or remove it. They cannot prove arbitrary code is honest, so semantic review and raw artifact inspection remain required and are disclosed in the certificate.

The certificate is deliberately scoped. It cannot establish causal validity, external validity, theoretical correctness, or journal acceptance from files alone. Those require domain judgment and evidence documented in the review.
