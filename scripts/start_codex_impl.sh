#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

PROMPT_FILE="$ROOT/docs/prompts/codex-implementation-handoff-prompt.md"

exec codex "$(cat "$PROMPT_FILE")"
