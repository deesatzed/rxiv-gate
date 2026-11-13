#!/usr/bin/env bash
# Copyright 2026 Wayne A. Satz, MD & Contributors
# Licensed under the Apache License, Version 2.0.
#
# Installs the rxiv-gate plugin into ~/.gemini/config/plugins/rxiv-gate

set -euo pipefail

PLUGIN_ID="rxiv-gate"
LEGACY_ID="antigravity-preprint-checker"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_ROOT="${HOME}/.gemini/config/plugins"
DEST_DIR="${DEST_ROOT}/${PLUGIN_ID}"

MODE="copy"
if [[ "${1:-}" == "--link" ]]; then
  MODE="link"
fi

mkdir -p "${DEST_ROOT}"

# Clean up legacy prototype symlink/folder if present to prevent duplicate skill/rule names
if [[ -L "${DEST_ROOT}/${LEGACY_ID}" || -d "${DEST_ROOT}/${LEGACY_ID}" ]]; then
  rm -rf "${DEST_ROOT}/${LEGACY_ID}"
fi

if [[ -L "${DEST_DIR}" || -d "${DEST_DIR}" ]]; then
  rm -rf "${DEST_DIR}"
fi

if [[ "${MODE}" == "link" ]]; then
  ln -s "${SRC_DIR}" "${DEST_DIR}"
  echo "Linked ${PLUGIN_ID} -> ${DEST_DIR}"
else
  mkdir -p "${DEST_DIR}"
  rsync -a \
    --exclude '.git' \
    --exclude '.pytest_cache' \
    --exclude '__pycache__' \
    --exclude '.preprint_gate' \
    "${SRC_DIR}/" "${DEST_DIR}/"
  echo "Installed ${PLUGIN_ID} -> ${DEST_DIR}"
fi

chmod +x "${SRC_DIR}/scripts/pre_submission_hook.py" || true
if [[ "${MODE}" == "copy" ]]; then
  chmod +x "${DEST_DIR}/scripts/pre_submission_hook.py" || true
fi

echo "Done! Restart Google Antigravity to activate '${PLUGIN_ID}'."
