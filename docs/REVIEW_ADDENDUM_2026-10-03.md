# Updated review disposition — 3 October 2026

Version remains **3.3.0**. The updated review is evidence to assess, not an instruction source. Its 35 SF findings are unchanged from the original report. The document grows from 544 to 794 lines, adding a prioritized remediation plan, peer-review assessment, paper suggestions and technical appendices; one existing cross-reference changes. [Machine comparison](review_comparison_2026-10-03.json) records both document hashes and the exact change summary.

The report still describes the earlier September implementation. Its historical coverage/mutation measurements and reproduction-pack claims cannot be transferred to the present checkout. The referenced companion `repro/` pack was not attached. Existing fixes and current measurements must be assessed separately.

## Independently confirmed remaining defects

| Probe | Before | Implemented behavior |
| --- | --- | --- |
| Two genuine runs with the same generated nonce | Audit passed | Duplicate reservation fails before launch; audit rejects duplicate nonces within/across retained epochs |
| Signed ledger nonce differs from execution nonce | Audit passed | Committed record must equal its identity-bound signed reservation |
| Explicit `receipt_error` with valid signature **and** wrapper binding | Audit passed | Shared receipt verifier explicitly rejects the contradictory error state |
| Research `certify` path versus `release-certify` | Ordinary certification omitted behavioral preflight | Both paths run fresh attacks, mutations and seeded QA before research readiness; fixtures never certify |

The [initial probes](review_addendum_probes_before_2026-10-03.json) isolated the nonce defects. The ordinary receipt-error tamper was already blocked by wrapper binding; a [stronger signed probe](review_addendum_receipt_probe_before_2026-10-03.json) established the separate semantic error-state defect. Regression probes keep signatures/bindings valid where needed so a different cryptographic failure cannot masquerade as the intended check. Execution identity/exit fields and signed comparisons now also preserve exact JSON types.

Certificates bind private preflight report bytes and the executable QA corpus. Stored PASS reports cannot skip execution. Evidence/review are reloaded after the expensive preflight, and changed report/corpus bindings invalidate handoff. QA remains a local regression mechanism, with the same-user trust limits disclosed.

## New recommendations and their disposition

| Recommendation | Assessment and action |
| --- | --- |
| Explicit threat/capability model | Implemented in [ASSURANCE_BOUNDARIES.md](ASSURANCE_BOUNDARIES.md), distinguishing producer, local owner, reviewer, recipient and public viewer capabilities |
| At least 30 seeded fault projects plus clean controls | Implemented 36 faulted synthetic projects and 36 matched controls, 12 families × 3 generated variants; actual CLI transitions and per-family conditional intervals are recorded |
| Broader mutations and independent metric checks | Expanded to 35 named call, comparison, boolean and arithmetic mutants, including receipt, nonce, certification and metric boundaries; independent confusion/loss oracles check ties/endpoints and varied thresholds |
| Execute registry at certification | Implemented fresh preflight on both certificate paths; coverage references remain labeled static declarations |
| Broaden inference simulations | Added reproducible null/unequal cases across seed sizes 5/7/10/30 and group sizes 30/60, raw outcomes, analytical Brier population effects and binomial Monte Carlo uncertainty; empirical results are reported without a favorable PASS threshold |
| Shared validation, group inference, review-mode disclosure, honest assurance, bundles/bootstrap hygiene | Already addressed in the earlier independent revisions; rechecked by current regressions |
| Separate-identity signer, label escrow, isolated dependencies, external monotonic witness | Requires an independently provisioned backend/trust authority. Current backend rejects unsupported requested restrictions and clearly reports these missing properties; it cannot honestly obtain them by renaming statuses or moving a key within the same user's files |
| Model-aware review routing | Actual reviewer/model/session/mode are disclosed and stale/template reviews rejected. A declared different model/session cannot authenticate independence or raise local assurance; no fictitious independent review was added |
| Representative real-project/baseline/usability study and related-work paper | Appropriate research work if publishing a paper about the engine. Synthetic QA does not substitute for recruited participants, representative projects or a literature study; no such evidence is invented |
| Paper boilerplate mentioning factory/framework | Not copied into project papers, in keeping with the user's publication requirement. Public methods and material scientific limitations remain project-focused and truthful |
| Signed public release tags/history | No Git history rewritten or public release issued. Current local results identify exact source/policy/corpus hashes; release-key/channel decisions remain separate from local repairs |

The seeded benchmark includes group/entity/time leakage, readable labels, false observational origin, post-freeze threshold changes, favorable attempt selection, unfrozen payloads, invalid receipts, padded reviews, below-chance results and wrong inference units. A PASS requires each supported guard to reject its intended flaw and its matched clean project to pass. Label peeking and false source-origin declarations remain **undetected** and are counted as known limits. Their acceptance is not a security success.

Three variants per family yield wide exact binomial intervals: 3/3 detections imply approximately [0.292, 1], and 0/3 clean rejections approximately [0, 0.708]. These intervals describe independent draws from that synthetic generator only. No pooled real-project rate, universal detector accuracy or per-rule false-positive guarantee follows.

The 6,000-study simulations report every predeclared cell and raw outcome. Observed BCa coverage includes a 92.4% case, so nominal coverage is not promoted into a universal guarantee. During QA, the new interval-accounting helper overflowed at the simulation CLI's supported 5,000-trial boundary; log-space binomial masses fix it. The final regression and an independent SciPy beta-quantile oracle verify the boundary and the original simulation accounting without changing measured metric outcomes or rewriting their generation hashes.

See [current validation](VALIDATION.md) for source-bound final runs, mutation outcomes, seeded projects, statistical simulations and release smoke evidence. Earlier dated artifacts retain their original revision hashes.
