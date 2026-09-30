# The AI Software Factory — Complete Reference

Version described: 2.6.0 · This document is self-contained. It exists so that any AI system, human, or automated process — with no other file attached — can understand what this Factory is, why it exists, how every part of it works, and how they fit together. If you are an AI reading this to answer questions about the Factory, treat everything below as authoritative and current as of v2.2.0 unless told otherwise by the person you're speaking with. **v2.2.0 note:** this pass updated role terminology throughout (Architect/Implementor, matching `architect_spec.md`/`implementor_spec.md`), §2, §7 (rewritten as a short pointer to `gatekeeper_spec.md` rather than a duplicated, independently-drifting command list — see §7's own note on why), and §12 (History) through the current version. §5's and §6's detailed internal mechanics were last fully synced at v1.2.0/v1.3.4 respectively and were not independently re-verified line-by-line in this pass beyond the role renaming — `factory_spec.md` and `dynamic_rules.md` are the authoritative, current source for anything in those sections that seems to undercount what those files actually contain. Flagged here rather than silently left ambiguous, per this file's own existing policy (see the identical disclosure the v1.4.2 header carried for the gap it was honest about). **v2.4.0 note:** this pass only updated the version banner and §12 (History), adding the v2.3.0 entry that was missed at the time and a new v2.4.0 entry — see `CHANGELOG.md`'s v2.4.0 entry for the substantive account. §2 through §11's internal mechanics were not re-synced and remain current only as of v2.2.0; `architect_spec.md`, `implementor_spec.md`, `factory_spec.md`, `gatekeeper_spec.md`, and `dynamic_rules.md` are the authoritative, current source for anything from v2.3.0 or v2.4.0 this document doesn't yet reflect. **v2.4.1 note:** this pass updated the version banner and §12 (History), adding the v2.4.1 entry for the five remaining Tier-A reference items from `factory_gap_analysis.md` — see `CHANGELOG.md`'s v2.4.1 entry for the substantive account. **v2.5.0 note:** this pass updated the version banner, ratified Constitution Principles C62–C64, activated dynamic rules D-054 through D-061, added 5 mechanical enforcement subcommands in `gatekeeper.py` (exit codes 23–26), eliminated same-session self-review on MAR 4–7 for peer-reviewed venues via cross-model adversarial audit, and updated §12 (History). **v2.6.0 note:** this pass updated the version banner, ratified Constitution Section 11 (Principles C65–C69), activated dynamic rules D-062 through D-073, added 4 mechanical enforcement subcommands in `gatekeeper.py` (exit codes 27–30), extended `verify-hardware-profile` with claim-gated physical energy/thermal/FLOPs verification, added 7 comprehensive academic rigor protocol sections to `venue_requirements_TEMPLATE.md`, and updated §12 (History).

---

## 1. What this is, in one paragraph

The AI Software Factory is a structured workflow for building real software projects using two AI models in different roles, with a human orchestrating between them and a small deterministic script (not an AI) enforcing the rules neither AI is trusted to enforce on itself. One AI (the **Architect**) plans architecture, breaks work into small verifiable units called **contracts**, and reviews finished work. A second AI (the **Implementor**) executes those contracts autonomously, one at a time, inside an actual codebase, running real tests before ever claiming something works. There is no third, standing AI role — any review function that might otherwise call for one (adversarial reading of raw artifacts, methodology review before implementation begins) is the Architect's own responsibility (v2.2.0, Constitution C55). A **Gatekeeper** script checks objective, mechanically-verifiable facts — file hashes, report existence, clean git state — because neither AI's self-report is treated as sufficient proof on its own. The whole system is versioned like software, with a Constitution of near-permanent rules at the top, a specification of concrete mechanics below that, and a rolling list of evidence-based "Dynamic Rules" that the Factory learns over time. Nothing is added to this system because it "seems like a good idea" — everything is justified by either a stated engineering principle or actual evidence from a completed project, and where that bar wasn't fully met (v2.2.0's own architectural fork, built at Human direction — see §12), the document says so rather than presenting itself as more validated than it is.

The core motivation, restated plainly: **AI models are extremely capable but not trustworthy by default.** They can produce plausible-sounding work that is subtly or completely wrong, they can claim success when they failed, and they have no persistent memory or accountability across sessions the way a human engineer would. The Factory exists to get useful, correct engineering work out of AI models anyway — not by hoping they behave, but by structuring the work so that fabrication is hard to get away with, verification is mandatory and mostly automated, and every claim of "done" has to be backed by something checkable. A second, related lesson, applied specifically in v2.2.0: **more roles and more registries are not the same thing as more protection.** A three-role, dozens-of-registries version of this Factory (v1.5.0 through v2.1.0, in this lineage's own history) still let a real contract declare `Scientific Claim Tier: NONE` while computing a Wilcoxon test and a Cliff's delta for a paper's core hypotheses (see §12) — the fix that actually closed that gap was one new mechanical check, not a new role.

---

## 2. The three roles

### 2.1 The Architect (currently bound to Claude)

Operates in a normal chat interface (claude.ai, in a browser). Responsible for every project-level decision: what to build, how to structure it, how to break it into chunks and contracts, what counts as done, and whether finished work is actually acceptable. The Architect is the only role allowed to make architectural decisions, and the only role allowed to implement work tagged "High" risk tier directly (see §5.3). The Architect is used at exactly two points per work cycle — the start (planning) and the end (review) — and is never assumed to be reachable in between. As of v2.2.0, the Architect is also the only role that performs Methodology Adversarial Review's judgment gates (§5.2, `architect_spec.md` §5a) — there is no separate Auditor to hand this to.

### 2.2 The Implementor (currently bound to Gemini, or any sufficiently capable coding agent — v2.2.0 renaming from "Implementation Engineer;" see `CHANGELOG.md`)

Operates inside an IDE-like agentic environment. Responsible for taking one contract at a time — a small, fully-specified unit of work the Architect already designed — and actually building it: writing code, running tests, checking its own work adversarially, and reporting honestly on what happened. The Implementor never makes architectural decisions, never touches files outside what a contract explicitly allows, and works through an entire chunk of contracts autonomously without anyone checking in mid-stream.

### 2.3 The Gatekeeper (a Python script, not an AI)

`gatekeeper.py`. Deterministic, non-negotiable, and dumb on purpose — it does not reason, evaluate quality, or use judgment. It checks facts: does this file's hash match what was recorded before work started (proves a "Frozen File" wasn't touched), does a required report exist and contain required sections, is the git working tree clean, what does the declared execution order say is next, does a dropped-in file match a known naming pattern, and — as of v2.2.0 — does a contract's own text imply a stronger empirical claim than its self-declared Scientific Claim Tier admits to. Its entire value proposition is that it cannot be talked into a false positive the way an AI might be. It implements a meaningful but partial subset of what a "complete" Gatekeeper would eventually do — the rest is still AI-attested, and the Factory is explicit and honest about which is which at all times (§7).

### 2.4 The Human

Owns final approval, physically moves files between the two AI workspaces (they don't share a filesystem or a conversation), makes any decision the Constitution says only a human can make, and provides anything no AI can produce itself (credentials, hardware access, external datasets, legal/business judgment calls). The Human's job is deliberately minimal: attach two documents once each, drop files into a shared inbox folder, and speak in short, informal, natural sentences to both AIs. The Human does not write or maintain prompts, does not manually sort files into the project structure, and does not repeat context that's already been established.

---

## 3. The document hierarchy — what governs what

```
Human
  ↓ (final authority; can override anything except safety-critical rules)
Constitution (constitution.md)
  ↓ (permanent, near-universal engineering principles — rarely changes)
Factory Specification (factory_spec.md)
  ↓ (concrete mechanics: what a contract looks like, what a chunk is, file formats)
Dynamic Rules (dynamic_rules.md)
  ↓ (evidence-based lessons learned from real projects — extends but never overrides the above)
Project Invariants (invariants.md, written per-project)
  ↓ (facts that must never become false for one specific project's lifetime)
Contracts (written per-chunk, per-project)
  ↓ (the actual unit of work an AI executes)
Implementation (the real code/output produced)
```

A lower layer never overrides a higher one. If something a Human asks for would require violating the Constitution, the correct behavior for either AI is to say so plainly rather than comply silently. Dynamic Rules extend the Constitution; they can never contradict it. Project Invariants are project-specific and never get promoted directly into the universal Dynamic Rules — only genuinely reusable lessons get promoted, and only after a real evidence trail.

---

## 4. The Constitution — permanent engineering principles

`constitution.md`, currently at v1.2.0 in content-parity terms (its actual rule content hasn't changed since v1.0.1; only cross-file version-number bumps have touched it). It is organized in two parts:

**Part 1 — Foundation.** Preamble, Purpose, Scope, Authority Hierarchy (same as §3 above), Guiding Philosophy, six numbered Engineering Philosophy principles (EP-001 through EP-006 — see below), a three-level Rule Classification system (Level A = Mandatory, Level B = Required Engineering Practice, Level C = Recommended Practice), formal Definitions for terms like Evidence, Verification, Fabrication, Contract, Stop Condition, and Provenance, and six Constitutional Principles (CP-001 through CP-006) that summarize the whole document's spirit in one line each.

**Section 2 onward — 59 numbered universal rules, C01 through C59** (C01–C50 since early versions; C51–C54, Scientific Validity, added v1.4.0; C55–C59, Two-Role Discipline And Fail-Closed Assurance, added v2.2.0), each with an Enforcement Level (A/B/C) and cross-references to related rules. These cover everything from "never fabricate anything" (C01, the single most load-bearing rule in the whole system) through research integrity, repository hygiene, documentation discipline, evidence handling, scientific validity (§7 of `constitution.md` — a project is complete when its methodology would survive adversarial peer review, not when all contracts pass), the two-role architecture and fail-closed assurance (§8 — declared assurance may exceed but never undercut what Gatekeeper can mechanically infer as a minimum), and the Factory's own self-governance (how the Factory itself is allowed to evolve — C40 through C50).

The six Engineering Philosophy principles, because they explain *why* the Factory is shaped the way it is:
- **EP-001 — Minimize Decisions.** Every decision an AI has to make in the moment is a place fabrication or error can creep in. Push decisions earlier (into planning) or eliminate them (into deterministic checks) wherever possible.
- **EP-002 — Determinism Over Interpretation.** If something can be checked mechanically instead of judged by an AI, it must be. This is the entire reason Gatekeeper exists and the entire reason `dropbox_manifest.json` (§8) uses exact patterns instead of an AI guessing where a file goes.
- **EP-003 — Complexity Must Earn Its Place.** Nothing gets added because it's clever. It has to solve a real, demonstrated problem.
- **EP-004 — The Factory Is Software.** The Factory itself is versioned, tested, and evolved the same disciplined way the projects it produces are — no special exemption for its own rules.
- **EP-005 — Evidence Drives Evolution.** The Factory does not change because an idea sounds good. It changes because a completed project produced evidence that something didn't work.
- **EP-006 — Reproducibility Is a Feature.** The same inputs should produce comparable, checkable outputs — this is why so much of the pipeline insists on raw evidence, exact commands, and literal output rather than paraphrased summaries.

Selected individual rules worth knowing by number, because they get referenced constantly throughout the rest of the system: **C01 (Never Fabricate)** — the foundational rule; nothing may be claimed without evidence produced in that session. **C03 (the Architect Owns Decisions)** — the Architect, not the Implementor, makes architectural calls. **C06 (Stop Conditions Are Absolute)** — if a contract's Stop Condition is triggered, work halts; it is never pushed through. **C07 (Deterministic Verification First)** — prefer a script's judgment over an AI's whenever a script can do the job. **C22/C23/C24 (Repository Integrity / Boundaries / Secrets)** — the physical and security discipline around the codebase itself. **C40–C50** — the rules governing how the Factory changes itself, including the versioning policy described in §11 below.

---

## 5. The Factory Specification — concrete mechanics

`factory_spec.md`, v1.2.0. This is where the Constitution's principles become actual file formats and procedures.

### 5.1 Repository shape

```
factory/          reusable infrastructure — constitution.md, factory_spec.md, dynamic_rules.md,
                   gatekeeper_spec.md, gatekeeper.py, bootstrap_manifest.yaml, CHANGELOG.md, VERSION,
                   architect_spec.md, implementor_spec.md, domain_checklists.md (v2.2.0 — ML/
                   topology-geometry/statistics review questions, reference only)
project/           this specific project's artifacts
  project_description.md, architecture.md, roadmap.md, project_knowledge.md, invariants.md
  RELEASE_CERTIFICATION.md   (v2.2.0 — written by `gatekeeper.py release-certify`, once, at actual
                   submission readiness; never per-chunk)
  chunks/
    chunkNN/
      chunkNN.md                 the chunk plan
      execution_manifest.yaml    machine-readable contract list + dependency order for this chunk
      contracts/                 one file per contract
      reports/                   one subfolder per contract, containing that contract's report
      notes/, scripts/           supporting material, owned by the Implementor
      chunk_report.md            compiled summary of the whole chunk, written at chunk end
  evolution/
    telemetry.jsonl, decision_log.md
source/            the actual implementation — real code
DROP_HERE/         a gitignored inbox folder — see §8
```

### 5.2 Project Initialization

Happens once, at the very start of a project. The Architect produces five founding documents from the Human's raw project description or notes:

- **project_description.md** — Executive Summary, Motivation, Objectives (functional / non-functional / research), Scope (included / excluded / future work), numbered Functional Requirements (FR-001 style), Non-Functional Requirements, Constraints (hardware, compute budget, time budget, dependencies, licenses), and Success Criteria that are all measurable ("Accuracy ≥ 95%, reproducible across 3 runs with identical seeds" — never "good performance").
- **architecture.md** — System Overview, Architectural Principles, Component breakdown (one responsibility per component, no exceptions), External Dependencies with version constraints and justification, Interfaces, Data Flow, Error Boundaries, Future Extension Points.
- **roadmap.md** — Chunks defined as architectural milestones, never calendar weeks. Each chunk gets an Objective, Deliverables, Dependencies on earlier chunks, Estimated complexity, and Success criteria. Chunks are ordered so each produces independently verifiable value.
- **project_knowledge.md** — Glossary, Domain Knowledge, Dataset provenance/licensing/limitations if applicable, Standards/References, and stable Assumptions.
- **invariants.md** — things that must never become false for the life of the project. Each entry gets an ID, Description, Reason, Verification Method, and Failure Impact.

The Architect checks these five documents against each other for contradictions before considering the step done — this is a one-time investment that every later chunk inherits, so it's worth doing carefully.

### 5.3 The Chunk and the Contract

A **chunk** is a batch of related work — an architectural milestone from the roadmap. A chunk contains one or more **contracts**, which are the actual atomic unit of execution. A contract specifies, exhaustively: Contract ID, Objective, Context, Dependencies on other contracts, **Risk Tier**, **Implementation Owner**, **Allowed Files** (the only files the Implementor may touch), **Frozen Files** (files that must not change at all, verified by hash), Inputs, Outputs, Implementation Instructions, Verification Scripts (the actual automated tests that decide pass/fail), an Invariant Checklist, Predicted Failure Modes, a Definition of Done (broken into individually checkable items), and a Stop Condition (an explicit trigger that means "halt and report, do not push through").

**Risk Tier** is assigned by the Architect based on what the contract actually touches, not how large it feels:
- **High** — decision thresholds, shared mutable state, cryptographic/authentication logic, anything a Frozen File's invariant depends on, or anything where a subtle error would be expensive to catch later. High-tier contracts are implemented by the Architect directly, in the same session as planning — never delegated.
- **Medium** — real logic with recoverable stakes. Goes to the Implementor.
- **Low** — mechanical, easily-reviewed work. Goes to the Implementor, and if an entire chunk is all-Low with no Frozen File or invariant involvement, it can be marked a **Lightweight Chunk** — this only lets two of the four execution phases (§5.5) combine into one document and makes some logging optional; it never skips verification or review.

**Human Action Required** is a special contract flag for dependencies no AI can resolve — training on hardware the Implementor doesn't have access to, obtaining an API key, anything physical. The contract specifies an exact `Action` (literal commands/paths, never vague) and `Blocks` (which later contracts need the result). The Implementor stops cleanly on exactly that one contract, reports what's needed, and — per the dependency graph — keeps working on anything else in the chunk that doesn't depend on it. It never fakes a substitute result.

### 5.4 The Execution Manifest

`execution_manifest.yaml`, one per chunk. Machine-readable: chunk ID, Factory version, weight (standard/lightweight), the full list of contracts with their id/risk_tier/implementation_owner/depends_on/allowed_files/frozen_files/verification_scripts/required_reports, an explicit `execution_order` (a precomputed dependency-respecting sequence — Gatekeeper reads this rather than computing dependency resolution itself), and repository preconditions. This file is what lets Gatekeeper's `next` command deterministically say "here's what to work on" without any AI reasoning involved.

### 5.5 The Execution Pipeline — Phases 1 through 4

Every contract, once assigned to the Implementor, goes through four phases in one continuous autonomous session:

- **Phase 1 — Planning.** No implementation happens here. A mandatory Comprehension Gate first (restate the Objective, Allowed/Frozen Files, Stop Conditions, and a checkable breakdown of the Definition of Done — verbatim, not paraphrased). Then repository understanding, context validation against the actual codebase, dependency analysis, a risk assessment table, a review of each Predicted Failure Mode, a verification strategy, an implementation strategy broken into small checkpoints, and a review of Stop Conditions and Definition of Done items. Ends in a gate: `READY FOR IMPLEMENTATION` (proceed) or `NOT READY` (stop completely — a genuine planning ambiguity should wait for human/Architect review, not be guessed past).

- **Phase 2 — Implementation.** Executes checkpoint by checkpoint. Before touching any file: is it in Allowed Files? Each checkpoint reports the literal change made, the literal verification command and its complete unedited output, and an explicit self-check on whether anything outside Allowed Files was touched. Refactoring outside scope, unrelated "while I'm here" fixes, undeclared new dependencies, and weakening a test to make it pass are all explicitly banned in this phase. Ends in a gate: `IMPLEMENTATION COMPLETE` (proceed) or `IMPLEMENTATION BLOCKED` (a genuine Stop Condition).

- **Phase 3 — Self Review.** The Implementor switches roles mentally and tries to find every real reason to reject its own just-finished work — re-reading the contract fresh, running Gatekeeper's deterministic checks, auditing Allowed/Frozen File compliance, auditing every Definition of Done item against actual evidence (never "looks correct"), re-running every Verification Script fresh (not reusing Phase 2's cached output), auditing Invariants, Predicted Failure Modes, and Stop Conditions, and a final implementation-quality pass for dead code, duplication, or placeholder logic. This has a hard **five-attempt ceiling per contract**: attempts 1–2 loop back to Phase 2 normally on failure; attempts 3–4 switch to a deliberately more conservative implementation strategy (simpler-and-verifiably-correct over elegant-and-still-failing); if attempt 5 still fails, the loop stops entirely and the contract is marked either `COMPLETE — FLAGGED` (an honest partial pass exists — document exactly what's short) or `BLOCKED — CARRIED FORWARD` (no honest pass exists at all — document every attempt). **A Verification Script is never weakened or skipped to force a pass, at any attempt number** — a fabricated `COMPLETE` is explicitly worse than an honest `FLAGGED` or `BLOCKED`.

- **Phase 4 — Reporting.** Produces `contract_report.md`, written to be fully self-contained — Objective and Definition of Done items quoted verbatim, not referenced — so a reader with no other file open can still understand exactly what happened. Includes Files Modified, per-script Verification Summary, Definition of Done audit with evidence, Invariant Status, Predicted Failure Mode outcomes, Self Review attempt history, Final Status, Remaining Risks, Repository State, and a short Plain-Language Summary for a non-technical reader.

**Human Usage Model:** the Human (and by extension the Architect) is only involved at exactly two points per chunk — the start (planning) and the end (Chunk Review). The Implementor is never waiting on a mid-chunk check-in that isn't coming; this is why the five-attempt Self Review ceiling exists as an autonomous fallback rather than an escalation path.

### 5.6 Chunk Review

Happens once per chunk, after every contract has a Final Status. The Architect reads the compiled `chunk_report.md` and every individual `contract_report.md`, but — critically — also inspects the **raw diffs and raw verification output** for every Medium and High tier contract, not just what the self-authored reports claim. This raw-artifact inspection is described repeatedly throughout the system as "the one independent check left in the whole pipeline" — if it's skipped, nothing else catches a self-report that's subtly wrong. The Architect specifically looks for: mismatches between a report's claims and the actual diff, contracts with multiple Self Review attempts that might indicate the conservative fallback papered over something worth flagging more prominently, verification passes that fit the letter of a test but not its intent, and Risk Tiers that look mis-assigned in hindsight.

The outcome is either **APPROVED** or **FIX PACKAGE**. A Fix Package (Affected Contracts, Findings with evidence, Required Changes, Acceptance Criteria, Verification Required) is never executed as a separate round-trip — its required changes become the *first* contracts of the next chunk. Small issues too minor for a full Fix Package go into `AI_Note.md` — an append-only log of patterns worth the Implementor knowing about going forward.

### 5.7 Evolution logging

Every contract execution appends to `project/evolution/telemetry.jsonl` (structured, machine-readable: timestamp, chunk, contract, risk tier, phase, event, status, self-review attempt count) and, for non-trivial decisions, `project/evolution/decision_log.md` (prose: decision, reason, alternative considered, expected effect). This is what eventually feeds a **Factory Retrospective** — a separate, one-time, project-end conversation (not part of the per-chunk loop) that reviews everything in `evolution/` to decide what, if anything, should be promoted into Dynamic Rules for future projects.

---

## 6. Dynamic Rules — the Factory's evidence-based memory

`dynamic_rules.md`, currently accumulating evidence across two completed real projects (RateLimiter, TeamNotes). This file is where the Factory accumulates proven lessons *across* projects, as distinct from the Constitution's permanent universal principles. (v1.3.4 correction — this section previously said no project had completed and no rule had been promoted; as of v1.3.3 eight Dynamic Rules are filed PROPOSED, D-001's promotion criteria are illustrated as a schema example in `factory_spec.md` rather than as a live entry, and no rule has yet cleared the full Promotion Pipeline to `ACTIVE` on this Factory's own evidence — that specific claim was already accurate, the surrounding "no project completed" framing was not.)

Every rule belongs to exactly one category: **G**ate (a deterministic validation that could be automated), **V**erification (improves correctness checking), **W**orkflow (execution efficiency), **P**reservation (protects engineering knowledge), or **R**eporting (improves report quality). Every rule has a status: `ACTIVE` (enforced now), `PROPOSED` (evidence exists, not yet approved), `DEPRECATED` (no longer recommended, kept for history), or `SUPERSEDED` (replaced, with a reference to what replaced it). Rules are never deleted — only their status changes — because historical knowledge about what didn't work is considered valuable in itself.

Promotion to `ACTIVE` follows a strict pipeline: Observation → Repeated occurrence → Evidence collected → Root cause identified → Candidate rule written → Applied experimentally → Improvement confirmed → Human approval → Promotion. No stage may be skipped, and a rule with insufficient evidence stays `PROPOSED` indefinitely rather than being promoted on the strength of a good argument alone. This is the concrete mechanism behind EP-005 (Evidence Drives Evolution).

<!-- Possible v1.3.5 candidates (not yet proposed): dynamic_rules.md's Candidate Observations
     Awaiting Evidence table, below the numbered D-XXX registry, holds unpromoted findings --
     including a "Possible v1.3.5 candidates" subsection covering a cross-project precedent
     ledger, an adversarial pre-decision pass at Chunk Review, and an automated risk-surface scan,
     each with its own mechanism, grounding, and honest limitations written out in full there. All
     three are self-gated on completing at least one more real project first. See that table for
     the complete list and each item's specific reason it isn't in this version yet. -->

---

## 7. Gatekeeper — what's actually implemented vs. what's designed

`gatekeeper_spec.md` describes the full intended Gatekeeper, including its own current Implementation Status section, exit-code table, and command-by-command evidence posture — that document, not this one, is the authoritative, current source for exactly what `gatekeeper.py` does and does not check. This section used to duplicate that list here; the duplication is itself why this section had drifted several versions behind by v1.4.2 (see this file's own now-superseded header notes through that release). Removed per C46/EP-003 rather than re-synced yet again into a second copy that will only drift again.

What's stable enough to state here directly, since it's a standing design commitment rather than a version-specific detail: `gatekeeper.py` implements a real, growing, but partial subset of `gatekeeper_spec.md`'s full design — currently 20 commands, spanning Frozen File/Report/Repository validation, dropbox sorting, `next`'s execution-order lookup, `materialize`, `commit-project`, `self-check`, `release-check`, `acquisition-audit`, `evidence-check`, the v1.4.2 Mandatory Mechanical Gate (`verify-contract`/`lint-contract`/`recompute`/`stamp-report`/`verify-stamps`), and, as of v2.2.0, `tier-check` (Fail-Closed Tier Inference, D-034) and `release-certify` (aggregate CERTIFIED/NOT CERTIFIED gate, D-038). The gap between what's specified and what's implemented is always disclosed explicitly, never glossed over — claiming a Gatekeeper "PASS" for a check the script doesn't actually run is itself treated as a C01 fabrication violation, and `gatekeeper.py` prints exactly which checks it ran in every invocation for exactly this reason. Gatekeeper is philosophically restricted to checking **facts, never interpretations** — "file exists," "hash matches," "exit code equals zero," and, as of v2.2.0, "does this text match a known pattern" are in scope; "architecture is good," "this operator is mathematically correct" are explicitly out of scope forever, by design, regardless of future implementation progress — which is exactly why `domain_checklists.md` (v2.2.0) exists as human/Architect/Implementor guidance rather than an attempted mechanical check of something mechanical checking can't actually establish.

---

## 8. The Dropbox system — how files move between the two AI workspaces

Because the Architect (claude.ai, browser) and the Implementor (an IDE-like agentic environment) share a repository but never share a conversation, something has to physically carry files between them. That's the Human's job, made close to effortless by two things working together:

**`DROP_HERE/`** — a gitignored inbox folder, created once at bootstrap. The Human drops any file here without sorting it into the project's real structure first.

**`dropbox_manifest.json`** — also created once at bootstrap, and living inside `DROP_HERE/` itself. It is a **permanent file**, never regenerated, with two parts:
- **`rules`** — fixed regex patterns, seeded by the bootstrap script, covering every predictable artifact type the naming convention (§9) defines: chunk plans, execution manifests, contract files, contract reports, chunk reports, fix packages, and the five project-init documents. A rule looks like `{"pattern": "^C(\\d+)-(\\d+)_contract\\.md$", "destination": "project/chunks/chunk{1}/contracts/C{1}-{2}_contract.md"}` — capture groups substitute directly into the destination path. This section is Factory infrastructure; neither AI needs to edit it.
- **`entries`** — exact-filename mappings for one-off, project-specific handoffs a fixed pattern can't anticipate: a dataset, a credential file, anything produced outside the Factory. The Architect appends to this list during chunk planning whenever a contract's stated Inputs imply the Human will need to hand something over physically.

`gatekeeper.py sort-dropbox` performs the actual filing: checks `entries` (exact match) first, then `rules` (pattern match, first match wins), refuses to silently overwrite an existing destination file without an explicit `--force`, and — critically — **leaves anything matching neither in place and reports it**, rather than ever guessing. This is deliberate: EP-002/C07 (determinism over interpretation) means a wrong guessed file placement is treated as worse than an honest "I don't know where this goes."

---

## 9. The naming convention — how automatic filing is possible at all

Because nothing gets sorted by content-sniffing or AI judgment, every artifact either AI produces follows an exact, predictable filename:

| Artifact | Filename | Auto-filed to |
|---|---|---|
| Chunk plan | `chunkNN.md` | `project/chunks/chunkNN/chunkNN.md` |
| Execution manifest | `execution_manifest_chunkNN.yaml` | `project/chunks/chunkNN/execution_manifest.yaml` |
| Contract | `C{NN}-{seq}_contract.md` | `project/chunks/chunkNN/contracts/C{NN}-{seq}_contract.md` |
| Contract report | `C{NN}-{seq}_contract_report.md` | `project/chunks/chunkNN/reports/C{NN}-{seq}/contract_report.md` |
| Chunk report | `chunkNN_report.md` | `project/chunks/chunkNN/chunk_report.md` |
| Fix package | `fix_package_chunkNN.md` | `project/chunks/chunkNN/fix_package.md` |
| Project-init docs | `project_description.md`, `architecture.md`, `roadmap.md`, `project_knowledge.md`, `invariants.md` | `project/<same name>` (fixed, one-time, no chunk number) |

**Chunk numbers are always zero-padded to 2 digits** (`chunk01`, never `chunk1`) and **contract IDs follow `C{chunk}-{sequence}`** with the same zero-padding on the chunk portion (`C01-01`, `C03-07`). `sort-dropbox` normalizes the chunk-number capture group to 2-digit padding automatically regardless of how it was typed in a dropped filename, specifically so `chunk1.md` and `chunk01.md` can never resolve to two different directories for what should be the same chunk.

---

## 10. The two onboarding documents — the entire human-facing interface

There is no per-contract or per-chunk prompt file anywhere in this system. Everything the Factory used to require pasting into a prompt has been consolidated into exactly two permanent documents, each read once and then relied on for an entire session or entire project:

**`architect_spec.md`** (v2.2.0 primary name; `ClaudeInitialization.md` remains as a short pointer to it, kept only so an old bootstrap run or habit doesn't hit a missing file — see `CHANGELOG.md`'s v2.2.0 entry) — attached once, alongside `project_description.md` or raw project notes, at the start of a fresh Architect (Claude) chat session. It explains the Architect's role, the authority hierarchy, the full repository shape and naming conventions, the entire project-initialization → chunk-planning → chunk-review cycle in detail, and the Architect's specific responsibility for keeping `dropbox_manifest.json`'s `entries` section accurate and for the Methodology Adversarial Review self-review pass (§5.2, v2.2.0 — no separate Auditor to hand this to). After reading it once, the Human can speak entirely informally: "give me chunk 3," "here are the reports, give me chunk 4."

**`implementor_spec.md`** (v2.0.0 primary name, unchanged in this release; `gemini_spec.md` remains as the same kind of pointer file) — read once per session by the Implementor. It explains the role, the six non-negotiable rules (never fabricate, only touch Allowed Files, stop immediately on a High-tier contract, never fake a Human-Action-Required dependency, no test is the same thing as being right, log continuously), how to auto-discover its own next task from the repository and `gatekeeper.py next` with zero typed input, the full Phase 1–4 execution procedure verbatim (nothing loosened in the consolidation, and, as of v2.2.0, a tier-sanity check folded into Phase 1), the five-attempt Self Review ceiling, and a **Mailbox Protocol** recognizing generic trigger phrases — "check the mailbox," "chunk 3 is here, do it," "do the next one," "compile the chunk report" — as standing instructions rather than needing a fresh pasted prompt each time.

This is the single biggest practical difference between the original Factory design and the current one: the Human's job shrank from "locate and fill in the right prompt template for this exact moment" to "attach two documents once, then talk normally." v2.2.0 kept this property deliberately, having forked away from a parallel line that had grown to three role documents (`architect_spec.md`, `implementor_spec.md`, `auditor_spec.md`) plus roughly a dozen more supplementary reference documents a project targeting a peer-reviewed venue was expected to also read.

---

## 11. Versioning — how the Factory changes itself

Governed by C50 and elaborated in `CHANGELOG.md`. The Factory evolves only through evidence, never because an idea sounds good in isolation — this applies to the Factory's own structure exactly as strictly as it applies to any project built with it.

- **Patch releases** (`v1.1.x`) — bug fixes, wording improvements, clarifications, documentation. Never architectural changes.
- **Minor releases** (`v1.x`) — evidence-backed workflow improvements. Normally require at least one completed project, measurable evidence, and retrospective review.
- **Major releases** (`vX.0`) — architectural redesign; may replace workflows or components.

Every release entry answers: what changed, why, what evidence justified it, and whether it's backward compatible. **Honesty about the evidence gate is treated as more important than satisfying it** — several early releases shipped without a completed real-world project behind them, and every one of those CHANGELOG entries says so explicitly rather than burying the gap; v2.2.0 does the same for its own evidence posture (§12) rather than presenting a Human-directed architectural fork as though it had cleared the usual completed-project bar.

**Backward compatibility** is preserved whenever practical; when it can't be, the break is documented rather than silently introduced. v2.2.0 is additive to v1.4.2 specifically (§12) — nothing under a v1.4.2 `project/` needs migration to adopt it.

---

## 12. History so far, briefly

- **v1.0.0 / v1.0.1** — initial architecture: Constitution, Factory Spec, Dynamic Rules, contract-based workflow, bootstrap process, Gatekeeper specification.
- **v1.1.0** — `gatekeeper.py` became a real partial implementation instead of spec-only; Risk Tier and Implementation Owner fields formalized; Architecture Amendment and Lightweight Chunk Designation introduced; several internal contradictions between files fixed.
- **v1.1.1** — corrected a wrong assumption that the Architect would be reachable mid-chunk; introduced the autonomous graceful-degradation Self Review ceiling that's still in use.
- **v1.1.2** — `gatekeeper.py` gained `snapshot-chunk` and `next`; formalized report file path conventions.
- **v1.1.3** — introduced `DROP_HERE/` and the first version of dropbox sorting and a Mailbox Protocol trigger phrase.
- **v1.1.4** — introduced a first consolidated Architect onboarding document (superseded almost immediately by v1.2.0's fuller version).
- **v1.2.0** — the entire per-contract, per-chunk prompt-file workflow was retired outright. Two permanent onboarding documents replaced six separate prompt files. `dropbox_manifest.json` became a permanent bootstrapped file with pattern-based rules instead of something regenerated per chunk. A strict filename convention was introduced so the Implementor can auto-discover its own work with zero typed input from the Human. Explicitly scoped to touch nothing about verification rigor, Risk Tier assignment, or the Phase 1–4 pipeline.
- **v1.2.1** — `TAKE_THIS/` introduced: the reverse of `DROP_HERE/`, where the Implementor stages a completed chunk's self-contained reports for the Human, cleared automatically when the next chunk starts.
- **v1.3.0** — the Factory's first release backed by a real completed project (RateLimiter, a deliberate 2-chunk C++17 mechanics test). Added `gatekeeper.py materialize`, Verification Parameters, an adversarial concurrency test requirement for High-tier contracts, `Traces To` traceability, Architect-side telemetry/decision logging, `technical_debt.md`, and a real bug fix in `check`'s report-path resolution. First real use of the Dynamic Rules promotion pipeline (D-002 through D-005).
- **v1.3.1** — a second completed project (TeamNotes, full-stack Express/React/Docker), confirming every v1.3.0 fix held on a differently-shaped project while surfacing two new findings (D-006, D-007). Confirmed multi-file Frozen File sets and the "Doc Sync" invariant pattern as validated, reusable patterns.
- **v1.3.2** — Project Repository Isolation: `project/` became its own independent, nested git repository, gitignored from the outer repo, with full real git history of its own.
- **v1.3.3** — Architect onboarding tightened: a six-check founding-artifacts cross-check table, a Risk Tier tie-breaker, and two new, unpiloted practices (a mandatory High Risk pre-resolution pass, optional Evidence Tiers T0–T3) filed `PROPOSED` (D-008, D-009) with explicitly zero supporting occurrences.
- **v1.3.4** — bug-fix release: parser scope, contract-ID padding, report-header matching, dropbox directory visibility, composite-failure reporting, repo-root resolution, ten documentation corrections, and a new diagnostic-only `gatekeeper.py self-check` subcommand.
- **v1.4.0** — Scientific Validity Layer, evidenced by one completed project (GLOF — glacial lake outburst flood detection, an IEEE TGRS submission). Added Constitution Section 7 (C51–C54), the T-DESC/T-COMP/T-CAUSAL Scientific Claim Tier table, Methodology Adversarial Review (MAR), Reality Gate, `venue_requirements.md`/`key_facts.md`, and `gatekeeper.py release-check`/`acquisition-audit`.
- **v1.4.1** — `gatekeeper.py evidence-check` (D-024, D-025, D-027): a contract report's declared verdict cross-checked against its own backing JSON artifact, evidenced by a second distinct incident within the same GLOF rework.
- **v1.4.2**, plus a dated amendment — `verify-contract`/`lint-contract`/`recompute`/`stamp-report`/`verify-stamps`, and the Mandatory Mechanical Gate making all four mechanically required for T-COMP/T-CAUSAL contracts (D-032, D-033).
- **v1.5.0 → v2.0.0 → v2.1.0** (a parallel line, not this lineage's direct continuation) — grew a third AI role (Auditor) and, across three releases, roughly thirty registry/manifest file kinds, three parallel schema/template generations, and a `gatekeeper.py` command surface that reached roughly 64 commands across 52 exit codes. Real, evidence-backed lessons came out of this line (see v2.2.0, below) but the operator-facing cost grew faster than this Factory's own EP-003/C46 would normally permit going unchallenged — by v2.1.0, this line's own uploaded test-project set had no completed test project at all, the concrete symptom that triggered v2.2.0.
- **v2.2.0** — forks back to v1.4.2's two-role architecture at explicit Human direction, carrying forward the v1.5.0→v2.1.0 line's genuinely evidence-backed lessons in deliberately smaller form: `gatekeeper.py tier-check` (Fail-Closed Tier Inference, D-034 — motivated by a real contract in that line's own uploaded TDLCR test project declaring `Scientific Claim Tier: NONE` while computing a Wilcoxon test and Cliff's delta for its core hypotheses) plus three bundled WARNING heuristics (D-035–D-037), `gatekeeper.py release-certify` (D-038), `domain_checklists.md`, and new Constitution Section 8 (C55–C59). Removes the Auditor role and the registry family entirely — their function, where worth keeping, is folded into mechanisms the Architect and Gatekeeper already had. Honestly recorded as a Human-directed architectural fork built ahead of this Factory's usual completed-project evidence bar, not a claim that this structure has itself completed a project yet. See `CHANGELOG.md`'s v2.2.0 entry for the full account, including what was deliberately not carried forward and why.
- **v2.3.0** — ceremony-collapse and completion-integrity release from four independent completed-project field reports (Sentinel-GL, KLStream, an AML/collusion-ring project, CoreMesh). Six new `gatekeeper.py` commands (`contract-preflight`, `begin`, `finalize`, `delegate`, `log-decision`, `release-status`, D-039 through D-053) and Constitution C60/C61. This entry was not written when v2.3.0 shipped — added here at v2.4.0, alongside that entry, rather than left as a silent gap in this file's own History section. See `CHANGELOG.md`'s v2.3.0 entry for the full account; this document's §5/§6 internal mechanics were not re-synced for either v2.3.0 or v2.4.0 (see this file's header note).
- **v2.4.0** — dispositions a single repo-grounded third-party gap analysis comparing this Factory against an external elite-IEEE/Nature-venue pre-submission audit manual, independently re-verified claim-by-claim rather than accepted on its own framing (a second, ungrounded document reviewed alongside it was excluded entirely). Adds six reference-only sections to `domain_checklists.md`/`venue_requirements_TEMPLATE.md` (hardware/efficiency claims, ablation design, generalization/stress-testing, sample-size planning, a baseline parity ledger, release documentation — all conditional, no gate change) and two new WARNING-only `tier-check` heuristics (D-054, D-055), plus two candidate Reality-Gate-adjacent schemas (D-056, D-057) and one release-documentation requirement (D-058) — all filed PROPOSED, none promoted to ACTIVE, and the source document's own drafted Constitution rule ("C62") deliberately not ratified, per the Amendment Policy's cross-project evidence bar. See `CHANGELOG.md`'s v2.4.0 entry for the full account.
- **v2.4.1** — closes the five remaining Tier-A reference-content items `factory_gap_analysis.md`'s own §7 disposition table named as not yet seen by v2.4.0 (sensitivity-analysis protocol specificity, variance-characterization completeness, theory-adjacent standards, and baseline-parity/ablation-design sub-items) across `domain_checklists.md` and `venue_requirements_TEMPLATE.md`. All five items filed as pure reference content, with no new `gatekeeper.py` command or rule number, matching v2.4.0's own treatment of its reference additions. See `CHANGELOG.md`'s v2.4.1 entry for the full account.
- **v2.5.0** — publication rigor mechanical enforcement release. Ratifies Constitution Section 10 (C62 Ablation Single-Factor Isolation, C63 Pre-Registration & Experiment Freeze, C64 Empirical Measurement Over Point Proxies). Promotes D-054 through D-058 to ACTIVE; ratifies D-059 (Baseline Parity Audit), D-060 (Seed-Lottery Firewall), and D-061 (Benchmark Contamination Audit). Implements 5 new deterministic `gatekeeper.py` subcommands (`verify-baseline-parity`, `verify-hardware-profile`, `freeze-experiment`, `verify-experiment-freeze`, `contamination-check`, exit codes 23–26). Eliminates same-session self-review on MAR Gates 4–7 for peer-reviewed venues via cross-model adversarial audit protocol. Adds `test_gatekeeper_v2_5_0.py` (186 total tests passing). See `CHANGELOG.md`'s v2.5.0 entry for the full account.
- **v2.6.0 (current)** — comprehensive academic rigor release. Full mechanical operationalization of DEEP-RESEARCH.MD standards. Ratifies Constitution Section 11 (C65 Statistical Test Selection, C66 Effect Sizes, C67 Negative Controls, C68 Fixed-HP vs. Retuned Ablations, C69 Failure Analysis as Evidence). Ratifies dynamic rules D-062 through D-073. Implements 4 new deterministic `gatekeeper.py` subcommands (`verify-statistical-protocol`, `verify-sensitivity-analysis`, `pre-submission-audit`, `verify-failure-taxonomy`, exit codes 27–30). Extends `verify-hardware-profile` (exit 24) with claim-gated physical energy, thermal throttling headroom, and FLOPs accounting. Adds 7 protocol sections to `venue_requirements_TEMPLATE.md` (decision trees, perturbation grids, Pareto frontiers, LLM declaration, calibration, failure taxonomy, venue-specific checklists for NeurIPS/CVPR/Nature MI/IEEE). Adds `test_gatekeeper_v2_6_0.py` (213 total tests passing). See `CHANGELOG.md`'s v2.6.0 entry.

---

## 13. What this Factory is not

It is not a fully autonomous system — a Human is still required at chunk boundaries, for approval, and for anything requiring judgment, credentials, or physical action. It is not a system that trusts AI self-reports at face value — the entire Gatekeeper/raw-artifact-review apparatus exists because self-reports are explicitly not sufficient on their own, a discipline that has already caught real issues (a false-positive diff, an under-specified formal proof, a contract report contradicting its own backing artifact, a scientific claim self-declared as making none) across the real projects run through it so far (RateLimiter, TeamNotes, GLOF). It is not finished — Gatekeeper implements a real but partial subset of its intended scope. It is not a static thing — it is versioned, self-critical software: real projects have each produced evaluated, partly-accepted-and-partly-declined proposals for how the Factory itself should change, with every accepted change traceable to a specific named finding rather than a hypothetical one, and even its own major architectural decisions (v2.2.0's two-role fork) are recorded honestly as directed rather than independently earned where that's the truth of it. It is not a system where more roles or more process automatically mean more safety — v2.2.0 exists specifically because a heavier, three-role version of this same lineage still missed a real, concrete instance of the exact failure it was built to catch.
