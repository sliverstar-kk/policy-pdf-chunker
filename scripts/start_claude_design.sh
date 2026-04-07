#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

PROMPT_FILE="$ROOT/docs/prompts/claude-design-handoff-prompt.md"

exec claude "$(cat "$PROMPT_FILE")"
