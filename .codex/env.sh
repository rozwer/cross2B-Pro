#!/usr/bin/env bash

# Set project-local Codex home so this repo's config/skills are used.
# Usage (from repo root):
#   source .codex/env.sh

export CODEX_HOME="${CODEX_HOME:-$PWD/.codex}"
