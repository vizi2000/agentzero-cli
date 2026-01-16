#!/bin/bash
# Bash completion helper for Agent Zero CLI slash commands.

COMMANDS=(
  "/help"
  "/theme"
  "/project"
  "/agent"
  "/new"
  "/close"
  "/clear"
  "/status"
  "/upload"
  "/rename"
  "/mode"
  "/context"
)

_agentzero_completions() {
  local cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=($(compgen -W "${COMMANDS[*]}" -- "$cur"))
}

complete -F _agentzero_completions agentzero agentzero-cli a0
