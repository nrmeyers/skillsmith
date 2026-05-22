#!/usr/bin/env bash
# Skillsmith signal-layer hook. Routed by SKILLSMITH_HOOK_EVENT env var.
# Soft-fails — always exits 0.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR"
while [[ "$ROOT" != "/" && ! -d "$ROOT/.git" ]]; do
    ROOT="$(dirname "$ROOT")"
done
cd "$ROOT" 2>/dev/null || exit 0

EVENT="${SKILLSMITH_HOOK_EVENT:-UserPromptSubmit}"

case "$EVENT" in
    UserPromptSubmit)
        skillsmith signal evaluate-phase \
            --prompt-file "${CLAUDE_PROMPT_FILE:-/dev/null}" 2>/dev/null || true
        ;;
    PostToolUse)
        TOOL="${SKILLSMITH_TOOL_NAME:-}"
        PATH_ARG="${SKILLSMITH_TOOL_PATH:-}"
        # Only fire on writes inside .skillsmith/contracts/
        if [[ "$TOOL" =~ ^(Edit|Write|MultiEdit)$ ]] \
           && [[ "$PATH_ARG" == *".skillsmith/contracts/"* ]]; then
            skillsmith signal watch-contract --path "$PATH_ARG" 2>/dev/null || true
        fi
        ;;
    PreToolUse)
        TOOL="${SKILLSMITH_TOOL_NAME:-}"
        skillsmith signal evaluate-system --tool "$TOOL" 2>/dev/null || true
        ;;
esac

exit 0
