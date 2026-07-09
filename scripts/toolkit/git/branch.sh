#!/bin/bash

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

ACTION="${1:-list}"
BRANCH="${2:-}"

cd "$PROJECT_ROOT" || exit 1

case "$ACTION" in
  list) git branch ;;
  create)
    [ -n "$BRANCH" ] || { echo "Uso: scripts/toolkit/git/branch.sh create <rama>"; exit 1; }
    git switch -c "$BRANCH"
    ;;
  switch)
    [ -n "$BRANCH" ] || { echo "Uso: scripts/toolkit/git/branch.sh switch <rama>"; exit 1; }
    git switch "$BRANCH"
    ;;
  *)
    echo "Uso: scripts/toolkit/git/branch.sh list|create|switch [rama]"
    exit 1
    ;;
esac
