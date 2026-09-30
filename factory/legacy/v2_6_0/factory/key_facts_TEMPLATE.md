# Key Facts

Status: Frozen-policy file (amended only via Architecture Amendment). Created at Project
Initialization. Checked automatically by `gatekeeper.py release-check` before any release-bound
artifact (manuscript, `REPRODUCIBILITY.md`, supplementary material) is submitted.

List every numeric or named fact where an inconsistency between the manuscript and this project's
own knowledge base would be embarrassing or critical: casualty figures, coordinates, key dates,
named totals, anything a reviewer would flag as a factual discrepancy on sight. This is deliberately
bounded — `release-check` only catches drift against facts declared here in advance. It does not,
and cannot, perform open-ended fact-checking of prose (that would require AI reasoning Gatekeeper's
own Purpose forbids). If it isn't listed here, it isn't checked.

Each entry is a `## Key Fact:` block with exactly these fields. `anchor` is the word or short phrase
`release-check` searches for in the manuscript; `expected_value` and `tolerance` define the
acceptable numeric range near that anchor.

---

## Key Fact: {{short descriptive name}}
anchor: {{the word release-check searches for, e.g. "fatalities"}}
expected_value: {{number}}
tolerance: {{acceptable +/- range, 0 for an exact match}}
context: {{the full, correct statement and its source — e.g. "approximately 55 deaths, 70-74 missing, per [6][7][8]"}}

## Key Fact: {{next one}}
anchor: {{...}}
expected_value: {{...}}
tolerance: {{...}}
context: {{...}}

---

Add one block per fact worth protecting. A malformed block (missing `anchor:` or
`expected_value:`) is reported by `release-check` as a finding, not silently skipped — a Key Fact
you intended to declare but mistyped should never fail open.
