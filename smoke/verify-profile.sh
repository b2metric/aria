#!/bin/bash
# ============================================================================
# smoke/verify-profile.sh — audit THIS project's Hermes profile against the
# Project Factory v4 contract: config-as-code symlinks, engineering-core,
# role + toolkit skills present AND curator-pinned, consumer bloat pruned,
# grounding + scaffolding.
#
# Thin wrapper over the canonical toolkit auditor (single source of truth, so
# the check can never drift). Auto-detects the slug from this repo's directory
# name and passes this repo as the workspace.
#
# Usage:  bash smoke/verify-profile.sh
#         HERMES_TOOLKIT=/path/to/hermes-toolkit bash smoke/verify-profile.sh
# Exit:   0 = PASS · 1 = drift detected · 2 = toolkit not found.
# ============================================================================
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SLUG="$(basename "$REPO")"
TOOLKIT="${HERMES_TOOLKIT:-$HOME/hermes-toolkit}"
VERIFY="$TOOLKIT/skills/project-factory/scripts/verify-project.sh"

if [ ! -f "$VERIFY" ]; then
  echo "verify-project.sh not found at: $VERIFY" >&2
  echo "Set HERMES_TOOLKIT, or clone B2M-Team/hermes-toolkit to ~/hermes-toolkit." >&2
  exit 2
fi

exec bash "$VERIFY" "$SLUG" "$REPO" "$@"
