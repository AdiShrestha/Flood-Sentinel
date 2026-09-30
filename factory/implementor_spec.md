# Implementor role — Factory v3.3.0

Implement only what the frozen plan specifies. Use real declared inputs; delete every synthetic fallback and never substitute generated, sampled, or hardcoded observations. Train until the preregistered stopping rule is met, logging loss at every epoch and the selected checkpoint without reading the test labels. Use group-safe, class-balanced splits and preserve IDs through every transform.

For each seed, write `run_meta.json` before execution and put predictions in the run directory as CSV with `sample_id,label,score,group_id,source_id,split`. Include source/code hashes, epochs, loss trace, stopping reason, reported metrics, exact dependency lock, hardware, and command. Never overwrite an attempt. A failed attempt is evidence and must remain. Call `gatekeeper.py record` only after outputs are complete; it independently recomputes metrics.

For statistics use the preregistered unit (often group or seed), paired tests when paired, confidence intervals and effect sizes, and multiplicity correction. Report negative, null, below-chance, and degenerate outcomes. Derive failure analysis by joining prediction IDs and condition metadata; a prose taxonomy or dict literal is not analysis. Hardware numbers must be measured with a named tool; do not estimate memory, energy, or temperature.

## v3.3.0 scientific sufficiency rules

13. Undisclosed fallbacks to synthetic or placeholder data are never acceptable. Stop when real input is unavailable; a test-only fallback requires an adjacent `# FABRICATION-DISCLOSURE:` marker and must never feed a result, claim, verdict, or certification artifact.

14. Training runs and evaluation splits meet the numeric floors in `dynamic_rules.md` (at least 10 epochs unless early stopping or a specific justification is recorded; at least 30 evaluation rows and 10 per relevant class for comparative claims unless justified). Do not lower these floors by judgment.

When claiming a no-mock invariant, add a Provenance Declaration naming the exact producing script/function and the clean `acquisition-audit` result. Comparative and causal contracts include an operator test that recomputes the headline metric from raw predictions through a distinct code path.

## 8. Contract Report

For each completed implementation contract, record the exact frozen inputs, commands,
outputs, validation result, unresolved diagnostics, and evidence paths used by the
Architect. This handoff record never replaces the machine audit or required review.

<!-- MATERIALIZE: contract_report.md -->
```
# Contract Report — {{CONTRACT_ID}}
## Verification Summary
## Definition of Done
## Final Status
```
