#!/usr/bin/env bash
# cc.sh — launch Claude Code on YOUR LLMs (claude-code-router → LiteLLM proxy).
# No Anthropic billing: requests route to gemini-reasoner / deepseek. See CLAUDE.md §2.
#   usage:  bash scripts/cc.sh        (wraps `ccr code .` with a preflight)
#   real Claude (Anthropic): just run `claude` instead.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1   # repo root

CCR_CONFIG="${CCR_CONFIG:-$HOME/.claude-code-router/config.json}"
LLM_HEALTH="${LLM_HEALTH:-http://localhost:4000/health/liveliness}"

command -v ccr >/dev/null 2>&1 || {
  echo "✗ claude-code-router (ccr) not found — install: npm i -g @musistudio/claude-code-router"; exit 1; }

[ -f "$CCR_CONFIG" ] || {
  echo "✗ no router config at $CCR_CONFIG"
  echo "  cp scripts/ccr-config.example.json \"$CCR_CONFIG\"   # then set your LiteLLM key"; exit 1; }

curl -fsS -o /dev/null --max-time 3 "$LLM_HEALTH" 2>/dev/null \
  || echo "⚠ LiteLLM proxy unreachable at $LLM_HEALTH — start it (hermes-llm-infra) or requests will fail."

echo "▶ Claude Code via claude-code-router → LiteLLM (own LLMs, no Anthropic billing)…"
exec ccr code .
