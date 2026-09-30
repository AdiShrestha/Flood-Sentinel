#!/bin/sh
# Offline, idempotent bootstrap. No git clone, network, prompts, or silent upgrades.
set -eu
BUNDLE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET=${1:-.}
mkdir -p "$TARGET"
TARGET=$(CDPATH= cd -- "$TARGET" && pwd)
if [ "$TARGET" != "$BUNDLE" ]; then
    if [ -e "$TARGET/factory" ]; then
        printf '%s\n' 'Factory already exists in target; use its init command or migrate in a new folder.' >&2
        exit 31
    fi
    cp -R "$BUNDLE/factory" "$TARGET/factory"
fi
python3 "$TARGET/factory/gatekeeper.py" init "$TARGET"
