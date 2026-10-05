#!/bin/sh
# Offline bootstrap. Existing installations are reused only when their active bytes match.
set -eu
BUNDLE=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
TARGET=${1:-.}
mkdir -p "$TARGET"
TARGET=$(CDPATH='' cd -- "$TARGET" && pwd)
python3 - "$BUNDLE" "$TARGET" <<'PY'
import json
import shutil
import sys
from pathlib import Path

bundle, target = map(Path, sys.argv[1:])
source = bundle / 'factory'
destination = target / 'factory'
manifest = json.loads((source / 'bootstrap_manifest.yaml').read_text())
if manifest.get('schema_version') != 1 or manifest.get('factory_version') != '3.3.0' or manifest.get('active_root') != 'factory':
    raise SystemExit('Unsupported bootstrap manifest')
excluded = set(manifest['excluded_names'])
suffixes = tuple(manifest['excluded_suffixes'])

def active_files(folder):
    return {path.relative_to(folder): path.read_bytes() for path in folder.rglob('*')
            if path.is_file() and not set(path.relative_to(folder).parts) & excluded
            and not path.name.endswith(suffixes)}

if destination != source:
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_dir() or active_files(destination) != active_files(source):
            raise SystemExit('Existing factory differs from this installation; migrate in a new directory. No files changed.')
    else:
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*excluded, *('*' + suffix for suffix in suffixes)))
PY
python3 -B "$TARGET/factory/gatekeeper.py" init "$TARGET"
