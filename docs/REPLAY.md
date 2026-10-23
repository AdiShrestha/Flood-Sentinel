# Replaying saved Flood Sentinel classifiers

The replay command runs selected classifier weights on a processed local bundle, writes fresh prediction ledgers, recomputes primary-support metrics, and compares both against the supplied saved ledgers and metric record. It performs inference only. It does not acquire data, train models, assert source vintage, or establish operational availability.

The manifest format is `flood-sentinel-local-replay-manifest-v1`. The example at [`examples/replay_manifest.example.json`](examples/replay_manifest.example.json) shows its required fields. Paths are resolved relative to the manifest unless written as absolute paths, so the manifest can live beside a private local bundle or be placed in another project directory.

The bundle must contain the normalized dynamic feature tensor, issue-to-window index, target labels and known-label mask, site static tensor, and issue metadata used by the saved fits. Each run names a `model_kind` (`no_ssl_tcn`, `ea_lstm`, or `score_d_transfer`), seed, architecture, selected checkpoint, validation-only thresholds, and saved prediction ledger. The deterministic-baseline ledger defines the locked primary common support. The paired-metric record supplies the comparison values.

Run from any working directory with the repository's supported Python environment and PyTorch installed:

```sh
python3 /path/to/flood-sentinel/source/runners/replay_flood_sentinel.py \
  --manifest /path/to/local/replay_manifest.json
```

The command writes one fresh compressed prediction ledger per run and `replay_report.json` beside the configured output directory. The report records runtime versions, maximum absolute logit and probability differences, primary support counts, metric differences, and a final pass flag. For each horizon it compares `n`, class denominators, confusion counts, alerts, exact-log-loss status, and the number of infinite exact-loss terms exactly; finite metric values and the threshold use the configured absolute tolerance. Undefined and infinite exact loss remain distinguishable even though both have a null numeric value. The default inference comparison tolerance is `atol=1e-6, rtol=1e-6`; primary-metric absolute tolerance defaults to `1e-10`. Change a tolerance only for a documented numerical compatibility reason and retain both the original and changed outcomes.

Only trusted, user-selected checkpoint files are loaded, using PyTorch's `weights_only=True`. The paths and data remain under the user's control. A passing replay confirms portable inference agreement for the supplied artifacts; it does not authenticate their origin, prove training provenance beyond their accompanying receipts, validate label science, or establish generalization.
