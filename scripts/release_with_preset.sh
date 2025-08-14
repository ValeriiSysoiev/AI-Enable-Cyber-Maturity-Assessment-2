#!/usr/bin/env bash
set -euo pipefail
# Usage:
#   scripts/release_with_preset.sh [/path/to/preset.json]
# If a path is provided and the file exists, it will be copied into imports/ and uploaded after deploy.

PRESET_SRC="${1:-}"
PRESET_DST="${PRESET_DST:-imports/preset_cscm_v3.json}"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
mkdir -p "$(dirname "$PRESET_DST")"

if [ -n "$PRESET_SRC" ]; then
  if [ ! -f "$PRESET_SRC" ]; then
    echo "Preset not found at: $PRESET_SRC"
    exit 1
  fi
  echo "==> Copying preset to repo: $PRESET_SRC -> $PRESET_DST"
  cp "$PRESET_SRC" "$PRESET_DST"
  git add "$PRESET_DST"
fi

# Deploy (build in ACR + update Container Apps)
scripts/release.sh

# Upload preset if we have it locally
if [ -f "$PRESET_DST" ]; then
  scripts/upload_preset.sh "$PRESET_DST"
else
  echo "Preset not found at $PRESET_DST — upload later via the web UI (/admin/presets) or run:"
  echo "  scripts/upload_preset.sh /path/to/preset.json"
fi
