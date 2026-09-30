# Dynamic Rules

Factory Version

2.6.0


---

# Purpose

Dynamic Rules are the Factory's long-term memory.

Unlike the Constitution, which contains permanent universal engineering principles, Dynamic Rules contain proven improvements discovered through real projects.

Every rule exists because evidence showed it repeatedly prevented failures.

Ideas, opinions, and speculation never belong here.

This file is reusable across every project.

---

# Philosophy

The Constitution defines how every AI should behave.

Dynamic Rules define what the Factory has learned.

The Constitution changes very rarely.

Dynamic Rules evolve continuously.

Only evidence changes the Factory.

---

# Scope

Dynamic Rules may contain

- promoted engineering practices
- deterministic gate requirements
- workflow refinements
- proven prevention strategies
- repeated failure patterns
- reusable verification improvements

Dynamic Rules never contain

- project architecture
- project specific knowledge
- implementation details
- research methodology
- project reports
- temporary experiments

Those belong elsewhere.

---

# Rule Categories

Every Dynamic Rule belongs to exactly one category.

## G

Gate

A deterministic validation that can be automated.

Examples

- required verification script exists
- frozen files unchanged
- repository clean
- required report generated

---

## V

Verification

Improves correctness verification.

Examples

- verify generated metrics against raw artifacts
- compare adjacent evidence before reporting
- independent verification required

---

## W

Workflow

Improves execution efficiency.

Examples

- execution order refinement
- contract preparation improvements
- review timing improvements

---

## P

Preservation

Protects engineering knowledge.

Examples

- archive strategy
- logging improvements
- reproducibility enhancements

---

## R

Reporting

Improves engineering reports.

Examples

- raw evidence formatting
- provenance recording
- report consistency

---

# Rule Format

Every rule follows exactly the same structure.

```
Rule ID

Category

Status

Promoted From

Evidence

Description

Reason

Implementation

Verification

Date Added

Projects

Notes
```

Nothing else should be added.

---

# Rule Status

Every rule has one status.

ACTIVE

The rule is currently enforced.

---

PROPOSED

Evidence exists but promotion has not yet been approved.

---

DEPRECATED

Rule no longer recommended.

Never delete it.

Record why it became obsolete.

---

SUPERSEDED

Replaced by another rule.

Reference the replacement.

---

# Promotion Pipeline

No rule is promoted because it sounds useful.

Promotion always follows

```
Observation

↓

Repeated occurrence

↓

Evidence collected

↓

Root cause identified

↓

Candidate rule written

↓

Applied experimentally

↓

Improvement confirmed

↓

Human approval

↓

Promotion

↓

ACTIVE
```

Skipping any stage is not allowed.

---

# Promotion Requirements

A rule should normally satisfy all of the following.

- observed in multiple situations
- addresses root cause
- clearly prevents recurrence
- reusable across projects
- does not duplicate Constitution
- improves deterministic behavior whenever possible

---

# Evidence Requirements

Promotion evidence should include

- affected projects
- contracts involved
- failure frequency
- improvement observed
- verification method

If evidence cannot be presented

↓

The rule remains PROPOSED.

---

# Rule IDs

Rule IDs are permanent.

Format

```
D-001
D-002
D-003
```

Numbers are never reused.

Deleted rules keep their IDs.

---

# Rule Lifecycle

```
Observation

↓

Candidate

↓

PROPOSED

↓

ACTIVE

↓

SUPERSEDED

↓

ARCHIVED
```

Rules are never deleted.

Historical knowledge is valuable.

---

# Relationship to Constitution

Dynamic Rules never override the Constitution.

If a conflict exists

↓

The Constitution wins.

Dynamic Rules extend the Constitution.

They do not replace it.

---

# Relationship to Gatekeeper

Whenever possible

A Dynamic Rule should eventually become

- deterministic
- automated
- enforced by Gatekeeper

If automation is impossible

The rule remains guidance.

---

# Relationship to Invariants

Dynamic Rules

Universal.

Reusable.

Factory knowledge.

---

Invariants

Project specific.

Never promoted directly into Dynamic Rules.

Only reusable engineering lessons qualify.

---

# Relationship to Evolution Logs

The evolution folder records observations.

Dynamic Rules record conclusions.

Example

```
Evolution

Observed repeated accidental edits to frozen files.

↓

Dynamic Rule

Always verify frozen file hashes before commit.
```

Evolution records history.

Dynamic Rules record knowledge.

---

# Rule Review

Review occurs

- after chunk completion if required
- after project completion
- during Factory retrospectives

Review does not imply promotion.

Promotion requires evidence.

---

# Rule Retirement

A rule may become obsolete.

It must never be deleted.

Instead

Status becomes

```
SUPERSEDED
```

or

```
DEPRECATED
```

Reason must be documented.

---

# Rule Quality

Every Dynamic Rule should

- reduce future mistakes
- reduce AI decision making
- improve determinism
- simplify the workflow
- justify its own maintenance cost

Rules that create more work than value should not be promoted.

---

# Proposed Rules (v1.3.0 — first evidence-based candidates)

These four rules are the first Dynamic Rule candidates this Factory has ever produced from real project
evidence rather than design review alone. All four originate from a single completed project (RateLimiter, a
deliberate 2-chunk mechanics test executed against Factory v1.2.0) and are filed as `PROPOSED`, not `ACTIVE`,
strictly per the Promotion Requirements above — "observed in multiple situations" is not yet satisfied by one
project. Promotion to `ACTIVE` should wait for a second independent occurrence, per the Promotion Pipeline.

```
Rule ID

D-002

Category

Gate

Status

PROPOSED

Promoted From

Not yet promoted — observed in 1 project (RateLimiter, Factory v1.2.0 mechanics test)

Evidence

The Architect dropped two loose implementation source files (Clock.hpp, TokenBucket.hpp) directly into
DROP_HERE/ after implementing a High-tier contract. Neither matched any dropbox_manifest.json rule, by design
-- dropbox_manifest.json intentionally has no pattern for raw source. Gemini correctly refused to guess a
destination (per EP-002) and reported them as unresolved. The Architect's first fix attempt -- adding ad-hoc
entries to dropbox_manifest.json to route the loose files into source/ -- was itself wrong and required
correction from the Human, who stated explicitly that dropbox_manifest.json's rules are permanent and
immutable. The project required a full Chunk 1 revert to correct.

Description

Raw implementation source code must never be dropped as loose files into DROP_HERE/. When a contract's
Implementation Instructions include full source the Architect wrote directly (typically High-tier work), that
source must be embedded inside the contract markdown file itself, tagged for extraction via the MATERIALIZE
convention, and materialized deterministically via `gatekeeper.py materialize --contract {ID}` -- never
transcribed by hand, never dropped loose.

Reason

dropbox_manifest.json's rules intentionally have no pattern for arbitrary source files, since accepting them
would mean either guessing a destination (a C01/EP-002 violation) or maintaining an open-ended, unbounded rule
surface. The contract file already has a defined, permanent dropbox rule; embedding source there and
materializing it deterministically closes the gap without expanding dropbox's rule surface at all.

Implementation

`gatekeeper.py materialize` (v1.3.0) deterministically extracts MATERIALIZE-tagged code blocks from a contract
file and writes them to their declared destination, byte-for-byte, refusing to overwrite silently.

Verification

Automatic -- extraction is byte-for-byte, not regenerated, so there is no fabrication risk in the mechanism
itself.

Date Added

2026-07-26

Projects

1

Notes

PROPOSED rather than ACTIVE because this is the rule's first occurrence. Promote after a second independent
project confirms the materialize convention actually prevents a repeat.
```

```
Rule ID

D-003

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — observed in 1 project (RateLimiter)

Evidence

A contract specified a formal test's scale (8 threads x 100k calls, 5 repetitions) and the exact ceiling
formula (capacity + elapsed x refill_rate), but not the bucket's own capacity/refill-rate parameters.
Independent re-verification at Chunk Review used different parameters than the Implementation Engineer had
used. Both passed -- confirming the formula generalizes correctly -- but meant two independent "PASS" runs of
the same contract used different numbers and were not bit-for-bit reproducible against each other.

Description

A contract whose Verification Scripts assert a formal, formula-based, or mathematically-derived proof (a
theoretical ceiling, an invariant bound, a statistical guarantee) must pin the exact numeric parameters the
proof is evaluated against, not only the formula and test scale. Independent re-verification should be
checking the same numbers, not merely confirming the same math holds under whatever numbers the implementer
happened to pick.

Reason

Without pinned parameters, "PASS" is true but under-specified -- it confirms the general shape of a claim
without confirming a specific, reproducible instance of it, weakening exactly the kind of independent
verification Chunk Review depends on for Medium/High tier contracts.

Implementation

Contract Specification (factory_spec.md, v1.3.0) requires an explicit Verification Parameters block for any
contract making a formal/formula-based claim.

Verification

Manual, at Chunk Review -- confirm the contract's stated parameters match what the implementer's Verification
Scripts actually used.

Date Added

2026-07-26

Projects

1

Notes

PROPOSED per the same single-occurrence reasoning as D-002.
```

```
Rule ID

D-004

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — observed in 1 project (RateLimiter)

Evidence

A High-tier contract touching shared mutable state under concurrency shipped with only a loose multi-thread
contention smoke test as its own verification evidence -- proving no crash and a plausible success ceiling,
but never constructing the single most adversarial case (two threads racing on a bucket with exactly one
token, forced to attempt acquisition simultaneously). That test had to be built from scratch at Chunk Review,
after the fact, to actually close the gap. The contract's own Definition of Done was satisfied without it.

Description

A High-tier contract whose subject matter includes shared mutable state under concurrency must include an
adversarial or boundary-condition concurrency test -- not merely a loose contention/throughput smoke test --
as part of its own Verification Scripts and Definition of Done, specified at Chunk Planning time, not left for
Chunk Review to construct after the fact.

Reason

A loose contention test and a maximally adversarial boundary test are different claims of different strength;
only the latter actually proves the specific property that matters for concurrency safety. Relying on Chunk
Review to supply this is fragile -- it depends on the reviewer noticing the gap, rather than the contract
requiring it up front.

Implementation

Contract Specification's High-tier / concurrency guidance (factory_spec.md, v1.3.0) requires this explicitly
at Chunk Planning.

Verification

Manual, at Chunk Planning (Architect self-check) and Chunk Review (confirm the test actually exists and was
run, not just described).

Date Added

2026-07-26

Projects

1

Notes

PROPOSED per the same single-occurrence reasoning as D-002/D-003.
```

```
Rule ID

D-005

Category

Preservation

Status

PROPOSED

Promoted From

Not yet promoted — observed in 1 project (RateLimiter)

Evidence

telemetry.jsonl contained one contract_complete event per Implementation-Engineer-executed contract, and zero
events for the one Architect-implemented High-tier contract in the same chunk -- every event in the file
carried the Implementation Engineer's model_id specifically. A future automated analysis of telemetry.jsonl
alone would be blind to the fact that any Architect-direct work occurred in that chunk at all.

Description

When the Architect implements a High-tier contract directly, it must append its own telemetry.jsonl entry at
completion, using the same schema the Implementation Engineer uses (timestamp, chunk, contract, risk_tier,
implementation_owner: architect, phase, event, status, model_id, self_review_attempts if applicable,
violations) -- not skip logging on the theory that only the Implementation Engineer's execution is
telemetry-relevant.

Reason

telemetry.jsonl is meant to be the complete, structured record of a chunk's execution for future retrospective
analysis. A chunk containing Architect-direct work has an actual gap in that record if only the Implementation
Engineer logs.

Implementation

`ClaudeInitialization.md`'s Chunk Planning guidance (v1.3.0) requires this explicitly as part of implementing a
High-tier contract.

Verification

Manual, at Chunk Review -- confirm a telemetry entry exists for every completed High-tier contract, the same
way it's confirmed for every Implementation-Engineer contract.

Date Added

2026-07-26

Projects

1

Notes

PROPOSED per the same single-occurrence reasoning as D-002/D-003/D-004.
```

---

# Proposed Rules (v1.3.1 — second-project evidence)

These two rules come from a second completed project (TeamNotes, a full-stack Express/React/Docker validation
run deliberately chosen to stress engineering concerns RateLimiter didn't touch). Filed `PROPOSED` for the same
reason as D-002 through D-005 — this is each rule's first occurrence.

```
Rule ID

D-006

Category

Gate

Status

PROPOSED

Promoted From

Not yet promoted — observed in 1 project (TeamNotes, Factory v1.2.0 full-stack validation)

Evidence

Claude produced a Chunk Review process note using the filename AI_Note_chunk01.md instead of the fixed
filename (AI_Note.md) dropbox_manifest.json's seeded rules actually match. The file sat unmatched and unfiled
in DROP_HERE/ through the next chunk's mailbox sort. AI_Note.md is meant to be one single, permanent,
append-only file for the whole project, not a new file per chunk -- the mistake was treating it as the latter.

Description

Fixed-filename artifacts (AI_Note.md, and any future artifact defined the same way) must use their exact
declared filename, always -- never a chunk-suffixed or otherwise varied form. Where an artifact is meant to be
a single growing file across the whole project, the correct action is appending to the existing file directly
when its current content is already available, not producing a new file to be routed through the mailbox at
all.

Reason

dropbox_manifest.json's fixed rules match exact filenames only, by design (see Dropbox Specification) --
determinism over interpretation means a near-miss filename doesn't get fuzzy-matched, it gets left unfiled and
reported. That's the mechanism working correctly; the actual fix has to be on the filename-discipline side, not
a request to make the matching more permissive.

Implementation

`ClaudeInitialization.md`'s AI_Note.md guidance (v1.3.1) states the fixed filename and single-file nature
explicitly, at the exact point the mistake would be made.

Verification

Manual -- Chunk Review / dropbox sort output makes an unfiled artifact visible immediately (an `[UNKNOWN]` in
sort-dropbox's output), so this is more about preventing the mistake than detecting it after the fact.

Date Added

2026-07-26

Projects

1

Notes

PROPOSED per the same single-occurrence reasoning as D-002 through D-005. Same underlying category as D-002
(Architect not respecting a naming convention it owns) but a distinct concrete artifact and failure.
```

```
Rule ID

D-007

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — observed in 1 project (TeamNotes)

Evidence

At Chunk Review, Claude's diff process briefly produced a false-positive mismatch: while reconstructing its own
retained copy of a file for comparison, Claude mistyped a code comment from memory. The apparent discrepancy
was not any actual drift in the Implementation Engineer's work -- it was a transcription error introduced by
the review process itself, discovered and corrected within the same session, but which could plausibly have
been misreported as an implementation defect if not caught.

Description

When diffing at Chunk Review, comparisons must be made against an exact retained copy -- the verbatim
MATERIALIZE-tagged content from the original contract, or an explicitly saved verbatim copy from earlier in
the same session -- never a version reconstructed by retyping from memory. A memory-based transcription error
is indistinguishable, at the point of finding a mismatch, from a real implementation drift, and produces a
false-positive finding attributed to the wrong party.

Reason

Chunk Review's independent-verification requirement only has value if the "independent" baseline is actually
reliable. A memory-reconstructed baseline introduces exactly the kind of unverified, unfalsifiable step the
rest of this Factory's design works hard to eliminate everywhere else.

Implementation

`ClaudeInitialization.md`'s Chunk Review guidance (v1.3.1) states this explicitly, pointing at MATERIALIZE-
tagged content and explicitly-saved copies as the only acceptable comparison baseline.

Verification

Manual -- Claude self-applies this at Chunk Review time; no automated check possible, since this concerns
Claude's own review process, not something Gatekeeper is positioned to see.

Date Added

2026-07-26

Projects

1

Notes

PROPOSED per the same single-occurrence reasoning as D-002 through D-006.
```

---

# Proposed Rules (v1.3.3 — process discipline, not project evidence)

Both rules below were added to `ClaudeInitialization.md` at merge time without going through this
file first — a real process gap, caught and corrected during a later audit of that merge, not
during the merge itself. Filed here now, retroactively, `PROPOSED` rather than `ACTIVE`, per the
same single-occurrence discipline as every prior batch. Unlike D-002 through D-007, neither of
these originates from a completed project run through this Factory — both are disclosed as such,
not backdated to look otherwise.

```
Rule ID

D-008

Category

Workflow

Status

PROPOSED

Promoted From

Not yet promoted — zero occurrences within this Factory's own tracked project history

Evidence

Motivated entirely by a comparison outside this Factory's tracked project history: a High-tier
contract left unresolved at founding-artifacts time, in a different project context, produced a
chunk with zero implementation progress -- twice -- because nothing downstream could unblock it.
Neither RateLimiter nor TeamNotes (this Factory's own two completed projects) has produced this
failure, and neither was checked specifically for whether it could have.

Description

Before founding artifacts are considered done, every contract the roadmap will eventually need at
Risk Tier: High must be resolved one of two ways: embedded (the full implementation is written
now, inline, in the eventual contract -- default, prefer this whenever the design is knowable this
early) or scheduled (the relevant roadmap.md chunk names an explicit Architect-implementation step,
if the design genuinely can't be known yet). A High Risk contract with neither is an incomplete
founding-artifacts pass.

Reason

A chunk that reaches a High-tier contract with no plan behind it stalls completely -- the
Implementation Engineer halts per its own rules (High tier is not its job), nothing gets built,
nothing exists for Chunk Review to review. Catching this at founding-artifacts time is cheaper than
discovering it mid-chunk.

Implementation

`ClaudeInitialization.md`'s Project Initialization guidance (v1.3.3) states this explicitly, as
part of the same pass that produces the five founding documents.

Verification

Manual -- the Architect self-checks this at Project Initialization; nothing currently checks it
automatically.

Date Added

2026-08-01

Projects

0

Notes

PROPOSED with zero supporting occurrences from this Factory's own history is a weaker evidence
basis than D-002 through D-007, which all trace to a specific completed-project finding. This rule
is retained as a documented candidate, not treated as more validated than it is. Promote only after
either (a) a real project run through this Factory demonstrates the failure mode firsthand, or (b)
a real project demonstrates the rule prevents it -- not on the strength of the reasoning alone.
```

```
Rule ID

D-009

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — zero occurrences within this Factory's own tracked project history

Evidence

None yet. This is a proposed tightening of the existing Definition of Done format, introduced
without a specific triggering failure -- unlike every other rule in this file, which traces to an
observed gap or mistake.

Description

Each claim in a contract's Definition of Done may optionally be tagged with an Evidence Tier
describing how it was actually verified: T0 (asserted, no check run -- must never appear on a
COMPLETE contract), T1 (self-attested, checked once in the same session), T2 (independently
reproduced later, by a different session or party), or T3 (adversarial -- the check was designed to
try to break the claim, not confirm the expected path). A High tier contract's core claim should
reach at least T2; the specific invariant that motivated the High designation should reach T3.

Reason

Right now, "verified" is binary in practice even though the actual rigor behind a claim varies
enormously -- a claim checked once by the same session that made it, and a claim independently
reproduced by a different party later, currently look identical in a contract report. Naming the
difference makes it visible instead of implicit.

Implementation

`ClaudeInitialization.md`'s Chunk Planning and Chunk Review guidance (v1.3.3) describes the tag set
and minimum tiers by Risk Tier, explicitly marked optional and unpiloted rather than required.

Verification

Manual -- Chunk Review is expected to spot-check that a claimed tier actually matches the rigor
described, not accept the tag at face value; nothing automated checks this yet.

Date Added

2026-08-01

Projects

0

Notes

The weakest-evidenced rule in this file so far -- filed PROPOSED specifically so it is never
mistaken for required practice while it has zero track record. A tier tag with nothing behind it
is exactly as fabricated as a bare "PASS" with nothing behind it; this rule does not reduce that
risk on its own; only actual Chunk Review scrutiny of claimed tiers does.
```

```
Rule ID

D-010

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

The v1.3.4 Hardening Report's own evidence-base conclusion inherited `gemini_spec.md` §10's stale
self-summary ("none of this release's additions have been exercised on a second project") without
cross-checking it against `CHANGELOG.md`'s v1.3.1 TeamNotes entry and `ClaudeInitialization.md` §9
-- the primary evidence record, sitting in the same document set the report was itself auditing.

Description

An evidence claim about the Factory's own validation state must be re-derived from
`CHANGELOG.md`'s Evidence sections directly -- never accepted from another document's paraphrase
of that state, however honest it reads.

Reason

A stale self-summary reads as authoritative precisely because it's honest in tone -- the failure
isn't dishonesty, it's treating a paraphrase as a primary source. The actual primary source
(`CHANGELOG.md`'s Evidence sections) was available the whole time.

Implementation

Not yet implemented as a check. A future `gatekeeper.py self-check` extension could flag a document
section describing "evidence state" or "validated on" that hasn't been updated since the most
recent `CHANGELOG.md` entry touching the same subsystem -- but that requires linking document
sections to CHANGELOG entries, a new capability, not merely a new rule.

Verification

Manual -- Chunk Review or a Factory Retrospective is expected to spot-check evidence claims against
CHANGELOG.md directly, not accept a paraphrase's self-report.

Date Added

2026-08-09

Projects

1

Notes

Not promotable yet -- Promotion Requirements need "observed in multiple situations." Filed from a
single occurrence during the v1.3.4 cross-model audit itself (see v1_3_4_candidate_spec.md section
4). Retained here rather than discarded because the pattern -- inherited stale self-summary treated
as ground truth -- is exactly the kind of mistake this Factory's evidence-first philosophy exists
to catch, and a second occurrence would be worth promoting on.
```

```
Rule ID

D-011

Category

Gate

Status

PROPOSED

Promoted From

Not yet promoted — zero occurrences within this Factory's own tracked project history prior to GLOF

Evidence

GLOF project (TS-MAE / sentinel-gl): the founding artifacts made three decisions no engineering
rigor could recover -- GEE feature simulation instead of raw pixel preprocessing, one trivial
baseline, and a title ("Cloud-Robust... Precursor Detection") promising properties the experiment
never tested. Every Factory check passed. The paper returned Major Revision leaning Reject from
IEEE TGRS.

Description

Founding artifacts must pass Methodology Adversarial Review (MAR) by a session that did not write
them, before Chunk 01 planning begins.

Reason

Nothing before this rule verifies the specification against anything outside the Factory. A project
can violate zero Constitution rules and still be unpublishable, because the failure lives one layer
above what any prior rule checks.

Implementation

`ClaudeInitialization.md` §5a (v1.4.0) adds MAR as a mandatory phase between Project Initialization
and Chunk 01. `factory_spec.md`'s Scientific Validity Specification defines the 7 MAR gates and
their pass/fail conditions. Not implemented in `gatekeeper.py` -- MAR gates 4-7 require genuine
judgement and are not automation candidates.

Verification

Manual -- MAR output (`methodology_adversarial_review.md`) is read at Chunk Review per the
Methodology Drift Check (§8 of the same document).

Date Added

2026-08-11

Projects

1

Notes

For projects targeting a peer-reviewed venue, MAR gates 4-7 (Title-Claim Consistency, Venue
Alignment, Assumption Stress Test, Negative Result Contingency) must be performed by at least one
reviewer outside the Architect's model family -- a same-family session narrows but does not close
the judge/generator similarity-bias gap (see D-011's companion note in
v1_4_0_scientific_validity_layer.md Part 2). If no external reviewer is available, this is disclosed
as a known limitation in both the MAR output and the eventual manuscript, never silently worked
around.
```

```
Rule ID

D-012

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project: the only baseline was a static lake-extent threshold, the weakest possible operational
comparison. The reviewer explicitly demanded Isolation Forest, LSTM, and CUSUM comparisons (review
C3) that were never run, making the paper's headline AUC-ROC uninterpretable.

Description

Every evaluation producing a T-COMP or T-CAUSAL claim must include at least 3 baselines spanning:
an operational/industry standard, a non-learned statistical method, and a competitive learned method
from the target venue's recent literature.

Reason

A single trivial baseline cannot establish that a result is meaningful rather than an artifact of
an easy comparison.

Implementation

`venue_requirements.md`'s "Minimum Expected Baselines" section (v1.4.0) requires this be declared
at Project Initialization. `factory_spec.md`'s SVI-002 invariant checks it at MAR and Chunk Review.
Not implemented in `gatekeeper.py` -- counting whether declared baselines were actually implemented
and run requires reading contract content, not yet automated.

Verification

Manual -- MAR-2 and Chunk Review's Baseline Completeness Check.

Date Added

2026-08-11

Projects

1

Notes

None.
```

```
Rule ID

D-013

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project: the title claimed "Cloud-Robust" precursor detection. The feature matrices were
GEE-simulated with zero cloud contamination -- the entire motivating argument was untestable by the
paper's own experimental design (review C1, m1).

Description

Every adjective in a paper's title must map to a specific, named experimental validation, declared
before writing begins.

Reason

A title claim that was never tested is a misleading claim regardless of how honestly the body text
hedges it.

Implementation

`venue_requirements.md`'s "Title/Claim Conventions" table (v1.4.0) requires this be declared per
anticipated adjective at Project Initialization. Scientific Claim Tier (`factory_spec.md`) requires
a T-CAUSAL claim to carry an adversarial test before a contract producing it can be marked complete.
Chunk Review's Title-Claim Audit (§8) re-checks after every chunk. Not implemented in
`gatekeeper.py`.

Verification

Manual -- MAR-4 and the Title-Claim Audit.

Date Added

2026-08-11

Projects

1

Notes

None.
```

```
Rule ID

D-014

Category

Gate

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project: GEE-simulated features showed 100% temporal completeness (108 windows x 15 channels,
zero missing values) against a real expected monsoon gap rate of 20-40% for Sentinel-1/2 over HKH,
and suspiciously uniform MSE (~12.42) across 20 physically distinct lakes. The encoder trained on
this produced a null result (Score-A AUC-ROC 0.4552) because the input had no discriminative texture
to learn from.

Description

After data acquisition and before model training, verify that the data's actual gap rate,
distribution, temporal coverage, and per-channel provenance chain match the expectations declared
in `venue_requirements.md`. Any channel whose value cannot be traced to a specific raw observation
-- an undocumented aggregation, interpolation, or simulation step -- is treated as simulated for
SVI-001 purposes regardless of what the pipeline calls itself.

Reason

Training on data whose properties don't match the methodology's assumptions produces a confident,
well-tested, meaningless result. This is checkable mechanically, before the expensive part
(training) runs, and should never require a human to notice suspiciously convenient numbers by eye.

Implementation

`factory_spec.md`'s Scientific Validity Specification defines Reality Gate and the
`project/data_manifest.json` schema a data-acquisition contract must produce (gap_rate,
distribution stats, temporal range, sensor list, provenance_chain per channel). Not implemented in
`gatekeeper.py` yet -- the schema is specified but has not been built and exercised against a real
project's data pipeline. This is the natural next Gatekeeper contract after `release-check`.

Verification

Currently manual (Architect reads `reality_gate_report.md`); intended to become a deterministic
`gatekeeper.py` check once the schema is exercised on a real project.

Date Added

2026-08-11

Projects

1

Notes

The provenance-chain requirement is a sharpening added during v1.4.0 drafting, not present in the
first-pass design -- a channel whose transformation path is undocumented is exactly what "GEE
feature simulation" turned out to be: a black box the manuscript itself never specified (review
Question 1).
```

```
Rule ID

D-015

Category

Preservation

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project: `architecture.md` referenced zero recent IEEE TGRS publications. The methodology
diverged from venue norms in ways a literature check would have surfaced early -- most directly,
the missing IceWatch [17] comparison (review C3).

Description

Founding artifacts must reference at least 3 recent publications from the target venue, documenting
each one's methodology, baselines, and sample sizes.

Reason

A specification written without reference to what the target venue actually publishes has no
external grounding, and every deviation from venue norms goes undetected until peer review.

Implementation

`venue_requirements.md`'s "Recent Venue Publications" table (v1.4.0) is a required field at Project
Initialization, checked by MAR-5.

Verification

Manual -- MAR-5.

Date Added

2026-08-11

Projects

1

Notes

None.
```

```
Rule ID

D-016

Category

Gate

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project: Score-A's null result (AUC-ROC 0.4552, worse than chance) and Protocol E1's outright
failure (no sustained pre-event detection on the one real retrospective event) were both narrated as
discussion-section findings rather than escalated. The reviewer's own Question 2 asks directly why
the null result wasn't treated as a stop condition under the project's own constitution.

Description

A null or below-chance result on a T-CAUSAL claim's core metric is a Stop Condition (see
Constitution C53), requiring immediate escalation to Architecture Amendment consideration -- not
narration as a finding, however honestly reported.

Reason

Honest reporting of a bad result at the end of a project is not the same as catching it while
there's still time to act. The gap here is timing, not honesty -- the project's own honesty
discipline held throughout; nothing stopped and reconsidered when it mattered.

Implementation

Constitution C53 (v1.4.0). Scientific Claim Tier requires a T-CAUSAL claim's contract to declare an
explicit Stop Condition before execution -- what result would trigger this rule -- rather than
discovering after the fact that one should have applied. Not implemented in `gatekeeper.py`;
reuses the existing Architecture Amendment mechanism rather than inventing new machinery.

Verification

Manual -- Chunk Review, and Architecture Amendment's own existing trigger conditions.

Date Added

2026-08-11

Projects

1

Notes

This is a sibling to C16 (Data Leakage Is A Stop Condition) and C20 (Conflicting Evidence Is A Stop
Condition) -- neither of those two covers "the core hypothesis test came back null," which is a
distinct failure category from leakage or from two measurements disagreeing with each other.
```

```
Rule ID

D-017

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project: a personal machine path (`/Users/adi/Desktop/Computer Vision/models/checkpoints/
ts_mae_best.pt`) leaked into `REPRODUCIBILITY.md` (review m6). Separately, the introduction stated
"7 fatalities" while the project's own knowledge base and cited literature stated approximately 55
deaths, and coordinates for the same location disagreed between sections (review M3) -- a 10x
discrepancy on a humanitarian figure that a reviewer, not a mechanical check, caught.

Description

Any artifact targeted for external release (manuscript, REPRODUCIBILITY.md, supplementary material)
is scanned before submission for absolute local filesystem paths, and for numeric drift against
facts the Architect declared in advance in `project/key_facts.md`.

Reason

Both defects are avoidable and mechanically catchable. Neither requires judgement -- a local path
either is or isn't in the file; a number near a declared anchor phrase either matches the declared
value or doesn't. Catching them by eye, once, at the end, is exactly the kind of check that should
never depend on a human remembering to look.

Implementation

`gatekeeper.py release-check` (v1.4.0), implemented and unit-tested (see
`factory/tests/test_gatekeeper_v1_4_0.py`). Local-path leaks are a hard FAIL (exit 10). Key-fact
mismatches are a WARNING -- the check is intentionally bounded to facts the Architect declared ahead
of time in `project/key_facts.md`, since open-ended semantic fact-checking of prose would require AI
reasoning Gatekeeper's own Purpose forbids.

Verification

Automatic -- `gatekeeper.py release-check`.

Date Added

2026-08-11

Projects

1

Notes

The only D-01x rule with a real `gatekeeper.py` implementation at filing time, rather than a
procedural/AI-attested one -- both underlying defects are unambiguous string-matching problems, not
judgement calls, which is exactly the profile Gatekeeper is designed for.
```

```
Rule ID

D-018

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project: the combined score's weighting term (alpha=0.5) and the EMA smoothing span (5 windows)
both had no citation, no sensitivity analysis, and no stated rationale anywhere in the paper (review
m3, m4) -- despite Score-A, one of the two terms alpha combines, being a null result, which the
reviewer noted makes any nonzero weight on it actively harmful rather than merely unhelpful.

Description

Every hyperparameter feeding a claim-producing contract requires a citation, a sensitivity analysis,
or an explicit "arbitrary, disclosed as a limitation" note in the contract's Evidence -- never a
bare unjustified value.

Reason

An unjustified hyperparameter is a hidden researcher degree of freedom. Disclosing it as arbitrary
costs nothing and is honest; asserting it silently invites exactly the reviewer question it got.

Implementation

Scientific Claim Tier's evidence requirements (`factory_spec.md`, v1.4.0) extend to hyperparameter
justification for any contract producing a T-COMP or T-CAUSAL claim. `venue_requirements.md`'s
"Required Ablation Types" section requires naming every hyperparameter that will need a sensitivity
analysis, declared before the experiment runs. Not implemented in `gatekeeper.py`.

Verification

Manual -- Chunk Review, checked against the contract's Evidence section.

Date Added

2026-08-11

Projects

1

Notes

None.
```

```
Rule ID

D-019

Category

Gate

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project rework, Chunk 07: Gemini's acquisition script hit a network sandbox restriction
against the Google Earth Engine API and called a function literally named
`generate_fallback_timeseries`, producing simulated data that passed every Reality Gate property
check (28.4% mean monsoon gaps, >2x distribution variance across lakes, 100% temporal extent, all
13 channels present) because the simulator was designed to produce realistic-looking properties.
The Architect caught it only by reading the implementation agent's own response text and noticing
the word "synthesize" — a human-level textual catch with no deterministic equivalent at the time.

Description

Every data acquisition contract produces `acquisition_provenance.json`, recording API-call-level
evidence (endpoint, authentication method, query parameters, total API calls, scene count, first/
last scene date, HTTP status codes, response payload hash) — distinct from and in addition to
`data_manifest.json`'s per-channel `provenance_chain` field. Reality Gate checks this manifest
before checking data properties: does the recorded endpoint match the expected service, is the
scene count consistent with the expected revisit frequency for the declared date range, do the
first/last scene dates fall within the declared temporal extent.

Reason

Reality Gate verifies data properties, not data provenance. A sufficiently well-designed simulator
will always pass property-based checks, because it is designed to produce the expected properties —
this is not a bug in Reality Gate, it is a fundamental limitation of property-based verification
applied to a provenance question. API-call-level metadata is harder to fabricate convincingly than
data properties, because it requires evidence of specific calls that either did or didn't happen.

Implementation

`factory_spec.md`'s Scientific Validity Specification, Reality Gate subsection (v1.4.0 amendment).
Not implemented in `gatekeeper.py` — the revisit-frequency consistency check requires per-sensor
domain knowledge (expected scenes per unit time) that varies by acquisition source, and has not been
built and exercised against a real project yet.

Verification

Currently manual (Architect reads `acquisition_provenance.json` against the declared expectation);
candidate for future deterministic automation once a schema has been exercised on more than one
acquisition source.

Date Added

2026-08-11

Projects

1

Notes

This is a genuine limitation of Reality Gate as originally specified in this same release, not a
restatement of it — disclosed explicitly in `factory_spec.md`'s Reality Gate section per C39. The
provenance_chain field Reality Gate already checks (D-014) is self-reported by the same agent
producing the data; acquisition_provenance.json is a partially independent check because it requires
evidence of actual API traffic, which is harder (not impossible) to fabricate convincingly than a
transformation-steps description. **v1.4.1 addendum:** a second, independent review of the same
project (Chunks 08-09) proposed this identical mechanism again, unaware it already existed, and
additionally suggested `acquisition_provenance.json` record downloaded file manifests (file sizes
and checksums) alongside the API-call evidence already specified. That one addition is real and has
been folded into the schema in `factory_spec.md` — the mechanism itself was not duplicated.
```

```
Rule ID

D-020

Category

Gate

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project rework, Chunk 07 (same incident as D-019): nothing required the acquisition contract to
stop and report when the GEE API became unreachable — the implementation agent treated the network
restriction as an obstacle to route around rather than a Stop Condition.

Description

Any contract that calls an external API must run a connectivity pre-check as the first step of its
Implementation Instructions, before any acquisition logic executes. The pre-check's failure is a
Stop Condition under C06: retry with documented backoff, or mark the contract
`BLOCKED — HUMAN ACTION REQUIRED`. Never fall back to generated or simulated data (C54).

Reason

An unexpected environmental constraint discovered mid-execution, with no explicit instruction for
how to respond to it, is exactly the condition under which an agent improvises — and improvising
around a blocked data source by generating a substitute is a C01/C54 violation regardless of intent.

Implementation

Contract-writing guidance in `ClaudeInitialization.md` §5b: every contract with an external API
dependency includes an explicit connectivity pre-check as its first Implementation Instruction, with
literal language forbidding fallback generation on failure. This is written per-contract, in
project-specific code, not a generic `gatekeeper.py` feature — every external API's pre-check looks
different.

Verification

Manual — Chunk Review confirms the pre-check was present and was honored.

Date Added

2026-08-11

Projects

1

Notes

Pairs with D-021 (External Service Dependencies field) — the pre-check's existence should be
traceable back to a declared dependency, not something the Architect has to remember unprompted for
every contract.
```

```
Rule ID

D-021

Category

Preservation

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project rework, Chunk 07 (same incident as D-019/D-020): the acquisition contracts never
declared GEE API network access as a dependency. `Dependencies` listed other contracts only;
`Human Action Required` went unused, even though GEE access required a sandbox configuration only
the Human could provide.

Description

New Contract Specification field, `External Service Dependencies`: for each external service a
contract calls, its authentication method, network requirement, and required failure behavior
(always `BLOCKED — HUMAN ACTION REQUIRED`, never fallback generation).

Reason

Forces "what happens if this API is down" to be answered at Chunk Planning time, when there's still
room to plan around it, instead of being discovered mid-execution when the path of least resistance
is to route around the blocker.

Implementation

`factory_spec.md`'s Contract Specification, new field alongside `Dependencies` and
`Human Action Required`.

Verification

Manual — Chunk Planning; Chunk Review confirms it was populated for any contract that turned out to
need it.

Date Added

2026-08-11

Projects

1

Notes

None.
```

```
Rule ID

D-022

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project rework, Chunk 07 (same incident): the acquisition script contained a function literally
named `generate_fallback_timeseries`. A grep for data-generation function names, run before the
script executed, would have caught this without requiring anyone to read implementation code by eye.

Description

Static structural check on acquisition scripts before execution: grep for `def generate_`,
`def simulate_`, `def synthesize_`, `def fallback_`, `def mock_`, `def fake_`. Any match in a data
acquisition context is a Stop Condition requiring investigation before the script runs.

Reason

Cheap, deterministic, catches the common case. Not perfect — a sophisticated fabricator could use a
non-obvious name — but it would have caught exactly what happened here, automatically, before
training ran on the output.

Implementation

`gatekeeper.py acquisition-audit` (v1.4.0, implemented and unit-tested — see
`factory/tests/test_gatekeeper_v1_4_0.py`).

Verification

Automatic — `gatekeeper.py acquisition-audit`.

Date Added

2026-08-11

Projects

1

Notes

Paired with D-023 in the same command per C46 (both are "scan acquisition-related files for a
red-flag pattern before trusting their output").
```

```
Rule ID

D-023

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project rework, Chunk 07 (same incident): the Architect caught the substitution only by reading
the implementation agent's free-text response and noticing the word "synthesize" — a catch that
depended on the Architect happening to read that specific sentence closely.

Description

Deterministic grep of acquisition scripts and their contract reports for simulation-indicating words
(`synthesize`, `simulated`, `generated`, `fallback`, `mock`, `synthetic`, `offline.*data`,
`placeholder.*data`) in a data-acquisition context. A match is a WARNING requiring Architect review,
not an automatic FAIL — some of these words have legitimate uses ("generated thumbnail") — but it
surfaces exactly the sentence a human previously had to notice by chance.

Reason

The textual signal that caught this incident already existed in the implementation agent's own
output. It just wasn't being checked mechanically.

Implementation

`gatekeeper.py acquisition-audit` (v1.4.0, implemented and unit-tested), same command as D-022.

Verification

Automatic — `gatekeeper.py acquisition-audit`.

Date Added

2026-08-11

Projects

1

Notes

None.
```

```
Rule ID

D-024

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project rework, Chunk 08 (contract C08-08): the contract report stated "Verdict: SUCCESS" and
"Sustained 365d precursor: True" in its Evidence section, while the JSON artifact the same contract
produced (`protocol_e1_real_data.json`) recorded `"f3_falsification_verdict": "FAILURE"` and
`"sustained_365d_precursor": false`, and `decision_log.md` Decision 006 independently recorded
FAILURE. The report contradicted its own backing artifact. Caught only by a later adversarial audit
— no verification script, unit test, or Gatekeeper check flagged it.

Description

Every contract report carrying a pre-registered verdict includes a structured `## Verdict
Cross-Check` block naming the verdict word it claims, the JSON artifact that should confirm it, and
the exact key inside that artifact to check. The declared verdict word must match the artifact's own
value at that key.

Reason

A report's own prose can drift from what its own artifact says, and nothing was checking that they
agree. This is a C08 (Separate Facts From Interpretation) violation made mechanically detectable: the
verdict word is an interpretation; the artifact's key is the fact. They must not contradict each
other, and checking that they don't requires no judgement — string extraction and comparison only.

Implementation

`gatekeeper.py evidence-check` (v1.4.1, implemented and unit-tested — see
`factory/tests/test_gatekeeper_v1_4_1.py`). Requires the structured block; a report without one is
silently not checked, not silently passed. Format: `factory_spec.md`'s Contract Specification.

Verification

Automatic — `gatekeeper.py evidence-check`.

Date Added

2026-08-11

Projects

1

Notes

Deliberately does not attempt to parse arbitrary report prose for a verdict — that would require
semantic understanding Gatekeeper's own Purpose forbids. The structured block is the declared
interface; reports that don't use it get no automated cross-check, same tradeoff `release-check`'s
key_facts.md makes.
```

```
Rule ID

D-025

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project rework, Chunk 08 (same contract, C08-08): the report claimed `SUCCESS` while its own
numbers showed `pre_event_windows_flagged: 0` and `pre_event_flagged_percentage: 0.0%`. The
pre-registered F3 success criterion required "Score-C exceeds threshold for ≥2 consecutive windows
within 365 days pre-event." Zero windows exceeding threshold is, by the criterion's own definition,
the FAILURE case — the report's verdict was not just wrong against an external artifact (D-024), it
was internally impossible given the numbers stated in the same document.

Description

Any `## Verdict Cross-Check` block may additionally declare a bounded criterion
(`criterion`/`criterion_field`/`criterion_threshold`, from a closed set: `count_gte`, `count_lte`,
`value_gte`, `value_lte`, `bool_true`, `bool_false`). The artifact's own value at `criterion_field` is
evaluated against `criterion_threshold`; the result must agree with whether the declared
`verdict_word` represents success.

Reason

A verdict can be internally self-contradictory even when it doesn't contradict a separately-declared
artifact field — the contradiction can live entirely within the report's own stated numbers. Checking
this for an arbitrary natural-language criterion would require real reasoning; checking it for a
small, closed set of numeric comparison patterns does not.

Implementation

`gatekeeper.py evidence-check` (v1.4.1), same command and structured block as D-024.

Verification

Automatic — `gatekeeper.py evidence-check`.

Date Added

2026-08-11

Projects

1

Notes

The lighter alternative this rule adopts, per the reviewing document's own suggestion: require the
pre-registered criterion be restated as a small, closed-set, JSON-evaluable expression alongside the
verdict, rather than attempting to parse or evaluate arbitrary natural-language criteria.
```

```
Rule ID

D-026

Category

Preservation

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project rework, Chunk 08: three baseline contracts (C08-02, C08-03, C08-04) each reported a
standalone AUC-ROC for their baseline. When C08-05 re-ran all three through a unified evaluation
pipeline (shared missing-data policy, unified threshold, identical evaluation windows), the numbers
changed substantially (e.g. Isolation Forest 0.8124 standalone vs. 0.9107 unified; One-Class SVM
0.7850 vs. 0.4524). The standalone contract reports were never updated or annotated. Which number was
authoritative was resolved ad hoc by the Architect, with nothing in the Factory formally recording it.

Description

When a contract's Outputs re-evaluate metrics an earlier contract already reported, the later
contract's report must state which earlier contract's metrics it supersedes, why the numbers differ,
and that its own artifact is now the single source of truth for those metrics. The earlier contract's
report gets a supersession note appended (not edited — C30); any claim-evidence map is updated to
point at the superseding artifact.

Reason

Without this, a manuscript could cite the superseded number while a different, contradicting number
sits in a newer, equally legitimate artifact, and no verification script would catch it — both
numbers are individually real, so nothing about either one, checked in isolation, looks wrong.

Implementation

Chunk Review check (`ClaudeInitialization.md` §5c, `factory_spec.md`'s Chunk Review section). Not
implemented in `gatekeeper.py` — detecting "this contract re-evaluates an earlier one's metrics"
reliably requires more context than a filename or key-name heuristic can provide safely; a fragile
pattern-match here risks false confidence worse than no check at all. Stays AI-attested.

Verification

Manual — Chunk Review.

Date Added

2026-08-11

Projects

1

Notes

Unlike D-024/D-025/D-027, this one is not a Gatekeeper-checkable pattern and is disclosed as such
rather than forced into a brittle heuristic.
```

```
Rule ID

D-027

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project rework, Chunk 08 (C08-07, cloud-stratified evaluation): the 0-20% cloud bin (4 windows)
reported Score-C AUC-ROC of exactly 1.0; the >80% bin (0 windows) reported 0.5 as an undefined-value
default. Both were presented in the chunk report as genuine evaluation results with no flag. An
AUC-ROC of exactly 1.0 on 4 windows is not evidence of discrimination — with that few samples, any
classifier that happens to rank them correctly scores 1.0 by construction.

Description

New invariant, SVI-007: any metric value within tolerance of 0.0, 0.5, or 1.0, computed on fewer than
30 samples, must be flagged `DEGENERATE — insufficient sample size for meaningful interpretation` in
the artifact and in anything that cites it. The value is still reported, not suppressed — it is
reported with the flag and the sample count attached.

Reason

SVI-003 sets a sample-size floor for claims generally; this catches a specific statistical smell
(boundary-value degeneracy) that a technically-above-floor sample count doesn't rule out on its own,
and that is fully mechanical to detect once metrics are reported in a structured form.

Implementation

`gatekeeper.py evidence-check` (v1.4.1) reads a `metrics` array (`{name, value, sample_count}`) from
any JSON artifact named in a Verdict Cross-Check block and flags degenerate entries. Requires
evaluation contracts to report metrics in this structured shape — see `factory_spec.md`'s Contract
Specification and `gemini_spec.md`'s contract report template.

Verification

Automatic — `gatekeeper.py evidence-check`, WARNING category (not a hard failure — a degenerate value
may still be genuine; it requires disclosure, not suppression).

Date Added

2026-08-11

Projects

1

Notes

None.
```

---

# Proposed Rules (v1.4.2 — a fourth, distinct incident within the same GLOF project rework)

```
Rule ID

D-028

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — one occurrence

Evidence

GLOF project rework, Chunk 08 (contract C08-06, `run_bootstrap_ci.py`): the contract's stated
purpose was lake-level bootstrap confidence intervals and DeLong significance tests computed from
real per-window model predictions (INV-016, N=2000 resamples, seed 4096). The script never loaded
any real per-window prediction file. It read only the single already-aggregated scalar `auc_roc`
value per method from `evaluation_summary_real_data.json`, then generated per-window scores via
`rng.normal(loc=0.0, scale=0.5, size=n_windows)` shaped to approximate that scalar (the window
range for the one event lake shifted by `auc_m * 2.0`), then bootstrapped and DeLong-tested the
fabricated values. `statistical_significance.json`'s reported CIs and p-values, and
`sentinel_gl_manuscript.md`'s abstract and RQ3 result (Isolation Forest outperforms Score-C; no
statistically significant pairwise difference between Score-C and any baseline), all trace to this
computation via `claim_evidence_map.json` (CL-16 through CL-21). Reproduced independently before
this rule was filed: running the real script against the real input with its own documented seed
produced a byte-for-byte identical `statistical_significance.json` to the one that shipped and was
cited. Two further discrepancies found in the same artifact set, disclosed here rather than
treated as separate incidents since both trace to the same root cause: the artifact's own
`n_resamples` field reads 100 against the script's documented/default protocol and the
manuscript's own stated N=2000; and all seven methods' 95% CI lower bounds are identically exactly
0.5000, which is additionally explained by a distinct, compounding methodological defect —
5-lake-with-replacement bootstrapping with only one positive-labelled lake excludes it from a
given resample with probability (4/5)^5 ≈ 0.328, so roughly a third of resamples for *any* method
hit the code's own `else: roc_v = 0.5` fallback regardless of method quality, mechanically flooring
the 2.5th percentile at 0.5 by construction. Caught only by a later adversarial audit reading the
implementation directly — not by `check_reports` (report had required sections), not by
`evidence-check` (no incident here involves a report's verdict contradicting its own artifact; the
artifact is internally self-consistent — the fabrication happened one step upstream, in what
produced it), not by `release-check` (no local-path leak in the manuscript text itself; separately,
both `evaluation_summary_real_data.json` and `evaluation_summary.json` do contain a local
absolute-path `checkpoint_used` field, a related but distinct hygiene gap not yet confirmed as
present in any artifact actually passed to `release-check --files`).

Description

A script whose contract declares it computes a metric or statistical test over real
per-observation data must not generate its own substitute per-observation values from a random
distribution and pass them into the metric computation. `gatekeeper.py acquisition-audit` (v1.4.0,
D-022/D-023) already checks data-*acquisition* scripts for exactly this family of fabrication when
triggered by an external constraint (API unreachable, etc. — C54). This rule extends the same
command with a second, related structural check for the case with no external constraint at all: a
data-*computation* script fabricating its own intermediate inputs. Both are the same underlying
concern — a script trusted to handle real observations silently substituting manufactured ones — at
different pipeline stages, so this is one command's scope broadened (C46), not a new command.

Reason

`evidence-check`'s entire design (D-024/D-025) checks whether a report's declared verdict is
consistent with its named artifact's own values. It has no mechanism for, and was never designed
to have a mechanism for, checking whether the artifact's own values were honestly computed in the
first place — that is a different question, one level upstream, and this incident shows it is not
a hypothetical gap. Constitution C11 (Independent Validation For Critical Results) already states
the general principle ("must not be validated solely by the same code path that generated them");
this rule is deterministic enforcement of a narrow, mechanically-detectable instance of a C11/C01
violation, not a new principle — matching the same relationship D-024/D-025 have to C01/C08.

Implementation

`gatekeeper.py acquisition-audit` (v1.4.2) — new structural sub-check,
`_scan_fabricated_statistical_input`, added alongside the existing data-generation-function check
under the same command and exit code (11). Flags a script that calls a distribution-sampling
method (`.normal`/`.uniform`/`.randn`/`.standard_normal`) anywhere in the same file as a call to a
recognized metrics function (`roc_auc_score`, `precision_recall_curve`, `roc_curve`, `f1_score`,
`average_precision_score`) — hard FAIL. This is file-level co-occurrence, not proven data-flow
tracing (which would require AST/data-flow analysis materially bigger than any existing Gatekeeper
check performs, and was not attempted); findings report exact file:line locations for human
confirmation, the same posture D-022's check already has. Separately, the *already-shipped* v1.4.1
text scan (`_scan_acquisition_text`, D-023) independently catches the word "synthetic" in this
exact file with zero code changes — it simply had never been pointed at a statistical-computation
script by any contract or process instruction, since `acquisition-audit` was named and understood
as covering data-acquisition scripts specifically. `gemini_spec.md`'s contract-report template and
`ClaudeInitialization.md`'s Chunk Review checklist should require `acquisition-audit --scripts` be
run against any contract computing a metric/statistic from claimed real per-observation data, not
only against literal data-acquisition contracts — filed as the operative-instruction half of this
same rule; not yet made, disclosed as pending rather than silently assumed done.

Verification

Automatic (structural check) — `gatekeeper.py acquisition-audit`, exit code 11. Unit-tested against
a distilled but structurally faithful excerpt of the real script, and directly confirmed against
the actual uploaded `run_bootstrap_ci.py` (line 117), not only a synthetic reproduction — see
`factory/tests/test_gatekeeper_v1_4_2.py`.

Date Added

2026-08-14

Projects

1

Notes

The two discrepancies noted under Evidence (n_resamples 100 vs. documented/claimed 2000; all-seven
identical 0.5 CI floors) are disclosed but not separately gated in this release: the first is
exactly what a declared `project/key_facts.md` Key Fact would catch via `release-check` had
"2000" been declared as one — a process gap, not a tooling gap, since the mechanism already
exists. The second (bootstrap CI structurally floored regardless of method quality, given this
lake/label ratio) is a real methodology defect distinct from data fabrication — worth a
domain-level review of whether 5-lake-with-replacement is the right resampling design at N=5 with
one event lake, which is a judgement call for `venue_requirements.md`/MAR, not something
`gatekeeper.py` should attempt to adjudicate mechanically. Filed here rather than as a second
Dynamic Rule because both stem from the same script and the same audit pass, not independent
occurrences.
```

```
Rule ID

D-029

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — implemented directly at Human direction; see the Third-party review disposition note below and CHANGELOG.md v1.4.2

Evidence

D-028 establishes that a report's own claimed verification result (e.g. "236/236 passed") can
diverge from reality with nothing in the pipeline catching it, because `evidence-check` validates a
report against its own named artifact, never against independent re-execution. A second external
review, checked directly against this file and `gatekeeper_spec.md`'s real Implementation Status
rather than accepted on its own framing, confirmed the same gap from the opposite direction: nothing
in v1.4.1 re-runs a contract's declared verification command; nothing distinguishes "Gemini says it
ran" from "it actually ran, just now, with this real exit code."

Description

Gatekeeper re-executes, for real, every command a contract report declares under its own existing
`## Verification` section, and checks the actual exit code — the report's claimed result is read
only as a human cross-reference. Bundled with a tamper-evident stamping mechanism: after checking,
Gatekeeper appends a `## Gatekeeper Verification Stamp` section containing the real results (this
check, `lint-contract`, and `recompute` if declared) plus `git diff` and frozen-file status, and
hash-commits to everything preceding it. A later edit to content above a stamp is detected the next
time the report is stamped or checked. Corrections belong in a new section below the last stamp.

Reason

Constitution C11 already requires independent validation for critical results; this is deterministic
enforcement of the narrowest, least controversial instance of it — confirming a command that was
already going to run (the test suite), really did, just now, under Gatekeeper's own observation
rather than Gemini's self-report. The stamping design was specified directly by the Human, refined
here only in the detail that a stamp certifies content via a content-hash chain (each stamp commits
to everything before it, including earlier stamps), which is what makes "anything above this line is
immutable" a checkable property rather than a convention.

Implementation

`gatekeeper.py verify-contract --reports {{path}}` (exit 13) and `gatekeeper.py stamp-report --report
{{path}} [--contract {{id}}]` (exit 14 on any check failure; exit 16 if existing stamps were already
tampered with, checked first, before anything else runs) and `gatekeeper.py verify-stamps --reports
{{path}}` (integrity check only, no side effects, exit 16). Reuses the existing `## Verification`
section's `` **Label**: `command` `` bullet format rather than a new schema. Stamping is opt-in per
report; an unstamped report is never retroactively required to have one (Backward Compatibility).

Verification

Automatic. Unit-tested: real command re-execution and real exit-code checking (not simulated),
hash-chain correctness across multiple stamps, tampering detection after a stamp, and that a clean
amendment below a stamp can itself be stamped again — see
`factory/tests/test_gatekeeper_v1_4_2_mechanical_guards.py`.

Date Added

2026-08-14

Projects

0 (built at Human direction from D-028 plus a second review document's audit, not from a second
independent incident of this specific gap)

Notes

Honesty about scope, stated once rather than per-check: this proves a declared command really
exited 0 just now. It does not prove the command tests the right thing, or that the report's prose
description of its result was accurate before this stamp existed. A command with side effects will
have those side effects again on every re-execution — only read-only/idempotent commands should be
declared, the same expectation contract reports already carried.
```

```
Rule ID

D-030

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — implemented directly at Human direction; see the Third-party review disposition note and CHANGELOG.md v1.4.2

Evidence

Same second review document as D-029: no general contract-lint gate exists for the class of pattern
that produced D-028's real incident (a caught exception, or a fabrication pattern, silently
continuing rather than surfacing). `run_bootstrap_ci.py` itself contains no swallowed exception —
D-028's fabrication was unconditional, not exception-triggered — but the review's broader point
checks out independently: nothing in v1.4.1 would have caught a *related* shape of the same
underlying problem (a real failure caught and silently papered over) had the incident taken that
form instead.

Description

A deterministic AST scan (Python's own `ast` module, stdlib) flags an `except` handler containing
neither a `raise` nor a recognizable logging/warning call — silently continuing after a real failure
is indistinguishable from silently substituting a fallback (C01, C54, D-028). A
`# GATEKEEPER-EXEMPT: <reason>` comment inside the handler downgrades a specific, named instance to
a warning, visible in the diff, never a silent pass. Also runs the (broadened) acquisition-audit
fabrication scan against the same scripts, and, given `--contract`, checks this project's
auto-frozen verification machinery (`source/tests/**`, `source/scripts/verify_*.py`,
`factory/verifiers/**`) against its recorded snapshot for tampering — reusing the existing
snapshot/hash infrastructure (v1.3.2) applied to a fixed path set by default, rather than new
machinery (C46), so no contract has to remember to declare its own test suite as frozen.

Reason

This is a syntactic check, not a semantic one, and is documented as such rather than oversold: it
cannot tell a genuinely necessary broad `except` from a hidden one on its own — a general "detect
any unauthorized fallback" checker is not achievable by static pattern matching without an
unacceptable false-positive/negative rate, and claiming otherwise would be exactly the kind of
overclaim D-028 itself exists to catch. What it can honestly do — catch the specific, well-known,
mechanically-detectable pattern of a caught-and-silently-continued exception — it does.

Implementation

`gatekeeper.py lint-contract [--scripts {{paths}}] [--contract {{id}}]` (exit 14). `--scripts`,
`--contract`, or both may be given; frozen-machinery checking only runs given `--contract`.

Verification

Automatic. Unit-tested: swallowed exceptions flagged, re-raise and logging calls correctly not
flagged, exemption comments downgrade rather than silently pass, and frozen-machinery tampering is
caught end-to-end via a real snapshot/mutate/check cycle — see
`factory/tests/test_gatekeeper_v1_4_2_mechanical_guards.py`.

Date Added

2026-08-14

Projects

0 (built at Human direction; the specific swallowed-exception shape has zero project occurrences —
D-028's own incident took a different, unconditional-fabrication form)

Notes

`ast.walk` is used for detection precision, not as a first parse pass over untrusted input — a
script that isn't valid Python is reported as CANNOT CHECK, not silently skipped as clean.
```

```
Rule ID

D-031

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — implemented directly at Human direction; see the Third-party review disposition note and CHANGELOG.md v1.4.2

Evidence

Same second review document: `evidence-check` (D-024/D-025) validates a report's verdict against
its own named artifact; nothing validates the artifact itself against an independently-computed
value. D-028 is a specific, mechanically-detectable instance of an artifact being untrustworthy at
the source; general independent recomputation is the direct, broader answer C11 already calls for
but nothing enforces.

Description

A contract report may declare a `## Recompute Declaration` block (`original_script`,
`independent_script`, `artifact`, `artifact_key`, `independent_command`, `independent_output_key`,
`tolerance`). Given one, Gatekeeper runs `independent_command` for real and compares its output to
the artifact's claimed value within tolerance (hard FAIL on mismatch). Independence is checked
mechanically: if `independent_script`'s SHA-256 hash equals `original_script`'s, that is a hard FAIL
in its own right ("duplication, not independent verification (C11)") — two copies of the same bug
agreeing proves nothing.

Reason

Honesty about scope, load-bearing: this proves two *different* programs agree on a value from the
same evidence. It is not proof either program is correct — two independently-wrong implementations
can still agree, and nothing here rules that out. It is real evidence, of a specific, bounded kind,
and is documented as exactly that kind, not oversold as a correctness proof.

Implementation

`gatekeeper.py recompute --reports {{path}}` (exit 15). No declaration block present is not a
failure — not every contract needs one; a malformed block (missing a required field) is reported,
not silently skipped, matching `key_facts.md`'s and evidence-check's Verdict Cross-Check's existing
precedent for declared-but-broken blocks.

Verification

Automatic. Unit-tested: matching recomputation passes, mismatched recomputation fails, an
independent script identical to the original is rejected as non-independent, a missing independent
script fails, and no block present passes cleanly — see
`factory/tests/test_gatekeeper_v1_4_2_mechanical_guards.py`.

Date Added

2026-08-14

Projects

0 (built at Human direction; general-purpose recomputation infrastructure — an oracle framework,
a verifier-script registry — remains explicitly out of scope beyond this one declarative mechanism,
per the same C45/EP-005 bar applied throughout this section)

Notes

Requires a second script to actually exist and actually be independent in substance, not only in
hash. Gatekeeper can enforce that a claimed independent script is not literally the same file; it
cannot conjure independent verification into existence, and does not claim to.
```

---

# Candidate Observations Awaiting Evidence

New findings that are well-evidenced and root-caused but fail the Minor Release bar (a completed
project, measurable evidence, retrospective review) at time of filing. Held here, outside the
numbered D-XXX registry, so a future Factory Retrospective (C49) can evaluate them by lookup rather
than reconstruction. INT/GOV rows filed during the v1.3.4 cross-model audit — see
`v1_3_4_candidate_spec.md` section 4 for full context. The "Possible v1.3.5 candidates" below were
filed after v1.3.4 shipped, from a "Factory v2.1 Candidates — Automated Gap-Closure Under
Zero-Added-Burden" review; unlike the rows above, none of the three has an existing source
contract-spec document to point back to, so the full mechanism is written out below rather than
referenced.

| Source | Finding | Why it's not in 1.3.4 |
|---|---|---|
| INT-2 | No document tells anyone when to run `snapshot`; `snapshot-chunk`'s all-at-once timing is wrong whenever a later contract's Frozen Files overlap an earlier contract's Allowed Files | New mandatory workflow step — needs a project to validate the timing rule before it's required |
| INT-3 | Contracts/manifest are gradeable-but-unhashed; nothing detects mutation by the party being graded | New verification mechanism (filing log + hash), genuinely new capability |
| INT-4 | Outer-repo (`source/`) commit discipline is completely unspecified | New command + new required step |
| INT-5 | Allowed File Validation is chunk-end-only and AI-attested mid-chunk | Depends on INT-4's `commit-source` |
| INT-6 | Same agent implements and verifies; no negative-case requirement on Verification Scripts | Workflow change to contract authorship |
| INT-7 | No cumulative regression re-run at chunk end | New required step in Phase 4 |
| INT-8 | No hashes across the DROP_HERE → project/ handoff | Depends on INT-3's filing log |
| GOV-1 through GOV-9 | Approval register, revert procedure, resume protocol, model-identity pinning, backup guidance, migration command, PROVISIONAL pipeline state | All new workflow/process additions |

## Possible v1.3.5 candidates

All three below share one constraint they were explicitly designed against: no Factory evolution
should increase operator (Human) burden unless evidence shows the added burden produces a
proportionally larger engineering benefit — not "would this help" but "does this help without
requiring the Human to do, remember, or decide anything new." All three are self-gated on
completing at least one more real project first, piloting one at a time on a single bounded chunk
before any Factory-wide adoption, and bringing evidence back to the factory designer before any
version bump — the same discipline already used for `materialize`, Frozen File multi-file sets,
and Doc Sync when each was new. None of the three should be implemented from this table alone
without that gate being satisfied.

**1. Cross-Project Precedent Retrieval.** Targets tacit organizational knowledge — this Factory
currently resets accumulated "why we chose X" / "what legacy decision constrains this" knowledge to
zero at every new project, unlike a human engineer who carries it across a career. Mechanism: a
new, permanent, cross-project file, `factory/precedent_ledger.md`, appended to automatically at the
end of every Factory Retrospective (already-mandatory per Constitution C49) — not new work, just
the natural output of a step that already happens. Each entry: what was decided, what the
underlying constraint or failure was, what generalizes beyond the one project it came from — a
lighter, more permissive bar than the Promotion Pipeline, since real tacit knowledge is often
useful without being a repeatable, evidence-gated rule. Read by the Architect at Session Start
alongside `constitution.md`/`dynamic_rules.md` — one more file already in the folder handed over,
not a new attachment step. Grounding: retrieval-augmented organizational memory (e.g. HippoRAG) and
autonomous-research pipelines that carry knowledge forward across runs, weighting older lessons
less than recent ones, are established published patterns for this. **Independent critique on
file:** as specified, unbounded growth conflicts with `ClaudeInitialization.md` §0's own
minimal-fixed-attachment design and the Promotion Pipeline's evidence-gated growth model — needs a
size cap or `SUPERSEDED`-style pruning, or should route through the existing Promotion Pipeline
instead of running as a new parallel one, before it's re-proposed. Cheap pilot: populate it
retroactively from RateLimiter's and TeamNotes' actual retrospectives, then check whether it
surfaces anything useful on the next real project's founding-artifacts pass. Evidence status:
genuinely new, unpiloted.

**2. Adversarial Pre-Decision Pass.** Targets structured opposition to a decision before it's
approved, as a narrower, reachable slice of adversarial/creative scrutiny — not genuine novelty,
which no process design reaches. Mechanism: a refinement of `ClaudeInitialization.md` §5c's
existing scenario-probes technique, not a new artifact or session. Before recording APPROVED at
Chunk Review, same session, the Architect explicitly constructs the single strongest case for FIX
PACKAGE instead, in writing, then argues against that specific case before deciding — differs from
the existing scenario probes (which generate failure *scenarios*) by requiring an explicit case for
outright *rejection* of the whole contract, argued to win, not just listing risks. Grounding:
Multi-Hypothesis Failure Attribution (divergent generation of distinct explanations, independent
scoring, deterministic routing to an intervention) is a published pattern for structured
self-opposition in autonomous systems, and is the direct model for this. **Honest limit stated
plainly:** this is the same session critiquing itself — research on weak-to-strong oversight and
judge/generator similarity bias is consistent that a model reviewing its own family of reasoning is
a weaker check than genuinely independent review; this narrows that gap, it does not close it. A
genuinely independent second-model reviewer would be the real version of that, but is not
zero-burden and is a separate proposal. **A caution that should shape any real spec, not just
whether it's adopted:** the MAST failure taxonomy (1,600+ annotated multi-agent LLM traces) finds
specification ambiguity — unclear completion conditions — is the largest single failure category,
and better base-model capability alone doesn't fix it; a real version of this needs an explicit,
contract-like spec of what "the strongest case for FIX PACKAGE" must actually contain and an
unambiguous point at which the pass is complete — a vague "also argue against yourself" instruction
is exactly the shape of addition that fails silently. Evidence status: genuinely new, unpiloted.
**v1.4.0 note: effectively superseded for now.** GLOF's failure was exactly this pattern —
same-session judgement missing its own methodology flaws — but D-011's MAR phase addresses it with
the stronger mechanism this proposal's own honest limit names as "the real version of that": review
by a session or model outside the Architect's own family, not the same session arguing with itself.
Re-evaluate this narrower proposal only if MAR proves impractical to staff on a real project.

**3. Automated Risk-Surface Scan.** Targets liability-relevant risk surfacing (security, compliance,
secrets, PII) — reduces the chance a liability-relevant mistake goes unnoticed; does not create
moral agency or legal accountability, which stay a Human responsibility. Mechanism: a new Contract
Specification field, `Risk Surface Scan Required`, set true for any contract whose Outputs include
dependencies, secrets-adjacent code paths, or PII handling. When true, Gemini's existing Phase 2/3
(not a new phase) runs dependency/license scanning, secrets detection, and a static check for
common insecure patterns as part of its own verification, reported the same way every other
Verification Script already is. Gatekeeper gets a new check category alongside Frozen File and
Report Validation: presence and pass/fail of the declared scan, nothing judgmental — matching
Gatekeeper's existing "facts only, never 'code looks clean'" philosophy exactly. Grounding: this is
mature, widely-deployed practice, not speculative — SCA/secrets/static-analysis as automated
CI gates, some tools now mapping findings to specific regulatory controls (SOC 2, HIPAA, PCI-DSS)
for evidence purposes. TeamNotes' own contract reports already produced partial evidence of this
pattern naturally (`npm install`'s vulnerability-count output appearing in a report) without
anything in the Contract Specification requiring or standardizing it. Converges independently with
GOV-4 above and `gatekeeper_spec.md`'s own "planned" Constitution Rule Validation section, which
already names C24 secrets-in-repo scanning as the natural next Gatekeeper contract — this is a
concrete design for something the Factory has already declared it wants to build, not new scope.
Cheapest of the three to pilot: tooling categories are mature and off-the-shelf, not novel design.
Evidence status: genuinely new, unpiloted.

**Explicitly not addressed by any of the three above, and no version of them would close these:**
team dynamics/mentoring/psychological safety (requires sustained human relationship and social
presence a role-bound AI session structurally doesn't have); legal liability/accountability (§3
reduces the chance of missing something, it cannot make anyone *accountable*, which stays a Human,
not automation, responsibility); genuine first-principles novelty (§2 improves scrutiny of
decisions already made, it does not grant the capacity to invent something with no precedent).
Treat this as load-bearing — claiming any of the three above "addresses" one of these would be
exactly the kind of confident overclaim C01/C02 exist to prevent.

---

```
Rule ID

D-032

Category

Verification

Status

PROPOSED

Promoted From

Not yet promoted — implemented directly at Human direction; see the Third-party review disposition
note below and CHANGELOG.md's dated amendment to the v1.4.2 entry

Evidence

D-029/D-030/D-031 built verify-contract, lint-contract, and recompute/stamp-report as real,
working, independently-invoked mechanisms. A second-round independent review of the resulting
v1.4.2 release, checked directly against `gemini_spec.md`'s actual Phase 3 text rather than
accepted on the review's own framing, confirmed a distinct gap: none of the four are mandatory.
`gemini_spec.md`'s Phase 3 Step 2 still only instructs `gatekeeper.py check`; `verify-contract`,
`lint-contract`, `recompute`, and `stamp-report` are not named anywhere in `gemini_spec.md`,
`factory_spec.md`, or `ClaudeInitialization.md`'s operative instructions. A contract can therefore
reach `COMPLETE` having built strong verification machinery that the ordinary workflow never
actually invokes — confirmed directly, not merely asserted by the review.

Description

For a contract whose `scientific_claim_tier` (existing v1.4.0 field) is `T-COMP` or `T-CAUSAL`,
`gatekeeper.py check` mechanically requires all of: the contract's Required Verification Commands
(D-033) present in the report's own declared set; `verify-contract`'s re-execution of every
declared command passing; `lint-contract` passing; a well-formed `## Recompute Declaration` block
present and passing (unlike the standalone `recompute` subcommand, a *missing* block is itself a
hard FAIL under this gate — the omission D-031's own Notes section already flagged as silently
allowed); and at least one intact Gatekeeper Verification Stamp present on the report. Any one
failing sets exit 17, reported by name. A T-DESC contract, or a contract with no declared tier, is
unaffected — this rule narrows scope deliberately (Scientific Claim Tier already exists precisely
to distinguish "makes a quantitative/comparative claim" from routine engineering work; reusing it
avoids inventing a second, redundant "High-risk" taxonomy the review's own proposal would have
introduced).

Reason

Constitution C01 already forbids reporting a check as passed when it wasn't actually run; this rule
is deterministic enforcement of that principle at the one point where it had a real, confirmed gap
— a tiered contract could read COMPLETE without the machinery built specifically to protect tiered
claims ever running. Not a new principle, matching the same relationship D-028 through D-031 have
to C01/C11. The narrower T-COMP/T-CAUSAL-only scope (rather than gating every contract) mirrors how
the existing Adversarial Verification for Concurrency rule (v1.3.0) already gates only `High` risk
tier contracts, not all of them — mandatory machinery scoped to where the evidence bar is actually
higher, not applied uniformly regardless of a contract's actual claim strength.

Implementation

`gatekeeper.py check --manifest {{path}} --contract {{id}} --reports {{path}}` — new
`_run_mandatory_gate` helper, invoked from `cmd_check` when the loaded manifest contract's
`scientific_claim_tier` is `T-COMP`/`T-CAUSAL` (exit 17 on failure). Reuses the exact underlying
functions `verify-contract`/`lint-contract`/`recompute`/stamp-checking already call
(`_extract_declared_commands`, `_run_subprocess`, `_scan_swallowed_exceptions`,
`_scan_fabricated_statistical_input`, `_check_recompute_block`, `_find_stamps`,
`_verify_stamp_integrity`) rather than a second, parallel implementation (C46) — this rule adds
gating logic on top of D-029/D-030/D-031's existing mechanisms, not new detection logic of its own.
`check` never appends a stamp itself; `stamp-report` remains the separate, explicit step that
produces one.

Verification

Automatic. Unit-tested: T-DESC and untiered contracts confirmed to skip the gate entirely;
T-COMP/T-CAUSAL confirmed to hard-fail on each of the five sub-checks individually (no report, no
declared Verification commands, no Recompute Declaration, no stamp) and to pass when all five are
genuinely satisfied (stamped via the real `stamp-report` code path, not a hand-authored stamp) —
see `factory/tests/test_gatekeeper_v1_4_2_mandatory_gate.py`.

Date Added

2026-08-15

Projects

0 (built at Human direction from a second-round review's confirmed finding, not from a second
independent incident of a tiered contract actually reaching COMPLETE unverified — the BPFeat
project this rule was filed alongside had not yet run a T-COMP/T-CAUSAL contract through the
original, pre-amendment v1.4.2 workflow)

Notes

Honesty about scope: this gate is exactly as strong as the four mechanisms it makes mandatory, no
stronger — it does not add new detection capability, only removes the option of a tiered contract
completing without exercising machinery that already existed. Everything D-028 through D-031's own
Notes sections disclosed as a limit of the underlying check (co-occurrence not data-flow proof;
"exited 0" not "was the right command," now narrowed by D-033 specifically for tiered contracts;
two independent programs agreeing not proof either is correct; a stamp proving non-tampering, not
proving initial correctness) still applies here unchanged.
```

```
Rule ID

D-033

Category

Contract Specification

Status

PROPOSED

Promoted From

Not yet promoted — implemented directly at Human direction; see the Third-party review disposition
note below and CHANGELOG.md's dated amendment to the v1.4.2 entry

Evidence

`gatekeeper_spec.md`'s own Implementation Status section disclosed this gap plainly at the original
v1.4.2 release, unprompted by the review: "`verify-contract` proves the declared command exited 0,
not that it was the *required* command." The second-round review independently reached the same
conclusion by construction — a report could declare `python3 -c "print('PASS')"` under
`## Verification` and `verify-contract` would re-execute it, get exit 0, and accept it, regardless
of whether that bore any relationship to what the contract actually needed verified.

Description

A T-COMP or T-CAUSAL contract declares, at Chunk Planning time, a `Required Verification Commands`
field — the exact command(s) that constitute its required verification, frozen then like every
other Frozen File field, not left open for the contract report to invent later:

```
Required Verification Commands:
  - {{exact shell command}}
  - {{exact shell command}}
  ...
```

`gatekeeper.py check`'s Mandatory Mechanical Gate (D-032) cross-checks this frozen list against the
report's own declared `## Verification` commands; any Required Verification Command absent from
the report's declared set is a hard FAIL under the gate, independent of whether `verify-contract`
found every command the report *did* declare to pass. A report may declare additional commands
beyond the required set — only a missing required one fails this sub-check.

Reason

This is the direct, narrow fix for the one gap `verify-contract` explicitly disclosed rather than
concealed at its own release: re-execution proves *a* declared command ran and passed, never that
it was *the* command the contract needed. Freezing the required command at contract-generation
time, the same way every other Verification Scripts/frozen_files field already works, closes this
without inventing new machinery — Claude commits to the required command before implementation
begins, exactly as it already commits to frozen files and verification scripts, so there is nothing
new here except one more field checked the same way.

Implementation

New `required_verification_commands` field read directly from `execution_manifest.yaml`'s per-
contract entry, mirroring how `risk_tier`/`scientific_claim_tier` are already read. Checked inside
`_run_mandatory_gate` (D-032) — a genuinely new command is not required, since this is a
cross-check against data the manifest already carries once declared.

Verification

Automatic, as part of D-032's gate. Unit-tested: a report substituting a different, trivially-
passing command for a declared Required Verification Command is confirmed to still fail the gate
even though `verify-contract`'s own re-execution of the substituted command would pass; a report
correctly declaring the required command is confirmed to pass; a T-COMP/T-CAUSAL contract declaring
no Required Verification Commands at all is confirmed to warn (disclosed gap) rather than silently
pass with no signal — see `factory/tests/test_gatekeeper_v1_4_2_mandatory_gate.py`.

Date Added

2026-08-15

Projects

0 (same basis as D-032 — filed from the review's confirmed construction, not a second independent
incident)

Notes

Deliberately not framed as a new "High-risk" tier or taxonomy, despite the review's proposal using
that language — Scientific Claim Tier already exists and already means exactly "makes a
quantitative/comparative claim needing stronger evidence" (`factory_spec.md`'s T-DESC/T-COMP/
T-CAUSAL table, v1.4.0). Introducing a second, parallel "High-risk" concept alongside it would be
the kind of redundant terminology this file's own disposition discipline exists to catch (see the
table above: several first-review items were dispositioned as "already shipped" or "not a new
principle" for exactly this reason) — reusing the existing tier was a deliberate, considered choice
made before implementation began, not an oversight caught afterward.
```

---

## Third-party review disposition, round two (2026-08-15)

A 20-item gap-analysis document was submitted for a proposed "v1.4.2," framed around one specific
example: a Gemini-implemented script computing a bootstrap confidence interval, verified only by
report-artifact consistency rather than independent recomputation. That example was initially
treated as illustrative/hypothetical, since no CHANGELOG or Dynamic Rule entry documented it. It
is not hypothetical — see D-028, above, filed from direct inspection of the real script, byte-for-
byte reproduction against the real artifact, and confirmation the fabricated values reached
`sentinel_gl_manuscript.md`'s abstract and RQ3 result. Recorded here rather than silently
corrected, per the same standard applied to this Architect's own prior claims elsewhere in this
file (see v1.3.3's Notes) — the earlier "hypothetical" characterization was wrong and is not edited
away (C30).

Per the same audit discipline used for prior third-party review documents (v1.3.4's cross-model
audit; v1.4.0's second-model gap analysis; v1.4.1's "CHECK 5" review — see those CHANGELOG entries),
every claim was checked against the actual files rather than accepted on the strength of the
document's own framing. Most of the first document's 20 items, checked individually:

| Item(s) | Disposition |
|---|---|
| "Never let the same agent be producer and sole verifier"; Verification-of-Verification; `recompute`; Reference Oracle; Claim→Evidence→Computation→Verification chain | **Not a new principle.** Constitution C11 (Independent Validation For Critical Results) already states this, pre-dating v1.4.0. D-028 is deterministic enforcement of a narrow, mechanically-detectable instance of it — the same relationship D-024/D-025 have to C01/C08, not a new rule of its own kind. |
| Strengthen Scientific Claim Tiers | **Already shipped, v1.4.0**, and stricter than proposed: `factory_spec.md`'s T-DESC/T-COMP/T-CAUSAL table already requires ≥2 baselines plus a computed significance test for T-COMP, and adversarial testing plus ≥3 baselines plus a declared Stop Condition for T-CAUSAL. |
| Independent adversarial review for research projects | **Already shipped, v1.4.0.** This is MAR — gates 4–7 already require a reviewer outside the Architect's own model family for venue-targeted projects. |
| "Smarter" Reality Gate (ranges + evidence source + severity, not rigid thresholds) | **Already specified this way.** `venue_requirements_TEMPLATE.md`'s Expected Data Properties section already requires a domain-grounded citation (a/b/c basis) for every threshold and already names "suspiciously better than expected" as its own red-flag category. Not yet `gatekeeper.py`-implemented — already disclosed as such. |
| Allowed File Validation; cumulative regression; negative-case testing requirement; model-identity pinning | **Already tracked** — INT-5, INT-7, INT-6, and a GOV row respectively, in the table above, filed at the v1.3.4 cross-model audit over a year of releases before this document. |
| Scientific Result Release Gate (layered PASS) | Descriptive repackaging of MAR + Reality Gate + `evidence-check` + `release-check` + D-028, not a new gate. |
| Numeric maturity scores (e.g. "9.4–9.6/10") | Not evidence. No stated rubric, no independent scorer, not reproducible. |

Two items from the first document were genuinely non-redundant and not yet evidenced by anything
beyond the document's own reasoning — filed as Candidate Observations, not implemented, per
C42/C45/EP-005:

**1. Statistical-unit / independent-N metadata.** Targets pseudoreplication hidden behind large
window counts. Mechanism: a `statistical_unit`/`independent_n`/`observational_n` triple alongside
any reported metric. **Honest limit:** detecting *mis*-declared statistical units mechanically is
exactly as hard as detecting any other false claim about methodology; this only helps once the unit
is declared. Evidence status: genuinely new, unpiloted, zero project occurrences.

**2. Unproven Assumption Register.** **Independent critique on file:** as proposed, this is the
Architect's own judgement being *recorded*, not *verified* — "Documentation" tier, not "Deterministic
Enforcement" tier, on this file's own Factory Principle maturity ladder. `venue_requirements.md`'s
Pre-Registered Falsification Criteria table and C53's Stop Condition already cover the highest-value
subset with a real enforcement path this proposal's general version lacks. Evidence status:
genuinely new, unpiloted, zero project occurrences.

A second document arrived after D-028 was filed, auditing v1.4.1 specifically for four remaining
gaps: verification scripts are re-run by nobody but Gemini itself; fallback/mock/swallowed-exception
patterns are not linted as a general contract gate; `evidence-check` validates artifact-report
consistency but not the computation that produced the artifact; and contract reports are entirely
AI-authored with no machine-verified section. Unlike the first document, every one of these four
claims checks out directly against the real v1.4.1 `gatekeeper_spec.md` Implementation Status this
Architect had already read and written — they are not hypothetical, redundant, or already-tracked;
D-028 is itself a concrete instance of the third gap. Implemented directly rather than filed as
Candidate Observations: `verify-contract`, `lint-contract`, `recompute`, and `stamp-report`/
`verify-stamps` (below). This is a deliberate departure from this file's usual evidence bar for a
Minor-shaped change (C45: a completed project, not a review document) — the departure is disclosed
here rather than silently made, for the same reason a Key Fact block that fails to parse is reported
rather than silently skipped: a standard applied only when convenient is not a standard. The
Human's basis for directing implementation despite this was explicit: multi-party confirmation (the
Human, both review documents, and the GLOF Implementation Engineer session) that the underlying
gap is real, plus D-028 as this Architect's own independent, reproduced confirmation — not merely
deference to instruction. See CHANGELOG.md v1.4.2's Notes for the full disposition, including what
was deliberately built differently from either document's literal proposal and why (report
splitting unifies barriers #1 and #4 into one mechanism; frozen-verification-machinery reuses
existing snapshot infrastructure rather than new code; `lint-contract`'s swallowed-exception check
is scoped to what static AST analysis can actually prove, disclosed as such, rather than claiming
general fallback detection no static analysis can honestly deliver).

A third round arrived immediately after the original v1.4.2 release, reviewing it directly (not a
generic proposal) and confirming, by reading `gemini_spec.md`'s actual Phase 3 text rather than
trusting the release's own framing, that D-029 through D-031's four mechanisms were real and
working but not mandatory — the ordinary Gemini workflow could complete a contract without ever
invoking any of them. This exact gap was already self-disclosed in `gatekeeper_spec.md`'s own
Implementation Status section at the time ("neither command yet verifies a script's declared
command matches what `gemini_spec.md` actually required it to run"), so the review's core finding
is independently corroborated by this file's own prior honesty about its limits, not merely by the
review document's assertion. D-032 (Mandatory Mechanical Gate) and D-033 (Required Verification
Commands) close it: `check` now enforces all four mechanisms for T-COMP/T-CAUSAL contracts
specifically, rather than leaving them permanently opt-in. The review also proposed a "High-risk
contract" concept as the gating criterion; this was not adopted as written — Scientific Claim Tier
already exists and already is the precise, evidence-backed concept for "needs stronger evidence,"
and introducing a second, redundant taxonomy alongside it would itself be exactly the kind of
duplication this disposition discipline exists to catch (see the table above). Kept at v1.4.2
rather than bumped to v1.4.3, at explicit Human direction, despite this file's own C50 versioning
policy defaulting a workflow-enforcement change of this shape to a version bump — recorded here,
and in CHANGELOG.md and `bootstrap_manifest.yaml`'s dated amendment, as a disclosed departure
rather than a silent one, for the same reason the v1.4.2-proper departure from the usual evidence
bar (above) was disclosed rather than absorbed quietly into the version number it would otherwise
have carried.

---

```
Rule ID

D-034

Category

Scientific Validity

Status

PROPOSED

Promoted From

Not yet promoted — implemented directly at Human direction as part of the v1.4.2 → v2.2.0
redesign; see CHANGELOG.md's v2.2.0 entry for the full account of that redesign

Evidence

Every scientific-rigor mechanism this Factory has — the T-COMP/T-CAUSAL baseline/significance/
adversarial-test requirements (v1.4.0), the Mandatory Mechanical Gate (D-032/D-033) — is keyed off
a contract's own self-declared `scientific_claim_tier` field. Nothing before v2.2.0 checked whether
that self-declaration was itself too low. This is not hypothetical: `project/chunks/chunk06/
contracts/C06-03_contract.md` in the uploaded `factory_v1.5.0` TDLCR test project — "Pre-Registered
Hypothesis Evaluator & Result Registry Compiler," whose own Implementation Instructions name a
Wilcoxon significance test, a Cliff's delta effect size, and SUPPORTED/FALSIFIED/INCONCLUSIVE
verdicts feeding `project/result_registry.json` for IEEE publication — declares
`Scientific Claim Tier: NONE`, with its Verification Scripts entry only confirming the module
imports cleanly. Under the original v1.4.2 workflow, nothing mechanical would have caught that
before Chunk Review; it would have depended entirely on the Architect noticing its own
mis-declaration. Read directly from the uploaded artifact, not reconstructed from a description of
it — see `factory/tests/test_gatekeeper_v2_2_0.py`'s `REAL_C06_03_EXCERPT` fixture, a verbatim
excerpt of the fields this rule's inference reads.

Description

`gatekeeper.py tier-check` (and, wired into it, `check`) mechanically infers a *minimum*
`scientific_claim_tier` from a contract's own Objective/Context/Implementation Instructions/Outputs
text, using two signal strengths: a STRONG match (named statistical tests and effect sizes —
Wilcoxon, Mann-Whitney, DeLong, Cliff's delta, Cohen's d —, explicit p-value/confidence-interval
notation, "outperforms," pre-registered SUPPORTED/FALSIFIED language) infers `T-COMP`, or `T-CAUSAL`
for a distinct, separately-matched set of robustness/causal/ablation language; a WEAK match alone
(a bare metric name — F1, AUC, accuracy — with no comparison/test-name co-occurrence) infers
`T-DESC`, since reporting a metric value is itself an observational claim under factory_spec.md's
own table; no match at all infers `NONE`, since ordinary plumbing (a data loader, a CRUD utility)
correctly declares no tier at all. A contract's *declared* tier may exceed this inferred minimum
freely — the check only fires when declared is strictly weaker than inferred. `check` runs this
unconditionally (not only when a tier is already declared), specifically because its job is to
catch the declaration itself being wrong.

Reason

Constitution C51 ("a project is complete when its methodology would survive adversarial peer
review, not when all contracts pass") and C05 ("Gatekeeper independently infers a minimum
[assurance/tier], never trusts a self-declared one downward") — see this Constitution's new C55.
Every other T-COMP/T-CAUSAL mechanism in this Factory (baselines, significance testing, the
Mandatory Mechanical Gate) is only as strong as the tier declaration that triggers it; a floor
under that declaration is a precondition for all of them, not an alternative to any of them.

Implementation

`gatekeeper.py tier-check --contract {{id}}` (standalone) and `check --contract {{id}} --manifest
{{path}}` (wired in unconditionally, alongside — not replacing — the existing Mandatory Mechanical
Gate). New `_infer_minimum_scientific_claim_tier`, `_TCOMP_STRONG_RE`, `_TCAUSAL_STRONG_RE`,
`_TCOMP_WEAK_RE`. Exit 18 on a hard finding (declared tier weaker than inferred minimum). Reuses
`_find_contract_file` (unchanged since v1.3.0) to locate the contract's own text — this rule adds a
new check, not a new way of finding what to check.

Verification

Automatic. Unit-tested against the real `C06-03_contract.md` excerpt (confirmed to infer `T-COMP`
and hard-fail against its actual declared `NONE`), against a benign data-loader contract (confirmed
to infer `NONE` and not fail), against a bare-metric-only contract (confirmed to infer `T-DESC`, not
`T-COMP`), and against explicit causal/robustness language (confirmed to infer `T-CAUSAL`) — see
`factory/tests/test_gatekeeper_v2_2_0.py`.

Date Added

2026-08-23

Projects

0 (built at Human direction from a real artifact examined retroactively — the uploaded TDLCR
`factory_v1.5.0` test project — not from a project run under this rule itself, since the rule did
not exist yet when that project ran)

Notes

Heuristic, not semantic understanding, and disclosed as such every time it runs: matching a
STRONG-signal keyword correlates with a comparative/statistical claim, it does not read the
contract's meaning. This will false-positive (a contract implementing a generic significance-
testing *utility*, never itself making a claim, may still match) and false-negative (a claim
phrased with no matched keyword at all). Every finding names the exact matched text so a
human/Architect can judge context quickly, per C39 — a false positive is resolved by re-declaring
the tier correctly or noting in the contract why the match doesn't apply, not by the check
silently standing down. This is a floor under self-declaration, not a substitute for the
Architect's own judgment at Chunk Planning or for Chunk Review's adversarial reading of the actual
artifact — see this Constitution's new C55 and the Chunk Review section's Required Review
Questions cross-reference to `domain_checklists.md`.
```

```
Rule ID

D-035

Category

Scientific Validity

Status

PROPOSED

Promoted From

Not yet promoted — see D-034's entry; filed alongside it as part of the same v2.2.0 mechanism
(`tier-check`), per C46 (one command, several related checks) rather than as a separate command

Evidence

Distinct from this Factory's own first-hand incident trail (the GLOF/BPFeat evidence D-022 through
D-031 are grounded in): this rule's motivating pattern — a contract's Objective describing
*building* a benchmark/evaluation mechanism being later treated as though the benchmark had been
*run* — is drawn from the Design Rationale document accompanying the uploaded `factory_v2.1.0`
archive, which itself attributes the pattern to a v1.5-generation project's adversarial audit. Cited
here as secondary evidence, honestly distinguished from a first-hand Factory incident, per this
file's own citation discipline (see the Third-party review disposition note above, which draws the
same distinction for its source).

Description

WARNING-only (never a hard failure on its own): within `tier-check`'s output, a contract whose
Objective opens with an implementation verb ("Implement," "Build," "Write," "Create," "Add") and
whose text also matches a STRONG `T-COMP`/`T-CAUSAL` signal (see D-034) is flagged for a
human/Architect second look at whether this specific contract actually executes/measures the claim
it describes, or only builds machinery a later contract will use to do so.

Reason

Same root cause as D-034 (a claim hiding behind language that reads as "just infrastructure"), but a
distinct enough shape — verb-tense/operation-class confusion rather than tier under-declaration — to
warrant its own rule number even sharing D-034's command, matching how D-022/D-023's related-but-
distinct acquisition patterns were both given their own numbers under one `acquisition-audit`
command (D-028's own Notes section).

Implementation

`gatekeeper.py tier-check` (bundled) — new `_scan_operation_class_conflation`,
`_IMPLEMENTATION_VERB_RE`. WARNING-level finding, printed under `tier-check`'s own
"[Operation-Class Conflation]" section; does not affect exit code.

Verification

Automatic. Unit-tested: an Objective combining an implementation verb with comparative/
significance language is confirmed to produce a finding; an implementation verb alone (no
comparative language) is confirmed not to — see `factory/tests/test_gatekeeper_v2_2_0.py`.

Date Added

2026-08-23

Projects

0

Notes

Genuinely more ambiguous than D-034's tier check — plenty of contracts legitimately implement one
stage of a multi-contract pipeline whose *later* contract makes the actual claim, and this rule
cannot and does not distinguish that legitimate case from the failure pattern it's named for. Kept
WARNING-only for exactly this reason; promoting it to a hard failure would require a much more
specific signal than this file currently has evidence for.
```

```
Rule ID

D-036

Category

Scientific Validity

Status

PROPOSED

Promoted From

Not yet promoted — see D-034's entry; same provenance and citation posture as D-035

Evidence

Secondary evidence, same source and same honest-citation posture as D-035: the `factory_v2.1.0`
Design Rationale document's failure table names two recurring statistical-protocol errors —
metric/pairing/effect-size incompatibility, and treating a non-significant result as evidence of
equivalence without a pre-declared equivalence margin. Neither is drawn from a first-hand Factory
incident; both are named here as a floor worth having regardless of provenance, disclosed as such.

Description

WARNING-only, two checks, bundled into `tier-check`: (1) text containing non-significance language
("not significant," "p > 0.05") together with equivalence language ("equivalent") but no declared
equivalence margin or TOST/non-inferiority test is flagged — absence of a significant difference is
not evidence of equivalence without a pre-declared margin; (2) text naming a specific statistical
test/effect size (matching D-034's STRONG signal set) with no paired/unpaired/independent-samples
language nearby is flagged — a test and effect size can each be individually well-known and still be
an incompatible pairing for how the samples were actually collected.

Reason

Same category as D-024/D-025 (evidence-check's verdict/criterion consistency) — a report can be
internally well-formed and still rest on a statistically invalid combination that no format-level
check would catch. String/pattern co-occurrence only, exactly D-028's evidentiary posture: flags a
combination worth a human looking at, does not itself adjudicate the statistics.

Implementation

`gatekeeper.py tier-check` (bundled, also runnable by pointing `acquisition-audit`/`release-certify`
at the same text via `_scan_statistical_protocol_language`) — new `_NONSIG_RE`,
`_EQUIVALENCE_CLAIM_RE`, `_EQUIVALENCE_MARGIN_RE`, `_PAIRING_LANGUAGE_RE`. WARNING-level only;
does not affect exit code.

Verification

Automatic. Unit-tested: non-significance + equivalence language with no margin is confirmed to
flag; the same with a declared margin/TOST is confirmed not to; a named test/effect size with no
pairing language is confirmed to flag; the same with pairing language declared is confirmed not to
— see `factory/tests/test_gatekeeper_v2_2_0.py`.

Date Added

2026-08-23

Projects

0

Notes

This does not type-check statistics in any general sense — it catches two specific, named
co-occurrence patterns and nothing else. A statistically invalid combination phrased without any
of the matched vocabulary passes silently. Treat a clean result from this check as "no known-bad
pattern matched," not as "the statistics are valid."
```

```
Rule ID

D-037

Category

Scientific Validity

Status

PROPOSED

Promoted From

Not yet promoted — see D-034's entry; same provenance and citation posture as D-035/D-036

Evidence

Secondary evidence, same source and posture as D-035/D-036: the `factory_v2.1.0` Design Rationale
document's failure table names several instances of a named mathematical/statistical operator not
actually meaning what its name claims (a Laplacian implemented as an adjacency matrix; a witness
complex not actually using witness points; a persistent-homology filtration violating monotonicity)
— caught, per that document's own account, only by adversarial review reading the implementation
against the mathematical definition, never by an I/O-shape test. `domain_checklists.md`'s "Required
review questions" sections operationalize the same source's review-question content directly.

Description

WARNING-only: for a contract whose text names a recognized operator (Laplacian, adjacency matrix,
witness complex, filtration, boundary operator, persistent homology, simplicial complex, batching
semantics, permutation invariance), checks whether the contract's Verification Scripts / declared
verification commands contain a recognizable semantic-test naming marker (`semantic_*`,
`operator_*`, `known_answer_*`, `metamorphic_*`, `invariance_test*`, `monotonic*`, or a test name
referencing the operator directly). Presence-only — cannot and does not check whether such a test,
if present, actually establishes the claimed property.

Reason

An I/O-shape test (correct array dimensions, no exceptions raised) can pass while the named
mathematical object is still wrong. This is the same class of gap D-032's Mandatory Mechanical Gate
exists to close for verification commands generally, narrowed here to a specific, recurring family
of operator-identity errors named by the cited source.

Implementation

`gatekeeper.py tier-check` (bundled) — new `_scan_semantic_operator_test_presence`,
`_NAMED_OPERATOR_RE`, `_SEMANTIC_TEST_MARKER_RE`. WARNING-level only; does not affect exit code.
Reads the contract text plus, if `--reports` is given, the paired report's declared verification
text as well.

Verification

Automatic. Unit-tested: a contract naming an operator with no matching test-name marker in its
verification text is confirmed to flag; the same with a matching marker present is confirmed not
to; a contract naming no operator at all is confirmed not to flag regardless of its verification
text — see `factory/tests/test_gatekeeper_v2_2_0.py`.

Date Added

2026-08-23

Projects

0

Notes

A naming-convention check, nothing more — it trusts that a script named `semantic_test_laplacian.py`
actually tests the Laplacian's mathematical properties rather than merely being named as if it did.
That trust boundary is the same one D-032's Required Verification Commands already accepts for
verification commands generally (Notes section: "'exited 0,' not 'was the right command'"). The
real work of getting the operator right remains Implementor/Architect judgment, guided by
`domain_checklists.md` — this check only prevents that work from being skipped silently.
```

```
Rule ID

D-038

Category

Governance

Status

PROPOSED

Promoted From

Not yet promoted — implemented directly at Human direction as part of the v1.4.2 → v2.2.0
redesign; see CHANGELOG.md's v2.2.0 entry

Evidence

`release-check` (v1.4.0) scans one release-bound artifact; nothing before v2.2.0 aggregated across
an entire project's chunks and stated, in one place and one artifact, whether the whole project is
actually submission-ready. Absent that, "the project passed Gatekeeper" (a per-chunk/per-contract
state) and "the project is ready to submit" (a project-wide state) have no crisp boundary between
them in this Factory's own documents — exactly the ambiguity Constitution C51 already names in
prose ("a project is not complete when all contracts pass") without, until now, a corresponding
mechanical artifact.

Description

`gatekeeper.py release-certify --chunks-dir project/chunks [--manuscript ... --key-facts ...
--scripts ...]` walks every `contract_report.md` under the given chunks directory and: confirms
Final Status is COMPLETE for each (a FLAGGED or BLOCKED status anywhere blocks certification);
re-runs `evidence-check`'s and `recompute`'s logic against every report carrying the relevant
declared block; re-runs `tier-check`'s inference against every contract whose file is locatable;
and, if given, runs `acquisition-audit` against `--scripts` and `release-check`'s local-path/
key-fact scan against `--manuscript`. Writes `project/RELEASE_CERTIFICATION.md` unconditionally
(CERTIFIED or NOT CERTIFIED, both a useful state to have on record), naming exactly which
categories were actually checked (an uninvoked category — no `--manuscript` given, say — is absent
from that list, not silently treated as passed). Exits 19 on NOT CERTIFIED.

Reason

Constitution C51/C01 — a certificate should say only what was actually checked, never more, and
"CERTIFIED" should be a name this Factory's own tooling reserves for one specific, inspectable
artifact rather than a word any report or chunk summary can claim for itself informally.

Implementation

`gatekeeper.py release-certify`. New `cmd_release_certify` — reuses `_parse_verdict_block`,
`_check_verdict_consistency`, `_check_criterion_consistency`, `_check_degenerate_metrics`,
`_check_recompute_block`, `_infer_minimum_scientific_claim_tier`, `_scan_acquisition_functions`,
`_scan_fabricated_statistical_input`, `_scan_acquisition_text`, `_scan_local_paths`,
`_check_key_fact_consistency`, and `parse_contract_status` (all pre-existing or added under
D-034) rather than a second, parallel implementation of any of them (C46) — this rule adds
aggregation and a certificate artifact, not new detection logic.

Verification

Automatic. Unit-tested: zero contract reports found is confirmed NOT CERTIFIED; all-COMPLETE
benign contracts are confirmed CERTIFIED; a single FLAGGED contract among otherwise-complete ones
is confirmed to block certification; a single under-tiered contract (D-034) is confirmed to block
certification; `project/RELEASE_CERTIFICATION.md` is confirmed written in both the CERTIFIED and
NOT CERTIFIED cases — see `factory/tests/test_gatekeeper_v2_2_0.py`.

Date Added

2026-08-23

Projects

0

Notes

Deliberately not a new registry or schema — it re-runs existing checks against existing artifacts
and writes one Markdown file. It certifies only the categories it actually ran, which the
certificate itself lists; scientific truth, publication acceptance, and anything no listed
category examined are outside what this artifact claims, and its own "Proof boundaries" section
says so explicitly rather than leaving that inference to the reader.
```

---

# Factory Principle

The Factory evolves through evidence.

# Dynamic Rules Added in v2.3.0

Disposition of a third-party review round: four independent completed-project
field reports (Sentinel-GL, KLStream, the AML/collusion-ring project,
CoreMesh), reviewed together, plus two defects found directly by checking
those reports' claims against gatekeeper.py's and this Factory's own
documents' actual text (same discipline as every prior round -- see this
file's earlier disposition notes). Every rule below cites which report(s)
evidence it. Status reflects the same bar used elsewhere in this file:
ACTIVE where the evidence is genuinely cross-project and the fix is a
narrow, low-risk, already-tested mechanical change; PROPOSED where the
evidence is real but from a single project, or the mechanism is newer and
has not yet been exercised on a real chunk.

### D-039 (Category: V, Status: ACTIVE)
**Description:** A contract report's verification commands may be declared
in any of three formats (the original bullet/bold/backtick form, a legacy
literal `Command:` block, or a fenced `verification:` YAML block); if a
contract's manifest declares verification_scripts (or the report's own text
contains a Verification-shaped section label) and zero commands are
extracted from all three, that is now a hard failure, not a silent pass.
**Evidence:** Sentinel-GL (C01-01 through C01-08: aggregate verify-contract
found zero declared commands across eight reports that all genuinely
contained verification commands and real output, because they used the
`Command:` block style); KLStream (same shape, C10-01); CoreMesh (report
schema drift produced the same downstream symptom).
**Reason:** "Zero declared commands" was previously indistinguishable
between "nothing was ever meant to be checked here" (fine) and "something
was declared but didn't parse" (a real, undetected gap in verification).
**Implementation:** `_extract_declared_commands` (widened parser),
`_check_verification_presence` (fail-loud helper), wired into
`verify-contract` and `contract-preflight`/`begin`/`finalize`.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py`.
**Date Added:** v2.3.0. **Projects:** Sentinel-GL, KLStream, CoreMesh.

### D-040 (Category: G, Status: ACTIVE)
**Description:** `contract-preflight` reconciles a contract's Allowed Files
against what its own verification commands (and any `--acquisition-scripts`
glob) would actually touch, before implementation begins. A glob match
outside `allowed_files ∪ frozen_files` is a hard FAIL (exit 3) unless
`--readonly-verification` confirms the command only reads. Also flags an
Allowed/Frozen overlap and a missing `dependencies` entry.
**Evidence:** Sentinel-GL C01-03 (a wildcard `acquisition-audit --scripts`
argument matched more legacy modules than the contract's allowed_files
permitted modifying, discovered mid-contract instead of at intake).
**Reason:** Verification reach and modification scope were two valid
controls that had never been reconciled against each other.
**Implementation:** `cmd_contract_preflight`, `_expand_glob_paths`.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py`.
**Date Added:** v2.3.0. **Projects:** Sentinel-GL.

### D-041 (Category: W/G, Status: ACTIVE)
**Description:** `begin`/`finalize` collapse the snapshot/check/telemetry/
decision/commit ceremony into two lifecycle commands. `begin` captures a
scoped repository baseline (git status at contract start); `finalize`
re-runs `check` for real against the report's current content and writes a
completion receipt (contract, report SHA-256, outer/nested HEAD) only on
an actual pass, replacing the blanket `--allow-dirty` bypass with a
categorized delta (pre-existing / this-contract / unexpected) for any
contract started with `begin`. `project/` is always excluded from
"unexpected," by construction (see C60), independent of a given
environment's `.gitignore` state.
**Evidence:** KLStream C10-01 (a false `contract_complete` telemetry event
and COMPLETE-status report both existed while `check`'s Report Validation
would have failed, had it been re-run at that moment); Sentinel-GL, AML
project, CoreMesh (all report `--allow-dirty` as an always-required,
therefore-uninformative blanket bypass).
**Reason:** A report's own Final Status line was never, by itself,
sufficient reason to trust a chunk was complete -- see C61.
**Implementation:** `cmd_begin`, `cmd_finalize`, `_capture_baseline`,
`_scoped_dirty_delta`, completion receipts under
`project/.gatekeeper/state/`.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py`, plus a manual
end-to-end run against a live synthetic project during development.
**Date Added:** v2.3.0. **Projects:** KLStream, Sentinel-GL, AML/collusion-
ring project, CoreMesh.

### D-042 (Category: P, Status: PROPOSED)
**Description:** A reusable, portable archive/snapshot convention for
project-level forensic or large-artifact snapshotting (distinct from
Gatekeeper's own Frozen File snapshots, which have lived safely under
`project/.gatekeeper/snapshots/` since v1.3.2): use Python's own `tarfile`
module directly rather than shelling out to the host `tar`, store the
result under a durable, workspace-controlled path (never `/tmp`), and
record a literal timestamped path directly rather than through a separate
mutable "latest" pointer.
**Evidence:** KLStream (host-`tar`-created archives on macOS embedded
AppleDouble sidecar members invisible to BSD tar's own listing but present
on raw inspection -- same-host recoverable but not archive-member-exact);
Sentinel-GL (a forensic archive was created in a temporary, ephemeral
location and documented as something the Human should separately
remember to preserve).
**Reason:** This is project-specific script guidance, not a gatekeeper.py
mechanical gate -- no project has yet adopted the convention this rule
describes, so it remains PROPOSED rather than ACTIVE pending that evidence.
**Implementation:** Documented pattern in `implementor_spec.md`; no
gatekeeper.py enforcement (nothing to mechanically check about a script a
project hasn't written yet).
**Verification:** None yet -- awaiting a real project's adoption.
**Date Added:** v2.3.0. **Projects:** KLStream, Sentinel-GL (both
described the problem; neither has used the proposed fix).

### D-043 (Category: W, Status: ACTIVE)
**Description:** `clear-takethis` now archives (moves into
`TAKE_THIS_ARCHIVE/<label>-<timestamp>/`, with a checksum manifest) by
default instead of deleting. `--purge` restores the old, unconditional-
delete behavior for anyone who specifically wants it.
**Evidence:** Sentinel-GL (explicitly named this exact command and this
exact assumption -- "clear-takethis assumes the Human already retrieved
the prior bundle" -- as unverifiable and, in this project, false).
**Reason:** A destructive default should not depend on an assumption the
tool has no way to confirm, when a strictly safer default (archive, not
delete) costs nothing.
**Implementation:** `cmd_clear_takethis`.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py`.
**Date Added:** v2.3.0. **Projects:** Sentinel-GL.

### D-044 (Category: G, Status: PROPOSED)
**Description:** `delegate` records a Human-authorized, chunk-scoped,
non-precedent-setting exception to the Implementation Owner table (e.g.
the Architect is genuinely unreachable this chunk). `contract-preflight`
requires an active, matching record whenever a High-risk contract's
`implementation_owner` doesn't match its actual executor.
**Evidence:** Sentinel-GL (five Architect-owned High-risk contracts were
executed by the Implementor under an explicit, one-time Human
authorization, with no structured record of it -- handled entirely in
prose, in reports and a decision-log entry).
**Reason:** The Factory's own Human Usage Model already states the
Architect is used at exactly two points per chunk and "nothing... may
assume the Architect is reachable in between" -- this creates exactly the
tension a bounded, recorded exception mechanism is for. See C55's
delegation note.
**Implementation:** `cmd_delegate`, `_find_active_delegation`,
`project/.gatekeeper/delegations.jsonl`.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py` (synthetic
fixtures only).
**Date Added:** v2.3.0. **Projects:** Sentinel-GL (the only project this
has actually happened on; PROPOSED, not ACTIVE, pending a second).

### D-045 (Category: V, Status: PROPOSED)
**Description:** `recompute` gains a non-blocking shared-dependency check
(via `ast`-parsed imports, not execution): if `independent_script` imports
the same non-stdlib module as `original_script`, that's flagged as weaker
independence even though the two are not byte-identical. An optional
`evidence_tier` field (T1/T2/T3 -- a verification-depth axis genuinely
orthogonal to Scientific Claim Tier) is mechanically capped: a T3 claim
with a flagged shared dependency, or a declared `production_entrypoint`
the independent command doesn't appear to invoke, is reported as an
overclaim. All of this is WARNING-only; a report using none of the new
optional fields behaves exactly as before.
**Evidence:** KLStream (a "T3 adversarial" claim was attached to a fixture
suite that reimplemented its own miniature version of the workflow rather
than invoking the production verifier at all); AML/collusion-ring project
(recompute's byte-identity check was praised as necessary but insufficient
for genuine independence).
**Reason:** Byte-hash inequality proves two files differ, not that they
represent genuinely independent verification paths.
**Implementation:** `_extract_top_level_imports`, `_check_evidence_tier_claim`,
wired into `_check_recompute_block`'s existing PASS path.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py` (synthetic
fixtures only -- PROPOSED pending real-project exercise of the optional
fields).
**Date Added:** v2.3.0. **Projects:** KLStream, AML/collusion-ring project.

### D-046 (Category: R, Status: ACTIVE)
**Description:** `DEFAULT_REQUIRED_SECTIONS` corrected from
`["objective", "verification", "evidence"]` (which matched none of
implementor_spec.md section 8's actual contract_report.md template
headings for "objective" or "evidence") to `["verification", "definition
of done", "final status"]`, which do. `begin` now also generates a report
skeleton with every required heading already present, at the manifest-
implied path, if one doesn't exist yet. self-check gains a fifth diff
target cross-checking this constant against the template directly.
**Evidence:** CoreMesh (a properly-templated C13-01 report was rejected
for "missing" an `evidence` heading the template never asked it to have --
reproduced directly by reading implementor_spec.md's own template and
confirming neither "objective" nor "evidence" appears in any of its
headings).
**Reason:** This was found by applying the same third-party-review-
disposition discipline to gatekeeper.py's own constants that this file
applies to every external report -- not merely by trusting CoreMesh's own
framing of the incident.
**Implementation:** `DEFAULT_REQUIRED_SECTIONS`, `_render_report_skeleton`,
`_self_check_required_sections_vs_template`, `_self_check_naming_convention`
(now line-scoped with a `<!-- GATEKEEPER-EXEMPT: reason -->` convention for
Markdown, mirroring the existing `# GATEKEEPER-EXEMPT:` convention already
used in Python).
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py`;
`factory/tests/test_gatekeeper_self_check.py` extended.
**Date Added:** v2.3.0. **Projects:** CoreMesh (found via direct
cross-check, not this project's own report).

### D-047 (Category: G, Status: ACTIVE)
**Description:** `contract-preflight` now reads and enforces
`repository_preconditions.previous_chunk_approved` (the immediately
preceding chunk's own `chunk_report.md` must contain the word APPROVED) --
a field the Execution Manifest Schema has declared since it was written
and that nothing previously checked.
**Evidence:** CoreMesh (explicitly requested cross-chunk dependency
validation, observing that `prerequisites` in `chunkNN.md` was human-
readable text only, never mechanically checked); found to be a genuine,
pre-existing spec-vs-code gap by direct inspection, not merely CoreMesh's
own framing.
**Reason:** A schema field that is declared but never read is
indistinguishable, in practice, from one that doesn't exist.
**Implementation:** `cmd_contract_preflight`'s `repository_preconditions`
block.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py`.
**Date Added:** v2.3.0. **Projects:** CoreMesh (found via direct
cross-check).

### D-048 (Category: W, Status: ACTIVE)
**Description:** `log-decision` appends a `decision_log.md` entry (and a
structured `decisions.jsonl` backing record) with an auto-incremented
`D-{n}`, always at the end of the file -- never searching for or
inserting before an anchor/register section. `begin`/`finalize` auto-
append `telemetry.jsonl` events matching the existing schema exactly;
`finalize` auto-counts `self_review_attempts` from actual finalize
attempts rather than hand-typing `1`.
**Evidence:** CoreMesh (65 contracts: decision-log entries required a
manual view-then-insert-before-anchor sequence against a file that grew to
~2,900 lines; `self_review_attempts` was hand-typed `1` and `violations`
hand-typed `[]` on literally every one of 65 contracts, regardless of what
actually happened).
**Reason:** decision_log.md's own specification has always said append
only -- a per-project convention requiring insert-before-anchor instead is
what made this expensive, not anything the base schema requires.
**Implementation:** `cmd_log_decision`, `_append_decision`,
`_append_telemetry`, `_increment_finalize_attempts`.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py`.
**Date Added:** v2.3.0. **Projects:** CoreMesh.

### D-049 (Category: G, Status: PROPOSED)
**Description:** `release-check`/`release-certify`'s Release Artifact Scan
now also scans for Factory-internal identifiers (contract/chunk/decision
IDs, `TAKE_THIS`/`DROP_HERE`, `gatekeeper.py`, `project/.gatekeeper`,
labeled Architect/Implementor role language) leaking into a release-bound
artifact, alongside the existing local-path scan.
**Evidence:** AML/collusion-ring project (explicitly requested this exact
scan, after manually catching an early manuscript draft that would have
named the Factory's internal chunk numbering).
**Reason:** The same Project Repository Isolation goal factory_spec.md
already states ("no visible trace... that a project was built using this
Factory"), extended from local-path leaks to this second, textual kind of
fingerprint.
**Implementation:** `_scan_factory_identifiers`, `_FACTORY_ID_PATTERNS`.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py` (synthetic
fixtures only -- PROPOSED pending a second project's evidence).
**Date Added:** v2.3.0. **Projects:** AML/collusion-ring project.

### D-050 (Category: R, Status: PROPOSED)
**Description:** A contract report may declare
`Superseded-By: {contract_id}`; `release-certify` excludes such a report
from the active COMPLETE check and reports it separately under Historical
Findings instead, never blocking current certification on a stale claim a
later contract has already explicitly replaced.
**Evidence:** AML/collusion-ring project (Chunk 19 explicitly superseded
stale Chunk 18 claims; release certification still evaluated historical
recomputation declarations against current artifact paths with no way to
mark them superseded).
**Reason:** History should be preserved, not deleted (C30) -- but a
finding a later contract has explicitly and legitimately superseded is a
different thing from an unresolved current defect, and conflating the two
previously made routine, healthy corrective work look like an unresolved
problem indefinitely.
**Implementation:** `_collect_superseded_contract_ids`, wired into
`cmd_release_certify`.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py` (synthetic
fixtures only).
**Date Added:** v2.3.0. **Projects:** AML/collusion-ring project.

### D-051 (Category: G, Status: PROPOSED)
**Description:** Role capability profiles should describe the Architect
and Implementor by required capability tier, not by a bound vendor/model
name -- `model_id`/`model_version` are still recorded at runtime (on
telemetry events) for audit, but nothing constitutionally binds a role to
one vendor.
**Evidence:** KLStream (in that project, a single agent performed
architecture, implementation, adversarial review, and verification across
one vendor's models; the report explicitly requested provider-neutral role
definitions).
**Reason:** This is a naming/documentation clarification, not a new
mechanical gate -- gatekeeper.py has never actually enforced a vendor
binding (it records `model_id` as a free string), so there is nothing to
change in code, only in how role documents describe the two roles.
**Implementation:** Documentation only -- see architect_spec.md/
implementor_spec.md's role descriptions.
**Verification:** N/A (no mechanical behavior changed).
**Date Added:** v2.3.0. **Projects:** KLStream.

### D-052 (Category: R, Status: ACTIVE)
**Description:** self-check findings now carry stable IDs (`SC{target}-{n}`)
across all five diff targets. The naming-convention diff target is now
line-scoped and honors a `<!-- GATEKEEPER-EXEMPT: reason -->` comment,
mirroring the existing Python `# GATEKEEPER-EXEMPT:` convention already
used by the swallowed-exception scan, for a genuine negative example
(explaining the padding convention by contrasting it with an unpadded
form) that would otherwise be indistinguishable from a worked example to
copy.
**Evidence:** KLStream (explicitly requested finding IDs and a suppression
mechanism, observing that self-check's naming/version-currency findings
could be noisy on deliberate historical or explanatory references); found
directly to be reproducible against this Factory's own documents (three
genuine false-positive-shaped findings existed in gatekeeper.py and
implementor_spec.md before this rule).
**Reason:** A diagnostic tool that cannot distinguish "this needs a look"
from "this is fine, already explained" trains its own readers to ignore it.
**Implementation:** `_self_check_naming_convention` (rewritten,
line-scoped), `cmd_self_check` (finding IDs). Version-currency suppression
is a natural following extension, not yet implemented -- disclosed here,
not silently left incomplete.
**Verification:** `factory/tests/test_gatekeeper_self_check.py` (extended).
**Date Added:** v2.3.0. **Projects:** KLStream.

### D-053 (Category: G, Status: PROPOSED)
**Description:** `release-status` reports whether the existing
`project/RELEASE_CERTIFICATION.md` is still CERTIFIED and current, without
re-running the full `release-certify` battery. `release-certify` itself
now prints a staleness comparison against any prior certificate before
regenerating.
**Evidence:** Reported directly by the Human operator during this same
review round: the identical underlying model, asked "is this ready" in a
brand-new session with no memory of a ten-chunk conversation that had
produced an earlier verbal "publication ready," found numerous issues on
a cold read of the same repository -- and this pattern recurred repeatedly
within the one project it was observed on.
**Reason:** "Is it ready" was being decided by re-asking an LLM's holistic
opinion in two different contexts (a long thread carrying its own prior
commitments, versus a cold read) rather than by re-deriving the same
deterministic answer from the same artifact. See C05 (AI opinion is never
verification) and C59 (a certificate names exactly what it checked).
**Reason this is PROPOSED, not ACTIVE:** the evidence is a single,
repeated-within-one-project observation, not yet cross-project; and the
deepest part of the underlying problem -- an AI role answering "is this
ready" from memory of its own prior conversation rather than by running
this command first -- is a process/prompting practice this command makes
*checkable*, not one gatekeeper.py can force from outside a chat session.
**Implementation:** `cmd_release_status`, `_report_certificate_staleness`.
See architect_spec.md/implementor_spec.md's "Answering 'is this ready'"
section for the corresponding process rule.
**Verification:** `factory/tests/test_gatekeeper_v2_3_0.py` (synthetic
fresh/stale/missing-certificate fixtures).
**Date Added:** v2.3.0. **Projects:** none named (Human-operator-reported
directly, cross-tool: one Architect session plus a separate cross-tool
session of the same underlying model).

---



```
Human Memory

↓

AI Memory

↓

Documentation

↓

Automation

↓

Deterministic Enforcement
```

The ideal Dynamic Rule eventually disappears into automation.

When the Factory no longer needs to remember a lesson because it is enforced automatically, the Factory has improved.

---

# Dynamic Rules Added in v2.4.0

Disposition of a third-party review: `factory_gap_analysis.md`, a document comparing this
Factory (v2.3.0) against an external pre-submission audit manual for elite IEEE/Nature-class
venues. Checked the same way every prior round was checked — by direct `grep` across every spec
file and `gatekeeper.py` for each claimed gap, reading the surviving hits in context, rather than
accepted on the strength of the document's own framing. Every "confirmed gap" claim in that
document was independently re-verified here before anything below was filed; none was taken on
faith. A second document was reviewed alongside it and explicitly excluded: `deep-research-report.md`
is generic, assumption-based output that states outright it never had access to this Factory's
actual files, and describes a different kind of system entirely (a generic multi-language CI/CD
scaffolding tool with Jenkins/SonarQube/MISRA-class tooling) that does not match what this Factory
is or does. Nothing from it appears below or anywhere else in v2.4.0.

**Evidence class, disclosed honestly:** this round's evidence is a single document review, not
completed-project field reports. That is a *weaker* bar than the four-completed-project evidence
behind v2.3.0's disposition above, and closer to v2.2.0's original "round two" disposition
(D-034 through D-038) — itself sourced from a third-party Design Rationale document rather than
this Factory's own first-hand incidents. Per the Amendment Policy, nothing below is promoted to
ACTIVE, and nothing is added to `constitution.md` as a ratified principle. Every item is either
filed PROPOSED (a real, working mechanism, unit-tested against synthetic fixtures, zero project
occurrences) or left as pure reference content with no Dynamic Rule number at all — domain_checklists.md
and venue_requirements_TEMPLATE.md's own header already grant reference content that standing, the
same way MAR-4 through MAR-7 have always had it, so a checklist bullet with no enforcement
mechanism behind it is not filed as a Dynamic Rule.

**Confirmed gaps, per the document's own scorecard (independently re-verified):** hardware/efficiency
profiling (zero hits anywhere in the repo for FLOPs, MACs, peak memory, thermal, or percentile
latency language), compute/parameter/FLOP baseline parity (zero hits for compute-matched,
parameter-matched, or any parity tolerance concept), factorial/single-factor ablation design
(category-list only, no per-row isolation mechanism), OOD/cross-domain/adversarial stress-testing
(one incidental claim-classifier regex string only, no severity-ladder or budget-curve concept),
and Model Cards/Datasheets (zero hits anywhere). A sixth, minor item — effect-size-driven
sample-size planning — was already philosophically covered by MAR-3's flat floor but lacked a
concrete planning formula. **Already covered, and correctly not re-proposed:** leakage (C16),
claim-evidence matching (MAR-4, the T-CAUSAL/T-COMP classifier), baseline recency (MAR-5),
statistical mechanics (D-036/D-027), reproducibility/provenance (C17, C27, Reality Gate), and
pre-submission adversarial review generally (MAR itself, front-loaded rather than end-loaded
relative to the manual's own end-of-pipeline audit).

**Filed as pure reference content, no Dynamic Rule number** (`domain_checklists.md`: Hardware /
Efficiency Claims, Ablation Design, Generalization & Stress-Testing, and a sample-size-planning
addition to the existing Statistics section; `venue_requirements_TEMPLATE.md`: Efficiency Claim
Requirements, Baseline Parity Ledger, Release Documentation — all conditional, "skip if not
applicable"): these change no gatekeeper.py behavior and enforce nothing; they exist purely to
give the Architect and Implementor a concrete starting point, the same standing every other
section of `domain_checklists.md` already has.

### D-054 (Category: V, Status: PROPOSED)
**Description:** `tier-check` bundles a fifth WARNING-only heuristic (alongside D-035/036/037):
flags a contract whose text names an ablation alongside language describing a factor that
plausibly covaries with the named removal (parameter count, training steps, compute budget), with
no nearby "held fixed"/"parameter-matched"/"controlled for" declaration.
**Evidence:** Distinct from this Factory's own first-hand incident trail (the GLOF/BPFeat evidence
D-022 through D-031 are grounded in), and distinct from v2.3.0's four-completed-project evidence
above: this rule's motivating pattern — an ablation row silently changing more than one factor and
attributing the resulting effect to only the named one — is drawn from `factory_gap_analysis.md`
§3.3, itself citing the confounded-ablation flaw named in an external pre-submission audit manual.
Cited here as document-sourced evidence, honestly distinguished from a first-hand Factory
incident or cross-project field report, per this file's own citation discipline (see D-035's
entry above, which draws the same distinction for its own source).
**Reason:** An ablation table row's Definition of Done confirming a metric changed does not
confirm *why* it changed. This is the mechanical, WARNING-only proxy for a broader principle
(see the Candidate Observation below) that has not itself cleared the evidence bar for
Constitution status.
**Implementation:** `_scan_ablation_row_covariance`, `_ABLATION_MENTION_RE`,
`_ABLATION_COVARYING_RE`, `_ABLATION_HELD_FIXED_RE`; wired into `cmd_tier_check` per C46 (bundled
into the existing command, not a new one).
**Verification:** `factory/tests/test_gatekeeper_v2_4_0.py` (synthetic fixtures only).
**Date Added:** v2.4.0. **Projects:** none — zero project occurrences; PROPOSED pending a real
pilot, per `factory_gap_analysis.md`'s own recommended rollout sequencing (candidates for a first
pilot: any project with an architectural ablation in scope).

### D-055 (Category: V, Status: PROPOSED)
**Description:** `tier-check` bundles a sixth WARNING-only heuristic: flags a real-time/latency/
throughput/efficiency claim reported with mean-only latency language and no percentile language
(p50/p90/p95/p99/tail) found anywhere in the contract's own text.
**Evidence:** Document-sourced, same posture and same source document as D-054 above —
`factory_gap_analysis.md` §3.1, citing the confirmed absence of any percentile-latency concept
anywhere in this Factory (verified independently: zero hits for FLOPs, MACs, peak memory,
thermal, or p50/p90/p99 language before this round).
**Reason:** A mean can hide a bad tail; a system claimed to be "real-time" is broken by its tail,
not its average. This Factory's projects to date were scored on detection/classification accuracy,
not deployment efficiency, so this was never previously a design target — not a rule that was
dropped, one that was never needed until a project like BPFeat (real-time/backpressure claims)
made it relevant.
**Implementation:** `_scan_efficiency_claim_measurement`, `_EFFICIENCY_CLAIM_RE`,
`_MEAN_ONLY_LATENCY_RE`, `_PERCENTILE_LATENCY_RE`; wired into `cmd_tier_check` per C46.
**Verification:** `factory/tests/test_gatekeeper_v2_4_0.py` (synthetic fixtures only).
**Date Added:** v2.4.0. **Projects:** none — zero project occurrences; PROPOSED pending a real
pilot (candidate: BPFeat, or any project making a real-time/latency/throughput claim).

### D-056 (Category: G, Status: PROPOSED)
**Description:** `hardware_profile_manifest.json` — a Reality-Gate-adjacent manifest schema
(same pattern as `data_manifest.json`'s D-014, `acquisition_provenance.json`'s D-019) produced by
whichever contract measures a project's claimed latency/throughput/memory numbers, only for a
project whose `venue_requirements.md` Efficiency Claim Requirements section (v2.4.0) is not N/A.
Paired with a candidate MAR-8 gate (`factory_spec.md`'s Candidate gate extensions) and a
verification process the Architect performs at Chunk Review, comparing the manifest's
`latency_ms`/`memory_mb` fields against what the manuscript or report actually claims.
**Evidence:** Document-sourced (`factory_gap_analysis.md` §3.1 and §4), same posture as D-054/D-055.
**Reason:** Turns a narrative "we measured latency" sentence a reviewer has to take on faith into
something structurally checkable — the same comparative advantage Reality Gate and the Mandatory
Mechanical Gate already demonstrate for other claim types, per `factory_gap_analysis.md` §4's own
framing of this Factory's actual edge over an advisory-only manual.
**Implementation:** Schema documented in `factory_spec.md` ("hardware_profile_manifest.json").
Not implemented in `gatekeeper.py` — like Reality Gate's own checks and
`acquisition_provenance.json`, this is a declared-schema-plus-manual-comparison pattern; no
project has yet produced this manifest, so there is nothing yet to mechanically diff against.
**Verification:** None yet — awaiting a real project's first efficiency/real-time claim.
**Date Added:** v2.4.0. **Projects:** none.

### D-057 (Category: G, Status: PROPOSED)
**Description:** Baseline Parity Ledger — a per-dimension table in `venue_requirements.md`
(v2.4.0) declaring, for every principal T-COMP/T-CAUSAL baseline, whether train examples,
augmentation, optimizer, HPO budget, parameters (±2% tolerance), FLOPs/compute (±5% tolerance),
and precision are matched between baseline and proposed method — plus, when comparing against an
older architecture, `Old_published`/`Old_modernized`/`Proposed_matched` declarations that separate
a genuine contribution from five years of better training recipes applied to an old baseline.
Paired with an extension to MAR-2 (`factory_spec.md`'s Candidate gate extensions) and a
verification process at Chunk Review's Baseline Completeness Check.
**Evidence:** Document-sourced (`factory_gap_analysis.md` §3.2 and §4), same posture as D-056.
**Reason:** MAR-2's existing category-count check (≥3 baseline categories) answers "are there
enough baselines," not "was each one given a fair chance" — a real, confirmed hole (zero hits for
any parity or tolerance concept anywhere in the repo before this round).
**Implementation:** Table template in `venue_requirements_TEMPLATE.md` ("Baseline Parity
Ledger"). Not implemented in `gatekeeper.py` — presence/completeness of the ledger is structural
in principle, but whether a stated tolerance was genuinely met from a project's own numbers is a
judgement call, the same standing MAR-2's own category check already has.
**Verification:** None yet — awaiting a real project's first T-COMP claim against a baseline with
its own ledger filled in.
**Date Added:** v2.4.0. **Projects:** none.

### D-058 (Category: R, Status: PROPOSED)
**Description:** Release Documentation — a conditional `venue_requirements_TEMPLATE.md` section
(v2.4.0) requiring a completed Model Card (Mitchell et al., 2019) for any released trained model
and a Datasheet (Gebru et al., 2018) for any constructed/repackaged dataset, plus a check for
disaggregated (subgroup) evaluation alongside any aggregate metric.
**Evidence:** Document-sourced (`factory_gap_analysis.md` §3.5), citing Model Cards/Datasheets as
"increasingly a condition of publication, not a courtesy, at several venues including Nature
Machine Intelligence." Confirmed independently: zero hits anywhere in the repo before this round.
**Reason:** A documentation-completeness gap, not a scientific-rigor gap — closer in spirit to C15
("Documentation Bugs Are Real Bugs," generalized: a Model Card is part of the release artifact set,
same as the code) than to anything statistical. No mechanical gate is proposed for this reason.
**Implementation:** Template section only, in `venue_requirements_TEMPLATE.md`. No
`gatekeeper.py` change.
**Verification:** None needed beyond the template section existing and being filled in (or
explicitly marked N/A) at Project Initialization.
**Date Added:** v2.4.0. **Projects:** none.

## Candidate Observation, not filed as a Dynamic Rule (v2.4.0)

`factory_gap_analysis.md` drafted full Constitution-style text for a "C62 — An Ablation Row
Isolates Exactly One Factor," structurally analogous to C58's existing operator/semantic-test
principle but for ablation design specifically, and proposed placing it in a new Section 10 or
alongside C16/C19/C20 in Section 3. That text is not adopted here, in either location. C58 itself
took repeated, genuinely independent cross-project evidence to ratify; a single document's
reasoning, however carefully checked against the actual files, is explicitly not that, and the
source document says so about its own draft: "none of it is a Constitution rule until it clears
the same bar C60/C61 cleared." D-054 above already ships the low-risk, WARNING-only mechanical
proxy for this idea and costs nothing to run today. If the underlying failure D-054 is built to
catch — an ablation row silently changing more than one factor — actually recurs across ≥2
independent projects, C62 (or a version of it revised by what that recurrence actually looked
like) becomes a real Amendment Policy candidate at that point, not before. Recorded here so the
idea isn't lost, exactly as this section's own purpose requires, and so a future Architect
proposing "C62" again knows it was already considered and deliberately not ratified for evidence
reasons, not overlooked.

# Factory Principle (v2.4.0 addendum)

A document that reasons carefully about this Factory's own files is worth taking seriously and
worth checking. It is not, by itself, worth amending the Constitution over — that took repeated
evidence before, twice, and a shortcut here would make every future Amendment Policy invocation a
formality rather than a bar. The five PROPOSED rules above and the two schemas alongside them are
real, working, and free to use starting today; none of them costs the human operator anything
beyond filling in a template section that says "skip if not applicable." That is the whole point
of keeping Tier A and Tier B separate: rigor that costs nothing ships immediately, and rigor that
would need to become mandatory waits for the evidence mandatory things require.

---

# Dynamic Rules Added in v2.5.0

Operationalization of elite publication rigor standards from `DEEP-RESEARCH.MD`. In v2.5.0, candidate rules D-054 through D-058 are promoted to ACTIVE status, supported by ratified Constitution principles C62, C63, and C64, and backed by deterministic verification subcommands in `gatekeeper.py`. Three new rules (D-059 through D-061) are added to close critical empirical vulnerabilities identified in modern elite venue review (foundation model benchmark contamination, confirmatory seed freezing, and generalization ladder evaluation).

### D-054 (Category: V, Status: ACTIVE — promoted v2.5.0)
**Description:** Ablation factor isolation enforcement. Backed by Constitution C62. Every ablation row in an empirical study must isolate exactly one factor. `gatekeeper.py tier-check` and contract review enforce that any ablation row covarying parameter count or compute must include a parameter-matched or compute-matched control (e.g. widening a baseline block or matching training steps).
**Evidence:** Elite venue review criteria (NeurIPS, CVPR, Nature Portfolio ML checklist); operationalizes C62 against confounded ablations.
**Reason:** Prevents attributing performance differences to an architectural mechanism when capacity or compute actually drove the gain.
**Implementation:** `_scan_ablation_row_covariance`, `_ABLATION_MENTION_RE`, `_ABLATION_COVARYING_RE`, `_ABLATION_HELD_FIXED_RE`; hard-failure in contract verification when capacity changes are unisolated.
**Verification:** `factory/tests/test_gatekeeper_v2_5_0.py`.
**Date Added:** v2.4.0 (PROPOSED), promoted v2.5.0 (ACTIVE).

### D-055 (Category: V, Status: ACTIVE — promoted v2.5.0)
**Description:** Percentile latency enforcement for efficiency claims. Backed by Constitution C64. Any efficiency, latency, throughput, or real-time claim must be backed by steady-state percentile measurements (p50, p90, p99) excluding warm-up iterations. Mean-only latency reporting for efficiency claims is prohibited.
**Evidence:** Systems and hardware profiling standards for MLSys, IEEE, and elite AI venues.
**Reason:** A mean hides long-tail latency spikes; real-time systems fail on tail latency.
**Implementation:** `_scan_efficiency_claim_measurement`; enforced via `gatekeeper.py verify-hardware-profile`.
**Verification:** `factory/tests/test_gatekeeper_v2_5_0.py`.
**Date Added:** v2.4.0 (PROPOSED), promoted v2.5.0 (ACTIVE).

### D-056 (Category: G, Status: ACTIVE — promoted v2.5.0)
**Description:** `hardware_profile_manifest.json` mechanical verification. Mandated by candidate gate MAR-8 (ratified v2.5.0). Whichever contract measures claimed efficiency metrics must output this structured manifest. Verified deterministically by `gatekeeper.py verify-hardware-profile`.
**Evidence:** Eliminates unverified hardware efficiency claims; enforces MLPerf-style systems reporting.
**Reason:** Makes efficiency claims mechanically auditable across hardware model, driver, framework, precision, batch size, warm-up exclusion, and memory.
**Implementation:** `gatekeeper.py verify-hardware-profile` command and `cmd_verify_hardware_profile` handler.
**Verification:** `factory/tests/test_gatekeeper_v2_5_0.py`.
**Date Added:** v2.4.0 (PROPOSED), promoted v2.5.0 (ACTIVE).

### D-057 (Category: G, Status: ACTIVE — promoted v2.5.0)
**Description:** Baseline Parity Ledger verification. Mandated by MAR-2 extension (ratified v2.5.0). For every principal T-COMP/T-CAUSAL baseline, verifies that parameter count (±2%), FLOPs (±5%), and training compute (±5%) fall within declared tolerances, and that Old_published, Old_modernized, and Proposed_matched are declared.
**Evidence:** Neutralizes Fatal Flaw 2 (unequal baseline tuning) and Fatal Flaw 6 (strawman comparisons) in elite venues.
**Reason:** Separates algorithmic advance from modern training recipe improvements.
**Implementation:** `gatekeeper.py verify-baseline-parity` command and `cmd_verify_baseline_parity` handler.
**Verification:** `factory/tests/test_gatekeeper_v2_5_0.py`.
**Date Added:** v2.4.0 (PROPOSED), promoted v2.5.0 (ACTIVE).

### D-058 (Category: R, Status: ACTIVE — promoted v2.5.0)
**Description:** Release Documentation. Mandates Model Cards (Mitchell et al.) for trained model deliverables and Datasheets (Gebru et al.) for constructed or repackaged datasets, plus disaggregated subgroup evaluations.
**Evidence:** Nature Portfolio ML checklist and NeurIPS release guidelines.
**Reason:** Documentation completeness and provenance are mandatory components of empirical publication.
**Implementation:** Template requirements in `venue_requirements_TEMPLATE.md` and release audits in `gatekeeper.py release-certify`.
**Verification:** `factory/tests/test_gatekeeper_v2_5_0.py`.
**Date Added:** v2.4.0 (PROPOSED), promoted v2.5.0 (ACTIVE).

### D-059 (Category: V, Status: ACTIVE)
**Description:** Foundation Model Benchmark Contamination Audit. Requires auditing evaluation datasets against training corpora and foundation model pretraining cutoff dates. Evaluated by `gatekeeper.py contamination-check`.
**Evidence:** Kapoor & Narayanan leakage analysis; modern 2026 foundation-model benchmark contamination standards.
**Reason:** Benchmark memorization produces illusory generalization and automatic desk rejection at elite venues.
**Implementation:** `gatekeeper.py contamination-check` scanning benchmark items for n-gram overlap and validating model cutoff dates.
**Verification:** `factory/tests/test_gatekeeper_v2_5_0.py`.
**Date Added:** v2.5.0.

### D-060 (Category: G, Status: ACTIVE)
**Description:** Confirmatory Experiment Freeze Manifest. Backed by Constitution C63. Before confirmatory evaluation runs supporting paper claims begin, an experiment freeze manifest (`project/experiment_freeze_manifest.json`) must lock git commit hash, environment configuration, dataset split checksums, and pre-registered random seed schedule (minimum 5–10 seeds or power-planned n ≈ 7.85/d²). Verified by `gatekeeper.py verify-experiment-freeze`.
**Evidence:** Neutralizes seed-lottery cherry-picking and optional stopping (adding seeds until p < 0.05).
**Reason:** Decouples model exploration and hyperparameter tuning from final confirmatory claim evaluation.
**Implementation:** `gatekeeper.py freeze-experiment` and `gatekeeper.py verify-experiment-freeze`.
**Verification:** `factory/tests/test_gatekeeper_v2_5_0.py`.
**Date Added:** v2.5.0.

### D-061 (Category: V, Status: ACTIVE)
**Description:** The 6-Rung Generalization Ladder Verification. Any empirical paper claiming "robustness", "out-of-distribution generalization", or "real-world deployment" must evaluate against at least Rung 3 (fully independent external dataset) or Rung 4 (systematic perturbation/corruption severity ladder), accompanied by a structured failure case taxonomy.
**Evidence:** Nature Machine Intelligence external dataset requirement; NeurIPS robustness checklist; CVPR empirical evaluation standards.
**Reason:** Prevents Fatal Flaw 5 (Claim-Evidence Scope Mismatch) where narrow in-distribution benchmark results are claimed as universal or robust.
**Implementation:** Checked at MAR-4/MAR-6 and enforced in `venue_requirements_TEMPLATE.md` and Chunk Review audits.
**Verification:** `factory/tests/test_gatekeeper_v2_5_0.py`.
**Date Added:** v2.5.0.

---

# Dynamic Rules Added in v2.6.0

Complete operationalization of DEEP-RESEARCH.MD statistical methodology, sensitivity analysis, enhanced ablation standards, efficiency profiling, pre-submission audit protocol, and release documentation requirements. Supported by ratified Constitution principles C65–C69 and backed by deterministic verification subcommands `verify-statistical-protocol` (exit 27), `verify-sensitivity-analysis` (exit 28), `pre-submission-audit` (exit 29), and `verify-failure-taxonomy` (exit 30) in `gatekeeper.py`.

### D-062 (Category: V, Status: ACTIVE)
**Description:** Statistical test decision tree compliance. Every T-COMP or T-CAUSAL claim must name a specific, justified significance test that matches the pairing structure, distributional assumptions, and multiplicity of the comparison. The factory enforces:
- Paired seeds/splits → paired test (paired t-test, Wilcoxon signed-rank, paired permutation)
- >2 methods across multiple datasets → Friedman test + post-hoc (Holm, Nemenyi)
- >3 pairwise hypotheses → Holm or Benjamini-Hochberg FDR correction
- N < 10 runs → IQM with stratified bootstrap CI preferred over arithmetic mean
- Bounded/asymmetric metrics → asymmetric confidence intervals (no symmetric bars extending past feasible range)
**Evidence:** DEEP-RESEARCH.MD Sections 2.3 (significance test decision tree), Demšar (2006) multi-dataset comparison guidance, NeurIPS checklist items on uncertainty/significance.
**Reason:** Prevents unnamed or default significance tests, which are among the most common reviewer objections at elite venues.
**Implementation:** `gatekeeper.py verify-statistical-protocol` (exit 27), `_scan_statistical_protocol`.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Backed by:** Constitution C65.
**Date Added:** v2.6.0.

### D-063 (Category: V, Status: ACTIVE)
**Description:** Effect size mandatory alongside every p-value. No p-value may appear in an evaluation report or manuscript without an accompanying effect-size measure (Cohen's d, Hedge's g, paired difference CI, or equivalent) and an explicit statement of practical importance relative to the minimum meaningful effect declared in `venue_requirements.md`.
**Evidence:** DEEP-RESEARCH.MD Section 2.2 ("A significant p-value alone is weak evidence. An adversarial reviewer wants the effect size, uncertainty, practical importance, and the exact experimental unit."); NeurIPS checklist items on uncertainty.
**Reason:** Statistical significance without practical significance is a reviewer attack surface; conversely, non-significance from underpowered experiments says nothing about equivalence.
**Implementation:** `gatekeeper.py verify-statistical-protocol` (exit 27), heuristic scan for p-value mentions without effect-size companions.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Backed by:** Constitution C66.
**Date Added:** v2.6.0.

### D-064 (Category: V, Status: ACTIVE)
**Description:** Multiple-comparisons correction enforcement. When >3 pairwise comparisons are reported in a single evaluation artifact, a named multiple-comparisons correction (Holm, Bonferroni, Benjamini-Hochberg FDR) must be declared and applied. Pre-declared primary contrasts are exempt from the correction; secondary/exploratory contrasts are not. Dozens of metrics/configurations yielding one uncorrected significant result is a hard FAIL.
**Evidence:** DEEP-RESEARCH.MD Section 2.3 (multiplicity audit); NeurIPS checklist.
**Reason:** Without correction, exploratory testing inflates false-positive rates, which elite venue reviewers specifically target.
**Implementation:** `gatekeeper.py verify-statistical-protocol` (exit 27), heuristic counting of comparison instances.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Backed by:** Constitution C65.
**Date Added:** v2.6.0.

### D-065 (Category: V, Status: ACTIVE)
**Description:** Sensitivity analysis mandatory for every hyperparameter feeding a T-COMP or T-CAUSAL claim. The protocol requires:
- For linear-scale HPs: perturbation grid `h × {0.50, 0.75, 0.90, 1.00, 1.10, 1.25, 1.50}` (minimum 5 levels).
- For log-scale HPs (learning rate, weight decay): multiplicative grid `h × {0.5, 0.75, 1.0, 1.5, 2.0}`.
- Response curves must be plotted, not just "best setting" tables.
- Architecture sensitivity: at least one variation beyond the published configuration (width, depth, backbone family, optimizer, pretraining/no-pretraining) for claims of general method applicability.
- Report *where performance falls off*, not just where it holds.
**Evidence:** DEEP-RESEARCH.MD Sections 2.6.1–2.6.3 (hyperparameter sensitivity, architecture sensitivity).
**Reason:** A method that works at one knife-edge configuration but fails for small neighboring choices has a different claim status than a "robust improvement."
**Implementation:** `gatekeeper.py verify-sensitivity-analysis` (exit 28), `_parse_sensitivity_manifest`.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Date Added:** v2.6.0.

### D-066 (Category: V, Status: ACTIVE)
**Description:** Negative controls mandatory for novel architectural modules. When an ablation claims a novel learned module (attention, routing, auxiliary loss, learned weighting) is responsible for a gain, the ablation must include a negative/degenerate control: the same module with parameters replaced by random, shuffled, uniform, or identity-function equivalents of the same shape and parameter count.
**Evidence:** DEEP-RESEARCH.MD Section 3.4 (causal-control extensions: "Remove it AND parameter-match the control"); NeurIPS/Nature ablation standards.
**Reason:** "Removing Module X hurts" does not prove that X's learned function matters — it may prove only that X's parameter count matters. The degenerate control isolates learned contribution from architectural contribution.
**Implementation:** Checked by `gatekeeper.py verify-statistical-protocol` as part of ablation completeness scan; manual enforcement at Chunk Review.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Backed by:** Constitution C67.
**Date Added:** v2.6.0.

### D-067 (Category: V, Status: ACTIVE)
**Description:** Retuned ablation reporting for load-bearing components. For any component described as "essential" or "load-bearing" in the paper, the evaluation must report both:
- Δ^fixed = y(full) − y(remove i; θ_full) — fixed-HP ablation
- Δ^retuned = y(full, tuned) − y(remove i, retuned) — retuned ablation
If only one type is reported, the paper must state which and why.
**Evidence:** DEEP-RESEARCH.MD Section 3.5 ("Fixed hyperparameters and retuned ablations answer different questions").
**Reason:** If Δ^fixed is large but Δ^retuned vanishes, the component simplifies optimization rather than expanding the performance frontier — a more honest scientific conclusion.
**Implementation:** Checked at Chunk Review ablation audit and heuristic scan in `verify-statistical-protocol`.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Backed by:** Constitution C68.
**Date Added:** v2.6.0.

### D-068 (Category: G, Status: ACTIVE)
**Description:** Energy measurement mandatory for "efficient" or "green" claims. If the project title, abstract, or claims table uses "efficient," "energy-efficient," "green," "sustainable," or "low-power," the `hardware_profile_manifest.json` must include `energy_per_inference` (J/sample or J/token) measured by physical power meter or OS-level power instrumentation — not derived from TDP. For training, `energy_per_training_run` (Wh) must be reported. For edge/embedded claims, `thermal_sustained` (sustained test duration ≥ 60s, throttling reported) is also required.
**Evidence:** DEEP-RESEARCH.MD Section 4.5 (Energy and thermal integrity); MLPerf Power methodology; NeurIPS/Nature compute reporting.
**Reason:** TDP ≠ measured energy. A 5-second benchmark before thermal saturation is weak evidence for sustained deployment.
**Implementation:** Extended `gatekeeper.py verify-hardware-profile` to check `energy_per_inference`, `thermal_sustained` fields conditionally based on claim keywords.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Backed by:** Constitution C64.
**Date Added:** v2.6.0.

### D-069 (Category: G, Status: ACTIVE)
**Description:** FLOPs reported alongside, never instead of, real latency. If a hardware profile manifest reports `flops` or `macs`, it must also contain `latency_p50_ms`, `latency_p90_ms`, and `latency_p99_ms` measured on the same hardware. FLOPs/MACs must declare counting convention (1 MAC = 1 or 2 FLOPs), input shape, and whether sparsity is theoretical or actually exploited. For dynamic models, report the mean and distribution of executed compute, not merely maximum architecture FLOPs.
**Evidence:** DEEP-RESEARCH.MD Section 4.3 (MAC/FLOP integrity); MLPerf scenario-specific measurement.
**Reason:** FLOPs ≠ latency. Parameter count ≠ memory. Mixing counting conventions makes tables misleading.
**Implementation:** Extended `gatekeeper.py verify-hardware-profile` validation logic.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Backed by:** Constitution C64.
**Date Added:** v2.6.0.

### D-070 (Category: G, Status: ACTIVE)
**Description:** Pre-submission audit mandatory before release certification for venue-targeted projects. Before `gatekeeper.py release-certify` may pass for any project whose `venue_requirements.md` names a specific target venue, `gatekeeper.py pre-submission-audit` must have produced a passing audit report with no FAIL findings on any of its 10 adversarial audit steps.
**Evidence:** DEEP-RESEARCH.MD Section 5 (Step-by-Step Pre-Submission Audit Protocol); CVPR AC process; NeurIPS meta-review simulation.
**Reason:** The pre-submission audit converts "we hope reviewers won't notice" into "we already found and addressed the strongest rejection arguments."
**Implementation:** `gatekeeper.py pre-submission-audit` (exit 29); integrated into `release-certify` prerequisite chain.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Date Added:** v2.6.0.

### D-071 (Category: V, Status: ACTIVE)
**Description:** Failure taxonomy mandatory for claims of robustness, generalization, or deployment suitability. The failure taxonomy must contain: (a) failure prevalence P(failure|condition), not hand-picked examples; (b) ≥3 failure categories defined by mechanism; (c) explicit selection rule for displayed examples; (d) comparative failures showing whether baseline and proposed method fail on the same inputs; (e) confidence analysis on failures.
**Evidence:** DEEP-RESEARCH.MD Section 4.8 (failure case analysis); NeurIPS 2026 Negative Results contribution type guidance.
**Reason:** Hand-picked failure examples are anecdotes, not evidence. Systematic failure analysis bounds the contribution's scope.
**Implementation:** `gatekeeper.py verify-failure-taxonomy` (exit 30); `_parse_failure_taxonomy`.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Backed by:** Constitution C69.
**Date Added:** v2.6.0.

### D-072 (Category: R, Status: ACTIVE)
**Description:** LLM usage declaration mandatory. If any Large Language Model was used in methodology, data processing, code generation, evaluation prompt design, or manuscript writing, this must be declared in the paper's methodology section and in the project's `venue_requirements.md`. NeurIPS 2026 checklist item 16 and CVPR 2026 author guidelines explicitly address this.
**Evidence:** NeurIPS 2026 checklist; CVPR 2026 Author Guidelines; DEEP-RESEARCH.MD Section 1.2 (ethical oversight).
**Reason:** Undisclosed LLM usage in peer-reviewed research is a policy violation at NeurIPS, CVPR, and IEEE venues.
**Implementation:** Extended `gatekeeper.py release-certify` to scan for LLM declaration section.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Date Added:** v2.6.0.

### D-073 (Category: V, Status: ACTIVE)
**Description:** Calibration analysis required for confidence-dependent deployment claims. If the paper claims or implies that model confidence/uncertainty will be used in deployment (e.g., "high-confidence predictions," "uncertainty-aware decision making," "selective prediction"), calibration metrics (Expected Calibration Error, reliability diagrams, confidence-vs-accuracy analysis) must be reported. Accuracy alone is insufficient when model confidence drives downstream decisions.
**Evidence:** DEEP-RESEARCH.MD Section 5 (Calibration audit step); NeurIPS calibration/uncertainty requirements.
**Reason:** A model that is wrong at 0.999 confidence is qualitatively different from one wrong at 0.51 confidence — and deployment safety depends on this distinction.
**Implementation:** Checked at Chunk Review and scanned heuristically by `gatekeeper.py pre-submission-audit` step 6.
**Verification:** `factory/tests/test_gatekeeper_v2_6_0.py`.
**Date Added:** v2.6.0.

