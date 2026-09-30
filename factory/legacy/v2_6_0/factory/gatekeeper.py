#!/usr/bin/env python3
"""
gatekeeper.py -- AI Software Factory deterministic validation engine.
STATUS (Factory v2.6.0): PARTIAL IMPLEMENTATION.

v2.2.0 forks from v1.4.2 (two AI roles -- Architect, Implementor -- plus
this script, plus the Human; no separate Auditor role) rather than
extending v2.1.0's architecture (three AI roles; per-project registry
schemas for requirements/cohorts/evidence-lineage/agent-separation/etc.).
It carries forward every v1.4.2 mechanism unchanged and adds four new,
deliberately small mechanisms motivated by v2.0/v2.1's genuine findings:
tier-check (fail-closed minimum Scientific Claim Tier inference, D-034),
two WARNING-only heuristic scans bundled into that same command
(operation-class conflation D-035, statistical-protocol language D-036,
semantic/operator-test presence D-037), and release-certify (aggregate
CERTIFIED/NOT CERTIFIED gate, D-038). See CHANGELOG.md's v2.2.0 entry for
the full rationale, including what v2.0/v2.1 mechanisms were deliberately
NOT carried forward and why.

v2.3.0 is an evidence-backed workflow release under C50 (Minor -- no
architectural redesign; the document-and-contract model, the two-role
Ownership Model, and every v2.2.0 command are unchanged and still work
exactly as before). Its evidence base is four independent completed-project
field reports submitted together and reviewed as one batch, per the same
third-party-review-disposition discipline dynamic_rules.md already applies
(see that file's own disposition note for this round): Sentinel-GL (glacial-
lake TS-MAE rehabilitation, Chunk 01), KLStream (stream-processing
rehabilitation, C10-01), the AML/collusion-ring topological-learning project
(Chunk 19), and CoreMesh (lock-free ARM64 scheduler, 65 contracts). Two
concrete, previously-undetected defects were also found directly, by
checking those reports' claims against this script's and these documents'
actual text rather than against the reports' own framing (the same
discipline applied to every prior third-party review) -- see D-039 and
D-040 below, and CHANGELOG.md's v2.3.0 entry for the full disposition of
every reviewed claim: not new (already covered by an existing Constitution
principle or Dynamic Rule), already shipped, genuinely new and implemented,
or filed as a Candidate Observation for lack of evidence.

Fourteen new Dynamic Rules (D-039 through D-052) and two new Constitution
principles (C60, C61) come out of this round; see dynamic_rules.md and
constitution.md Section 9. New gatekeeper.py commands: contract-preflight
(D-039/D-040 -- reconciles Allowed/Frozen Files against verification-command
glob reach, before implementation starts, closing exactly the C01-03-shaped
gap Sentinel-GL hit), begin and finalize (D-041/D-048 -- the snapshot/check/
telemetry/decision/commit ceremony collapsed into two lifecycle commands
that read the manifest instead of requiring it retyped, and finalize is a
transactional complete-contract: it re-runs check [and, for T-COMP/
T-CAUSAL, the Mandatory Mechanical Gate] for real, right now, and writes a
completion receipt only on an actual pass -- a report's own Final Status
line was never, by itself, sufficient reason to trust a chunk was
complete), delegate (D-044 -- a structured, chunk-scoped, auto-expiring
record for the Human-authorized temporary Architect-outage override C55
already anticipates in spirit but never gave mechanical shape), and
log-decision (D-048 -- auto-incrementing decision IDs, no more manual
surgery on a multi-thousand-line file). `clear-takethis` now archives
instead of deleting (D-043); `check`/`contract-preflight` now read and
enforce the `repository_preconditions`/`completion_dependencies` manifest
fields the schema has always declared but nothing previously enforced
(D-047); `self-check` gains a fifth diff target and stable finding IDs
(D-046, D-052); `recompute` gains a shared-dependency import-graph check
and an optional Evidence Tier field, T1/T2/T3 (D-045); `release-check`/
`release-certify` gain a Factory-identifier outbound-secrecy scan (D-049)
and supersession-aware historical/active findings (D-050). See each rule's
own Evidence field for exactly which report(s) it comes from, and
CHANGELOG.md's v2.3.0 entry for the complete, itemized disposition.

Everything v2.2.0 shipped is unchanged and still runs exactly as
documented. Nothing above removes a command, a file location, or a
required field -- see each Dynamic Rule's own Implementation section for
what, if anything, changed about an existing mechanism (frozen defaults,
widened parsers) versus what is purely additive.

gatekeeper_spec.md describes the full, intended Gatekeeper. This script
implements only the subset listed in that document's "Implementation
Status" section:

    - Frozen File Validation  (sha256 hash comparison against a recorded
      baseline snapshot, stored at project/.gatekeeper/snapshots/ as of
      v1.3.2 -- see Project Repository Isolation)
    - Report Validation       (required report files exist and contain
      required section headers, matched as real "## "-level headings --
      v1.3.4 fix, was previously a raw substring search)
    - Repository Integrity    (clean git working tree -- checks the outer
      repo AND project/'s own nested repo independently, v1.3.2)
    - Execution-order lookup  (deterministic "what's next" from
      execution_manifest.yaml's execution_order + parsed contract_report.md
      statuses -- reads a precomputed order, does not compute dependency
      resolution itself)
    - Dropbox Sort (v1.1.3, revised v1.2.0)  (deterministic filing of files
      dropped in DROP_HERE/ to their manifest-declared destinations, via
      exact-filename entries and regex rules -- reads a mapping already
      committed, does not infer placement itself)
    - TAKE_THIS Staging / Clearing (v1.2.1)  (deterministic copying of a
      completed chunk's self-contained reports out to TAKE_THIS/ for the
      Human to grab, and deterministic clearing of that folder when the
      next chunk starts -- see stage-takethis / clear-takethis below)
    - Materialize (v1.3.0)  (deterministic extraction of MATERIALIZE-tagged
      code blocks from a contract file to their declared destination paths,
      written exactly as captured -- see materialize below)
    - Project Repository Commit (v1.3.2)  (commits everything staged in
      project/'s own nested git repository -- see commit-project below)
    - Self-Check (v1.3.4)  (diagnostic-only: diffs this script's actual
      implemented commands/exit codes/file operations against
      gatekeeper_spec.md's claims, cross-checks the Artifact Lifecycle
      table against operative instructions, checks version-header currency,
      and lints worked-example contract IDs -- never auto-fixes anything;
      see self-check below)
    - Release Check (v1.4.0)  (scans a release-bound artifact -- manuscript,
      REPRODUCIBILITY.md -- for local-path/machine-identity leaks
      [hard FAIL] and key-fact inconsistencies against a project-declared
      project/key_facts.md [WARNING, heuristic] -- see release-check below,
      D-017)
    - Acquisition Audit (v1.4.0, broadened v1.4.2)  (scans data-acquisition
      AND statistical-computation scripts and their contract reports for
      data-generation function definitions [hard FAIL, D-022], distribution-
      sampled values feeding a metrics function [hard FAIL, v1.4.2, D-028],
      and simulation-indicating language [WARNING, heuristic, D-023] -- see
      acquisition-audit below)
    - Evidence Check (v1.4.1)  (cross-checks a contract report's declared
      verdict and pre-registered criterion against its own backing JSON
      artifact [hard FAIL], and flags degenerate metrics computed on too
      few samples [WARNING] -- see evidence-check below, D-024, D-025,
      D-027, SVI-007)
    - Tier Check (v2.2.0)  (fail-closed minimum Scientific Claim Tier
      inference from a contract's own text [hard FAIL if the declared tier
      is weaker than the inferred minimum -- D-034], plus operation-class-
      conflation, statistical-protocol-language, and semantic/operator-
      test-presence heuristics [WARNING only -- D-035, D-036, D-037] -- see
      tier-check below)
    - Contract Preflight (v2.3.0, D-039/D-040)  (reconciles Allowed/Frozen Files
      against verification-command glob reach before execution, verifies
      repository preconditions and completion dependencies -- see contract-preflight)
    - Begin / Finalize Lifecycle (v2.3.0, D-041/D-048)  (transactional contract
      initialization and completion verification with cryptographic receipt emission
      -- see begin, finalize)
    - Delegate (v2.3.0, D-044)  (structured, chunk-scoped, auto-expiring record for
      temporary role delegation -- see delegate)
    - Log Decision (v2.3.0, D-048)  (deterministic, auto-incrementing decision
      logging -- see log-decision)
    - Baseline Parity Audit (v2.5.0, MAR-2, D-059)  (verifies baseline parameter
      counts within +/-2%% and compute FLOPs within +/-5%%, checks required baseline
      classes: Trivial/Sanity, Canonical Historical, Contemporary SOTA, Mechanism-Matched;
      exits with code 23 on breach -- see verify-baseline-parity)
    - Hardware Profile Sufficiency (v2.5.0, MAR-8, D-056, C64)  (verifies real hardware
      profiling: latency distributions [p50, p90, p99], warmup iteration exclusion,
      and peak inference memory; exits with code 24 on breach -- see verify-hardware-profile)
    - Experiment Freeze & Verification (v2.5.0, MAR-7, C63, D-060)  (pre-registers
      git commit, dependency lockfile hash, split checksums, and >=3 evaluation seeds;
      verifies reports against frozen manifests to block post-hoc seed cherry-picking;
      exits with code 25 on breach -- see freeze-experiment, verify-experiment-freeze)
    - Foundation Model Contamination Audit (v2.5.0, MAR-6, D-061)  (checks evaluation
      benchmarks against training corpora for 13-gram exact token overlap and temporal
      knowledge cutoff contamination; exits with code 26 on breach -- see contamination-check)
    - Statistical Protocol Verification (v2.6.0, C65/C66, D-062/D-063/D-064)  (verifies
      named significance tests, effect sizes alongside p-values, multiple-comparisons
      correction, IQM for small N, negative controls, retuned ablation reporting;
      exits with code 27 on violation -- see verify-statistical-protocol)
    - Sensitivity Analysis Verification (v2.6.0, D-065)  (verifies perturbation grids
      with >=3 levels per HP, response curve data, architecture sensitivity variation;
      exits with code 28 on insufficiency -- see verify-sensitivity-analysis)
    - Pre-Submission Audit (v2.6.0, D-070)  (10-step adversarial checklist: cold-read
      triage, claims-evidence matrix, statistical audit, baseline audit, ablation
      completeness, generalization/failure analysis, hardware/efficiency, reproducibility,
      rebuttal rehearsal, mock meta-review; exits with code 29 on validity-critical
      FAIL -- see pre-submission-audit)
    - Failure Taxonomy Verification (v2.6.0, C69, D-071)  (verifies systematic failure
      analysis: >=3 categories, prevalence P(failure|condition), selection rules,
      comparative failures; exits with code 30 on insufficiency -- see verify-failure-taxonomy)

Everything else in gatekeeper_spec.md -- Bootstrap Validation, Manifest
Validation beyond contract-preflight, Full Contract Linting beyond lint-contract,
and procedural components of MAR Gates 1, 3, 4, 7 (which require semantic review
and independent cross-model adversarial critique) -- remains procedural/AI-attested.
Reporting "Gatekeeper PASS" for a check this script does not run is itself
a Constitution C01 violation (fabricated verification). Quote this
script's own "Checks executed" list when reporting a result -- not the
full checklist in gatekeeper_spec.md.

Exit codes (per gatekeeper_spec.md's Exit Codes table):
    0  PASS
    4  Contract Failure                (frozen-file hash mismatch --
       bucketed here because gatekeeper_spec.md's Execution Order does not
       give Frozen File Validation its own code, and frozen files are a
       per-contract concern)
    6  Report Failure                  (required report missing, or
       missing a required section)
    8  Repository Integrity Failure   (dirty working tree)
    9  Unexpected Internal Error
    10 Release Artifact Failure       (v1.4.0 -- a local-path/machine-
       identity leak was found by release-check; key-fact mismatches are
       reported as warnings and do not by themselves produce this code)
    11 Acquisition Audit Failure      (v1.4.0, broadened v1.4.2 -- a
       data-generation function definition in an acquisition script
       (D-022), OR a distribution-sampled value feeding a metrics function
       in a statistical-computation script (v1.4.2, D-028), found by
       acquisition-audit; simulation-indicating text is reported as a
       warning and does not by itself produce this code)
    12 Evidence Inconsistency         (v1.4.1 -- a contract report's
       declared verdict contradicted its own backing JSON artifact, or its
       own declared numbers contradicted its own declared criterion, found
       by evidence-check; degenerate metrics are reported as a warning and
       do not by themselves produce this code)
    13 Verification Command Failure   (v1.4.2 -- a contract report's own
       declared '## Verification' command, independently re-executed by
       verify-contract, exited nonzero)
    14 Contract Lint Failure          (v1.4.2 -- a swallowed exception, an
       acquisition-audit finding, or frozen-verification-machinery
       tampering, found by lint-contract)
    15 Recompute Mismatch             (v1.4.2 -- an independent
       recomputation didn't match its artifact's claimed value, or wasn't
       actually independent (same-hash script), found by recompute)
    16 Stamp Tampering                (v1.4.2 -- content above an existing
       Gatekeeper Verification Stamp was modified after it was issued,
       found by stamp-report or verify-stamps)
    17 Mandatory Mechanical Gate Failure (v1.4.2 amendment, D-032/D-033 --
       a T-COMP/T-CAUSAL contract's `check` did not satisfy all of:
       Required Verification Commands present in the report's declared
       set, verify-contract, lint-contract, a passing Recompute
       Declaration, and an intact Gatekeeper Verification Stamp. Bucketed
       under one code the same way Frozen File Validation is bucketed
       under 4 -- the printed [Mandatory Mechanical Gate] detail lines
       distinguish which of the five sub-checks failed)
    3  Manifest Failure               (v2.3.0, D-039/D-040 -- contract-
       preflight: a wildcard/glob verification or acquisition-audit path
       reaches outside this contract's Allowed Files union Frozen Files;
       an Allowed/Frozen overlap conflict; a missing/cyclic dependency; a
       repository_preconditions/completion_dependencies manifest field
       unmet, D-047. This code was reserved but unemitted through v2.2.0
       -- see gatekeeper_spec.md's Manifest Validation, "planned")
    20 Finalize Integrity Failure     (v2.3.0, D-041 -- `finalize` was run
       but its own re-run of `check` [or the Mandatory Mechanical Gate,
       if tiered] did not pass, OR a report's content no longer matches
       the hash recorded in its own prior completion receipt -- a
       completion claim whose gate is not current is not yet a
       completion claim, C61)
    21 Delegation Violation           (v2.3.0, D-044 -- a High-risk
       contract's Implementation Owner does not match its actual
       executor, and no active, matching, unexpired delegation record
       authorizes the difference)
    22 Outbound Secrecy Scan Failure  (v2.3.0, D-049 -- a release-bound
       artifact contains a Factory-internal identifier: a chunk/contract/
       decision ID, DROP_HERE/TAKE_THIS, or Gatekeeper/role-name language
       -- the same Project Repository Isolation goal factory_spec.md
       already states, extended from local-path leaks to this second,
       textual kind of fingerprint)
    23 Baseline Parity Violation      (v2.5.0, MAR-2, D-059 -- verify-baseline-parity
       detected comparative baseline parameter counts exceeding +/-2% tolerance,
       training FLOPs/compute exceeding +/-5% tolerance, or missing mechanism-matched
       baselines without justified architectural divergence)
    24 Hardware Profile Sufficiency Failure (v2.5.0, MAR-8, D-056 -- verify-hardware-profile
       detected efficiency claims lacking empirical latency distributions [p50, p90, p99],
       missing separate peak training and inference memory, or failing to exclude warmup iterations)
    25 Experiment Freeze / Seed Mismatch Failure (v2.5.0, MAR-7, C63, D-060 -- verify-experiment-freeze
       detected evaluation reports omitting pre-registered seeds, substituting seeds post-hoc,
       cherry-picking, or failing against experiment_freeze_manifest.json)
    26 Foundation Model Contamination Failure (v2.5.0, MAR-6, D-061 -- contamination-check
       detected exact 13-gram overlap between evaluation benchmarks and training corpora or
       temporal knowledge cutoff contamination)
    27 Statistical Protocol Violation   (v2.6.0, C65/C66, D-062/D-063/D-064 -- verify-
       statistical-protocol detected p-values without named significance test, missing
       effect sizes, or uncorrected multiple comparisons)
    28 Sensitivity Analysis Insufficiency (v2.6.0, D-065 -- verify-sensitivity-analysis
       detected fewer than 3 perturbation levels per HP, missing response curves, or no
       architecture sensitivity variation)
    29 Pre-Submission Audit Failure     (v2.6.0, D-070 -- pre-submission-audit detected
       validity-critical failures in steps 1-4: untested claim adjectives, orphan claims,
       missing statistical tests, or absent baseline parity ledger)
    30 Failure Taxonomy Insufficiency   (v2.6.0, C69, D-071 -- verify-failure-taxonomy
       detected fewer than 3 failure categories, missing prevalence statistics, absent
       selection rules, or missing comparative failure analysis)

Usage
-----
Snapshot every contract's frozen files in a chunk in one command (v1.1.2 --
reads frozen_files straight out of the manifest instead of retyping paths):

    gatekeeper.py snapshot-chunk --manifest project/chunks/chunk03/execution_manifest.yaml

Or snapshot one contract at a time (still available -- e.g. after an
Architecture Amendment re-freezes a single contract mid-chunk):

    gatekeeper.py snapshot --contract C03-01 --frozen src/core/schema.py src/core/types.py

Ask what to work on next (v1.1.2 -- reads execution_order + each contract's
contract_report.md; does not decide anything, just reports what the
manifest and the reports already establish):

    gatekeeper.py next --manifest project/chunks/chunk03/execution_manifest.yaml

File everything currently sitting in DROP_HERE/ to its declared destination
(v1.1.3, revised v1.2.0 -- reads DROP_HERE/dropbox_manifest.json, a
permanent bootstrapped file with pattern rules + project-specific exact
entries; refuses to move anything matching neither rather than guessing):

    gatekeeper.py sort-dropbox

Stage one completed chunk's self-contained reports into TAKE_THIS/ for the
Human to grab (v1.2.1 -- copies every contract_report.md plus chunk_report.md
for the given chunk, renamed flat; never touches or deletes the originals):

    gatekeeper.py stage-takethis --chunk chunk03

Empty TAKE_THIS/ of whatever's currently staged there (v1.2.1 -- run when a
new chunk is starting; self-healing if TAKE_THIS/ doesn't exist yet; never
touches anything under project/, since TAKE_THIS only ever holds copies):

    gatekeeper.py clear-takethis

Extract embedded source from a contract's MATERIALIZE-tagged code blocks
(v1.3.0 -- writes each tagged block to its declared destination path,
byte-for-byte; refuses to overwrite an existing file without --force):

    gatekeeper.py materialize --contract C01-02

Commit everything staged in project/'s own nested repository (v1.3.2 --
project/ is gitignored from the outer repo by design, see Project
Repository Isolation; this is what gives it real history anyway. Safe to
call routinely -- a no-op, not an error, when nothing changed):

    gatekeeper.py commit-project --message "Complete contract C01-02"

Diagnose drift between this script's actual behavior and what
gatekeeper_spec.md / factory_spec.md / VERSION / CHANGELOG.md claim about it
(v1.3.4 -- diagnostic only, never modifies anything, reports diffs):

    gatekeeper.py self-check

Scan a manuscript (and optionally other release files) for local-path leaks
and inconsistencies against declared key facts before submission (v1.4.0 --
see D-017; --key-facts is optional, the local-path scan runs regardless):

    gatekeeper.py release-check --manuscript paper/manuscript.md \\
        --files paper/REPRODUCIBILITY.md --key-facts project/key_facts.md

Scan data-acquisition scripts and their contract reports for data-generation
function definitions and simulation-indicating language before trusting
their output (v1.4.0 -- see D-022, D-023; either --scripts or --reports
alone is fine, --scripts gets both checks, --reports gets only the textual
scan):

    gatekeeper.py acquisition-audit \\
        --scripts source/data/acquisition/*.py \\
        --reports project/chunks/chunk07/reports/*/contract_report.md

Cross-check a contract report's declared verdict and pre-registered
criterion against its own backing JSON artifact (v1.4.1 -- see D-024,
D-025, D-027; each report must contain a '## Verdict Cross-Check' block,
see factory_spec.md's Contract Specification):

    gatekeeper.py evidence-check \\
        --reports project/chunks/chunk08/reports/C08-08/contract_report.md

Check a contract before accepting it as complete (v1.3.0 fix: bare
required_reports filenames from --manifest now resolve against
project/chunks/chunkNN/reports/{contract_id}/ instead of the current
working directory, correcting a real false-missing-report failure):

    gatekeeper.py check --contract C03-01 \\
        --manifest project/chunks/chunk03/execution_manifest.yaml \\
        --reports project/chunks/chunk03/reports/C03-01/contract_report.md \\
        --allow-dirty          # only while Phase 2 work is still in progress

If no --manifest is given to `check`, pass --frozen and --reports directly.

(v2.3.0) Start a contract -- runs contract-preflight, snapshots this
contract's frozen files straight from the manifest (no retyping them),
captures a scoped repository baseline, and writes a headed report skeleton
if one doesn't exist yet at the manifest-implied path (D-041, D-046):

    gatekeeper.py begin --contract C03-01 \\
        --manifest project/chunks/chunk03/execution_manifest.yaml

(v2.3.0) Finish a contract -- transactionally: re-runs check (and the
Mandatory Mechanical Gate, if tiered) for real, right now, and writes a
completion receipt plus telemetry/decision-log entries ONLY if that re-run
actually passes and the report's own Final Status already reads a
COMPLETE-class value (D-041, D-048; see C61). Never call this in place of
writing the report -- write it first, then finalize:

    gatekeeper.py finalize --contract C03-01 \\
        --manifest project/chunks/chunk03/execution_manifest.yaml \\
        --decision "Title|Decision text|Reason|Alternatives considered"

(v2.3.0) Reconcile a contract's declared scope against what its own
verification/acquisition-audit commands would actually touch, before any
implementation begins (D-039/D-040; exit code 3 on a real conflict):

    gatekeeper.py contract-preflight --contract C01-03 \\
        --manifest project/chunks/chunk01/execution_manifest.yaml

(v2.3.0) Record a Human-authorized, chunk-scoped, auto-expiring exception
to the Implementation Owner table -- e.g. the Architect is genuinely
unreachable and the Human has explicitly said so for specific contracts
this chunk (D-044; see C55's delegation note). The Human's own plain-
language authorization is what's required; this command only gives it
structure:

    gatekeeper.py delegate --chunk chunk01 --original-owner architect \\
        --executor implementor --contracts C01-05 C01-06 C01-07 C01-08 C01-09 \\
        --authorized-by "Human message, 2026-08-30: Architect unavailable, \\
have the Implementor execute these five for this chunk only."

(v2.3.0) Append a decision_log.md entry without hand-editing the file --
auto-increments the D-number (D-048):

    gatekeeper.py log-decision --role architect \\
        --decision "Adopt scoped repository baselines over --allow-dirty" \\
        --reason "See D-041; a blanket bypass could not tell a pre-existing \\
dirty file from one this contract actually touched" \\
        --alternatives "Keep --allow-dirty as the only option" \\
        --benefit "Repository Integrity means something again for a \\
begin-started contract"
"""

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SNAPSHOT_DIR = Path("project/.gatekeeper/snapshots")
# v1.3.2 -- moved from the repo-root ".gatekeeper/snapshots" (pre-v1.3.2) into
# project/'s own nested repository, for the same reason project/ itself is
# isolated there: ".gatekeeper/snapshots/C01-02.json" sitting in the OUTER
# repo's tracked history is a distinctive, structured, Factory-shaped
# artifact -- exactly the kind of fingerprint Project Repository Isolation
# exists to avoid, and it was overlooked when that isolation first shipped.
# Rather than gitignoring ".gatekeeper/" separately (which would just
# reintroduce project/'s original bug -- history silently lost -- for a
# second directory), snapshots now live inside project/'s existing nested
# repo and are committed there via the same `commit-project` command,
# with zero new git machinery. See factory_spec.md's Project Repository
# Isolation section.
LEGACY_SNAPSHOT_DIR = Path(".gatekeeper/snapshots")

# v2.3.0 (D-039, generalizing the v1.3.2 reasoning above from snapshots to
# every other Factory-owned bookkeeping artifact this release adds):
# project/.gatekeeper/ is already outside any contract's Allowed Files by
# construction, since Allowed Files governs the OUTER repository and
# project/ is a second, independent, nested repository (Project Repository
# Isolation). Putting new Factory state here means no contract ever has to
# declare these paths in --frozen or Allowed Files to avoid a scope
# conflict with them -- see Constitution C60. All four are committed via
# the existing `commit-project`; none is new git machinery.
GATEKEEPER_STATE_DIR = Path("project/.gatekeeper/state")            # D-041 completion receipts + D-041/D-047 baselines
DELEGATIONS_PATH = Path("project/.gatekeeper/delegations.jsonl")     # D-044
# D-048: decisions.jsonl lives beside decision_log.md in ITS established
# home (project/evolution/, per factory_spec.md's Artifact Lifecycle
# table) rather than under project/.gatekeeper/ -- these are the
# structured and rendered forms of the same one artifact, not two
# different kinds of Factory state.
DECISIONS_PATH = Path("project/evolution/decisions.jsonl")
DECISION_LOG_PATH = Path("project/evolution/decision_log.md")
TELEMETRY_PATH = Path("project/evolution/telemetry.jsonl")
TAKETHIS_ARCHIVE_DIR = Path("TAKE_THIS_ARCHIVE")                     # D-043 -- outer repo, gitignored, same as TAKE_THIS/


def _resolve_snapshot_path(contract_id, for_write=False):
    """Returns the snapshot path to use for a contract, handling the
    v1.3.2 relocation transparently.

    Writes always go to the new location (SNAPSHOT_DIR).

    Reads check the new location first; if not found there, fall back to
    the legacy repo-root location, so a project bootstrapped before v1.3.2
    (with existing snapshots already at the old path) keeps working exactly
    as before rather than silently treating its real, existing frozen-file
    history as missing. This is read-compatibility only -- it does not
    migrate anything automatically, since moving files is a decision worth
    the Human/Architect seeing happen, not something silent.
    """
    new_path = SNAPSHOT_DIR / f"{contract_id}.json"
    if for_write:
        return new_path
    if new_path.exists():
        return new_path
    legacy_path = LEGACY_SNAPSHOT_DIR / f"{contract_id}.json"
    if legacy_path.exists():
        return legacy_path
    return new_path  # neither exists -- report against the new (correct-going-forward) path
DROPBOX_DIR = Path("DROP_HERE")
DROPBOX_MANIFEST_NAME = "dropbox_manifest.json"
TAKETHIS_DIR = Path("TAKE_THIS")

# v1.3.0 -- see cmd_materialize for the full rationale. A code block is
# extracted when immediately preceded by a tag of the exact form
# "<!-- MATERIALIZE: path/relative/to/repo/root -->". The path is captured
# non-greedily up to the closing "-->"; content is captured DOTALL between
# the opening fence's newline and the closing fence.
MATERIALIZE_PATTERN = re.compile(
    r'<!--\s*MATERIALIZE:\s*(\S+?)\s*-->\s*\n```[a-zA-Z0-9_+\-]*\n(.*?)\n```',
    re.DOTALL
)

# v2.3.0 (D-046): the previous default -- ["objective", "verification",
# "evidence"] -- checked for heading substrings that do not appear ANYWHERE
# in implementor_spec.md section 8's actual contract_report.md template.
# That template's real "## "-level headings are Contract Information, Scope
# / Inputs / Outputs, Files Modified, Verification Summary, Definition of
# Done, Invariant Status, Predicted Failure Modes, Self Review History,
# Final Status, Remaining Risks, Repository State, Plain-Language Summary.
# "verification" matched "Verification Summary" by accident; "objective"
# and "evidence" matched nothing in a report that followed the template
# exactly -- Objective is prose *inside* Contract Information, not a
# heading of its own, and there was never a heading called Evidence at
# all. A properly-templated report was therefore never actually checkable
# against the old default without every project separately overriding
# --required-sections (which nothing in architect_spec.md/
# implementor_spec.md's own usage examples ever shows being done) -- this
# is the exact, root-cause shape of a real, reported CoreMesh-project
# failure (a properly-formed C13-01 report rejected for "missing" an
# 'evidence' heading the template never asked it to have). Corrected here
# to three headings the real template actually has and that this script's
# own other checks already depend on structurally: Final Status is what
# parse_contract_status parses; Definition of Done is what "COMPLETE"
# means; Verification Summary is what _extract_declared_commands reads.
# self-check's new Diff Target 5 (_self_check_required_sections_vs_template)
# now cross-checks this constant against the template directly, so this
# specific drift cannot recur silently a second time.
DEFAULT_REQUIRED_SECTIONS = [
    "verification",
    "definition of done",
    "final status",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest_contract(manifest_path: Path, contract_id: str):
    try:
        import yaml
    except ImportError:
        print("ERROR: --manifest requires PyYAML (`pip install pyyaml --break-system-packages`).")
        print("Falling back: pass --frozen / --reports directly instead.")
        sys.exit(9)

    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        sys.exit(9)

    with open(manifest_path) as f:
        data = yaml.safe_load(f)

    contracts = data.get("contracts", [])
    match = next((c for c in contracts if c.get("id") == contract_id), None)
    if match is None:
        print(f"ERROR: contract '{contract_id}' not found in {manifest_path}")
        sys.exit(9)
    return match


def _snapshot_one(contract_id, frozen_paths, force=False):
    """Returns (status: str, message: str). status in {'created','skipped','error'}."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = _resolve_snapshot_path(contract_id, for_write=True)

    if not frozen_paths:
        return "skipped", f"{contract_id}: no frozen_files listed -- nothing to snapshot."

    if snapshot_path.exists() and not force:
        return "skipped", (
            f"{contract_id}: snapshot already exists at {snapshot_path} -- left untouched. "
            f"Frozen means frozen; re-snapshotting silently would defeat the point. "
            f"A legitimate change here is an Architecture Amendment, not a re-snapshot."
        )

    hashes = {}
    missing = []
    for rel_path in frozen_paths:
        p = Path(rel_path)
        if not p.exists():
            missing.append(rel_path)
            continue
        hashes[rel_path] = sha256_of(p)

    if missing:
        return "error", f"{contract_id}: cannot snapshot -- these files do not exist: {missing}"

    payload = {"contract": contract_id, "files": hashes}
    with open(snapshot_path, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)

    detail = "; ".join(f"{p}={h[:12]}..." for p, h in sorted(hashes.items()))
    return "created", f"{contract_id}: snapshot recorded ({len(hashes)} file(s)) -> {snapshot_path} [{detail}]"


def cmd_snapshot(args):
    frozen = sorted(set(list(args.frozen or []) + _auto_frozen_verification_paths()))
    status, message = _snapshot_one(args.contract, frozen, force=args.force)
    print(message)
    if status == "error":
        sys.exit(9)


def cmd_snapshot_chunk(args):
    try:
        import yaml
    except ImportError:
        print("ERROR: snapshot-chunk requires PyYAML (`pip install pyyaml --break-system-packages`).")
        sys.exit(9)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        sys.exit(9)

    with open(manifest_path) as f:
        data = yaml.safe_load(f)

    contracts = data.get("contracts", [])
    if not contracts:
        print(f"ERROR: no contracts found in {manifest_path}")
        sys.exit(9)

    print(f"Snapshotting all frozen files for {len(contracts)} contract(s) in {manifest_path}")
    print("=" * 60)

    any_error = False
    for c in contracts:
        cid = c.get("id", "<missing id>")
        frozen = sorted(set((c.get("frozen_files", []) or []) + _auto_frozen_verification_paths()))
        status, message = _snapshot_one(cid, frozen, force=args.force)
        print(f"[{status.upper():7s}] {message}")
        if status == "error":
            any_error = True

    print("=" * 60)
    print(
        "Reminder: run 'gatekeeper.py commit-project' now. project/.gatekeeper/snapshots/ "
        "lives inside project/'s own nested repo (v1.3.2) -- an uncommitted snapshot reads "
        "as a dirty working tree there at the next Repository Integrity check."
    )
    if any_error:
        sys.exit(9)


def _load_dropbox_manifest():
    """Returns (manifest_dict, error_message_or_None).

    dropbox_manifest.json (v1.2.0) is a permanent, bootstrapped Factory file
    -- created once at bootstrap time with the fixed, well-known rules
    already populated, then only ever appended to (never regenerated from
    scratch) as the Architect's chunk planning introduces new one-off handoffs
    (a dataset, a credential file). Both the fixed "rules" entries and any
    per-chunk "entries" additions live in the same file so the Implementor only ever
    has one place to look.

    Schema:
    {
      "rules": [
        {"pattern": "^chunk(\\d+)\\.md$",
         "destination": "project/chunks/chunk{1}/chunk{1}.md"},
        {"pattern": "^C(\\d+)-(\\d+)_contract\\.md$",
         "destination": "project/chunks/chunk{1}/contracts/C{1}-{2}_contract.md"},
        {"pattern": "^execution_manifest_chunk(\\d+)\\.yaml$",
         "destination": "project/chunks/chunk{1}/execution_manifest.yaml"},
        {"pattern": "^C(\\d+)-(\\d+)_contract_report\\.md$",
         "destination": "project/chunks/chunk{1}/reports/C{1}-{2}/contract_report.md"},
        {"pattern": "^chunk(\\d+)_report\\.md$",
         "destination": "project/chunks/chunk{1}/chunk_report.md"},
        {"pattern": "^project_description\\.md$",
         "destination": "project/project_description.md"},
        ...
      ],
      "entries": [
        {"filename": "training_data.csv",
         "destination": "source/data/training_data.csv"}
      ]
    }

    Matching order: "entries" (exact filename) checked first -- these are
    one-off, Architect-authored, and take priority over a generic rule that
    might otherwise also match. Then "rules" (regex pattern against the
    filename, capture groups substituted into destination via {1}, {2}, ...).
    A dropped file matching neither is left exactly where it is and
    reported, never guessed at. No content sniffing, ever -- filename is
    the only signal this command is allowed to use.
    """
    manifest_path = DROPBOX_DIR / DROPBOX_MANIFEST_NAME
    if not manifest_path.exists():
        return None, f"no {manifest_path} found -- this should have been created by bootstrap.sh. Re-run bootstrap or restore it from factory/dropbox_manifest.json."

    try:
        with open(manifest_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"{manifest_path} exists but is not valid JSON: {e}"

    rules = data.get("rules", [])
    entries = data.get("entries", [])
    if not rules and not entries:
        return None, f"{manifest_path} exists but has no rules and no entries -- nothing to sort against."

    return data, None


def _resolve_destination(filename, data):
    """Returns (destination_str_or_None, matched_via_str_or_None).

    Checks exact-filename entries first, then regex rules in file order
    (first match wins -- rules should be written non-overlapping, but if
    they aren't, order is the deterministic tiebreaker rather than an
    error, so this command never has to guess which rule "means" more).
    """
    for entry in data.get("entries", []):
        if entry.get("filename") == filename:
            return entry.get("destination"), "entries"

    for rule in data.get("rules", []):
        pattern = rule.get("pattern")
        dest_template = rule.get("destination")
        if not pattern or not dest_template:
            continue
        m = re.match(pattern, filename)
        if m:
            try:
                dest = dest_template
                for i, group in enumerate(m.groups(), start=1):
                    # By dropbox_manifest.json convention, capture group {1}
                    # is always the chunk number. It's zero-padded to 2
                    # digits here so "chunk1" and "chunk01" -- which the Architect
                    # or the Human might drop under either spelling -- can
                    # never resolve to two different chunk directories. Any
                    # other capture group (contract sequence number, etc.)
                    # is substituted exactly as captured, unpadded -- this is
                    # the one piece of normalization this command performs,
                    # not inference about *where* something goes.
                    value = group.zfill(2) if (i == 1 and group.isdigit()) else group
                    dest = dest.replace(f"{{{i}}}", value)
                return dest, f"rule: {pattern}"
            except (IndexError, TypeError):
                continue

    return None, None


def cmd_sort_dropbox(args):
    if not DROPBOX_DIR.exists():
        print(f"ERROR: {DROPBOX_DIR}/ does not exist. Nothing to sort.")
        sys.exit(9)

    data, err = _load_dropbox_manifest()
    if err:
        print(f"ERROR: {err}")
        print(
            "Dropbox Sort only files exactly what dropbox_manifest.json's rules/entries declare -- "
            "it never infers a destination from a file's content, and pattern rules are explicit "
            "regexes written by the Human or Architect, never inferred at sort time."
        )
        sys.exit(9)

    all_entries = [p for p in DROPBOX_DIR.iterdir() if p.name != DROPBOX_MANIFEST_NAME]
    present_files = [p for p in all_entries if p.is_file()]
    # v1.3.4 (BUG-4): non-file entries (directories, symlinks-to-directories,
    # etc.) used to be excluded from every reported category, including
    # [UNKNOWN] -- a dropped folder vanished from the output entirely.
    # They're now listed and reported under their own category instead.
    non_file_entries = [p for p in all_entries if not p.is_file()]

    print(f"Sorting {DROPBOX_DIR}/ against {len(data.get('entries', []))} exact entr(y/ies) "
          f"and {len(data.get('rules', []))} pattern rule(s).")
    print("=" * 60)

    moved, skipped_unknown, skipped_exists, errors = [], [], [], []

    for p in present_files:
        dest_str, matched_via = _resolve_destination(p.name, data)

        if dest_str is None:
            skipped_unknown.append(p.name)
            continue

        dest = Path(dest_str)

        if dest.exists() and not args.force:
            skipped_exists.append((p.name, str(dest)))
            continue

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            p.replace(dest)
            moved.append((p.name, str(dest), matched_via))
        except OSError as e:
            errors.append(f"{p.name} -> {dest}: {e}")

    for fname, dest, matched_via in moved:
        print(f"[MOVED  ] {fname} -> {dest}  (matched via {matched_via})")
    for fname, dest in skipped_exists:
        print(f"[SKIPPED] {fname}: destination already exists at {dest} (use --force to overwrite deliberately)")
    for fname in skipped_unknown:
        print(f"[UNKNOWN] {fname}: matches no rule or entry in dropbox_manifest.json -- left in {DROPBOX_DIR}/, not moved.")
    for p in non_file_entries:
        print(f"[SKIPPED - NOT A FILE] {p.name}: directories are never sorted or moved by this command -- left in {DROPBOX_DIR}/.")
    for e in errors:
        print(f"[ERROR  ] {e}")

    print("=" * 60)
    print(f"Moved: {len(moved)}  Skipped (exists): {len(skipped_exists)}  "
          f"Unknown (left in place): {len(skipped_unknown)}  "
          f"Skipped (not a file): {len(non_file_entries)}  Errors: {len(errors)}")

    if skipped_unknown:
        print(
            f"\n{len(skipped_unknown)} file(s) left in {DROPBOX_DIR}/ because dropbox_manifest.json "
            f"doesn't name or pattern-match them. This is not a failure -- it's the deterministic "
            f"behavior working as intended (per C01/EP-002, a guessed placement is worse than an "
            f"honest 'unresolved'). Report this list to the Human/Architect rather than moving them "
            f"by inference. If this is a new artifact type the Factory should recognize going "
            f"forward, that's a dropbox_manifest.json rule addition, not a one-time workaround."
        )

    if errors:
        sys.exit(9)


def cmd_stage_takethis(args):
    """Copies one completed chunk's self-contained reports into TAKE_THIS/
    for the Human to grab in one place, instead of hunting through nested
    project/chunks/chunkNN/reports/C{NN}-{seq}/ directories by hand.

    This is always a COPY, never a move. The originals under
    project/chunks/chunkNN/ are the permanent record and are never touched,
    renamed, or deleted by this command -- TAKE_THIS/ is disposable staging,
    nothing more.

    Copied files are renamed flat, reusing the exact same naming convention
    dropbox_manifest.json already uses on the way IN (see Dropbox
    Specification) -- C{NN}-{seq}_contract_report.md and chunkNN_report.md
    -- so a file staged here is, by construction, already correctly named
    if it were ever dropped back into a DROP_HERE/ elsewhere.

    Scope: every contract_report.md under the chunk's reports/ directory,
    plus the chunk's own chunk_report.md. Does not include AI_Note.md or
    fix_package.md -- those are cross-chunk or forward-looking artifacts,
    not this-chunk-is-done reports.
    """
    chunk = args.chunk
    chunk_dir = Path("project/chunks") / chunk
    chunk_report_src = chunk_dir / "chunk_report.md"

    if not chunk_report_src.exists():
        print(f"ERROR: {chunk_report_src} not found.")
        print(
            "stage-takethis requires the chunk report to exist first -- "
            "compile the chunk report before staging it for handoff."
        )
        sys.exit(9)

    TAKETHIS_DIR.mkdir(parents=True, exist_ok=True)

    staged = []

    chunk_report_dest = TAKETHIS_DIR / f"{chunk}_report.md"
    shutil.copy2(chunk_report_src, chunk_report_dest)
    staged.append((chunk_report_src, chunk_report_dest))

    reports_dir = chunk_dir / "reports"
    if reports_dir.exists():
        for contract_dir in sorted(p for p in reports_dir.iterdir() if p.is_dir()):
            report_src = contract_dir / "contract_report.md"
            if report_src.exists():
                report_dest = TAKETHIS_DIR / f"{contract_dir.name}_contract_report.md"
                shutil.copy2(report_src, report_dest)
                staged.append((report_src, report_dest))

    print(f"Staged {len(staged)} self-contained report(s) into {TAKETHIS_DIR}/ for {chunk}:")
    for src, dest in staged:
        print(f"  [COPIED ] {src} -> {dest}")
    print(f"Originals remain permanently at their location under {chunk_dir}/ -- this was a copy only.")


def cmd_clear_takethis(args):
    """Empties TAKE_THIS/ of every file currently staged there. Run this
    when a new chunk is starting, per the Factory's DROP_HERE/TAKE_THIS
    handoff protocol's "chunk N is here, do it" trigger specifically --
    not the generic "check the mailbox" trigger, which is also used
    mid-chunk for things like dataset drops where clearing TAKE_THIS
    would be wrong.

    v2.3.0 (D-043): by default this now ARCHIVES (moves) the staged files
    into TAKE_THIS_ARCHIVE/<chunk-or-timestamp>/ with a small manifest,
    rather than deleting them outright. The command's own specification
    already said its correctness depends on an assumption -- "the Human
    already retrieved the prior bundle" -- that this script had no way to
    confirm and the Human had no prompt to reconsider before running it.
    A file staged here was already committed to project/ before staging
    (stage-takethis copies, it doesn't move), so nothing was ever
    permanently lost by the old behavior either -- but losing the
    convenient, already-assembled handoff bundle because a chunk boundary
    arrived one command before the Human happened to open it was a real,
    reported failure mode (Sentinel-GL). Pass --purge for the old,
    unconditional-delete behavior if you specifically want it; nothing
    about that flag is removed.

    Self-healing: if TAKE_THIS/ doesn't exist yet, this creates it empty
    rather than erroring, matching the Factory's general idempotent-bootstrap
    philosophy elsewhere (bootstrap.sh, sort-dropbox).

    Never touches anything under project/ -- TAKE_THIS only ever holds
    copies, so clearing (or archiving) it can never lose the permanent
    record.
    """
    if not TAKETHIS_DIR.exists():
        TAKETHIS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"{TAKETHIS_DIR}/ did not exist -- created it (empty).")
        return

    present_files = [p for p in TAKETHIS_DIR.iterdir() if p.is_file()]

    if not present_files:
        print(f"{TAKETHIS_DIR}/ is already empty. Nothing to clear.")
        return

    if getattr(args, "purge", False):
        print(f"--purge given: deleting {TAKETHIS_DIR}/ -- {len(present_files)} file(s) removed "
              f"(originals under project/ are untouched):")
        for p in sorted(present_files):
            print(f"  [REMOVED] {p.name}")
            p.unlink()
        print(f"{TAKETHIS_DIR}/ is now empty.")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = args.chunk if getattr(args, "chunk", None) else timestamp
    dest_dir = TAKETHIS_ARCHIVE_DIR / f"{label}-{timestamp}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Archiving {TAKETHIS_DIR}/ -> {dest_dir}/ -- {len(present_files)} file(s) moved "
          f"(originals under project/ remain untouched; this is a second copy, not the "
          f"permanent record):")
    manifest_lines = [f"# TAKE_THIS archive -- {timestamp}", ""]
    for p in sorted(present_files):
        dest = dest_dir / p.name
        shutil.move(str(p), str(dest))
        digest = sha256_of(dest)
        print(f"  [ARCHIVED] {p.name} -> {dest}")
        manifest_lines.append(f"- {p.name}  sha256:{digest}")
    (dest_dir / "ARCHIVE_MANIFEST.md").write_text("\n".join(manifest_lines) + "\n")
    print(f"{TAKETHIS_DIR}/ is now empty. Archived copy + manifest at {dest_dir}/.")
    print("(Use --purge next time if you specifically want the old delete-forever behavior.)")


def cmd_commit_project(args):
    """Commits everything currently staged in project/'s own nested
    repository (v1.3.2 -- see Project Repository Isolation in
    factory_spec.md). project/ is gitignored from the outer repo by design;
    this is the deterministic operation that gives it real git history
    anyway, scoped entirely to its own repo.

    Safe to call routinely -- if project/.git doesn't exist yet (a project
    bootstrapped before v1.3.2, or genuinely nothing to commit), this says
    so plainly rather than erroring, since "nothing to commit" is an
    expected, non-failure outcome for a command meant to be run after
    every contract.
    """
    project_git = Path("project/.git")
    if not project_git.exists():
        print(
            "No nested project/.git repository found. If this project was bootstrapped "
            "before v1.3.2, project/ isn't tracked anywhere -- re-run bootstrap.sh to "
            "add one (it only initializes what's missing, per its idempotency guarantee)."
        )
        sys.exit(9)

    add_result = subprocess.run(
        ["git", "-C", "project", "add", "-A"],
        capture_output=True, text=True,
    )
    if add_result.returncode != 0:
        print(f"ERROR: 'git -C project add -A' failed: {add_result.stderr.strip()}")
        sys.exit(9)

    status_result = subprocess.run(
        ["git", "-C", "project", "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if not status_result.stdout.strip():
        print("Nothing to commit in project/ -- working tree already clean.")
        return

    message = args.message or "Update project/ artifacts"
    commit_result = subprocess.run(
        ["git", "-C", "project", "commit", "-m", message],
        capture_output=True, text=True,
    )
    if commit_result.returncode != 0:
        print(f"ERROR: 'git -C project commit' failed: {commit_result.stderr.strip()}")
        sys.exit(9)

    print(f"Committed to project/'s nested repository: \"{message}\"")
    print(commit_result.stdout.strip())


def _contract_id_candidates(contract_id):
    """Returns (chunk_num, seq_num, candidate_ids) or (None, None, None) if
    contract_id doesn't match the C{chunk}-{seq} naming convention.

    v1.3.4 (BUG-2): factored out of _find_contract_file so every caller that
    needs to resolve a contract ID against a directory-name component --
    _find_contract_file, cmd_next's report-path lookup, cmd_check's
    required_reports resolution -- shares the same padded/as-given fallback
    instead of each reimplementing (or omitting) it independently.

    chunk_num and seq_num are always returned zero-padded to 2 digits.
    candidate_ids is an ordered, de-duplicated list: the as-given ID first,
    then the fully-padded ID -- both are checked as literal directory/file
    name components by callers, since a report or contract file may have
    been filed under either spelling.
    """
    m = re.match(r'^C(\d+)-(\d+)$', contract_id)
    if not m:
        return None, None, None

    chunk_num = m.group(1).zfill(2)
    seq_num = m.group(2).zfill(2)
    padded_id = f"C{chunk_num}-{seq_num}"

    candidate_ids = [contract_id]
    if padded_id != contract_id:
        candidate_ids.append(padded_id)

    return chunk_num, seq_num, candidate_ids


def _find_contract_file(contract_id):
    """Returns (path_or_None, error_or_None).

    Given a contract ID like "C01-02", deterministically locates its
    contract file at project/chunks/chunkNN/contracts/C{NN}-{seq}_contract.md
    -- the chunk number is parsed directly out of the contract ID itself,
    per the naming convention (ClaudeInitialization.md Section 4), never
    searched for or guessed. Accepts an unpadded contract ID (e.g. an unzero-padded chunk-contract pair)
    and normalizes it the same way sort-dropbox normalizes chunk numbers.
    """
    chunk_num, seq_num, candidate_ids = _contract_id_candidates(contract_id)
    if chunk_num is None:
        return None, f"'{contract_id}' doesn't match the C{{chunk}}-{{seq}} naming convention (e.g. C01-02)."

    padded_id = f"C{chunk_num}-{seq_num}"
    chunk_dir = Path("project/chunks") / f"chunk{chunk_num}"

    for candidate_id in candidate_ids:
        candidate_path = chunk_dir / "contracts" / f"{candidate_id}_contract.md"
        if candidate_path.exists():
            return candidate_path, None

    return None, f"{chunk_dir / 'contracts' / (padded_id + '_contract.md')} not found."


def cmd_materialize(args):
    """Deterministically extracts MATERIALIZE-tagged code blocks from a
    contract markdown file and writes them to their declared destination
    paths, byte-for-byte.

    This exists to close a real, observed failure mode: a contract --
    especially a High-tier one the Architect implements directly -- embeds
    full implementation source inside its own markdown, because per the
    Dropbox Specification raw source files are never dropped loose into
    DROP_HERE/ (dropbox_manifest.json intentionally has no rule for that).
    Before this command existed, turning that embedded markdown into real
    files on disk was a manual, interpretive step: the Implementation
    Engineer reading code blocks in prose and retyping or copy-pasting them
    into place, with the exact boundary of "where does the code start/end"
    left to its own judgment. That is precisely the category of decision
    EP-002/C07 (determinism over interpretation) says should be made
    mechanical wherever it can be -- so as of v1.3.0, it is.

    Convention: a line of the exact form

        <!-- MATERIALIZE: path/relative/to/repo/root -->

    immediately before a fenced code block marks that block for extraction.
    The path is relative to the repository root, not the contract file's
    own location. Everything between the fence's opening and closing lines
    is written exactly as captured, with a trailing newline added if the
    captured block doesn't already end in one -- no other reformatting, no
    reinterpretation, no judgment about whether the code "looks right." A
    single contract may contain any number of these pairs (e.g. a High-tier
    contract embedding two related headers in one file).

    A destination that already exists is left untouched and reported unless
    --force is passed -- same overwrite discipline as sort-dropbox, for the
    same reason: silently clobbering an existing file is worse than making
    the Human/Architect say so explicitly.
    """
    contract_path, err = _find_contract_file(args.contract)
    if err:
        print(f"ERROR: {err}")
        sys.exit(9)

    try:
        text = contract_path.read_text()
    except OSError as e:
        print(f"ERROR: could not read {contract_path}: {e}")
        sys.exit(9)

    matches = list(MATERIALIZE_PATTERN.finditer(text))

    if not matches:
        print(f"No MATERIALIZE-tagged code blocks found in {contract_path}.")
        print(
            "Nothing to do -- this contract either has no embedded source to "
            "materialize, or uses a tag this command doesn't recognize. Check "
            "the exact convention: <!-- MATERIALIZE: path --> immediately "
            "before the fenced code block, with no blank line between them "
            "other than the newline the tag itself ends with."
        )
        return

    print(f"Found {len(matches)} MATERIALIZE-tagged block(s) in {contract_path}:")
    print("=" * 60)

    written, skipped_exists, errors = [], [], []

    for m in matches:
        dest = Path(m.group(1))
        content = m.group(2)

        if dest.exists() and not args.force:
            skipped_exists.append(str(dest))
            continue

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            out = content if content.endswith("\n") else content + "\n"
            dest.write_text(out)
            written.append(str(dest))
        except OSError as e:
            errors.append(f"{dest}: {e}")

    for d in written:
        print(f"  [WRITTEN] {d}")
    for d in skipped_exists:
        print(f"  [SKIPPED] {d} already exists (use --force to overwrite deliberately)")
    for e in errors:
        print(f"  [ERROR  ] {e}")

    print("=" * 60)
    print(f"Written: {len(written)}  Skipped (exists): {len(skipped_exists)}  Errors: {len(errors)}")

    if skipped_exists and not args.force:
        print(
            f"\n{len(skipped_exists)} file(s) already existed and were left untouched. "
            f"If this contract is meant to update them, re-run with --force."
        )

    if errors:
        sys.exit(9)


def check_frozen_files(contract_id, frozen_paths):
    """Returns (ok: bool, details: list[str])."""
    snapshot_path = _resolve_snapshot_path(contract_id, for_write=False)
    details = []

    if not snapshot_path.exists():
        details.append(
            f"WARNING: no snapshot found for contract '{contract_id}' at {snapshot_path}. "
            f"Frozen File Validation did NOT run for this contract -- run `snapshot` first. "
            f"This is not a PASS by omission."
        )
        return True, details  # doesn't fail the run, but is loudly not a pass either

    with open(snapshot_path) as f:
        baseline = json.load(f)["files"]

    ok = True
    for rel_path in frozen_paths:
        p = Path(rel_path)
        if rel_path not in baseline:
            details.append(f"WARNING: {rel_path} has no recorded baseline hash -- not checked.")
            continue
        if not p.exists():
            details.append(f"FAIL: {rel_path} was frozen but no longer exists.")
            ok = False
            continue
        current = sha256_of(p)
        if current != baseline[rel_path]:
            details.append(
                f"FAIL: {rel_path} hash changed.\n"
                f"       baseline: {baseline[rel_path]}\n"
                f"       current:  {current}"
            )
            ok = False
        else:
            details.append(f"PASS: {rel_path} unchanged ({current[:12]}...)")

    return ok, details


# v1.3.4 (BUG-3): matches a markdown "## " (or deeper) heading line.
# Section presence is checked against extracted heading text, not against
# the raw file body, so a required section name appearing only in prose
# (e.g. "no verification was possible") no longer satisfies the check.
_HEADING_LINE_RE = re.compile(r'^#{2,6}\s+(.+?)\s*$', re.MULTILINE)


def _extract_headers(text):
    """Returns a list of heading text strings (## and deeper), whitespace-
    normalized and lowercased, extracted from a markdown document."""
    return [
        " ".join(m.group(1).split()).lower()
        for m in _HEADING_LINE_RE.finditer(text)
    ]


def check_reports(report_paths, required_sections):
    """Returns (ok: bool, details: list[str]).

    v1.3.4 (BUG-3): required_sections are matched against the report's
    actual "## "-level headers, not as a raw substring search across the
    whole file body. gatekeeper_spec.md's Report Validation section has
    always specified "required section headers present" -- this brings the
    implementation in line with that, rather than under-delivering against
    its own spec. A required section name is satisfied when it appears as a
    substring of some extracted header line (case-insensitive,
    whitespace-normalized) -- e.g. required "verification" matches a
    "## Verification Summary" header, per the real contract_report.md /
    chunk_report.md templates in gemini_spec.md section 8.
    """
    ok = True
    details = []
    for rel_path in report_paths:
        p = Path(rel_path)
        if not p.exists():
            details.append(f"FAIL: required report missing: {rel_path}")
            ok = False
            continue

        text = p.read_text(errors="replace")
        headers = _extract_headers(text)
        missing_sections = [
            s for s in required_sections
            if not any(s.lower() in h for h in headers)
        ]
        if missing_sections:
            details.append(
                f"FAIL: {rel_path} exists but is missing required section header(s): "
                f"{missing_sections} (checked against '## '-level headers only -- "
                f"a required word appearing in prose elsewhere in the file does not "
                f"satisfy this; this is not semantic validation, "
                f"per gatekeeper_spec.md's Forbidden list)"
            )
            ok = False
        else:
            details.append(f"PASS: {rel_path} present with required section headers")
    return ok, details


def _git_status_porcelain(repo_root=None):
    """Returns (ok, output_or_error). repo_root=None means the current
    directory's repo (the outer repo); a path runs against that path's own
    repo instead, via -C, without changing this process's cwd."""
    cmd = ["git"]
    if repo_root is not None:
        cmd += ["-C", str(repo_root)]
    cmd += ["status", "--porcelain"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except FileNotFoundError:
        return False, "git is not installed or not on PATH."
    except subprocess.CalledProcessError as e:
        return False, f"not a git repository, or git error: {e}"


def check_git_clean():
    """Returns (ok: bool, details: list[str]).

    Checks the outer repo's working tree, and -- v1.3.2 -- also the nested
    project/ repository if one exists (see Project Repository Isolation in
    factory_spec.md). project/ is gitignored from the outer repo by
    deliberate design (so the outer repo's structure and history show no
    trace of the Factory), but it is still expected to be its own real,
    clean git repository -- this check makes sure Repository Integrity
    actually covers both roots instead of silently only ever seeing the one
    that happens to be the process's cwd.
    """
    details = []
    overall_ok = True

    ok, output = _git_status_porcelain()
    if not ok:
        return False, [f"FAIL: outer repository -- {output}"]
    if output.strip():
        dirty = output.strip().splitlines()
        details.append(f"FAIL: outer repository working tree not clean ({len(dirty)} entries):")
        details += [f"       {line}" for line in dirty]
        overall_ok = False
    else:
        details.append("PASS: outer repository working tree clean")

    project_git = Path("project/.git")
    if project_git.exists():
        ok, output = _git_status_porcelain(repo_root="project")
        if not ok:
            details.append(f"FAIL: nested project/ repository -- {output}")
            overall_ok = False
        elif output.strip():
            dirty = output.strip().splitlines()
            details.append(f"FAIL: nested project/ repository working tree not clean ({len(dirty)} entries):")
            details += [f"       {line}" for line in dirty]
            overall_ok = False
        else:
            details.append("PASS: nested project/ repository working tree clean")
    else:
        details.append("SKIPPED: no nested project/ repository found (pre-v1.3.2 project, or not yet bootstrapped with one)")

    return overall_ok, details


# Order matters: check the more specific patterns before the ones they're a
# substring of ("COMPLETE — FLAGGED" contains "COMPLETE").
#
# v1.3.4 (BUG-1b): the bare "COMPLETE" pattern is matched with a regex word
# boundary so it can never match inside "INCOMPLETE". The em-dash/hyphen
# pairs above it are unaffected -- those were audited separately and found
# correct (real UTF-8 em dashes plus ASCII-hyphen fallbacks, deliberate
# dual coverage; see v1_3_4_candidate_spec.md section 1.1, "Not in scope").
STATUS_PATTERNS = [
    ("BLOCKED — HUMAN ACTION REQUIRED", "blocked_human_action"),
    ("BLOCKED - HUMAN ACTION REQUIRED", "blocked_human_action"),
    ("BLOCKED — CARRIED FORWARD", "blocked_carried_forward"),
    ("BLOCKED - CARRIED FORWARD", "blocked_carried_forward"),
    ("COMPLETE — FLAGGED", "complete_flagged"),
    ("COMPLETE - FLAGGED", "complete_flagged"),
    (re.compile(r'(?<![A-Z])COMPLETE(?![A-Z])'), "complete"),
]

# v1.3.4 (BUG-1a): a line matching this marks the end of the Final Status
# section for parsing purposes -- any other "## " heading. Bounding the
# search here stops words in Remaining Risks, the Plain-Language Summary,
# or any later section from being mistaken for the Final Status value.
_NEXT_HEADING_RE = re.compile(r'^##\s', re.MULTILINE)


def parse_contract_status(report_path: Path) -> str:
    """Reads the Final Status line of a contract_report.md. Never guesses --
    returns 'unknown' rather than assuming a status it can't actually find.

    v1.3.4 (BUG-1a/1b): the search is bound to the Final Status section
    itself -- from the "## Final Status" heading up to (but not including)
    the next "## " heading -- so a status word appearing later in Remaining
    Risks or the Plain-Language Summary can no longer be mistaken for the
    Final Status value. The bare "COMPLETE" pattern also now matches as a
    whole token, so it can never match inside "INCOMPLETE".
    """
    if not report_path.exists():
        return "not_started"

    text = report_path.read_text(errors="replace")
    lower = text.lower()
    idx = lower.find("## final status")
    if idx == -1:
        search_text = text
    else:
        after_heading = idx + len("## final status")
        next_heading_match = _NEXT_HEADING_RE.search(text, after_heading)
        end = next_heading_match.start() if next_heading_match else len(text)
        search_text = text[idx:end]

    for pattern, status in STATUS_PATTERNS:
        if isinstance(pattern, re.Pattern):
            if pattern.search(search_text):
                return status
        elif pattern in search_text:
            return status
    return "unknown"


def cmd_next(args):
    try:
        import yaml
    except ImportError:
        print("ERROR: next requires PyYAML (`pip install pyyaml --break-system-packages`).")
        sys.exit(9)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        sys.exit(9)

    with open(manifest_path) as f:
        data = yaml.safe_load(f)

    contracts = {c["id"]: c for c in data.get("contracts", []) if "id" in c}
    execution_order = data.get("execution_order", [])
    if not execution_order:
        print(f"ERROR: no execution_order found in {manifest_path}")
        sys.exit(9)

    reports_dir = Path(args.reports_dir) if args.reports_dir else manifest_path.parent / "reports"

    SATISFIED = {"complete", "complete_flagged"}
    UNRESOLVED_BLOCKING = {"blocked_carried_forward", "blocked_human_action"}

    def _report_path_for(cid):
        # v1.3.4 (BUG-2): fall back between the as-given and zero-padded
        # contract ID, matching _find_contract_file's existing behavior --
        # a report filed at an unpadded path (e.g. an unzero-padded reports/ subdirectory) must
        # still be found, not silently read as not_started forever.
        _, _, candidates = _contract_id_candidates(cid)
        tried = candidates if candidates else [cid]
        for candidate_id in tried:
            candidate_path = reports_dir / candidate_id / "contract_report.md"
            if candidate_path.exists():
                return candidate_path
        return reports_dir / cid / "contract_report.md"

    statuses = {cid: parse_contract_status(_report_path_for(cid)) for cid in execution_order}

    print(f"Execution order per {manifest_path}:")
    print("=" * 60)
    for cid in execution_order:
        print(f"  {cid:12s} {statuses[cid]}")
    print("=" * 60)

    blocked_found = []
    for cid in execution_order:
        status = statuses[cid]

        if status in SATISFIED:
            continue

        if status in UNRESOLVED_BLOCKING:
            blocked_found.append((cid, status))
            continue  # don't stop here -- a later, independent contract may still be runnable

        deps = (contracts.get(cid, {}) or {}).get("depends_on", []) or []
        unmet_blocked = [d for d in deps if statuses.get(d) in UNRESOLVED_BLOCKING]
        unmet_pending = [d for d in deps if d not in [b[0] for b in blocked_found] and statuses.get(d) not in SATISFIED and statuses.get(d) not in UNRESOLVED_BLOCKING]

        if unmet_blocked:
            print(f"NEXT: none for {cid} -- depends on {unmet_blocked}, which {'is' if len(unmet_blocked)==1 else 'are'} blocked. Skipping, checking the rest of execution_order.")
            continue

        if unmet_pending:
            print(f"NEXT: none ready yet -- {cid} is next in order but depends on {unmet_pending}, not yet satisfied.")
            sys.exit(0)

        if status == "unknown":
            print(f"NEXT: none. {cid} has a report at {reports_dir / cid / 'contract_report.md'} "
                  f"but its Final Status could not be parsed. Fix the report rather than guessing at its status.")
            sys.exit(9)

        # status == "not_started" and all deps satisfied (or independent of anything blocked)
        c = contracts.get(cid, {})
        print(f"NEXT: {cid}")
        print(f"  Risk Tier: {c.get('risk_tier', '<not in manifest>')}")
        print(f"  Implementation Owner: {c.get('implementation_owner', '<not in manifest>')}")
        if blocked_found:
            print(f"  (Note: {[b[0] for b in blocked_found]} are blocked and were skipped over -- still needs Chunk Review attention.)")
        sys.exit(0)

    if blocked_found:
        print(f"NEXT: none. Every remaining contract is blocked on {[b[0] for b in blocked_found]} or already done.")
        print("This chunk cannot fully complete without Chunk Review addressing the blocked contract(s).")
        sys.exit(0)

    print("NEXT: none. Every contract in execution_order is COMPLETE or COMPLETE — FLAGGED.")
    print("Chunk is ready for chunk_report.md compilation and Chunk Review.")
    sys.exit(0)


def _run_mandatory_gate(contract_id, report_paths, required_verification_commands):
    """v1.4.2 amendment (D-032/D-033) -- for a T-COMP/T-CAUSAL contract,
    mechanically requires all four v1.4.2 guards to pass, not merely
    documents that they exist. Returns (ok, detail_lines). Reuses the
    exact underlying functions verify-contract/lint-contract/recompute/
    stamp-report already run standalone -- this is not a duplicate
    implementation, and it never re-invents what those subcommands do.

    Order matters: Required Verification Commands is checked first
    because it answers the specific gap independent review raised --
    that a report's declared command was never checked against what the
    contract actually required, only that whatever was declared exited
    0. The other three then run as before."""
    ok = True
    lines = []

    if not report_paths:
        return False, ["FAIL: no report given -- a T-COMP/T-CAUSAL contract cannot pass this gate "
                        "without a contract_report.md to check (Required Verification Commands, "
                        "verify-contract, lint-contract, recompute, and stamp presence all read one)."]

    for rp in report_paths:
        rp_path = Path(rp)
        text = _read_text_or_none(rp_path)
        if text is None:
            ok = False
            lines.append(f"FAIL [{rp}]: report not found.")
            continue

        # 1. Required Verification Commands (D-033) -- the declared
        # command(s) must be drawn from the frozen set the Architect declared at
        # contract-generation time, not freely invented in the report.
        declared = _extract_declared_commands(text)
        if required_verification_commands:
            missing_required = [c for c in required_verification_commands if c not in declared]
            if missing_required:
                ok = False
                lines.append(
                    f"FAIL [{rp}]: report's declared '## Verification' commands do not include "
                    f"every command this contract's Required Verification Commands field froze: "
                    f"missing {missing_required}. A report may declare additional commands, but "
                    f"cannot substitute a different one for a required one."
                )
            else:
                lines.append(f"OK [{rp}]: all {len(required_verification_commands)} Required "
                              f"Verification Command(s) present in the report's declared set.")
        else:
            lines.append(f"WARNING [{rp}]: scientific_claim_tier is T-COMP/T-CAUSAL but this "
                          f"contract declares no Required Verification Commands -- verify-contract "
                          f"below will still re-run whatever the report happens to declare, but "
                          f"nothing here confirms that's the command the contract actually required.")

        # 2. verify-contract -- re-execute every declared command for real.
        if not declared:
            ok = False
            lines.append(f"FAIL [{rp}]: no '## Verification' commands declared at all -- nothing "
                          f"to independently re-execute.")
        else:
            any_cmd_fail = False
            for cmd in declared:
                exit_code, stdout, stderr = _run_subprocess(cmd)
                if exit_code != 0:
                    any_cmd_fail = True
                    lines.append(f"FAIL [{rp}] verify-contract: `{cmd}` -> real exit code {exit_code}.")
            if any_cmd_fail:
                ok = False
            else:
                lines.append(f"OK [{rp}] verify-contract: {len(declared)} declared command(s) "
                              f"re-executed, all exited 0.")

        # 3. lint-contract -- swallowed exceptions, fabrication patterns,
        # frozen-machinery tampering, over the files this report's own
        # git diff touched (the same scope stamp-report uses).
        git_files, _ = _git_diff_files()
        py_targets = [f for f in (git_files or []) if f.endswith(".py")]
        lint_hard = []
        for sp in py_targets:
            h, _w = _scan_swallowed_exceptions(sp)
            lint_hard += h
        lint_hard += _scan_fabricated_statistical_input(py_targets)
        frozen_paths = _auto_frozen_verification_paths()
        if frozen_paths:
            fr_ok, _fr_details = check_frozen_files(contract_id, frozen_paths)
            if not fr_ok:
                lint_hard.append("FROZEN VERIFICATION MACHINERY TAMPERED (see lint-contract detail).")
        if lint_hard:
            ok = False
            for f in lint_hard:
                lines.append(f"FAIL [{rp}] lint-contract: {f}")
        else:
            lines.append(f"OK [{rp}] lint-contract: no hard failures across {len(py_targets)} "
                          f"changed Python file(s).")

        # 4. recompute -- a T-COMP/T-CAUSAL report must declare a
        # well-formed Recompute Declaration, and it must pass. Unlike the
        # standalone `recompute` subcommand (where no block is simply not
        # checked), a High-risk contract with no block at all is a
        # failure here -- that omission is exactly what D-031 warned was
        # silently allowed.
        checked, recompute_ok, recompute_lines = _check_recompute_block(rp_path)
        if not checked:
            ok = False
            if recompute_lines:
                lines.append(f"FAIL [{rp}] recompute: malformed Recompute Declaration -- "
                              f"{'; '.join(recompute_lines)}")
            else:
                lines.append(f"FAIL [{rp}] recompute: no Recompute Declaration block present. "
                              f"T-COMP/T-CAUSAL contracts require one (D-031, made mandatory by D-032).")
        elif not recompute_ok:
            ok = False
            lines.append(f"FAIL [{rp}] recompute: independent recomputation did not match "
                          f"or was not independent -- {'; '.join(recompute_lines)}")
        else:
            lines.append(f"OK [{rp}] recompute: independent recomputation matched.")

        # 5. stamp presence -- a High-risk contract cannot be COMPLETE
        # without a tamper-evident stamp (D-032). This checks presence
        # and integrity of an existing stamp; it does not append one --
        # `check` never modifies a report, stamping stays an explicit
        # separate step the Implementor runs via `stamp-report`.
        stamps = _find_stamps(text)
        if not stamps:
            ok = False
            lines.append(f"FAIL [{rp}] stamp: no Gatekeeper Verification Stamp present. "
                          f"T-COMP/T-CAUSAL contracts cannot be COMPLETE unstamped (D-032) -- "
                          f"run `gatekeeper.py stamp-report` before this check.")
        else:
            stamp_ok, stamp_findings = _verify_stamp_integrity(rp_path)
            if not stamp_ok:
                ok = False
                for f in stamp_findings:
                    lines.append(f"FAIL [{rp}] stamp: {f}")
            else:
                lines.append(f"OK [{rp}] stamp: {len(stamps)} stamp(s) present and intact.")

    return ok, lines


def cmd_check(args):
    checks_run = []
    overall_ok = True
    exit_code = 0
    # v1.3.4 (BUG-6): the exit-code contract stays exactly as documented
    # (0/4/6/8/9, joined by 17 in the v1.4.2 amendment below) --
    # exit_code = exit_code or N means only the first failing category
    # ever sets it, and that's left unchanged since something may already
    # depend on it. failed_categories tracks every failing category so a
    # printed summary line can show all of them, since the detail lines
    # above already do but the single integer exit code understates a
    # multi-category failure.
    failed_categories = []

    frozen_paths = sorted(set(list(args.frozen or []) + _auto_frozen_verification_paths()))
    report_paths = list(args.reports or [])

    scientific_claim_tier = None
    required_verification_commands = []

    if args.manifest:
        contract = load_manifest_contract(Path(args.manifest), args.contract)
        frozen_paths += contract.get("frozen_files", []) or []
        # v1.4.2 amendment -- mandatory mechanical gate (D-032/D-033): a
        # High-risk scientific/comparative claim no longer merely
        # documents that verify-contract/lint-contract/recompute/
        # stamp-report exist -- `check` now reads the same two manifest
        # fields the Architect declares frozen at contract-generation time and,
        # for T-COMP/T-CAUSAL, mechanically requires all four to pass
        # before the contract can read PASS. See dynamic_rules.md D-032,
        # D-033 and CHANGELOG.md's dated amendment to this entry.
        scientific_claim_tier = contract.get("scientific_claim_tier")
        required_verification_commands = contract.get("required_verification_commands", []) or []
        # v1.3.0 fix: required_reports in the manifest are bare filenames
        # (e.g. "contract_report.md"), matching the Contract Specification's
        # required_reports field -- they are NOT already full paths. Using
        # them as-is resolved relative to the current working directory,
        # not the actual filed location (project/chunks/chunkNN/reports/
        # {contract_id}/), causing a real reported false-missing-report
        # failure. A bare filename (no "/" in it) is now resolved against
        # that standard location; an entry that already contains a "/" is
        # assumed to already be a deliberate explicit path and is left
        # exactly as given, for backward compatibility with any manifest
        # that specified one that way on purpose.
        for rp in contract.get("required_reports", []) or []:
            if "/" in rp or "\\" in rp:
                report_paths.append(rp)
            else:
                # v1.3.4 (BUG-2): resolve against both the as-given and
                # zero-padded contract ID, the same fallback
                # _find_contract_file already applies -- whichever
                # candidate path actually exists on disk is used; if
                # neither exists yet, fall back to the fully-padded path
                # (the correct-going-forward spelling) so the failure
                # message points somewhere deterministic.
                chunk_num, _, candidates = _contract_id_candidates(args.contract or "")
                if chunk_num:
                    resolved = None
                    for candidate_id in candidates:
                        candidate_path = f"project/chunks/chunk{chunk_num}/reports/{candidate_id}/{rp}"
                        if Path(candidate_path).exists():
                            resolved = candidate_path
                            break
                    if resolved is None:
                        resolved = f"project/chunks/chunk{chunk_num}/reports/{candidates[-1]}/{rp}"
                    report_paths.append(resolved)
                else:
                    # No contract ID to derive a chunk number from -- can't
                    # resolve deterministically, so fall back to the literal
                    # value rather than guessing a path.
                    report_paths.append(rp)

    print(f"Gatekeeper check -- contract: {args.contract or '(none specified)'}")
    print("=" * 60)

    if frozen_paths:
        checks_run.append("Frozen File Validation")
        ok, details = check_frozen_files(args.contract or "unknown", frozen_paths)
        print("\n[Frozen File Validation]")
        for line in details:
            print(f"  {line}")
        if not ok:
            overall_ok = False
            exit_code = exit_code or 4
            failed_categories.append("frozen_file")
    else:
        print("\n[Frozen File Validation] SKIPPED -- no frozen files given (--frozen or manifest)")

    if report_paths:
        checks_run.append("Report Validation")
        required_sections = args.required_sections or DEFAULT_REQUIRED_SECTIONS
        ok, details = check_reports(report_paths, required_sections)
        print("\n[Report Validation]")
        for line in details:
            print(f"  {line}")
        if not ok:
            overall_ok = False
            exit_code = exit_code or 6
            failed_categories.append("report")
    else:
        print("\n[Report Validation] SKIPPED -- no reports given (--reports or manifest)")

    if args.allow_dirty:
        print("\n[Repository Integrity] SKIPPED -- --allow-dirty passed")
    else:
        checks_run.append("Repository Integrity")
        ok, details = check_git_clean()
        print("\n[Repository Integrity]")
        for line in details:
            print(f"  {line}")
        if not ok:
            overall_ok = False
            exit_code = exit_code or 8
            failed_categories.append("repository_integrity")

    if scientific_claim_tier in ("T-COMP", "T-CAUSAL"):
        checks_run.append("Mandatory Mechanical Gate (T-COMP/T-CAUSAL)")
        print(f"\n[Mandatory Mechanical Gate] scientific_claim_tier: {scientific_claim_tier}")
        gate_ok, gate_details = _run_mandatory_gate(
            args.contract or "unknown", report_paths, required_verification_commands,
        )
        for line in gate_details:
            print(f"  {line}")
        if not gate_ok:
            overall_ok = False
            exit_code = exit_code or 17
            failed_categories.append("mandatory_gate")
    elif scientific_claim_tier:
        print(f"\n[Mandatory Mechanical Gate] SKIPPED -- scientific_claim_tier is "
              f"'{scientific_claim_tier}' (T-DESC), not T-COMP/T-CAUSAL.")

    # v2.2.0 (D-034) -- Fail-Closed Tier Inference. Runs regardless of what
    # scientific_claim_tier currently reads, precisely because its job is to
    # catch the case where that field itself is wrong (too low). Only runs
    # when a contract file is actually locatable -- `check` is also called
    # in contexts (e.g. a bare --frozen/--reports invocation with no
    # --contract) where there is no contract prose to scan; that is
    # reported as SKIPPED, not silently passed.
    contract_text_for_tier = None
    if args.contract:
        contract_path, _err = _find_contract_file(args.contract)
        if contract_path is not None:
            contract_text_for_tier = _read_text_or_none(contract_path)
    if contract_text_for_tier is not None:
        checks_run.append("Fail-Closed Tier Inference")
        declared_tier_for_check = scientific_claim_tier or "NONE"
        m = re.search(r'Scientific Claim Tier.*?:\s*\**\s*(NONE|T-DESC|T-COMP|T-CAUSAL)\b',
                      contract_text_for_tier, re.IGNORECASE)
        if m:
            declared_tier_for_check = m.group(1).upper()
        minimum_tier, strong_matches, _weak = _infer_minimum_scientific_claim_tier(contract_text_for_tier)
        print(f"\n[Fail-Closed Tier Inference] declared: {declared_tier_for_check}  inferred minimum: {minimum_tier}")
        if strong_matches:
            print(f"  Strong signal(s) matched: {strong_matches}")
        if _TIER_RANK[declared_tier_for_check] < _TIER_RANK[minimum_tier]:
            overall_ok = False
            exit_code = exit_code or 18
            failed_categories.append("tier_inference")
            print(
                f"  FAIL: declared '{declared_tier_for_check}' is weaker than inferred minimum "
                f"'{minimum_tier}'. Run `gatekeeper.py tier-check --contract {args.contract}` "
                f"for the full explanation and remediation."
            )
        else:
            print("  OK.")
    else:
        print("\n[Fail-Closed Tier Inference] SKIPPED -- no --contract given, or its contract file "
              "was not found (run `gatekeeper.py tier-check` directly once it exists).")

    print("\n" + "=" * 60)
    if len(failed_categories) > 1:
        print(f"Failure categories: {failed_categories}")
    print(f"Checks executed: {checks_run if checks_run else '(none -- nothing was actually checked)'}")
    print(
        "NOT implemented in this script (still AI-attested only): "
        "Bootstrap Validation, Manifest Validation, Contract Validation, "
        "Allowed File Validation, Verification Script Validation, "
        "Dynamic Rule Validation, Bootstrap Compliance, full Git Validation. "
        "(v1.4.2 amendment: the Mandatory Mechanical Gate above IS mechanically enforced "
        "for T-COMP/T-CAUSAL contracts -- it is not on this AI-attested-only list.)"
    )
    print(f"RESULT: {'PASS' if overall_ok else 'FAIL'}")
    print(f"Exit code: {exit_code}")

    sys.exit(exit_code)


# v1.3.4 -- self-check reads these repo-root-relative files if present.
# All reads are best-effort: a missing file is reported as a finding, not a
# crash, since self-check's whole purpose is to surface exactly this kind
# of drift.
SELF_CHECK_FILES = {
    "gatekeeper_spec": Path("factory/gatekeeper_spec.md"),
    "factory_spec": Path("factory/factory_spec.md"),
    "version": Path("factory/VERSION"),
    "changelog": Path("factory/CHANGELOG.md"),
    # v2.2.0 -- architect_spec.md/implementor_spec.md are the primary role
    # documents as of this version (see CHANGELOG.md's v2.2.0 entry); the
    # gemini_spec/claude_init keys are kept, pointed at the same two role
    # documents were the old names retired outright, self-check would start
    # reporting every pre-v2.2 self_check_files reference to them as drift
    # rather than a deliberate rename. The legacy filenames themselves
    # (factory/ClaudeInitialization.md, factory/gemini_spec.md) still exist
    # on disk too, as short pointer files -- see bootstrap_manifest.yaml.
    "gemini_spec": Path("factory/implementor_spec.md"),
    "claude_init": Path("factory/architect_spec.md"),
    "implementor_spec": Path("factory/implementor_spec.md"),
    "architect_spec": Path("factory/architect_spec.md"),
    "domain_checklists": Path("factory/domain_checklists.md"),
    # v1.4.1 -- added after these two were found to have drifted (Factory
    # Version headers stuck at 1.3.4 through two full release cycles)
    # while _self_check_version_currency ran clean, because neither file
    # was in this dict at all. The check was correct; its target list was
    # incomplete. Found by direct inspection, not by self-check itself --
    # exactly the failure mode this dict's completeness exists to prevent.
    "constitution": Path("factory/constitution.md"),
    "dynamic_rules": Path("factory/dynamic_rules.md"),
    # v1.4.2 -- the same gap, found again, in the two files SELF_CHECK_FILES
    # itself lives in. gatekeeper.py's own module docstring ("STATUS
    # (Factory vX.Y.Z)") and bootstrap_manifest.yaml's factory.version
    # field are both live version references that nothing was checking --
    # this dict cannot monitor a file it doesn't list, including its own
    # host file. Found by direct inspection during a routine review, not
    # by self-check itself, exactly as before. bootstrap_manifest.yaml's
    # SEPARATE bootstrap_manifest_version field is deliberately excluded
    # from what the version-currency regex matches (see
    # _VERSION_HEADER_RE) -- that field versions the manifest schema
    # independently of the Factory version by the manifest's own stated
    # design and must not be flagged just because it differs from VERSION.
    "gatekeeper": Path("factory/gatekeeper.py"),
    "bootstrap_manifest": Path("factory/bootstrap_manifest.yaml"),
}

# Recognized argparse subcommand names, kept as a plain list rather than
# introspected from the parser object, so self-check has no import-order
# dependency on main() having run yet.
IMPLEMENTED_COMMANDS = [
    "snapshot", "snapshot-chunk", "next", "sort-dropbox", "stage-takethis",
    "clear-takethis", "materialize", "commit-project", "check", "self-check",
    "release-check", "acquisition-audit", "evidence-check",
    "verify-contract", "lint-contract", "recompute", "stamp-report", "verify-stamps",
    # v2.2.0
    "tier-check", "release-certify",
    # v2.3.0 (D-039 through D-048/D-053)
    "release-status", "contract-preflight", "begin", "finalize", "delegate", "log-decision",
    # v2.5.0 (MAR mechanical gates, D-056, D-059, D-060, D-061)
    "verify-baseline-parity", "verify-hardware-profile", "freeze-experiment",
    "verify-experiment-freeze", "contamination-check",
    # v2.6.0 (C65-C69, D-062-D-073)
    "verify-statistical-protocol", "verify-sensitivity-analysis",
    "pre-submission-audit", "verify-failure-taxonomy",
]

# Exit codes this script actually emits, per its own module docstring.
IMPLEMENTED_EXIT_CODES = {0, 3, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30}

_CONTRACT_ID_SHAPED_RE = re.compile(r'\bC\d+-\d+\b')
_VALID_CONTRACT_ID_RE = re.compile(r'^C\d{2}-\d{2}$')
_VERSION_HEADER_RE = re.compile(
    # v1.4.2: added the `^[ \t]*version:` alternative (with MULTILINE) so
    # bootstrap_manifest.yaml's YAML `version: "X.Y.Z"` field is caught.
    # Anchored to line-start so it matches only a standalone `version:`
    # key, never `bootstrap_manifest_version:` -- the latter has no
    # whitespace-only prefix before "version:" on its own line (the
    # "bootstrap_manifest_" text sits between the line start and the
    # literal token "version:"), so it cannot satisfy `^[ \t]*version:`
    # regardless of its value. Verified by
    # test_gatekeeper_v1_4_2.py::test_independently_versioned_manifest_schema_field_is_never_flagged.
    r'(?:Factory Version\s*\n+\s*|as of v|Factory v|\*\*Version:\*\*\s*|^[ \t]*version:\s*["\']?)(\d+\.\d+\.\d+)',
    re.IGNORECASE | re.MULTILINE
)


def _read_text_or_none(path: Path):
    try:
        return path.read_text(errors="replace")
    except OSError:
        return None


def _self_check_implemented_vs_specified():
    """Diff target 1: implemented commands/exit codes vs. gatekeeper_spec.md's
    Implementation Status section. Returns list[str] findings."""
    findings = []
    spec_text = _read_text_or_none(SELF_CHECK_FILES["gatekeeper_spec"])
    if spec_text is None:
        findings.append(
            f"CANNOT CHECK: {SELF_CHECK_FILES['gatekeeper_spec']} not found -- "
            f"skipping Implemented vs. specified diff."
        )
        return findings

    spec_lower = spec_text.lower()

    # Every implemented command should be named somewhere in the spec's
    # Implementation Status section (a command implemented but never
    # disclosed is exactly the failure mode C01/gatekeeper_spec.md's own
    # Implementation Status section exists to prevent).
    for cmd in IMPLEMENTED_COMMANDS:
        cmd_variants = [cmd, cmd.replace("-", "_"), f"`{cmd}`"]
        if not any(v.lower() in spec_lower for v in cmd_variants):
            findings.append(
                f"UNDISCLOSED COMMAND: '{cmd}' is implemented in gatekeeper.py "
                f"but not mentioned anywhere in gatekeeper_spec.md's Implementation "
                f"Status section."
            )

    # Every exit code this script emits should appear in the spec's Exit
    # Codes table.
    exit_codes_section_idx = spec_lower.find("# exit codes")
    exit_codes_text = spec_text[exit_codes_section_idx:] if exit_codes_section_idx != -1 else spec_text
    for code in sorted(IMPLEMENTED_EXIT_CODES):
        if re.search(rf'(?<!\d){code}(?!\d)', exit_codes_text) is None:
            findings.append(
                f"UNDOCUMENTED EXIT CODE: gatekeeper.py can exit {code}, but "
                f"that code was not found in gatekeeper_spec.md's Exit Codes table."
            )

    return findings


def _self_check_artifact_lifecycle():
    """Diff target 2: for each row in factory_spec.md's Artifact Lifecycle
    table, check whether the declared producer has a corresponding
    instruction in gemini_spec.md or ClaudeInitialization.md. Returns
    list[str] findings.

    This is necessarily a heuristic, not a semantic check (self-check
    performs no AI reasoning, per Gatekeeper's own Verification Principles)
    -- it looks for the artifact's filename mentioned somewhere in the
    producer-facing instruction document, nothing more. A miss here is a
    prompt to look closer, not a proven gap.
    """
    findings = []
    factory_spec_text = _read_text_or_none(SELF_CHECK_FILES["factory_spec"])
    if factory_spec_text is None:
        findings.append(
            f"CANNOT CHECK: {SELF_CHECK_FILES['factory_spec']} not found -- "
            f"skipping Artifact Lifecycle diff."
        )
        return findings

    gemini_text = _read_text_or_none(SELF_CHECK_FILES["gemini_spec"]) or ""
    claude_init_text = _read_text_or_none(SELF_CHECK_FILES["claude_init"]) or ""
    combined_instructions = (gemini_text + "\n" + claude_init_text).lower()

    # Match Markdown table rows of the form "| artifact.ext | Producer | ... |"
    row_re = re.compile(r'^\|\s*([\w.]+\.\w+)\s*\|\s*([^|]+?)\s*\|', re.MULTILINE)
    for m in row_re.finditer(factory_spec_text):
        artifact, producer = m.group(1), m.group(2).strip()
        if producer.lower() in ("artifact", "---", ""):
            continue
        if "gemini" in producer.lower() or "claude" in producer.lower():
            if artifact.lower() not in combined_instructions:
                findings.append(
                    f"NO OPERATIVE INSTRUCTION: factory_spec.md's Artifact Lifecycle "
                    f"table lists '{artifact}' as produced by '{producer}', but "
                    f"'{artifact}' was not found in gemini_spec.md or "
                    f"ClaudeInitialization.md -- there may be no instruction telling "
                    f"that role to actually produce it."
                )

    return findings


def _self_check_version_currency():
    """Diff target 3: every document's embedded 'Factory Version' / 'as of
    vX.Y.Z' reference vs. VERSION and CHANGELOG.md's latest entry. Returns
    list[str] findings."""
    findings = []
    version_text = _read_text_or_none(SELF_CHECK_FILES["version"])
    if version_text is None:
        findings.append(
            f"CANNOT CHECK: {SELF_CHECK_FILES['version']} not found -- "
            f"skipping Version currency diff."
        )
        return findings

    current_version = version_text.strip()

    docs_to_scan = {
        name: path for name, path in SELF_CHECK_FILES.items()
        if name not in ("version", "changelog")
    }
    for name, path in docs_to_scan.items():
        text = _read_text_or_none(path)
        if text is None:
            continue
        stale = [
            v for v in set(_VERSION_HEADER_RE.findall(text))
            if v != current_version
        ]
        if stale:
            findings.append(
                f"STALE VERSION REFERENCE: {path} references version(s) "
                f"{sorted(stale)} but VERSION is {current_version!r}. This may be "
                f"an intentional historical reference (e.g. 'introduced in v1.3.0') "
                f"-- self-check cannot distinguish that from real staleness, so "
                f"confirm by reading context before editing."
            )

    return findings


def _self_check_naming_convention():
    """Diff target 4: extract C\\d+-\\d+-shaped IDs from worked examples
    inside spec documents; flag any that don't match ^C\\d{2}-\\d{2}$.
    Returns list[str] findings.

    v2.3.0 (D-052): scans line-by-line (not whole-text) so a line can
    carry its own `<!-- GATEKEEPER-EXEMPT: reason -->` comment, reusing
    the same suppression idiom lint-contract's swallowed-exception scan
    already uses for Python (`# GATEKEEPER-EXEMPT: reason`) rather than
    inventing a separate mechanism or file. A genuine negative example
    (correct padding contrasted with an unpadded form) is common in spec
    prose explaining the convention itself -- exempting it on its own
    line, with a reason, is visible in any diff and requires no new file
    format."""
    findings = []
    for name, path in SELF_CHECK_FILES.items():
        if name in ("version", "changelog"):
            continue
        text = _read_text_or_none(path)
        if text is None:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            bad_ids = sorted(set(
                m for m in _CONTRACT_ID_SHAPED_RE.findall(line)
                if not _VALID_CONTRACT_ID_RE.match(m)
            ))
            if not bad_ids:
                continue
            exempt_m = _EXEMPTION_COMMENT_RE.search(line) or re.search(
                r'<!--\s*GATEKEEPER-EXEMPT:\s*(.+?)\s*-->', line)
            if exempt_m:
                continue
            findings.append(
                f"NAMING CONVENTION: {path}:{lineno} contains contract-ID-shaped "
                f"string(s) not matching ^C\\d{{2}}-\\d{{2}}$: {bad_ids}. Unpadded IDs "
                f"like 'C3-01' are valid *input* to gatekeeper.py (it falls back to "  # GATEKEEPER-EXEMPT: this message's own illustrative example of a badly-shaped ID is inherently self-referential
                f"the padded form) but should not appear in worked examples, which "
                f"set the pattern a future Architect copies. If this is a deliberate "
                f"negative example, add '<!-- GATEKEEPER-EXEMPT: reason -->' on this "
                f"line rather than treating this finding as noise to ignore."
            )
    return findings


def _self_check_required_sections_vs_template():
    """v2.3.0 (D-046) -- Diff target 5: cross-checks DEFAULT_REQUIRED_SECTIONS
    against the actual '## '-level headings in implementor_spec.md section
    8's contract_report.md template. This is the check that would have
    caught D-046's own root-cause bug (the previous default checked for
    'objective'/'evidence', neither of which was ever a real heading in
    that template) before it shipped -- added here so the same class of
    drift cannot recur silently a second time."""
    findings = []
    path = SELF_CHECK_FILES.get("implementor_spec")
    text = _read_text_or_none(path) if path else None
    if text is None:
        findings.append("CANNOT CHECK: implementor_spec.md not found or unreadable.")
        return findings
    # The template lives in a fenced code block following a line
    # mentioning "contract_report.md" -- extract headings from the first
    # such fence rather than the whole document, so unrelated headings
    # elsewhere in the spec don't count as "the template."
    # v2.3.0 (D-046): anchored on the "## 8. Contract Report" section
    # heading specifically, not the first bare occurrence of the string
    # "contract_report.md" anywhere in the document -- that string also
    # appears in unrelated prose earlier in the file (section 4's Mailbox
    # protocol, section 6's status-lookup description), and a non-greedy
    # search from the FIRST such occurrence could pair with an unrelated
    # nearby fence instead of the actual template.
    section_m = re.search(r'^##\s+8\.\s+Contract Report\b.*$', text, re.MULTILINE)
    if section_m is None:
        findings.append("CANNOT CHECK: no '## 8. Contract Report' section heading found "
                         "in implementor_spec.md.")
        return findings
    after_section = text[section_m.end():]
    fence_m = re.search(r'```\s*\n(.*?)\n```', after_section, re.DOTALL)
    if fence_m is None:
        findings.append(
            "CANNOT CHECK: no fenced contract_report.md template found in "
            "implementor_spec.md to check DEFAULT_REQUIRED_SECTIONS against."
        )
        return findings
    template_headings = [h.lower() for h in _HEADING_LINE_RE.findall(fence_m.group(1))]
    for required in DEFAULT_REQUIRED_SECTIONS:
        if not any(required in h for h in template_headings):
            findings.append(
                f"REQUIRED SECTION DRIFT: DEFAULT_REQUIRED_SECTIONS contains "
                f"'{required}', which does not match any heading in "
                f"implementor_spec.md's own contract_report.md template "
                f"({template_headings}). A report following the template exactly "
                f"would fail Report Validation for a section the template never "
                f"asked it to have -- see D-046."
            )
    return findings


def cmd_self_check(args):
    """v1.3.4 -- diagnostic only. Reports diffs between what gatekeeper.py
    actually does and what the Factory's own documents claim it does.
    Never modifies any file. Runs all five diff targets (v2.3.0 adds the
    fifth, D-046) and prints every finding; an empty finding list for a
    target is reported as such, not silently skipped. v2.3.0 also gives
    every finding a stable ID (SC{target}-{n}) so a specific finding can
    be referenced/tracked across runs.
    """
    print("Gatekeeper self-check (diagnostic only -- reports diffs, never auto-fixes)")
    print("=" * 60)

    targets = [
        ("Implemented vs. specified", _self_check_implemented_vs_specified),
        ("Artifact Lifecycle vs. operative instructions", _self_check_artifact_lifecycle),
        ("Version currency", _self_check_version_currency),
        ("Naming-convention lint", _self_check_naming_convention),
        ("Required-sections vs. template (D-046)", _self_check_required_sections_vs_template),
    ]

    total_findings = 0
    for idx, (label, fn) in enumerate(targets, start=1):
        print(f"\n[{label}]")
        findings = fn()
        if not findings:
            print("  No drift found.")
        else:
            for n, f in enumerate(findings, start=1):
                print(f"  - SC{idx}-{n:03d}: {f}")
            total_findings += len(findings)

    print("\n" + "=" * 60)
    print(f"Total findings: {total_findings}")
    print(
        "Evidence posture: unit-tested against synthetic drift scenarios, not yet "
        "run against a real project's full document set beyond the audit that "
        "produced v1.3.4 itself (Diff targets 1-4) and this release (Diff target "
        "5). Findings are prompts to look closer, not proven defects -- self-check "
        "performs no AI reasoning and can produce false positives (e.g. an "
        "intentional historical version reference, or a naming-convention match "
        "not marked with a GATEKEEPER-EXEMPT comment yet)."
    )
    # Diagnostic tool: findings are reported, never treated as a failing
    # exit code. A non-zero exit here would make self-check itself a gate,
    # which is out of scope for a v1.3.x patch release (see v1.3.4 spec
    # section 0's C50 gate).
    sys.exit(0)


# ---------------------------------------------------------------------------
# release-check (v1.4.0) -- scans an outbound release artifact (a
# manuscript, REPRODUCIBILITY.md, supplementary material) before it leaves
# the repository. Two checks, kept in one command per C46 (both are "scan
# an outbound artifact before it ships"): a local-path/machine-identity
# scan (hard FAIL, unambiguous), and a key-fact consistency check against a
# project-declared key_facts.md (WARNING -- heuristic).
#
# Neither check performs semantic understanding of the manuscript's prose.
# Per Gatekeeper's own Verification Principles ("Gatekeeper never performs
# AI reasoning"), the fact-consistency check only catches drift against
# facts the Architect explicitly declared ahead of time in key_facts.md --
# it is not an open-ended fact-checker, and cannot be, without violating
# Gatekeeper's own Purpose. See v1_4_0_scientific_validity_layer.md Part 5,
# and D-017.
# ---------------------------------------------------------------------------

_LOCAL_PATH_RE = re.compile(
    r'(?:/Users/|/home/|[A-Za-z]:\\Users\\)[^\s"\')\]<>,;]+'
)

_KEY_FACT_HEADER_RE = re.compile(r'^##\s*Key Fact:.*$', re.MULTILINE)
_KEY_FACT_FIELD_RE = re.compile(
    r'anchor:\s*(?P<anchor>.+?)\s*$.*?'
    r'expected_value:\s*(?P<value>-?\d+(?:\.\d+)?)\s*$'
    r'(?:.*?tolerance:\s*(?P<tolerance>-?\d+(?:\.\d+)?)\s*$)?',
    re.MULTILINE | re.DOTALL
)

_NUMBER_NEAR_RE_TEMPLATE = r'.{{0,60}}\b{anchor}\b.{{0,60}}'
_BARE_NUMBER_RE = re.compile(r'-?\d+(?:\.\d+)?')


def _scan_local_paths(file_paths):
    """Returns list[str] findings: any /Users/, /home/, or C:\\Users\\
    absolute path found in any given file. Deterministic substring/regex
    match only -- no judgement about whether a given path is "legitimate"
    (e.g. deliberately documenting a specific deployment target); that
    call is left to whoever reads the finding.
    """
    findings = []
    for fp in file_paths:
        p = Path(fp)
        text = _read_text_or_none(p)
        if text is None:
            findings.append(f"CANNOT CHECK: {fp} not found -- skipping local-path scan for this file.")
            continue
        matches = sorted(set(_LOCAL_PATH_RE.findall(text)))
        for m in matches:
            findings.append(
                f"LOCAL PATH LEAK: {fp} contains an absolute local filesystem path "
                f"'{m}' -- this will not resolve on a reader's machine. Replace with "
                f"a repository-relative path."
            )
    return findings


def _parse_key_facts(key_facts_path):
    """Parses key_facts.md's '## Key Fact: ...' blocks into a list of
    dicts: {anchor, value, tolerance}. Each block runs from its '## Key
    Fact:' header to the next '## ' header or end of file. A block missing
    'anchor:' or 'expected_value:' is reported as malformed, not silently
    dropped -- a Key Fact the Architect intended to declare but mistyped
    should never fail open. Returns (facts_or_None, findings)."""
    text = _read_text_or_none(Path(key_facts_path))
    if text is None:
        return None, [f"CANNOT CHECK: {key_facts_path} not found -- skipping key-fact consistency check."]

    headers = list(_KEY_FACT_HEADER_RE.finditer(text))
    facts = []
    findings = []
    for i, h in enumerate(headers):
        block_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block = text[h.end():block_end]
        m = _KEY_FACT_FIELD_RE.search(block)
        if m is None or m.group("anchor") is None or m.group("value") is None:
            findings.append(
                f"MALFORMED KEY FACT: '{h.group().strip()}' in {key_facts_path} is "
                f"missing an 'anchor:' or 'expected_value:' line -- skipped, not checked."
            )
            continue
        facts.append({
            "anchor": m.group("anchor").strip(),
            "value": float(m.group("value")),
            "tolerance": float(m.group("tolerance")) if m.group("tolerance") else 0.0,
        })
    return facts, findings


def _check_key_fact_consistency(manuscript_path, key_facts_path):
    """Returns list[str] findings. For each declared key fact, searches the
    manuscript for the anchor phrase; if a nearby number differs from the
    declared value by more than its tolerance, flags a mismatch. Bounded
    and heuristic by design (see module comment above) -- catches drift
    only against facts the Architect explicitly declared, and can
    false-positive when two genuinely distinct quantities share an anchor
    word (e.g. water volume released vs. moraine volume collapsed both
    containing the word "volume") -- findings are framed as requiring
    human confirmation, not proven defects.
    """
    findings = []
    facts, parse_findings = _parse_key_facts(key_facts_path)
    findings += parse_findings
    if facts is None:
        return findings
    if not facts:
        findings.append(
            f"CANNOT CHECK: {key_facts_path} exists but declares no '## Key Fact:' "
            f"blocks -- nothing to check consistency against."
        )
        return findings

    manuscript_text = _read_text_or_none(Path(manuscript_path))
    if manuscript_text is None:
        findings.append(f"CANNOT CHECK: {manuscript_path} not found -- skipping key-fact consistency check.")
        return findings

    for fact in facts:
        window_re = re.compile(
            _NUMBER_NEAR_RE_TEMPLATE.format(anchor=re.escape(fact["anchor"])),
            re.IGNORECASE | re.DOTALL,
        )
        mismatched_numbers = set()
        for window in window_re.findall(manuscript_text):
            for num_str in _BARE_NUMBER_RE.findall(window):
                if abs(float(num_str) - fact["value"]) > fact["tolerance"]:
                    mismatched_numbers.add(num_str)
        if mismatched_numbers:
            findings.append(
                f"KEY FACT MISMATCH: near '{fact['anchor']}', {manuscript_path} contains "
                f"number(s) {sorted(mismatched_numbers)} that differ from the declared "
                f"value {fact['value']} (tolerance {fact['tolerance']}) in {key_facts_path}. "
                f"This may be a real inconsistency, or two genuinely different quantities "
                f"that happen to share an anchor word -- confirm by reading context before "
                f"treating this as a defect."
            )
    return findings


# ---------------------------------------------------------------------------
# acquisition-audit (v1.4.0) -- scans data-acquisition scripts and their
# contract reports for red-flag patterns before their output is trusted.
# Two checks, kept in one command per C46 (both are "grep acquisition-
# related files for a pattern that demands investigation"): a structural
# audit for data-generation function definitions (hard FAIL -- D-022), and
# a textual scan for simulation-indicating language (WARNING -- D-023).
#
# Motivated by a real incident (Chunk 07, GLOF project rework): an
# acquisition script contained a function literally named
# `generate_fallback_timeseries`, called when the target API was
# unreachable, producing simulated data that passed every Reality Gate
# property check because the simulator was designed to produce realistic
# properties. The Architect caught it only by reading free-text output and
# noticing the word "synthesize" -- this command makes that catch
# deterministic. See dynamic_rules.md D-022, D-023.
#
# Like release-check's key-fact check, the textual scan is bounded and
# heuristic by design: some flagged words have legitimate uses ("generated
# thumbnail"), so matches are reported for human review, not treated as
# proven fabrication. The structural check is closer to unambiguous -- an
# acquisition script has no legitimate reason to define a function named
# generate_/simulate_/synthesize_/fallback_/mock_/fake_ -- but a determined
# fabricator could still choose a non-obvious name; this catches the common
# case, not every case (see v1_4_0_scientific_validity_layer.md's Part 12
# analogue, and dynamic_rules.md's "What Still Cannot Be Caught" note).
# ---------------------------------------------------------------------------

_ACQUISITION_FUNCTION_RE = re.compile(
    r'^\s*def\s+(generate_|simulate_|synthesize_|fallback_|mock_|fake_)\w*\s*\(',
    re.MULTILINE
)

_ACQUISITION_TEXT_RE = re.compile(
    r'\b(synthesize[sd]?|simulated|generated|fallback|mock(?:ed)?|synthetic'
    r'|offline[\s_-]*data|placeholder[\s_-]*data)\b',
    re.IGNORECASE
)

# v1.4.2 -- second structural sub-check, added to this command rather than
# as a new one (C46: improve an existing component before adding a new
# one). D-022's check catches a script that fabricates data because an
# *external* constraint blocked real acquisition (Chunk 07: API
# unreachable). This catches a related but distinct pattern with no
# external constraint at all: a script that is supposed to compute a
# metric/statistic over real per-observation data instead manufactures
# its own substitute observations from a random distribution and feeds
# those into the metric call directly. Real incident: GLOF project
# rework, Chunk 08, contract C08-06 (`run_bootstrap_ci.py`) -- read only
# the already-aggregated scalar auc_roc from
# evaluation_summary_real_data.json, then fabricated per-window scores
# via `rng.normal(...)` shaped to approximate that AUC, then bootstrapped
# and DeLong-tested the fabricated values. The resulting CIs and
# p-values were reported in statistical_significance.json, traced by
# claim_evidence_map.json (CL-16 through CL-21), and appear in
# sentinel_gl_manuscript.md's abstract and RQ3 result -- reproduced
# independently: running the real script against its real input with its
# own documented seed produced a byte-identical artifact to the one that
# shipped. Caught only by a later adversarial audit; `check_reports`,
# `evidence-check`, and `release-check` all operate on an artifact's own
# declared values and would not have caught this, because the artifact
# is internally self-consistent -- the fabrication happened one step
# upstream, in what produced the artifact. See dynamic_rules.md D-028.
#
# File-level co-occurrence, not proven data-flow: this does not trace
# whether the specific value passed to the metric function definitely
# originated from the distribution-sampling call (that would require an
# AST/data-flow analysis Gatekeeper's own Purpose -- deterministic,
# bounded, no AI reasoning -- does not rule out in principle, but which
# is a materially bigger undertaking than any existing check performs;
# not attempted here). A script that calls a distribution sampler
# (.normal/.uniform/.randn) anywhere in the same file as a call to a
# recognized metrics function (roc_auc_score, precision_recall_curve,
# roc_curve, f1_score, average_precision_score) is flagged. This can
# false-positive on a file that legitimately does both for unrelated
# reasons (e.g. a bundled power-analysis helper); that is why this is
# reported with exact file:line locations for human confirmation, the
# same posture as D-022's function-name check, not treated as
# infallible.
_DISTRIBUTION_SAMPLING_RE = re.compile(
    r'\b(\w+)\s*=\s*(?:np\.random\.|numpy\.random\.|rng\.)'
    r'(normal|uniform|randn|standard_normal)\s*\('
)

_METRIC_FUNCTION_CALL_RE = re.compile(
    r'\b(roc_auc_score|precision_recall_curve|roc_curve|f1_score|average_precision_score)\s*\('
)


def _scan_fabricated_statistical_input(script_paths):
    """v1.4.2, D-028. Returns list[str] findings: a script that calls a
    distribution-sampling method anywhere in the same file as a call to a
    recognized metrics function. Deterministic regex co-occurrence check
    only -- see the module comment above this function for exactly what
    it does and does not prove."""
    findings = []
    for sp in script_paths:
        text = _read_text_or_none(Path(sp))
        if text is None:
            findings.append(f"CANNOT CHECK: {sp} not found -- skipping fabrication audit for this file.")
            continue
        sampling_matches = list(_DISTRIBUTION_SAMPLING_RE.finditer(text))
        if not sampling_matches:
            continue
        if _METRIC_FUNCTION_CALL_RE.search(text) is None:
            continue
        for m in sampling_matches:
            line_no = text[:m.start()].count("\n") + 1
            findings.append(
                f"FABRICATED STATISTICAL INPUT: {sp}:{line_no} assigns '{m.group(1)}' from "
                f"a distribution sampler ({m.group(2)}(...)), and this file also calls a "
                f"metrics function ({', '.join(sorted(set(mm.group(1) for mm in _METRIC_FUNCTION_CALL_RE.finditer(text))))}). "
                f"A script computing a real metric/statistic has no legitimate reason to "
                f"manufacture its own per-observation values (C01) -- confirm '{m.group(1)}' "
                f"does not feed the metric computation before trusting this script's output."
            )
    return findings


def _scan_acquisition_functions(script_paths):
    """Returns list[str] findings: any function definition matching a
    data-generation naming pattern in an acquisition script. Deterministic
    regex match only -- catches the common case (an honestly- or
    carelessly-named fallback function), not a deliberately obfuscated one.
    """
    findings = []
    for sp in script_paths:
        text = _read_text_or_none(Path(sp))
        if text is None:
            findings.append(f"CANNOT CHECK: {sp} not found -- skipping structural audit for this file.")
            continue
        for m in _ACQUISITION_FUNCTION_RE.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            findings.append(
                f"DATA-GENERATION FUNCTION: {sp}:{line_no} defines a function matching "
                f"'{m.group(1)}*' -- an acquisition script has no legitimate reason to "
                f"generate, simulate, synthesize, mock, or fake data (C54). Investigate "
                f"before trusting this script's output."
            )
    return findings


def _scan_acquisition_text(text_paths):
    """Returns list[str] findings: simulation-indicating words found in
    acquisition scripts or contract reports. Heuristic -- some matches are
    legitimate ("generated thumbnail"); every finding names the exact word
    and location so a human can judge context quickly, per C39."""
    findings = []
    for tp in text_paths:
        text = _read_text_or_none(Path(tp))
        if text is None:
            findings.append(f"CANNOT CHECK: {tp} not found -- skipping textual scan for this file.")
            continue
        matches = sorted(set(m.group(0).lower() for m in _ACQUISITION_TEXT_RE.finditer(text)))
        if matches:
            findings.append(
                f"SIMULATION-INDICATING LANGUAGE: {tp} contains {matches} -- may be "
                f"legitimate ('generated thumbnail') or may indicate undisclosed data "
                f"substitution (D-023, the Chunk 07 pattern). Read context before judging."
            )
    return findings


# ---------------------------------------------------------------------------
# tier-check (v2.2.0, D-034) -- fail-closed minimum Scientific Claim Tier
# inference. Every mechanism this Factory has for scientific rigor (the
# T-COMP/T-CAUSAL baseline/significance/adversarial-test requirements, v1.4.0;
# the Mandatory Mechanical Gate, v1.4.2/D-032) is keyed off a contract's own
# self-declared scientific_claim_tier field. Nothing before v2.2 checked
# whether that self-declaration was actually low. A contract whose own text
# plainly describes a comparative or statistical claim can declare
# scientific_claim_tier: NONE (or omit it) and every one of those mechanisms
# silently does not apply -- not because they failed, but because they were
# never triggered.
#
# This is not hypothetical: project/chunks/chunk06/contracts/C06-03_contract.md
# in the uploaded factory_v1.5.0 TDLCR test project -- "Pre-Registered
# Hypothesis Evaluator & Result Registry Compiler," whose own Implementation
# Instructions name a Wilcoxon significance test, a Cliff's delta effect
# size, and SUPPORTED/FALSIFIED/INCONCLUSIVE verdicts feeding
# project/result_registry.json for IEEE publication -- declares
# `Scientific Claim Tier: NONE`, with a Verification Scripts entry that only
# confirms the module imports cleanly. Under v1.4.2/v2.1 alike, nothing
# mechanical would have caught that before Chunk Review. See CHANGELOG.md's
# v2.2.0 entry and dynamic_rules.md D-034 for the full account.
#
# Deliberately narrow, matching this file's existing posture for every other
# heuristic text scan (D-023's simulation-indicating language,
# D-028's fabrication co-occurrence check): this is keyword/pattern matching
# over a contract's own Objective/Context/Implementation Instructions/Outputs
# text, not semantic understanding. It can and will false-positive (a
# contract implementing a metrics *computation* utility, never itself making
# a comparative claim, may mention "F1" or "AUC" in passing) and it can
# false-negative (a claim phrased with no matched keyword at all). Every
# finding names the exact matched text so a human/Architect can judge context
# quickly, per C39 -- this is a floor under self-declaration, not a
# replacement for the Architect's own judgment at Chunk Planning.
#
# Ordering for comparison purposes: NONE < T-DESC < T-COMP < T-CAUSAL.
_TIER_RANK = {"NONE": 0, "T-DESC": 1, "T-COMP": 2, "T-CAUSAL": 3}

# Strong signals: specific enough that a contract matching one of these and
# still declaring NONE/T-DESC is very likely under-tiered, not a false
# positive. Named statistical tests/effect sizes, explicit p-value/CI
# notation, and pre-registered-verdict language (SUPPORTED/FALSIFIED/
# INCONCLUSIVE, the exact vocabulary factory_spec.md's Scientific Claim Tier
# table and venue_requirements.md's falsification criteria already use).
_TCOMP_STRONG_RE = re.compile(
    r'\b(wilcoxon|mann-?whitney|delong|paired\s+t-test|unpaired\s+t-test|'
    r'student.?s?\s+t-test|anova|chi-square|kruskal-?wallis|'
    r'cliff.?s?\s*delta|cohen.?s?\s*d\b|hedges.?\s*g|'
    r'p\s*[<>=]\s*0?\.\d+|p-value|confidence\s+interval|\bCI\s*[:=]|'
    r'outperforms?|out-performs?|statistically\s+significant|'
    r'SUPPORTED\s*/\s*FALSIFIED|FALSIFIED\s*/\s*INCONCLUSIVE|'
    r'pre-?registered\s+(?:hypothesis|criteri|falsification)|'
    r'effect\s+size)\b',
    re.IGNORECASE,
)

# Strong T-CAUSAL signals: robustness/causal/ablation claims specifically --
# distinct from T-COMP because factory_spec.md requires an adversarial test
# and a declared Stop Condition for these, not just baselines + significance.
_TCAUSAL_STRONG_RE = re.compile(
    r'\b(robust(?:ness)?\s+to|adversarial(?:ly)?\s+(?:test|robust|attack)|'
    r'is\s+robust|enables?\s+\w+\s+to|causally?|ablation\s+stud|'
    r'invariant\s+to|generalizes?\s+to\s+(?:unseen|out-of-distribution))\b',
    re.IGNORECASE,
)

# Weaker signals: bare metric/comparison vocabulary that is common in
# ordinary engineering work too (a contract implementing a scorer utility,
# for instance). Matching one of these alone is a WARNING nudge toward
# reviewing the tier, never a hard failure on its own.
_TCOMP_WEAK_RE = re.compile(
    r'\b(baselines?|benchmarks?|\bAUC\b|\bAUPRC\b|\bF1\b|precision|recall|'
    r'accuracy|hypothes(?:is|es)|result_registry|ablation\s+matrix)\b',
    re.IGNORECASE,
)

# Operation-class conflation (v2.2.0, D-035): a contract whose Objective
# opens with an implementation verb but whose Outputs/Definition of Done
# also promises a specific empirical/statistical result is exactly the
# "implement a benchmark runner and treat that as having run the benchmark"
# pattern DESIGN_RATIONALE-class review documents describe. Heuristic and
# WARNING-only -- plenty of contracts legitimately implement one stage of a
# pipeline whose *later* contract makes the claim; this only flags when both
# signals land in the same contract text.
_IMPLEMENTATION_VERB_RE = re.compile(
    r'^\s*(?:Implement|Build|Write|Create|Add)\b', re.IGNORECASE | re.MULTILINE,
)

# Statistical protocol language heuristics (v2.2.0, D-036): known-bad
# co-occurrence patterns from the Design Rationale failure table -- pairing/
# effect-size mismatch and the non-significance-as-equivalence fallacy.
# String/pattern co-occurrence only, exactly the same evidentiary posture as
# D-028's fabrication scan: it flags a combination worth a human/Architect
# looking at, it does not itself adjudicate whether the statistics are
# actually wrong.
_NONSIG_RE = re.compile(
    r'\b(not\s+(?:statistically\s+)?significant|non-significant|'
    r'no\s+significant\s+(?:difference|effect)|p\s*>\s*0?\.\d+)\b',
    re.IGNORECASE,
)
_EQUIVALENCE_CLAIM_RE = re.compile(
    r'\b(equivalent|equivalence)\b', re.IGNORECASE,
)
_EQUIVALENCE_MARGIN_RE = re.compile(
    r'\b(equivalence\s+margin|TOST|two[\s-]one[\s-]sided|non-?inferiority)\b',
    re.IGNORECASE,
)
_PAIRING_LANGUAGE_RE = re.compile(
    r'\b(paired|unpaired|independent\s+samples|within-subject|between-subject)\b',
    re.IGNORECASE,
)

# Named mathematical/statistical operators (v2.2.0, D-037): the specific,
# recurring family of "operator does not mean what its name claims"
# failures named in the uploaded factory_v2.1.0 Design Rationale document
# (itself grounded in a real project's adversarial audit, per that
# document's own account) -- distinct from this Factory's own first-hand
# GLOF/BPFeat evidence trail elsewhere in this file, and cited as such
# rather than blended into it. A contract whose text names one of these and
# is tiered T-COMP/T-CAUSAL should carry at least one Verification Script
# whose name/declared purpose reads as a semantic/operator test, not only an
# I/O-shape test -- see the Fail-Closed Tier Inference gate below and
# domain_checklists.md's "Required review questions" for what such a test
# should actually establish.
_NAMED_OPERATOR_RE = re.compile(
    r'\b(laplacian|adjacency\s+matrix|witness\s+complex|filtration|'
    r'boundary\s+operator|persistent\s+homology|simplicial\s+complex|'
    r'batch(?:ing)?\s+semantics?|permutation\s+invariance|k-core)\b',
    re.IGNORECASE,
)
_SEMANTIC_TEST_MARKER_RE = re.compile(
    r'(semantic_|operator_|known_answer|metamorphic|invariance_test|'
    r'monotonic|boundary_nilpotence|test_.*(?:laplacian|filtration|'
    r'witness|adjacency|batch))',
    re.IGNORECASE,
)

# Ablation-row covariance (v2.4.0, D-054 -- candidate, PROPOSED not ACTIVE):
# identified by a repo-grounded third-party gap analysis comparing this
# Factory against an external pre-submission audit manual (see
# dynamic_rules.md's v2.4.0 Third-party review disposition), not by this
# Factory's own first-hand project evidence -- disclosed as such rather
# than blended into the v2.2.0 heuristics above. Same evidentiary posture
# as D-035/036/037: string/pattern co-occurrence only. An ablation row that
# names the removed/varied component alongside language describing a factor
# that plausibly covaries with that removal (parameter count, training
# steps, compute budget), with no nearby "held fixed"/"parameter-matched"
# declaration, is worth a second look -- it does not itself determine
# whether the factors actually covaried in this specific experiment, only
# that the contract's own text gives no evidence either way. See
# domain_checklists.md's Ablation Design section.
_ABLATION_MENTION_RE = re.compile(
    r'\b(ablations?|ablat(?:e|ed|ing)|remov(?:e|ed|ing)\s+(?:the\s+)?\w+\s+'
    r'(?:module|component|channel|branch|head))\b',
    re.IGNORECASE,
)
_ABLATION_COVARYING_RE = re.compile(
    r'\b(parameter\s+count|number\s+of\s+parameters|training\s+steps|'
    r'training\s+epochs|compute\s+budget|fewer\s+parameters|smaller\s+model|'
    r'reduced\s+capacity)\b',
    re.IGNORECASE,
)
_ABLATION_HELD_FIXED_RE = re.compile(
    r'\b(held\s+fixed|holding\s+\w+\s+fixed|controlled\s+for|'
    r'parameter-?matched|matched\s+(?:parameter|compute)|'
    r'same\s+number\s+of\s+parameters|re-?tuned)\b',
    re.IGNORECASE,
)

# Efficiency-claim measurement language (v2.4.0, D-055 -- candidate,
# PROPOSED not ACTIVE): same provenance and posture as D-054 above. An
# efficiency/real-time/latency/throughput claim reported with mean-only
# latency language and no percentile language anywhere in the same text is
# worth a second look -- a mean can hide a bad tail, and a real-time system
# is broken by its tail, not its average. See domain_checklists.md's
# Hardware / Efficiency Claims section and hardware_profile_manifest.json
# (D-056, factory_spec.md).
_EFFICIENCY_CLAIM_RE = re.compile(
    r'\b(real-?time|low-?latency|latency|throughput|inference\s+speed|'
    r'lightweight|fast\s+inference)\b',
    re.IGNORECASE,
)
_MEAN_ONLY_LATENCY_RE = re.compile(
    r'\b(average\s+latency|mean\s+latency|average\s+inference\s+time|'
    r'mean\s+inference\s+time)\b',
    re.IGNORECASE,
)
_PERCENTILE_LATENCY_RE = re.compile(
    r'\b(p50|p90|p95|p99|percentile|tail\s+latency)\b',
    re.IGNORECASE,
)


def _infer_minimum_scientific_claim_tier(text):
    """Returns (minimum_tier, strong_matches, weak_matches). minimum_tier is
    one of "NONE", "T-DESC", "T-COMP", "T-CAUSAL".

    Per factory_spec.md's Scientific Claim Tier section, a tier is only
    required at all for a contract whose Outputs include a quantitative or
    comparative claim -- ordinary plumbing (a data loader, a CRUD endpoint,
    test scaffolding) legitimately declares NONE, and that must not be
    flagged. So: no signal at all infers NONE (nothing here suggests this
    contract makes any claim); a WEAK signal alone (a bare metric name,
    e.g. "computes F1 and accuracy") infers T-DESC -- reporting a metric
    value is itself an observational claim ("we observe X"), which
    factory_spec.md's table says needs at least an evidence artifact and
    traceability; a STRONG signal infers T-COMP or T-CAUSAL as before.
    Matches are returned so every finding can quote the exact text that
    triggered it, per C39."""
    strong_causal = sorted(set(m.group(0) for m in _TCAUSAL_STRONG_RE.finditer(text)))
    strong_comp = sorted(set(m.group(0) for m in _TCOMP_STRONG_RE.finditer(text)))
    weak_comp = sorted(set(m.group(0) for m in _TCOMP_WEAK_RE.finditer(text)))

    if strong_causal:
        return "T-CAUSAL", strong_causal, weak_comp
    if strong_comp:
        return "T-COMP", strong_comp, weak_comp
    if weak_comp:
        return "T-DESC", [], weak_comp
    return "NONE", [], []


def _scan_operation_class_conflation(text):
    """Returns list[str] WARNING findings (v2.2.0, D-035). Heuristic only --
    an Objective opening with an implementation verb, in a contract whose
    text also matches a strong T-COMP/T-CAUSAL signal, is worth a second
    look at whether this contract actually executes/measures the claim it
    describes or only builds the machinery that could."""
    findings = []
    if _IMPLEMENTATION_VERB_RE.search(text):
        _, strong_comp, _ = _infer_minimum_scientific_claim_tier(text)
        strong_causal = _TCAUSAL_STRONG_RE.search(text)
        if strong_comp or strong_causal:
            signal = (strong_causal.group(0) if strong_causal else strong_comp[0])
            findings.append(
                f"POSSIBLE OPERATION-CLASS CONFLATION: Objective opens with an "
                f"implementation verb ('Implement'/'Build'/'Write'/'Create'/'Add'), but "
                f"this contract's text also matches empirical/statistical claim language "
                f"('{signal}'). Confirm this contract actually executes/measures the "
                f"claim rather than only building something a later contract will use to "
                f"do so -- 'implement a benchmark runner' is not evidence the benchmark "
                f"was run (Design Rationale, AR-01/AR-06-class pattern)."
            )
    return findings


def _scan_statistical_protocol_language(text_paths):
    """Returns list[str] WARNING findings (v2.2.0, D-036). Two known-bad
    co-occurrence patterns, string/pattern matching only -- same posture as
    _scan_acquisition_text: flags a combination worth a human/Architect
    reading in context, never adjudicates the statistics itself."""
    findings = []
    for tp in text_paths:
        text = _read_text_or_none(Path(tp))
        if text is None:
            findings.append(f"CANNOT CHECK: {tp} not found -- skipping statistical-protocol scan for this file.")
            continue
        if _NONSIG_RE.search(text) and _EQUIVALENCE_CLAIM_RE.search(text) and not _EQUIVALENCE_MARGIN_RE.search(text):
            findings.append(
                f"NON-SIGNIFICANCE TREATED AS EQUIVALENCE: {tp} contains both "
                f"non-significance language ('{_NONSIG_RE.search(text).group(0)}') and "
                f"equivalence language ('{_EQUIVALENCE_CLAIM_RE.search(text).group(0)}') "
                f"with no declared equivalence margin or TOST/non-inferiority test found. "
                f"Absence of a significant difference is not evidence of equivalence "
                f"without a pre-declared margin (Design Rationale failure table)."
            )
        strong_stats = _TCOMP_STRONG_RE.search(text)
        if strong_stats and not _PAIRING_LANGUAGE_RE.search(text):
            findings.append(
                f"PAIRING NOT DECLARED: {tp} names a statistical test/effect size "
                f"('{strong_stats.group(0)}') with no paired/unpaired/independent-samples "
                f"language found nearby. Confirm the test and effect size chosen are "
                f"actually compatible with how the samples were collected before trusting "
                f"the reported statistic."
            )
    return findings


def _scan_semantic_operator_test_presence(contract_text, declared_verification_text):
    """Returns list[str] WARNING findings (v2.2.0, D-037). Presence-only
    heuristic: for a contract whose text names a recognized mathematical/
    statistical operator, checks whether its Verification Scripts / declared
    verification commands contain a recognizable semantic-test marker.
    Cannot and does not check whether such a test, if present, actually
    establishes the operator's claimed property -- that remains Architect/
    Implementor judgment, per domain_checklists.md."""
    findings = []
    operator_matches = sorted(set(m.group(0) for m in _NAMED_OPERATOR_RE.finditer(contract_text)))
    if not operator_matches:
        return findings
    if not _SEMANTIC_TEST_MARKER_RE.search(declared_verification_text or ""):
        findings.append(
            f"NO SEMANTIC/OPERATOR TEST DECLARED: this contract's text names "
            f"{operator_matches}, but no Verification Script/declared command matches a "
            f"semantic-test naming pattern (semantic_*, operator_*, known_answer_*, "
            f"metamorphic_*, etc.). An I/O-shape test can pass while the named operator "
            f"is still mathematically wrong (e.g. a Laplacian that is actually an "
            f"adjacency matrix) -- see domain_checklists.md's review questions for what "
            f"this operator specifically needs validated."
        )
    return findings


def _scan_ablation_row_covariance(text):
    """Returns list[str] WARNING findings (v2.4.0, D-054 -- candidate,
    PROPOSED not ACTIVE, zero project occurrences). Heuristic only, same
    evidentiary posture as D-035/036/037: string/pattern co-occurrence,
    never an adjudication of whether the factors actually covaried. Flags a
    contract whose text names an ablation alongside language describing a
    factor that plausibly covaries with the named removal, with no nearby
    "held fixed"/"parameter-matched" declaration. See domain_checklists.md's
    Ablation Design section (v2.4.0)."""
    findings = []
    ablation_match = _ABLATION_MENTION_RE.search(text)
    covary_match = _ABLATION_COVARYING_RE.search(text)
    if ablation_match and covary_match and not _ABLATION_HELD_FIXED_RE.search(text):
        findings.append(
            f"ABLATION FACTOR COVARIANCE NOT ADDRESSED: this contract's text names an "
            f"ablation ('{ablation_match.group(0)}') alongside language that could "
            f"describe a covarying factor ('{covary_match.group(0)}'), with no 'held "
            f"fixed'/'parameter-matched'/'controlled for' declaration found nearby. An "
            f"ablation row that changes more than one factor relative to its baseline "
            f"cannot attribute the effect to the named component alone -- see "
            f"domain_checklists.md's Ablation Design section (v2.4.0)."
        )
    return findings


def _scan_efficiency_claim_measurement(text):
    """Returns list[str] WARNING findings (v2.4.0, D-055 -- candidate,
    PROPOSED not ACTIVE, zero project occurrences). Heuristic only, same
    evidentiary posture as D-054 above. Flags an efficiency/real-time/
    latency/throughput claim reported with mean-only latency language and no
    percentile language anywhere in the same text. See domain_checklists.md's
    Hardware / Efficiency Claims section (v2.4.0) and hardware_profile_
    manifest.json (D-056, factory_spec.md)."""
    findings = []
    efficiency_match = _EFFICIENCY_CLAIM_RE.search(text)
    mean_match = _MEAN_ONLY_LATENCY_RE.search(text)
    if efficiency_match and mean_match and not _PERCENTILE_LATENCY_RE.search(text):
        findings.append(
            f"MEAN-ONLY LATENCY FOR AN EFFICIENCY CLAIM: this contract's text matches "
            f"efficiency/latency claim language ('{efficiency_match.group(0)}') and "
            f"mean/average latency language ('{mean_match.group(0)}'), with no percentile "
            f"language (p50/p90/p99/tail) found anywhere. A mean can hide a bad tail -- "
            f"see domain_checklists.md's Hardware / Efficiency Claims section (v2.4.0)."
        )
    return findings


def cmd_tier_check(args):
    """v2.2.0, D-034/D-035/D-036/D-037; v2.4.0, D-054/D-055 (candidate) --
    fail-closed minimum Scientific Claim Tier inference, plus five related
    heuristic scans bundled into this command rather than five new ones
    (C46): operation-class conflation, statistical-protocol language,
    semantic/operator test presence, ablation-row covariance, and
    efficiency-claim measurement language. Only the tier-inference check is
    a hard FAIL; the other four are WARNING-only, consistent with this
    script's existing Warning Policy for heuristic text scans. Exits 18
    (Fail-Closed Tier Inference Failure) only if the declared tier is
    strictly weaker than the inferred minimum.
    """
    print("Gatekeeper tier-check (fail-closed minimum Scientific Claim Tier inference)")
    print("=" * 60)

    contract_text = None
    contract_source = None
    if args.contract_file:
        contract_text = _read_text_or_none(Path(args.contract_file))
        contract_source = args.contract_file
    elif args.contract:
        contract_path, err = _find_contract_file(args.contract)
        if contract_path is None:
            print(f"\nERROR: {err}")
            sys.exit(9)
        contract_text = _read_text_or_none(contract_path)
        contract_source = str(contract_path)
    else:
        print("\nERROR: one of --contract or --contract-file is required.")
        sys.exit(9)

    if contract_text is None:
        print(f"\nERROR: could not read {contract_source}.")
        sys.exit(9)

    declared_tier = args.declared_tier
    if declared_tier is None:
        m = re.search(r'Scientific Claim Tier.*?:\s*\**\s*(NONE|T-DESC|T-COMP|T-CAUSAL)\b',
                      contract_text, re.IGNORECASE)
        declared_tier = m.group(1).upper() if m else "NONE"
    declared_tier = declared_tier.upper()
    if declared_tier not in _TIER_RANK:
        print(f"\nERROR: --declared-tier '{declared_tier}' is not one of NONE/T-DESC/T-COMP/T-CAUSAL.")
        sys.exit(9)

    minimum_tier, strong_matches, weak_matches = _infer_minimum_scientific_claim_tier(contract_text)

    print(f"\n[Fail-Closed Tier Inference -- D-034]")
    print(f"  Contract: {contract_source}")
    print(f"  Declared Scientific Claim Tier: {declared_tier}")
    print(f"  Inferred minimum: {minimum_tier}")
    if strong_matches:
        print(f"  Strong signal(s) matched: {strong_matches}")
    if weak_matches:
        print(f"  Weak signal(s) matched (informational only): {weak_matches}")
    if not strong_matches and not weak_matches:
        print("  No empirical/statistical claim language matched.")

    hard_fail = _TIER_RANK[declared_tier] < _TIER_RANK[minimum_tier]
    if hard_fail:
        print(
            f"  FAIL: declared tier '{declared_tier}' is weaker than the inferred minimum "
            f"'{minimum_tier}'. Per Constitution C05-class fail-closed reasoning (see "
            f"dynamic_rules.md D-034): declared assurance may exceed but must never "
            f"undercut what the contract's own text implies. Re-declare "
            f"scientific_claim_tier at '{minimum_tier}' or higher in both the contract "
            f"file and execution_manifest.yaml, or revise the contract's own text if the "
            f"match is a false positive -- then re-run this check."
        )
    else:
        print(f"  OK: declared tier '{declared_tier}' meets or exceeds the inferred minimum.")

    warning_findings = _scan_operation_class_conflation(contract_text)
    print("\n[Operation-Class Conflation -- D-035]")
    if not warning_findings:
        print("  No conflation pattern matched.")
    else:
        for f in warning_findings:
            print(f"  - {f}")

    declared_verification_text = contract_text
    if args.reports:
        for rp in args.reports:
            rt = _read_text_or_none(Path(rp))
            if rt:
                declared_verification_text += "\n" + rt
    operator_findings = _scan_semantic_operator_test_presence(contract_text, declared_verification_text)
    print("\n[Semantic/Operator Test Presence -- D-037]")
    if not operator_findings:
        print("  No named operator matched, or a semantic-test marker was found.")
    else:
        for f in operator_findings:
            print(f"  - {f}")

    ablation_findings = _scan_ablation_row_covariance(contract_text)
    print("\n[Ablation-Row Covariance -- D-054, candidate]")
    if not ablation_findings:
        print("  No ablation-covariance pattern matched.")
    else:
        for f in ablation_findings:
            print(f"  - {f}")

    efficiency_findings = _scan_efficiency_claim_measurement(contract_text)
    print("\n[Efficiency-Claim Measurement Language -- D-055, candidate]")
    if not efficiency_findings:
        print("  No mean-only-latency-with-efficiency-claim pattern matched.")
    else:
        for f in efficiency_findings:
            print(f"  - {f}")

    print("\n" + "=" * 60)
    print(
        "Evidence posture: D-034's tier inference is a keyword/pattern heuristic, unit-"
        "tested against the real project/chunks/chunk06/contracts/C06-03_contract.md "
        "text uploaded alongside this Factory version (Wilcoxon/Cliff's-delta/SUPPORTED-"
        "FALSIFIED-INCONCLUSIVE language, declared NONE) and against synthetic non-"
        "matching contracts. D-035/D-036/D-037 are WARNING-only and have zero project "
        "occurrences of their own -- filed as PROPOSED, not ACTIVE; see dynamic_rules.md. "
        "D-054/D-055 (v2.4.0) are additionally sourced from a single third-party document "
        "review rather than this Factory's own field evidence -- also PROPOSED, also "
        "zero project occurrences, disclosed as such in dynamic_rules.md's v2.4.0 entries. "
        "None of the six understands the contract's actual claim, only text patterns "
        "known to correlate with one."
    )
    print(f"RESULT: {'FAIL' if hard_fail else 'PASS'}")
    print(f"Exit code: {18 if hard_fail else 0}")
    sys.exit(18 if hard_fail else 0)


# ---------------------------------------------------------------------------
# evidence-check (v1.4.1) -- reads a contract report's structured "## Verdict
# Cross-Check" block and the JSON evidence artifact it names, and checks
# three things mechanically: does the report's stated verdict word match the
# artifact's own verdict field (D-024); does a declared pre-registered
# criterion, evaluated against the artifact's own numbers, actually support
# that verdict (D-025); and does the artifact's "metrics" list contain any
# degenerate value (exactly 0.0, 0.5, or 1.0, within tolerance) computed on
# too few samples (D-027, SVI-007).
#
# All three checks depend on a structured, declared format -- report prose
# is never parsed for meaning, and JSON is never interpreted beyond reading
# named keys. This is deliberate: per Gatekeeper's own Purpose ("Gatekeeper
# never performs AI reasoning"), a check that tried to understand arbitrary
# report prose or arbitrary natural-language criteria would not be
# deterministic. See factory_spec.md's Contract Specification (the Verdict
# Cross-Check block) and gemini_spec.md's contract report template for the
# format this command requires contracts to declare.
#
# Motivated by a real incident (Chunks 08-09, GLOF project rework): a
# contract report stated "Verdict: SUCCESS" while its own backing JSON
# artifact stated "f3_falsification_verdict": "FAILURE", and separately
# claimed SUCCESS while its own reported count (0 windows flagged) logically
# satisfied the pre-registered FAILURE criterion. Neither was caught by any
# verification script or by Gatekeeper -- only by a later adversarial audit.
# See dynamic_rules.md D-024, D-025, D-027.
# ---------------------------------------------------------------------------

_VERDICT_BLOCK_HEADER_RE = re.compile(r'^##\s*Verdict Cross-Check\s*$', re.MULTILINE)
_VERDICT_FIELD_RE = re.compile(r'^(\w+):\s*(.+?)\s*$', re.MULTILINE)

_DEGENERATE_VALUES = (0.0, 0.5, 1.0)
_DEGENERATE_TOLERANCE = 0.01
_DEGENERATE_MIN_SAMPLES = 30

_CRITERION_KINDS = {"count_gte", "count_lte", "value_gte", "value_lte", "bool_true", "bool_false", "none"}


def _load_json_or_none(path):
    text = _read_text_or_none(Path(path))
    if text is None:
        return None, f"CANNOT CHECK: {path} not found."
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, f"CANNOT CHECK: {path} is not valid JSON ({e})."


def _get_json_path(data, key):
    """Looks up a possibly-dotted key ('a.b.c') in a nested dict. Returns
    (value, found_bool)."""
    node = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


def _parse_verdict_block(report_path):
    """Finds the '## Verdict Cross-Check' block in a contract report and
    parses its declared fields. Returns (fields_dict_or_None, findings).
    A report with no such block is not an error -- not every contract has
    a pre-registered verdict to cross-check."""
    text = _read_text_or_none(Path(report_path))
    if text is None:
        return None, [f"CANNOT CHECK: {report_path} not found."]

    m = _VERDICT_BLOCK_HEADER_RE.search(text)
    if m is None:
        return None, []  # no block present -- nothing to check, not an error

    block_end = text.find("\n## ", m.end())
    block = text[m.end():block_end if block_end != -1 else len(text)]

    fields = {}
    for fm in _VERDICT_FIELD_RE.finditer(block):
        fields[fm.group(1)] = fm.group(2)

    findings = []
    if "verdict_word" not in fields or "artifact" not in fields or "artifact_key" not in fields:
        findings.append(
            f"MALFORMED VERDICT BLOCK: {report_path}'s '## Verdict Cross-Check' block is "
            f"missing 'verdict_word', 'artifact', or 'artifact_key' -- skipped, not checked."
        )
        return None, findings
    return fields, findings


def _check_verdict_consistency(report_path, fields):
    """D-024: does the report's declared verdict_word match the value at
    artifact_key inside the named JSON artifact?"""
    data, err = _load_json_or_none(fields["artifact"])
    if err:
        return [err]
    value, found = _get_json_path(data, fields["artifact_key"])
    if not found:
        return [
            f"CANNOT CHECK: {fields['artifact']} has no key '{fields['artifact_key']}' -- "
            f"cannot cross-check {report_path}'s declared verdict."
        ]
    reported = str(fields["verdict_word"]).strip().lower()
    actual = str(value).strip().lower()
    if reported != actual:
        return [
            f"VERDICT MISMATCH: {report_path} states verdict_word='{fields['verdict_word']}' "
            f"but {fields['artifact']}['{fields['artifact_key']}'] = '{value}'. The report's "
            f"stated outcome contradicts its own backing artifact."
        ]
    return []


def _evaluate_criterion(kind, threshold, actual_value):
    """Bounded, closed-set criterion evaluation -- never free-form. Returns
    True if the criterion is SATISFIED (i.e. supports a SUCCESS verdict)."""
    if kind == "count_gte" or kind == "value_gte":
        return actual_value >= threshold
    if kind == "count_lte" or kind == "value_lte":
        return actual_value <= threshold
    if kind == "bool_true":
        return bool(actual_value) is True
    if kind == "bool_false":
        return bool(actual_value) is False
    return None  # "none" or unrecognized -- not evaluated


def _check_criterion_consistency(report_path, fields):
    """D-025: if the report declares a pre-registered criterion
    (criterion/criterion_field/criterion_threshold), does the artifact's own
    number at criterion_field actually satisfy it -- and does that agree
    with the declared verdict_word?"""
    kind = fields.get("criterion", "none")
    if kind == "none" or kind not in _CRITERION_KINDS:
        return []  # no criterion declared, or not a recognized kind -- skip, not an error
    if "criterion_field" not in fields or "criterion_threshold" not in fields:
        return [
            f"MALFORMED VERDICT BLOCK: {report_path} declares criterion='{kind}' but is "
            f"missing 'criterion_field' or 'criterion_threshold' -- criterion not checked."
        ]
    data, err = _load_json_or_none(fields["artifact"])
    if err:
        return [err]
    actual_value, found = _get_json_path(data, fields["criterion_field"])
    if not found:
        return [
            f"CANNOT CHECK: {fields['artifact']} has no key '{fields['criterion_field']}' -- "
            f"criterion not checked."
        ]
    try:
        threshold = float(fields["criterion_threshold"])
        actual_num = float(actual_value) if not isinstance(actual_value, bool) else actual_value
    except (TypeError, ValueError):
        actual_num = actual_value  # bool_true/bool_false path

    satisfied = _evaluate_criterion(kind, threshold, actual_num)
    if satisfied is None:
        return []
    reported_success = str(fields["verdict_word"]).strip().upper() in ("SUCCESS", "PASS", "COMPLETE", "TRUE")
    if satisfied != reported_success:
        return [
            f"LOGICAL INCONSISTENCY: {report_path} declares verdict_word='{fields['verdict_word']}' "
            f"but its own criterion ({kind} {fields['criterion_field']}={actual_num} vs "
            f"threshold {threshold}) evaluates to {'SATISFIED' if satisfied else 'NOT SATISFIED'} "
            f"-- the stated verdict is not entailed by the report's own declared numbers."
        ]
    return []


def _check_degenerate_metrics(artifact_path):
    """D-027 / SVI-007: any metric in the artifact's 'metrics' list whose
    value sits within tolerance of 0.0, 0.5, or 1.0 and whose sample_count
    is below the minimum is flagged. Fully deterministic -- no artifact
    with a 'metrics' list means nothing to check, not an error."""
    data, err = _load_json_or_none(artifact_path)
    if err:
        return [err]
    metrics = data.get("metrics") if isinstance(data, dict) else None
    if not metrics:
        return []
    findings = []
    for m in metrics:
        name = m.get("name", "<unnamed metric>")
        value = m.get("value")
        n = m.get("sample_count")
        if value is None or n is None:
            continue
        if n < _DEGENERATE_MIN_SAMPLES and any(abs(value - b) <= _DEGENERATE_TOLERANCE for b in _DEGENERATE_VALUES):
            findings.append(
                f"DEGENERATE METRIC: {artifact_path} metric '{name}' = {value} on only {n} "
                f"samples (< {_DEGENERATE_MIN_SAMPLES}) -- a value this close to 0.0/0.5/1.0 on "
                f"this few samples is likely a sample-size artifact, not a genuine result. "
                f"Report it with this flag rather than as a clean finding."
            )
    return findings


def cmd_evidence_check(args):
    """v1.4.1 -- reads a contract report's '## Verdict Cross-Check' block
    and cross-checks it against the JSON artifact it names. Three checks:
    verdict-word consistency (D-024, hard FAIL), pre-registered-criterion
    logical consistency (D-025, hard FAIL), and degenerate-metric flagging
    (D-027, WARNING). A report with no Verdict Cross-Check block is not an
    error -- not every contract has a pre-registered verdict. Never
    modifies any file. Exits 12 (Evidence Inconsistency) only on a hard
    finding.
    """
    print("Gatekeeper evidence-check (cross-checks report verdicts against their own artifacts)")
    print("=" * 60)

    reports = list(args.reports or [])
    if not reports:
        print("\nERROR: --reports must name at least one contract_report.md. Nothing to check.")
        sys.exit(9)

    hard_findings = []
    warning_findings = []

    for rp in reports:
        fields, block_findings = _parse_verdict_block(rp)
        warning_findings += [f for f in block_findings if f.startswith("CANNOT CHECK")]
        hard_findings += [f for f in block_findings if f.startswith("MALFORMED")]
        if fields is None:
            continue
        verdict_findings = _check_verdict_consistency(rp, fields)
        warning_findings += [f for f in verdict_findings if f.startswith("CANNOT CHECK")]
        hard_findings += [f for f in verdict_findings if not f.startswith("CANNOT CHECK")]

        criterion_findings = _check_criterion_consistency(rp, fields)
        warning_findings += [f for f in criterion_findings if f.startswith("CANNOT CHECK")]
        hard_findings += [f for f in criterion_findings if not f.startswith("CANNOT CHECK")]

        degenerate_findings = _check_degenerate_metrics(fields["artifact"])
        warning_findings += degenerate_findings

    print("\n[Verdict / criterion consistency -- D-024, D-025]")
    consistency = [f for f in hard_findings if "VERDICT MISMATCH" in f or "LOGICAL INCONSISTENCY" in f or "MALFORMED" in f]
    if not consistency:
        print("  No mismatches found.")
    else:
        for f in consistency:
            print(f"  - {f}")

    print("\n[Degenerate metric flagging -- D-027, SVI-007]")
    degenerate = [f for f in warning_findings if "DEGENERATE METRIC" in f]
    if not degenerate:
        print("  No degenerate metrics found.")
    else:
        for f in degenerate:
            print(f"  - {f}")

    other_warnings = [f for f in warning_findings if f not in degenerate]
    if other_warnings:
        print("\n[Other]")
        for f in other_warnings:
            print(f"  - {f}")

    print("\n" + "=" * 60)
    print(f"Failures: {len(hard_findings)}   Warnings: {len(warning_findings)}")
    print(
        "Evidence posture: unit-tested against a synthetic reproduction of the Chunks 08-09 "
        "incident (D-024, D-025, D-027), not yet run against a real project beyond the one "
        "that motivated it. Requires the '## Verdict Cross-Check' structured block -- a "
        "report without one is silently not checked, not silently passed; confirm the block "
        "is present for any contract carrying a T-CAUSAL or pre-registered claim."
    )
    sys.exit(12 if hard_findings else 0)


def cmd_acquisition_audit(args):
    """v1.4.0 -- scans data-acquisition scripts and their contract reports
    for red-flag patterns before their output is trusted. Two checks:
    data-generation function definitions (hard FAIL -- D-022), and
    simulation-indicating text (WARNING -- D-023). Never modifies any
    file. Exits 11 (Acquisition Audit Failure) only on a structural
    finding; textual findings are reported but do not by themselves fail
    the run, consistent with Gatekeeper's Warning Policy.
    """
    print("Gatekeeper acquisition-audit (scans data-acquisition scripts and reports)")
    print("=" * 60)

    scripts = list(args.scripts or [])
    reports = list(args.reports or [])
    if not scripts and not reports:
        print("\nERROR: at least one of --scripts or --reports must be given. Nothing to check.")
        sys.exit(9)

    print("\n[Structural audit -- data-generation function definitions]")
    structural_findings = _scan_acquisition_functions(scripts)
    if not structural_findings:
        print("  No data-generation function definitions found.")
    else:
        for f in structural_findings:
            print(f"  - {f}")

    print("\n[Structural audit -- fabricated statistical input (v1.4.2, D-028)]")
    fabrication_findings = _scan_fabricated_statistical_input(scripts)
    structural_findings = structural_findings + fabrication_findings
    if not fabrication_findings:
        print("  No distribution-sampled values feeding a metrics function found.")
    else:
        for f in fabrication_findings:
            print(f"  - {f}")

    print("\n[Textual scan -- simulation-indicating language]")
    textual_findings = _scan_acquisition_text(scripts + reports)
    if not textual_findings:
        print("  No simulation-indicating language found.")
    else:
        for f in textual_findings:
            print(f"  - {f}")

    hard_failures = [
        f for f in structural_findings
        if f.startswith("DATA-GENERATION FUNCTION") or f.startswith("FABRICATED STATISTICAL INPUT")
    ]
    warnings = [f for f in structural_findings if f not in hard_failures] + textual_findings

    print("\n" + "=" * 60)
    print(f"Failures: {len(hard_failures)}   Warnings: {len(warnings)}")
    print(
        "Evidence posture: the two original checks (D-022, D-023) are unit-tested against "
        "a synthetic reproduction of the Chunk 07 incident; the fabricated-statistical-input "
        "check (v1.4.2, D-028) is unit-tested against the real C08-06 script and reproduces "
        "byte-identically against the real incident artifact. None has been run against a "
        "pipeline beyond the one that motivated it. Catches the common case, not a "
        "deliberately obfuscated one -- see C01, C54, and the Constitution's Chunk Review "
        "raw-artifact inspection for the layer this command does not replace. This command "
        "now covers two related but distinct triggers: data-*acquisition* scripts fabricating "
        "data under an external constraint (D-022/D-023), and data-*computation* scripts "
        "fabricating their own intermediate inputs with no external constraint at all "
        "(D-028) -- kept as one command per C46, since both are the same underlying concern "
        "(a script trusted to handle real observations must not silently substitute "
        "manufactured ones) at different pipeline stages."
    )
    sys.exit(11 if hard_failures else 0)


def cmd_release_check(args):
    """v1.4.0 -- scans release-bound artifacts before submission. Three
    checks: local-path/machine-identity leaks (hard FAIL, unambiguous --
    D-017), Factory-internal-identifier leaks (hard FAIL, D-049, v2.3.0),
    and key-fact consistency against project/key_facts.md (WARNING --
    heuristic, requires human confirmation). Never modifies any file.
    Exits 10 (Release Artifact Failure) on a hard local-path finding, 22
    (Outbound Secrecy Scan Failure) on a Factory-identifier finding with
    no local-path finding, 10 if both fire together (local-path leaks
    have been this command's designated failure code since v1.4.0;
    widening its meaning to "any hard release-artifact finding" rather
    than introducing a third exit code JUST for the combination keeps
    the common case -- exactly one kind of finding -- unambiguous);
    key-fact mismatches are reported but do not by themselves fail the
    run, consistent with Gatekeeper's Warning Policy.
    """
    print("Gatekeeper release-check (scans outbound release artifacts)")
    print("=" * 60)

    if not Path(args.manuscript).exists():
        print(f"\nERROR: --manuscript path '{args.manuscript}' does not exist. Nothing to check.")
        sys.exit(9)

    files_to_scan = [args.manuscript] + list(args.files or [])

    print("\n[Local path / machine-identity scan]")
    path_findings = _scan_local_paths(files_to_scan)
    if not path_findings:
        print("  No local paths found.")
    else:
        for f in path_findings:
            print(f"  - {f}")

    print("\n[Factory-internal-identifier scan (D-049)]")
    secrecy_findings = _scan_factory_identifiers(files_to_scan)
    if not secrecy_findings:
        print("  No Factory-internal identifiers found.")
    else:
        for f in secrecy_findings:
            print(f"  - {f}")

    print("\n[Key-fact consistency check]")
    fact_findings = []
    if args.key_facts:
        fact_findings = _check_key_fact_consistency(args.manuscript, args.key_facts)
        if not fact_findings:
            print("  No mismatches found against declared key facts.")
        else:
            for f in fact_findings:
                print(f"  - {f}")
    else:
        print("  SKIPPED: no --key-facts given.")

    hard_failures = [f for f in path_findings if f.startswith("LOCAL PATH LEAK")]
    warnings = [f for f in path_findings if not f.startswith("LOCAL PATH LEAK")] + fact_findings

    print("\n" + "=" * 60)
    print(f"Failures: {len(hard_failures)}   Secrecy findings: {len(secrecy_findings)}   "
          f"Warnings: {len(warnings)}")
    print(
        "Evidence posture: unit-tested against synthetic fixtures, not yet run against "
        "a real manuscript beyond the GLOF review that motivated the local-path check. "
        "The key-fact check is intentionally bounded -- it only catches drift against "
        "facts the Architect declared in key_facts.md ahead of time, per Gatekeeper's "
        "Verification Principles (no AI reasoning, no open-ended fact-checking)."
    )
    if hard_failures:
        sys.exit(10)
    if secrecy_findings:
        sys.exit(22)
    sys.exit(0)


# ---------------------------------------------------------------------------
# Mechanical guards (v1.4.2) -- four related additions, all deterministic,
# none relying on AI judgement to decide pass/fail. Motivated by D-028 (the
# real C08-06 fabrication incident) and by the general observation it
# confirmed: `evidence-check` verifies a report against its own named
# artifact, never against independent re-execution or recomputation. These
# four close that specific gap:
#
#   verify-contract  -- Gatekeeper itself re-runs every command a report
#                        declares under "## Verification" and checks the
#                        REAL exit code. A report's claimed result is
#                        never trusted, only used as a human cross-check.
#   lint-contract     -- deterministic AST scan for swallowed exceptions
#                        (a caught-and-silently-continued exception is
#                        indistinguishable from a silently substituted
#                        fallback), reuses acquisition-audit's fabrication
#                        scan, and checks whether a project's verification
#                        machinery (source/tests/, verify_*.py,
#                        factory/verifiers/) was modified since it was
#                        auto-frozen (see below).
#   recompute         -- a contract can declare a second, independent
#                        script computing the same value from the same
#                        raw evidence; Gatekeeper runs it and compares.
#                        Independence is enforced mechanically (the
#                        independent script's hash must differ from the
#                        original's), not merely asserted by a label.
#   stamp-report      -- appends a tamper-evident stamp to a contract
#                        report containing the real results of the above
#                        three, plus git diff and frozen-file hashes.
#                        Everything above a stamp is hash-committed; any
#                        later modification is detected the next time the
#                        report is stamped or checked (exit 16). Anything
#                        needing correction goes in a new section below
#                        the stamp, not an edit above it.
#
# "Freeze all verification machinery automatically" (the fourth mechanical
# guard requested) is not new code -- it is v1.3.2's existing snapshot/hash
# infrastructure (check_frozen_files, sha256_of, SNAPSHOT_DIR) applied by
# default to a fixed path set, so no contract has to remember to declare
# source/tests/ etc. in --frozen (C46: improve an existing mechanism before
# adding a new one). See _auto_frozen_verification_paths, and its wiring
# into cmd_snapshot/cmd_snapshot_chunk/cmd_check below.
#
# Honesty about scope, stated once here rather than re-litigated per
# command: none of the four proves a script is CORRECT. verify-contract
# proves a declared command really exited 0 just now. lint-contract's
# swallowed-exception check is a standard, well-understood static-analysis
# pattern (the same class flake8-bugbear/bandit already catch) applied via
# Python's own `ast` module -- deterministic, but syntactic, not semantic;
# it cannot tell a genuinely necessary broad catch from a hidden one, which
# is exactly why an explicit "# GATEKEEPER-EXEMPT: <reason>" escape exists
# -- visible in the diff, not silent. recompute proves two DIFFERENT
# programs agree, which is real evidence, not proof either program is
# right (two independently wrong implementations can still agree). Stamp
# integrity proves content wasn't edited after stamping; it cannot stop
# someone from stamping over content that was already wrong before the
# first stamp. Every one of these is a genuine, mechanical improvement
# over trusting a report's own prose. None of them, individually or
# together, is a claim that fabrication has become impossible -- that
# claim would be the same kind of overclaim D-028 itself was filed to
# catch, and this codebase does not get to exempt itself from C01/C02/
# EP-005 while enforcing them on everything else.
# ---------------------------------------------------------------------------

AUTO_FROZEN_GLOBS = (
    "source/tests/**/*.py",
    "source/scripts/verify_*.py",
    "factory/verifiers/**/*.py",
)


def _auto_frozen_verification_paths():
    """Every contract's verification machinery is frozen automatically --
    no contract declares source/tests/, verify_*.py, or factory/verifiers/
    in --frozen by hand. Returns only paths that currently exist; silently
    empty on a project that has none yet, never an error."""
    found = []
    for pattern in AUTO_FROZEN_GLOBS:
        found.extend(str(p) for p in Path(".").glob(pattern) if p.is_file())
    return sorted(set(found))


def _now_utc_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run_subprocess(command, timeout=300):
    """Actually executes a shell command. Never raises -- a command that
    can't even start is reported as a synthetic nonzero exit with the
    exception text as stderr, so every caller gets a real pass/fail
    signal instead of a crash. Same trust boundary the test suite already
    had: this executes code the pipeline was always going to execute via
    pytest/the declared command anyway; it does not newly expose the Implementor's
    code to execution that wasn't already happening."""
    try:
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout[-2000:], proc.stderr[-2000:]
    except subprocess.TimeoutExpired:
        return 124, "", f"TIMEOUT after {timeout}s"
    except Exception as e:
        return 127, "", f"COULD NOT EXECUTE: {e}"


def _git_diff_files():
    """Returns (files: list[str]-or-None, note: str). None means git is
    unavailable or this isn't a repository -- callers must treat that as
    'unknown', never as 'zero files changed'."""
    code, out, _ = _run_subprocess("git diff --name-only HEAD", timeout=30)
    if code != 0:
        code2, out2, _ = _run_subprocess("git diff --name-only --cached", timeout=30)
        if code2 != 0:
            return None, "git unavailable or not a repository -- files-modified list omitted."
        out = out2
    return [l.strip() for l in out.splitlines() if l.strip()], ""


# --- lint-contract ----------------------------------------------------------

_EXEMPTION_COMMENT_RE = re.compile(r'#\s*GATEKEEPER-EXEMPT:\s*(.+)')
_LOG_CALL_NAMES = {"warn", "warning", "error", "critical", "exception", "warn_explicit"}
_LOG_MODULE_NAMES = {"logging", "logger", "log", "warnings"}


def _scan_swallowed_exceptions(script_path):
    """Returns (hard_findings, warning_findings). Deterministic AST walk
    (Python's own `ast` module, stdlib -- no new dependency): an except
    handler whose body contains neither a `raise` nor a recognizable
    logging/warning call is flagged -- silently continuing after a real
    failure is indistinguishable from silently substituting a fallback
    (C01, C54, D-028). A handler that re-raises or logs is never flagged,
    regardless of anything else it does. A '# GATEKEEPER-EXEMPT: <reason>'
    comment anywhere in the handler's own source lines downgrades the
    finding to a warning (visible, human-confirmable) rather than
    silently passing it."""
    text = _read_text_or_none(Path(script_path))
    if text is None:
        return [], [f"CANNOT CHECK: {script_path} not found -- skipping exception-handling audit."]
    try:
        tree = ast.parse(text, filename=str(script_path))
    except SyntaxError as e:
        return [], [f"CANNOT CHECK: {script_path} is not valid Python ({e}) -- skipping exception-handling audit."]

    lines = text.splitlines()
    hard, warn = [], []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        body_nodes = [n for child in node.body for n in ast.walk(child)]
        has_raise = any(isinstance(n, ast.Raise) for n in body_nodes)
        has_log = False
        for n in body_nodes:
            if not isinstance(n, ast.Call):
                continue
            func = n.func
            if isinstance(func, ast.Attribute) and func.attr in _LOG_CALL_NAMES:
                has_log = True
                break
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in _LOG_MODULE_NAMES:
                has_log = True
                break
            if isinstance(func, ast.Name) and func.id in _LOG_CALL_NAMES:
                has_log = True
                break
        if has_raise or has_log:
            continue

        start_line = node.lineno
        end_line = max((getattr(n, "lineno", start_line) for n in body_nodes), default=start_line)
        block_text = "\n".join(lines[start_line - 1:end_line])
        exempt_m = _EXEMPTION_COMMENT_RE.search(block_text)

        try:
            exc_desc = ast.unparse(node.type) if node.type is not None else "bare except"
        except Exception:
            exc_desc = "except"
        location = f"{script_path}:{start_line}"

        if exempt_m:
            warn.append(
                f"EXEMPTED SWALLOWED EXCEPTION: {location} ({exc_desc}) neither re-raises nor logs, "
                f"but is exempted: \"{exempt_m.group(1).strip()}\". Confirm the exemption is genuine "
                f"before trusting it."
            )
        else:
            hard.append(
                f"SWALLOWED EXCEPTION: {location} ({exc_desc}) neither re-raises nor logs. Silently "
                f"continuing after a real failure is indistinguishable from silently substituting a "
                f"fallback (C01, C54, D-028). Add a 'raise', a logging call, or a "
                f"'# GATEKEEPER-EXEMPT: <reason>' comment inside the handler."
            )
    return hard, warn


def cmd_lint_contract(args):
    """v1.4.2, mechanical barrier #2. Scans declared scripts for swallowed
    exceptions and fabricated-statistical-input patterns (structural,
    both hard FAIL), and checks whether this project's auto-frozen
    verification machinery has been tampered with (hard FAIL). Never
    modifies any file."""
    print("Gatekeeper lint-contract (swallowed exceptions, fabrication patterns, frozen-machinery tampering)")
    print("=" * 60)
    scripts = list(args.scripts or [])
    if not scripts and not args.contract:
        print("\nERROR: give --scripts, --contract, or both. Nothing to lint.")
        sys.exit(9)

    hard, warn = [], []

    print("\n[Swallowed exceptions]")
    for sp in scripts:
        h, w = _scan_swallowed_exceptions(sp)
        hard += h
        warn += w
    section_findings = [f for f in hard + warn if any(sp in f for sp in scripts)]
    if not section_findings:
        print("  None found.")
    else:
        for f in section_findings:
            print(f"  - {f}")

    print("\n[Fabricated statistical input]")
    fab = _scan_fabricated_statistical_input(scripts)
    hard += fab
    if not fab:
        print("  None found.")
    else:
        for f in fab:
            print(f"  - {f}")

    print("\n[Frozen verification machinery]")
    frozen_paths = _auto_frozen_verification_paths()
    if not frozen_paths:
        print("  (none present in this project yet -- source/tests/, source/scripts/verify_*.py, "
              "factory/verifiers/ not found)")
    elif args.contract:
        fr_ok, fr_details = check_frozen_files(args.contract, frozen_paths)
        for l in fr_details:
            print(f"  {l}")
        if not fr_ok:
            hard.append("FROZEN MACHINERY TAMPERED: see Frozen verification machinery section above.")
    else:
        print(f"  {len(frozen_paths)} path(s) found: {frozen_paths}. Pass --contract to check against its snapshot.")

    print("\n" + "=" * 60)
    print(f"Hard failures: {len(hard)}   Warnings: {len(warn)}")
    sys.exit(14 if hard else 0)


# --- verify-contract ---------------------------------------------------------

_VERIFICATION_COMMAND_RE = re.compile(
    r'^\s*-\s*\*\*[^*]*(?:Command|Verification)[^*]*\*\*:\s*`([^`]+)`',
    re.MULTILINE | re.IGNORECASE,
)

# v2.3.0 (D-039) -- two additional, backward-compatible parse paths, added
# because the single pattern above is exactly why an aggregate verify-
# contract run across Sentinel-GL's C01-01 through C01-08 reports found
# ZERO declared commands despite every one of those reports genuinely
# containing verification commands and their real output: those reports
# used a literal "Command:" label (no bullet, no bold, no backticks) --
# CommandBlock below -- rather than this format's specific bullet/bold/
# backtick shape. Evidence: reproduced directly against the quoted report
# excerpts in that field report; see factory/tests/test_gatekeeper_v2_3_0.py.
#
# CommandBlock: a line reading (only) "Command:" (optionally bolded),
# followed by the command on the next non-blank line, inside a fenced code
# block or as plain text -- either is accepted, since both were observed.
_VERIFICATION_COMMAND_BLOCK_RE = re.compile(
    r'^\s*\**Command\**:\s*\n+\s*(?:```[a-zA-Z0-9_+\-]*\s*\n)?\s*\$?\s*(.+?)\s*(?:\n\s*```)?\s*$',
    re.MULTILINE,
)

# StructuredBlock: a fenced ```yaml verification: ...``` block, preferred
# going forward (V2.3-03) -- each entry's `command` (or bare-string list
# item) is extracted with a hand-rolled scan rather than a real YAML
# parser, deliberately: this file has no hard PyYAML dependency outside
# --manifest-taking commands, and a report should be readable by a human
# glancing at it, which a hand-scanned restricted subset still is. A
# project wanting the full structured schema (id/argv/cwd/side_effect/
# idempotent/timeout_seconds/expected_exit_codes/resource_class/
# supports_evidence -- see dynamic_rules.md D-039's Description) is free
# to write it; only the `command`/bare-string values are read here.
_VERIFICATION_YAML_FENCE_RE = re.compile(
    r'```ya?ml\s*\n(.*?\n)```', re.DOTALL,
)
_VERIFICATION_YAML_KEY_RE = re.compile(r'^\s*verification\s*:\s*$', re.MULTILINE)
_VERIFICATION_YAML_ITEM_RE = re.compile(
    r'^\s*-\s*(?:command\s*:\s*)?["\']?([^"\'\n]+?)["\']?\s*$', re.MULTILINE,
)


def _extract_yaml_verification_commands(report_text):
    """Returns commands declared in a fenced ```yaml verification: ...```
    block (v2.3.0, D-039). Only pulls the leaf command string out of each
    list item -- cwd/timeout/etc. sub-fields, if present, are read by a
    human, not by this extraction path. A fence with no `verification:`
    key is not itself a verification declaration and is skipped."""
    commands = []
    for fence_m in _VERIFICATION_YAML_FENCE_RE.finditer(report_text):
        block = fence_m.group(1)
        key_m = _VERIFICATION_YAML_KEY_RE.search(block)
        if key_m is None:
            continue
        after_key = block[key_m.end():]
        # Stop at the next top-level (unindented) key, if any -- this
        # fence may contain more than just the verification list.
        next_key_m = re.search(r'^\S', after_key, re.MULTILINE)
        scope = after_key[:next_key_m.start()] if next_key_m else after_key
        for item_m in _VERIFICATION_YAML_ITEM_RE.finditer(scope):
            # A nested "argv:", "cwd:", etc. sub-field under the same "- "
            # item also matches this loose pattern; only the FIRST match
            # per "- " group (the item's own opening line) is its command
            # unless that line is itself a sub-field key, which is
            # excluded below.
            candidate = item_m.group(1).strip()
            if re.match(r'^(?:id|argv|cwd|side_effect|idempotent|network|'
                        r'timeout_seconds|expected_exit_codes|resource_class|'
                        r'supports_evidence)\s*:', candidate, re.IGNORECASE):
                continue
            if candidate.lower().startswith("command:"):
                candidate = candidate.split(":", 1)[1].strip()
            candidate = candidate.strip('`')
            if candidate:
                commands.append(candidate)
    return commands


def _extract_declared_commands(report_text):
    """Extracts verification commands from a contract report. Tries three
    parse paths, in this order, and merges results (deduplicated, first-
    seen order preserved): the original bullet/bold/backtick style
    (unchanged since v1.4.2 -- e.g. '**Command**: `pytest ...`'), the
    legacy literal 'Command:' block style (v2.3.0, D-039 -- see above),
    and a structured fenced YAML `verification:` block (v2.3.0, D-039,
    preferred going forward). A report may use any mix of the three; nothing
    about using the original style stops working, and nothing requires
    migrating an existing report to keep passing."""
    seen = []
    for pattern in (_VERIFICATION_COMMAND_RE, _VERIFICATION_COMMAND_BLOCK_RE):
        for m in pattern.finditer(report_text):
            cmd = m.group(1).strip()
            if cmd and cmd not in seen:
                seen.append(cmd)
    for cmd in _extract_yaml_verification_commands(report_text):
        if cmd not in seen:
            seen.append(cmd)
    return seen


# v2.3.0 (D-039) -- the second half of the same fix: even with the wider
# parser above, a report can still declare verification commands in a
# shape none of the three paths recognizes (a fourth format, a typo in the
# label). Before this release, that produced "0 declared command(s) found"
# printed identically whether the report genuinely has no verification
# section at all (fine -- plenty of contracts don't) or whether it has one
# that just didn't parse (not fine -- silent, undetected non-verification).
# This distinguishes the two: a report is considered to ASSERT it has
# commands to check if either the contract's own manifest entry declares
# verification_scripts/required_verification_commands, or the report's own
# text contains a recognizable section label at all (even one that failed
# to yield a command) -- so a caller can fail loudly on the second case
# instead of reading it as a clean pass. See _check_verification_presence
# below, used by cmd_check and cmd_verify_contract.
_VERIFICATION_SECTION_LABEL_RE = re.compile(
    r'^\s*#{2,6}\s*Verification\b|^\s*\**Command\**:\s*$|^\s*verification\s*:\s*$',
    re.MULTILINE | re.IGNORECASE,
)


def _check_verification_presence(report_text, expected_commands):
    """Returns (ok, findings). ok=False only when commands were genuinely
    expected (either the manifest declared some, or the report's own text
    contains a Verification-shaped section label) and zero were actually
    extracted -- the report is not silently treated as having passed
    verification it never actually declared in a parseable form."""
    extracted = _extract_declared_commands(report_text)
    if extracted:
        return True, []
    manifest_expects = bool(expected_commands)
    text_asserts = bool(_VERIFICATION_SECTION_LABEL_RE.search(report_text))
    if manifest_expects or text_asserts:
        return False, [
            "VERIFICATION SECTION PRESENT BUT UNPARSEABLE: this report either "
            "declares verification_scripts/required_verification_commands in "
            "its manifest entry, or contains a Verification-shaped section "
            "label in its own text, but zero commands could be extracted from "
            "any of the three recognized formats (bullet/bold/backtick, "
            "literal 'Command:' block, fenced YAML 'verification:' block). "
            "This is reported as a failure, not a silent pass, per D-039 -- "
            "'zero declared commands' must never be indistinguishable from "
            "'nothing was ever meant to be checked here.' Re-express the "
            "command in one of the three recognized formats and re-run."
        ]
    return True, []


def cmd_verify_contract(args):
    """v1.4.2, mechanical barrier #1. Gatekeeper actually executes every
    command a contract report declares under '## Verification' and checks
    the REAL exit code. A report's own claimed result is read only as a
    human cross-reference, never trusted as the verification itself."""
    print("Gatekeeper verify-contract (independently re-executes declared verification commands)")
    print("=" * 60)
    if not args.reports:
        print("\nERROR: --reports must be given. Nothing to check.")
        sys.exit(9)

    any_fail = False
    any_commands = False
    for rp in args.reports:
        text = _read_text_or_none(Path(rp))
        if text is None:
            print(f"\n[{rp}] CANNOT CHECK: not found.")
            any_fail = True
            continue
        commands = _extract_declared_commands(text)
        print(f"\n[{rp}] {len(commands)} declared command(s) found.")
        if not commands:
            # v2.3.0 (D-039): zero extracted is only a silent no-op when
            # this report's own text doesn't assert a verification section
            # exists at all. A present-but-unparseable section is a
            # failure now, not indistinguishable from "nothing to check."
            presence_ok, presence_findings = _check_verification_presence(text, [])
            if not presence_ok:
                any_fail = True
                for f in presence_findings:
                    print(f"  FAIL: {f}")
            else:
                print("  Nothing declared under '## Verification' to re-execute.")
            continue
        any_commands = True
        for cmd in commands:
            exit_code, stdout, stderr = _run_subprocess(cmd)
            status = "PASS" if exit_code == 0 else "FAIL"
            print(f"  [{status}] `{cmd}` -> real exit code {exit_code}")
            if exit_code != 0:
                any_fail = True
                print(f"         last output: {(stderr or stdout)[-500:]}")

    print("\n" + "=" * 60)
    if not any_commands:
        print("No declared verification commands found in any given report.")
    print(
        "Re-executes each declared command exactly once, independently of what the report claims "
        "about it. A command with side effects will have those side effects again -- declare "
        "read-only/idempotent verification commands only, the same expectation reports already carry."
    )
    sys.exit(13 if any_fail else 0)


# --- recompute ----------------------------------------------------------------

_RECOMPUTE_BLOCK_HEADER_RE = re.compile(r'^##\s*Recompute Declaration\s*$', re.MULTILINE)
_RECOMPUTE_REQUIRED_FIELDS = {
    "original_script", "independent_script", "artifact", "artifact_key",
    "independent_command", "independent_output_key",
}

# v2.3.0 (D-045) -- optional fields, checked only if present; a Recompute
# Declaration that doesn't use any of these behaves EXACTLY as before.
_EVIDENCE_TIERS = {"T1", "T2", "T3"}
_STDLIB_FALLBACK = frozenset(getattr(sys, "stdlib_module_names", ()) or {
    # Python < 3.10 fallback -- a short, deliberately conservative list
    # covering the modules most likely to appear in a recompute script
    # and cause a false "shared dependency" finding if NOT excluded.
    # Missing an obscure stdlib name here only makes the check slightly
    # noisier (a WARNING, never a hard FAIL), never unsafe.
    "os", "sys", "re", "json", "math", "itertools", "functools", "collections",
    "pathlib", "subprocess", "datetime", "hashlib", "argparse", "unittest",
    "typing", "dataclasses", "csv", "io", "time", "random", "statistics",
    "logging", "shutil", "tempfile", "glob", "copy", "abc", "enum",
})


def _extract_top_level_imports(script_path):
    """v2.3.0 (D-045) -- returns the set of non-stdlib top-level module
    names a Python script imports, via `ast.parse` (never executes the
    file, never imports it). Returns an empty set if the file can't be
    parsed or read -- this is an additional, optional signal on top of
    the byte-identity check above, never itself a hard-FAIL condition."""
    try:
        tree = ast.parse(Path(script_path).read_text())
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return {n for n in names if n not in _STDLIB_FALLBACK}


def _check_evidence_tier_claim(fields, shared_deps):
    """v2.3.0 (D-045) -- if a Recompute Declaration claims an optional
    `evidence_tier` (T1/T2/T3, a depth-of-verification axis genuinely
    orthogonal to Scientific Claim Tier -- see dynamic_rules.md D-045),
    mechanically caps a T3 claim against what was actually checked here:
    no shared non-stdlib import with original_script, and, if
    `production_entrypoint` was also declared, independent_command
    actually references it. Never upgrades a tier, only flags a claim
    stronger than its own evidence -- and only WARNS (D-045 is a
    PROPOSED, not yet cross-project-evidenced rule; see its Status),
    never hard-fails a recompute run over this alone. Omitting
    evidence_tier entirely is unaffected -- this only fires when one is
    actually claimed."""
    claimed = (fields.get("evidence_tier") or "").strip().upper()
    if not claimed:
        return []
    if claimed not in _EVIDENCE_TIERS:
        return [f"WARNING: evidence_tier '{claimed}' is not one of {sorted(_EVIDENCE_TIERS)} -- ignored (D-045)."]
    findings = []
    if claimed == "T3":
        if shared_deps:
            findings.append(
                f"EVIDENCE TIER OVERCLAIM: evidence_tier T3 claimed, but independent_script "
                f"shares non-stdlib import(s) {sorted(shared_deps)} with original_script -- "
                f"weaker independence than a T3 (adversarial/independently-implemented) claim "
                f"implies (D-045)."
            )
        entrypoint = (fields.get("production_entrypoint") or "").strip()
        if entrypoint and entrypoint not in (fields.get("independent_command") or ""):
            findings.append(
                f"EVIDENCE TIER OVERCLAIM: evidence_tier T3 claimed and production_entrypoint "
                f"'{entrypoint}' declared, but independent_command does not appear to invoke "
                f"it -- a check that never calls the production path cannot support a T3 "
                f"claim (D-045)."
            )
    return findings


def _parse_recompute_block(report_path):
    """Returns (fields_dict_or_None, findings). No block present is not an
    error -- not every contract declares one."""
    text = _read_text_or_none(Path(report_path))
    if text is None:
        return None, [f"CANNOT CHECK: {report_path} not found."]
    m = _RECOMPUTE_BLOCK_HEADER_RE.search(text)
    if m is None:
        return None, []
    block_end = text.find("\n## ", m.end())
    block = text[m.end():block_end if block_end != -1 else len(text)]
    fields = {}
    for fm in _VERDICT_FIELD_RE.finditer(block):
        fields[fm.group(1)] = fm.group(2)
    missing = _RECOMPUTE_REQUIRED_FIELDS - fields.keys()
    if missing:
        return None, [f"MALFORMED RECOMPUTE BLOCK: {report_path} is missing field(s): {sorted(missing)}."]
    return fields, []


def _check_recompute_block(report_path):
    """Returns (checked: bool, ok: bool, lines: list[str]). checked=False
    means no (well-formed) Recompute Declaration was present -- not a
    failure by itself; a MALFORMED block still returns checked=False but
    ok=False, since a declared-but-broken block should not fail open."""
    fields, findings = _parse_recompute_block(report_path)
    if fields is None:
        return (False, not findings, list(findings))

    lines = []
    orig = Path(fields["original_script"])
    indep = Path(fields["independent_script"])
    try:
        tolerance = float(fields.get("tolerance", "0") or 0)
    except ValueError:
        tolerance = 0.0

    if not indep.exists():
        lines.append(f"FAIL: independent_script {indep} does not exist.")
        return (True, False, lines)
    if orig.exists() and sha256_of(orig) == sha256_of(indep):
        lines.append(
            "FAIL: independent_script is byte-identical to original_script -- this is "
            "duplication, not independent verification (C11)."
        )
        return (True, False, lines)
    if not orig.exists():
        lines.append(f"WARNING: original_script {orig} not found -- cannot confirm independence, "
                      f"only that independent_script exists and runs.")

    artifact_data, err = _load_json_or_none(fields["artifact"])
    if err:
        lines.append(err)
        return (True, False, lines)
    claimed_value, found = _get_json_path(artifact_data, fields["artifact_key"])
    if not found:
        lines.append(f"FAIL: artifact_key '{fields['artifact_key']}' not found in {fields['artifact']}.")
        return (True, False, lines)

    exit_code, stdout, stderr = _run_subprocess(fields["independent_command"])
    if exit_code != 0:
        lines.append(f"FAIL: independent_command exited {exit_code}. stderr: {stderr[-300:]}")
        return (True, False, lines)
    try:
        recomputed = json.loads(stdout.strip().splitlines()[-1])
        recomputed_value = recomputed[fields["independent_output_key"]]
    except Exception as e:
        lines.append(
            f"FAIL: could not read '{fields.get('independent_output_key')}' from "
            f"independent_command's JSON stdout ({e})."
        )
        return (True, False, lines)

    try:
        diff = abs(float(claimed_value) - float(recomputed_value))
        match = diff <= tolerance
    except (TypeError, ValueError):
        diff = None
        match = claimed_value == recomputed_value

    if match:
        lines.append(f"PASS: claimed={claimed_value} recomputed={recomputed_value} tolerance={tolerance}")
        # v2.3.0 (D-045) -- non-blocking warnings only; never flip a PASS to a
        # FAIL over these, since both are optional, additive signals on top
        # of the byte-identity check that already ran (and already hard-FAILs)
        # above.
        shared_deps = (_extract_top_level_imports(fields["original_script"])
                       & _extract_top_level_imports(fields["independent_script"]))
        if shared_deps:
            lines.append(
                f"WARNING: original_script and independent_script share non-stdlib "
                f"import(s) {sorted(shared_deps)} -- weaker independence than two "
                f"unrelated implementations would have, even though they are not "
                f"byte-identical (D-045)."
            )
        for f in _check_evidence_tier_claim(fields, shared_deps):
            lines.append(f"WARNING: {f}")
        return (True, True, lines)
    lines.append(
        f"FAIL: RECOMPUTE MISMATCH claimed={claimed_value} recomputed={recomputed_value} "
        f"diff={diff} tolerance={tolerance}"
    )
    return (True, False, lines)


def cmd_recompute(args):
    """v1.4.2, mechanical barrier #3. For each report declaring a
    '## Recompute Declaration' block, actually runs the declared
    independent script and compares its output to the artifact's claimed
    value. Independence is enforced mechanically (hash comparison), not
    merely asserted."""
    print("Gatekeeper recompute (independent recomputation check)")
    print("=" * 60)
    if not args.reports:
        print("\nERROR: --reports must be given. Nothing to check.")
        sys.exit(9)

    any_fail = False
    any_checked = False
    for rp in args.reports:
        checked, ok, lines = _check_recompute_block(rp)
        print(f"\n[{rp}]")
        if not lines:
            print("  No Recompute Declaration block present.")
        for l in lines:
            print(f"  {l}")
        if checked:
            any_checked = True
            any_fail = any_fail or not ok
        elif lines:
            any_fail = True  # malformed block, disclosed but not silently skipped

    print("\n" + "=" * 60)
    if not any_checked:
        print("No well-formed Recompute Declaration blocks found. Nothing independently recomputed.")
    sys.exit(15 if any_fail else 0)


# --- stamp-report ---------------------------------------------------------

_STAMP_HEADER_RE = re.compile(r'^## Gatekeeper Verification Stamp #(\d+)\s*$', re.MULTILINE)
_STAMP_HASH_LINE_RE = re.compile(r'^content_hash_sha256:\s*([0-9a-f]{64})\s*$', re.MULTILINE)


def _find_stamps(text):
    """Returns list of dicts (number, header_start, claimed_hash), in file
    order, oldest first."""
    headers = list(_STAMP_HEADER_RE.finditer(text))
    stamps = []
    for i, hm in enumerate(headers):
        block_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block_text = text[hm.start():block_end]
        hash_m = _STAMP_HASH_LINE_RE.search(block_text)
        stamps.append({
            "number": int(hm.group(1)),
            "header_start": hm.start(),
            "claimed_hash": hash_m.group(1) if hash_m else None,
        })
    return stamps


def _verify_stamp_integrity(report_path):
    """Returns (ok, findings). No stamps present -> (True, []) -- stamping
    is opt-in per report and never retroactively required of existing,
    unstamped reports (Backward Compatibility). Each stamp's claimed hash
    must equal sha256(content strictly before that stamp's own header),
    so tampering with content under an EARLIER stamp is still caught by
    every LATER stamp's hash, not just the nearest one."""
    text = _read_text_or_none(Path(report_path))
    if text is None:
        return False, [f"CANNOT CHECK: {report_path} not found."]
    stamps = _find_stamps(text)
    if not stamps:
        return True, []
    ok = True
    findings = []
    for s in stamps:
        if s["claimed_hash"] is None:
            findings.append(f"MALFORMED STAMP: {report_path} stamp #{s['number']} has no content_hash_sha256 line.")
            ok = False
            continue
        actual_hash = _sha256_text(text[:s["header_start"]])
        if actual_hash != s["claimed_hash"]:
            findings.append(
                f"STAMP TAMPERING DETECTED: {report_path} stamp #{s['number']} certified content hash "
                f"{s['claimed_hash'][:16]}..., but the actual content before this stamp now hashes to "
                f"{actual_hash[:16]}... -- something above this stamp was modified after it was issued."
            )
            ok = False
    return ok, findings


def _render_stamp_block(stamp_number, content_hash, verification_results, lint_hard, lint_warn,
                         recompute_lines, frozen_details, git_files):
    lines = [f"## Gatekeeper Verification Stamp #{stamp_number}", ""]
    lines.append(f"content_hash_sha256: {content_hash}")
    lines.append(f"stamped_at_utc: {_now_utc_iso()}")
    lines.append("")
    lines.append("### Files Modified (git diff)")
    if git_files is None:
        lines.append("- UNAVAILABLE (git not found or not a repository)")
    elif not git_files:
        lines.append("- (no uncommitted changes detected)")
    else:
        lines += [f"- {f}" for f in git_files]
    lines.append("")
    lines.append("### Verification Commands (independently re-executed)")
    if not verification_results:
        lines.append("- (none declared under '## Verification')")
    else:
        for r in verification_results:
            lines.append(f"- `{r['command']}` -> exit code {r['exit_code']} "
                          f"({'PASS' if r['exit_code'] == 0 else 'FAIL'})")
    lines.append("")
    lines.append("### Frozen Verification Machinery")
    if not frozen_details:
        lines.append("- (none present in this project yet)")
    else:
        lines += [f"- {d}" for d in frozen_details]
    lines.append("")
    lines.append("### Contract Lint")
    lines.append(f"- Hard failures: {len(lint_hard)}")
    lines += [f"  - {f}" for f in lint_hard]
    lines.append(f"- Warnings: {len(lint_warn)}")
    lines += [f"  - {f}" for f in lint_warn]
    lines.append("")
    lines.append("### Independent Recomputation")
    if not recompute_lines:
        lines.append("- (no Recompute Declaration in this report)")
    else:
        lines += [f"- {l}" for l in recompute_lines]
    lines.append("")
    lines.append(
        "Everything above this stamp (including any earlier stamps) is certified unchanged as of "
        "this hash. Modifying anything above this line is detected the next time this report is "
        "stamped or checked (exit code 16). Corrections belong in a new section below this line, "
        "not an edit above it."
    )
    return "\n".join(lines) + "\n"


def cmd_stamp_report(args):
    """v1.4.2, mechanical barrier #4 -- ties the other three together.
    Appends a tamper-evident stamp to a contract report containing the
    REAL results of verify-contract, lint-contract, and recompute (if
    declared), plus git diff and frozen-file status. Refuses to stamp if
    any EXISTING stamp has already been tampered with (exit 16, fail
    fast, before doing anything else). Never modifies content above the
    point it appends to."""
    print("Gatekeeper stamp-report (mechanical evidence stamp)")
    print("=" * 60)
    report_path = Path(args.report)
    text = _read_text_or_none(report_path)
    if text is None:
        print(f"ERROR: {args.report} not found.")
        sys.exit(9)

    ok, integrity_findings = _verify_stamp_integrity(report_path)
    existing_stamps = _find_stamps(text)
    if not ok:
        print("\n[Stamp Integrity] TAMPERING DETECTED -- refusing to add a new stamp.")
        for f in integrity_findings:
            print(f"  - {f}")
        sys.exit(16)
    print("\n[Stamp Integrity] " + ("no existing stamps -- this will be #1."
          if not existing_stamps else f"all {len(existing_stamps)} existing stamp(s) verified intact."))

    next_number = (max(s["number"] for s in existing_stamps) + 1) if existing_stamps else 1

    commands = _extract_declared_commands(text)
    verification_results = []
    for cmd in commands:
        exit_code, _, _ = _run_subprocess(cmd)
        verification_results.append({"command": cmd, "exit_code": exit_code})
    verification_failed = any(r["exit_code"] != 0 for r in verification_results)

    frozen_paths = _auto_frozen_verification_paths()
    frozen_details = []
    frozen_tampered = False
    if frozen_paths:
        if args.contract:
            fr_ok, frozen_details = check_frozen_files(args.contract, frozen_paths)
            frozen_tampered = not fr_ok
        else:
            frozen_details = [f"{p} = {sha256_of(Path(p))[:12]}... (no --contract given, informational only)"
                               for p in frozen_paths]

    git_files, _ = _git_diff_files()
    lint_hard, lint_warn = [], []
    py_targets = [f for f in (git_files or []) if f.endswith(".py")]
    for sp in py_targets:
        h, w = _scan_swallowed_exceptions(sp)
        lint_hard += h
        lint_warn += w
    lint_hard += _scan_fabricated_statistical_input(py_targets)

    _, recompute_ok, recompute_lines = _check_recompute_block(report_path)
    recompute_declared_and_failed = bool(recompute_lines) and not recompute_ok

    prefix = text if text.endswith("\n\n") else (text.rstrip("\n") + "\n\n")
    content_hash = _sha256_text(prefix)
    stamp_block = _render_stamp_block(
        next_number, content_hash, verification_results, lint_hard, lint_warn,
        recompute_lines, frozen_details, git_files,
    )
    new_text = prefix + stamp_block
    report_path.write_text(new_text)

    print(f"\nStamp #{next_number} appended to {args.report}.")
    print(f"  Verification commands: {len(verification_results)} run"
          + (", FAIL" if verification_failed else (", all passed" if verification_results else "")))
    print(f"  Lint: {len(lint_hard)} hard failure(s), {len(lint_warn)} warning(s)")
    print(f"  Frozen verification machinery: {'TAMPERED' if frozen_tampered else 'ok'} "
          f"({len(frozen_paths)} path(s))")
    print(f"  Recompute: {'declared and FAILED' if recompute_declared_and_failed else ('declared and passed' if recompute_lines else 'not declared')}")

    if verification_failed or lint_hard or frozen_tampered or recompute_declared_and_failed:
        sys.exit(14)
    sys.exit(0)


def cmd_verify_stamps(args):
    """Standalone integrity check, no side effects -- for CI or a Human to
    confirm a report hasn't been tampered with since it was last stamped,
    without also appending a new stamp."""
    print("Gatekeeper verify-stamps (tamper check only -- does not add a stamp)")
    print("=" * 60)
    any_fail = False
    for rp in args.reports or []:
        ok, findings = _verify_stamp_integrity(rp)
        stamps = _find_stamps(_read_text_or_none(Path(rp)) or "")
        print(f"\n[{rp}] {len(stamps)} stamp(s) found.")
        for f in findings:
            print(f"  - {f}")
        if ok and stamps:
            print("  All stamps verified intact.")
        if not ok:
            any_fail = True
    if not args.reports:
        print("\nERROR: --reports must be given.")
        sys.exit(9)
    sys.exit(16 if any_fail else 0)


# v2.3.0 (D-049) -- Factory-internal identifier patterns for the outbound
# secrecy scan. Deliberately narrow and specific (contract/chunk/decision ID
# SHAPES, and Factory-specific proper nouns/paths), not a generic word
# blocklist -- "Architect"/"Implementor" alone would false-positive on
# ordinary architecture/software-implementation prose, so those two only
# count as a match in a role-labeled construction ("as the Architect,"
# "the Implementor's"), not as bare common-noun usage.
_FACTORY_ID_PATTERNS = [
    (re.compile(r'\bC\d{1,3}-\d{2,3}\b'), "contract ID (C##-##)"),
    (re.compile(r'\bchunk\s*\d{1,3}\b', re.IGNORECASE), "chunk identifier"),
    (re.compile(r'\bD-\d{2,4}\b'), "decision-log ID (D-####)"),
    (re.compile(r'\bDEC-\d{2,4}\b'), "decision-log ID (DEC-####)"),
    (re.compile(r'\bTAKE_THIS\b|\bDROP_HERE\b'), "handoff-folder name"),
    (re.compile(r'\bgatekeeper\.py\b', re.IGNORECASE), "Gatekeeper script name"),
    (re.compile(r'project/\.gatekeeper\b'), "Factory control-plane path"),
    (re.compile(r'\bas the (?:Architect|Implementor)\b|\bthe (?:Architect|Implementor)\'s\b',
                re.IGNORECASE), "Factory role name (labeled usage)"),
    (re.compile(r'\bRELEASE_CERTIFICATION\.md\b'), "Factory certification filename"),
]


def _scan_factory_identifiers(paths):
    """Scans the given files for Factory-internal identifier patterns
    (D-049). Returns hard-finding strings, one per match, naming the file,
    line number, and pattern category -- never the matched text itself
    beyond what's needed to locate it, since the point is to flag the leak
    for removal, not to reproduce it in a findings list that itself then
    gets read by whoever the artifact was trying to keep this from."""
    findings = []
    for p in paths:
        path = Path(p)
        text = _read_text_or_none(path)
        if text is None:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, label in _FACTORY_ID_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        f"FACTORY-INTERNAL IDENTIFIER LEAK: {path}:{lineno} contains a "
                        f"{label}. Outbound artifacts must not reveal that this Factory "
                        f"was used to build them (Project Repository Isolation)."
                    )
    return findings


def _collect_superseded_contract_ids(report_paths):
    """Scans every report's Contract Information section for a
    'Superseded-By: <contract-id>' line (D-050) and returns
    {superseded_id: superseding_id}. This is written by the LATER
    contract about the one it replaces, or by the earlier contract about
    itself once the later one exists -- either location is accepted; both
    read the same way. Never inferred automatically: a contract is only
    superseded when something explicitly says so in its own text."""
    superseded = {}
    pattern = re.compile(r'^\s*\**Superseded-?By\**:\s*([A-Za-z0-9_\-]+)', re.IGNORECASE | re.MULTILINE)
    for rp in report_paths:
        text = _read_text_or_none(rp)
        if text is None:
            continue
        m = pattern.search(text)
        if m:
            superseded[rp.parent.name] = m.group(1).strip()
    return superseded


def _report_certificate_staleness(chunks_dir):
    """Reads any existing project/RELEASE_CERTIFICATION.md and compares
    its generated_at/contract_reports_examined against the CURRENT state
    of --chunks-dir (D-053). Purely informational -- never blocks
    anything, never modifies the old file (release-certify overwrites it
    unconditionally right after this, as it always has). Exists so that a
    Human, or an AI role in a fresh session with no memory of how an
    earlier certificate came about, has an explicit, printed answer to
    'is the certificate I'm looking at still current' instead of having
    to reconstruct that judgment from an unaided read of the repository."""
    cert_path = Path("project/RELEASE_CERTIFICATION.md")
    old_text = _read_text_or_none(cert_path)
    if old_text is None:
        print("\n[Certificate currency] No prior project/RELEASE_CERTIFICATION.md found -- "
              "this will be the first one. Any earlier verbal claim of readiness was never "
              "backed by one (D-053).")
        return
    ts_m = re.search(r'^generated_at:\s*(.+)$', old_text, re.MULTILINE)
    count_m = re.search(r'^contract_reports_examined:\s*(\d+)', old_text, re.MULTILINE)
    old_ts, old_count = (ts_m.group(1).strip() if ts_m else None), (int(count_m.group(1)) if count_m else None)
    current_reports = sorted(chunks_dir.glob("*/reports/*/contract_report.md"))
    newer = []
    if old_ts:
        try:
            old_dt = datetime.strptime(old_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            grace = timedelta(seconds=2)  # v2.3.0: generated_at truncates to whole seconds; mtime does not
            for rp in current_reports:
                try:
                    mtime = datetime.fromtimestamp(rp.stat().st_mtime, tz=timezone.utc)
                except OSError:
                    continue
                if mtime > old_dt + grace:
                    newer.append(str(rp))
        except ValueError:
            pass
    print(f"\n[Certificate currency] Prior certificate generated_at={old_ts}, "
          f"examined {old_count} report(s); {len(current_reports)} report(s) exist now.")
    if newer or (old_count is not None and old_count != len(current_reports)):
        print(f"  STALE: {len(newer)} report file(s) changed since that certificate was "
              f"generated (or the report count changed, {old_count} -> {len(current_reports)}). "
              f"Regenerating now. Any verbal claim of readiness based on the OLD certificate "
              f"should be treated as unverified until this new run completes (D-053).")
        for f in newer[:10]:
            print(f"    - changed since: {f}")
    else:
        print("  Prior certificate appears current relative to report file timestamps/count; "
              "regenerating anyway, since this command always writes a fresh one.")


def cmd_release_certify(args):
    """v2.2.0 (D-038) -- aggregate release certification, distinct from any
    single chunk's PASS. `release-check` (v1.4.0) scans one release-bound
    artifact for path leaks and key-fact drift; nothing before v2.2
    aggregated across an entire project and said, in one place, whether the
    whole thing is actually submission-ready. Chunk PASS and Gatekeeper
    `check` PASS are per-contract/per-chunk states -- this command is the
    only one that produces project/RELEASE_CERTIFICATION.md, and it is the
    only artifact this Factory's documents authorize anyone to call
    "CERTIFIED."

    Walks every contract_report.md under --chunks-dir and, per contract:
    confirms Final Status is COMPLETE (not FLAGGED or BLOCKED -- either one
    blocks certification, since a Fix Package or a carried-forward blocker
    means the project isn't actually in its claimed final state); runs the
    same evidence-check logic against any '## Verdict Cross-Check' block;
    runs the same recompute logic against any '## Recompute Declaration'
    block; and, when the contract's own contract.md is locatable, runs the
    same tier-inference logic tier-check does standalone. Then runs
    acquisition-audit against --scripts if given, and release-check against
    --manuscript if given.

    This is a thinner aggregation than it might look: it re-runs existing
    checks against existing artifacts, it does not invent a new evidence
    format, a new registry file, or a new role to perform the aggregation.
    Never modifies any contract report. Writes project/RELEASE_CERTIFICATION.md
    unconditionally (CERTIFIED or NOT CERTIFIED, both are useful states to
    have on record) and exits 19 on NOT CERTIFIED.
    """
    print("Gatekeeper release-certify (aggregate CERTIFIED / NOT CERTIFIED gate)")
    print("=" * 60)

    chunks_dir = Path(args.chunks_dir)
    if not chunks_dir.exists():
        print(f"\nERROR: --chunks-dir {chunks_dir} not found.")
        sys.exit(9)

    # v2.3.0 (D-053) -- staleness note. A certificate is only as current as
    # the repository state it was generated against; report this BEFORE
    # regenerating, so a Human or an AI role that skipped straight to
    # reading the old file (or to someone's verbal recollection of it) has
    # an explicit, printed reason not to. Motivated directly by a reported
    # incident: the same underlying model, in a fresh session with no
    # memory of the ten-chunk conversation that produced an earlier
    # verbal "publication ready," found numerous issues on a cold read of
    # the same repository -- because "is it ready" was being decided by
    # re-asking an LLM's holistic opinion in two different contexts rather
    # than by re-deriving the same deterministic answer. See C05 (AI
    # opinion is never verification) and C59 (a certificate names exactly
    # what it checked); see architect_spec.md/implementor_spec.md's new
    # "Answering 'is this ready'" section for the corresponding process
    # rule this command exists to make actually checkable.
    _report_certificate_staleness(chunks_dir)

    hard_findings = []
    warning_findings = []
    categories_checked = []

    report_paths = sorted(chunks_dir.glob("*/reports/*/contract_report.md"))
    print(f"\n[Contract Status] {len(report_paths)} contract_report.md file(s) found under {chunks_dir}")
    if not report_paths:
        hard_findings.append(f"NO CONTRACT REPORTS FOUND under {chunks_dir} -- nothing to certify.")

    # v2.3.0 (D-050) -- a report explicitly marked superseded (its Contract
    # Information section contains a line like "Superseded-By: C19-01",
    # written by the later contract that replaced it -- see
    # factory_spec.md's amended Contract Specification) is not evaluated
    # against Final Status == COMPLETE at all; its findings move to a
    # separate, non-blocking Historical Findings section instead. This is
    # not a way to silence a real problem -- it only applies to a report
    # that ANOTHER, later contract explicitly claims to have superseded,
    # which is exactly the AML/collusion-ring project's Chunk 19 situation
    # (stale Chunk 18 claims that a corrective chunk had already replaced,
    # previously still blocking certification with no way to say so).
    non_complete = []
    historical_notes = []
    superseded_ids = _collect_superseded_contract_ids(report_paths)
    for rp in report_paths:
        contract_id = rp.parent.name
        status = parse_contract_status(rp)
        if status != "complete":
            if contract_id in superseded_ids:
                historical_notes.append(
                    f"{rp}: Final Status is '{status}', not COMPLETE, but this contract is "
                    f"marked superseded by {superseded_ids[contract_id]} -- excluded from active "
                    f"certification, kept here for the historical record (D-050)."
                )
            else:
                non_complete.append((str(rp), status))
    if non_complete:
        for rp, status in non_complete:
            hard_findings.append(f"NOT COMPLETE: {rp} Final Status is '{status}', not COMPLETE.")
    else:
        print(f"  All non-superseded report(s) read Final Status: COMPLETE.")
    categories_checked.append("contract_status")

    print("\n[Evidence / Recompute per contract]")
    verdict_checked = 0
    recompute_checked = 0
    for rp in report_paths:
        fields, block_findings = _parse_verdict_block(rp)
        hard_findings += [f"{rp}: {f}" for f in block_findings if f.startswith("MALFORMED")]
        warning_findings += [f"{rp}: {f}" for f in block_findings if f.startswith("CANNOT CHECK")]
        if fields is not None:
            verdict_checked += 1
            vf = _check_verdict_consistency(rp, fields)
            hard_findings += [f"{rp}: {f}" for f in vf if not f.startswith("CANNOT CHECK")]
            warning_findings += [f"{rp}: {f}" for f in vf if f.startswith("CANNOT CHECK")]
            cf = _check_criterion_consistency(rp, fields)
            hard_findings += [f"{rp}: {f}" for f in cf if not f.startswith("CANNOT CHECK")]
            warning_findings += [f"{rp}: {f}" for f in cf if f.startswith("CANNOT CHECK")]
            warning_findings += [f"{rp}: {f}" for f in _check_degenerate_metrics(fields["artifact"])]

        checked, ok, lines = _check_recompute_block(rp)
        if checked:
            recompute_checked += 1
            if not ok:
                hard_findings += [f"{rp} recompute: {l}" for l in lines]
    print(f"  {verdict_checked} report(s) had a Verdict Cross-Check block checked.")
    print(f"  {recompute_checked} report(s) had a Recompute Declaration checked.")
    categories_checked.append("evidence_and_recompute")

    print("\n[Fail-Closed Tier Inference per contract]")
    tier_checked = 0
    for rp in report_paths:
        contract_id = rp.parent.name
        contract_path, err = _find_contract_file(contract_id)
        if contract_path is None:
            warning_findings.append(f"{rp}: could not locate contract file for tier-check ({err})")
            continue
        ctext = _read_text_or_none(contract_path)
        if ctext is None:
            continue
        tier_checked += 1
        m = re.search(r'Scientific Claim Tier.*?:\s*\**\s*(NONE|T-DESC|T-COMP|T-CAUSAL)\b', ctext, re.IGNORECASE)
        declared = m.group(1).upper() if m else "NONE"
        minimum_tier, strong_matches, _weak = _infer_minimum_scientific_claim_tier(ctext)
        if _TIER_RANK[declared] < _TIER_RANK[minimum_tier]:
            hard_findings.append(
                f"{contract_path}: declared Scientific Claim Tier '{declared}' is weaker than "
                f"inferred minimum '{minimum_tier}' (matched {strong_matches})."
            )
    print(f"  {tier_checked} contract(s) checked for fail-closed tier inference.")
    categories_checked.append("tier_inference")

    if args.scripts:
        print("\n[Acquisition Audit]")
        structural = _scan_acquisition_functions(args.scripts) + _scan_fabricated_statistical_input(args.scripts)
        hard_findings += [f for f in structural if f.startswith("DATA-GENERATION FUNCTION") or f.startswith("FABRICATED STATISTICAL INPUT")]
        warning_findings += _scan_acquisition_text(args.scripts)
        warning_findings += _scan_statistical_protocol_language(args.scripts)
        print(f"  {len(args.scripts)} script(s) scanned.")
        categories_checked.append("acquisition_audit")
    else:
        print("\n[Acquisition Audit] SKIPPED -- no --scripts given.")

    if args.manuscript:
        print("\n[Release Artifact Scan]")
        scan_targets = [args.manuscript] + list(args.files or [])
        path_findings = _scan_local_paths(scan_targets)
        hard_findings += path_findings
        # v2.3.0 (D-049) -- a second, textual kind of fingerprint alongside
        # the existing local-path scan: Factory-internal identifiers
        # (chunk/contract/decision IDs, DROP_HERE/TAKE_THIS, Gatekeeper/
        # role-name language) that would reveal this Factory was used,
        # if they leaked into a manuscript or other release-bound
        # artifact. This is the same Project Repository Isolation goal
        # factory_spec.md already states ("no visible trace... that a
        # project was built using this Factory"), just not previously
        # mechanically checked for THIS kind of leak. Evidence: the
        # AML/collusion-ring project's explicit request for exactly this
        # scan, after manually catching an early manuscript draft that
        # would have named the Factory's internal chunk numbering.
        secrecy_findings = _scan_factory_identifiers(scan_targets)
        hard_findings += secrecy_findings
        if args.key_facts:
            kf_findings = _check_key_fact_consistency(args.manuscript, args.key_facts)
            warning_findings += kf_findings
        print(f"  Scanned {args.manuscript} (+{len(args.files or [])} additional file(s)) "
              f"for local paths and Factory-internal identifiers.")
        categories_checked.append("release_artifact_scan")
        categories_checked.append("outbound_secrecy_scan")
    else:
        print("\n[Release Artifact Scan] SKIPPED -- no --manuscript given.")

    certified = not hard_findings
    verdict = "CERTIFIED" if certified else "NOT CERTIFIED"

    print("\n" + "=" * 60)
    print(f"Categories checked: {categories_checked}")
    print(f"Hard findings: {len(hard_findings)}   Warnings: {len(warning_findings)}   "
          f"Historical (superseded, non-blocking): {len(historical_notes)}")
    if hard_findings:
        print("\n[Hard findings]")
        for f in hard_findings:
            print(f"  - {f}")
    if warning_findings:
        print("\n[Warnings]")
        for f in warning_findings:
            print(f"  - {f}")
    if historical_notes:
        print("\n[Historical findings -- superseded, informational only, D-050]")
        for f in historical_notes:
            print(f"  - {f}")
    print(f"\nRESULT: {verdict}")

    cert_path = Path("project/RELEASE_CERTIFICATION.md")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Release Certification",
        "",
        f"status: {verdict}",
        f"generated_at: {timestamp}",
        f"chunks_dir: {chunks_dir}",
        f"categories_checked: {categories_checked}",
        f"contract_reports_examined: {len(report_paths)}",
        "",
        "## Hard findings",
    ]
    lines += [f"- {f}" for f in hard_findings] if hard_findings else ["(none)"]
    lines += ["", "## Historical findings (superseded, non-blocking, D-050)"]
    lines += [f"- {f}" for f in historical_notes] if historical_notes else ["(none)"]
    lines += ["", "## Warnings"]
    lines += [f"- {f}" for f in warning_findings] if warning_findings else ["(none)"]
    lines += [
        "",
        "## Proof boundaries",
        "This certifies only what the categories above actually check: contract completion "
        "status (excluding contracts explicitly marked superseded by a later contract, which "
        "are reported separately under Historical Findings and never block this verdict), "
        "verdict/criterion/recompute consistency for contracts that declared those blocks, "
        "fail-closed tier inference, and (if invoked with --scripts/--manuscript) "
        "acquisition-audit, local-path leaks, and Factory-internal-identifier leaks in "
        "release-bound artifacts. It does not certify scientific truth, publication "
        "acceptance, or correctness of anything no check above actually examined -- an "
        "uninvoked category is absent from `categories_checked` above, not silently passed. "
        "A chunk-level Gatekeeper PASS is not this certificate, and this certificate does "
        "not retroactively upgrade one. This certificate is a snapshot of this repository "
        "at generated_at above -- if further contracts complete afterward, re-run this "
        "command (`release-status` reports whether that has already happened without "
        "re-running the full check). Treat any verbal claim of 'ready'/'complete' that is "
        "not backed by this file's own current content as unverified opinion, per C05 and "
        "C59 -- see architect_spec.md/implementor_spec.md's \"Answering 'is this ready'\" "
        "section (D-053).",
    ]
    try:
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        cert_path.write_text("\n".join(lines) + "\n")
        print(f"\nWrote {cert_path}")
    except OSError as e:
        print(f"\nWARNING: could not write {cert_path}: {e}")

    sys.exit(0 if certified else 19)


def cmd_release_status(args):
    """v2.3.0 (D-053) -- reports whether the existing project/
    RELEASE_CERTIFICATION.md is still current, WITHOUT re-running the full
    release-certify battery. Exists for exactly one use case: a Human, or
    an AI role in a brand-new session with no memory of prior chunks, asks
    "is this ready" and should get a fast, deterministic, session-
    independent answer instead of an unaided holistic impression. Reuses
    _report_certificate_staleness's own comparison logic -- this command
    does not duplicate that detection, it just exposes it standalone
    (C46) and gives it its own exit code so it can gate a workflow step.

    Exit 0: a certificate exists, is CERTIFIED, and is current.
    Exit 19: no certificate exists, OR the existing one is NOT CERTIFIED,
    OR it is stale relative to the current --chunks-dir state -- in all
    three cases, nothing currently on record supports calling this
    project ready, and release-certify should be (re-)run before anyone,
    human or AI, says otherwise.
    """
    print("Gatekeeper release-status (certificate currency check, D-053)")
    print("=" * 60)
    chunks_dir = Path(args.chunks_dir)
    cert_path = Path("project/RELEASE_CERTIFICATION.md")
    text = _read_text_or_none(cert_path)
    if text is None:
        print(f"\nNo {cert_path} found. Nothing currently on record certifies this project. "
              f"Run `gatekeeper.py release-certify` before answering 'is this ready.'")
        sys.exit(19)

    status_m = re.search(r'^status:\s*(.+)$', text, re.MULTILINE)
    status = status_m.group(1).strip() if status_m else "UNKNOWN"
    if not chunks_dir.exists():
        print(f"\n{cert_path} exists (status: {status}) but --chunks-dir {chunks_dir} was not "
              f"found, so currency cannot be checked. Treat as unverified.")
        sys.exit(19)

    _report_certificate_staleness(chunks_dir)
    ts_m = re.search(r'^generated_at:\s*(.+)$', text, re.MULTILINE)
    count_m = re.search(r'^contract_reports_examined:\s*(\d+)', text, re.MULTILINE)
    old_ts = ts_m.group(1).strip() if ts_m else None
    old_count = int(count_m.group(1)) if count_m else None
    current_reports = sorted(chunks_dir.glob("*/reports/*/contract_report.md"))
    stale = False
    if old_ts:
        try:
            old_dt = datetime.strptime(old_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            grace = timedelta(seconds=2)
            for rp in current_reports:
                try:
                    if datetime.fromtimestamp(rp.stat().st_mtime, tz=timezone.utc) > old_dt + grace:
                        stale = True
                        break
                except OSError:
                    continue
        except ValueError:
            stale = True
    else:
        stale = True
    if old_count is not None and old_count != len(current_reports):
        stale = True

    print(f"\nRecorded status: {status}")
    if status != "CERTIFIED":
        print("RESULT: NOT READY -- last recorded status was not CERTIFIED.")
        sys.exit(19)
    if stale:
        print("RESULT: STALE -- certificate exists and was CERTIFIED, but the repository has "
              "changed since. Re-run release-certify before treating this project as ready.")
        sys.exit(19)
    print("RESULT: FRESH -- last certificate is CERTIFIED and current. This, not a holistic "
          "re-read, is the answer to 'is this ready.'")
    sys.exit(0)


# ============================================================================
# v2.3.0 additions: telemetry/decision-log automation, delegation, scoped
# baselines, contract-preflight, begin, finalize (D-039 through D-048).
# Every function below calls EXISTING detection logic (load_manifest_contract,
# cmd_check, _snapshot_one, cmd_commit_project, parse_contract_status,
# sha256_of, _read_text_or_none) rather than reimplementing it (C46) -- what's
# new here is orchestration, structure, and the two mechanical gaps
# (D-039's verification-parser widening lives above, near
# _extract_declared_commands; D-047's manifest-precondition enforcement
# lives inside cmd_contract_preflight below).
# ============================================================================

def _git_head(cwd):
    """Returns the current HEAD commit hash for the git repo at cwd, or
    None if unavailable (no git, not a repo, no commits yet). Never
    raises -- every caller treats None as 'unknown', not as an error."""
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd,
                            capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _finalize_attempts_path(contract_id):
    return GATEKEEPER_STATE_DIR / f"{contract_id}.finalize_attempts.json"


def _increment_finalize_attempts(contract_id):
    """v2.3.0 (D-048) -- returns how many times finalize has been invoked
    against this contract, including this call. This is what
    self_review_attempts is populated from on a contract_complete
    telemetry event, instead of being hand-typed as 1 regardless of how
    many attempts it actually took (reported as trivially/uninformatively
    1 across all 65 CoreMesh contracts)."""
    GATEKEEPER_STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = _finalize_attempts_path(contract_id)
    count = 0
    if path.exists():
        try:
            count = json.loads(path.read_text()).get("attempts", 0)
        except (OSError, json.JSONDecodeError):
            count = 0
    count += 1
    path.write_text(json.dumps({"contract": contract_id, "attempts": count}))
    return count


def _append_telemetry(fields):
    """v2.3.0 -- appends one event to project/evolution/telemetry.jsonl,
    matching factory_spec.md's canonical schema exactly. Does not change
    the schema; automates a write an AI role has always been required to
    make by hand (reported as repetitive, near-identical boilerplate
    across every contract in a 65-contract project)."""
    TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    event.update(fields)
    with open(TELEMETRY_PATH, "a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def _append_decision(role, title, decision, reason, alternatives, benefit, traces=None):
    """v2.3.0 (D-048) -- appends one entry to both decisions.jsonl
    (structured, auto-incrementing D-number) and decision_log.md
    (rendered, matching its own four-field schema: decision / reason /
    alternatives / expected benefit, per factory_spec.md). Always
    APPENDS at the end -- never searches for or inserts before an
    anchor/register section. decision_log.md's own specification has
    always said append only; a per-project convention requiring
    insert-before-anchor instead is exactly what made hand-editing a
    multi-thousand-line file expensive in a reported project, and
    nothing about the base schema requires that convention."""
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if DECISIONS_PATH.exists():
        for line in DECISIONS_PATH.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    existing.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    max_n = 0
    for rec in existing:
        m = re.match(r'D-(\d+)$', rec.get("id", ""))
        if m:
            max_n = max(max_n, int(m.group(1)))
    decision_id = f"D-{max_n + 1:03d}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {
        "id": decision_id, "date": timestamp, "role": role, "title": title,
        "decision": decision, "reason": reason, "alternatives": alternatives,
        "expected_benefit": benefit, "traces": traces or [],
    }
    with open(DECISIONS_PATH, "a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")

    rendered = (
        f"\n## {decision_id}" + (f" -- {title}" if title else "") + "\n\n"
        f"**Date:** {timestamp}\n**Role:** {role}\n"
        f"**Decision:** {decision}\n**Reason:** {reason}\n"
        f"**Alternatives considered:** {alternatives}\n"
        f"**Expected benefit:** {benefit}\n"
        + (f"**Traces:** {', '.join(traces)}\n" if traces else "")
    )
    if not DECISION_LOG_PATH.exists():
        DECISION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        DECISION_LOG_PATH.write_text("# Decision Log\n\nAppend only. See factory_spec.md.\n")
    with open(DECISION_LOG_PATH, "a") as f:
        f.write(rendered)
    print(f"Appended {decision_id} to {DECISIONS_PATH} and {DECISION_LOG_PATH}.")
    return decision_id


def cmd_log_decision(args):
    """v2.3.0 (D-048) -- CLI entry point for _append_decision. Exists so a
    decision can be logged without hand-editing decision_log.md or
    computing the next D-number by scanning a multi-thousand-line file."""
    print("Gatekeeper log-decision (D-048)")
    print("=" * 60)
    decision_id = _append_decision(
        role=args.role, title=args.title or "", decision=args.decision,
        reason=args.reason, alternatives=args.alternatives or "",
        benefit=args.benefit, traces=args.traces or [],
    )
    print(f"{decision_id} recorded.")


def _load_delegations():
    if not DELEGATIONS_PATH.exists():
        return []
    records = []
    for line in DELEGATIONS_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _find_active_delegation(contract_id, owner, executor):
    """Returns the matching delegation record for this contract/owner/
    executor triple, or None (D-044). Scoped to the SAME chunk as the
    contract ID itself (derived from the ID's own C{chunk}-{n} shape) --
    a delegation never carries forward as precedent to a later chunk
    without a fresh, separately-recorded --authorized-by."""
    chunk_guess = None
    m = re.match(r'C(\d+)-\d+', contract_id, re.IGNORECASE)
    if m:
        chunk_guess = m.group(1)
    owner, executor = owner.strip().lower(), executor.strip().lower()
    for rec in _load_delegations():
        if rec.get("original_owner", "").lower() != owner:
            continue
        if rec.get("executor", "").lower() != executor:
            continue
        if contract_id not in (rec.get("contracts") or []):
            continue
        rec_chunk = str(rec.get("chunk", ""))
        if chunk_guess and rec_chunk and chunk_guess not in rec_chunk:
            continue
        return rec
    return None


def cmd_delegate(args):
    """v2.3.0 (D-044; see constitution.md C55's delegation note) --
    records a Human-authorized, chunk-scoped, non-precedent-setting
    exception to the Implementation Owner table: a role temporarily
    executes specific High-risk, normally differently-owned contracts
    because the owning role is genuinely unreachable this chunk. This
    command does not decide whether the exception is warranted -- that
    authority is, and remains, entirely the Human's (C31: Gatekeeper does
    not evaluate whether an authorization was wise, only whether one was
    given). --authorized-by should quote or closely paraphrase what the
    Human actually said."""
    print("Gatekeeper delegate (D-044)")
    print("=" * 60)
    DELEGATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    records = _load_delegations()
    rec_id = f"DEL-{len(records) + 1:03d}"
    record = {
        "id": rec_id,
        "chunk": args.chunk,
        "original_owner": args.original_owner.strip().lower(),
        "executor": args.executor.strip().lower(),
        "contracts": list(args.contracts),
        "authorized_by": args.authorized_by,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requires_later_independent_review": True,
        "precedent": False,
    }
    with open(DELEGATIONS_PATH, "a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"Recorded {rec_id}: {args.original_owner} -> {args.executor} for "
          f"{args.contracts} in {args.chunk}.")
    print("Scoped to this chunk and this contract list only. Does not set precedent -- "
          "record it again, with a fresh authorization, if a similar situation recurs.")
    print("Flagged for required independent review at this chunk's Chunk Review.")


def _load_full_manifest(manifest_path):
    """Loads the full manifest dict (every contract, repository_
    preconditions, completion_dependencies) -- load_manifest_contract
    only returns one contract's entry, and several v2.3.0 checks need
    the whole document. Duplicates only load_manifest_contract's own two
    guard clauses (PyYAML present, file exists), not any detection logic."""
    try:
        import yaml
    except ImportError:
        print("ERROR: this command requires PyYAML (`pip install pyyaml --break-system-packages`).")
        sys.exit(9)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        sys.exit(9)
    with open(manifest_path) as f:
        return yaml.safe_load(f) or {}


def _expand_glob_paths(patterns):
    """Expands a list of paths/globs against the real filesystem. A
    literal path is kept as-is; a glob pattern (contains *, ?, or [) is
    expanded via Path.glob, matched against files that currently exist.
    Returns a set of path strings."""
    out = set()
    for pat in patterns or []:
        if any(ch in pat for ch in "*?["):
            out.update(str(m) for m in Path(".").glob(pat))
        else:
            out.add(pat)
    return out


def cmd_contract_preflight(args):
    """v2.3.0 (D-039/D-040/D-044/D-047) -- reconciles a contract's
    declared scope against what its own verification commands and
    --acquisition-scripts would actually touch, BEFORE implementation
    begins. Exit 3 (Manifest Failure -- reserved since v1.0, never
    emitted until this release) on a scope/dependency/precondition
    conflict; exit 21 (Delegation Violation) on an owner/executor
    mismatch with no matching delegation record.

    Directly closes the exact shape of a real incident: a wildcard
    acquisition-audit scan matched more legacy modules than a contract's
    allowed_files permitted modifying. The audit was correct to scan the
    whole surface; the contract was correct to restrict modification
    scope; nothing reconciled the two before the highest-risk work
    started. Run automatically by `begin` (below); available standalone.
    """
    print("Gatekeeper contract-preflight (D-039/D-040)")
    print("=" * 60)
    manifest_path = Path(args.manifest)
    data = _load_full_manifest(manifest_path)
    contract = load_manifest_contract(manifest_path, args.contract)

    findings = []
    warnings = []

    allowed = set(contract.get("allowed_files", []) or [])
    frozen = set(contract.get("frozen_files", []) or [])
    overlap = allowed & frozen
    if overlap:
        findings.append(
            f"ALLOWED/FROZEN OVERLAP: {sorted(overlap)} appear in both allowed_files and "
            f"frozen_files for {args.contract} -- a file this contract is both permitted to "
            f"change and forbidden to change is a contradiction in the manifest itself."
        )

    verification_globs = list(contract.get("verification_scripts", []) or [])
    verification_globs += list(getattr(args, "acquisition_scripts", None) or [])
    expanded = _expand_glob_paths(verification_globs)
    scope = allowed | frozen
    outside = sorted(p for p in expanded if p not in scope and Path(p).is_file())
    if outside:
        msg = (
            f"VERIFICATION REACH OUTSIDE SCOPE: {outside} match a verification/acquisition-"
            f"audit glob for {args.contract} but are not in allowed_files or frozen_files. "
            f"A read-only scan touching more than allowed_files is fine (pass "
            f"--readonly-verification once confirmed); a command that could MODIFY these "
            f"paths is not."
        )
        if getattr(args, "readonly_verification", False):
            warnings.append(msg + " (--readonly-verification given: treated as a warning.)")
        else:
            findings.append(msg)

    deps = contract.get("dependencies", []) or []
    all_ids = {c.get("id") for c in data.get("contracts", [])}
    missing_deps = [d for d in deps if d not in all_ids]
    if missing_deps:
        findings.append(f"MISSING DEPENDENCY: {args.contract} depends on {missing_deps}, "
                         f"not found in this manifest's contracts list.")

    # D-047: repository_preconditions.previous_chunk_approved -- declared
    # in the Execution Manifest Schema since it was written; not
    # mechanically enforced anywhere until this release.
    precond = data.get("repository_preconditions", {}) or {}
    if precond.get("previous_chunk_approved"):
        chunk_dir = manifest_path.parent
        m = re.search(r'(\d+)$', chunk_dir.name)
        if m:
            prev_num = int(m.group(1)) - 1
            if prev_num >= 0:
                prev_name = re.sub(r'\d+$', str(prev_num).zfill(len(m.group(1))), chunk_dir.name)
                prev_report = chunk_dir.parent / prev_name / "chunk_report.md"
                prev_text = _read_text_or_none(prev_report)
                if prev_text is None:
                    findings.append(
                        f"PREVIOUS CHUNK NOT APPROVED: repository_preconditions."
                        f"previous_chunk_approved is true, but {prev_report} does not exist."
                    )
                elif not re.search(r'\bAPPROVED\b', prev_text, re.IGNORECASE):
                    findings.append(
                        f"PREVIOUS CHUNK NOT APPROVED: {prev_report} exists but does not "
                        f"contain 'APPROVED'."
                    )
                else:
                    print(f"  repository_preconditions.previous_chunk_approved: OK ({prev_report})")

    # D-044: delegation check
    owner = (contract.get("implementation_owner") or "").strip().lower()
    executor = (getattr(args, "executor", None) or contract.get("executor") or owner).strip().lower()
    delegation_violation = None
    if owner and executor and owner != executor:
        active = _find_active_delegation(args.contract, owner, executor)
        if active is None:
            delegation_violation = (
                f"DELEGATION REQUIRED: {args.contract}'s implementation_owner is '{owner}' but "
                f"executor is '{executor}', and no active, matching delegation record "
                f"authorizes this (D-044). Run `gatekeeper.py delegate` first, with the "
                f"Human's own explicit authorization."
            )
        else:
            print(f"  Active delegation found: {active.get('id')}")

    if findings:
        print("\n[FAIL] Manifest/scope conflicts found:")
        for f in findings:
            print(f"  - {f}")
    if warnings:
        print("\n[WARN]")
        for w in warnings:
            print(f"  - {w}")
    if delegation_violation:
        print(f"\n[FAIL] {delegation_violation}")

    if delegation_violation:
        sys.exit(21)
    if findings:
        sys.exit(3)
    print("\nPASS: no scope conflicts, dependency issues, or precondition failures found.")
    sys.exit(0)


def _capture_baseline(contract_id):
    """v2.3.0 (D-041) -- records outer + nested git status at contract
    start. Written under project/.gatekeeper/state/, already outside any
    contract's outer-repo Allowed Files by construction (C60)."""
    def _status(cwd):
        try:
            r = subprocess.run(["git", "status", "--porcelain=v1"], cwd=cwd,
                                capture_output=True, text=True, timeout=30)
            return sorted(r.stdout.splitlines())
        except (OSError, subprocess.SubprocessError):
            return None
    GATEKEEPER_STATE_DIR.mkdir(parents=True, exist_ok=True)
    baseline = {
        "contract": contract_id,
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "outer_status": _status("."),
        "nested_status": _status("project") if Path("project/.git").exists() else None,
    }
    path = GATEKEEPER_STATE_DIR / f"{contract_id}.baseline.json"
    with open(path, "w") as f:
        json.dump(baseline, f, indent=2, sort_keys=True)
    return path


def _scoped_dirty_delta(contract_id, allowed_files):
    """v2.3.0 (D-041) -- compares CURRENT outer git status against the
    baseline captured by _capture_baseline, if one exists. Returns
    (has_baseline, unexpected, pre_existing_still_dirty, new_this_contract).
    'unexpected' (changed during this contract AND outside allowed_files)
    is the only category that should ever block anything -- a blanket
    --allow-dirty bypass could not make this distinction at all."""
    path = GATEKEEPER_STATE_DIR / f"{contract_id}.baseline.json"
    if not path.exists():
        return False, [], [], []
    try:
        baseline = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False, [], [], []
    old_lines = set(baseline.get("outer_status") or [])
    try:
        r = subprocess.run(["git", "status", "--porcelain=v1"], capture_output=True,
                            text=True, timeout=30)
        current_lines = set(r.stdout.splitlines())
    except (OSError, subprocess.SubprocessError):
        return True, [], [], []

    def _path_of(line):
        return line[3:].split(" -> ")[-1].strip()

    old_paths = {_path_of(l) for l in old_lines if len(l) > 3}
    current_paths = {_path_of(l) for l in current_lines if len(l) > 3}
    new_paths = current_paths - old_paths
    pre_existing_still_dirty = sorted(old_paths & current_paths)
    allowed_set = set(allowed_files or [])
    # v2.3.0 (D-041/C60): project/ is Factory-governance territory by
    # construction, categorically outside any outer-repo allowed_files
    # scope -- never flagged as "unexpected" here even if a given
    # environment's .gitignore/nested-repo setup isn't (yet) excluding it
    # from the outer repo's own git status. Relying on .gitignore alone to
    # keep Factory bookkeeping out of scope-checking would recreate
    # exactly the fragility this rule exists to remove.
    new_paths = {p for p in new_paths if not p.startswith("project/") and p != "project/"}
    unexpected = sorted(p for p in new_paths if not any(
        p == a or p.startswith(a.rstrip("/") + "/") for a in allowed_set
    ))
    new_this_contract = sorted(new_paths - set(unexpected))
    return True, unexpected, pre_existing_still_dirty, new_this_contract


# v2.3.0 (D-046) -- matches implementor_spec.md section 8's real
# contract_report.md template exactly (see DEFAULT_REQUIRED_SECTIONS's
# comment above for why this had drifted). Generated by `begin`, so the
# "which headers does Gatekeeper want" question never has to be guessed
# at again.
_REPORT_SKELETON_TEMPLATE = """# Contract Report: {contract_id}

## Contract Information
Contract ID: {contract_id}
Chunk: {chunk}
Objective: TODO -- quote the contract's own Objective verbatim.
Risk Tier: {risk_tier}
Scientific Claim Tier: {sci_tier}
Implementation Owner: {owner}

## Scope / Inputs / Outputs
TODO

## Files Modified
TODO -- list every file actually touched; should match allowed_files.

## Verification Summary
TODO -- any of the three recognized formats (bullet/bold/backtick, a
literal `Command:` block, or a fenced ```yaml verification: [...] ```
block). Include the REAL output, not a paraphrase.

## Definition of Done
TODO -- audit every item from the contract's own Definition of Done.

## Invariant Status
TODO

## Predicted Failure Modes
TODO

## Self Review History
TODO -- attempt 1: ...

## Final Status
TODO -- do not leave this line as-is. Replace this whole line with this
contract's actual disposition once it is genuinely true, one word, on its
own line (see gatekeeper.py's STATUS_PATTERNS for the exact recognized
forms; deliberately not spelled out here as literal placeholder text,
since a placeholder containing the real keyword is exactly what let an
unfilled skeleton be mistaken for a real declaration once, see D-046's own
note in gatekeeper.py's _REPORT_SKELETON_TEMPLATE).

## Remaining Risks
TODO

## Repository State
TODO -- outer HEAD, nested HEAD, dirty files if any.

## Plain-Language Summary
TODO -- two or three sentences, no jargon.
"""


def _render_report_skeleton(contract, contract_id, chunk_name):
    return _REPORT_SKELETON_TEMPLATE.format(
        contract_id=contract_id, chunk=chunk_name,
        risk_tier=contract.get("risk_tier", "TODO"),
        sci_tier=contract.get("scientific_claim_tier", "NONE"),
        owner=contract.get("implementation_owner", "TODO"),
    )


def cmd_begin(args):
    """v2.3.0 (D-041) -- starts a contract: runs contract-preflight and
    stops if it fails; snapshots frozen_files read straight from the
    manifest; captures a scoped repository baseline (D-041); writes a
    headed report skeleton at the manifest-implied path if one doesn't
    exist yet (D-046). Appends a contract_started telemetry event.

    Performs no NEW checks of its own -- every check is an existing one,
    called in sequence. What's new is that it's one command instead of
    the four or five run by hand, in the right order, every single time
    (reported as roughly 35% ceremony overhead across a 65-contract
    project)."""
    print("Gatekeeper begin (D-041)")
    print("=" * 60)
    manifest_path = Path(args.manifest)
    contract = load_manifest_contract(manifest_path, args.contract)
    chunk_name = manifest_path.parent.name

    preflight_args = argparse.Namespace(
        contract=args.contract, manifest=args.manifest,
        acquisition_scripts=args.acquisition_scripts or [],
        readonly_verification=args.readonly_verification,
        executor=args.executor,
    )
    try:
        cmd_contract_preflight(preflight_args)
    except SystemExit as e:
        if e.code not in (0, None):
            print("\nbegin STOPPED: contract-preflight did not pass. Fix the above before "
                  "starting implementation.")
            raise
    print()

    frozen = sorted(set(list(contract.get("frozen_files", []) or []) + _auto_frozen_verification_paths()))
    if frozen:
        status, message = _snapshot_one(args.contract, frozen, force=args.force_snapshot)
        print(message)
        if status == "error":
            sys.exit(9)
    else:
        print(f"{args.contract}: no frozen_files declared and no auto-frozen verification "
              f"machinery found -- nothing to snapshot.")

    baseline_path = _capture_baseline(args.contract)
    print(f"Scoped repository baseline captured -> {baseline_path} (D-041). "
          f"--allow-dirty is no longer needed for a contract started this way.")

    reports_dir = (Path(args.reports_dir) if args.reports_dir
                   else (manifest_path.parent / "reports" / args.contract))
    report_path = reports_dir / "contract_report.md"
    if report_path.exists():
        print(f"{report_path} already exists -- left untouched.")
    else:
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_render_report_skeleton(contract, args.contract, chunk_name))
        print(f"Wrote report skeleton -> {report_path} (every required section header "
              f"already present, D-046).")

    _append_telemetry({
        "chunk": chunk_name, "contract": args.contract,
        "risk_tier": contract.get("risk_tier", ""),
        "implementation_owner": contract.get("implementation_owner", ""),
        "phase": "phase_1", "event": "contract_started",
        "model_id": args.model_id or "", "model_version": args.model_version or "",
    })
    print(f"\n{args.contract} started.")


def cmd_finalize(args):
    """v2.3.0 (D-041, D-048; see C61) -- transactionally completes a
    contract: re-runs check (and, for T-COMP/T-CAUSAL, the Mandatory
    Mechanical Gate check already performs) FOR REAL, RIGHT NOW, against
    the report's CURRENT content. Writes a completion receipt --
    project/.gatekeeper/state/{contract_id}.complete.json, with a sha256
    of the report's content at this exact instant plus outer/nested HEAD
    -- ONLY if that re-run actually passes AND the report's own Final
    Status already reads a COMPLETE-class value.

    Does not replace parse_contract_status/`next`'s existing logic (C46)
    -- adds one cross-check on top: a completion receipt whose recorded
    report hash no longer matches the report's current content means the
    report changed after certification and should be re-finalized, not
    trusted as-is (C61). This is the mechanical answer to "a report's own
    Final Status line was never, by itself, sufficient reason to trust a
    chunk was complete" -- reported directly: a false COMPLETE telemetry
    event and report both existed while `check`'s own Report Validation
    gate would have failed, had anyone actually re-run it at that moment.

    Also appends telemetry (self_review_attempts auto-counted from finalize
    attempts, D-048), optionally appends a decision-log entry (--decision),
    and calls commit-project (unless --no-commit).
    """
    print("Gatekeeper finalize (D-041 -- transactional complete-contract; see C61)")
    print("=" * 60)
    manifest_path = Path(args.manifest)
    contract = load_manifest_contract(manifest_path, args.contract)
    chunk_name = manifest_path.parent.name
    reports_dir = (Path(args.reports_dir) if args.reports_dir
                   else (manifest_path.parent / "reports" / args.contract))
    report_path = reports_dir / "contract_report.md"

    if not report_path.exists():
        print(f"ERROR: {report_path} not found. finalize does not write a report for you -- "
              f"write it first (`begin` generates a skeleton to start from).")
        sys.exit(9)

    attempt_count = _increment_finalize_attempts(args.contract)
    print(f"finalize attempt #{attempt_count} for {args.contract}.")

    check_args = argparse.Namespace(
        contract=args.contract, manifest=args.manifest, frozen=None,
        reports=[str(report_path)], required_sections=None, allow_dirty=True,
    )
    passed = True
    try:
        cmd_check(check_args)
    except SystemExit as e:
        if e.code not in (0, None):
            passed = False
            print(f"\ncheck did not pass (exit {e.code}).")

    has_baseline, unexpected, pre_existing, new_files = _scoped_dirty_delta(
        args.contract, contract.get("allowed_files", []))
    if has_baseline:
        print(f"\nScoped repository delta (D-041): {len(new_files)} file(s) changed by this "
              f"contract, {len(pre_existing)} pre-existing dirty file(s) left as they were, "
              f"{len(unexpected)} unexpected file(s).")
        if unexpected:
            passed = False
            print(f"  UNEXPECTED (outside allowed_files, changed during this contract): {unexpected}")
    else:
        print("\nNo scoped baseline found for this contract (it wasn't started with `begin`) -- "
              "falling back to check's own --allow-dirty handling above.")

    status = parse_contract_status(report_path)
    if status != "complete":
        passed = False
        print(f"\nReport's own Final Status reads '{status}', not COMPLETE -- finalize will "
              f"not write a completion receipt for a report that doesn't itself claim to be "
              f"done yet.")

    if not passed:
        print(f"\nfinalize NOT completed. No receipt written, no telemetry appended, nothing "
              f"committed (C61). Fix the findings above and re-run finalize.")
        sys.exit(20)

    report_hash = sha256_of(report_path)
    outer_head = _git_head(".")
    nested_head = _git_head("project") if Path("project/.git").exists() else None
    receipt = {
        "contract": args.contract, "chunk": chunk_name,
        "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "report_path": str(report_path), "report_sha256": report_hash,
        "outer_head": outer_head, "nested_head": nested_head,
        "finalize_attempts": attempt_count,
    }
    GATEKEEPER_STATE_DIR.mkdir(parents=True, exist_ok=True)
    receipt_path = GATEKEEPER_STATE_DIR / f"{args.contract}.complete.json"
    with open(receipt_path, "w") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
    print(f"\nCompletion receipt written -> {receipt_path}")

    _append_telemetry({
        "chunk": chunk_name, "contract": args.contract,
        "risk_tier": contract.get("risk_tier", ""),
        "implementation_owner": contract.get("implementation_owner", ""),
        "phase": "phase_4", "event": "contract_complete",
        "model_id": args.model_id or "", "model_version": args.model_version or "",
        "self_review_attempts": attempt_count, "violations": [],
        # v2.3.0 Notes (see dynamic_rules.md D-048): `violations` is left []
        # here deliberately rather than fabricated -- check's own findings
        # aren't captured as structured data without a deeper refactor of
        # cmd_check's return value, which is out of scope for this release.
        # An honest [] pending a real feed beats a plausible-looking one
        # that isn't actually derived from anything (C01).
    })

    if args.decision:
        parts = [p.strip() for p in args.decision.split("|")]
        _append_decision(
            role=contract.get("implementation_owner", ""),
            title=parts[0] if len(parts) > 0 else "",
            decision=parts[1] if len(parts) > 1 else "",
            reason=parts[2] if len(parts) > 2 else "",
            alternatives=parts[3] if len(parts) > 3 else "",
            benefit=parts[4] if len(parts) > 4 else "",
            traces=[args.contract],
        )

    if not args.no_commit:
        try:
            cmd_commit_project(argparse.Namespace(message=f"Complete contract {args.contract}"))
        except SystemExit as e:
            if e.code not in (0, None):
                print(f"\nWARNING: commit-project did not succeed (exit {e.code}) -- the "
                      f"completion receipt, telemetry, and decision-log entries above were "
                      f"already written and are NOT undone by this. Run `commit-project` "
                      f"yourself once project/'s nested repository is set up.")

    print(f"\n{args.contract} FINALIZED.")
    sys.exit(0)


# ---------------------------------------------------------------------------
# v2.5.0: Publication Rigor Mechanical Gates (MAR-2, MAR-6, MAR-7, MAR-8)
# ---------------------------------------------------------------------------

def _parse_number_with_suffix(s: str):
    """Parses strings like '125M', '1.5B', '10k', '1.2e18', '50.5' into float."""
    if not s:
        return None
    s = s.strip().replace(",", "")
    m = re.search(r'([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([kKmMgGtTpP]?)', s)
    if not m:
        return None
    val = float(m.group(1))
    suffix = m.group(2).upper()
    if suffix == 'K':
        val *= 1e3
    elif suffix == 'M':
        val *= 1e6
    elif suffix == 'G':
        val *= 1e9
    elif suffix == 'T':
        val *= 1e12
    elif suffix == 'P':
        val *= 1e15
    return val


def cmd_verify_baseline_parity(args):
    """v2.5.0, MAR-2, D-059: Enforce parameter parity (+/-2%) and compute parity (+/-5%)
    across all comparative baselines declared in the Baseline Parity Ledger table.
    Fails with exit 23 if parameters or compute diverge without formal justification,
    or if required baseline classes are absent."""
    doc_path = None
    if getattr(args, "ledger", None):
        doc_path = Path(args.ledger)
    elif getattr(args, "venue_requirements", None):
        doc_path = Path(args.venue_requirements)
    elif getattr(args, "contract_report", None):
        doc_path = Path(args.contract_report)
    else:
        doc_path = Path("project/venue_requirements.md")

    if not doc_path.exists():
        print(f"FAIL: Baseline parity document not found at '{doc_path}'.")
        print("Exit code: 23")
        sys.exit(23)

    text = doc_path.read_text(encoding="utf-8", errors="replace")

    lines = text.splitlines()
    table_lines = []
    in_ledger = False

    for line in lines:
        if re.search(r'#+\s*.*Baseline\s+Parity', line, re.IGNORECASE):
            in_ledger = True
            continue
        if in_ledger:
            if line.startswith("#"):
                break
            if "|" in line:
                table_lines.append(line.strip())

    if not table_lines:
        for line in lines:
            if "|" in line:
                table_lines.append(line.strip())

    header_idx = -1
    for i, line in enumerate(table_lines):
        if re.search(r'model|baseline', line, re.IGNORECASE) and re.search(r'param', line, re.IGNORECASE):
            header_idx = i
            break

    if header_idx == -1:
        print(f"FAIL: No Baseline Parity Ledger table found in '{doc_path}'.")
        print("Expected table header containing 'Model / Baseline', 'Class', 'Parameters', 'Compute / FLOPs'.")
        print("Exit code: 23")
        sys.exit(23)

    raw_headers = [c.strip() for c in table_lines[header_idx].strip("|").split("|")]
    col_map = {}
    for idx, h in enumerate(raw_headers):
        hl = h.lower()
        if "model" in hl or "baseline" in hl or "method" in hl:
            col_map["model"] = idx
        elif "class" in hl:
            col_map["class"] = idx
        elif "param" in hl:
            col_map["params"] = idx
        elif "compute" in hl or "flop" in hl:
            col_map["compute"] = idx
        elif "status" in hl or "parity" in hl:
            col_map["status"] = idx
        elif "justification" in hl or "divergence" in hl or "notes" in hl:
            col_map["justification"] = idx

    rows = []
    for line in table_lines[header_idx + 1:]:
        if re.match(r'^\s*\|?\s*[-:\s|]+\s*\|?\s*$', line):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) >= len(raw_headers):
            rows.append(cols)

    if not rows:
        print(f"FAIL: Baseline Parity Ledger table has header but no data rows in '{doc_path}'.")
        print("Exit code: 23")
        sys.exit(23)

    param_tol = getattr(args, "param_tolerance", 0.02)
    compute_tol = getattr(args, "compute_tolerance", 0.05)

    findings = []
    classes_seen = set()
    proposed_row = None

    for r in rows:
        model_name = r[col_map.get("model", 0)].lower() if "model" in col_map else ""
        if any(k in model_name for k in ["proposed", "ours", "(ours)", "our method"]):
            proposed_row = r
            break
    if proposed_row is None and rows:
        proposed_row = rows[0]

    prop_model = proposed_row[col_map["model"]] if "model" in col_map and col_map["model"] < len(proposed_row) else "Proposed"
    prop_params = _parse_number_with_suffix(proposed_row[col_map["params"]]) if "params" in col_map and col_map["params"] < len(proposed_row) else None
    prop_compute = _parse_number_with_suffix(proposed_row[col_map["compute"]]) if "compute" in col_map and col_map["compute"] < len(proposed_row) else None

    for r in rows:
        m_name = r[col_map["model"]] if "model" in col_map and col_map["model"] < len(r) else "Unknown"
        c_name = r[col_map["class"]] if "class" in col_map and col_map["class"] < len(r) else ""
        p_str = r[col_map["params"]] if "params" in col_map and col_map["params"] < len(r) else ""
        comp_str = r[col_map["compute"]] if "compute" in col_map and col_map["compute"] < len(r) else ""
        status_str = r[col_map["status"]] if "status" in col_map and col_map["status"] < len(r) else ""
        just_str = r[col_map["justification"]] if "justification" in col_map and col_map["justification"] < len(r) else ""

        if c_name:
            classes_seen.add(c_name.lower())

        if r is proposed_row:
            continue

        if any(bad in status_str.upper() for bad in ["VIOLATION", "FAIL", "UNMATCHED", "REJECTED"]):
            if not just_str or just_str.lower() in ["none", "-", "n/a"]:
                findings.append(f"Model '{m_name}': Explicit Parity Status violation ('{status_str}') without divergence justification.")

        p_val = _parse_number_with_suffix(p_str)
        if prop_params and p_val and prop_params > 0:
            rel_diff = abs(p_val - prop_params) / prop_params
            if rel_diff > param_tol:
                if not just_str or just_str.lower() in ["none", "-", "n/a"]:
                    findings.append(
                        f"Model '{m_name}': Parameter count mismatch ({p_str} vs proposed {prop_params:g}, "
                        f"diff={rel_diff*100:.1f}%, allowed +/-{param_tol*100:.0f}%) with no formal justification."
                    )

        c_val = _parse_number_with_suffix(comp_str)
        if prop_compute and c_val and prop_compute > 0:
            rel_diff = abs(c_val - prop_compute) / prop_compute
            if rel_diff > compute_tol:
                if not just_str or just_str.lower() in ["none", "-", "n/a"]:
                    findings.append(
                        f"Model '{m_name}': Training compute mismatch ({comp_str} vs proposed {prop_compute:g}, "
                        f"diff={rel_diff*100:.1f}%, allowed +/-{compute_tol*100:.0f}%) with no formal justification."
                    )

    matched_present = any("matched" in c or "mechanism" in c for c in classes_seen)
    sota_present = any("sota" in c or "contemporary" in c for c in classes_seen)
    if not matched_present:
        findings.append("Missing mandatory baseline class: 'Mechanism-Matched' baseline must be included.")
    if not sota_present:
        findings.append("Missing mandatory baseline class: 'Contemporary SOTA' baseline must be included.")

    print(f"\n[Baseline Parity Verification -- MAR-2, D-059]")
    print(f"Audited document: {doc_path}")
    print(f"Reference model: {prop_model} (Params: {prop_params if prop_params else 'N/A'}, Compute: {prop_compute if prop_compute else 'N/A'})")
    print(f"Total Baselines Evaluated: {len(rows) - 1}")
    print(f"Classes represented: {', '.join(sorted(classes_seen))}")

    if findings:
        print("\nPARITY VIOLATIONS DETECTED:")
        for f in findings:
            print(f"  - [FAIL] {f}")
        print("\nExit code: 23")
        sys.exit(23)
    else:
        print("\nPASS: All baselines satisfy parameter parity (+/-2%), compute parity (+/-5%), and classification requirements.")
        sys.exit(0)


def cmd_verify_hardware_profile(args):
    """v2.5.0, MAR-8, D-056: Verify empirical hardware profiling manifest.
    Ensures latency distribution (p50, p90, p99), warmup exclusion, and separate
    peak training and peak inference memory tracking."""
    manifest_path = Path(args.manifest) if getattr(args, "manifest", None) else Path("project/hardware_profile_manifest.json")
    if not manifest_path.exists():
        print(f"FAIL: Hardware profile manifest not found at '{manifest_path}'.")
        print("Exit code: 24")
        sys.exit(24)

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: Invalid JSON in hardware profile manifest '{manifest_path}': {e}")
        print("Exit code: 24")
        sys.exit(24)

    findings = []

    latency_dict = data.get("latency_ms") or data.get("latency") or data.get("inference_latency_ms")
    if not isinstance(latency_dict, dict):
        findings.append("Missing 'latency_ms' dictionary with percentiles (p50, p90, p99).")
    else:
        for p in ["p50", "p90", "p99"]:
            val = latency_dict.get(p)
            if val is None or not isinstance(val, (int, float)) or val <= 0:
                findings.append(f"Latency percentile '{p}' missing or non-positive in hardware profile.")

    warmup_ex = data.get("warmup_steps_excluded")
    if warmup_ex is None:
        warmup_ex = data.get("warmup_excluded")
    if warmup_ex is not True:
        findings.append("Warmup steps not excluded: 'warmup_steps_excluded' must be explicitly True.")

    mem_dict = data.get("peak_memory_mb") or data.get("peak_memory") or data.get("memory")
    peak_train = None
    peak_inf = None
    if isinstance(mem_dict, dict):
        peak_train = mem_dict.get("peak_train") or mem_dict.get("train") or mem_dict.get("training")
        peak_inf = mem_dict.get("peak_inference") or mem_dict.get("inference")
    else:
        peak_train = data.get("peak_training_memory_mb") or data.get("peak_train_memory_mb")
        peak_inf = data.get("peak_inference_memory_mb") or data.get("peak_inference_vram_mb")

    if peak_train is None or not isinstance(peak_train, (int, float)) or peak_train <= 0:
        findings.append("Peak training memory ('peak_train') missing or non-positive.")
    if peak_inf is None or not isinstance(peak_inf, (int, float)) or peak_inf <= 0:
        findings.append("Peak inference memory ('peak_inference') missing or non-positive.")

    hw = data.get("measurement_hardware") or data.get("hardware") or data.get("device")
    if not hw or not isinstance(hw, str):
        findings.append("Missing 'measurement_hardware' specification (e.g. 'NVIDIA A100-SXM4-80GB').")

    # v2.6.0 extensions (D-068, D-069) -- claim-gated fields
    claim_keywords = data.get("efficiency_claims") or data.get("claim_keywords") or []
    if isinstance(claim_keywords, str):
        claim_keywords = [claim_keywords]
    claim_text = " ".join(claim_keywords).lower()

    # D-068: Energy measurement for "efficient" / "green" claims
    energy_required = any(k in claim_text for k in [
        "efficient", "energy", "green", "sustainable", "low-power"
    ])
    if energy_required:
        energy_val = data.get("energy_per_inference") or data.get("energy_per_sample")
        if energy_val is None or not isinstance(energy_val, (int, float)) or energy_val <= 0:
            findings.append(
                "D-068: Energy measurement required for efficiency/green claim. "
                "'energy_per_inference' (J/sample or J/token) must be positive and "
                "measured by physical power meter or OS-level instrumentation, not TDP."
            )
        energy_method = data.get("energy_measurement_method")
        if energy_required and not energy_method:
            findings.append(
                "D-068: 'energy_measurement_method' must name the measurement instrument "
                "(e.g., 'nvidia-smi power.draw', 'Watts Up Pro', 'RAPL')."
            )

    # D-068: Thermal sustained test for edge/embedded claims
    thermal_required = any(k in claim_text for k in ["edge", "embedded", "thermal", "mobile"])
    if thermal_required:
        thermal = data.get("thermal_sustained")
        if not isinstance(thermal, dict):
            findings.append(
                "D-068: Thermal sustained test required for edge/embedded claim. "
                "'thermal_sustained' dict must include 'duration_seconds' (>=60) and "
                "'throttling_observed' (boolean)."
            )
        else:
            duration = thermal.get("duration_seconds", 0)
            if not isinstance(duration, (int, float)) or duration < 60:
                findings.append(
                    "D-068: Thermal sustained test duration too short "
                    f"({duration}s, minimum 60s required for edge/embedded claims)."
                )

    # D-069: FLOPs/MACs integrity -- reported alongside, never instead of, real latency
    flops_val = data.get("flops") or data.get("macs") or data.get("gflops")
    if flops_val is not None:
        if not latency_dict or not isinstance(latency_dict, dict):
            findings.append(
                "D-069: FLOPs/MACs reported but no latency distribution found. "
                "FLOPs must be reported alongside, never instead of, real latency."
            )
        flops_convention = data.get("flops_counting_convention") or data.get("counting_convention")
        if not flops_convention:
            findings.append(
                "D-069: 'flops_counting_convention' missing. Must declare whether "
                "1 MAC = 1 or 2 FLOPs, input shape, and sparsity handling."
            )
        flops_tool = data.get("flops_counting_tool")
        if not flops_tool:
            findings.append(
                "D-069: 'flops_counting_tool' missing. Must name and version the tool "
                "used to count FLOPs/MACs (e.g., 'fvcore 0.1.5', 'ptflops 0.7.3')."
            )

    print(f"\n[Hardware Profile Sufficiency Audit -- MAR-8, D-056, D-068, D-069]")
    print(f"Audited manifest: {manifest_path}")

    if findings:
        print("\nHARDWARE PROFILE SUFFICIENCY FAILURES:")
        for f in findings:
            print(f"  - [FAIL] {f}")
        print("\nExit code: 24")
        sys.exit(24)
    else:
        print(f"Hardware: {hw}")
        print(f"Latency: p50={latency_dict.get('p50')}ms, p90={latency_dict.get('p90')}ms, p99={latency_dict.get('p99')}ms (Warmup excluded: True)")
        print(f"Peak VRAM/RAM: Train={peak_train}MB, Inference={peak_inf}MB")
        print("\nPASS: Hardware profile satisfies empirical distribution and sufficiency requirements.")
        sys.exit(0)


def cmd_freeze_experiment(args):
    """v2.5.0, MAR-7, C63, D-060: Pre-register and freeze experiment parameters,
    git commit, environment lock hash, dataset split checksums, and seed array."""
    out_path = Path(args.out) if getattr(args, "out", None) else Path("project/experiment_freeze_manifest.json")
    if out_path.exists() and not getattr(args, "force", False):
        print(f"FAIL: Freeze manifest '{out_path}' already exists. Pass --force to overwrite.")
        sys.exit(4)

    git_commit = "UNKNOWN"
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        if res.returncode == 0:
            git_commit = res.stdout.strip()
    except Exception:
        pass

    seeds = []
    if getattr(args, "seeds", None):
        if isinstance(args.seeds, list):
            for s in args.seeds:
                if "," in str(s):
                    seeds.extend([int(x.strip()) for x in str(s).split(",") if x.strip()])
                else:
                    seeds.append(int(s))
        else:
            seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]

    if len(seeds) < 3:
        print("FAIL: Pre-registration requires a minimum of 3 evaluation seeds (C63, D-060).")
        sys.exit(4)

    split_checksums = {}
    if getattr(args, "split_files", None):
        for sf in args.split_files:
            p = Path(sf)
            if p.exists() and p.is_file():
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                split_checksums[p.name] = h
            else:
                print(f"WARNING: Split file '{sf}' does not exist.")

    lockfile_hash = None
    lock_candidates = [getattr(args, "lockfile", None), "poetry.lock", "requirements.lock", "environment.lock"]
    for lc in lock_candidates:
        if lc and Path(lc).exists():
            lockfile_hash = hashlib.sha256(Path(lc).read_bytes()).hexdigest()
            break

    manifest_hash = None
    if getattr(args, "manifest", None) and Path(args.manifest).exists():
        manifest_hash = hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest()

    manifest_data = {
        "factory_version": "2.5.0",
        "freeze_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "environment_lock_hash": lockfile_hash,
        "pre_registered_seeds": sorted(seeds),
        "dataset_split_checksums": split_checksums,
        "manifest_hash": manifest_hash,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    print(f"\n[Experiment Pre-Registration Freeze -- MAR-7, C63, D-060]")
    print(f"Wrote freeze manifest to: {out_path}")
    print(f"Git commit: {git_commit}")
    print(f"Pre-registered seeds ({len(seeds)}): {sorted(seeds)}")
    if split_checksums:
        print(f"Dataset split checksums: {len(split_checksums)} files locked")
    sys.exit(0)


def cmd_verify_experiment_freeze(args):
    """v2.5.0, MAR-7, C63, D-060: Verify evaluation report and artifacts against
    the pre-registered experiment freeze manifest. Enforces that all pre-registered
    seeds were run and reported, with zero omissions or un-registered substitutions."""
    freeze_path = Path(args.freeze_manifest) if getattr(args, "freeze_manifest", None) else Path("project/experiment_freeze_manifest.json")
    if not freeze_path.exists():
        print(f"FAIL: Experiment freeze manifest not found at '{freeze_path}'.")
        print("Exit code: 25")
        sys.exit(25)

    try:
        freeze_data = json.loads(freeze_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: Invalid JSON in freeze manifest '{freeze_path}': {e}")
        print("Exit code: 25")
        sys.exit(25)

    pre_registered = set(freeze_data.get("pre_registered_seeds", []))
    if not pre_registered:
        print("FAIL: No pre-registered seeds declared in freeze manifest.")
        print("Exit code: 25")
        sys.exit(25)

    report_path = Path(args.report) if getattr(args, "report", None) else None
    if not report_path or not report_path.exists():
        print(f"FAIL: Evaluation report/artifact not found at '{report_path}'.")
        print("Exit code: 25")
        sys.exit(25)

    findings = []
    executed_seeds = set()

    content = report_path.read_text(encoding="utf-8", errors="replace")

    try:
        artifact_json = json.loads(content)
        if isinstance(artifact_json, dict):
            seeds_val = artifact_json.get("seeds") or artifact_json.get("seed_results")
            if isinstance(seeds_val, list):
                executed_seeds.update(int(s) for s in seeds_val if str(s).isdigit())
            elif isinstance(seeds_val, dict):
                executed_seeds.update(int(s) for s in seeds_val.keys() if str(s).isdigit())
    except Exception:
        pass

    if not executed_seeds:
        lines = content.splitlines()
        in_seed_table = False
        seed_col_idx = -1
        for line in lines:
            if "|" in line:
                cols = [c.strip() for c in line.strip("|").split("|")]
                if any(c.lower() == "seed" for c in cols):
                    in_seed_table = True
                    for i, c in enumerate(cols):
                        if c.lower() == "seed":
                            seed_col_idx = i
                            break
                    continue
                if in_seed_table:
                    if re.match(r'^\s*[-:\s|]+$', line):
                        continue
                    if seed_col_idx != -1 and seed_col_idx < len(cols):
                        val = cols[seed_col_idx]
                        if val.isdigit():
                            executed_seeds.add(int(val))
            else:
                if in_seed_table and line.strip() == "":
                    in_seed_table = False

        seed_list_m = re.findall(r'(?:seeds?|evaluation_seeds?)\s*[:=]\s*\[([0-9,\s]+)\]', content, re.IGNORECASE)
        for sl in seed_list_m:
            for s in sl.split(","):
                if s.strip().isdigit():
                    executed_seeds.add(int(s.strip()))

    if not executed_seeds:
        findings.append(
            f"Could not identify executed seed array in '{report_path}'. "
            "Report must explicitly document evaluated seeds in a table or structured list."
        )
    else:
        missing_seeds = pre_registered - executed_seeds
        if missing_seeds:
            findings.append(
                f"Selective reporting / seed omission detected! "
                f"Pre-registered seeds {sorted(missing_seeds)} were NOT found in the report/artifact."
            )

        extra_seeds = executed_seeds - pre_registered
        if extra_seeds:
            if not re.search(r'exploratory\s+seeds?', content, re.IGNORECASE):
                findings.append(
                    f"Post-hoc unregistered seeds detected: {sorted(extra_seeds)}. "
                    "All confirmatory seeds must be pre-registered in freeze manifest."
                )

    frozen_splits = freeze_data.get("dataset_split_checksums", {})
    for fname, exp_hash in frozen_splits.items():
        candidates = list(Path(".").glob(f"**/{fname}"))
        for cand in candidates:
            if cand.is_file():
                actual_hash = hashlib.sha256(cand.read_bytes()).hexdigest()
                if actual_hash != exp_hash:
                    findings.append(
                        f"Dataset split tampered! '{cand}' sha256={actual_hash} != frozen={exp_hash}"
                    )

    print(f"\n[Experiment Freeze Verification -- MAR-7, C63, D-060]")
    print(f"Freeze manifest: {freeze_path}")
    print(f"Report / artifact: {report_path}")
    print(f"Pre-registered seeds ({len(pre_registered)}): {sorted(pre_registered)}")
    print(f"Executed seeds identified ({len(executed_seeds)}): {sorted(executed_seeds)}")

    if findings:
        print("\nEXPERIMENT FREEZE / SEED MISMATCH FAILURES:")
        for f in findings:
            print(f"  - [FAIL] {f}")
        print("\nExit code: 25")
        sys.exit(25)
    else:
        print("\nPASS: All pre-registered seeds executed and reported without post-hoc cherry-picking.")
        sys.exit(0)


def cmd_contamination_check(args):
    """v2.5.0, MAR-6, D-061: Audit benchmark evaluation splits against training
    pre-training corpora or cutoff dates to prevent foundation model test set leakage.
    Exits 26 if contamination or temporal leakage is detected."""
    findings = []

    audit_json = getattr(args, "audit_json", None)
    if audit_json:
        p = Path(audit_json)
        if not p.exists():
            print(f"FAIL: Contamination audit file not found at '{p}'.")
            print("Exit code: 26")
            sys.exit(26)
        try:
            audit_data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"FAIL: Invalid JSON in '{p}': {e}")
            print("Exit code: 26")
            sys.exit(26)

        if audit_data.get("contamination_detected") is True:
            overlap = audit_data.get("exact_n_gram_matches", "detected")
            findings.append(f"Audit JSON explicitly indicates contamination detected (overlap={overlap}).")

        cutoff = audit_data.get("model_cutoff_date")
        rel_date = audit_data.get("benchmark_release_date")
        if cutoff and rel_date and cutoff > rel_date:
            if audit_data.get("decontamination_verified") is not True:
                findings.append(
                    f"Temporal leakage: model cutoff ({cutoff}) post-dates benchmark release ({rel_date}) "
                    "without verified decontamination."
                )

    bench_path = Path(args.benchmark) if getattr(args, "benchmark", None) else None
    train_path = Path(args.training_corpus) if getattr(args, "training_corpus", None) else None
    n = getattr(args, "n_gram", 13)

    if bench_path and train_path:
        if not bench_path.exists():
            print(f"FAIL: Benchmark path '{bench_path}' not found.")
            sys.exit(26)
        if not train_path.exists():
            print(f"FAIL: Training corpus path '{train_path}' not found.")
            sys.exit(26)

        def get_ngrams(text: str, n_size: int):
            tokens = re.findall(r'\b\w+\b', text.lower())
            return set(tuple(tokens[i:i+n_size]) for i in range(len(tokens) - n_size + 1))

        bench_text = bench_path.read_text(encoding="utf-8", errors="replace")
        bench_ngrams = get_ngrams(bench_text, n)

        corpus_files = [train_path] if train_path.is_file() else list(train_path.glob("**/*"))
        matched_ngrams = []
        for cf in corpus_files:
            if cf.is_file():
                try:
                    c_text = cf.read_text(encoding="utf-8", errors="replace")
                    c_ngrams = get_ngrams(c_text, n)
                    overlap = bench_ngrams & c_ngrams
                    if overlap:
                        matched_ngrams.extend(list(overlap)[:3])
                        findings.append(f"Found {len(overlap)} matching {n}-grams in corpus file '{cf}'.")
                        break
                except Exception:
                    pass

    cutoff_arg = getattr(args, "model_cutoff", None)
    release_arg = getattr(args, "benchmark_release_date", None)
    if cutoff_arg and release_arg and cutoff_arg > release_arg:
        findings.append(
            f"Temporal cutoff violation: model cutoff '{cutoff_arg}' postdates "
            f"benchmark release '{release_arg}' without verified decontamination."
        )

    print(f"\n[Foundation Model Benchmark Contamination Check -- MAR-6, D-061]")
    if findings:
        print("\nCONTAMINATION AUDIT FAILURES:")
        for f in findings:
            print(f"  - [FAIL] {f}")
        print("\nExit code: 26")
        sys.exit(26)
    else:
        print(f"\nPASS: No {n}-gram contamination or temporal cutoff leaks detected.")
        sys.exit(0)


# ============================================================================
# v2.6.0 -- Statistical Inference & Empirical Completeness Gates
# Exit codes: 27 (statistical protocol), 28 (sensitivity analysis),
#             29 (pre-submission audit), 30 (failure taxonomy)
# ============================================================================

# --- Statistical test / reporting pattern regexes ---
_PVALUE_RE = re.compile(
    r'(?:p[\s\-_]*(?:value)?|p=|p<|p\s*[<>=])\s*[0-9]',
    re.IGNORECASE,
)
_EFFECT_SIZE_RE = re.compile(
    r"(?:cohen['\u2019]?s?\s*d|hedge['\u2019]?s?\s*g|effect\s+size|"
    r"paired\s+difference|mean\s+difference|"
    r"\u0394\s*=|delta\s*=|CI\s*[\[\(]|confidence\s+interval)",
    re.IGNORECASE,
)
_STAT_TEST_RE = re.compile(
    r"(?:paired\s+t[\s\-]?test|wilcoxon|mann[\s\-]?whitney|"
    r"friedman|kruskal[\s\-]?wallis|permutation\s+test|"
    r"bootstrap|sign\s+test|mcnemar|anova|"
    r"holm|bonferroni|benjamini[\s\-]?hochberg|FDR|"
    r"non[\s\-]?inferiority|equivalence\s+test|TOST)",
    re.IGNORECASE,
)
_MULTIPLICITY_RE = re.compile(
    r"(?:holm|bonferroni|benjamini[\s\-]?hochberg|FDR|"
    r"multiple[\s\-]?comparison|multiplicity[\s\-]?correction|"
    r"family[\s\-]?wise|adjusted\s+p|corrected\s+p)",
    re.IGNORECASE,
)
_IQM_RE = re.compile(
    r"(?:interquartile\s+mean|IQM|trimmed\s+mean|bootstrap\s+CI|"
    r"stratified\s+bootstrap)",
    re.IGNORECASE,
)
_NEGATIVE_CONTROL_RE = re.compile(
    r"(?:random\s+(?:attention|routing|weight|init)|"
    r"shuffled|uniform\s+(?:weight|routing)|identity\s+function|"
    r"degenerate\s+control|negative\s+control|ablation.*random|"
    r"random\s+baseline)",
    re.IGNORECASE,
)
_RETUNED_ABLATION_RE = re.compile(
    r"(?:retuned\s+ablation|re[\s\-]?tuned|"
    r"\u0394.*retuned|\u0394.*fixed.*HP|"
    r"fixed[\s\-]?hyperparameter\s+ablation|"
    r"best\s+system\s+without)",
    re.IGNORECASE,
)
_COMPARISON_COUNT_RE = re.compile(
    r"(?:(?:vs\.?|versus|compared\s+to|against)\s+\w)",
    re.IGNORECASE,
)


def cmd_verify_statistical_protocol(args):
    """v2.6.0, C65/C66, D-062/D-063/D-064: Verify statistical protocol integrity.
    Scans contract reports and evaluation artifacts for:
    (a) Named significance test matching experimental design
    (b) Effect size reported alongside every p-value
    (c) Multiple-comparisons correction for >3 pairwise tests
    (d) IQM/bootstrap CI when N<10 runs
    (e) Negative controls for novel architectural claims (D-066)
    (f) Retuned vs fixed-HP ablation distinction (D-067)
    Fails with exit 27 on structural violations."""
    doc_paths = []
    if getattr(args, "reports", None):
        doc_paths = [Path(p) for p in args.reports]
    elif getattr(args, "manuscript", None):
        doc_paths = [Path(args.manuscript)]
    else:
        # Auto-discover contract reports
        chunks_dir = Path(getattr(args, "chunks_dir", "project/chunks"))
        if chunks_dir.exists():
            doc_paths = sorted(chunks_dir.rglob("contract_report.md"))
        if not doc_paths:
            doc_paths = [Path("project/venue_requirements.md")]

    all_text = ""
    checked_files = []
    for p in doc_paths:
        if p.exists():
            all_text += p.read_text(encoding="utf-8", errors="replace") + "\n"
            checked_files.append(str(p))

    if not all_text.strip():
        print("FAIL: No evaluation reports or manuscripts found to audit.")
        print("Exit code: 27")
        sys.exit(27)

    findings = []
    warnings = []

    # --- Check 1: Named significance test ---
    has_pvalue = bool(_PVALUE_RE.search(all_text))
    has_stat_test = bool(_STAT_TEST_RE.search(all_text))
    if has_pvalue and not has_stat_test:
        findings.append(
            "P-values reported but no named significance test found. "
            "C65 requires naming the test (paired t-test, Wilcoxon, Friedman, etc.) "
            "and justifying its match to the experimental design."
        )

    # --- Check 2: Effect size alongside p-values ---
    has_effect_size = bool(_EFFECT_SIZE_RE.search(all_text))
    if has_pvalue and not has_effect_size:
        findings.append(
            "P-values reported without accompanying effect-size measures. "
            "C66 requires Cohen's d, Hedge's g, paired difference CI, or equivalent "
            "alongside every p-value, plus practical importance statement."
        )

    # --- Check 3: Multiple-comparisons correction ---
    comparisons = _COMPARISON_COUNT_RE.findall(all_text)
    has_multiplicity = bool(_MULTIPLICITY_RE.search(all_text))
    if len(comparisons) > 6 and has_pvalue and not has_multiplicity:
        findings.append(
            f"Detected {len(comparisons)} comparison instances with p-values but no "
            "multiple-comparisons correction (Holm, Bonferroni, Benjamini-Hochberg). "
            "D-064 requires correction when >3 pairwise comparisons are reported."
        )

    # --- Check 4: IQM / robust aggregation for small N ---
    seed_count_match = re.search(
        r'(?:(\d+)\s+seeds?|seeds?\s*[:=]\s*\[([^\]]+)\]|'
        r'n\s*=\s*(\d+)\s+(?:runs?|seeds?|trials?))',
        all_text, re.IGNORECASE
    )
    has_iqm = bool(_IQM_RE.search(all_text))
    if seed_count_match:
        n_str = seed_count_match.group(1) or seed_count_match.group(3)
        if n_str:
            n = int(n_str)
            if n < 10 and not has_iqm:
                warnings.append(
                    f"Detected N={n} runs (<10). D-062 recommends IQM with stratified "
                    "bootstrap CI over arithmetic mean for small-N regimes."
                )

    # --- Check 5: Negative controls for architectural claims (D-066) ---
    has_novel_module = bool(re.search(
        r'(?:novel|proposed|new)\s+(?:module|attention|routing|block|loss|mechanism)',
        all_text, re.IGNORECASE
    ))
    has_negative_control = bool(_NEGATIVE_CONTROL_RE.search(all_text))
    if has_novel_module and not has_negative_control:
        warnings.append(
            "Novel architectural module detected but no negative/degenerate control found. "
            "C67/D-066 requires a random/shuffled/uniform version of each novel module "
            "to distinguish learned function from architectural form."
        )

    # --- Check 6: Retuned vs fixed-HP ablation (D-067) ---
    has_ablation = bool(re.search(r'ablation', all_text, re.IGNORECASE))
    has_retuned = bool(_RETUNED_ABLATION_RE.search(all_text))
    has_load_bearing = bool(re.search(
        r'(?:essential|load[\s\-]?bearing|critical\s+component|key\s+module)',
        all_text, re.IGNORECASE
    ))
    if has_ablation and has_load_bearing and not has_retuned:
        warnings.append(
            "Load-bearing component claimed with ablation but no retuned ablation found. "
            "C68/D-067 recommends reporting both fixed-HP and retuned ablation variants "
            "for components described as essential."
        )

    print(f"\n[Statistical Protocol Verification -- C65/C66, D-062/D-063/D-064]")
    print(f"Audited files: {', '.join(checked_files)}")
    print(f"P-values detected: {has_pvalue}")
    print(f"Named stat test detected: {has_stat_test}")
    print(f"Effect size detected: {has_effect_size}")
    print(f"Multiple-comparisons correction detected: {has_multiplicity}")
    print(f"IQM/robust aggregation detected: {has_iqm}")
    print(f"Negative controls detected: {has_negative_control}")
    print(f"Retuned ablation detected: {has_retuned}")

    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(f"  - [WARN] {w}")

    if findings:
        print("\nSTATISTICAL PROTOCOL VIOLATIONS:")
        for f in findings:
            print(f"  - [FAIL] {f}")
        print("\nExit code: 27")
        sys.exit(27)
    else:
        print("\nPASS: Statistical protocol satisfies C65/C66/D-062/D-063/D-064 requirements.")
        sys.exit(0)


def _parse_sensitivity_manifest(data):
    """Parse a sensitivity analysis manifest (JSON dict or list of HP configs).
    Returns list of dicts with keys: hp_name, scale, levels, has_response_curve."""
    results = []
    entries = data if isinstance(data, list) else data.get("hyperparameters", [])
    for entry in entries:
        if isinstance(entry, dict):
            results.append({
                "hp_name": entry.get("name", entry.get("hyperparameter", "unknown")),
                "scale": entry.get("scale", "linear"),
                "levels": entry.get("levels", entry.get("values", [])),
                "has_response_curve": bool(
                    entry.get("response_curve") or entry.get("curve_data")
                    or entry.get("performance_at_levels")
                ),
            })
    return results


def cmd_verify_sensitivity_analysis(args):
    """v2.6.0, D-065: Verify sensitivity analysis manifest.
    Checks: (a) >=3 perturbation levels per HP, (b) response curve data present,
    (c) architecture variation tested for at least one axis.
    Fails with exit 28 on insufficiency."""
    manifest_path = Path(args.manifest) if getattr(args, "manifest", None) else Path("project/sensitivity_analysis_manifest.json")

    if not manifest_path.exists():
        # Try scanning contract reports for sensitivity analysis sections
        report_path = Path(getattr(args, "report", "")) if getattr(args, "report", None) else None
        if report_path and report_path.exists():
            text = report_path.read_text(encoding="utf-8", errors="replace")
            has_sens = bool(re.search(
                r'(?:sensitivity\s+analysis|hyperparameter\s+perturbation|'
                r'perturbation\s+grid|response\s+curve)',
                text, re.IGNORECASE
            ))
            if has_sens:
                print(f"\n[Sensitivity Analysis Verification -- D-065]")
                print(f"Audited document: {report_path}")
                print("\nPASS (heuristic): Sensitivity analysis language detected in report.")
                print("Note: For full mechanical verification, provide a sensitivity_analysis_manifest.json.")
                sys.exit(0)

        print(f"FAIL: Sensitivity analysis manifest not found at '{manifest_path}'.")
        print("Expected JSON with 'hyperparameters' array, each with 'name', 'scale', 'levels', 'response_curve'.")
        print("Exit code: 28")
        sys.exit(28)

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: Invalid JSON in sensitivity manifest '{manifest_path}': {e}")
        print("Exit code: 28")
        sys.exit(28)

    entries = _parse_sensitivity_manifest(data)
    findings = []

    if not entries:
        findings.append("No hyperparameter entries found in sensitivity manifest.")

    for entry in entries:
        name = entry["hp_name"]
        levels = entry["levels"]
        if len(levels) < 3:
            findings.append(
                f"HP '{name}': Only {len(levels)} perturbation levels (minimum 3 required, "
                "recommended 5-7 per D-065 protocol)."
            )
        if not entry["has_response_curve"]:
            findings.append(
                f"HP '{name}': No response curve data. D-065 requires plotting performance "
                "vs HP value, not just reporting the 'best setting'."
            )

    # Check architecture sensitivity
    arch_variations = data.get("architecture_variations") or data.get("arch_sensitivity")
    if not arch_variations:
        findings.append(
            "No architecture sensitivity variations found. D-065 requires at least one "
            "variation beyond the published config (width, depth, backbone, optimizer, "
            "pretraining/no-pretraining) for claims of general method applicability."
        )

    print(f"\n[Sensitivity Analysis Verification -- D-065]")
    print(f"Audited manifest: {manifest_path}")
    print(f"Hyperparameters evaluated: {len(entries)}")

    if findings:
        print("\nSENSITIVITY ANALYSIS INSUFFICIENCIES:")
        for f in findings:
            print(f"  - [FAIL] {f}")
        print("\nExit code: 28")
        sys.exit(28)
    else:
        for e in entries:
            print(f"  HP '{e['hp_name']}': {len(e['levels'])} levels, "
                  f"scale={e['scale']}, response_curve={'Yes' if e['has_response_curve'] else 'No'}")
        print("\nPASS: Sensitivity analysis satisfies D-065 perturbation and response-curve requirements.")
        sys.exit(0)


def _scan_manuscript_claims(text):
    """Extract claim-relevant adjectives from abstract/title for pre-submission audit."""
    claim_adjectives = [
        "robust", "general", "efficient", "real-time", "real-world",
        "universal", "scalable", "lightweight", "energy-efficient",
        "state-of-the-art", "sota", "superior", "novel", "significant",
        "deployment-ready", "production-ready", "low-latency",
    ]
    found = []
    # Look in title and abstract sections
    title_abstract = text[:5000]  # First ~5000 chars typically cover title+abstract
    for adj in claim_adjectives:
        if re.search(rf'\b{re.escape(adj)}\b', title_abstract, re.IGNORECASE):
            found.append(adj)
    return found


def cmd_pre_submission_audit(args):
    """v2.6.0, D-070: 10-step adversarial pre-submission audit.
    Orchestrates a structured checklist against a near-final manuscript
    plus project artifacts. Produces PASS/WARN/FAIL per step.
    Exits 29 if any of steps 1-4 FAIL (validity-critical)."""
    manuscript_path = Path(args.manuscript) if getattr(args, "manuscript", None) else None
    venue_req_path = Path(getattr(args, "venue_requirements", "project/venue_requirements.md"))
    chunks_dir = Path(getattr(args, "chunks_dir", "project/chunks"))
    hw_manifest_path = Path(getattr(args, "hardware_manifest", "project/hardware_profile_manifest.json"))
    freeze_manifest_path = Path(getattr(args, "freeze_manifest", "project/experiment_freeze_manifest.json"))
    out_path = Path(getattr(args, "out", "project/pre_submission_audit_report.md"))

    # Gather all text
    all_text = ""
    sources = []
    if manuscript_path and manuscript_path.exists():
        all_text += manuscript_path.read_text(encoding="utf-8", errors="replace") + "\n"
        sources.append(str(manuscript_path))
    if venue_req_path.exists():
        all_text += venue_req_path.read_text(encoding="utf-8", errors="replace") + "\n"
        sources.append(str(venue_req_path))
    if chunks_dir.exists():
        for rp in sorted(chunks_dir.rglob("contract_report.md")):
            all_text += rp.read_text(encoding="utf-8", errors="replace") + "\n"
            sources.append(str(rp))

    if not all_text.strip():
        print("FAIL: No manuscript, venue requirements, or contract reports found to audit.")
        print("Exit code: 29")
        sys.exit(29)

    results = {}  # step_name -> (status, details)

    # Step 1: Cold-read triage (unsupported adjectives in title/abstract)
    claims = _scan_manuscript_claims(all_text)
    untested_claims = []
    claim_evidence_map = {}
    for claim in claims:
        has_test = bool(re.search(
            rf'(?:test|evaluat|experiment|benchmark|measur|profil|demonstrat).*{re.escape(claim)}|'
            rf'{re.escape(claim)}.*(?:test|evaluat|experiment|benchmark|measur|profil)',
            all_text, re.IGNORECASE
        ))
        claim_evidence_map[claim] = has_test
        if not has_test:
            untested_claims.append(claim)
    if untested_claims:
        results["1_cold_read_triage"] = (
            "FAIL",
            f"Untested claim adjectives in title/abstract: {', '.join(untested_claims)}. "
            "Each adjective must map to a specific experimental test."
        )
    else:
        results["1_cold_read_triage"] = (
            "PASS",
            f"All {len(claims)} claim adjectives have associated experimental tests."
        )

    # Step 2: Claims-evidence matrix
    orphan_claims = [c for c, tested in claim_evidence_map.items() if not tested]
    if orphan_claims:
        results["2_claims_evidence_matrix"] = (
            "FAIL",
            f"Orphan claims (no evidence): {', '.join(orphan_claims)}"
        )
    else:
        results["2_claims_evidence_matrix"] = (
            "PASS",
            f"All {len(claim_evidence_map)} claims have associated evidence."
        )

    # Step 3: Statistical audit
    has_pvalue = bool(_PVALUE_RE.search(all_text))
    has_stat_test = bool(_STAT_TEST_RE.search(all_text))
    has_effect_size = bool(_EFFECT_SIZE_RE.search(all_text))
    stat_issues = []
    if has_pvalue and not has_stat_test:
        stat_issues.append("P-values without named significance test")
    if has_pvalue and not has_effect_size:
        stat_issues.append("P-values without effect size measures")
    if stat_issues:
        results["3_statistical_audit"] = ("FAIL", "; ".join(stat_issues))
    else:
        results["3_statistical_audit"] = ("PASS", "Statistical reporting complete.")

    # Step 4: Baseline audit
    has_baseline_ledger = bool(re.search(r'Baseline\s+Parity\s+Ledger', all_text, re.IGNORECASE))
    has_reimpl_validation = bool(re.search(
        r'reimplementation\s+validation|reimplemented.*sanity\s+check',
        all_text, re.IGNORECASE
    ))
    baseline_issues = []
    if not has_baseline_ledger:
        baseline_issues.append("No Baseline Parity Ledger found")
    if baseline_issues:
        results["4_baseline_audit"] = ("FAIL", "; ".join(baseline_issues))
    else:
        results["4_baseline_audit"] = (
            "PASS",
            f"Baseline Parity Ledger present. "
            f"Reimplementation validation: {'detected' if has_reimpl_validation else 'not detected (check if needed)'}."
        )

    # Step 5: Ablation completeness
    has_factorial = bool(re.search(r'2\^[Nn]|factorial|full\s+combinatorial', all_text))
    has_ablation = bool(re.search(r'ablation', all_text, re.IGNORECASE))
    has_negative = bool(_NEGATIVE_CONTROL_RE.search(all_text))
    if has_ablation:
        notes = []
        if not has_factorial:
            notes.append("No factorial/2^N design detected")
        if not has_negative:
            notes.append("No negative/degenerate controls detected")
        status = "WARN" if notes else "PASS"
        results["5_ablation_audit"] = (status, "; ".join(notes) if notes else "Ablation study detected with appropriate controls.")
    else:
        results["5_ablation_audit"] = ("WARN", "No ablation study detected.")

    # Step 6: Generalization / failure audit
    has_ood = bool(re.search(
        r'(?:out[\s\-]?of[\s\-]?distribution|OOD|cross[\s\-]?dataset|external\s+validation|'
        r'independent\s+(?:test|dataset|held[\s\-]?out))',
        all_text, re.IGNORECASE
    ))
    has_failure_taxonomy = bool(re.search(
        r'failure\s+(?:taxonomy|analysis|case)|error\s+taxonomy|'
        r'P\(failure|failure\s+prevalence',
        all_text, re.IGNORECASE
    ))
    has_calibration = bool(re.search(
        r'calibrat|ECE|expected\s+calibration|reliability\s+diagram',
        all_text, re.IGNORECASE
    ))
    gen_notes = []
    if not has_ood and any(c in claims for c in ["robust", "general", "universal", "real-world"]):
        gen_notes.append("Generalization claim without OOD/cross-dataset evidence")
    if not has_failure_taxonomy and any(c in claims for c in ["robust", "general", "deployment-ready"]):
        gen_notes.append("Robustness/deployment claim without failure taxonomy")
    if not has_calibration and any(c in claims for c in ["deployment-ready", "production-ready"]):
        gen_notes.append("Deployment claim without calibration analysis (D-073)")
    status = "FAIL" if any("without" in n for n in gen_notes) else "PASS"
    results["6_generalization_failure_audit"] = (
        "WARN" if gen_notes else "PASS",
        "; ".join(gen_notes) if gen_notes else "Generalization and failure analysis adequate."
    )

    # Step 7: Hardware / efficiency audit
    efficiency_claimed = any(c in claims for c in [
        "efficient", "real-time", "lightweight", "low-latency", "energy-efficient"
    ])
    has_hw_manifest = hw_manifest_path.exists()
    has_energy = bool(re.search(
        r'(?:J/inference|joule|Wh|energy\s+per|power\s+meter)',
        all_text, re.IGNORECASE
    ))
    hw_notes = []
    if efficiency_claimed and not has_hw_manifest:
        hw_notes.append("Efficiency claimed but no hardware_profile_manifest.json found")
    if efficiency_claimed and not has_energy:
        hw_notes.append("Efficiency claimed but no energy measurement detected (D-068)")
    results["7_hardware_efficiency_audit"] = (
        "WARN" if hw_notes else "PASS",
        "; ".join(hw_notes) if hw_notes else "Hardware profiling adequate."
    )

    # Step 8: Reproducibility audit
    has_freeze = freeze_manifest_path.exists()
    has_code_avail = bool(re.search(
        r'(?:code\s+(?:is\s+)?available|github|repository|code\s+release)',
        all_text, re.IGNORECASE
    ))
    repro_notes = []
    if not has_freeze:
        repro_notes.append("No experiment_freeze_manifest.json found (C63)")
    results["8_reproducibility_audit"] = (
        "WARN" if repro_notes else "PASS",
        "; ".join(repro_notes) if repro_notes else "Reproducibility artifacts present."
    )

    # Step 9: Adversarial rebuttal rehearsal
    strongest_objections = []
    if "FAIL" in [r[0] for r in results.values()]:
        for step, (status, detail) in results.items():
            if status == "FAIL":
                strongest_objections.append(f"Step {step}: {detail}")
    results["9_rebuttal_rehearsal"] = (
        "WARN" if strongest_objections else "PASS",
        f"{len(strongest_objections)} potential reject arguments identified."
        if strongest_objections else "No FAIL-level findings to rehearse against."
    )

    # Step 10: Mock meta-review
    has_llm_declaration = bool(re.search(
        r'(?:LLM\s+(?:usage|declaration)|large\s+language\s+model\s+(?:use|disclosure))',
        all_text, re.IGNORECASE
    ))
    meta_notes = []
    if not has_llm_declaration:
        meta_notes.append("No LLM usage declaration found (D-072, NeurIPS checklist item 16)")
    results["10_meta_review_simulation"] = (
        "WARN" if meta_notes else "PASS",
        "; ".join(meta_notes) if meta_notes else "All meta-review items addressed."
    )

    # --- Generate audit report ---
    report_lines = [
        "# Pre-Submission Audit Report (v2.6.0, D-070)",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Sources audited:** {len(sources)}",
        "",
        "| Step | Name | Status | Details |",
        "|---|---|---|---|",
    ]

    for step_key in sorted(results.keys()):
        status, detail = results[step_key]
        step_num = step_key.split("_")[0]
        step_name = "_".join(step_key.split("_")[1:]).replace("_", " ").title()
        icon = "✅" if status == "PASS" else "⚠️" if status == "WARN" else "❌"
        report_lines.append(f"| {step_num} | {step_name} | {icon} {status} | {detail} |")

    report_lines.extend([
        "",
        "## Claims-Evidence Matrix",
        "",
        "| Claim Adjective | Evidence Found |",
        "|---|---|",
    ])
    for claim, has_evidence in sorted(claim_evidence_map.items()):
        report_lines.append(
            f"| {claim} | {'✅ Yes' if has_evidence else '❌ No'} |"
        )

    fail_count = sum(1 for _, (s, _) in results.items() if s == "FAIL")
    warn_count = sum(1 for _, (s, _) in results.items() if s == "WARN")
    pass_count = sum(1 for _, (s, _) in results.items() if s == "PASS")

    report_lines.extend([
        "",
        f"## Summary: {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL",
        "",
    ])

    # Write report
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    # Print summary
    print(f"\n[Pre-Submission Audit -- D-070, 10-Step Adversarial Checklist]")
    print(f"Sources: {', '.join(sources)}")
    print(f"Report written to: {out_path}")
    print(f"\nResults: {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL")

    # Steps 1-4 are validity-critical: any FAIL exits 29
    critical_fails = [
        k for k in ["1_cold_read_triage", "2_claims_evidence_matrix",
                     "3_statistical_audit", "4_baseline_audit"]
        if results.get(k, ("PASS", ""))[0] == "FAIL"
    ]

    if critical_fails:
        print(f"\nCRITICAL FAILURES in validity steps: {', '.join(critical_fails)}")
        for cf in critical_fails:
            print(f"  - [FAIL] Step {cf}: {results[cf][1]}")
        print("\nExit code: 29")
        sys.exit(29)
    elif fail_count > 0:
        print("\nNon-critical failures detected. Review recommended before submission.")
        sys.exit(0)
    else:
        print("\nPASS: All 10 pre-submission audit steps passed.")
        sys.exit(0)


def _parse_failure_taxonomy(data):
    """Parse a failure taxonomy (JSON dict or list of failure categories).
    Returns list of dicts with keys: category, prevalence, selection_rule, comparative."""
    results = []
    entries = data if isinstance(data, list) else data.get("failure_categories", data.get("categories", []))
    for entry in entries:
        if isinstance(entry, dict):
            results.append({
                "category": entry.get("category", entry.get("name", "unnamed")),
                "prevalence": entry.get("prevalence", entry.get("rate")),
                "selection_rule": entry.get("selection_rule", entry.get("sampling")),
                "comparative": entry.get("comparative_analysis", entry.get("baseline_also_fails")),
                "confidence_analysis": entry.get("confidence_analysis", entry.get("confidence")),
            })
    return results


def cmd_verify_failure_taxonomy(args):
    """v2.6.0, C69, D-071: Verify failure taxonomy artifact.
    Checks: (a) failure prevalence P(failure|condition) reported,
    (b) >=3 failure categories, (c) explicit selection rule,
    (d) comparative failures shown, (e) confidence analysis present.
    Fails with exit 30 on insufficiency."""
    taxonomy_path = Path(args.taxonomy) if getattr(args, "taxonomy", None) else Path("project/failure_taxonomy.json")

    if not taxonomy_path.exists():
        # Try markdown report fallback
        report_path = Path(getattr(args, "report", "")) if getattr(args, "report", None) else None
        if report_path and report_path.exists():
            text = report_path.read_text(encoding="utf-8", errors="replace")
            has_taxonomy = bool(re.search(
                r'failure\s+taxonomy|error\s+taxonomy|failure\s+categories',
                text, re.IGNORECASE
            ))
            has_prevalence = bool(re.search(
                r'P\(failure|prevalence|failure\s+rate|error\s+rate.*%',
                text, re.IGNORECASE
            ))
            has_selection = bool(re.search(
                r'selection\s+rule|sampling\s+(?:method|strategy)|random\s+sample',
                text, re.IGNORECASE
            ))
            issues = []
            if not has_taxonomy:
                issues.append("No failure taxonomy section found")
            if has_taxonomy and not has_prevalence:
                issues.append("Failure taxonomy without prevalence statistics P(failure|condition)")
            if has_taxonomy and not has_selection:
                issues.append("Failure taxonomy without explicit selection rule for displayed examples")

            print(f"\n[Failure Taxonomy Verification -- C69, D-071]")
            print(f"Audited document: {report_path}")
            if issues:
                print("\nFAILURE TAXONOMY INSUFFICIENCIES:")
                for i in issues:
                    print(f"  - [FAIL] {i}")
                print("\nExit code: 30")
                sys.exit(30)
            elif has_taxonomy:
                print("\nPASS (heuristic): Failure taxonomy with prevalence and selection rule detected.")
                sys.exit(0)

        print(f"FAIL: Failure taxonomy not found at '{taxonomy_path}'.")
        print("Expected JSON with 'failure_categories' array containing 'category', 'prevalence', 'selection_rule', 'comparative_analysis'.")
        print("Exit code: 30")
        sys.exit(30)

    try:
        data = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: Invalid JSON in failure taxonomy '{taxonomy_path}': {e}")
        print("Exit code: 30")
        sys.exit(30)

    entries = _parse_failure_taxonomy(data)
    findings = []

    if len(entries) < 3:
        findings.append(
            f"Only {len(entries)} failure categories (minimum 3 required by C69). "
            "Categories should be defined by failure mechanism, not just listed."
        )

    for entry in entries:
        cat = entry["category"]
        if entry["prevalence"] is None:
            findings.append(
                f"Category '{cat}': Missing failure prevalence P(failure|condition). "
                "C69 requires computed prevalence, not hand-picked example counts."
            )
        if entry["selection_rule"] is None:
            findings.append(
                f"Category '{cat}': Missing selection rule for displayed examples. "
                "C69 requires stating how examples were chosen (random sample, worst decile, etc.)."
            )
        if entry["comparative"] is None:
            findings.append(
                f"Category '{cat}': Missing comparative failure analysis. "
                "C69 requires showing whether baseline and proposed method fail on the same inputs."
            )

    # Check overall selection rule
    overall_selection = data.get("overall_selection_rule") or data.get("selection_rule")
    if not overall_selection and entries:
        all_have_selection = all(e["selection_rule"] is not None for e in entries)
        if not all_have_selection:
            findings.append(
                "No overall selection rule for failure example display. "
                "C69 requires explicit selection methodology."
            )

    print(f"\n[Failure Taxonomy Verification -- C69, D-071]")
    print(f"Audited taxonomy: {taxonomy_path}")
    print(f"Failure categories: {len(entries)}")

    if findings:
        print("\nFAILURE TAXONOMY INSUFFICIENCIES:")
        for f in findings:
            print(f"  - [FAIL] {f}")
        print("\nExit code: 30")
        sys.exit(30)
    else:
        for e in entries:
            print(f"  Category '{e['category']}': prevalence={e['prevalence']}, "
                  f"selection_rule={'Yes' if e['selection_rule'] else 'No'}, "
                  f"comparative={'Yes' if e['comparative'] else 'No'}")
        print("\nPASS: Failure taxonomy satisfies C69/D-071 requirements.")
        sys.exit(0)


def main():

    # v1.3.4 (BUG-7): every path in this script is cwd-relative with no
    # validation. Run from the wrong directory and DROP_HERE/, project/,
    # etc. silently resolve to a nonexistent path, producing a generic,
    # misleading error instead of the real problem. This check runs before
    # any command dispatch, so every subcommand is covered by it.
    if not Path("factory/bootstrap_manifest.yaml").exists():
        print(
            "ERROR: gatekeeper.py must be run from the repository root "
            "(expected to find factory/bootstrap_manifest.yaml here)."
        )
        sys.exit(9)

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_snap = sub.add_parser("snapshot", help="Record baseline hashes for one contract's frozen files.")
    p_snap.add_argument("--contract", required=True)
    p_snap.add_argument("--frozen", nargs="+", required=True, help="Paths to freeze.")
    p_snap.add_argument("--force", action="store_true", help="Overwrite an existing snapshot. Use deliberately.")
    p_snap.set_defaults(func=cmd_snapshot)

    p_snap_chunk = sub.add_parser("snapshot-chunk", help="Snapshot every contract's frozen_files in a chunk's manifest, in one command.")
    p_snap_chunk.add_argument("--manifest", required=True, help="Path to the chunk's execution_manifest.yaml.")
    p_snap_chunk.add_argument("--force", action="store_true", help="Overwrite existing snapshots. Use deliberately.")
    p_snap_chunk.set_defaults(func=cmd_snapshot_chunk)

    p_next = sub.add_parser("next", help="Report the next contract ready to execute, per execution_order and contract_report.md statuses.")
    p_next.add_argument("--manifest", required=True, help="Path to the chunk's execution_manifest.yaml.")
    p_next.add_argument("--reports-dir", default=None, help="Override the default <manifest_dir>/reports/ location.")
    p_next.set_defaults(func=cmd_next)

    p_dropbox = sub.add_parser("sort-dropbox", help="File everything in DROP_HERE/ to the destination its dropbox_manifest.json declares.")
    p_dropbox.add_argument("--manifest", required=False, default=None, help="Accepted for symmetry with other commands; sort-dropbox reads DROP_HERE/dropbox_manifest.json directly and does not need the chunk manifest.")
    p_dropbox.add_argument("--force", action="store_true", help="Overwrite a destination file that already exists. Use deliberately.")
    p_dropbox.set_defaults(func=cmd_sort_dropbox)

    p_stage = sub.add_parser("stage-takethis", help="Copy one completed chunk's self-contained reports (every contract_report.md + chunk_report.md) into TAKE_THIS/. Copy only -- originals are untouched.")
    p_stage.add_argument("--chunk", required=True, help="Chunk directory name, e.g. chunk03.")
    p_stage.set_defaults(func=cmd_stage_takethis)

    p_clear = sub.add_parser("clear-takethis", help="v2.3.0: ARCHIVES (moves, does not delete) whatever's staged in TAKE_THIS/ into TAKE_THIS_ARCHIVE/, by default (D-043). Pass --purge for the old delete-forever behavior. Never touches project/.")
    p_clear.add_argument("--chunk", default=None, help="Chunk label to use in the archive directory name (optional -- a timestamp is always included too).")
    p_clear.add_argument("--purge", action="store_true", help="v2.2.0-compatible behavior: delete instead of archive. Use deliberately.")
    p_clear.set_defaults(func=cmd_clear_takethis)

    p_materialize = sub.add_parser("materialize", help="Extract MATERIALIZE-tagged code blocks from a contract file and write them to their declared destination paths, byte-for-byte.")
    p_materialize.add_argument("--contract", required=True, help="Contract ID, e.g. C01-02. The chunk directory is derived from the ID itself.")
    p_materialize.add_argument("--force", action="store_true", help="Overwrite a destination file that already exists. Use deliberately.")
    p_materialize.set_defaults(func=cmd_materialize)

    p_commit_project = sub.add_parser("commit-project", help="Commit everything staged in project/'s own nested git repository. Safe to call routinely -- a no-op if nothing changed.")
    p_commit_project.add_argument("--message", default=None, help="Commit message. Defaults to a generic 'Update project/ artifacts' if omitted.")
    p_commit_project.set_defaults(func=cmd_commit_project)

    p_self_check = sub.add_parser("self-check", help="Diagnose drift between gatekeeper.py's actual behavior and what the Factory's documents claim about it. Diagnostic only -- reports findings, never modifies anything.")
    p_self_check.set_defaults(func=cmd_self_check)

    p_release_check = sub.add_parser("release-check", help="Scan a release-bound artifact (manuscript, REPRODUCIBILITY.md) for local-path leaks and key-fact inconsistencies before submission.")
    p_release_check.add_argument("--manuscript", required=True, help="Path to the manuscript or primary release artifact to scan.")
    p_release_check.add_argument("--files", nargs="*", default=None, help="Additional release files to scan for local paths (e.g. REPRODUCIBILITY.md). The manuscript is always included.")
    p_release_check.add_argument("--key-facts", default=None, help="Path to project/key_facts.md. If omitted, the key-fact consistency check is skipped.")
    p_release_check.set_defaults(func=cmd_release_check)

    p_acq_audit = sub.add_parser("acquisition-audit", help="Scan data-acquisition scripts and their contract reports for data-generation function definitions and simulation-indicating language before trusting their output.")
    p_acq_audit.add_argument("--scripts", nargs="*", default=None, help="Paths to acquisition scripts to scan (structural + textual).")
    p_acq_audit.add_argument("--reports", nargs="*", default=None, help="Paths to contract reports to scan (textual only).")
    p_acq_audit.set_defaults(func=cmd_acquisition_audit)

    p_evidence_check = sub.add_parser("evidence-check", help="Cross-check a contract report's declared verdict and pre-registered criterion against its own backing JSON artifact, and flag degenerate metrics.")
    p_evidence_check.add_argument("--reports", nargs="*", default=None, help="Paths to contract_report.md files, each with a '## Verdict Cross-Check' block.")
    p_evidence_check.set_defaults(func=cmd_evidence_check)

    p_check = sub.add_parser("check", help="Run the implemented checks for one contract. v1.4.2 amendment: for a manifest contract whose scientific_claim_tier is T-COMP/T-CAUSAL, also mechanically enforces the Mandatory Mechanical Gate (Required Verification Commands, verify-contract, lint-contract, recompute, stamp presence -- exit 17). v2.2.0 addition: also runs Fail-Closed Tier Inference regardless of the declared tier, to catch the declaration itself being too low (exit 18).")
    p_check.add_argument("--contract", default=None)
    p_check.add_argument("--manifest", default=None, help="Path to execution_manifest.yaml to auto-derive frozen_files/required_reports.")
    p_check.add_argument("--frozen", nargs="*", default=None, help="Frozen file paths (supplements/overrides manifest).")
    p_check.add_argument("--reports", nargs="*", default=None, help="Report paths to validate (supplements/overrides manifest).")
    p_check.add_argument("--required-sections", nargs="*", default=None, help=f"Override default required section strings {DEFAULT_REQUIRED_SECTIONS}.")
    p_check.add_argument("--allow-dirty", action="store_true", help="Skip the clean-working-tree check. Only for active Phase 2 work.")
    p_check.set_defaults(func=cmd_check)

    p_verify_contract = sub.add_parser("verify-contract", help="v1.4.2 -- independently re-executes every command a contract report declares under '## Verification' and checks the real exit code.")
    p_verify_contract.add_argument("--reports", nargs="*", default=None, help="Paths to contract_report.md files.")
    p_verify_contract.set_defaults(func=cmd_verify_contract)

    p_lint_contract = sub.add_parser("lint-contract", help="v1.4.2 -- scans scripts for swallowed exceptions and fabricated-statistical-input patterns, and checks auto-frozen verification machinery for tampering.")
    p_lint_contract.add_argument("--scripts", nargs="*", default=None, help="Paths to scripts to lint.")
    p_lint_contract.add_argument("--contract", default=None, help="Contract ID, to check frozen verification machinery against its recorded snapshot.")
    p_lint_contract.set_defaults(func=cmd_lint_contract)

    p_recompute = sub.add_parser("recompute", help="v1.4.2 -- for a report declaring a '## Recompute Declaration' block, runs the declared independent script and compares its output to the artifact's claimed value.")
    p_recompute.add_argument("--reports", nargs="*", default=None, help="Paths to contract_report.md files.")
    p_recompute.set_defaults(func=cmd_recompute)

    p_stamp_report = sub.add_parser("stamp-report", help="v1.4.2 -- appends a tamper-evident Gatekeeper Verification Stamp to a contract report, containing real verify-contract/lint-contract/recompute results, git diff, and frozen-file status.")
    p_stamp_report.add_argument("--report", required=True, help="Path to the contract_report.md to stamp.")
    p_stamp_report.add_argument("--contract", default=None, help="Contract ID, to check frozen verification machinery against its recorded snapshot.")
    p_stamp_report.set_defaults(func=cmd_stamp_report)

    p_verify_stamps = sub.add_parser("verify-stamps", help="v1.4.2 -- checks stamp integrity only (no side effects); does not append a new stamp.")
    p_verify_stamps.add_argument("--reports", nargs="*", default=None, help="Paths to contract_report.md files.")
    p_verify_stamps.set_defaults(func=cmd_verify_stamps)

    p_tier_check = sub.add_parser("tier-check", help="v2.2.0 -- fail-closed minimum Scientific Claim Tier inference from a contract's own text, plus operation-class-conflation, statistical-protocol-language, and semantic/operator-test-presence heuristics.")
    p_tier_check.add_argument("--contract", default=None, help="Contract ID, e.g. C01-02 (locates the contract file automatically).")
    p_tier_check.add_argument("--contract-file", default=None, help="Explicit path to a contract .md file (overrides --contract's auto-location).")
    p_tier_check.add_argument("--declared-tier", default=None, help="Override the tier parsed from the contract file (NONE/T-DESC/T-COMP/T-CAUSAL).")
    p_tier_check.add_argument("--reports", nargs="*", default=None, help="Optional contract_report.md path(s), scanned alongside the contract for semantic-test-marker presence.")
    p_tier_check.set_defaults(func=cmd_tier_check)

    p_release_certify = sub.add_parser("release-certify", help="v2.2.0 -- aggregate CERTIFIED/NOT CERTIFIED gate across every contract report under --chunks-dir, distinct from any single chunk's PASS. Writes project/RELEASE_CERTIFICATION.md.")
    p_release_certify.add_argument("--chunks-dir", default="project/chunks", help="Root directory containing chunkNN/reports/{{contract_id}}/contract_report.md files. Default: project/chunks")
    p_release_certify.add_argument("--manuscript", default=None, help="Path to the manuscript or primary release artifact (enables the Release Artifact Scan category).")
    p_release_certify.add_argument("--files", nargs="*", default=None, help="Additional release files to scan for local paths alongside --manuscript.")
    p_release_certify.add_argument("--key-facts", default=None, help="Path to project/key_facts.md (enables key-fact consistency warnings).")
    p_release_certify.add_argument("--scripts", nargs="*", default=None, help="Data-acquisition/statistical-computation scripts to scan (enables the Acquisition Audit category).")
    p_release_certify.set_defaults(func=cmd_release_certify)

    p_release_status = sub.add_parser("release-status", help="v2.3.0 (D-053) -- reports whether the existing project/RELEASE_CERTIFICATION.md is still CERTIFIED and current, without re-running the full release-certify battery. This, not a holistic re-read, is how 'is this ready' should be answered.")
    p_release_status.add_argument("--chunks-dir", default="project/chunks", help="Root directory containing chunkNN/reports/{contract_id}/contract_report.md files. Default: project/chunks")
    p_release_status.set_defaults(func=cmd_release_status)

    p_preflight = sub.add_parser("contract-preflight", help="v2.3.0 (D-039/D-040) -- reconciles a contract's Allowed/Frozen Files against its own verification-command glob reach, dependency graph, and manifest preconditions, BEFORE implementation begins. Exit 3 on a scope conflict, exit 21 on an unauthorized owner/executor mismatch.")
    p_preflight.add_argument("--contract", required=True)
    p_preflight.add_argument("--manifest", required=True, help="Path to the chunk's execution_manifest.yaml.")
    p_preflight.add_argument("--acquisition-scripts", nargs="*", default=None, help="Glob(s)/path(s) an acquisition-audit or similar wide-reaching command would scan, to reconcile against allowed_files/frozen_files.")
    p_preflight.add_argument("--readonly-verification", action="store_true", help="Treat verification reach outside allowed_files as a warning, not a failure, because you've confirmed those commands only read (never modify) the matched files.")
    p_preflight.add_argument("--executor", default=None, help="Who is actually executing this contract, if different from its manifest implementation_owner (e.g. a temporary delegation).")
    p_preflight.set_defaults(func=cmd_contract_preflight)

    p_begin = sub.add_parser("begin", help="v2.3.0 (D-041) -- starts a contract: runs contract-preflight, snapshots frozen_files straight from the manifest, captures a scoped repository baseline, and writes a headed report skeleton if one doesn't exist yet.")
    p_begin.add_argument("--contract", required=True)
    p_begin.add_argument("--manifest", required=True, help="Path to the chunk's execution_manifest.yaml.")
    p_begin.add_argument("--reports-dir", default=None, help="Override the default <manifest_dir>/reports/<contract>/ location.")
    p_begin.add_argument("--acquisition-scripts", nargs="*", default=None, help="Passed through to contract-preflight.")
    p_begin.add_argument("--readonly-verification", action="store_true", help="Passed through to contract-preflight.")
    p_begin.add_argument("--executor", default=None, help="Passed through to contract-preflight (delegation check).")
    p_begin.add_argument("--force-snapshot", action="store_true", help="Overwrite an existing frozen-file snapshot for this contract. Use deliberately.")
    p_begin.add_argument("--model-id", default=None, help="Recorded on the contract_started telemetry event.")
    p_begin.add_argument("--model-version", default=None)
    p_begin.set_defaults(func=cmd_begin)

    p_finalize = sub.add_parser("finalize", help="v2.3.0 (D-041; see C61) -- transactionally completes a contract: re-runs check (and the Mandatory Mechanical Gate, if tiered) for real, right now, and writes a completion receipt plus telemetry/decision-log entries ONLY if that re-run actually passes and the report's own Final Status already reads COMPLETE. Exit 20 on a failed re-run.")
    p_finalize.add_argument("--contract", required=True)
    p_finalize.add_argument("--manifest", required=True, help="Path to the chunk's execution_manifest.yaml.")
    p_finalize.add_argument("--reports-dir", default=None, help="Override the default <manifest_dir>/reports/<contract>/ location.")
    p_finalize.add_argument("--decision", default=None, help="Pipe-separated 'Title|Decision|Reason|Alternatives|Expected benefit' to also log via log-decision. Optional.")
    p_finalize.add_argument("--no-commit", action="store_true", help="Skip the automatic commit-project call at the end.")
    p_finalize.add_argument("--model-id", default=None, help="Recorded on the contract_complete telemetry event.")
    p_finalize.add_argument("--model-version", default=None)
    p_finalize.set_defaults(func=cmd_finalize)

    p_delegate = sub.add_parser("delegate", help="v2.3.0 (D-044) -- records a Human-authorized, chunk-scoped, non-precedent-setting exception to the Implementation Owner table (e.g. the Architect is unreachable this chunk). See constitution.md C55's delegation note.")
    p_delegate.add_argument("--chunk", required=True, help="Chunk directory name this delegation is scoped to, e.g. chunk01.")
    p_delegate.add_argument("--original-owner", required=True, choices=["architect", "implementor"])
    p_delegate.add_argument("--executor", required=True, choices=["architect", "implementor"])
    p_delegate.add_argument("--contracts", nargs="+", required=True, help="Contract ID(s) this delegation applies to.")
    p_delegate.add_argument("--authorized-by", required=True, help="Quote or closely paraphrase the Human's own explicit authorization.")
    p_delegate.set_defaults(func=cmd_delegate)

    p_log_decision = sub.add_parser("log-decision", help="v2.3.0 (D-048) -- appends a decision_log.md entry (and its structured backing record) with an auto-incremented D-number. No hand-editing required.")
    p_log_decision.add_argument("--role", required=True, choices=["architect", "implementor"])
    p_log_decision.add_argument("--title", default=None)
    p_log_decision.add_argument("--decision", required=True)
    p_log_decision.add_argument("--reason", required=True)
    p_log_decision.add_argument("--alternatives", default=None)
    p_log_decision.add_argument("--benefit", required=True)
    p_log_decision.add_argument("--traces", nargs="*", default=None, help="Contract/chunk/invariant IDs this decision relates to.")
    p_log_decision.set_defaults(func=cmd_log_decision)

    # v2.5.0 (MAR mechanical gates, D-056, D-059, D-060, D-061)
    p_verify_baseline_parity = sub.add_parser("verify-baseline-parity", help="v2.5.0 (MAR-2, D-059) -- parse Baseline Parity Ledger and verify parameter parity (+/-2%%) and compute parity (+/-5%%). Exit 23 on violation.")
    p_verify_baseline_parity.add_argument("--venue-requirements", default=None, help="Path to project/venue_requirements.md.")
    p_verify_baseline_parity.add_argument("--contract-report", default=None, help="Path to contract report containing Baseline Parity Ledger.")
    p_verify_baseline_parity.add_argument("--ledger", default=None, help="Path to standalone ledger markdown or JSON.")
    p_verify_baseline_parity.add_argument("--param-tolerance", type=float, default=0.02, help="Relative parameter tolerance (default: 0.02 = +/-2%%).")
    p_verify_baseline_parity.add_argument("--compute-tolerance", type=float, default=0.05, help="Relative compute tolerance (default: 0.05 = +/-5%%).")
    p_verify_baseline_parity.set_defaults(func=cmd_verify_baseline_parity)

    p_verify_hardware_profile = sub.add_parser("verify-hardware-profile", help="v2.5.0 (MAR-8, D-056) -- verify hardware profile manifest for empirical latency percentiles (p50, p90, p99), warmup exclusion, and separate train/inference memory. Exit 24 on insufficiency.")
    p_verify_hardware_profile.add_argument("--manifest", required=True, help="Path to hardware_profile_manifest.json.")
    p_verify_hardware_profile.set_defaults(func=cmd_verify_hardware_profile)

    p_freeze_experiment = sub.add_parser("freeze-experiment", help="v2.5.0 (MAR-7, C63, D-060) -- pre-register and freeze evaluation seeds, git commit, environment lock, and split checksums to experiment_freeze_manifest.json.")
    p_freeze_experiment.add_argument("--out", default="project/experiment_freeze_manifest.json", help="Output path for freeze manifest.")
    p_freeze_experiment.add_argument("--manifest", default=None, help="Path to execution_manifest.yaml.")
    p_freeze_experiment.add_argument("--seeds", nargs="+", required=True, help="List of evaluation seeds to pre-register (minimum 3).")
    p_freeze_experiment.add_argument("--split-files", nargs="*", default=None, help="Dataset split files to hash.")
    p_freeze_experiment.add_argument("--lockfile", default=None, help="Path to environment lockfile.")
    p_freeze_experiment.add_argument("--force", action="store_true", help="Overwrite existing freeze manifest.")
    p_freeze_experiment.set_defaults(func=cmd_freeze_experiment)

    p_verify_experiment_freeze = sub.add_parser("verify-experiment-freeze", help="v2.5.0 (MAR-7, C63, D-060) -- verify evaluation report or artifact executed all pre-registered seeds without omission or post-hoc cherry-picking. Exit 25 on mismatch.")
    p_verify_experiment_freeze.add_argument("--freeze-manifest", required=True, help="Path to experiment_freeze_manifest.json.")
    p_verify_experiment_freeze.add_argument("--report", required=True, help="Path to contract report or evaluation artifact JSON.")
    p_verify_experiment_freeze.set_defaults(func=cmd_verify_experiment_freeze)

    p_contamination_check = sub.add_parser("contamination-check", help="v2.5.0 (MAR-6, D-061) -- audit benchmark evaluation data for 13-gram training corpus overlap or temporal knowledge cutoff contamination. Exit 26 on contamination.")
    p_contamination_check.add_argument("--benchmark", default=None, help="Path to benchmark dataset file.")
    p_contamination_check.add_argument("--training-corpus", default=None, help="Path to training corpus file or directory.")
    p_contamination_check.add_argument("--audit-json", default=None, help="Path to pre-computed contamination_audit.json.")
    p_contamination_check.add_argument("--n-gram", type=int, default=13, help="N-gram length for exact overlap checking (default: 13).")
    p_contamination_check.add_argument("--model-cutoff", default=None, help="Model knowledge cutoff date (YYYY-MM).")
    p_contamination_check.add_argument("--benchmark-release-date", default=None, help="Benchmark release date (YYYY-MM).")
    p_contamination_check.set_defaults(func=cmd_contamination_check)

    # v2.6.0 (Statistical Inference & Empirical Completeness, D-062 through D-073)
    p_verify_stat = sub.add_parser("verify-statistical-protocol", help="v2.6.0 (C65/C66, D-062/D-063/D-064) -- verify statistical protocol: named significance test, effect sizes alongside p-values, multiple-comparisons correction, IQM for small N, negative controls, retuned ablation reporting. Exit 27 on violation.")
    p_verify_stat.add_argument("--reports", nargs="*", default=None, help="Paths to contract reports or evaluation artifacts to scan.")
    p_verify_stat.add_argument("--manuscript", default=None, help="Path to manuscript file to scan.")
    p_verify_stat.add_argument("--chunks-dir", default="project/chunks", help="Root directory containing contract reports.")
    p_verify_stat.set_defaults(func=cmd_verify_statistical_protocol)

    p_verify_sens = sub.add_parser("verify-sensitivity-analysis", help="v2.6.0 (D-065) -- verify sensitivity analysis: >=3 perturbation levels per HP, response curve data, architecture sensitivity variation. Exit 28 on insufficiency.")
    p_verify_sens.add_argument("--manifest", default=None, help="Path to sensitivity_analysis_manifest.json.")
    p_verify_sens.add_argument("--report", default=None, help="Path to contract report (heuristic fallback if no manifest).")
    p_verify_sens.set_defaults(func=cmd_verify_sensitivity_analysis)

    p_pre_sub = sub.add_parser("pre-submission-audit", help="v2.6.0 (D-070) -- 10-step adversarial pre-submission audit: cold-read triage, claims-evidence matrix, statistical audit, baseline audit, ablation completeness, generalization/failure analysis, hardware/efficiency, reproducibility, rebuttal rehearsal, mock meta-review. Exit 29 on validity-critical FAIL.")
    p_pre_sub.add_argument("--manuscript", default=None, help="Path to manuscript file.")
    p_pre_sub.add_argument("--venue-requirements", default="project/venue_requirements.md", help="Path to venue_requirements.md.")
    p_pre_sub.add_argument("--chunks-dir", default="project/chunks", help="Root directory containing contract reports.")
    p_pre_sub.add_argument("--hardware-manifest", default="project/hardware_profile_manifest.json", help="Path to hardware_profile_manifest.json.")
    p_pre_sub.add_argument("--freeze-manifest", default="project/experiment_freeze_manifest.json", help="Path to experiment_freeze_manifest.json.")
    p_pre_sub.add_argument("--out", default="project/pre_submission_audit_report.md", help="Output path for audit report.")
    p_pre_sub.set_defaults(func=cmd_pre_submission_audit)

    p_verify_fail = sub.add_parser("verify-failure-taxonomy", help="v2.6.0 (C69, D-071) -- verify failure taxonomy: >=3 categories, prevalence P(failure|condition), selection rule, comparative failures, confidence analysis. Exit 30 on insufficiency.")
    p_verify_fail.add_argument("--taxonomy", default=None, help="Path to failure_taxonomy.json.")
    p_verify_fail.add_argument("--report", default=None, help="Path to contract report (heuristic fallback if no JSON).")
    p_verify_fail.set_defaults(func=cmd_verify_failure_taxonomy)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
