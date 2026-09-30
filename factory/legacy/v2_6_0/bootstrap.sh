#!/bin/bash

set -euo pipefail

# ==============================
# Software Factory Bootstrap
# ==============================
#
# v1.1.0 changes from v1.0.1:
#   - Actually reads bootstrap_manifest.yaml (idempotent flag, copy_factory_files
#     list) instead of hardcoding behavior that silently disagreed with it.
#   - Idempotent: checks factory/, project/, source/ individually and fills
#     only what's missing, instead of refusing to run if any already exist.
#   - Copies only the files bootstrap_manifest.yaml's copy_factory_files lists,
#     instead of the entire factory/ directory from the cloned repo.
#   - Rollback on failure only removes what THIS run created, never
#     pre-existing content.
#   - Supports non-interactive use via FACTORY_BOOTSTRAP_YES=1 (e.g. for an
#     agent or CI running this without a TTY).
# See CHANGELOG.md v1.1.0 for why.
#
# v1.1.3 changes:
#   - Creates DROP_HERE/ (gitignored) -- a generic inbox files can be handed
#     to the Implementation Engineer through, sorted deterministically by
#     `gatekeeper.py sort-dropbox`. Idempotent like everything else here:
#     left alone if it already exists.
# See CHANGELOG.md v1.1.3 for why.
#
# v1.1.4 changes (superseded by v1.2.0 below):
#   - No script logic changes. factory/ClaudeInitialization.md added to
#     bootstrap_manifest.yaml's copy_factory_files.
#
# v1.2.0 changes:
#   - factory/gemini_spec.md now copied alongside the other factory files
#     (manifest-driven, [4/8] -- no new logic needed for that part).
#   - DROP_HERE/dropbox_manifest.json is now seeded on first run with the
#     fixed filename->destination rules from factory_spec.md's Dropbox
#     Specification, instead of being left for someone to create by hand.
#     Idempotent: only written if it doesn't already exist, exactly like
#     every other generated file here -- an existing dropbox_manifest.json
#     (with Claude's own project-specific entries already appended into it)
#     is never overwritten by a re-run.
# See CHANGELOG.md v1.2.0 for why.
#
# v1.2.1 changes:
#   - Creates TAKE_THIS/ (gitignored) -- the reverse direction of DROP_HERE/:
#     a place the Implementation Engineer stages a completed chunk's
#     self-contained reports (`gatekeeper.py stage-takethis`) for the Human
#     to grab in one spot, cleared (`gatekeeper.py clear-takethis`) when the
#     next chunk starts. Idempotent like DROP_HERE/: left alone if it
#     already exists.
# See CHANGELOG.md v1.2.1 for why.
#
# v1.3.0 changes:
#   - Auto-detects a non-interactive stdin ([ ! -t 0 ]) and proceeds
#     automatically instead of hanging at the confirmation prompt --
#     surfaced by a real autonomous-agent bootstrap run hanging on
#     `read -r -p` with no TTY to read from. Safe because bootstrap's
#     execution is already idempotent/non-destructive by design; the
#     detection is announced explicitly, never silent. FACTORY_BOOTSTRAP_YES=1
#     still works exactly as before and is the more explicit option.
# See CHANGELOG.md v1.3.0 for why.
#
# v2.2.0 changes:
#   - factory/architect_spec.md and factory/implementor_spec.md are now the
#     primary role-document filenames (manifest-driven, no new script logic
#     needed for the copy itself). factory/ClaudeInitialization.md and
#     factory/gemini_spec.md are still copied too, but now contain only a
#     short pointer to the new filenames -- kept so a re-run against an
#     existing project, or a script/habit still referencing the old names,
#     doesn't hit a missing file.
#   - factory/domain_checklists.md now copied alongside the other factory
#     files (manifest-driven).
#   - factory/tests/test_gatekeeper_v2_2_0.py now copied alongside the other
#     test files (manifest-driven).
# See CHANGELOG.md v2.2.0 for why.

FACTORY_REPO="git@github.com:AdiShrestha/software-factory.git"

# Usage:
# ./bootstrap.sh            -> latest main
# ./bootstrap.sh v1.1.0     -> specific version/tag
# ./bootstrap.sh develop    -> specific branch
# ./bootstrap.sh <commit>   -> specific commit
#
# FACTORY_BOOTSTRAP_YES=1 ./bootstrap.sh   -> skip the interactive confirmation

FACTORY_REF="${1:-main}"

TEMP_DIR=".factory_temp"

FACTORY_DIR="factory"
PROJECT_DIR="project"
SOURCE_DIR="source"
DROPBOX_DIR="DROP_HERE"
TAKETHIS_DIR="TAKE_THIS"

ASSUME_YES="${FACTORY_BOOTSTRAP_YES:-0}"

# v1.3.0 -- an autonomous agent (or CI, or any non-interactive caller)
# running this script with no explicit FACTORY_BOOTSTRAP_YES=1 would
# previously hang forever at the confirmation prompt below, since there's
# no TTY to read a keystroke from. Detect that case and default to
# proceeding automatically -- this is low-risk specifically because
# bootstrap's own execution is already idempotent and non-destructive by
# design (v1.1.0: fills in only what's missing, never overwrites existing
# content, rollback only removes what THIS run created). Still announced
# explicitly below rather than silently assumed, so it's never a surprise
# in the log. An explicit FACTORY_BOOTSTRAP_YES=0 is not supported --
# there is no way to force-require the interactive prompt in a
# non-interactive shell, since there'd be nothing to read from.
if [ "$ASSUME_YES" != "1" ] && [ ! -t 0 ]; then
    ASSUME_YES="1"
    AUTO_DETECTED_NONINTERACTIVE=1
else
    AUTO_DETECTED_NONINTERACTIVE=0
fi

ROLLBACK_NEEDED=0
declare -a CREATED_THIS_RUN=()

cleanup_on_exit() {
    EXIT_CODE=$?

    rm -rf "$TEMP_DIR"

    if [ "$EXIT_CODE" -ne 0 ] && [ "$ROLLBACK_NEEDED" = "1" ]; then
        echo ""
        echo "================================="
        echo " Bootstrap Failed"
        echo " Rolling back only what this run created..."
        echo "================================="
        for created in "${CREATED_THIS_RUN[@]}"; do
            echo "  removing: $created"
            rm -rf "$created"
        done
    fi

    exit "$EXIT_CODE"
}

trap cleanup_on_exit EXIT

echo "================================="
echo " Software Factory Bootstrap"
echo "================================="
echo ""
echo "Factory Repository:"
echo "$FACTORY_REPO"
echo ""
echo "Requested Version:"
echo "$FACTORY_REF"
echo ""

# ==============================
# Idempotent pre-check
# ==============================
# v1.0.1 failed immediately if factory/, project/, or source/ existed at all.
# That contradicted factory_spec.md's Idempotency section outright. Now each
# is checked individually; existing ones are verified/left alone, not
# treated as fatal errors.

EXISTING_ITEMS=()
for d in "$FACTORY_DIR" "$PROJECT_DIR" "$SOURCE_DIR" "$DROPBOX_DIR" "$TAKETHIS_DIR"; do
    if [ -e "$d" ]; then
        EXISTING_ITEMS+=("$d")
    fi
done

if [ -e "$TEMP_DIR" ]; then
    echo "Found stale $TEMP_DIR from an interrupted previous run."
    echo "It is disposable (reconstructed from a fresh clone) — removing it."
    rm -rf "$TEMP_DIR"
fi

if [ ${#EXISTING_ITEMS[@]} -gt 0 ]; then
    echo "Already present in $(pwd) (will be verified, not overwritten):"
    for item in "${EXISTING_ITEMS[@]}"; do
        echo "  - $item"
    done
    echo ""
fi

if [ "$ASSUME_YES" != "1" ]; then
    read -r -p "Bootstrap into $(pwd)? [y/N] " CONFIRM
    if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
        echo "Cancelled."
        exit 0
    fi
elif [ "$AUTO_DETECTED_NONINTERACTIVE" = "1" ]; then
    echo "No TTY on stdin detected — proceeding automatically as a non-interactive run."
    echo "(Set FACTORY_BOOTSTRAP_YES=1 explicitly to silence this message; safe because"
    echo " bootstrap only ever fills in what's missing and never overwrites existing content.)"
else
    echo "FACTORY_BOOTSTRAP_YES=1 set — skipping interactive confirmation."
fi

# ==============================
# Clone Factory
# ==============================

echo ""
echo "[1/8] Cloning Factory..."

git clone \
    "$FACTORY_REPO" \
    "$TEMP_DIR"

echo ""
echo "Checking out:"
echo "$FACTORY_REF"

git -C "$TEMP_DIR" checkout "$FACTORY_REF"

# ==============================
# Validate Factory
# ==============================

echo ""
echo "[2/8] Validating Factory..."

if [ ! -d "$TEMP_DIR/factory" ]; then
    echo "ERROR: Invalid Factory repository."
    echo "Missing factory/ directory."
    exit 1
fi

if [ ! -f "$TEMP_DIR/factory/VERSION" ]; then
    echo "ERROR: Invalid Factory repository."
    echo "Missing factory/VERSION."
    exit 1
fi

if [ ! -f "$TEMP_DIR/factory/bootstrap_manifest.yaml" ]; then
    echo "ERROR: Invalid Factory repository."
    echo "Missing factory/bootstrap_manifest.yaml."
    exit 1
fi

VERSION=$(cat "$TEMP_DIR/factory/VERSION")

COMMIT=$(git -C "$TEMP_DIR" rev-parse HEAD)

SHORT_COMMIT=$(git -C "$TEMP_DIR" rev-parse --short HEAD)

echo "Factory Version : $VERSION"
echo "Factory Commit  : $SHORT_COMMIT"

# ==============================
# Read bootstrap_manifest.yaml
# ==============================
# v1.0.1 never read this file at all despite factory_spec.md's Bootstrap
# Procedure listing "Read bootstrap_manifest.yaml" as step one. This reads
# it from the freshly cloned copy so the manifest, not this script, is the
# actual source of truth for the idempotent flag and the file copy list.

echo ""
echo "[3/8] Reading bootstrap_manifest.yaml..."

MANIFEST="$TEMP_DIR/factory/bootstrap_manifest.yaml"

MANIFEST_IDEMPOTENT=$(grep -E '^[[:space:]]*idempotent:' "$MANIFEST" | awk -F':' '{gsub(/[ \t]/,"",$2); print $2}' | head -1)
echo "Manifest idempotent flag: ${MANIFEST_IDEMPOTENT:-<not found>}"

if [ "$MANIFEST_IDEMPOTENT" != "true" ] && [ ${#EXISTING_ITEMS[@]} -gt 0 ]; then
    echo "ERROR: manifest declares idempotent: ${MANIFEST_IDEMPOTENT:-<missing>}, but the following already exist: ${EXISTING_ITEMS[*]}"
    echo "Refusing to run non-idempotently against a non-empty target."
    echo "Either remove the existing directories, or set idempotent: true in the Factory repo's bootstrap_manifest.yaml."
    exit 1
fi

COPY_FILES=()
while IFS= read -r line; do
    [ -n "$line" ] && COPY_FILES+=("$line")
done < <(awk '
    /^[[:space:]]*copy_factory_files:/ { grab=1; next }
    grab && /^[[:space:]]*-[[:space:]]*/ { sub(/^[[:space:]]*-[[:space:]]*/, ""); print; next }
    grab && /^[[:space:]]*[A-Za-z_]+:/ { grab=0 }
' "$MANIFEST")

if [ ${#COPY_FILES[@]} -eq 0 ]; then
    echo "ERROR: could not parse copy_factory_files from the manifest."
    exit 1
fi

echo "Files to copy per manifest (${#COPY_FILES[@]}):"
for f in "${COPY_FILES[@]}"; do
    echo "  - $f"
done

# ==============================
# Populate factory/ (manifest-driven, not a blanket directory copy)
# ==============================

echo ""
echo "[4/8] Populating factory/..."

if [ ! -d "$FACTORY_DIR" ]; then
    mkdir -p "$FACTORY_DIR"
    CREATED_THIS_RUN+=("$FACTORY_DIR")
    ROLLBACK_NEEDED=1
fi

for rel_path in "${COPY_FILES[@]}"; do
    src="$TEMP_DIR/$rel_path"
    dest="$rel_path"

    if [ ! -f "$src" ]; then
        echo "  WARNING: $rel_path is listed in the manifest but not present in the Factory repo at $FACTORY_REF — skipping."
        continue
    fi

    mkdir -p "$(dirname "$dest")"

    if [ -f "$dest" ]; then
        echo "  already present, left untouched: $dest"
    else
        cp "$src" "$dest"
        echo "  created: $dest"
    fi
done

# ==============================
# Create Project Structure
# ==============================

echo ""
echo "[5/8] Creating Project Structure..."

if [ ! -d "$PROJECT_DIR" ]; then
    CREATED_THIS_RUN+=("$PROJECT_DIR")
    ROLLBACK_NEEDED=1
fi
mkdir -p "$PROJECT_DIR/chunks"

# ==============================
# Nested project/ repository (v1.3.2)
# ==============================
# project/ is gitignored at the outer level by explicit design (see
# CHANGELOG.md v1.3.2) -- the Human wants no visible trace, in the outer
# repository's structure or history, that this project was built via an
# AI orchestration pipeline. But project/'s own contents (chunk plans,
# contracts, reports, decision log) still deserve real git history for
# diffing, audit, and Chunk Review purposes -- the earlier bug this
# replaces was losing that history entirely rather than protecting it.
#
# The fix: project/ is its own independent git repository, nested inside
# the outer one. The outer repo's .gitignore rule for "project/" means
# outer git commands never see into it at all -- not the directory, not
# its .git folder, nothing. Anyone cloning or browsing the outer repo
# normally sees source code only. Full real history still exists, just
# scoped to its own repo instead of erased.
#
# Idempotent: only initialized if project/.git doesn't already exist, so a
# re-run never disturbs an existing project repository or its history.
if [ ! -d "$PROJECT_DIR/.git" ]; then
    (cd "$PROJECT_DIR" && git init -q)
    echo "  initialized nested repository: $PROJECT_DIR/.git (independent of the outer repo, gitignored from it)"
    echo "  note: uses your normal global git identity for commits, same as any other local repo --"
    echo "  deliberately not a distinct 'factory' identity, since that would be a bigger fingerprint"
    echo "  than the directory itself if this repo's history were ever seen by anyone."
else
    echo "  nested repository already present, left untouched: $PROJECT_DIR/.git"
fi

if [ ! -d "$SOURCE_DIR" ]; then
    mkdir -p "$SOURCE_DIR"
    CREATED_THIS_RUN+=("$SOURCE_DIR")
    ROLLBACK_NEEDED=1
fi

if [ ! -d "$DROPBOX_DIR" ]; then
    mkdir -p "$DROPBOX_DIR"
    CREATED_THIS_RUN+=("$DROPBOX_DIR")
    ROLLBACK_NEEDED=1
    echo "  created: $DROPBOX_DIR/"
else
    echo "  already present, left untouched: $DROPBOX_DIR/"
fi

if [ ! -d "$TAKETHIS_DIR" ]; then
    mkdir -p "$TAKETHIS_DIR"
    CREATED_THIS_RUN+=("$TAKETHIS_DIR")
    ROLLBACK_NEEDED=1
    echo "  created: $TAKETHIS_DIR/"
else
    echo "  already present, left untouched: $TAKETHIS_DIR/"
fi

# ==============================
# Seed dropbox_manifest.json (v1.2.0)
# ==============================
# A permanent Factory file, not something regenerated per chunk. Written
# once with the fixed filename->destination patterns from
# factory_spec.md's Dropbox Specification. If it already exists (e.g. this
# project's Architect session has already appended project-specific entries
# to it), it is left completely untouched -- same idempotent rule as
# everything else in this script.

DROPBOX_MANIFEST="$DROPBOX_DIR/dropbox_manifest.json"

if [ ! -f "$DROPBOX_MANIFEST" ]; then
cat > "$DROPBOX_MANIFEST" <<'DROPBOX_EOF'
{
  "rules": [
    {"pattern": "^chunk(\\d+)\\.md$",
     "destination": "project/chunks/chunk{1}/chunk{1}.md"},
    {"pattern": "^execution_manifest_chunk(\\d+)\\.yaml$",
     "destination": "project/chunks/chunk{1}/execution_manifest.yaml"},
    {"pattern": "^C(\\d+)-(\\d+)_contract\\.md$",
     "destination": "project/chunks/chunk{1}/contracts/C{1}-{2}_contract.md"},
    {"pattern": "^C(\\d+)-(\\d+)_contract_report\\.md$",
     "destination": "project/chunks/chunk{1}/reports/C{1}-{2}/contract_report.md"},
    {"pattern": "^chunk(\\d+)_report\\.md$",
     "destination": "project/chunks/chunk{1}/chunk_report.md"},
    {"pattern": "^fix_package_chunk(\\d+)\\.md$",
     "destination": "project/chunks/chunk{1}/fix_package.md"},
    {"pattern": "^project_description\\.md$",
     "destination": "project/project_description.md"},
    {"pattern": "^architecture\\.md$",
     "destination": "project/architecture.md"},
    {"pattern": "^roadmap\\.md$",
     "destination": "project/roadmap.md"},
    {"pattern": "^project_knowledge\\.md$",
     "destination": "project/project_knowledge.md"},
    {"pattern": "^invariants\\.md$",
     "destination": "project/invariants.md"},
    {"pattern": "^AI_Note\\.md$",
     "destination": "project/AI_Note.md"},
    {"pattern": "^venue_requirements\\.md$",
     "destination": "project/venue_requirements.md"},
    {"pattern": "^key_facts\\.md$",
     "destination": "project/key_facts.md"},
    {"pattern": "^methodology_adversarial_review\\.md$",
     "destination": "project/methodology_adversarial_review.md"},
    {"pattern": "^chunk(\\d+)_data_manifest\\.json$",
     "destination": "project/chunks/chunk{1}/data_manifest.json"},
    {"pattern": "^chunk(\\d+)_reality_gate_report\\.md$",
     "destination": "project/chunks/chunk{1}/reality_gate_report.md"}
  ],
  "entries": []
}
DROPBOX_EOF
    echo "  created: $DROPBOX_MANIFEST (seeded with fixed rules)"
else
    echo "  already present, left untouched: $DROPBOX_MANIFEST"
fi

# ==============================
# Create .gitignore
# ==============================

echo ""
echo "[6/8] Updating .gitignore..."

touch .gitignore

grep -qxF "factory/" .gitignore || echo "factory/" >> .gitignore
grep -qxF "project/" .gitignore || echo "project/" >> .gitignore
grep -qxF "bootstrap.sh" .gitignore || echo "bootstrap.sh" >> .gitignore
grep -qxF "DROP_HERE/" .gitignore || echo "DROP_HERE/" >> .gitignore
grep -qxF "TAKE_THIS/" .gitignore || echo "TAKE_THIS/" >> .gitignore

# ==============================
# Record Provenance
# ==============================

echo ""
echo "[7/8] Recording Factory Information..."

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ ! -f "$PROJECT_DIR/factory_info.json" ]; then
cat > "$PROJECT_DIR/factory_info.json" <<EOF
{
  "factory_version": "$VERSION",
  "factory_reference": "$FACTORY_REF",
  "factory_commit": "$COMMIT",
  "factory_repository": "$FACTORY_REPO",
  "bootstrapped_on": "$TIMESTAMP",
  "bootstrap_command": "$0 $*"
}
EOF
    echo "  created: $PROJECT_DIR/factory_info.json"
else
    echo "  already present, left untouched: $PROJECT_DIR/factory_info.json"
fi

if [ ! -f "$PROJECT_DIR/factory_info.md" ]; then
cat > "$PROJECT_DIR/factory_info.md" <<EOF
# Factory Information

Factory Version

$VERSION

Factory Reference

$FACTORY_REF

Factory Commit

$COMMIT

Bootstrapped On

$TIMESTAMP

Factory Repository

$FACTORY_REPO

Bootstrap Command

$0 $*
EOF
    echo "  created: $PROJECT_DIR/factory_info.md"
else
    echo "  already present, left untouched: $PROJECT_DIR/factory_info.md"
fi

# ==============================
# Finish
# ==============================

echo ""
echo "[8/8] Finalizing..."

echo ""
echo "Running gatekeeper.py self-check (v1.3.4 -- diagnostic only, never fails bootstrap)..."
if command -v python3 >/dev/null 2>&1; then
    python3 factory/gatekeeper.py self-check || true
else
    echo "  SKIPPED -- python3 not found on PATH. Run 'python3 factory/gatekeeper.py self-check' manually once available."
fi

echo ""
echo "================================="
echo " Bootstrap Complete"
echo "================================="
echo ""

echo "factory/ contents match copy_factory_files in the manifest."
echo "project/, project/chunks/, source/ present."
echo ".gitignore updated."

echo ""
echo "Factory Version:"
echo "$VERSION"

echo ""
echo "Factory Commit:"
echo "$SHORT_COMMIT"

echo ""
echo "Next Step:"
echo ""
echo "Bootstrap this project according to Factory $VERSION"
